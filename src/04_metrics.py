"""Stage 4: share, trend and opportunity metrics (PRD Appendix A, "Metrics").

Runs for one lender (config/lender.py). Reads the shared Phase 2 market files (limited to the
lender's loan types) and config/ga_counties.csv, and writes,
in data/processed/<key>/:
  counties.csv                every Georgia county: footprint flag, OMB tags, market group
  opportunity_top25.csv       R2: top 25 footprint tracts (stage 07 adds context for outputs/)
  tract_metrics.csv           every Georgia tract, scoring year
  depth_by_county.csv         depth opportunity rolled up by footprint county
  trend_summary.csv           footprint / non-footprint / statewide share by year and purpose
  county_year_metrics.csv     every county x year, by purpose
  lender_trend_footprint.csv  footprint share by year: top 10 footprint lenders and the subject lender
  expansion_counties.csv      non-footprint counties: gain at the expansion target share
  expansion_groups.csv        expansion gain by market group and by tier
plus the checks in phase3_checks/ and the Phase 3 section of the lender's data-quality log.

Run from the repo root:  python src/04_metrics.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as s  # noqa: E402
from config.lender import LENDER as L  # noqa: E402
from src.common import lender_log_heading, lender_market, md_table, write_data_quality  # noqa: E402

OUT = L.processed / "phase3_checks"
PURPOSES = ["purchase", "refinance", "all"]
TOP_N = 25
NO_GROUP = "(no metro/micro area)"


def load_builders():
    """LEIs of builder-owned lenders (config/builder_lenders.csv, rows with include = 1)."""
    b = pd.read_csv(s.CONFIG / "builder_lenders.csv", dtype=str)
    return b, set(b.loc[b["include"] == "1", "lei"])


def load_originations(builders):
    """Every year's originations (action_taken = 1) of the lender's product, with 0/1
    subject-lender, footprint and builder-lender columns."""
    cols = ["lei", "county_fips", "census_tract", "action_taken", "purpose_group", "has_tract"]
    frames = []
    for y in s.YEARS:
        df = lender_market(L, y, cols)
        frames.append(df[df["action_taken"] == "1"].drop(columns="action_taken").assign(year=y))
    orig = pd.concat(frames, ignore_index=True)
    orig["footprint_flag"] = orig["county_fips"].isin(L.footprint).astype("int8")
    orig["lender"] = (orig["lei"] == L.lei).astype(int)
    orig["builder"] = orig["lei"].isin(builders).astype(int)
    return orig


def market_groups(counties, orig):
    """market_group per county (PRD Appendix A): the county's CSA if it has one, else its CBSA.

    The CSA that holds the footprint's main metro area (the CBSA with the most scoring-year
    footprint originations) is split back into its CBSAs: as one group it would swallow the
    nearby metros (for an Atlanta footprint: Athens, Gainesville, Rome) that are separate
    expansion choices. Returns the counties with market_group, and the main metro (or None).
    """
    cur = orig[(orig["year"] == s.SCORING_YEAR) & (orig["footprint_flag"] == 1)]
    loans = counties["county_fips"].map(cur.groupby("county_fips").size()).fillna(0)
    fp = counties.assign(loans=loans)[(counties["footprint_flag"] == 1) & counties["cbsa_code"].notna()]
    by_cbsa = fp.groupby("cbsa_code").agg(counties=("county_fips", "size"), loans=("loans", "sum"))
    main = None
    if len(by_cbsa):
        code = by_cbsa["loans"].sort_values(ascending=False, kind="stable").index[0]
        row = counties[counties["cbsa_code"] == code].iloc[0]
        main = {"cbsa_code": code, "cbsa_title": row["cbsa_title"], "csa_code": row["csa_code"],
                "csa_title": row["csa_title"], "counties": int(by_cbsa.loc[code, "counties"]),
                "loan_share": by_cbsa.loc[code, "loans"] / len(cur)}
    home_csa = main["csa_code"] if main else None
    use_csa = counties["csa_code"].notna() & ~counties["csa_code"].isin([home_csa])
    counties = counties.assign(market_group=counties["csa_title"].where(use_csa, counties["cbsa_title"]))
    return counties, main


def counts(orig, keys):
    """Market and subject-lender originations by keys, one column per purpose.

    SQL: SELECT keys, COUNT(*) and SUM(lender) for each purpose ... GROUP BY keys.
    """
    g = orig.groupby(keys + ["purpose_group"]).agg(market=("lender", "size"), lender=("lender", "sum"))
    wide = g.unstack("purpose_group", fill_value=0)
    wide.columns = [f"{m}_{p}" for m, p in wide.columns]
    for m in ["market", "lender"]:
        wide[f"{m}_all"] = wide[f"{m}_purchase"] + wide[f"{m}_refinance"]
    return wide.reset_index()


def add_shares(df):
    for p in PURPOSES:
        df[f"share_{p}"] = df[f"lender_{p}"] / df[f"market_{p}"].where(df[f"market_{p}"] > 0)
    return df


def fill_counts(df):
    """After a LEFT JOIN onto a full list (all tracts, all counties), missing counts are zero."""
    num = [c for c in df.columns if c.startswith(("market_", "lender_"))]
    df[num] = df[num].fillna(0).astype(int)
    return df


def lender_names(leis, lenders):
    # A few 2025 LEIs are missing from the HMDA filers list (DATA_QUALITY.md, Phase 3 check 11).
    return leis.map(lenders).fillna("LEI " + leis + " (no name in filers list)")


def rank_by(df, col):
    """1 = highest score. Ties go to the bigger market, then the tract/county code."""
    key = "census_tract" if "census_tract" in df.columns else "county_fips"
    order = df[df[col].notna()].sort_values([col, "market_all", key], ascending=[False, False, True])
    return pd.Series(np.arange(1, len(order) + 1), index=order.index).reindex(df.index).astype("Int64")


# ---------------------------------------------------------------- trend (R3, R5)

def build_trend(orig):
    scopes = {"footprint": orig[orig["footprint_flag"] == 1], "non_footprint": orig[orig["footprint_flag"] == 0],
              "statewide": orig}
    t = pd.concat([counts(sub, ["year"]).assign(scope=name) for name, sub in scopes.items()],
                  ignore_index=True)
    t = add_shares(t)
    t["market_refi_mix"] = t["market_refinance"] / t["market_all"]
    t["lender_refi_mix"] = t["lender_refinance"] / t["lender_all"]
    t["note"] = t["year"].map({2022: "tail of the 2020-21 refi boom"}).fillna("")
    first = ["scope", "year"]
    return t[first + [c for c in t.columns if c not in first]]


def build_county_year(orig, counties):
    full = pd.MultiIndex.from_product([counties["county_fips"], s.YEARS],
                                      names=["county_fips", "year"]).to_frame(index=False)
    cy = fill_counts(full.merge(counts(orig, ["county_fips", "year"]), how="left"))
    cy = counties[["county_fips", "county_name", "footprint_flag", "market_group",
                   "urban_rural_tier"]].merge(cy, on="county_fips")
    return add_shares(cy)


def build_lender_trend(orig, lenders):
    """Footprint share by year for the top 10 footprint lenders in the scoring year, plus the subject lender."""
    footprint = orig[orig["footprint_flag"] == 1]
    cur = footprint[footprint["year"] == s.SCORING_YEAR]["lei"].value_counts()
    footprint_rank = pd.Series(np.arange(1, len(cur) + 1), index=cur.index)
    top = [lei for lei in cur.index if lei != L.lei][:10] + [L.lei]

    loans = footprint.groupby(["lei", "year", "purpose_group"]).size().unstack(fill_value=0)
    loans["all"] = loans.sum(axis=1)
    market = footprint.groupby(["year", "purpose_group"]).size().unstack(fill_value=0)
    market["all"] = market.sum(axis=1)

    idx = pd.MultiIndex.from_product([top, s.YEARS], names=["lei", "year"])
    loans = loans.reindex(idx, fill_value=0)[PURPOSES]
    shares = loans / market.loc[loans.index.get_level_values("year"), PURPOSES].to_numpy()
    out = loans.add_prefix("loans_").join(shares.add_prefix("share_")).reset_index()
    out["name"] = lender_names(out["lei"], lenders)
    out[f"footprint_rank_{s.SCORING_YEAR}"] = out["lei"].map(footprint_rank)
    return out[["lei", "name", f"footprint_rank_{s.SCORING_YEAR}", "year"]
               + [c for c in out.columns if c.startswith(("loans_", "share_"))]]


# ---------------------------------------------------------------- depth (R1, R2)

def top_competitors(cur, lenders, key="census_tract"):
    """Top 3 competitors (not the subject lender) per tract (or per county) in the scoring year.

    SQL: ROW_NUMBER() OVER (PARTITION BY key ORDER BY loans DESC, footprint_volume DESC, lei).
    Ties on loans go to the lender with more footprint-wide volume.
    """
    comp = cur[cur["lender"] == 0]
    by = comp.groupby([key, "lei"]).size().rename("loans").reset_index()
    footprint_volume = comp[comp["footprint_flag"] == 1].groupby("lei").size().rename("footprint_volume")
    by = by.merge(footprint_volume, how="left", left_on="lei", right_index=True)
    by["footprint_volume"] = by["footprint_volume"].fillna(0)
    by = by.sort_values([key, "loans", "footprint_volume", "lei"], ascending=[True, False, False, True])
    by["rank"] = by.groupby(key).cumcount() + 1

    # A tie "decides" a top 3 spot when the 3rd and 4th lenders have the same number of loans.
    third_fourth = by[by["rank"].isin([3, 4])].pivot(index=key, columns="rank", values="loans")
    tie = (third_fourth[3] == third_fourth[4]).rename("top3_tie")

    top = by[by["rank"] <= 3].copy()
    top["name"] = lender_names(top["lei"], lenders)
    wide = top.pivot(index=key, columns="rank", values=["name", "loans"])
    wide.columns = [f"competitor_{r}" if v == "name" else f"competitor_{r}_loans"
                    for v, r in wide.columns]
    wide = wide[[f"competitor_{r}{x}" for r in [1, 2, 3] for x in ["", "_loans"]]]
    lender_count = cur.groupby(key)["lei"].nunique().rename("lenders_in_tract")
    return wide.join(lender_count, how="outer").join(tie).reset_index()


def build_tracts(orig, counties, lenders, footprint_share, footprint_share_contestable):
    tiger = gpd.read_file(s.RAW / "tiger" / "tl_2024_13_tract.zip", ignore_geometry=True)
    spine = pd.DataFrame({"census_tract": tiger["GEOID"],
                          "county_fips": tiger["STATEFP"] + tiger["COUNTYFP"]})
    placed = orig[orig["has_tract"] == 1]
    cur = placed[placed["year"] == s.SCORING_YEAR]

    t = fill_counts(spine.merge(counts(cur, ["census_tract"]), how="left", on="census_tract"))
    t = add_shares(t)
    # Stability check: tract share from the two latest years combined.
    two = counts(placed[placed["year"] >= s.SCORING_YEAR - 1], ["census_tract"])
    two = two.set_index("census_tract")
    t["share_2yr"] = t["census_tract"].map(two["lender_all"] / two["market_all"])
    t = counties[["county_fips", "county_name", "footprint_flag", "market_group",
                  "urban_rural_tier"]].merge(t, on="county_fips", how="right")
    t["low_volume"] = t["market_all"] < s.LOW_VOLUME_THRESHOLD

    # Depth scores only footprint tracts; other areas are scored by county (expansion).
    footprint = t["footprint_flag"] == 1
    gap = (footprint_share - t["share_all"].fillna(0)).clip(lower=0)
    gap_2yr = (footprint_share - t["share_2yr"].fillna(0)).clip(lower=0)
    t["gap_to_footprint_share"] = gap.where(footprint)
    t["opportunity_score"] = (t["market_all"] * gap).where(footprint)
    t["opportunity_score_2yr"] = (t["market_all"] * gap_2yr).where(footprint)
    t["opportunity_rank"] = rank_by(t, "opportunity_score")
    t["opportunity_rank_2yr"] = rank_by(t, "opportunity_score_2yr")
    t["stable_top25"] = (t["opportunity_rank"] <= TOP_N) & (t["opportunity_rank_2yr"] <= TOP_N)

    # Contestable market: leave out builder-owned lenders' loans, which the lender rarely wins.
    # The benchmark is the lender's footprint share of the same contestable market.
    builder = cur[cur["builder"] == 1].groupby("census_tract").size()
    t["builder_loans"] = t["census_tract"].map(builder).fillna(0).astype(int)
    t["market_contestable"] = t["market_all"] - t["builder_loans"]
    share_c = t["lender_all"] / t["market_contestable"].where(t["market_contestable"] > 0)
    gap_c = (footprint_share_contestable - share_c.fillna(0)).clip(lower=0)
    t["opportunity_score_contestable"] = (t["market_contestable"] * gap_c).where(footprint)
    t["opportunity_rank_contestable"] = rank_by(t, "opportunity_score_contestable")
    t = t.merge(top_competitors(cur, lenders), on="census_tract", how="left")
    t["top3_tie"] = t["top3_tie"].fillna(False).astype(bool)
    t["lenders_in_tract"] = t["lenders_in_tract"].fillna(0).astype(int)
    return t.sort_values("census_tract").reset_index(drop=True)


def top25_output(tracts):
    """R2 deliverable: shares as percents, for reading in Excel."""
    top = tracts[tracts["opportunity_rank"] <= TOP_N].sort_values("opportunity_rank")
    out = top[["opportunity_rank", "census_tract", "county_name", "market_all", "market_purchase",
               "market_refinance", "lender_all", "lender_purchase", "lender_refinance"]].copy()
    out["lender_share_pct"] = (top["share_all"] * 100).round(2)
    out["gap_to_footprint_share_pct"] = (top["gap_to_footprint_share"] * 100).round(2)
    out["opportunity_score"] = top["opportunity_score"].round(1)
    out["rank_using_2024_25_share"] = top["opportunity_rank_2yr"]
    out["stable_top25"] = top["stable_top25"]
    out["builder_lender_loans"] = top["builder_loans"]
    out["contestable_score"] = top["opportunity_score_contestable"].round(1)
    out["contestable_rank"] = top["opportunity_rank_contestable"]
    comp_cols = [c for c in top.columns if c.startswith("competitor_")]
    out[comp_cols + ["lenders_in_tract"]] = top[comp_cols + ["lenders_in_tract"]]
    return out


def build_depth_by_county(tracts, orig, lenders):
    """Depth opportunity per footprint county: more stable than single tracts (check 6)."""
    f = tracts[tracts["footprint_flag"] == 1]
    d = f.groupby(["county_fips", "county_name"]).agg(
        tracts=("census_tract", "size"), low_volume_tracts=("low_volume", "sum"),
        market_all=("market_all", "sum"), lender_all=("lender_all", "sum"),
        builder_loans=("builder_loans", "sum"),
        opportunity=("opportunity_score", "sum"), opportunity_2yr=("opportunity_score_2yr", "sum"),
        opportunity_contestable=("opportunity_score_contestable", "sum"),
        top25_tracts=("opportunity_rank", lambda x: int((x <= TOP_N).sum())),
        stable_top25_tracts=("stable_top25", "sum")).reset_index()
    d["share_all"] = d["lender_all"] / d["market_all"]
    for col in ["opportunity", "opportunity_2yr", "opportunity_contestable"]:
        d[col.replace("opportunity", "rank")] = rank_by(d, col)
    cur = orig[(orig["year"] == s.SCORING_YEAR) & (orig["footprint_flag"] == 1) & (orig["has_tract"] == 1)]
    comp = top_competitors(cur, lenders, key="county_fips").drop(columns=["top3_tie"])
    d = d.merge(comp.rename(columns={"lenders_in_tract": "lenders_in_county"}), on="county_fips")
    return d.sort_values("rank").reset_index(drop=True)


# ---------------------------------------------------------------- expansion (R3a, R3b)

def build_expansion(county_year):
    cy = county_year[county_year["footprint_flag"] == 0]
    base_col = f"market_purchase_{s.PURCHASE_CHANGE_BASE_YEAR}"
    base = cy.loc[cy["year"] == s.PURCHASE_CHANGE_BASE_YEAR, ["county_fips", "market_purchase"]]
    e = cy[cy["year"] == s.SCORING_YEAR].merge(
        base.rename(columns={"market_purchase": base_col}), on="county_fips")
    e["purchase_market_change"] = (e["market_purchase"] / e[base_col].where(e[base_col] > 0)) - 1
    e["current_share"] = e["share_all"].fillna(0)
    e["expansion_gain"] = e["market_all"] * (L.expansion_target_share - e["current_share"]).clip(lower=0)
    e["expansion_rank"] = rank_by(e, "expansion_gain")
    cols = ["expansion_rank", "county_fips", "county_name", "market_group", "urban_rural_tier",
            "market_all", "market_purchase", "market_refinance", "lender_all", "current_share",
            "expansion_gain", base_col, "purchase_market_change"]
    return e.sort_values("expansion_rank")[cols].reset_index(drop=True)


def build_groups(expansion, counties):
    """Expansion gain rolled up by market group and by urban/rural tier (SQL: GROUP BY ... ROLLUP)."""
    base_col = f"market_purchase_{s.PURCHASE_CHANGE_BASE_YEAR}"
    # A market group partly inside the footprint (e.g. the Atlanta metro) says so in its label.
    partial = set(counties.loc[counties["footprint_flag"] == 1, "market_group"].dropna())
    label = expansion["market_group"].fillna(NO_GROUP)
    label = label.where(~label.isin(partial), label + f" (outside {L.footprint_label})")
    rows = []
    for grouping, key in [("market_group", label), ("tier", expansion["urban_rural_tier"])]:
        g = expansion.assign(group=key).groupby("group").agg(
            counties=("county_name", "size"),
            county_names=("county_name", lambda x: ", ".join(sorted(x))),
            market_all=("market_all", "sum"), lender_all=("lender_all", "sum"),
            expansion_gain=("expansion_gain", "sum"),
            market_purchase=("market_purchase", "sum"), **{base_col: (base_col, "sum")})
        g["current_share"] = g["lender_all"] / g["market_all"]
        g["purchase_market_change"] = g["market_purchase"] / g[base_col] - 1
        g = g.sort_values("expansion_gain", ascending=False).reset_index()
        g.insert(0, "grouping", grouping)
        g.insert(2, "gain_rank", np.arange(1, len(g) + 1))
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------- checks

def check_totals(orig, county_year, tracts, spine_tracts):
    """Check 1: county sums match Phase 2's market size; tracts + unplaced rows match counties."""
    size = pd.read_csv(L.processed / "phase2_checks" / "market_size.csv")
    rows = []
    for _, r in size.iterrows():
        cy = county_year[county_year["year"] == r["year"]]
        if r["scope"] == "footprint":
            cy = cy[cy["footprint_flag"] == 1]
        for col in ["market_originations", "market_purchase", "market_refinance",
                    "lender_originations", "lender_purchase", "lender_refinance"]:
            ours = int(cy[col.replace("originations", "all")].sum())
            rows.append({"check": "county sum vs. Phase 2", "year": r["year"], "scope": r["scope"],
                         "measure": col, "expected": int(r[col]), "ours": ours})

    cur = orig[orig["year"] == s.SCORING_YEAR]
    for scope, footprint_only in [("statewide", False), ("footprint", True)]:
        c = cur[cur["footprint_flag"] == 1] if footprint_only else cur
        t = tracts[tracts["footprint_flag"] == 1] if footprint_only else tracts
        no_tract = c["has_tract"] == 0
        off_spine = (c["has_tract"] == 1) & ~c["census_tract"].isin(spine_tracts)
        for m, col in [("market", "market_all"), ("lender", "lender_all")]:
            weight = c["lender"] if m == "lender" else 1
            ours = int(t[col].sum() + (no_tract * weight).sum() + (off_spine * weight).sum())
            rows.append({"check": "tracts + no-tract + not-in-TIGER vs. all",
                         "year": s.SCORING_YEAR, "scope": scope, "measure": m,
                         "expected": int(len(c) if m == "market" else c["lender"].sum()),
                         "ours": ours})
    out = pd.DataFrame(rows)
    out["match"] = out["expected"] == out["ours"]
    if not out["match"].all():
        raise ValueError(f"Totals don't reconcile:\n{out[~out['match']]}")
    return out


