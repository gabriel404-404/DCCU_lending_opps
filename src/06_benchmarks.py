"""Stage 6: benchmark ladder and market-structure evidence (PRD Appendix A, "Benchmark ladder").

Runs for one lender (config/lender.py). Reads its Phase 3 outputs and the shared market file
for the scoring year, and writes, in data/processed/<key>/:
  benchmark_ladder.csv         base / stretch / ceiling: unit, rule, share, depth
  depth_ladder_by_county.csv   depth at each rung, per footprint county
  market_structure.csv         the top quarter (counties, or tracts for a small footprint) vs. the rest
  peer_comparison.csv          subject-lender share by loan size and tract competition
plus phase5_checks/ (the ladder by county and by tract, channel field) and the
"Phase 5: benchmarks" section of the lender's data-quality log.
Run from the repo root:  python src/06_benchmarks.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as s  # noqa: E402
from config.lender import LENDER as L  # noqa: E402
from src.common import lender_log_heading, lender_market, md_table, write_data_quality  # noqa: E402

OUT = L.processed / "phase5_checks"
TOP, REST = "top quarter", "rest of footprint"


def ladder_unit(counties):
    """The ladder's unit (PRD Appendix A): county, or tract when too few footprint counties qualify."""
    n = int((counties["market_all"] >= s.LADDER_MIN_MARKET).sum())
    return "county" if n >= s.LADDER_MIN_COUNTIES else "tract"


def qualifying_units(counties, tracts, unit):
    """Footprint counties or tracts with enough market originations to set a rung, strongest first."""
    if unit == "county":
        q = counties[counties["market_all"] >= s.LADDER_MIN_MARKET]
        return q.sort_values(["share_all", "market_all"], ascending=False)
    q = tracts[(tracts["footprint_flag"] == 1) & (tracts["market_all"] >= s.LADDER_MIN_TRACT_MARKET)]
    return q.sort_values(["share_all", "market_all", "census_tract"], ascending=[False, False, True])


def build_ladder(counties, tracts, unit):
    """Base, stretch and ceiling shares, and depth at each rung (tract level, like the PRD's depth).

    The reference group is the top quarter of qualifying footprint counties, or of qualifying
    footprint tracts when unit is "tract". Returns the ladder, depth by county, the top quarter
    as a tract mask over footprint tracts, and the qualifying and top-quarter units.
    """
    qualifying = qualifying_units(counties, tracts, unit)
    if qualifying.empty:
        raise ValueError(f"No footprint {unit} qualifies for the benchmark ladder")
    top = qualifying.head(int(np.ceil(s.LADDER_TOP_FRACTION * len(qualifying))))
    weakest = top.loc[top["share_all"].idxmin()]
    ft = tracts[tracts["footprint_flag"] == 1]
    if unit == "county":
        stretch_ref, ceiling_ref = weakest["county_name"], ", ".join(top["county_name"])
        in_top = ft["county_name"].isin(top["county_name"])
    else:
        stretch_ref = f"tract {weakest['census_tract']} ({weakest['county_name']})"
        ceiling_ref = f"{len(top)} tracts"
        in_top = ft["census_tract"].isin(top["census_tract"])
    rungs = [
        ("base", "footprint average", counties["lender_all"].sum() / counties["market_all"].sum(),
         "all footprint counties"),
        ("stretch", f"weakest {unit} in the top quarter", weakest["share_all"], stretch_ref),
        ("ceiling", "top quarter, pooled" if unit == "county" else "top quarter of tracts, pooled",
         top["lender_all"].sum() / top["market_all"].sum(), ceiling_ref),
    ]
    current = counties["lender_all"].sum()
    rows, by_county = [], counties[["county_fips", "county_name", "market_all", "lender_all",
                                    "share_all"]].copy()
    # in_top_quarter: the county itself is in the reference group (county unit only).
    by_county["in_top_quarter"] = by_county["county_name"].isin(top["county_name"]) & (unit == "county")
    by_county["top_quarter_tracts"] = by_county["county_name"].map(
        in_top.groupby(ft["county_name"]).sum()).fillna(0).astype(int)
    for rung, rule, share, reference in rungs:
        # Same form as opportunity_score: lift every tract below the rung up to it.
        gain = ft["market_all"] * (share - ft["share_all"].fillna(0)).clip(lower=0)
        rows.append({"rung": rung, "unit": unit, "rule": rule, "share": share, "reference": reference,
                     "depth": gain.sum(), "depth_outside_top_quarter": gain[~in_top].sum(),
                     "depth_vs_current_loans": gain.sum() / current})
        by_county[f"depth_{rung}"] = by_county["county_name"].map(gain.groupby(ft["county_name"]).sum())
    return (pd.DataFrame(rows), by_county.sort_values("depth_base", ascending=False),
            ft.loc[in_top, "census_tract"], qualifying, top)


