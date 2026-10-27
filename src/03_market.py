"""Stage 3: build the mortgage market dataset (PRD Appendix A, "Market definition").

For each year:
  1. Combine the 159 county CSVs into data/processed/hmda_ga_{year}.parquet (all rows, all columns).
  2. Apply the market filters from config/settings.py to every lender, logging rows removed at each step.
  3. Write data/processed/market_{year}.parquet with added columns:
     county_fips, fom_flag, purpose_group (purchase / refinance), has_tract.
Also writes data/processed/lenders.csv (LEI -> latest name), reconciles DCCU against the
HMDA API, and replaces the Phase 2 section of DATA_QUALITY.md.

Run from the repo root:  python src/03_market.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.csv as pcsv
import pyarrow.parquet as pq
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as s  # noqa: E402
from src.common import fetch, md_table, write_data_quality  # noqa: E402

HMDA = s.RAW / "hmda"
OUT = s.PROCESSED / "phase2_checks"


def combine_year(year, counties):
    """Stack the county CSVs for one year into a single all-text parquet file."""
    tables = []
    for c in counties:
        path = HMDA / str(year) / f"{c}.csv"
        # Force every column to text, like Phase 1 (keeps leading zeros, "NA", "Exempt").
        tables.append(pcsv.read_csv(path, convert_options=pcsv.ConvertOptions(
            column_types=_text_schema(path), strings_can_be_null=False)))
    table = pa.concat_tables(tables)
    pq.write_table(table, s.PROCESSED / f"hmda_ga_{year}.parquet")
    return table.to_pandas()


def _text_schema(path):
    with open(path, encoding="utf-8") as f:
        names = f.readline().strip().split(",")
    return {n.strip('"'): pa.string() for n in names}


def apply_filters(df, year):
    """Apply each market filter in order. Like a chain of SQL WHERE clauses, with a COUNT(*) after each."""
    waterfall, exempt_kept = [], []

    def log(step):
        orig = df["action_taken"] == "1"
        dccu = df["lei"] == s.DCCU_LEI
        waterfall.append({"year": year, "step": step, "rows_all": len(df),
                          "originations_all": int(orig.sum()), "rows_dccu": int(dccu.sum()),
                          "originations_dccu": int((orig & dccu).sum())})

    log("start: all GA rows with a county")
    for name, field, op, values in s.MARKET_FILTERS:
        if op == "in":
            df = df[df[field].isin(values)]
        else:
            df = df[~df[field].isin(values)]
            # Exempt lenders don't say whether a loan is a HELOC/reverse/business; we keep them.
            n_ex = int((df[field] == s.EXEMPT_CODE).sum())
            if field != "action_taken":
                exempt_kept.append({"year": year, "filter": name, "field": field,
                                    "rows_kept_with_exempt": n_ex,
                                    "lenders": df.loc[df[field] == s.EXEMPT_CODE, "lei"].nunique()})
        log(name)
    return df, waterfall, exempt_kept


def add_columns(df, fom_fips):
    df = df.copy()
    df["county_fips"] = df["county_code"]
    df["fom_flag"] = df["county_fips"].isin(fom_fips).astype("int8")
    df["purpose_group"] = df["loan_purpose"].map({"1": "purchase", "31": "refinance", "32": "refinance"})
    df["has_tract"] = (~df["census_tract"].isin(["", "NA"])).astype("int8")
    return df


def reconcile_dccu(year, ga):
    """Compare DCCU's GA originations under one filter at a time with the HMDA API's own count."""
    d = ga[(ga["lei"] == s.DCCU_LEI) & (ga["action_taken"] == "1")]
    checks = {"none": (None, None)} | s.API_CHECK_FILTERS
    rows = []
    for param, (field, values) in checks.items():
        resp = json.loads((HMDA / "dccu_checks" / f"{year}_{param}.json").read_text())
        # The API silently ignores filters it doesn't support; make sure this one was applied.
        applied = param == "none" or param in resp["parameters"]
        api = sum(a["count"] for a in resp["aggregations"])
        ours = len(d) if field is None else int(d[field].isin(values).sum())
        rows.append({"year": year, "filter": param, "api_applied_filter": applied,
                     "dccu_api": api, "dccu_ours": ours, "match": applied and api == ours})
    return rows


def build_lenders(market_leis):
    """LEI -> latest name in the HMDA filers lists. market_leis: {lei: latest market year}.

    Market LEIs missing from every filers list are named from GLEIF (cached per LEI).
    """
    rows = []
    for y in s.YEARS:
        inst = json.loads((HMDA / f"filers_{y}.json").read_text())["institutions"]
        rows += [{"lei": i["lei"], "name": i["name"], "year": y} for i in inst]
    lenders = (pd.DataFrame(rows).sort_values("year")
               .groupby("lei", as_index=False).last()
               .rename(columns={"year": "latest_year"}))
    lenders["name_source"] = "hmda_filers"

    gleif = []
    for lei in sorted(set(market_leis) - set(lenders["lei"])):
        path = s.RAW / "gleif" / f"{lei}.json"
        try:
            fetch(f"{s.GLEIF_API}/{lei}", path)
        except requests.HTTPError as e:
            if e.response.status_code != 404:
                raise
            path.write_text('{"data": null}')  # cache "not in GLEIF" too
        data = json.loads(path.read_text())["data"]
        name = data["attributes"]["entity"]["legalName"]["name"] if data else None
        gleif.append({"lei": lei, "name": name, "latest_year": market_leis[lei],
                      "name_source": "gleif" if data else "not_found"})
    lenders = pd.concat([lenders, pd.DataFrame(gleif)], ignore_index=True)
    lenders.to_csv(s.PROCESSED / "lenders.csv", index=False)
    return lenders


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    counties = pd.read_csv(s.CONFIG / "ga_counties.csv", dtype=str)
    fom_fips = set(counties.loc[counties["fom_flag"] == "1", "county_fips"])

    waterfall, exempt, recon, sizes = [], [], [], []
    market_leis = {}  # lei -> latest year with market rows
    for y in s.YEARS:
        print(f"{y}: combining county files...")
        ga = combine_year(y, counties["county_fips"].tolist())
        recon += reconcile_dccu(y, ga)
        market, w, e = apply_filters(ga, y)
        waterfall += w
        exempt += e
        market = add_columns(market, fom_fips)
        market.to_parquet(s.PROCESSED / f"market_{y}.parquet", index=False)
        market_leis |= dict.fromkeys(market["lei"].unique(), y)

        orig = market[market["action_taken"] == "1"]
        for scope, sub in [("statewide", orig), ("fom", orig[orig["fom_flag"] == 1])]:
            dccu = sub[sub["lei"] == s.DCCU_LEI]
            sizes.append({
                "year": y, "scope": scope,
                "market_originations": len(sub),
                "market_purchase": int((sub["purpose_group"] == "purchase").sum()),
                "market_refinance": int((sub["purpose_group"] == "refinance").sum()),
                "market_no_tract": int((sub["has_tract"] == 0).sum()),
                "lenders": sub["lei"].nunique(),
                "dccu_originations": len(dccu),
                "dccu_purchase": int((dccu["purpose_group"] == "purchase").sum()),
                "dccu_refinance": int((dccu["purpose_group"] == "refinance").sum()),
                "dccu_no_tract": int((dccu["has_tract"] == 0).sum()),
            })
        print(f"  market rows {len(market):,}, originations {len(orig):,}")

    lenders = build_lenders(market_leis)
    waterfall, exempt = pd.DataFrame(waterfall), pd.DataFrame(exempt)
    recon, sizes = pd.DataFrame(recon), pd.DataFrame(sizes)
    waterfall.to_csv(OUT / "filter_waterfall.csv", index=False)
    exempt.to_csv(OUT / "exempt_flags_kept.csv", index=False)
    recon.to_csv(OUT / "dccu_api_reconciliation.csv", index=False)
    sizes.to_csv(OUT / "market_size.csv", index=False)

    # Summaries for DATA_QUALITY.md
    latest = s.YEARS[-1]
    wf = waterfall[waterfall["year"] == latest].drop(columns="year")
    wf["originations_removed"] = (-wf["originations_all"].diff()).fillna(0).astype(int)
    ex = exempt.groupby(["filter", "field"], as_index=False)["rows_kept_with_exempt"].sum()
    sections = [
        f"### Filter waterfall ({latest}; all years in `phase2_checks/filter_waterfall.csv`)\n"
        "Filters run in order, so each row's count is after every filter above it. "
        "Rows with no county code (Phase 1, check 1) never enter, so the start is slightly "
        "below the statewide total.\n\n" + md_table(wf),
        "### Exempt flags kept\nRows kept although the lender reported the field as exempt "
        "(`1111`), all years. Exempt lenders are small and rarely make these products.\n\n"
        + md_table(ex),
        "### DCCU reconciliation with the HMDA API\nDCCU's GA originations with one market "
        "filter at a time, our data vs. the API's own count (the API allows at most two filters, "
        "so the full definition can't be checked in one query). Occupancy can't be checked: the "
        f"API ignores that filter.\n\nMismatches: **{int((~recon['match']).sum())}** of {len(recon)}.\n\n"
        + md_table(recon[recon["year"] == latest].drop(columns="year")),
        "### Market size (originations, after all filters)\n" + md_table(sizes),
        "### Rows without a census tract\n`market_no_tract` originations stay in the market "
        "data (`has_tract = 0`) and count toward county and statewide totals, but can't be "
        "placed on the map or in tract metrics.",
        f"### Lenders\n`data/processed/lenders.csv`: {len(lenders):,} LEIs with their latest "
        "reported name. Names come from the HMDA filers lists; market LEIs missing from every "
        "list are named from GLEIF (the global LEI registry).\n\n"
        + md_table(lenders["name_source"].value_counts().rename_axis("name_source")
                   .reset_index(name="leis")),
    ]
    write_data_quality("phase2", "Phase 2: market definition", sections)
    print(sizes.to_string(index=False))
    print(f"Reconciliation mismatches: {int((~recon['match']).sum())} of {len(recon)}")


if __name__ == "__main__":
    main()
