import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.engine.generator import CompilerTestGenerator
from src.engine.runner import CompilerSandbox

def main():
    gen = CompilerTestGenerator(seed=42)
    suite = gen.generate_suite_with_metadata("compiler_tests", count=12, mode="balanced")
    sandbox = CompilerSandbox(compiler_type="gcc")

    print(f"=== VALIDATING ALL {len(suite)} GENERATED C++ CODES IN GCC CONTAINER ===")
    
    passed_validations = 0
    for idx, item in enumerate(suite, 1):
        test_filename = Path(item.filepath).name
        res = sandbox.run_compilation(item.filepath)
        
        status = res["status"]
        expected = item.expected_outcome
        duration = res["duration_ms"]
        
        is_match = (status == expected)
        if is_match:
            passed_validations += 1

        match_str = "CORRECT" if is_match else "DISCREPANCY"
        print(f"[{idx:02d}/12] {test_filename} -> {status} (Expected: {expected}) [{match_str}] in {duration}ms")
        print(f"       Category: {item.category} ({item.target_pass})")
        
        if status != "PASS":
            err_lines = [l.strip() for l in res["logs"].splitlines() if "error:" in l.lower() or "fatal" in l.lower()]
            if err_lines:
                print(f"       Compiler Diagnostic: {err_lines[0]}")
        print()

    print(f"SUMMARY: {passed_validations}/{len(suite)} test behaviors verified matching expectations.")

if __name__ == "__main__":
    main()