def ladder_both_ways(counties, tracts, chosen):
    """Check: the ladder by county and by tract, so the tract fallback runs on every lender's data."""
    rows = []
    for unit in ["county", "tract"]:
        if qualifying_units(counties, tracts, unit).empty:
            rows.append({"unit": unit, "used": unit == chosen, "note": f"no qualifying {unit}"})
            continue
        ladder, _, _, qualifying, top = build_ladder(counties, tracts, unit)
        for r in ladder.itertuples():
            rows.append({"unit": unit, "used": unit == chosen, "rung": r.rung, "share": r.share,
                         "depth": r.depth, "reference": r.reference, "qualifying": len(qualifying),
                         "top_quarter": len(top),
                         "top_quarter_on_one_loan": int((top["lender_all"] == 1).sum()), "note": ""})
    return pd.DataFrame(rows)


def load_market(builders, top_tracts, top_counties, unit):
    """Scoring-year footprint originations, loan level, with group and subject-lender flags.

    Loans are grouped by county (county unit) or by tract (tract unit; loans with no tract
    can't be in a top-quarter tract and count as the rest)."""
    cols = ["lei", "county_fips", "census_tract", "action_taken", "purpose_group",
            "has_tract", "loan_amount", "income", "conforming_loan_limit", "submission_of_application"]
    m = lender_market(L, s.SCORING_YEAR, cols)
    o = m[(m["action_taken"] == "1") & m["county_fips"].isin(L.footprint)].copy()
    names = pd.read_csv(L.processed / "counties.csv", dtype=str).set_index("county_fips")["county_name"]
    o["county_name"] = o["county_fips"].map(names)
    in_top = (o["county_name"].isin(top_counties) if unit == "county"
              else o["census_tract"].isin(top_tracts) & (o["has_tract"] == 1))
    o["group"] = np.where(in_top, TOP, REST)
    o["subject"] = (o["lei"] == L.lei).astype(int)
    o["builder"] = o["lei"].isin(builders)
    o["amount"] = pd.to_numeric(o["loan_amount"], errors="coerce")
    o["income_k"] = pd.to_numeric(o["income"], errors="coerce")
    lenders_in_tract = o[o["has_tract"] == 1].groupby("census_tract")["lei"].nunique()
    o["tract_lenders"] = o["census_tract"].map(lenders_in_tract)
    return o


def hhi(leis):
    """Herfindahl-Hirschman index of lender shares (0-10,000; higher = more concentrated)."""
    shares = leis.value_counts(normalize=True)
    return float((shares ** 2).sum() * 10_000)


