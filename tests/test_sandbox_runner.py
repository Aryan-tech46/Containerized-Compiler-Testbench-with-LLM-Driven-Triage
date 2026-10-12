import unittest
import subprocess
from src.engine.runner import CompilerSandbox


class TestCompilerSandbox(unittest.TestCase):
    def setUp(self):
        self.sandbox = CompilerSandbox(image_name="compiler-sandbox-gcc")

    def test_clean_cpp_compilation(self):
        clean_code = """
#include <iostream>
int main() {
    std::cout << "Hello Antigravity" << std::endl;
    return 0;
}
"""
        result = self.sandbox.run_compilation("test_clean.cpp", source_code=clean_code)
        print("Clean Test Result:", result["status"], "Exit code:", result["exit_code"])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["exit_code"], 0)

    def test_syntax_error_compilation(self):
        broken_code = """
#include <iostream>
int main() {
    this_is_an_invalid_syntax_error_undefined_identifier;
    return 0;
}
"""
        result = self.sandbox.run_compilation("test_broken.cpp", source_code=broken_code)
        print("Broken Test Result:", result["status"], "Exit code:", result["exit_code"])
        self.assertEqual(result["status"], "COMPILE_ERROR")
        self.assertNotEqual(result["exit_code"], 0)
        self.assertIn("error:", result["logs"])

    def test_zero_orphaned_containers(self):
        # Verify docker ps -a contains zero orphaned containers from the tests
        out = subprocess.check_output(["docker", "ps", "-a", "--filter", "ancestor=compiler-sandbox-gcc", "-q"], text=True)
        containers = [c.strip() for c in out.strip().splitlines() if c.strip()]
        self.assertEqual(len(containers), 0, f"Found orphaned containers: {containers}")


if __name__ == "__main__":
    unittest.main()
