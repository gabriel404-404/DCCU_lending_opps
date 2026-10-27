"""Stage 1: download every raw source into data/raw/.

Each download is skipped if its file already exists, so re-running this script
only fetches what is missing (and makes no network calls once everything is cached).
It also builds config/ga_counties.csv from the downloaded county and OMB files.

Run from the repo root:  python src/01_download.py
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as s  # noqa: E402
from src.common import SESSION, fetch  # noqa: E402


def download_reference_files():
    print("Reference files (county list, OMB delineation, TIGER tracts, ACS households)")
    fetch(s.GA_COUNTIES_URL, s.RAW / "census" / "st13_ga_cou2020.txt")
    fetch(s.OMB_DELINEATION_URL, s.RAW / "omb" / "list1_2023.xlsx")
    fetch(s.TIGER_TRACTS_URL, s.RAW / "tiger" / "tl_2024_13_tract.zip")
    fetch(s.ACS_B11001_URL, s.RAW / "acs" / f"acsdt5y{s.ACS_YEAR}-b11001.dat")


def county_tags(omb):
    """CBSA, CSA, urban/rural tier and market group for each county in an OMB area (PRD Appendix A)."""
    t = omb.rename(columns={
        "CBSA Code": "cbsa_code", "CBSA Title": "cbsa_title", "CSA Code": "csa_code",
        "CSA Title": "csa_title", "Metropolitan/Micropolitan Statistical Area": "cbsa_type"})
    t["urban_rural_tier"] = t["cbsa_type"].map({"Metropolitan Statistical Area": "metro",
                                                "Micropolitan Statistical Area": "micro"})
    if t["urban_rural_tier"].isna().any():
        raise ValueError(f"Unexpected CBSA types: {t['cbsa_type'].unique()}")
    # Hybrid market groups: use the CSA where there is one, so Macon + Warner Robins rank as one
    # market. Not the Atlanta CSA, though: it would swallow Athens, Gainesville, Rome and LaGrange.
    atl_csa = t.loc[t["cbsa_code"] == s.ATLANTA_CBSA, "csa_code"].iloc[0]
    use_csa = t["csa_code"].notna() & (t["csa_code"] != atl_csa)
    t["market_group"] = t["csa_title"].where(use_csa, t["cbsa_title"])
    return t[["county_fips", "urban_rural_tier", "market_group", "cbsa_title", "csa_title"]]


def build_county_config():
    """Write config/ga_counties.csv: all Georgia counties with FOM, Atlanta MSA and metro-area tags."""
    counties = pd.read_csv(s.RAW / "census" / "st13_ga_cou2020.txt", sep="|", dtype=str)
    counties["county_fips"] = counties["STATEFP"] + counties["COUNTYFP"]
    counties["county_name"] = counties["COUNTYNAME"].str.replace(" County", "", regex=False)

    omb = pd.read_excel(s.RAW / "omb" / "list1_2023.xlsx", skiprows=2, dtype=str)
    omb = omb[omb["FIPS State Code"] == s.STATE_FIPS].copy()
    omb["county_fips"] = omb["FIPS State Code"] + omb["FIPS County Code"]
    atl_fips = set(omb.loc[omb["CBSA Code"] == s.ATLANTA_CBSA, "county_fips"])

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
    # Counties in no metro or micro area are rural and have no market group.
    out = out.merge(county_tags(omb), on="county_fips", how="left")
    out["urban_rural_tier"] = out["urban_rural_tier"].fillna("rural")
    out.to_csv(s.CONFIG / "ga_counties.csv", index=False)
    tiers = out["urban_rural_tier"].value_counts().to_dict()
    print(f"  config/ga_counties.csv: {len(out)} counties, "
          f"{out['fom_flag'].sum()} FOM, {out['atlanta_msa_flag'].sum()} in Atlanta MSA, tiers {tiers}")
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
        # DCCU's GA originations under one market filter at a time (Phase 2 reconciliation).
        fetch(f"{s.HMDA_API}/aggregations", hmda / "dccu_checks" / f"{y}_none.json",
              params={"years": y, "states": s.STATE_ABBR, "leis": s.DCCU_LEI, "actions_taken": "1"})
        for param, (_, values) in s.API_CHECK_FILTERS.items():
            fetch(f"{s.HMDA_API}/aggregations", hmda / "dccu_checks" / f"{y}_{param}.json",
                  params={"years": y, "states": s.STATE_ABBR, "leis": s.DCCU_LEI,
                          "actions_taken": "1", param: ",".join(values)})

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
