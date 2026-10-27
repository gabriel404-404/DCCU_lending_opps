"""Stage 5: households, density, branch distance, population growth and clusters (PRD Appendix A).

Reads the Phase 3 outputs and the Phase 4 raw files, and writes:
  data/processed/branches.csv              DCCU sites in both NCUA snapshots, geocoded
  data/processed/tract_context.csv         every tract: households, density, penetration, distance
  data/processed/share_by_distance.csv     R4: DCCU share by distance band (FOM, statewide, FOM county)
  data/processed/county_context.csv        every county: households, population growth, adjacency
  data/processed/expansion_scorecard.csv   R3a: non-FOM counties, Phase 3 fields plus this context
  data/processed/growth_clusters.csv       R3b: neighboring fast-growing non-FOM counties
plus the checks in data/processed/phase4_checks/ and the Phase 4 section of DATA_QUALITY.md.

Run from the repo root:  python src/05_context.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as s  # noqa: E402
from src.common import dccu_branches, md_table, write_data_quality  # noqa: E402

OUT = s.PROCESSED / "phase4_checks"
SQ_METERS_PER_SQ_MILE = 2_589_988.11
EARTH_RADIUS_MILES = 3958.8
GEOCODE_COLS = ["site_id", "input_address", "match", "match_type", "matched_address",
                "coordinates", "tiger_line_id", "side"]


def band_labels(edges):
    labels = [f"{a:g}-{b:g}" for a, b in zip(edges[:-2], edges[1:-1])]
    return labels + [f"{edges[-2]:g}+"]


# ---------------------------------------------------------------- branches

def load_branches():
    """DCCU's sites in the scoring-year and latest NCUA snapshots, with coordinates and scope."""
    exclusions = pd.read_csv(s.CONFIG / "branch_exclusions.csv", dtype=str).set_index("site_id")
    manual = pd.read_csv(s.CONFIG / "branch_coordinates_manual.csv", dtype=str).set_index("site_id")
    zips = sorted((s.RAW / "ncua").glob("call-report-data-*.zip"))
    y, m = s.NCUA_SCORING_CYCLE
    snapshots = {"scoring_year": f"{y}-{m:02d}", "current": zips[-1].stem.split("data-")[1]}

    frames = []
    for snapshot, cycle in snapshots.items():
        _, b = dccu_branches(s.RAW / "ncua" / f"call-report-data-{cycle}.zip")
        geo = pd.read_csv(s.RAW / "geocode" / f"branches_{cycle}.csv", header=None,
                          names=GEOCODE_COLS, dtype=str)
        b = b.rename(columns={"SiteId": "site_id", "SiteName": "site_name",
                              "PhysicalAddressLine1": "address", "PhysicalAddressCity": "city",
                              "PhysicalAddressStateCode": "state",
                              "PhysicalAddressCountyName2": "ncua_county"})
        b = b.merge(geo[["site_id", "match", "match_type", "coordinates"]], on="site_id", how="left")
        lonlat = b["coordinates"].str.split(",", expand=True)
        b["lon"], b["lat"] = pd.to_numeric(lonlat[0]), pd.to_numeric(lonlat[1])
        b["coord_source"] = np.where(b["lat"].notna(), "census_geocoder", "")
        # Addresses the geocoder can't match get hand-checked coordinates (config, with method).
        fix = b["lat"].isna() & b["site_id"].isin(manual.index)
        b.loc[fix, "lat"] = b.loc[fix, "site_id"].map(manual["lat"]).astype(float)
        b.loc[fix, "lon"] = b.loc[fix, "site_id"].map(manual["lon"]).astype(float)
        b.loc[fix, "coord_source"] = "manual (config)"

        b["exclusion_reason"] = b["site_id"].map(exclusions["reason"]).fillna("")
        b.loc[b["state"] != s.STATE_ABBR, "exclusion_reason"] = "out of state"
        b["in_scope"] = b["exclusion_reason"] == ""
        b["ncua_no_member_services"] = b["MemberServices"] == "0"
        frames.append(b.assign(snapshot=snapshot, cycle=cycle))
    out = pd.concat(frames, ignore_index=True)

    missing = out[out["in_scope"] & out["lat"].isna()]
    if len(missing):
        raise ValueError(f"In-scope branches with no coordinates:\n{missing[['site_id', 'site_name']]}")
    cols = ["snapshot", "cycle", "site_id", "site_name", "address", "city", "state", "ncua_county",
            "in_scope", "exclusion_reason", "ncua_no_member_services", "lat", "lon",
            "coord_source", "match", "match_type"]
    return out[cols], snapshots