def check_unplaced(orig, spine_tracts):
    """Checks 3-4: scoring-year originations that can't go into tract metrics."""
    cur = orig[orig["year"] == s.SCORING_YEAR]
    rows = []
    for scope, c in [("statewide", cur), ("footprint", cur[cur["footprint_flag"] == 1])]:
        no_tract = c["has_tract"] == 0
        off_spine = (c["has_tract"] == 1) & ~c["census_tract"].isin(spine_tracts)
        rows.append({"scope": scope, "no_tract_market": int(no_tract.sum()),
                     "no_tract_lender": int(c.loc[no_tract, "lender"].sum()),
                     "not_in_tiger_market": int(off_spine.sum()),
                     "not_in_tiger_tracts": c.loc[off_spine, "census_tract"].nunique()})
    return pd.DataFrame(rows)


def check_min_volume(tracts):
    """Check 5: what a minimum-volume rule would remove (footprint tracts, scoring year)."""
    f = tracts[tracts["footprint_flag"] == 1]
    total = f["opportunity_score"].sum()
    rows = [{"threshold": "zero originations", "tracts": int((f["market_all"] == 0).sum()),
             "market_loans": 0, "lender_loans": 0, "opportunity": 0.0, "pct_of_opportunity": 0.0,
             "tracts_share_over_10pct": 0}]
    for th in [10, 15, 20, 30]:
        lo = f[(f["market_all"] > 0) & (f["market_all"] < th)]
        rows.append({"threshold": f"< {th}", "tracts": len(lo),
                     "market_loans": int(lo["market_all"].sum()),
                     "lender_loans": int(lo["lender_all"].sum()),
                     "opportunity": round(lo["opportunity_score"].sum(), 1),
                     "pct_of_opportunity": round(100 * lo["opportunity_score"].sum() / total, 1),
                     "tracts_share_over_10pct": int((lo["share_all"] > 0.10).sum())})
    return pd.DataFrame(rows)


