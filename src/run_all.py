"""Rebuild everything from raw data with one command: python src/run_all.py

Runs each stage in order and stops at the first failure. Downloads are cached,
so after the first run only the processing stages do real work.
"""

import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
STAGES = ["01_download.py", "02_validate.py", "03_market.py", "04_metrics.py", "05_context.py",
          "06_benchmarks.py", "07_outputs.py"]

for stage in STAGES:
    print(f"\n=== {stage} ===", flush=True)
    result = subprocess.run([sys.executable, str(SRC / stage)], cwd=SRC.parent)
    if result.returncode != 0:
        sys.exit(f"{stage} failed (exit code {result.returncode})")
print("\nAll stages finished.")