def nearest(points_lat, points_lon, branches):
    """Miles to, and name of, the nearest branch for each point (haversine).

    SQL: CROSS JOIN points x branches, then MIN(distance) GROUP BY point.
    """
    lat1, lon1 = np.radians(points_lat)[:, None], np.radians(points_lon)[:, None]
    lat2, lon2 = np.radians(branches["lat"].to_numpy())[None, :], np.radians(branches["lon"].to_numpy())[None, :]
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    miles = 2 * EARTH_RADIUS_MILES * np.arcsin(np.sqrt(a))
    idx = miles.argmin(axis=1)
    return miles.min(axis=1), branches["site_name"].to_numpy()[idx]


# ---------------------------------------------------------------- tracts (R4, R6)

def build_tract_context(tiger, branches):
    tm = pd.read_csv(s.PROCESSED / "tract_metrics.csv", dtype={"census_tract": str, "county_fips": str})
    acs = pd.read_csv(s.PROCESSED / "phase1_checks" / "7_acs_households.csv", dtype={"tract": str})
    hm = pd.read_parquet(s.PROCESSED / f"hmda_ga_{s.SCORING_YEAR}.parquet",
                         columns=["census_tract", "tract_owner_occupied_units"])
    owner = (hm[~hm["census_tract"].isin(["", "NA"])]
             .drop_duplicates("census_tract").set_index("census_tract")["tract_owner_occupied_units"])

    t = tm[["census_tract", "county_fips", "county_name", "fom_flag", "market_all", "market_purchase",
            "market_refinance", "dccu_all", "dccu_purchase", "dccu_refinance", "low_volume"]].copy()
    t = t.merge(tiger[["census_tract", "ALAND", "INTPTLAT", "INTPTLON"]], on="census_tract", how="left")
    t = t.merge(acs[["tract", "households", "households_moe", "flag"]].rename(
        columns={"tract": "census_tract", "flag": "households_flag"}), on="census_tract", how="left")
    t["land_sq_mi"] = t["ALAND"].astype(float) / SQ_METERS_PER_SQ_MILE
    t["household_density"] = t["households"] / t["land_sq_mi"].where(t["land_sq_mi"] > 0)
    t["owner_occupied_units"] = pd.to_numeric(t["census_tract"].map(owner), errors="coerce")
    t["penetration"] = 1000 * t["market_all"] / t["owner_occupied_units"].where(t["owner_occupied_units"] > 0)

    lat, lon = t["INTPTLAT"].astype(float).to_numpy(), t["INTPTLON"].astype(float).to_numpy()
    for snapshot in ["scoring_year", "current"]:
        b = branches[(branches["snapshot"] == snapshot) & branches["in_scope"]]
        t[f"branch_miles_{snapshot}"], t[f"nearest_branch_{snapshot}"] = nearest(lat, lon, b)
    # R4 uses the branches open during the scoring year.
    t["distance_band"] = pd.cut(t["branch_miles_scoring_year"], s.DISTANCE_BANDS, right=False,
                                labels=band_labels(s.DISTANCE_BANDS))
    t["distance_band_detail"] = pd.cut(t["branch_miles_scoring_year"], s.DISTANCE_BANDS_DETAIL,
                                       right=False, labels=band_labels(s.DISTANCE_BANDS_DETAIL))
    return t.drop(columns=["ALAND", "INTPTLAT", "INTPTLON"])


