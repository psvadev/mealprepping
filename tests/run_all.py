"""Run every tests/test_*.py in its own process; exit non-zero if any suite fails.

Run before committing changes to storage, import/export or Drive code:
    python tests/run_all.py                      # Firefox, WebKit and Chromium
    BROWSERS=firefox python tests/run_all.py     # one engine, for a quick loop
"""
import os, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
env = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # the suites print ⚠, → and emoji; cp1252 would crash on them
failed = []
for suite in sorted(here.glob("test_*.py")):
    print(f"\n=== {suite.name} ===", flush=True)
    if subprocess.run([sys.executable, str(suite)], cwd=here, env=env).returncode:
        failed.append(suite.name)
print("\nAll suites passed." if not failed else f"\nFailed suites: {', '.join(failed)}")
sys.exit(1 if failed else 0)
