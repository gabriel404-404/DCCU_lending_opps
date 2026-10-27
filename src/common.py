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


def dccu_branches(zip_path):
    """DCCU's charter number and branch rows from one NCUA call report zip."""
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        foicu_name = next(n for n in names if n.lower().endswith("foicu.txt"))
        branch_name = next(n for n in names if "branch" in n.lower())
        foicu = pd.read_csv(z.open(foicu_name), dtype=str, encoding="latin-1")
        branches = pd.read_csv(z.open(branch_name), dtype=str, encoding="latin-1")
    # NCUA lists DCCU as "DELTA COMMUNITY" (no "CREDIT UNION"), so match on that plus state.
    cu = foicu[foicu["CU_NAME"].str.upper().str.strip().str.startswith("DELTA COMMUNITY")
               & (foicu["STATE"] == s.STATE_ABBR)]
    if len(cu) != 1:
        raise ValueError(f"Expected one DCCU record in FOICU, found {len(cu)}")
    charter = cu["CU_NUMBER"].iloc[0]
    return charter, branches[branches["CU_NUMBER"] == charter]


def md_table(df):
    return df.to_markdown(index=False) if len(df) else "_none_"


def write_data_quality(phase, title, sections):
    """Replace one phase's section of DATA_QUALITY.md, keeping the other sections."""
    path = s.ROOT / "DATA_QUALITY.md"
    start, end = f"<!-- {phase}:start -->", f"<!-- {phase}:end -->"
    body = f"{start}\n## {title}\n\n" + "\n\n".join(sections) + f"\n{end}"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Data quality log\n\n"
    if start in text:
        text = text[:text.index(start)] + body + text[text.index(end) + len(end):]
    else:
        text = text.rstrip() + "\n\n" + body + "\n"
    path.write_text(text, encoding="utf-8")