def check_stability(tracts):
    """Check 6: top 25 on the scoring year vs. on the two latest years combined."""
    either = tracts[(tracts["opportunity_rank"] <= TOP_N) | (tracts["opportunity_rank_2yr"] <= TOP_N)]
    out = either[["census_tract", "county_name", "opportunity_rank", "opportunity_rank_2yr",
                  "market_all", "lender_all", "share_all", "share_2yr"]].copy()
    out["in_both"] = (out["opportunity_rank"] <= TOP_N) & (out["opportunity_rank_2yr"] <= TOP_N)
    return out.sort_values(["opportunity_rank"]).reset_index(drop=True)


def check_lenders(orig, lenders):
    """Check 8: footprint lenders that were top 25 in any year, for a by-hand merger review.

    Flags years with no loans and year-over-year moves in purchase share above 1.5x or below
    1/1.5. Purchase share, not loan count or total share, so the 2023 refi collapse doesn't
    flag every refi-heavy lender.
    """
    footprint = orig[(orig["footprint_flag"] == 1) & (orig["lender"] == 0)]
    loans = footprint.groupby(["lei", "year"]).size().unstack("year", fill_value=0)
    purchase = orig[(orig["footprint_flag"] == 1) & (orig["purpose_group"] == "purchase")]
    share = (purchase.groupby(["lei", "year"]).size().unstack("year", fill_value=0)
             .reindex(loans.index, fill_value=0) / purchase.groupby("year").size())
    top_years = {y: set(loans[y].nlargest(TOP_N).index) for y in s.YEARS}
    universe = sorted(set().union(*top_years.values()))

    rows = []
    for lei in universe:
        sh = share.loc[lei]
        jumps = []
        for a, b in zip(s.YEARS, s.YEARS[1:]):
            if sh[a] > 0 and sh[b] > 0 and not (1 / 1.5 <= sh[b] / sh[a] <= 1.5):
                jumps.append(f"{a}->{b} x{sh[b] / sh[a]:.1f}")
        rows.append({"lei": lei,
                     **{f"loans_{y}": int(loans.loc[lei, y]) for y in s.YEARS},
                     "top25_years": ", ".join(str(y) for y in s.YEARS if lei in top_years[y]),
                     "years_with_no_loans": ", ".join(str(y) for y in s.YEARS if loans.loc[lei, y] == 0),
                     "purchase_share_jumps": "; ".join(jumps)})
    out = pd.DataFrame(rows).sort_values(f"loans_{s.SCORING_YEAR}", ascending=False)
    out.insert(1, "name", lender_names(out["lei"], lenders))
    out["flagged"] = (out["years_with_no_loans"] != "") | (out["purchase_share_jumps"] != "")
    return out.reset_index(drop=True)