def market_structure(o):
    """Is the rest of the footprint more competitive than the top quarter?"""
    top10 = o.loc[o["subject"] == 0, "lei"].value_counts().head(10).index
    rows = []
    for group in [TOP, REST]:
        d = o[o["group"] == group]
        tracts = d[d["has_tract"] == 1].groupby("census_tract").agg(loans=("lei", "size"),
                                                                    lenders=("lei", "nunique"))
        county = d.groupby("county_fips").agg(hhi=("lei", hhi), loans=("lei", "size"))
        # submission_of_application: 1 = submitted directly to the lender, 2 = not (e.g. a broker).
        known = d[d["submission_of_application"].isin(["1", "2"])]
        subject = known[known["subject"] == 1]
        rows.append({
            "group": group, "counties": d["county_name"].nunique(), "market_loans": len(d),
            "lender_loans": int(d["subject"].sum()), "lender_share": d["subject"].mean(),
            "purchase_mix": (d["purpose_group"] == "purchase").mean(),
            "median_lenders_per_tract": tracts["lenders"].median(),
            "lenders_per_100_loans": (100 * tracts["lenders"] / tracts["loans"]).median(),
            "county_hhi": np.average(county["hhi"], weights=county["loans"]),
            "top10_lenders_share": d["lei"].isin(top10).mean(),
            "broker_submitted_share": (known["submission_of_application"] == "2").mean(),
            "lender_broker_submitted_share": (subject["submission_of_application"] == "2").mean(),
            "builder_lender_share": d["builder"].mean(),
            "median_loan_amount": d["amount"].median(),
            "jumbo_share": (d["conforming_loan_limit"] == "NC").mean(),
            "median_income_k": d["income_k"].median(),
        })
    return pd.DataFrame(rows)


def band_labels(edges, fmt):
    return [f"{fmt(a)}-{fmt(b)}" for a, b in zip(edges[:-1], edges[1:])]


