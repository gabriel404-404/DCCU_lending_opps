# DCCU v1 baseline

Every CSV in `data/processed/` and `outputs/` as of commit 18cf1c8 (v1 complete, 2026-10-30),
before the productize refactor. `src/check_baseline.py` compares each DCCU run against these
files. They use v1's names (`dccu_*`, `fom_*`) and paths; the check maps them to the new ones.
Do not edit these files.
