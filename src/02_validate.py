"""Stage 2: validate the raw downloads. Nothing is dropped; every result is logged.

Writes one CSV per check to data/processed/phase1_checks/ and replaces the
Phase 1 section of DATA_QUALITY.md with a summary.

Run from the repo root:  python src/02_validate.py
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as s  # noqa: E402
from src.common import dccu_branches, md_table, read_hmda, write_data_quality  # noqa: E402

OUT = s.PROCESSED / "phase1_checks"
HMDA = s.RAW / "hmda"
ACTIONS = {1: "originated", 2: "approved_not_accepted", 3: "denied", 4: "withdrawn",
           5: "incomplete", 6: "purchased", 7: "preapproval_denied", 8: "preapproval_approved_not_accepted"}


def scan_county_files(counties):
    """One pass over every year x county file, collecting what checks 1, 4 and 5 need."""
    counts, tracts, missing_tract, exempt = [], [], [], []
    for y in s.YEARS:
        for c in counties:
            df = read_hmda(HMDA / str(y) / f"{c}.csv")
            # Check 1 input: rows per action_taken, compared with the API's own counts later.
            got = df["action_taken"].value_counts()
            agg = json.loads((HMDA / str(y) / f"agg_{c}.json").read_text())["aggregations"]
            api = {int(a["actions_taken"]): a["count"] for a in agg}
            for a in ACTIONS:
                counts.append({"year": y, "county_fips": c, "action_taken": a,
                               "rows_downloaded": int(got.get(str(a), 0)),
                               "rows_api": api.get(a, 0)})
            # Check 4 inputs: which tracts appear, and rows with no usable tract.
            bad = df["census_tract"].isin(["", "NA"])
            tracts.append(df.loc[~bad, ["census_tract"]].drop_duplicates().assign(year=y))
            if bad.any():
                missing_tract.append(df.loc[bad].groupby("lei").size()
                                     .rename("rows").reset_index().assign(year=y, county_fips=c))
            # Check 5 input: "Exempt" values by lender and field (partially exempt lenders).
            is_ex = df.eq("Exempt")
            if is_ex.any().any():
                ex = is_ex.groupby(df["lei"]).sum()
                ex = ex.loc[:, ex.sum() > 0].stack().rename("rows").reset_index()
                ex.columns = ["lei", "field", "rows"]
                exempt.append(ex[ex["rows"] > 0].assign(year=y))
    counts = pd.DataFrame(counts)
    counts["diff"] = counts["rows_downloaded"] - counts["rows_api"]
    tracts = pd.concat(tracts).drop_duplicates()
    missing = pd.concat(missing_tract) if missing_tract else pd.DataFrame(
        columns=["lei", "rows", "year", "county_fips"])
    exempt = (pd.concat(exempt).groupby(["year", "lei", "field"], as_index=False)["rows"].sum()
              if exempt else pd.DataFrame(columns=["year", "lei", "field", "rows"]))
    return counts, tracts, missing, exempt


def load_filers():
    rows = []
    for y in s.YEARS:
        inst = json.loads((HMDA / f"filers_{y}.json").read_text())["institutions"]
        rows += [{"year": y, "lei": i["lei"], "name": i["name"], "filer_count": i["count"]}
                 for i in inst]
    return pd.DataFrame(rows)


def check_dccu(filers, fom_fips):
    """Checks 2 and 3: DCCU present every year; nationwide records reconcile to the filers count."""
    rows = []
    for y in s.YEARS:
        f = filers[(filers["year"] == y) & (filers["lei"] == s.DCCU_LEI)]
        df = read_hmda(HMDA / f"dccu_{y}.csv")
        county = df["county_code"]
        rows.append({
            "year": y,
            "in_filers_list": len(f) == 1,
            "filers_name": f["name"].iloc[0] if len(f) else None,
            # The filers list was requested for GA, so its count is DCCU's GA records only.
            "filers_count":int(f["filer_count"].iloc[0]) if len(f) else None,
            "records_downloaded": len(df),
            "records_in_ga": int((df["state_code"] == s.STATE_ABBR).sum()),
            "records_in_fom": int(county.isin(fom_fips).sum()),
            "ga_records_no_county": int(((df["state_code"] == s.STATE_ABBR)
                                         & county.isin(["", "NA"])).sum()),
            "originations": int((df["action_taken"] == "1").sum()),
            "originations_in_fom": int(((df["action_taken"] == "1") & county.isin(fom_fips)).sum()),
        })
    out = pd.DataFrame(rows)
    out["reconciles"] = out["filers_count"] == out["records_in_ga"]
    return out


def check_name_changes(filers):
    """Check 6: LEIs whose reported name differs across years."""
    names = filers.groupby("lei")["name"].nunique()
    changed = filers[filers["lei"].isin(names[names > 1].index)].copy()
    # Many "changes" are only case or punctuation ("Eclipse Bank" vs "ECLIPSE BANK, INC.").
    changed["normalized"] = (changed["name"].str.upper()
                             .str.replace(r"[^A-Z0-9 ]", "", regex=True)
                             .str.replace(r"\b(INC|LLC|CORP|CORPORATION|CO|THE)\b", "", regex=True)
                             .str.split().str.join(" "))
    wording = changed.groupby("lei")["normalized"].nunique() > 1
    out = changed.pivot_table(index="lei", columns="year", values="name", aggfunc="first").reset_index()
    out["wording_changed"] = out["lei"].map(wording)
    return out


def load_acs():
    path = s.RAW / "acs" / f"acsdt5y{s.ACS_YEAR}-b11001.dat"
    acs = pd.read_csv(path, sep="|", dtype=str)
    acs = acs[acs["GEO_ID"].str.startswith(f"1400000US{s.STATE_FIPS}")].copy()  # GA tracts only
    acs["tract"] = acs["GEO_ID"].str[-11:]
    acs["households"] = pd.to_numeric(acs["B11001_E001"])
    acs["households_moe"] = pd.to_numeric(acs["B11001_M001"])
    return acs[["tract", "households", "households_moe"]]


def check_acs(acs):
    """Check 7: flag unreliable household counts (coefficient of variation > 30%)."""
    acs = acs.copy()
    # ACS margins of error are 90% confidence; MOE / 1.645 = standard error.
    acs["cv"] = (acs["households_moe"] / 1.645) / acs["households"].where(acs["households"] > 0)
    acs["flag"] = "ok"
    acs.loc[acs["cv"] > 0.30, "flag"] = "high_moe"
    acs.loc[acs["households"] == 0, "flag"] = "zero_households"
    return acs


def check_tract_coverage(hmda_tracts, acs):
    """Check 4b: tracts in HMDA vs TIGER vs ACS, mismatches listed each way."""
    tiger = gpd.read_file(f"zip://{s.RAW / 'tiger' / 'tl_2024_13_tract.zip'}", ignore_geometry=True)
    sets = {
        "hmda": set(hmda_tracts["census_tract"]),
        "tiger": set(tiger["GEOID"]),
        "acs": set(acs["tract"]),
    }
    rows = []
    for a in sets:
        for b in sets:
            if a != b:
                rows += [{"tract": t, "in": a, "missing_from": b} for t in sorted(sets[a] - sets[b])]
    sizes = {k: len(v) for k, v in sets.items()}
    return pd.DataFrame(rows, columns=["tract", "in", "missing_from"]), sizes


def check_ncua():
    """Check 8: find DCCU's branches in the latest NCUA call report."""
    zips = sorted((s.RAW / "ncua").glob("call-report-data-*.zip"))
    charter, mine = dccu_branches(zips[-1])
    lat_cols = [c for c in mine.columns if "lat" in c.lower() or "long" in c.lower()]
    return zips[-1].name, charter, mine, lat_cols