def share_by_distance(t):
    """R4: pooled DCCU share by band (SUM(dccu) / SUM(market), not an average of tract shares)."""
    def agg(df, keys):
        g = df.groupby(keys, observed=True).agg(
            tracts=("census_tract", "size"), households=("households", "sum"),
            market_all=("market_all", "sum"), dccu_all=("dccu_all", "sum"),
            market_purchase=("market_purchase", "sum"), dccu_purchase=("dccu_purchase", "sum"),
            market_refinance=("market_refinance", "sum"), dccu_refinance=("dccu_refinance", "sum"))
        for p in ["all", "purchase", "refinance"]:
            g[f"share_{p}"] = g[f"dccu_{p}"] / g[f"market_{p}"].where(g[f"market_{p}"] > 0)
        return g.reset_index().rename(columns={keys[-1]: "band"})

    fom = t[t["fom_flag"] == 1]
    by_county = agg(fom, ["county_name", "distance_band"])
    # County-adjusted view: is a band above its own county's average? Expected DCCU loans =
    # band market x the county's share (like indirect standardization). This separates
    # proximity from county-level differences such as DCCU's south-side legacy.
    county_share = by_county.groupby("county_name")[["dccu_all", "market_all"]].sum()
    by_county["expected_dccu"] = by_county["market_all"] * by_county["county_name"].map(
        county_share["dccu_all"] / county_share["market_all"])
    adjusted = by_county.groupby("band", observed=True)[["tracts", "market_all", "dccu_all",
                                                        "expected_dccu"]].sum().reset_index()
    adjusted["vs_county_average"] = adjusted["dccu_all"] / adjusted["expected_dccu"]
    parts = [agg(fom, ["distance_band"]).assign(scope="fom"),
             agg(t, ["distance_band_detail"]).assign(scope="statewide"),
             by_county.assign(scope="fom_county"),
             adjusted.assign(scope="fom_county_adjusted")]
    out = pd.concat(parts, ignore_index=True)
    first = ["scope", "county_name", "band"]
    return out[first + [c for c in out.columns if c not in first]]


# ---------------------------------------------------------------- counties (R3a, R3b)

def load_population():
    p = pd.read_csv(s.RAW / "census" / s.PEP_COUNTY_URL.rsplit("/", 1)[1], dtype=str,
                    encoding="latin-1")
    p = p[p["STATE"] == s.STATE_FIPS]
    years = sorted({s.POP_GROWTH_BASE_YEAR, s.POP_RECENT_BASE_YEAR, s.PEP_YEAR})
    cols = {f"POPESTIMATE{y}": f"pop_{y}" for y in years}
    out = p[["SUMLEV", "STATE", "COUNTY", "CTYNAME"] + list(cols)].rename(columns=cols)
    out[list(cols.values())] = out[list(cols.values())].astype(int)
    out["county_fips"] = out["STATE"] + out["COUNTY"]
    return out


def load_adjacency():
    """Georgia county pairs (both directions); out-of-state neighbors are counted and dropped."""
    a = pd.read_csv(s.RAW / "census" / s.ADJACENCY_URL.rsplit("/", 1)[1], sep="|", dtype=str)
    a = a.rename(columns={"County GEOID": "county_fips", "Neighbor GEOID": "neighbor_fips"})
    a = a[a["county_fips"].str.startswith(s.STATE_FIPS) & (a["county_fips"] != a["neighbor_fips"])]
    out_of_state = int((~a["neighbor_fips"].str.startswith(s.STATE_FIPS)).sum())
    return a[a["neighbor_fips"].str.startswith(s.STATE_FIPS)][["county_fips", "neighbor_fips"]], out_of_state


