"""Rebuild everything from raw data with one command:

    python src/run_all.py                  # the default lender (dccu)
    python src/run_all.py --lender dccu    # one configured lender
    python src/run_all.py --lender all     # every lender under config/lenders/

Market stages (01-03) run once and cover every configured lender's raw inputs and checks.
Lender stages (04-07) run once per lender, which is picked with the MGM_LENDER environment
variable. Afterwards, any lender with a saved baseline (tests/baseline/<key>/) is compared with
it. Stops at the first failure. Downloads are cached, so after the first run only the
processing stages do real work.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC.parent))
from config import settings as s  # noqa: E402
from config.lender import DEFAULT, configured  # noqa: E402

MARKET_STAGES = ["01_download.py", "02_validate.py", "03_market.py"]
LENDER_STAGES = ["04_metrics.py", "05_context.py", "06_benchmarks.py", "07_outputs.py"]


def run(script, lender=None):
    label = f"{script} [{lender}]" if lender else script
    print(f"\n=== {label} ===", flush=True)
    env = os.environ | ({"MGM_LENDER": lender} if lender else {})
    result = subprocess.run([sys.executable, str(SRC / script)], cwd=SRC.parent, env=env)
    if result.returncode != 0:
        sys.exit(f"{label} failed (exit code {result.returncode})")


def main():
    parser = argparse.ArgumentParser(description="Rebuild the pipeline from raw data.")
    parser.add_argument("--lender", default=DEFAULT,
                        help="a lender key under config/lenders/, or 'all' (default: %(default)s)")
    args = parser.parse_args()
    keys = [lc.key for lc in configured()]
    lenders = keys if args.lender == "all" else [args.lender]
    unknown = [k for k in lenders if k not in keys]
    if unknown:
        sys.exit(f"Unknown lender {unknown}; configured: {keys}")

    for script in MARKET_STAGES:
        run(script)
    for key in lenders:
        for script in LENDER_STAGES:
            run(script, key)
        if (s.ROOT / "tests" / "baseline" / key).exists():
            run("check_baseline.py", key)
    print("\nAll stages finished.")


if __name__ == "__main__":
    main()
