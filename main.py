"""Main CLI Entry Point: Containerized Compiler Testbench with LLM-Driven Triage.

Orchestrates synthetic edge-case C++ test generation, isolated compilation inside
Docker containers, RAG vector retrieval, and AI triage reporting.
"""

import argparse
import os
import sys
import warnings
from pathlib import Path
from typing import List

# Suppress library deprecation warnings from polluting CLI output
warnings.filterwarnings("ignore", category=FutureWarning)

from dotenv import load_dotenv

# Ensure stdout uses UTF-8 encoding on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

from src.engine.generator import CompilerTestGenerator
from src.engine.runner import CompilerSandbox
from src.rag.vector_store import HistoricalBugVectorStore
from src.llm.triage_agent import CompilerTriageAgent
from src.utils.cache import TriageCache

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown

    console = Console()
except ImportError:
    console = None


def print_banner():
    banner = """
================================================================================
   CONTAINERIZED COMPILER TESTBENCH & LLM TRIAGE ENGINE
================================================================================
"""
    if console:
        console.print(f"[bold cyan]{banner}[/bold cyan]")
    else:
        print(banner)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Containerized Compiler Testbench with LLM-Driven Triage"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=4,
        help="Number of synthetic C++ test cases to generate and evaluate (default: 4)",
    )
    parser.add_argument(
        "--seed-db",
        action="store_true",
        help="Seed historical compiler crash signatures into the vector store",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Stream real-time container status and compilation feedback",
    )
    parser.add_argument(
        "--image",
        type=str,
        default="compiler-sandbox-gcc",
        help="Docker sandbox image tag to run (default: compiler-sandbox-gcc)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="compiler_tests",
        help="Directory to save generated test suites (default: compiler_tests)",
    )
    parser.add_argument(
        "--inject-broken",
        action="store_true",
        help="Inject a deliberate compiler stress/syntax edge file to verify the AI triage loop",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    print_banner()

    # 1. Initialize RAG Vector Store & Cache
    if console:
        console.print("[dim]Initializing vector store & caching layer...[/dim]")
    vector_store = HistoricalBugVectorStore()
    cache = TriageCache()
    triage_agent = CompilerTriageAgent()

    if args.seed_db:
        if console:
            console.print("[bold yellow]Seeding historical compiler crash dataset into Vector Store...[/bold yellow]")
        else:
            print("Seeding historical compiler crash dataset into Vector Store...")
        seed_count = vector_store.seed_historical_bugs()
        if console:
            console.print(f"[bold green]✓ Successfully seeded {seed_count} historical bug signatures.[/bold green]\n")
        else:
            print(f"Successfully seeded {seed_count} historical bug signatures.\n")

    # 2. Test Case Generation
    if console:
        console.print(f"[bold cyan]Generating {args.count} synthetic C++ compiler stress tests into '{args.output_dir}'...[/bold cyan]")
    else:
        print(f"Generating {args.count} synthetic C++ compiler stress tests into '{args.output_dir}'...")

    generator = CompilerTestGenerator()
    test_files = generator.generate_suite(output_dir=args.output_dir, count=args.count)

    # If requested or for demonstration, add a deliberate stress/syntax violation to trigger RAG triage
    if args.inject_broken:
        broken_path = os.path.join(args.output_dir, "test_edge_ice_violation.cpp")
        with open(broken_path, "w", encoding="utf-8") as f:
            f.write(
                "// Deliberate SFINAE / concept recursion limit violation\n"
                "#include <type_traits>\n"
                "template <typename T> struct InfiniteRec : InfiniteRec<T*> {};\n"
                "int main() { InfiniteRec<int> x; return 0; }\n"
            )
        test_files.append(broken_path)

    # 3. Setup Sandbox Runner
    sandbox = CompilerSandbox(image_name=args.image)
    if not sandbox.is_docker_available():
        msg = f"[CRITICAL] Docker daemon is not accessible. Ensure Docker Desktop is active."
        if console:
            console.print(f"[bold red]{msg}[/bold red]")
        else:
            print(msg)
        return 1

    # 4. Compilation Pipeline Execution
    results = []
    if console:
        console.print(f"[bold green]Running sandboxed compilation inside ephemeral containers ({args.image})...[/bold green]\n")
    else:
        print(f"Running sandboxed compilation inside ephemeral containers ({args.image})...\n")

    for idx, test_file in enumerate(test_files, 1):
        test_name = Path(test_file).name
        if args.live:
            if console:
                console.print(f"  [dim]Executing [{idx}/{len(test_files)}] {test_name}...[/dim]")
            else:
                print(f"  Executing [{idx}/{len(test_files)}] {test_name}...")

        run_result = sandbox.run_compilation(test_file)
        results.append(run_result)
        status = run_result["status"]
        exit_code = run_result["exit_code"]

        if status == "PASS":
            if console:
                console.print(f"  [bold green][PASS][/bold green] {test_name} (Exit code: {exit_code})")
            else:
                print(f"  [PASS] {test_name} (Exit code: {exit_code})")
        else:
            # Alert on COMPILE_ERROR or CRASH
            badge_color = "bold red" if status == "CRASH" else "bold yellow"
            if console:
                console.print(f"  [{badge_color}][{status}][/{badge_color}] {test_name} (Exit code: {exit_code})")
            else:
                print(f"  [{status}] {test_name} (Exit code: {exit_code})")

            # Trigger RAG Retrieval
            crash_logs = run_result["logs"]
            if console:
                console.print("    [cyan]→ Querying Pinecone vector store for matching historical bugs...[/cyan]")
            else:
                print("    -> Querying Pinecone vector store for matching historical bugs...")

            similar_bugs = vector_store.query_similar_bugs(crash_logs, top_k=3)

            # Trigger AI Triage
            if console:
                console.print("    [magenta]→ Dispatching to LLM Triage Agent fallback chain...[/magenta]")
            else:
                print("    -> Dispatching to LLM Triage Agent fallback chain...")

            cached_report = cache.get(crash_logs)
            if cached_report:
                from src.llm.triage_agent import TriageReport
                report = TriageReport(**cached_report)
            else:
                report = triage_agent.triage(crash_logs, similar_bugs)
                cache.set(crash_logs, report.model_dump())

            # Render Triage Report
            md_output = report.to_markdown()
            if console:
                console.print(Panel(Markdown(md_output), title=f"Triage Analysis: {test_name}", border_style="red"))
            else:
                print("\n" + md_output + "\n")

    # 5. Summary Dashboard
    total_count = len(results)
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    err_count = sum(1 for r in results if r["status"] == "COMPILE_ERROR")
    crash_count = sum(1 for r in results if r["status"] == "CRASH")

    if console:
        table = Table(title="Testbench Compilation Summary")
        table.add_column("Total Tests", justify="center", style="bold")
        table.add_column("Passed", justify="center", style="green")
        table.add_column("Compile Errors", justify="center", style="yellow")
        table.add_column("Crashes / ICE", justify="center", style="red")
        table.add_row(str(total_count), str(pass_count), str(err_count), str(crash_count))
        console.print("\n", table)
    else:
        print("\n=== Testbench Compilation Summary ===")
        print(f"Total: {total_count} | Passed: {pass_count} | Compile Errors: {err_count} | Crashes: {crash_count}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
