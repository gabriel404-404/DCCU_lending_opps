"""Helpers shared by the pipeline stages."""

import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as s  # noqa: E402

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "DCCU_lending_opps research script"


def fetch(url, dest, params=None, retries=4):
    """Download url to dest unless dest exists. Returns True if a network call was made.

    Writes to a .part file first and renames at the end, so an interrupted
    download never looks like a finished (cached) one.
    """
    dest = Path(dest)
    if dest.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    for attempt in range(1, retries + 1):
        try:
            with SESSION.get(url, params=params, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            tmp.replace(dest)
            return True
        except requests.RequestException as e:
            # A 4xx (e.g. 404 not found) won't fix itself on retry.
            client_error = getattr(e.response, "status_code", 500) < 500
            if attempt == retries or client_error:
                raise
            wait = 5 * attempt
            print(f"  retry {attempt} for {dest.name} in {wait}s ({e})")
            time.sleep(wait)


def read_hmda(path, **kw):
    # Read everything as text: tract and county codes have leading zeros, and
    # numeric fields can contain "Exempt" or "NA".
    return pd.read_csv(path, dtype=str, keep_default_na=False, **kw)


def lender_successors():
    """Merged lenders: old LEI -> successor LEI (config/lender_successors.csv, with sources)."""
    t = pd.read_csv(s.CONFIG / "lender_successors.csv", dtype=str)
    return t, t.set_index("old_lei")["successor_lei"].to_dict()


def lender_market(lender, year, columns):
    """One year of the shared market file, limited to the lender's product (its loan types).

    Every lender's loans of those types are kept, so competitors are measured the same way.
    A lender whose lending business went to another lender counts as that successor
    (config/lender_successors.csv), so a merger doesn't read as one rival vanishing and another
    surging.
    SQL: SELECT columns FROM market_{year} WHERE loan_type IN (lender's loan types).
    """
    m = pd.read_parquet(s.PROCESSED / f"market_{year}.parquet", columns=[*columns, "loan_type"])
    m = m[m["loan_type"].isin(lender.loan_types)].drop(columns="loan_type")
    if "lei" in m.columns:
        m["lei"] = m["lei"].replace(lender_successors()[1])
    return m


def ncua_branches(zip_path, charter):
    """A credit union's NCUA record (FOICU) and branch rows from one call report zip."""
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        foicu_name = next(n for n in names if n.lower().endswith("foicu.txt"))
        branch_name = next(n for n in names if "branch" in n.lower())
        foicu = pd.read_csv(z.open(foicu_name), dtype=str, encoding="latin-1")
        branches = pd.read_csv(z.open(branch_name), dtype=str, encoding="latin-1")
    cu = foicu[foicu["CU_NUMBER"] == charter]
    if len(cu) != 1:
        raise ValueError(f"Expected one FOICU record for NCUA charter {charter}, found {len(cu)}")
    return cu.iloc[0], branches[branches["CU_NUMBER"] == charter]


def md_table(df):
    return df.to_markdown(index=False) if len(df) else "_none_"


def write_data_quality(phase, title, sections, path=None, heading="# Data quality log"):
    """Replace one phase's section of a data-quality log, keeping the other sections.

    path defaults to the repo's DATA_QUALITY.md (market checks); lender stages pass the
    lender's own log (outputs/<key>/DATA_QUALITY.md).
    """
    path = path or s.ROOT / "DATA_QUALITY.md"
    start, end = f"<!-- {phase}:start -->", f"<!-- {phase}:end -->"
    body = f"{start}\n## {title}\n\n" + "\n\n".join(sections) + f"\n{end}"
    text = path.read_text(encoding="utf-8") if path.exists() else f"{heading}\n\n"
    if start in text:
        text = text[:text.index(start)] + body + text[text.index(end) + len(end):]
    else:
        text = text.rstrip() + "\n\n" + body + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def lender_log_heading(lender):
    return (f"# Data quality log: {lender.name}\n\nChecks for this lender. Market-wide checks "
            "(Phases 1-2: downloads, tracts, market definition) are in the repo's DATA_QUALITY.md.")
