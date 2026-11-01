"""Regression check: does this run reproduce the lender's saved baseline exactly?

Compares every CSV in tests/baseline/<key>/<version>/ with the file the pipeline writes now,
cell by cell. Text must match exactly; numbers must match to 1e-9. Exits with an error on any
difference, and writes the result to the lender's data-quality log.

DCCU's v1 baseline was saved before the productize refactor, so it uses v1 names and paths
(`dccu_*` and `fom_*` columns, everything in data/processed/ and outputs/). map_v1() translates
each v1 file to where, and under what names, the same numbers live now. Changes decided on
purpose are listed below (SUPERSEDED, ADDED_COLUMNS), each with the productize step that made
it. Everything else must match.

Later baselines are saved with --save under current names: processed/ is a copy of the
lender's data/processed/<key>/ CSVs and outputs/ of its outputs/<key>/ CSVs. --save also writes
tests/baseline/<key>/CURRENT, the one version the check compares against; older versions stay as
history. Without a CURRENT file, every version is compared.

Run from the repo root (MGM_LENDER picks the lender):
    python src/check_baseline.py               # compare every saved baseline
    python src/check_baseline.py --save p3     # save this run as tests/baseline/<key>/p3/
"""

import argparse
import re
import shutil
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
                 "6_lender_name_changes", "7_acs_households"}
RENAMED_FILES = {"2_3_dccu_reconciliation": "2_3_lender_reconciliation",
                 "8_dccu_branches": "8_branches", "dccu_api_reconciliation": "api_reconciliation"}
IGNORE_COLUMNS = {"key_numbers.csv": {"source", "description"}}  # notes about files, not numbers
# v1 files no run can reproduce any more, with the reason (reported, not failed).
SUPERSEDED = {"exempt_flags_kept": "P2: the market files keep all loan types, so this market-wide "
                                   "count now includes FHA, VA and USDA rows"}
# Columns a later step added on purpose, by baseline path; every v1 column must still match.
ADDED_COLUMNS = {  # P2: ladder fallback (unit county or tract)
    "data/processed/benchmark_ladder.csv": {"unit"},
    "data/processed/depth_ladder_by_county.csv": {"top_quarter_tracts"},
    "outputs/depth_by_county.csv": {"top_quarter_tracts"},
}


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
    # Since P2 the root market tables count all loan types. v1's market numbers (conventional
    # only) are the market as the lender defines it, which its own waterfall and market size hold.
    if name in ("filter_waterfall", "market_size"):
        return [(L.processed / "phase2_checks" / f"{name}.csv", None, None)]
    sub = parts[2:-1]  # e.g. ("phase3_checks",) or ()
    return [(L.processed.joinpath(*sub) / f"{v1_names(name)}.csv", None, None)]


def map_saved(rel):
    """Where a file of a baseline saved under current names (with --save) lives now."""
    top, rest = Path(rel).parts[0], Path(*Path(rel).parts[1:])
    return [((L.processed if top == "processed" else L.outputs) / rest, None, None)]


def save(version):
    """Copy the lender's current CSVs to tests/baseline/<key>/<version>/ (never overwrites)."""
    dest = BASELINES / version
    if dest.exists():
        sys.exit(f"{dest.relative_to(s.ROOT).as_posix()} already exists; pick a new version name")
    n = 0
    for top, src in [("processed", L.processed), ("outputs", L.outputs)]:
        for path in sorted(src.rglob("*.csv")):
            target = dest / top / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            n += 1
    (BASELINES / "CURRENT").write_text(version + "\n", encoding="utf-8")
    print(f"Saved {n} CSVs to {dest.relative_to(s.ROOT).as_posix()}; CURRENT = {version}")


def versions():
    """The baseline version(s) to compare: the one named in CURRENT, else all of them."""
    current = BASELINES / "CURRENT"
    if current.exists():
        return [BASELINES / current.read_text(encoding="utf-8").strip()]
    return sorted(p for p in BASELINES.iterdir() if p.is_dir())


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


def compare(base, now, columns, ignore, added=frozenset()):
    """Differences between two tables, as short text lines."""
    problems = []
    cols = columns or list(base.columns)
    missing = [c for c in cols if c not in now.columns]
    extra = [] if columns else [c for c in now.columns if c not in base.columns and c not in added]
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
    parser = argparse.ArgumentParser(description="Compare this run with the lender's saved baselines.")
    parser.add_argument("--save", metavar="VERSION", help="save this run as a new baseline instead")
    args = parser.parse_args()
    if args.save:
        return save(args.save)
    rows = []
    for version in versions():
        for path in sorted(version.rglob("*.csv")):
            rel = path.relative_to(version).as_posix()
            v1 = version.name == "v1"  # the only baseline saved under pre-productize names
            if v1 and path.stem in SUPERSEDED:
                rows.append({"baseline": f"{version.name}/{rel}", "now": "", "rows": 0,
                             "result": f"superseded: {SUPERSEDED[path.stem]}"})
                continue
            base = read(path)
            if v1:
                base.columns = [v1_names(c) for c in base.columns]
                base = base.map(v1_names)
            for target, row_filter, columns in (map_v1(rel) if v1 else map_saved(rel)):
                b = base
                if row_filter:
                    b = b[b[row_filter[0]] == row_filter[1]].reset_index(drop=True)
                if not target.exists():
                    problems = [f"missing: {target.relative_to(s.ROOT).as_posix()}"]
                else:
                    problems = compare(b, read(target), columns, IGNORE_COLUMNS.get(path.name, set()),
                                       ADDED_COLUMNS.get(rel, frozenset()))
                rows.append({"baseline": f"{version.name}/{rel}",
                             "now": target.relative_to(s.ROOT).as_posix(), "rows": len(b),
                             "result": "match" if not problems else "; ".join(problems)})
    out = pd.DataFrame(rows)
    superseded = out[out["result"].str.startswith("superseded")]
    failed = out[(out["result"] != "match") & ~out["result"].str.startswith("superseded")]
    compared = len(out) - len(superseded)
    v1_note = (
        " The v1 files use pre-productize names and paths, which the check translates. Decided "
        "changes (`src/check_baseline.py`): superseded files, and columns added later "
        f"({', '.join(f'`{f}`: {sorted(c)}' for f, c in ADDED_COLUMNS.items())}), which are allowed "
        "while every v1 column still matches." if (BASELINES / "v1").exists() else "")
    sections = [
        f"### Result\n{compared} comparisons against `tests/baseline/{L.key}/` "
        f"({', '.join(v.name for v in versions())}): **{compared - len(failed)} "
        f"match**, **{len(failed)} differ**; {len(superseded)} file(s) superseded on purpose. Text must "
        f"match exactly and numbers to 1e-9.{v1_note}\n\n"
        + md_table(pd.concat([failed, superseded])[["baseline", "now", "rows", "result"]])
        + ("" if len(failed) else "\n\nEvery compared file matches.")]
    write_data_quality("baseline", "Regression check against the saved baseline", sections,
                       path=L.data_quality, heading=lender_log_heading(L))
    print(f"{compared} comparisons: {compared - len(failed)} match, {len(failed)} differ; "
          f"{len(superseded)} superseded")
    if len(failed):
        print(failed.to_string(index=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