def check_unnamed(orig, lender_table):
    """Check 11: originations by LEIs not named in the HMDA filers lists (named from GLEIF instead)."""
    other = lender_table[lender_table["name_source"] != "hmda_filers"].set_index("lei")
    o = orig[orig["lei"].isin(other.index)]
    out = o.groupby(["year", "lei"]).agg(originations=("lender", "size"),
                                         footprint_originations=("footprint_flag", "sum")).reset_index()
    out["name"] = out["lei"].map(other["name"])
    out["name_source"] = out["lei"].map(other["name_source"])
    return out.sort_values(["year", "originations"], ascending=[True, False]).reset_index(drop=True)


def check_builders(builder_list, orig):
    """Check 12: builder-lender list and each lender's scoring-year footprint volume."""
    cur = orig[(orig["year"] == s.SCORING_YEAR) & (orig["footprint_flag"] == 1)]
    loans = cur.groupby("lei").size()
    purchases = cur[cur["purpose_group"] == "purchase"].groupby("lei").size()
    b = builder_list[["lender_name", "builder", "include", "basis", "lei"]].copy()
    b["footprint_loans"] = b["lei"].map(loans).fillna(0).astype(int)
    b["footprint_purchase_share"] = b["lei"].map(purchases).fillna(0) / purchases.sum()
    return b.drop(columns="lei")


