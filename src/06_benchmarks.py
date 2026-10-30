"""Stage 6: benchmark ladder and market-structure evidence (PRD Appendix A, "Benchmark ladder").

Reads the Phase 3 outputs and the Phase 2 market file for the scoring year, and writes:
  data/processed/benchmark_ladder.csv         base / stretch / ceiling: rule, share, depth
  data/processed/depth_ladder_by_county.csv   depth at each rung, per footprint county
  data/processed/market_structure.csv         top-quarter footprint counties vs. the rest
  data/processed/peer_comparison.csv          subject-lender share by loan size and tract competition
plus the "Phase 5: benchmarks" section of DATA_QUALITY.md.

Lender-neutral: the subject lender and its footprint come from config/settings.py.
Run from the repo root:  python src/06_benchmarks.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as s  # noqa: E402
from src.common import md_table, neutral, read_processed, write_data_quality  # noqa: E402

OUT = s.PROCESSED / "phase5_checks"
TOP, REST = "top quarter", "rest of footprint"


def build_ladder(counties, tracts):
    """Base, stretch and ceiling shares, and depth at each rung (tract level, like the PRD's depth)."""
    qualifying = counties[counties["market_all"] >= s.LADDER_MIN_MARKET].sort_values(
        ["share_all", "market_all"], ascending=False)
    top = qualifying.head(int(np.ceil(s.LADDER_TOP_FRACTION * len(qualifying))))
    weakest = top.loc[top["share_all"].idxmin()]
    rungs = [
        ("base", "footprint average", counties["lender_all"].sum() / counties["market_all"].sum(),
         "all footprint counties"),
        ("stretch", "weakest county in the top quarter", weakest["share_all"], weakest["county_name"]),
        ("ceiling", "top quarter, pooled", top["lender_all"].sum() / top["market_all"].sum(),
         ", ".join(top["county_name"])),
    ]
    ft = tracts[tracts["footprint_flag"] == 1]
    in_top = ft["county_name"].isin(top["county_name"])
    current = counties["lender_all"].sum()
    rows, by_county = [], counties[["county_fips", "county_name", "market_all", "lender_all",
                                    "share_all"]].copy()
    by_county["in_top_quarter"] = by_county["county_name"].isin(top["county_name"])
    for rung, rule, share, reference in rungs:
        # Same form as opportunity_score: lift every tract below the rung up to it.
        gain = ft["market_all"] * (share - ft["share_all"].fillna(0)).clip(lower=0)
        rows.append({"rung": rung, "rule": rule, "share": share, "reference": reference,
                     "depth": gain.sum(), "depth_outside_top_quarter": gain[~in_top].sum(),
                     "depth_vs_current_loans": gain.sum() / current})
        by_county[f"depth_{rung}"] = by_county["county_name"].map(gain.groupby(ft["county_name"]).sum())
    return pd.DataFrame(rows), by_county.sort_values("depth_base", ascending=False), top, qualifying


def load_market(builders, top_names):
    """Scoring-year footprint originations, loan level, with group and subject-lender flags."""
    cols = ["lei", "county_fips", "census_tract", "action_taken", "fom_flag", "purpose_group",
            "has_tract", "loan_amount", "income", "conforming_loan_limit", "submission_of_application"]
    m = neutral(pd.read_parquet(s.PROCESSED / f"market_{s.SCORING_YEAR}.parquet", columns=cols))
    o = m[(m["action_taken"] == "1") & (m["footprint_flag"] == 1)].copy()
    names = pd.read_csv(s.CONFIG / "ga_counties.csv", dtype=str).set_index("county_fips")["county_name"]
    o["county_name"] = o["county_fips"].map(names)
    o["group"] = np.where(o["county_name"].isin(top_names), TOP, REST)
    o["subject"] = (o["lei"] == s.LENDER_LEI).astype(int)
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
    cy = read_processed("county_year_metrics", dtype={"county_fips": str})
    counties = cy[(cy["footprint_flag"] == 1) & (cy["year"] == s.SCORING_YEAR)].reset_index(drop=True)
    tracts = read_processed("tract_metrics", dtype={"census_tract": str, "county_fips": str})
    b = pd.read_csv(s.CONFIG / "builder_lenders.csv", dtype=str)
    builders = set(b.loc[b["include"] == "1", "lei"])

    ladder, by_county, top, qualifying = build_ladder(counties, tracts)
    o = load_market(builders, set(top["county_name"]))
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

    ladder.round(6).to_csv(s.PROCESSED / "benchmark_ladder.csv", index=False)
    by_county.round(6).to_csv(s.PROCESSED / "depth_ladder_by_county.csv", index=False)
    structure.round(6).to_csv(s.PROCESSED / "market_structure.csv", index=False)
    peers.round(6).to_csv(s.PROCESSED / "peer_comparison.csv", index=False)
    codes.to_csv(OUT / "channel_field_coverage.csv", index=False)

    show = ladder.assign(share=(ladder["share"] * 100).round(2)).rename(columns={"share": "share_pct"})
    sections = [
        f"### 1. Benchmark ladder ({s.SCORING_YEAR})\nRules in `config/settings.py`: counties need "
        f"{s.LADDER_MIN_MARKET}+ market originations to qualify ({len(qualifying)} of {len(counties)} do; "
        f"excluded: {', '.join(excluded) or 'none'}); the top quarter is the top "
        f"{len(top)} by share. The base rung reproduces Phase 3's depth opportunity exactly, and the "
        "county breakdown sums to each rung's total.\n\n" + md_table(show.round(2)),
        "### 2. Channel field (`submission_of_application`)\nShares of broker-submitted loans use codes "
        "1 and 2 only; exempt and other codes are left out.\n\n" + md_table(codes)
        + f"\n\nSubject lender's codes: {subject_codes}.",
        f"### 3. Like-for-like comparison\nSmallest cell: **{min_cell:,}** market originations. "
        "Originations without a tract have no tract-competition band and are left out of that "
        f"dimension ({int(o['tract_lenders'].isna().sum())} loans).",
    ]
    write_data_quality("phase5_benchmarks", "Phase 5: benchmark ladder and market structure", sections)

    print(show[["rung", "rule", "share_pct", "reference", "depth", "depth_outside_top_quarter"]]
          .round(1).to_string(index=False))
    print()
    print(structure.round(4).T.to_string())
    print()
    print(peers.pivot_table(index=["dimension", "band"], columns="group", values="lender_share",
                            observed=True).mul(100).round(2).to_string())


if __name__ == "__main__":
    main()