def find_clusters(nodes, pairs):
    """Connected components of the adjacency graph restricted to `nodes` (like a recursive CTE)."""
    nbrs = {n: set() for n in nodes}
    for a, b in pairs[["county_fips", "neighbor_fips"]].itertuples(index=False):
        if a in nbrs and b in nbrs:
            nbrs[a].add(b)
    seen, comps = set(), []
    for n in sorted(nodes):
        if n in seen:
            continue
        stack, comp = [n], set()
        while stack:
            x = stack.pop()
            if x not in comp:
                comp.add(x)
                stack.extend(nbrs[x] - comp)
        seen |= comp
        comps.append(comp)
    return comps


def build_county_context(t, counties, pop, pairs):
    g = t.groupby("county_fips").agg(households=("households", "sum"),
                                     land_sq_mi=("land_sq_mi", "sum"))
    # Household-weighted miles to the nearest current branch: where the typical household is.
    w = t.assign(hh_miles=t["households"] * t["branch_miles_current"]).groupby("county_fips")
    g["branch_miles_hh_weighted"] = w["hh_miles"].sum() / w["households"].sum()
    g["household_density"] = g["households"] / g["land_sq_mi"]
    c = counties[["county_fips", "county_name", "fom_flag", "market_group", "urban_rural_tier"]].merge(
        g.reset_index(), on="county_fips", how="left")
    c = c.merge(pop[pop["SUMLEV"] == "050"].drop(columns=["SUMLEV", "STATE", "COUNTY", "CTYNAME"]),
                on="county_fips", how="left")
    base, recent, end = (f"pop_{y}" for y in [s.POP_GROWTH_BASE_YEAR, s.POP_RECENT_BASE_YEAR, s.PEP_YEAR])
    c["pop_growth"] = c[end] / c[base] - 1
    c["pop_growth_recent"] = c[end] / c[recent] - 1
    state = pop[pop["SUMLEV"] == "040"].iloc[0]
    state_growth = state[end] / state[base] - 1
    c["growing"] = c["pop_growth"] > state_growth
    c["fast_growing"] = c["pop_growth"] > s.CLUSTER_GROWTH_MULTIPLE * state_growth

    fom = set(c.loc[c["fom_flag"] == 1, "county_fips"])
    name = c.set_index("county_fips")["county_name"]
    fom_nbrs = pairs[pairs["neighbor_fips"].isin(fom)].groupby("county_fips")["neighbor_fips"].apply(
        lambda x: ", ".join(sorted(name[x])))
    c["fom_neighbors"] = c["county_fips"].map(fom_nbrs).fillna("")
    c["adjacent_to_fom"] = (c["fom_neighbors"] != "") & (c["fom_flag"] == 0)

    # Growth clusters: 2+ neighboring non-FOM counties, all fast-growing.
    grow = set(c.loc[c["fast_growing"] & (c["fom_flag"] == 0), "county_fips"])
    comps = [comp for comp in find_clusters(grow, pairs) if len(comp) >= 2]
    comps.sort(key=lambda comp: -c.loc[c["county_fips"].isin(comp), end].sum())
    cluster = {f: f"C{i + 1}" for i, comp in enumerate(comps) for f in comp}
    c["growth_cluster"] = c["county_fips"].map(cluster).fillna("")
    return c, state_growth


def build_scorecard(county_ctx):
    e = pd.read_csv(s.PROCESSED / "expansion_counties.csv", dtype={"county_fips": str})
    ctx = county_ctx[["county_fips", "households", "household_density", "land_sq_mi",
                      f"pop_{s.PEP_YEAR}", "pop_growth", "pop_growth_recent", "growing", "fast_growing",
                      "adjacent_to_fom", "fom_neighbors", "branch_miles_hh_weighted", "growth_cluster"]]
    return e.merge(ctx, on="county_fips", how="left")


