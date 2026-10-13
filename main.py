"""Main CLI Entry Point: Containerized Compiler Testbench with LLM-Driven Triage.

Orchestrates synthetic edge-case C++ test generation, isolated compilation inside
ephemeral Docker containers, RAG vector retrieval, and AI triage reporting.
"""

import argparse
import os
import sys
import time
import warnings
from pathlib import Path
from typing import List, Dict, Any

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
    """Prints a responsive terminal banner that automatically adapts to window width."""
    title = "CONTAINERIZED COMPILER TESTBENCH & LLM TRIAGE ENGINE"
    subtitle = "Isolated Docker Sandboxing • Pinecone Vector RAG • Multi-Model Fallback AI Triage"
    if console:
        console.print(
            Panel(
                f"[bold cyan]{title}[/bold cyan]\n[dim]{subtitle}[/dim]",
                border_style="cyan",
                expand=True,
            )
        )
    else:
        print(f"\n=== {title} ===\n{subtitle}\n")


def print_system_diagnostics(
    docker_available: bool,
    compiler_mode: str,
    vector_store: HistoricalBugVectorStore,
    triage_agent: CompilerTriageAgent,
    cache: TriageCache,
):
    """Renders a startup diagnostic summary table showing connected services."""
    docker_status = (
        f"[green]Connected[/green] (Target: {compiler_mode.upper()})"
        if docker_available
        else "[red]Offline / Daemon Unreachable[/red]"
    )

    rag_status = (
        f"[green]Pinecone Cloud Active[/green] (Index: {vector_store.index_name})"
        if vector_store._index is not None
        else "[yellow]Local Fallback Vector Engine[/yellow] (In-Memory Cosine Store)"
    )

    # LLM Provider chains
    gemini_active = bool(triage_agent.gemini_api_key)
    grok_active = bool(triage_agent.grok_api_key)

    if gemini_active and grok_active:
        llm_status = f"[green]Multi-Provider Active[/green] (1: Gemini Flash, 2: Grok 2)"
    elif gemini_active:
        llm_status = f"[green]Gemini Active[/green] ({triage_agent.primary_model})" + " | [dim]Grok: Unconfigured[/dim]"
    elif grok_active:
        llm_status = f"[green]Grok Active[/green] ({triage_agent.grok_model})" + " | [dim]Gemini: Unconfigured[/dim]"
    else:
        llm_status = "[yellow]Offline Heuristic Compiler Agent[/yellow] (Deterministic Rulebase)"

    cache_status = (
        f"[green]Redis Online[/green] ({cache.host}:{cache.port})"
        if cache._client is not None
        else "[dim]In-Memory Cache[/dim]"
    )

    if console:
        table = Table(
            title="Runtime Diagnostics & Environment Status",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Subsystem", style="bold", width=24)
        table.add_column("Status & Driver", style="white")
        table.add_row("Docker Sandbox", docker_status)
        table.add_row("RAG Vector Store", rag_status)
        table.add_row("AI Triage Chains", llm_status)
        table.add_row("Report Cache", cache_status)
        console.print(table)
        console.print()
    else:
        print("=== Runtime Diagnostics & Environment Status ===")
        print(f"Docker Sandbox:   {docker_status}")
        print(f"RAG Vector Store:  {rag_status}")
        print(f"AI Triage Chains:  {llm_status}")
        print(f"Report Cache:     {cache_status}\n")


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
        "--mode",
        type=str,
        choices=["balanced", "aggressive", "valid-only"],
        default="balanced",
        help="Stress mode: 'balanced' (mix of valid and limit edge tests), 'aggressive' (heavy failure induction), 'valid-only' (sanity)",
    )
    parser.add_argument(
        "--compiler",
        type=str,
        choices=["gcc", "clang", "both"],
        default="gcc",
        help="Target compiler environment: 'gcc', 'clang', or 'both' for differential testing (default: gcc)",
    )
    parser.add_argument(
        "--seed-db",
        action="store_true",
        help="Seed historical compiler crash signatures into the vector store",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Stream real-time container status and compilation latency",
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


def run_test_and_triage(
    sandbox: CompilerSandbox,
    test_file: str,
    vector_store: HistoricalBugVectorStore,
    triage_agent: CompilerTriageAgent,
    cache: TriageCache,
    live: bool,
) -> Dict[str, Any]:
    """Compiles a single test file and triggers RAG triage if failure/crash occurs."""
    test_name = Path(test_file).name
    compiler_tag = sandbox.compiler_type.upper()

    if live and console:
        with console.status(f"[bold cyan]Compiling {test_name} with {compiler_tag}...[/bold cyan]"):
            run_result = sandbox.run_compilation(test_file)
    else:
        run_result = sandbox.run_compilation(test_file)

    status = run_result["status"]
    exit_code = run_result["exit_code"]
    duration_ms = run_result.get("duration_ms", 0.0)

    if status == "PASS":
        badge = "[bold green][PASS][/bold green]"
        line = f"  {badge} [{compiler_tag}] {test_name} (Exit: {exit_code}, {duration_ms}ms)"
        if console:
            console.print(line)
        else:
            print(line)
    else:
        badge_color = "bold red" if status == "CRASH" else "bold yellow"
        badge = f"[{badge_color}][{status}][/{badge_color}]"
        line = f"  {badge} [{compiler_tag}] {test_name} (Exit: {exit_code}, {duration_ms}ms)"
        if console:
            console.print(line)
        else:
            print(line)

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
            console.print(Panel(Markdown(md_output), title=f"Triage Analysis: {test_name} ({compiler_tag})", border_style="red"))
        else:
            print("\n" + md_output + "\n")

    return run_result


def main() -> int:
    args = parse_arguments()
    print_banner()

    # 1. Initialize RAG Vector Store & Cache
    vector_store = HistoricalBugVectorStore()
    cache = TriageCache()
    triage_agent = CompilerTriageAgent()

    # 2. Setup Sandboxes
    sandboxes: List[CompilerSandbox] = []
    if args.compiler in ["gcc", "both"]:
        sandboxes.append(CompilerSandbox(compiler_type="gcc"))
    if args.compiler in ["clang", "both"]:
        sandboxes.append(CompilerSandbox(compiler_type="clang"))

    docker_available = all(sb.is_docker_available() for sb in sandboxes)
    print_system_diagnostics(
        docker_available=docker_available,
        compiler_mode=args.compiler,
        vector_store=vector_store,
        triage_agent=triage_agent,
        cache=cache,
    )

    if not docker_available:
        msg = "[CRITICAL] Docker daemon is unreachable. Please ensure Docker Desktop is running."
        if console:
            console.print(f"[bold red]{msg}[/bold red]")
        else:
            print(msg)
        return 1

    # 3. Seed Database if requested
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

    # 4. Test Case Generation
    if console:
        console.print(
            f"[bold cyan]Generating {args.count} tests ({args.mode} mode) into '{args.output_dir}'...[/bold cyan]"
        )
    else:
        print(f"Generating {args.count} tests ({args.mode} mode) into '{args.output_dir}'...")

    generator = CompilerTestGenerator()
    test_files = generator.generate_suite(
        output_dir=args.output_dir,
        count=args.count,
        mode=args.mode,
    )

    if args.inject_broken:
        broken_path = os.path.join(args.output_dir, "test_manual_injected_ice.cpp")
        with open(broken_path, "w", encoding="utf-8") as f:
            f.write(
                "// Deliberate SFINAE / concept recursion limit violation\n"
                "#include <type_traits>\n"
                "template <typename T> struct InfiniteRec : InfiniteRec<T*> {};\n"
                "int main() { InfiniteRec<int> x; return 0; }\n"
            )
        test_files.append(broken_path)

    # 5. Compilation Pipeline Execution
    if console:
        console.print(f"[bold green]Running sandboxed compilation inside ephemeral containers...[/bold green]\n")
    else:
        print(f"Running sandboxed compilation inside ephemeral containers...\n")

    all_results: List[Dict[str, Any]] = []

    for test_file in test_files:
        for sandbox in sandboxes:
            res = run_test_and_triage(
                sandbox=sandbox,
                test_file=test_file,
                vector_store=vector_store,
                triage_agent=triage_agent,
                cache=cache,
                live=args.live,
            )
            all_results.append(res)

    # 6. Summary Dashboard
    total_count = len(all_results)
    pass_count = sum(1 for r in all_results if r["status"] == "PASS")
    err_count = sum(1 for r in all_results if r["status"] == "COMPILE_ERROR")
    crash_count = sum(1 for r in all_results if r["status"] == "CRASH")

    if console:
        table = Table(title="Testbench Compilation Summary")
        table.add_column("Compiler", justify="center", style="bold")
        table.add_column("Total Executions", justify="center", style="bold")
        table.add_column("Passed", justify="center", style="green")
        table.add_column("Compile Errors", justify="center", style="yellow")
        table.add_column("Crashes / ICE", justify="center", style="red")

        for c_type in (["gcc", "clang"] if args.compiler == "both" else [args.compiler]):
            sub_results = [r for r in all_results if r.get("compiler", "").lower() == c_type]
            if sub_results:
                table.add_row(
                    c_type.upper(),
                    str(len(sub_results)),
                    str(sum(1 for r in sub_results if r["status"] == "PASS")),
                    str(sum(1 for r in sub_results if r["status"] == "COMPILE_ERROR")),
                    str(sum(1 for r in sub_results if r["status"] == "CRASH")),
                )

        console.print("\n", table)
    else:
        print("\n=== Testbench Compilation Summary ===")
        print(f"Total: {total_count} | Passed: {pass_count} | Compile Errors: {err_count} | Crashes: {crash_count}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