def check_groups(counties):
    """Check 9: market group and tier assignment for every county."""
    c = counties.assign(market_group=counties["market_group"].fillna(NO_GROUP))
    g = c.groupby(["market_group", "urban_rural_tier"]).agg(
        counties=("county_name", "size"), footprint_counties=("footprint_flag", "sum"),
        county_names=("county_name", lambda x: ", ".join(sorted(x)))).reset_index()
    return g.sort_values("counties", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- main

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    counties = pd.read_csv(s.CONFIG / "ga_counties.csv", dtype=str)
    counties["footprint_flag"] = counties["county_fips"].isin(L.footprint).astype(int)
    lender_table = pd.read_csv(s.PROCESSED / "lenders.csv", dtype=str)
    lenders = lender_table.dropna(subset=["name"]).set_index("lei")["name"].to_dict()

    builder_list, builders = load_builders()

    print("Loading originations...")
    orig = load_originations(builders)
    counties, main_metro = market_groups(counties, orig)
    counties.to_csv(L.processed / "counties.csv", index=False)
    county_year = build_county_year(orig, counties)
    footprint_cur = county_year[(county_year["year"] == s.SCORING_YEAR) & (county_year["footprint_flag"] == 1)]
    footprint_share = footprint_cur["lender_all"].sum() / footprint_cur["market_all"].sum()
    footprint_orig = orig[(orig["year"] == s.SCORING_YEAR) & (orig["footprint_flag"] == 1)]
    footprint_builder = int(footprint_orig["builder"].sum())
    footprint_share_contestable = footprint_cur["lender_all"].sum() / (footprint_cur["market_all"].sum() - footprint_builder)
    print(f"  footprint_share {s.SCORING_YEAR}: {footprint_share:.4%} "
          f"(contestable market, without builder lenders: {footprint_share_contestable:.4%})")

    trend = build_trend(orig)
    lender_trend = build_lender_trend(orig, lenders)
    print("Scoring tracts...")
    tracts = build_tracts(orig, counties, lenders, footprint_share, footprint_share_contestable)
    spine_tracts = set(tracts["census_tract"])
    top25 = top25_output(tracts)
    depth_county = build_depth_by_county(tracts, orig, lenders)
    expansion = build_expansion(county_year)
    groups = build_groups(expansion, counties)

    totals = check_totals(orig, county_year, tracts, spine_tracts)
    unplaced = check_unplaced(orig, spine_tracts)
    min_volume = check_min_volume(tracts)
    stability = check_stability(tracts)
    lender_review = check_lenders(orig, lenders)
    group_check = check_groups(counties)
    unnamed = check_unnamed(orig, lender_table)
    builder_check = check_builders(builder_list, orig)
    at_target = expansion[expansion["current_share"] >= L.expansion_target_share]

    top25.to_csv(L.processed / "opportunity_top25.csv", index=False)
    for name, df in [("tract_metrics", tracts), ("depth_by_county", depth_county),
                     ("trend_summary", trend),
                     ("county_year_metrics", county_year), ("lender_trend_footprint", lender_trend),
                     ("expansion_counties", expansion), ("expansion_groups", groups)]:
        df.round(6).to_csv(L.processed / f"{name}.csv", index=False)
    for name, df in [("1_totals_reconciliation", totals), ("3_4_unplaced_originations", unplaced),
                     ("5_min_volume_sensitivity", min_volume), ("6_stability_top25", stability),
                     ("8_lender_merger_review", lender_review), ("9_market_groups", group_check),
                     ("11_gleif_named_lenders", unnamed), ("12_builder_lenders", builder_check)]:
        df.round(6).to_csv(OUT / f"{name}.csv", index=False)

    # Summaries for DATA_QUALITY.md
    in_both = int(stability["in_both"].sum())
    county_move = int((depth_county["rank"] - depth_county["rank_2yr"]).abs().max())
    footprint_tracts = tracts[tracts["footprint_flag"] == 1]
    top_ties = int(tracts.loc[tracts["opportunity_rank"] <= TOP_N, "top3_tie"].sum())
    flagged = lender_review[lender_review["flagged"]]
    sections = [
        "### 1. Totals reconcile\nCounty sums match the Phase 2 market-size table for every year, "
        f"scope and measure; scoring-year tracts plus unplaced rows match the totals. "
        f"Mismatches: **{int((~totals['match']).sum())}** of {len(totals)} "
        "(the script stops on any mismatch). Details: `phase3_checks/1_totals_reconciliation.csv`.",
        f"### 2. Benchmark\n`footprint_share` ({s.SCORING_YEAR}) = {footprint_cur['lender_all'].sum():,} / "
        f"{footprint_cur['market_all'].sum():,} = **{footprint_share:.2%}**. Expansion uses "
        f"`expansion.target_share` = {L.expansion_target_share:.1%} from the lender config "
        "(planning assumption).",
        f"### 3-4. Originations outside tract metrics ({s.SCORING_YEAR})\nThey stay in county, {L.footprint_label} "
        "and statewide figures but have no tract to score. All 2,796 TIGER tracts are in "
        f"`tract_metrics.csv`; {int((footprint_tracts['market_all'] == 0).sum())} {L.footprint_label} tracts had no "
        f"{s.SCORING_YEAR} originations and are kept with zeros.\n\n" + md_table(unplaced),
        f"### 5. Minimum volume ({L.footprint_label} tracts, {s.SCORING_YEAR})\nNo tract is dropped. Tracts under "
        f"{s.LOW_VOLUME_THRESHOLD} market originations get `low_volume = True` (greyed out on the "
        "map, left out of share statistics). The top 25 all have "
        f"{int(top25['market_all'].min())}+ market originations, so the rule doesn't affect "
        "the ranking.\n\n" + md_table(min_volume),
        f"### 6. Stability of the top 25\n**{in_both} of {TOP_N}** tracts are in the top 25 both "
        f"on {s.SCORING_YEAR} share and on {s.SCORING_YEAR - 1}-{s.SCORING_YEAR} combined share "
        f"(`stable_top25 = True`). Most top tracts have zero or one {L.label} loan, so one loan more or "
        "less moves a tract many places. County totals are steadier: the largest move between "
        f"the two county rankings is **{county_move} place(s)** (`depth_by_county.csv`), so "
        "findings lead with counties and use tracts to say where within a county. "
        "Details: `phase3_checks/6_stability_top25.csv`.",
        f"### 7. Competitor ties\nTies on loan count are broken by the lender's {L.footprint_label}-wide "
        f"{s.SCORING_YEAR} volume. A tie decided the 3rd competitor in **{top_ties} of {TOP_N}** "
        f"top tracts ({int(footprint_tracts['top3_tie'].sum())} of {len(footprint_tracts):,} {L.footprint_label} tracts).",
        f"### 8. Lender merger review (open item 3)\n{len(lender_review)} non-{L.label} lenders were in "
        f"the {L.footprint_label} top {TOP_N} in at least one year; **{len(flagged)}** are flagged (a year with no "
        f"loans, or {L.footprint_label} purchase share moving by more than 1.5x year over year). "
        "Review by hand for "
        "mergers. "
        "Full list: `phase3_checks/8_lender_merger_review.csv`.\n\n"
        + md_table(flagged.drop(columns=["lei", "flagged"])),
        "### 9. Market groups and tiers\nHybrid rule (PRD Appendix A): CSA where one exists, "
        "else CBSA, except the CSA that holds the footprint's main metro area, which is split into "
        "its CBSAs. " + (
            f"Main metro area: **{main_metro['cbsa_title']}** (CBSA {main_metro['cbsa_code']}), "
            f"{main_metro['counties']} of {len(L.footprint)} {L.footprint_label} counties and "
            f"{main_metro['loan_share']:.1%} of {L.footprint_label} originations in {s.SCORING_YEAR}. "
            + (f"Split CSA: {main_metro['csa_title']}." if pd.notna(main_metro["csa_code"])
               else "It is in no CSA, so nothing is split.")
            if main_metro else f"No {L.footprint_label} county is in a metro or micro area, so nothing "
            "is split.") + " Each county's group is in `counties.csv`.\n\n" + md_table(group_check),
        f"### 10. Expansion edge cases\nNon-{L.footprint_label} counties where {L.label} is already at or above "
        f"{L.expansion_target_share:.0%} (expansion gain 0): "
        + (", ".join(f"{r.county_name} ({r.current_share:.1%})" for r in at_target.itertuples())
           or "none") + ".",
        "### 11. Lenders missing from the HMDA filers lists\nLEIs with market originations that "
        "are missing from every cached HMDA `/view/filers` list, named from GLEIF instead "
        "(Phase 2 builds `lenders.csv`). Any LEI GLEIF can't name shows as "
        "`LEI ... (no name in filers list)`. All originations are kept.\n\n"
        + md_table(unnamed.drop(columns="lei")),
        "### 12. Builder-owned lenders (contestable market)\n`config/builder_lenders.csv`, "
        "**pending your review**. Rows with `include = 1` are left out of the contestable market "
        "(`opportunity_score_contestable`); `include = 0` rows are candidates that show the "
        "builder pattern (almost no refinance, purchases packed into a few tracts) but are not "
        f"confirmed. Included lenders made {footprint_builder:,} of {footprint_cur['market_all'].sum():,} {L.footprint_label} "
        f"originations in {s.SCORING_YEAR}. Contestable `footprint_share` = "
        f"**{footprint_share_contestable:.2%}**. Depth opportunity: "
        f"{footprint_tracts['opportunity_score'].sum():,.0f} loans on the full market, "
        f"{footprint_tracts['opportunity_score_contestable'].sum():,.0f} on the contestable market.\n\n"
        + md_table(builder_check.assign(
            footprint_purchase_share=(builder_check["footprint_purchase_share"] * 100).round(2))
            .rename(columns={"footprint_purchase_share": "footprint_purchase_share_pct"})),
    ]
    write_data_quality("phase3", "Phase 3: share, trend and opportunity metrics", sections,
                       path=L.data_quality, heading=lender_log_heading(L))

    # Console summary
    tr = trend.set_index(["scope", "year"])
    print(f"\n{L.label} share by scope and year (purchase / refinance / all):")
    for (scope, year), r in tr.iterrows():
        print(f"  {scope:9s} {year}: {r['share_purchase']:.2%} / {r['share_refinance']:.2%} / "
              f"{r['share_all']:.2%}   market refi mix {r['market_refi_mix']:.0%}")
    print(f"\nDepth opportunity ({L.footprint_label} tracts, {s.SCORING_YEAR}): "
          f"{footprint_tracts['opportunity_score'].sum():,.0f} loans "
          f"({footprint_tracts['opportunity_score_contestable'].sum():,.0f} without builder lenders)")
    print(f"Expansion gain at {L.expansion_target_share:.0%} ({len(expansion)} non-{L.footprint_label} counties): "
          f"{expansion['expansion_gain'].sum():,.0f} loans")
    print(f"Stability: {in_both} of {TOP_N} tracts in both top 25s; "
          f"largest county rank move {county_move}")
    print(f"Lenders flagged for merger review: {len(flagged)}")


if __name__ == "__main__":
    main()
