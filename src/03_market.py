"""Stage 3: build the mortgage market dataset (PRD Appendix A, "Market definition").

For each year:
  1. Combine the 159 county CSVs into data/processed/hmda_ga_{year}.parquet (all rows, all columns).
  2. Apply the market filters from config/settings.py to every lender, logging rows removed at each step.
  3. Write data/processed/market_{year}.parquet with added columns:
     county_fips, purpose_group (purchase / refinance), has_tract.
The market files are shared by every lender and keep all loan types: lender stages apply their
own product filter (loan types) and footprint flag.
Also writes data/processed/lenders.csv (LEI -> latest name) and the Phase 2 section of
DATA_QUALITY.md. For each configured lender it writes data/processed/<key>/phase2_checks/
(its filter waterfall with its product filter, its originations by loan type, reconciliation
with the HMDA API, and market size) and the Phase 2 section of its own data-quality log.

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
from config.lender import configured  # noqa: E402
from src.common import fetch, lender_log_heading, md_table, write_data_quality  # noqa: E402

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


def apply_filters(df, year, lenders):
    """Apply each market filter in order. Like a chain of SQL WHERE clauses, with a COUNT(*) after each.

    Returns the market waterfall and, per lender, a waterfall of the market as that lender
    defines it (all lenders' rows, `_all`) and the lender's own rows (`_lender`). A lender's
    waterfall adds its product filter (loan types) right after s.PRODUCT_FILTER_AFTER.
    """
    waterfall, lender_steps, exempt_kept = [], [], []
    product_on = False

    def log(step, market=True):
        orig = df["action_taken"] == "1"
        if market:
            waterfall.append({"year": year, "step": step, "rows_all": len(df),
                              "originations_all": int(orig.sum())})
        for lender in lenders:
            scope = (df["loan_type"].isin(lender.loan_types) if product_on
                     else pd.Series(True, index=df.index))
            mine = scope & (df["lei"] == lender.lei)
            lender_steps.append({"lender": lender.key, "year": year,
                                 "step": step or lender.product_step,
                                 "rows_all": int(scope.sum()),
                                 "originations_all": int((orig & scope).sum()),
                                 "rows_lender": int(mine.sum()),
                                 "originations_lender": int((orig & mine).sum())})

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
        if name == s.PRODUCT_FILTER_AFTER:
            product_on = True
            log(None, market=False)  # each lender's product step, named from its loan types
    return df, waterfall, lender_steps, exempt_kept


def add_columns(df):
    df = df.copy()
    df["county_fips"] = df["county_code"]
    df["purpose_group"] = df["loan_purpose"].map({"1": "purchase", "31": "refinance", "32": "refinance"})
    df["has_tract"] = (~df["census_tract"].isin(["", "NA"])).astype("int8")
    return df


def reconcile_lender(lender, year, ga):
    """Compare a lender's GA originations under one filter at a time with the HMDA API's own count."""
    d = ga[(ga["lei"] == lender.lei) & (ga["action_taken"] == "1")]
    checks = {"none": (None, None)} | lender.api_check_filters
    rows = []
    for param, (field, values) in checks.items():
        path = lender.raw / "api_checks" / f"{year}_{param}.json"
        resp = json.loads(path.read_text())
        # A cached answer fetched under different values (e.g. before a config change) is stale.
        got = resp["parameters"].get(param)
        if field is not None and got is not None and got != ",".join(values):
            raise ValueError(f"{path} was fetched with {param}={got}, but the config says "
                             f"{','.join(values)}. Delete it and rerun 01_download.py.")
        # The API silently ignores filters it doesn't support; make sure this one was applied.
        applied = param == "none" or got is not None
        api = sum(a["count"] for a in resp["aggregations"])
        ours = len(d) if field is None else int(d[field].isin(values).sum())
        rows.append({"year": year, "filter": param, "api_applied_filter": applied,
                     "lender_api": api, "lender_ours": ours, "match": applied and api == ours})
    return rows


def market_size(orig, year, lender=None):
    """Market originations, statewide; with a lender, the market as it defines it (its loan
    types), statewide and in its footprint, with the lender's own originations."""
    if lender:
        orig = orig[orig["loan_type"].isin(lender.loan_types)]
    scopes = [("statewide", orig)]
    if lender:
        scopes.append(("footprint", orig[orig["county_fips"].isin(lender.footprint)]))
    rows = []
    for scope, sub in scopes:
        row = {"year": year, "scope": scope,
               "market_originations": len(sub),
               "market_purchase": int((sub["purpose_group"] == "purchase").sum()),
               "market_refinance": int((sub["purpose_group"] == "refinance").sum()),
               "market_no_tract": int((sub["has_tract"] == 0).sum()),
               "lenders": sub["lei"].nunique()}
        if lender:
            mine = sub[sub["lei"] == lender.lei]
            row |= {"lender_originations": len(mine),
                    "lender_purchase": int((mine["purpose_group"] == "purchase").sum()),
                    "lender_refinance": int((mine["purpose_group"] == "refinance").sum()),
                    "lender_no_tract": int((mine["has_tract"] == 0).sum())}
        rows.append(row)
    return rows


def by_loan_type(orig, year):
    """Originations by loan type (SQL: GROUP BY loan_type), after every market filter."""
    g = orig.groupby("loan_type").agg(
        originations=("lei", "size"), purchase=("purpose_group", lambda x: int((x == "purchase").sum())),
        refinance=("purpose_group", lambda x: int((x == "refinance").sum())), lenders=("lei", "nunique"))
    g = g.reindex(list(s.LOAN_TYPES), fill_value=0).rename_axis("loan_type").reset_index()
    g.insert(0, "year", year)
    g.insert(2, "loan_type_name", g["loan_type"].map(s.LOAN_TYPES))
    return g.to_dict("records")


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


def lender_report(lender, steps, recon, sizes, product):
    """Write one lender's Phase 2 checks to its folder and its data-quality log."""
    out = lender.processed / "phase2_checks"
    out.mkdir(parents=True, exist_ok=True)
    steps = steps.drop(columns="lender")
    steps.to_csv(out / "filter_waterfall.csv", index=False)
    recon.to_csv(out / "api_reconciliation.csv", index=False)
    sizes.to_csv(out / "market_size.csv", index=False)
    product["kept"] = product["loan_type"].isin(lender.loan_types)
    product.to_csv(out / "product_filter.csv", index=False)

    latest = s.YEARS[-1]
    wf = steps[steps["year"] == latest].drop(columns="year")
    wf["originations_removed"] = (-wf["originations_lender"].diff()).fillna(0).astype(int)
    pf = product.groupby("year").apply(lambda g: pd.Series({
        "lender_originations": g["originations"].sum(),
        "kept": g.loc[g["kept"], "originations"].sum()}), include_groups=False).reset_index()
    pf["kept_share"] = (pf["kept"] / pf["lender_originations"]).round(4)
    by_type = product.pivot(index="year", columns="loan_type_name", values="originations")
    sections = [
        f"### Product filter: {lender.product_label} (`loan_types` {list(lender.loan_types)})\n"
        f"{lender.label}'s market is every lender's {lender.product_label} loans, so the filter "
        "applies to competitors too. Below: "
        f"{lender.label}'s own GA originations by loan type, after the other market filters "
        f"(`phase2_checks/product_filter.csv`). A large share left out would mean the config "
        f"misses part of {lender.label}'s lending.\n\n"
        + md_table(by_type[list(s.LOAN_TYPES.values())].reset_index().merge(pf, on="year")),
        f"### {lender.label} through the market filters ({latest}; all years in "
        "`phase2_checks/filter_waterfall.csv`)\nThe same filters apply to every lender. "
        f"`{lender.product_step}` is {lender.label}'s product filter; `_all` columns count the "
        f"market as {lender.label} defines it, `_lender` columns {lender.label}'s own rows. Each "
        "row is the count after every filter above it.\n\n" + md_table(wf),
        f"### {lender.label} reconciliation with the HMDA API\n{lender.label}'s GA originations "
        "with one market filter at a time, our data vs. the API's own count (the API allows at most "
        "two filters, so the full definition can't be checked in one query). Occupancy can't be "
        f"checked: the API ignores that filter.\n\nMismatches: **{int((~recon['match']).sum())}** "
        f"of {len(recon)}.\n\n" + md_table(recon[recon["year"] == latest].drop(columns="year")),
        f"### Market size and {lender.label} ({lender.product_label} originations, after all filters)\n"
        + md_table(sizes),
    ]
    write_data_quality("phase2_lender", "Phase 2: lender within the market definition", sections,
                       path=lender.data_quality, heading=lender_log_heading(lender))
    print(f"{lender.key}: reconciliation mismatches {int((~recon['match']).sum())} of {len(recon)}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    counties = pd.read_csv(s.CONFIG / "ga_counties.csv", dtype=str)
    lenders_cfg = configured()

    waterfall, exempt, sizes, loan_types, files = [], [], [], [], []
    steps, recon, lender_sizes = [], {lc.key: [] for lc in lenders_cfg}, {lc.key: [] for lc in lenders_cfg}
    product = {lc.key: [] for lc in lenders_cfg}
    market_leis = {}  # lei -> latest year with market rows
    for y in s.YEARS:
        print(f"{y}: combining county files...")
        ga = combine_year(y, counties["county_fips"].tolist())
        for lc in lenders_cfg:
            recon[lc.key] += reconcile_lender(lc, y, ga)
        market, w, st, e = apply_filters(ga, y, lenders_cfg)
        waterfall += w
        steps += st
        exempt += e
        market = add_columns(market)
        path = s.PROCESSED / f"market_{y}.parquet"
        market.to_parquet(path, index=False)
        files.append({"file": path.name, "rows": len(market), "mb": round(path.stat().st_size / 1e6, 1)})
        market_leis |= dict.fromkeys(market["lei"].unique(), y)

        orig = market[market["action_taken"] == "1"]
        sizes += market_size(orig, y)
        loan_types += by_loan_type(orig, y)
        for lc in lenders_cfg:
            lender_sizes[lc.key] += market_size(orig, y, lc)
            product[lc.key] += by_loan_type(orig[orig["lei"] == lc.lei], y)
        print(f"  market rows {len(market):,}, originations {len(orig):,}")

    lenders = build_lenders(market_leis)
    waterfall, exempt, sizes = pd.DataFrame(waterfall), pd.DataFrame(exempt), pd.DataFrame(sizes)
    loan_types, files = pd.DataFrame(loan_types), pd.DataFrame(files)
    waterfall.to_csv(OUT / "filter_waterfall.csv", index=False)
    exempt.to_csv(OUT / "exempt_flags_kept.csv", index=False)
    sizes.drop(columns="scope").to_csv(OUT / "market_size.csv", index=False)
    loan_types.to_csv(OUT / "market_by_loan_type.csv", index=False)

    # Summaries for DATA_QUALITY.md
    latest = s.YEARS[-1]
    wf = waterfall[waterfall["year"] == latest].drop(columns="year")
    wf["originations_removed"] = (-wf["originations_all"].diff()).fillna(0).astype(int)
    ex = exempt.groupby(["filter", "field"], as_index=False)["rows_kept_with_exempt"].sum()
    lt = loan_types.pivot(index="year", columns="loan_type_name", values="originations")
    lt = lt[list(s.LOAN_TYPES.values())].assign(all=lt.sum(axis=1)).reset_index()
    sections = [
        f"### Filter waterfall ({latest}; all years in `phase2_checks/filter_waterfall.csv`)\n"
        "Filters run in order, so each row's count is after every filter above it. "
        "Rows with no county code (Phase 1, check 1) never enter, so the start is slightly "
        "below the statewide total. Loan type is not a market filter: the market files keep all "
        "loan types, and each lender's product filter (`loan_types` in its `lender.toml`) is "
        "applied in its own stages. Each lender's waterfall (with its product filter), "
        "product check and reconciliation with the HMDA API are in "
        "`outputs/<lender>/DATA_QUALITY.md`.\n\n" + md_table(wf),
        "### Market by loan type (originations, after all filters, statewide)\n"
        "`phase2_checks/market_by_loan_type.csv` also splits purchase and refinance.\n\n"
        + md_table(lt) + "\n\nMarket files (all loan types, all actions):\n\n" + md_table(files),
        "### Exempt flags kept\nRows kept although the lender reported the field as exempt "
        "(`1111`), all years. Exempt lenders are small and rarely make these products.\n\n"
        + md_table(ex),
        "### Market size (originations, after all filters, statewide, all loan types)\n"
        + md_table(sizes.drop(columns="scope")),
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

    steps = pd.DataFrame(steps)
    for lc in lenders_cfg:
        lender_report(lc, steps[steps["lender"] == lc.key], pd.DataFrame(recon[lc.key]),
                      pd.DataFrame(lender_sizes[lc.key]), pd.DataFrame(product[lc.key]))


if __name__ == "__main__":
    main()
