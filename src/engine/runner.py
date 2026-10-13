"""Containerized Compiler Sandbox Runner module.

Executes C++ test compilation inside ephemeral Docker containers with strict resource
quotas and guaranteed container destruction.
"""

import io
import os
import tarfile
import time
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import docker
    from docker.errors import DockerException, NotFound, APIError
except ImportError:
    docker = None
    DockerException = Exception
    NotFound = Exception
    APIError = Exception


class CompilerSandbox:
    """Ephemeral Docker sandbox runner for compiling C++ test cases under strict quotas."""

    def __init__(
        self,
        compiler_type: str = "gcc",
        image_name: Optional[str] = None,
        mem_limit: str = "512m",
        cpu_quota: int = 50000,
        cpu_period: int = 100000,
        timeout_seconds: int = 30,
        compiler_cmd: Optional[str] = None,
    ):
        self.compiler_type = compiler_type.lower()
        if image_name:
            self.image_name = image_name
        else:
            self.image_name = "compiler-sandbox-clang" if self.compiler_type == "clang" else "compiler-sandbox-gcc"

        if compiler_cmd:
            self.compiler_cmd = compiler_cmd
        else:
            self.compiler_cmd = "clang++ -O3 -Wall" if self.compiler_type == "clang" else "g++ -O3 -Wall"

        self.mem_limit = mem_limit
        self.cpu_quota = cpu_quota
        self.cpu_period = cpu_period
        self.timeout_seconds = timeout_seconds
        self._client: Optional[docker.DockerClient] = None

    def get_client(self) -> docker.DockerClient:
        """Retrieves or initializes the Docker client instance."""
        if docker is None:
            raise RuntimeError("docker package is not installed. Run 'pip install docker'.")
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def is_docker_available(self) -> bool:
        """Checks whether the Docker daemon is accessible."""
        try:
            client = self.get_client()
            client.ping()
            return True
        except Exception:
            return False

    def _create_tar_archive(self, filename: str, content: str) -> io.BytesIO:
        """Creates an in-memory tar archive to inject into the container."""
        tar_stream = io.BytesIO()
        data = content.encode("utf-8")
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(data)
        tarinfo.mode = 0o644

        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tar.addfile(tarinfo, io.BytesIO(data))

        tar_stream.seek(0)
        return tar_stream

    def classify_status(self, exit_code: int, logs: str) -> str:
        """Determines the test outcome: PASS, COMPILE_ERROR, or CRASH."""
        if exit_code == 0:
            return "PASS"

        # Signal-based terminations:
        # 139 = SIGSEGV (128 + 11)
        # 134 = SIGABRT (128 + 6)
        # 137 = SIGKILL / OOM (128 + 9)
        # 136 = SIGFPE (128 + 8)
        # 132 = SIGILL (128 + 4)
        crash_signals = {139, 134, 137, 136, 132}
        lower_logs = logs.lower()

        is_ice_or_segfault = any(
            crash_indicator in lower_logs
            for crash_indicator in [
                "internal compiler error",
                "segmentation fault",
                "core dumped",
                "signal terminated",
                "out of memory",
                "please submit a full bug report",
            ]
        )

        if exit_code in crash_signals or is_ice_or_segfault:
            return "CRASH"

        return "COMPILE_ERROR"

    def run_compilation(
        self,
        test_file: str,
        source_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs compilation in an ephemeral container with strict resource limits.

        Ensures cleanup in a finally block regardless of success or failure.

        Returns:
            Dict containing:
                "test_file": str,
                "status": "PASS" | "COMPILE_ERROR" | "CRASH",
                "exit_code": int,
                "logs": str,
        """
        filename = Path(test_file).name
        if source_code is None:
            with open(test_file, "r", encoding="utf-8") as f:
                source_code = f.read()

        client = self.get_client()
        container = None
        logs = ""
        exit_code = -1
        start_time = time.perf_counter()

        try:
            # Spin up ephemeral container under strict isolation
            container = client.containers.create(
                image=self.image_name,
                command="/bin/bash -c 'sleep 3600'",
                mem_limit=self.mem_limit,
                cpu_quota=self.cpu_quota,
                cpu_period=self.cpu_period,
                network_mode="none",
                working_dir="/sandbox",
                detach=True,
            )
            container.start()

            # Inject test source code into the sandbox container
            tar_stream = self._create_tar_archive(filename, source_code)
            container.put_archive("/sandbox", tar_stream.getvalue())

            # Compile the injected file
            output_bin = f"/tmp/{Path(filename).stem}.out"
            cmd = f"{self.compiler_cmd} /sandbox/{filename} -o {output_bin}"
            exec_result = container.exec_run(
                cmd=f"/bin/bash -c '{cmd}'",
                demux=False,
            )

            exit_code = exec_result.exit_code
            raw_output = exec_result.output
            if isinstance(raw_output, bytes):
                logs = raw_output.decode("utf-8", errors="replace")
            else:
                logs = str(raw_output or "")

        except Exception as e:
            logs = f"Sandbox Execution Exception: {str(e)}"
            exit_code = -1
        finally:
            if container is not None:
                try:
                    container.stop(timeout=1)
                except Exception:
                    pass
                try:
                    container.remove(force=True)
                except Exception:
                    pass

        duration_ms = round((time.perf_counter() - start_time) * 1000, 1)
        status = self.classify_status(exit_code, logs)
        return {
            "test_file": str(test_file),
            "compiler": self.compiler_type,
            "status": status,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "logs": logs.strip(),
        }


if __name__ == "__main__":
    sandbox = CompilerSandbox()
    print("Docker available:", sandbox.is_docker_available())