def build_clusters(scorecard):
    end, base = f"pop_{s.PEP_YEAR}", f"pop_{s.POP_GROWTH_BASE_YEAR}"
    sc = scorecard[scorecard["growth_cluster"] != ""].copy()
    sc[base] = sc[end] / (1 + sc["pop_growth"])
    g = sc.groupby("growth_cluster").agg(
        counties=("county_name", "size"), county_names=("county_name", lambda x: ", ".join(sorted(x))),
        market_groups=("market_group", lambda x: "; ".join(sorted(x.dropna().unique()))),
        touches_fom=("adjacent_to_fom", "any"), **{end: (end, "sum"), base: (base, "sum")},
        market_all=("market_all", "sum"), expansion_gain=("expansion_gain", "sum"))
    g["pop_growth"] = g[end] / g[base] - 1
    g[base] = g[base].round().astype(int)
    return g.sort_values("expansion_gain", ascending=False).reset_index()


# ---------------------------------------------------------------- main

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    counties = pd.read_csv(s.CONFIG / "ga_counties.csv", dtype=str)
    counties["fom_flag"] = counties["fom_flag"].astype(int)
    tiger = gpd.read_file(s.RAW / "tiger" / "tl_2024_13_tract.zip").rename(columns={"GEOID": "census_tract"})

    branches, snapshots = load_branches()
    tracts = build_tract_context(tiger, branches)
    bands = share_by_distance(tracts)
    pop = load_population()
    pairs, out_of_state = load_adjacency()
    county_ctx, state_growth = build_county_context(tracts, counties, pop, pairs)
    scorecard = build_scorecard(county_ctx)
    clusters = build_clusters(scorecard)

    # ---- checks
    inscope = branches[branches["in_scope"] & (branches["state"] == s.STATE_ABBR)]
    # 1. Each branch's tract (point in polygon) gives its county; compare with NCUA's county.
    pts = gpd.GeoDataFrame(inscope, geometry=gpd.points_from_xy(inscope["lon"], inscope["lat"]),
                           crs="EPSG:4326").to_crs(tiger.crs)
    located = gpd.sjoin(pts, tiger[["census_tract", "COUNTYFP", "geometry"]], how="left",
                        predicate="within")
    name = counties.set_index("county_fips")["county_name"]
    located["geocoded_county"] = (s.STATE_FIPS + located["COUNTYFP"]).map(name)
    located["county_match"] = located["geocoded_county"] == located["ncua_county"]
    tract_miles = tracts.set_index("census_tract")["branch_miles_scoring_year"]
    located["own_tract_miles"] = located["census_tract"].map(tract_miles)
    geocode_check = located[["snapshot", "site_id", "site_name", "ncua_county", "geocoded_county",
                             "county_match", "coord_source", "match_type", "census_tract",
                             "own_tract_miles"]]
    # Strict for geocoder matches; hand-interpolated points can sit on a county-line road.
    bad = geocode_check[~geocode_check["county_match"] & (geocode_check["coord_source"] == "census_geocoder")]
    if len(bad):
        raise ValueError(f"Branch county mismatch:\n{bad}")
    manual_off = geocode_check[~geocode_check["county_match"] & (geocode_check["snapshot"] == "current")]
    # 2. Branch changes between snapshots.
    ids = {k: set(branches.loc[(branches["snapshot"] == k) & branches["in_scope"], "site_id"])
           for k in snapshots}
    opened = sorted(ids["current"] - ids["scoring_year"])
    closed = sorted(ids["scoring_year"] - ids["current"])
    # 3-5. Tract coverage, penetration, distance.
    coverage = pd.DataFrame([
        {"check": "tracts", "count": len(tracts)},
        {"check": "missing households (no ACS row)", "count": int(tracts["households"].isna().sum())},
        {"check": "zero households", "count": int((tracts["households"] == 0).sum())},
        {"check": "high MOE households (CV > 30%)", "count": int((tracts["households_flag"] == "high_moe").sum())},
        {"check": "zero land area (density blank)", "count": int((tracts["land_sq_mi"] == 0).sum())},
        {"check": "missing or zero owner-occupied units (penetration blank)",
         "count": int(tracts["penetration"].isna().sum())},
        {"check": "missing distance", "count": int(tracts["branch_miles_scoring_year"].isna().sum())},
    ])
    fom_t = tracts[tracts["fom_flag"] == 1]
    # 6. Population: counties sum to the state row.
    pop_check = pd.DataFrame([{"year": y, "state_row": int(pop.loc[pop["SUMLEV"] == "040", f"pop_{y}"].iloc[0]),
                               "county_sum": int(pop.loc[pop["SUMLEV"] == "050", f"pop_{y}"].sum())}
                              for y in sorted({s.POP_GROWTH_BASE_YEAR, s.POP_RECENT_BASE_YEAR, s.PEP_YEAR})])
    pop_check["match"] = pop_check["state_row"] == pop_check["county_sum"]
    # 7. Adjacency: symmetric, every county has a neighbor.
    pair_set = set(map(tuple, pairs.to_numpy()))
    asymmetric = sum((b, a) not in pair_set for a, b in pair_set)
    no_neighbor = sorted(set(counties["county_fips"]) - set(pairs["county_fips"]))
    # 8. Scorecard completeness.
    key_cols = ["households", "household_density", f"pop_{s.PEP_YEAR}", "pop_growth",
                "branch_miles_hh_weighted"]
    blanks = int(scorecard[key_cols].isna().any(axis=1).sum())
    gain_phase3 = pd.read_csv(s.PROCESSED / "expansion_counties.csv")["expansion_gain"].sum()
    if len(scorecard) != 139 or blanks or not np.isclose(scorecard["expansion_gain"].sum(), gain_phase3):
        raise ValueError("Expansion scorecard is incomplete or doesn't match Phase 3")

    # ---- write
    branches.to_csv(s.PROCESSED / "branches.csv", index=False)
    for name_, df in [("tract_context", tracts), ("share_by_distance", bands),
                      ("county_context", county_ctx), ("expansion_scorecard", scorecard),
                      ("growth_clusters", clusters)]:
        df.round(6).to_csv(s.PROCESSED / f"{name_}.csv", index=False)
    for name_, df in [("1_branch_geocoding", geocode_check), ("3_tract_coverage", coverage),
                      ("6_population_totals", pop_check)]:
        df.round(4).to_csv(OUT / f"{name_}.csv", index=False)

    # ---- DATA_QUALITY.md
    current = branches[branches["snapshot"] == "current"]
    excluded = current[~current["in_scope"]]
    no_services = current.loc[current["in_scope"] & current["ncua_no_member_services"], "site_name"]
    band_fom = bands[bands["scope"] == "fom"][["band", "tracts", "households", "market_all", "dccu_all",
                                              "share_all", "share_purchase"]]
    fom_dist = fom_t["distance_band"].value_counts(sort=False).rename_axis("band").reset_index(name="fom_tracts")
    sections = [
        f"### 1. Branches and geocoding\nNCUA snapshots: scoring year `{snapshots['scoring_year']}` "
        f"(share by distance) and current `{snapshots['current']}` (expansion scorecard). "
        f"In-scope Georgia branches: **{len(ids['scoring_year'])}** and **{len(ids['current'])}**. "
        "Excluded sites (`config/branch_exclusions.csv`, plus out-of-state):\n\n"
        + md_table(excluded[["site_id", "site_name", "state", "exclusion_reason"]])
        + "\n\nThe Census Geocoder matched every in-scope branch except those below, whose "
        "coordinates come from `config/branch_coordinates_manual.csv` (interpolated between two "
        "matched house numbers on the same street; error a few hundred meters).\n\n"
        + md_table(current[current["coord_source"] == "manual (config)"]
                   [["site_id", "site_name", "address", "lat", "lon"]])
        + "\n\nEvery geocoder-matched branch falls in the county NCUA lists. Hand-placed points "
        "outside NCUA's county (they sit on a county-line road; distances are unaffected): "
        + (", ".join(f"{r.site_name} (NCUA {r.ncua_county}, point in {r.geocoded_county})"
                     for r in manual_off.itertuples()) or "none")
        + f". The farthest any branch's tract internal point is from its nearest branch is "
        f"{geocode_check['own_tract_miles'].max():.2f} mi. "
        "Branches flagged `ncua_no_member_services` but kept: "
        + (", ".join(no_services) or "none") + ".",
        f"### 2. Branch changes between snapshots\nOpened: {', '.join(opened) or 'none'}. "
        f"Closed: {', '.join(closed) or 'none'}.",
        "### 3-5. Tract coverage, penetration and distance\nNo tract is dropped; gaps are flags or "
        "blanks.\n\n" + md_table(coverage)
        + f"\n\nFOM tracts by distance band ({snapshots['scoring_year']} branches); farthest FOM "
        f"tract: {fom_t['branch_miles_scoring_year'].max():.1f} mi.\n\n" + md_table(fom_dist)
        + "\n\nDCCU share by band, FOM tracts (pooled: sum of DCCU loans / sum of market loans):\n\n"
        + md_table(band_fom.round(4))
        + "\n\nCounty-adjusted (`vs_county_average` = DCCU loans / loans expected at the county's "
        "own share). Most of the raw gradient is between counties, not proximity:\n\n"
        + md_table(bands[bands["scope"] == "fom_county_adjusted"][
            ["band", "tracts", "market_all", "dccu_all", "expected_dccu", "vs_county_average"]].round(2)),
        f"### 6. Population estimates (Vintage {s.PEP_YEAR})\nCounty totals sum to the state row "
        f"in every year used. Georgia grew **{state_growth:.2%}** from July {s.POP_GROWTH_BASE_YEAR} "
        f"to July {s.PEP_YEAR}; counties above that are `growing`, and counties above "
        f"{s.CLUSTER_GROWTH_MULTIPLE:g}x that ({s.CLUSTER_GROWTH_MULTIPLE * state_growth:.2%}) are "
        "`fast_growing` (the bar for named clusters).\n\n" + md_table(pop_check),
        f"### 7. County adjacency\n{len(pairs):,} Georgia county pairs (both directions); "
        f"{out_of_state} out-of-state neighbor pairs dropped. Asymmetric pairs: **{asymmetric}**. "
        f"Counties with no Georgia neighbor: {', '.join(no_neighbor) or 'none'}.",
        f"### 8. Expansion scorecard\n{len(scorecard)} non-FOM counties, no blanks in "
        f"{', '.join(key_cols)}; expansion gain total matches Phase 3 "
        f"({scorecard['expansion_gain'].sum():,.0f} loans). Growth clusters (2+ neighboring "
        f"fast-growing non-FOM counties): **{len(clusters)}**.\n\n"
        + md_table(clusters[["growth_cluster", "counties", "county_names", "touches_fom",
                             "pop_growth", "expansion_gain"]].round(3)),
    ]
    write_data_quality("phase4", "Phase 4: households, density, branch distance and growth", sections)

    # ---- console summary
    print(f"Branches in scope: {len(ids['scoring_year'])} ({snapshots['scoring_year']}), "
          f"{len(ids['current'])} ({snapshots['current']}); opened {opened}, closed {closed}")
    print("\nFOM share by distance band:")
    print(band_fom.to_string(index=False))
    print("\nStatewide share by distance band:")
    print(bands[bands["scope"] == "statewide"][["band", "tracts", "market_all", "dccu_all", "share_all"]]
          .to_string(index=False))
    print(f"\nGeorgia population growth {s.POP_GROWTH_BASE_YEAR}-{s.PEP_YEAR}: {state_growth:.2%}; "
          f"growing non-FOM counties: {int((county_ctx['growing'] & (county_ctx['fom_flag'] == 0)).sum())}, "
          f"fast-growing: {int((county_ctx['fast_growing'] & (county_ctx['fom_flag'] == 0)).sum())}; "
          f"clusters: {len(clusters)}")


if __name__ == "__main__":
    main()