def main():
    OUT.mkdir(parents=True, exist_ok=True)
    counties = pd.read_csv(s.CONFIG / "ga_counties.csv", dtype=str)
    fom_fips = set(counties.loc[counties["fom_flag"] == "1", "county_fips"])

    print("Scanning HMDA county files (checks 1, 4, 5)...")
    counts, hmda_tracts, missing, exempt = scan_county_files(counties["county_fips"].tolist())
    filers = load_filers()
    names = filers.drop_duplicates("lei", keep="last").set_index("lei")["name"]

    print("DCCU, lender names, ACS, tracts, NCUA (checks 2, 3, 6, 7, 4b, 8)...")
    dccu = check_dccu(filers, fom_fips)
    changes = check_name_changes(filers)
    acs = check_acs(load_acs())
    coverage, sizes = check_tract_coverage(hmda_tracts, acs)
    ncua_file, charter, branches, latlong_cols = check_ncua()

    counts.to_csv(OUT / "1_row_counts.csv", index=False)
    dccu.to_csv(OUT / "2_3_dccu_reconciliation.csv", index=False)
    missing.assign(lender=missing["lei"].map(names)).to_csv(OUT / "4_missing_tracts.csv", index=False)
    coverage.to_csv(OUT / "4_tract_coverage.csv", index=False)
    exempt.assign(lender=exempt["lei"].map(names)).to_csv(OUT / "5_exempt_fields.csv", index=False)
    changes.to_csv(OUT / "6_lender_name_changes.csv", index=False)
    acs.to_csv(OUT / "7_acs_households.csv", index=False)
    branches.to_csv(OUT / "8_dccu_branches.csv", index=False)

    # Summaries for DATA_QUALITY.md
    by_year = counts.groupby("year")[["rows_downloaded", "rows_api"]].sum().reset_index()
    by_year["diff"] = by_year["rows_downloaded"] - by_year["rows_api"]
    by_year["ga_total_api"] = [
        sum(a["count"] for a in json.loads((HMDA / f"agg_{y}_state.json").read_text())["aggregations"])
        for y in by_year["year"]]
    by_year["no_county_rows"] = by_year["ga_total_api"] - by_year["rows_api"]
    by_year["no_county_pct"] = (100 * by_year["no_county_rows"] / by_year["ga_total_api"]).round(2)
    off = counts[counts["diff"] != 0]
    miss_by_year = (missing.groupby("year")["rows"].sum().reset_index()
                    if len(missing) else pd.DataFrame(columns=["year", "rows"]))
    top_exempt = (exempt.groupby("lei", as_index=False)["rows"].sum()
                  .assign(lender=lambda d: d["lei"].map(names))
                  .sort_values("rows", ascending=False).head(10))
    flags = acs["flag"].value_counts().rename_axis("flag").reset_index(name="tracts")
    cov_summary = (coverage.groupby(["in", "missing_from"]).size().reset_index(name="tracts")
                   if len(coverage) else coverage)

    sections = [
        "### 1. Completeness: rows downloaded vs. HMDA API counts\n"
        + md_table(by_year)
        + f"\n\nYear × county × action cells that don't match: **{len(off)}** "
          "(details in `data/processed/phase1_checks/1_row_counts.csv`).\n\n"
          "`no_county_rows` are Georgia records with no county code. Downloads are by county, "
          "so these rows are not in the raw data. They can't be placed in a tract either, so "
          "tract and county metrics are unaffected; statewide totals are understated by "
          "`no_county_pct`. DCCU's own no-county records are in the table below.",
        "### 2–3. DCCU presence and reconciliation\n"
        "`filers_count` is DCCU's Georgia HMDA record count from the filers API (all action "
        "types). It should equal `records_in_ga` from the nationwide LEI download. Records "
        "outside GA are loans on out-of-state properties.\n\n"
        + md_table(dccu),
        "### 4. Census tracts\n"
        f"Rows with missing/NA tract, by year (all lenders):\n\n{md_table(miss_by_year)}\n\n"
        f"Tract sets: HMDA {sizes['hmda']:,}, TIGER {sizes['tiger']:,}, ACS {sizes['acs']:,}. "
        f"Mismatches:\n\n{md_table(cov_summary)}\n\n"
        "Tracts present in TIGER/ACS with no HMDA records are usually water, airport, park or "
        "institutional tracts (codes 98xxxx/99xxxx, near-zero households); list in "
        "`4_tract_coverage.csv`. Rows with no tract can't be mapped and are excluded from "
        "tract metrics (Phase 2 logs the count).",
        "### 5. `Exempt` fields (partially exempt lenders)\n"
        f"{exempt['lei'].nunique()} lenders report `Exempt` in some fields. Top 10 by number of "
        "exempt values (rows × fields), all years; detail by field in `5_exempt_fields.csv`. "
        "Exempt fields are mostly pricing and underwriting details; v1 share metrics use only "
        "fields that can't be exempted.\n\n"
        + md_table(top_exempt.rename(columns={"rows": "exempt_values"})),
        f"### 6. Lender name changes across years\n{len(changes)} LEIs reported more than one "
        f"name; {int(changes['wording_changed'].sum())} differ in wording (renames, rebrands), "
        "the rest only in case or punctuation (`6_lender_name_changes.csv`). The analysis keys "
        "on LEI and displays the latest name, so renames don't split a lender. Mergers that "
        "retire an LEI are not detected here; review the top competitors by hand in Phase 3.",
        "### 7. ACS household reliability\n"
        f"ACS {s.ACS_YEAR - 4}–{s.ACS_YEAR} 5-year, table B11001. CV = (MOE / 1.645) / estimate; "
        "flag when CV > 30%.\n\n" + md_table(flags),
        f"### 8. DCCU branches (NCUA `{ncua_file}`)\n"
        f"Charter: {charter}. Branch records: {len(branches)}. "
        + (f"Lat/long columns: {', '.join(latlong_cols)}."
           if latlong_cols else "**No lat/long columns: branches need geocoding in Phase 4.**"),
        "### Known limitations\n"
        "- The FOM list is DCCU's current 20 counties, applied to every year. DCCU added counties "
        "over time, so early-year FOM share may be understated for recently added counties.",
    ]
    write_data_quality("phase1", "Phase 1: download and validate", sections)
    print(by_year.to_string(index=False))
    print(dccu.to_string(index=False))
    print(f"Cells off: {len(off)}; tract sets {sizes}; branches {len(branches)}; lat/long {latlong_cols}")


if __name__ == "__main__":
    main()
