#!/usr/bin/env python3
"""Run all tests and write results to a file."""
import io, sys, subprocess, os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "--tb=short", "-q"],
    capture_output=True, text=True
)

outfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results.txt")
with open(outfile, "w", encoding="utf-8") as f:
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)
    f.write("\n=== EXIT CODE: %d ===\n" % result.returncode)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
print("STDOUT:")
print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
print("EXIT CODE:", result.returncode)
