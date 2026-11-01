"""Regression check: does this run reproduce the lender's saved baseline exactly?

Compares every CSV in tests/baseline/<key>/<version>/ with the file the pipeline writes now,
cell by cell. Text must match exactly; numbers must match to 1e-9. Exits with an error on any
difference, and writes the result to the lender's data-quality log.

The v1 baseline was saved before the productize refactor, so it uses v1 names and paths
(`dccu_*` and `fom_*` columns, everything in data/processed/ and outputs/). map_v1() translates
each v1 file to where, and under what names, the same numbers live now.

Run from the repo root:  python src/check_baseline.py   (MGM_LENDER picks the lender)
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as s  # noqa: E402
from config.lender import LENDER as L  # noqa: E402
from src.common import lender_log_heading, md_table, write_data_quality  # noqa: E402

BASELINES = s.ROOT / "tests" / "baseline" / L.key
MARKET_CHECKS = {"1_row_counts", "4_missing_tracts", "4_tract_coverage", "5_exempt_fields",
                 "6_lender_name_changes", "7_acs_households", "exempt_flags_kept"}
RENAMED_FILES = {"2_3_dccu_reconciliation": "2_3_lender_reconciliation",
                 "8_dccu_branches": "8_branches", "dccu_api_reconciliation": "api_reconciliation"}
IGNORE_COLUMNS = {"key_numbers.csv": {"source", "description"}}  # notes about files, not numbers


def v1_names(text):
    """v1 names -> current names (columns, values and file names)."""
    for old, new in RENAMED_FILES.items():
        text = text.replace(old, new)
    text = re.sub(r"(?<![A-Za-z])dccu(?![A-Za-z])", "lender", text)
    return re.sub(r"(?<![A-Za-z])fom(?![A-Za-z])", "footprint", text)


def map_v1(rel):
    """Where a v1 baseline file's contents live now: [(current path, row filter, columns or None)]."""
    parts = Path(rel).parts
    name = Path(rel).stem
    if parts[0] == "outputs":
        return [(s.OUTPUTS / L.key / parts[-1], None, None)]
    if name == "lenders":
        return [(s.PROCESSED / "lenders.csv", None, None)]
    if name in MARKET_CHECKS:
        return [(s.PROCESSED / parts[-2] / parts[-1], None, None)]
    if name == "filter_waterfall":
        return [(s.PROCESSED / "phase2_checks" / "filter_waterfall.csv", None,
                 ["year", "step", "rows_all", "originations_all"]),
                (L.processed / "phase2_checks" / "filter_waterfall.csv", None,
                 ["year", "step", "rows_lender", "originations_lender"])]
    if name == "market_size":
        return [(s.PROCESSED / "phase2_checks" / "market_size.csv", ("scope", "statewide"),
                 ["year", "market_originations", "market_purchase", "market_refinance",
                  "market_no_tract", "lenders"]),
                (L.processed / "phase2_checks" / "market_size.csv", None, None)]
    sub = parts[2:-1]  # e.g. ("phase3_checks",) or ()
    return [(L.processed.joinpath(*sub) / f"{v1_names(name)}.csv", None, None)]


def read(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def same(a, b):
    """Cell-by-cell equality: exact text, or numbers within 1e-9."""
    if a == b:
        return True
    try:
        x, y = float(a), float(b)
    except ValueError:
        return False
    return bool(np.isclose(x, y, rtol=1e-9, atol=1e-12))


def compare(base, now, columns, ignore):
    """Differences between two tables, as short text lines."""
    problems = []
    cols = columns or list(base.columns)
    missing = [c for c in cols if c not in now.columns]
    extra = [] if columns else [c for c in now.columns if c not in base.columns]
    if missing or extra:
        problems.append(f"columns missing {missing}, extra {extra}")
    if len(base) != len(now):
        return problems + [f"rows {len(base)} vs. {len(now)}"]
    for c in [c for c in cols if c in now.columns and c not in ignore]:
        bad = [i for i, (x, y) in enumerate(zip(base[c], now[c])) if not same(x, y)]
        if bad:
            i = bad[0]
            problems.append(f"{c}: {len(bad)} cells differ (row {i}: {base[c][i]!r} vs. {now[c][i]!r})")
    return problems


def main():
    rows = []
    for version in sorted(p for p in BASELINES.iterdir() if p.is_dir()):
        for path in sorted(version.rglob("*.csv")):
            rel = path.relative_to(version).as_posix()
            base = read(path)
            base.columns = [v1_names(c) for c in base.columns]
            base = base.map(v1_names)
            for target, row_filter, columns in map_v1(rel):
                b = base
                if row_filter:
                    b = b[b[row_filter[0]] == row_filter[1]].reset_index(drop=True)
                if not target.exists():
                    problems = [f"missing: {target.relative_to(s.ROOT).as_posix()}"]
                else:
                    problems = compare(b, read(target), columns, IGNORE_COLUMNS.get(path.name, set()))
                rows.append({"baseline": f"{version.name}/{rel}",
                             "now": target.relative_to(s.ROOT).as_posix(), "rows": len(b),
                             "result": "match" if not problems else "; ".join(problems)})
    out = pd.DataFrame(rows)
    failed = out[out["result"] != "match"]
    sections = [
        f"### Result\n{len(out)} comparisons against `tests/baseline/{L.key}/`: **{len(out) - len(failed)} "
        f"match**, **{len(failed)} differ**. Text must match exactly and numbers to 1e-9; the v1 "
        "files use pre-productize names and paths, which the check translates.\n\n"
        + md_table(failed if len(failed) else out[["baseline", "now", "rows", "result"]].head(0))
        + ("" if len(failed) else "\n\nEvery file matches.")]
    write_data_quality("baseline", "Regression check against the saved baseline", sections,
                       path=L.data_quality, heading=lender_log_heading(L))
    print(f"{len(out)} comparisons: {len(out) - len(failed)} match, {len(failed)} differ")
    if len(failed):
        print(failed.to_string(index=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
