"""Stage 1: download every raw source into data/raw/.

Each download is skipped if its file already exists, so re-running this script
only fetches what is missing (and makes no network calls once everything is cached).
It also builds config/ga_counties.csv from the downloaded county and OMB files.

Run from the repo root:  python src/01_download.py
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
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
            if attempt == retries:
                raise
            wait = 5 * attempt
            print(f"  retry {attempt} for {dest.name} in {wait}s ({e})")
            time.sleep(wait)


def download_reference_files():
    print("Reference files (county list, OMB delineation, TIGER tracts, ACS households)")
    fetch(s.GA_COUNTIES_URL, s.RAW / "census" / "st13_ga_cou2020.txt")
    fetch(s.OMB_DELINEATION_URL, s.RAW / "omb" / "list1_2023.xlsx")
    fetch(s.TIGER_TRACTS_URL, s.RAW / "tiger" / "tl_2024_13_tract.zip")
    fetch(s.ACS_B11001_URL, s.RAW / "acs" / f"acsdt5y{s.ACS_YEAR}-b11001.dat")


def build_county_config():
    """Write config/ga_counties.csv: all Georgia counties with FOM and Atlanta MSA flags."""
    counties = pd.read_csv(s.RAW / "census" / "st13_ga_cou2020.txt", sep="|", dtype=str)
    counties["county_fips"] = counties["STATEFP"] + counties["COUNTYFP"]
    counties["county_name"] = counties["COUNTYNAME"].str.replace(" County", "", regex=False)

    omb = pd.read_excel(s.RAW / "omb" / "list1_2023.xlsx", skiprows=2, dtype=str)
    atl = omb[omb["CBSA Code"] == s.ATLANTA_CBSA]
    atl_fips = set(atl["FIPS State Code"] + atl["FIPS County Code"])

    fom = pd.read_csv(s.CONFIG / "fom_counties.csv", dtype=str)
    # The FOM config was typed by hand, so check its FIPS codes against the Census list.
    merged = fom.merge(counties[["county_fips", "county_name"]], on="county_fips",
                       how="left", suffixes=("", "_census"))
    bad = merged[merged["county_name"] != merged["county_name_census"]]
    if len(bad):
        raise ValueError(f"FOM config FIPS/name mismatch:\n{bad}")

    out = counties[["county_fips", "county_name"]].copy()
    out["fom_flag"] = out["county_fips"].isin(fom["county_fips"]).astype(int)
    out["atlanta_msa_flag"] = out["county_fips"].isin(atl_fips).astype(int)
    out.to_csv(s.CONFIG / "ga_counties.csv", index=False)
    print(f"  config/ga_counties.csv: {len(out)} counties, "
          f"{out['fom_flag'].sum()} FOM, {out['atlanta_msa_flag'].sum()} in Atlanta MSA")
    return out["county_fips"].tolist()


def download_hmda(county_fips):
    print("HMDA filers, DCCU nationwide records, and row-count aggregations")
    hmda = s.RAW / "hmda"
    for y in s.YEARS:
        fetch(f"{s.HMDA_API}/filers", hmda / f"filers_{y}.json",
              params={"years": y, "states": s.STATE_ABBR})
        fetch(f"{s.HMDA_API}/csv", hmda / f"dccu_{y}.csv",
              params={"years": y, "leis": s.DCCU_LEI})
        # Statewide counts catch rows with no county code, which no county file contains.
        fetch(f"{s.HMDA_API}/aggregations", hmda / f"agg_{y}_state.json",
              params={"years": y, "states": s.STATE_ABBR, "actions_taken": "1,2,3,4,5,6,7,8"})

    # One small request per year x county, so an interrupted run resumes where it stopped.
    jobs = []
    for y in s.YEARS:
        for c in county_fips:
            jobs.append((f"{s.HMDA_API}/aggregations", hmda / str(y) / f"agg_{c}.json",
                         {"years": y, "counties": c, "actions_taken": "1,2,3,4,5,6,7,8"}))
            jobs.append((f"{s.HMDA_API}/csv", hmda / str(y) / f"{c}.csv",
                         {"years": y, "counties": c}))
    todo = [j for j in jobs if not j[1].exists()]
    print(f"  {len(jobs) - len(todo)} of {len(jobs)} county files cached; fetching {len(todo)}")
    done = 0
    # 4 parallel requests: faster than one at a time, still gentle on a public API.
    with ThreadPoolExecutor(max_workers=4) as pool:
        for _ in pool.map(lambda j: fetch(j[0], j[1], params=j[2]), todo):
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(todo)}")


def download_ncua():
    """Fetch the latest quarterly NCUA call report zip (it holds the branch file)."""
    print("NCUA call report (branch locations)")
    ncua = s.RAW / "ncua"
    existing = sorted(ncua.glob("call-report-data-*.zip")) if ncua.exists() else []
    if existing:
        print(f"  cached: {existing[-1].name}")
        return
    today = date.today()
    y, q_month = today.year, ((today.month - 1) // 3) * 3  # last completed quarter end
    for _ in range(6):
        if q_month == 0:
            y, q_month = y - 1, 12
        url = s.NCUA_URL_TEMPLATE.format(yyyy=y, mm=f"{q_month:02d}")
        if SESSION.head(url, timeout=60).status_code == 200:
            fetch(url, ncua / f"call-report-data-{y}-{q_month:02d}.zip")
            print(f"  downloaded {y}-{q_month:02d}")
            return
        q_month -= 3
    raise RuntimeError("No NCUA call report zip found for the last 6 quarters")


def main():
    download_reference_files()
    county_fips = build_county_config()
    download_hmda(county_fips)
    download_ncua()
    print("Done.")


if __name__ == "__main__":
    main()