def peer_comparison(o):
    """Like-for-like: subject-lender share within loan-size quintiles and tract-competition terciles."""
    o = o.copy()
    _, amount_edges = pd.qcut(o["amount"], 5, retbins=True)
    o["loan_size"] = pd.cut(o["amount"], amount_edges, include_lowest=True,
                            labels=band_labels(amount_edges, lambda v: f"${v / 1000:,.0f}k"))
    _, lender_edges = pd.qcut(o["tract_lenders"], 3, retbins=True)
    o["tract_competition"] = pd.cut(o["tract_lenders"], lender_edges, include_lowest=True,
                                    labels=band_labels(lender_edges, lambda v: f"{v:.0f}"))
    parts = []
    for dim in ["loan_size", "tract_competition"]:
        g = o.groupby([dim, "group"], observed=True).agg(market_loans=("subject", "size"),
                                                         lender_loans=("subject", "sum")).reset_index()
        g["lender_share"] = g["lender_loans"] / g["market_loans"]
        parts.append(g.rename(columns={dim: "band"}).assign(dimension=dim))
    out = pd.concat(parts, ignore_index=True)
    return out[["dimension", "band", "group", "market_loans", "lender_loans", "lender_share"]]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cy = pd.read_csv(L.processed / "county_year_metrics.csv", dtype={"county_fips": str})
    counties = cy[(cy["footprint_flag"] == 1) & (cy["year"] == s.SCORING_YEAR)].reset_index(drop=True)
    tracts = pd.read_csv(L.processed / "tract_metrics.csv", dtype={"census_tract": str, "county_fips": str})
    b = pd.read_csv(s.CONFIG / "builder_lenders.csv", dtype=str)
    builders = set(b.loc[b["include"] == "1", "lei"])

    unit = ladder_unit(counties)
    ladder, by_county, top_tracts, qualifying, top = build_ladder(counties, tracts, unit)
    both = ladder_both_ways(counties, tracts, unit)
    o = load_market(builders, set(top_tracts), set(top["county_name"]), unit)
    structure = market_structure(o)
    peers = peer_comparison(o)

    # Checks
    base_depth = tracts.loc[tracts["footprint_flag"] == 1, "opportunity_score"].sum()
    if not np.isclose(ladder.loc[ladder["rung"] == "base", "depth"].iloc[0], base_depth):
        raise ValueError("Base rung doesn't reproduce the Phase 3 depth opportunity")
    if not np.isclose(by_county["depth_ceiling"].sum(), ladder.loc[ladder["rung"] == "ceiling", "depth"].iloc[0]):
        raise ValueError("County ladder doesn't sum to the ladder total")
    codes = o["submission_of_application"].value_counts().rename_axis("code").reset_index(name="originations")
    codes["meaning"] = codes["code"].map({"1": "submitted directly to the lender",
                                          "2": "not submitted directly (e.g. broker)",
                                          "3": "not applicable", s.EXEMPT_CODE: "exempt"}).fillna("other")
    subject_codes = o.loc[o["subject"] == 1, "submission_of_application"].value_counts().to_dict()
    min_cell = int(peers["market_loans"].min())
    excluded = counties.loc[counties["market_all"] < s.LADDER_MIN_MARKET, "county_name"].tolist()
    n_counties = int((counties["market_all"] >= s.LADDER_MIN_MARKET).sum())

    ladder.round(6).to_csv(L.processed / "benchmark_ladder.csv", index=False)
    by_county.round(6).to_csv(L.processed / "depth_ladder_by_county.csv", index=False)
    structure.round(6).to_csv(L.processed / "market_structure.csv", index=False)
    peers.round(6).to_csv(L.processed / "peer_comparison.csv", index=False)
    codes.to_csv(OUT / "channel_field_coverage.csv", index=False)
    both.round(6).to_csv(OUT / "ladder_both_ways.csv", index=False)

    show = ladder.assign(share=(ladder["share"] * 100).round(2)).rename(columns={"share": "share_pct"})
    both_show = both.assign(share_pct=(both["share"] * 100).round(2), depth=both["depth"].round(1))
    units = "counties" if unit == "county" else "tracts"
    unit_rule = (
        f"{n_counties} of {len(counties)} footprint counties have {s.LADDER_MIN_MARKET}+ market "
        f"originations (excluded: {', '.join(excluded) or 'none'}). With at least "
        f"{s.LADDER_MIN_COUNTIES} qualifying counties the ladder uses counties; otherwise it uses "
        f"footprint tracts with {s.LADDER_MIN_TRACT_MARKET}+ market originations. **Unit used: {unit}**; "
        f"{len(qualifying):,} qualifying {units}, the top quarter is the top {len(top):,} by share")
    sections = [
        f"### 1. Benchmark ladder ({s.SCORING_YEAR})\nRules in `config/settings.py`. {unit_rule}. "
        f"Top-quarter {units} resting on a single {L.label} loan: "
        f"**{int((top['lender_all'] == 1).sum())}** of {len(top)}. The base rung reproduces Phase 3's "
        "depth opportunity exactly, and the county breakdown sums to each rung's total.\n\n"
        + md_table(show.round(2))
        + "\n\nThe ladder both ways, by county and by tract (`phase5_checks/ladder_both_ways.csv`), "
        "so the tract rule runs on every lender's data. Tract shares are noisier: a top-quarter "
        "tract can rest on one loan.\n\n"
        + md_table(both_show[["unit", "used", "rung", "share_pct", "depth", "qualifying",
                              "top_quarter", "top_quarter_on_one_loan"]]),
        "### 2. Channel field (`submission_of_application`)\nShares of broker-submitted loans use codes "
        "1 and 2 only; exempt and other codes are left out.\n\n" + md_table(codes)
        + f"\n\nSubject lender's codes: {subject_codes}.",
        f"### 3. Like-for-like comparison\nSmallest cell: **{min_cell:,}** market originations. "
        "Originations without a tract have no tract-competition band and are left out of that "
        f"dimension ({int(o['tract_lenders'].isna().sum())} loans)."
        + ("" if unit == "county" else " With the tract unit they also can't be in a top-quarter "
           f"tract, so they count as the rest of the footprint ({int((o['has_tract'] == 0).sum())} loans)."),
    ]
    write_data_quality("phase5_benchmarks", "Phase 5: benchmark ladder and market structure", sections,
                       path=L.data_quality, heading=lender_log_heading(L))

    print(show[["rung", "rule", "share_pct", "reference", "depth", "depth_outside_top_quarter"]]
          .round(1).to_string(index=False))
    print()
    print(structure.round(4).T.to_string())
    print()
    print(peers.pivot_table(index=["dimension", "band"], columns="group", values="lender_share",
                            observed=True).mul(100).round(2).to_string())


if __name__ == "__main__":
    main()
