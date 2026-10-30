"""Stage 7: maps, charts, final tables and key numbers (PRD R1-R7).

Reads earlier stages' outputs and writes everything in outputs/:
  map_footprint_share.png        R1: footprint tracts by share vs. the footprint average
  map_footprint_opportunity.png  R1, R2: footprint tracts by opportunity score, top 25 numbered
  map_statewide.png              R1, R3b: county share, and expansion gain with growth clusters
  mortgage_map.html              R1, R6: interactive map (share, opportunity, density, expansion)
  chart_share_trend.png          R5
  chart_share_by_distance.png    R4
  chart_depth_vs_expansion.png   R3a: depth at the three benchmark rungs vs. expansion
  opportunity_top25.csv, depth_by_county.csv, expansion_scorecard.csv, growth_clusters.csv
  key_numbers.csv                every number FINDINGS.md quotes, with its source file
plus the "Phase 5: map, table and findings" section of DATA_QUALITY.md, which also checks
FINDINGS.md (length, and any number in it that isn't in key_numbers.csv).

Lender-neutral: names and labels come from config/settings.py. Colors follow the reference
palette of the data-viz guidance (surfaces, ink, the blue ramp, categorical slots 1-2).
Run from the repo root:  python src/07_outputs.py
"""

import json
import re
import sys
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # draw to files, no window
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as s  # noqa: E402
from src.common import md_table, neutral, read_processed, write_data_quality  # noqa: E402

OUT = s.OUTPUTS
FINDINGS = s.ROOT / "FINDINGS.md"
FINDINGS_WORD_LIMIT = 550  # about one page
TOP_N = 25

# ---------------------------------------------------------------- palette

SURFACE, PLANE = "#fcfcfb", "#f9f9f7"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NEUTRAL = "#e1e0d9", "#c3c2b7", "#f0efec"
BLUE = {250: "#86b6ef", 350: "#5598e7", 400: "#3987e5", 450: "#2a78d6", 550: "#1c5cab",
        650: "#104281", 700: "#0d366b"}
SLOT_1, SLOT_2 = "#2a78d6", "#eb6834"  # categorical slots 1-2 (blue, orange)
RED_HUE = "#e34948"                    # categorical red: the hue of the diverging "below" arm


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def to_oklch(hexcolor):
    r, g, b = (_lin(int(hexcolor[i:i + 2], 16) / 255) for i in (1, 3, 5))
    l_ = np.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = np.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = np.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, np.hypot(a, bb), np.arctan2(bb, a)


def from_oklch(L, C, h):
    """OKLCH -> hex, lowering chroma until the color fits in sRGB."""
    for c in np.linspace(C, 0, 60):
        a, b = c * np.cos(h), c * np.sin(h)
        l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        rgb = [4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
               -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
               -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_]
        if all(-1e-6 <= v <= 1 + 1e-6 for v in rgb):
            return "#" + "".join(f"{round(255 * _srgb(min(max(v, 0.0), 1.0))):02x}" for v in rgb)
    raise ValueError("no in-gamut color")


def matched(hue_hex, step_hex):
    """A step in hue_hex's hue with the same OKLCH lightness and chroma as a blue ramp step."""
    L, C, _ = to_oklch(step_hex)
    return from_oklch(L, C, to_oklch(hue_hex)[2])


# Diverging around the footprint average: red arm below, blue arm above, gray midpoint.
DIVERGING = [matched(RED_HUE, BLUE[550]), matched(RED_HUE, BLUE[250]), NEUTRAL, BLUE[250], BLUE[550]]
DIV_EDGES = [0.5, 0.9, 1.1, 2.0]
DIV_LABELS = ["Under 0.5x average (incl. no loans)", "0.5-0.9x", "About average (0.9-1.1x)",
              "1.1-2x", "Over 2x average"]
# Sequential (one hue, light -> dark), binned, so the lightest step is 250 (clears 2:1 on the
# surface). Expansion is a second magnitude on the same page, so it takes orange.
OPP_COLORS = [NEUTRAL, BLUE[250], BLUE[400], BLUE[550], BLUE[700]]
OPP_EDGES = [0.5, 1.0, 2.0]
OPP_LABELS = ["None (at or above average)", "Under 0.5 loans a year", "0.5-1", "1-2", "2 or more"]
EXP_COLORS = [matched(SLOT_2, BLUE[k]) for k in (250, 350, 450, 550, 650)]
EXP_EDGES = [2, 5, 10, 20]
EXP_LABELS = ["Under 2 loans a year", "2-5", "5-10", "10-20", "20 or more"]
DEN_COLORS = [BLUE[k] for k in (250, 350, 450, 550, 650)]
DEN_EDGES = [100, 500, 1000, 2000]
DEN_LABELS = ["Under 100 households / sq mi", "100-500", "500-1,000", "1,000-2,000", "2,000 or more"]


def classes(values, edges, colors, zero_class=False):
    """Color per value from bin edges. zero_class: exact zeros get colors[0], the rest shift up."""
    v = np.nan_to_num(np.asarray(values, dtype=float), nan=0.0)
    idx = np.digitize(v, edges)
    if zero_class:
        idx = np.where(v > 0, idx + 1, 0)
    return np.array(colors)[idx]


def halo(width=2.5):
    return [pe.withStroke(linewidth=width, foreground=SURFACE)]


def style():
    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9, "text.color": INK,
        "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK_2,
        "axes.titlecolor": INK, "axes.titlesize": 10, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK_2,
        "ytick.labelcolor": INK_2, "legend.frameon": False, "legend.fontsize": 8.5})


def header(fig, title, subtitle, note=None):
    """Title and subtitle at fixed distances (in inches) from the top, whatever the figure height."""
    h = fig.get_figheight()
    fig.text(0.01, 1 - 0.05 / h, title, ha="left", va="top", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.01, 1 - 0.36 / h, subtitle, ha="left", va="top", fontsize=9.5, color=INK_2)
    if note:
        fig.text(0.01, 0.005, note, ha="left", va="bottom", fontsize=7.5, color=MUTED)


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


# ---------------------------------------------------------------- data

def load():
    d = {}
    d["tracts"] = read_processed("tract_metrics", dtype={"census_tract": str, "county_fips": str})
    ctx = read_processed("tract_context", dtype={"census_tract": str, "county_fips": str})
    d["tracts"] = d["tracts"].merge(ctx[["census_tract", "households", "household_density", "penetration",
                                        "branch_miles_scoring_year", "nearest_branch_scoring_year",
                                        "distance_band"]], on="census_tract", how="left")
    d["county_year"] = read_processed("county_year_metrics", dtype={"county_fips": str})
    d["trend"] = read_processed("trend_summary")
    d["lender_trend"] = read_processed("lender_trend_fom")
    d["bands"] = read_processed("share_by_distance")
    d["depth"] = read_processed("depth_by_county", dtype={"county_fips": str})
    d["ladder"] = read_processed("benchmark_ladder")
    d["ladder_county"] = read_processed("depth_ladder_by_county", dtype={"county_fips": str})
    d["structure"] = read_processed("market_structure")
    d["peers"] = read_processed("peer_comparison")
    d["scorecard"] = read_processed("expansion_scorecard", dtype={"county_fips": str})
    d["clusters"] = read_processed("growth_clusters")
    d["county_ctx"] = read_processed("county_context", dtype={"county_fips": str})
    d["top25"] = read_processed("opportunity_top25", dtype={"census_tract": str})
    b = read_processed("branches", dtype={"site_id": str})
    d["branches"] = b[(b["snapshot"] == "current") & b["in_scope"]]
    d["counties"] = neutral(pd.read_csv(s.CONFIG / "ga_counties.csv", dtype={"county_fips": str}))
    d["market_size"] = pd.read_csv(s.PROCESSED / "phase2_checks" / "market_size.csv")
    d["recon"] = pd.read_csv(s.PROCESSED / "phase2_checks" / "dccu_api_reconciliation.csv")
    builders = pd.read_csv(s.CONFIG / "builder_lenders.csv", dtype=str)
    d["builders_included"] = int((builders["include"] == "1").sum())

    cur = d["county_year"][d["county_year"]["year"] == s.SCORING_YEAR]
    fp = cur[cur["footprint_flag"] == 1]
    d["base"] = fp["lender_all"].sum() / fp["market_all"].sum()

    tiger = gpd.read_file(s.RAW / "tiger" / "tl_2024_13_tract.zip")[["GEOID", "geometry"]]
    tiger = tiger.rename(columns={"GEOID": "census_tract"}).to_crs(5070)  # equal-area, for drawing
    d["tract_geo"] = tiger.merge(d["tracts"], on="census_tract", how="left")
    county_geo = d["tract_geo"].dissolve(by="county_fips", as_index=False)[["county_fips", "geometry"]]
    county_geo = county_geo.merge(d["counties"][["county_fips", "county_name", "footprint_flag"]],
                                  on="county_fips")
    county_geo = county_geo.merge(cur[["county_fips", "market_all", "lender_all", "share_all"]],
                                  on="county_fips", how="left")
    county_geo = county_geo.merge(d["scorecard"][["county_fips", "expansion_gain", "growth_cluster"]],
                                  on="county_fips", how="left")
    d["county_geo"] = county_geo
    d["branch_geo"] = gpd.GeoDataFrame(
        d["branches"], geometry=gpd.points_from_xy(d["branches"]["lon"], d["branches"]["lat"]),
        crs="EPSG:4326").to_crs(5070)
    return d


# ---------------------------------------------------------------- static maps (R1, R2, R3b)

def footprint_frame(ax, d):
    """Context counties, footprint extent and county labels shared by the two footprint maps."""
    cg = d["county_geo"]
    fp = cg[cg["footprint_flag"] == 1]
    xmin, ymin, xmax, ymax = fp.total_bounds
    pad = 0.04 * max(xmax - xmin, ymax - ymin)
    cg.plot(ax=ax, color=SURFACE, edgecolor=GRID, linewidth=0.6, zorder=0)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_axis_off()
    return fp


def footprint_overlays(ax, d, fp):
    fp.boundary.plot(ax=ax, color=INK_2, linewidth=0.7, zorder=3)
    for _, r in fp.iterrows():
        p = r.geometry.representative_point()
        ax.text(p.x, p.y, r["county_name"], fontsize=6.5, color=INK_2, ha="center", va="center",
                zorder=6, path_effects=halo())
    d["branch_geo"].plot(ax=ax, color=INK, markersize=12, edgecolor=SURFACE, linewidth=0.8, zorder=5)


def legend_below(ax, handles, ncol=3, title=None):
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=ncol,
              title=title, title_fontsize=8.5, handlelength=1.2, columnspacing=1.2)


def swatches(colors, labels):
    return [Patch(facecolor=c, edgecolor=AXIS, linewidth=0.5, label=lab) for c, lab in zip(colors, labels)]


def branch_handle(label):
    return Line2D([], [], marker="o", linestyle="", markersize=5, markerfacecolor=INK,
                  markeredgecolor=SURFACE, label=label)


def map_footprint_share(d):
    fig, ax = plt.subplots(figsize=(8.5, 9.6))
    fp = footprint_frame(ax, d)
    t = d["tract_geo"][d["tract_geo"]["footprint_flag"] == 1]
    colors = classes(t["share_all"] / d["base"], DIV_EDGES, DIVERGING)
    colors = np.where(t["low_volume"], SURFACE, colors)
    t.plot(ax=ax, color=colors, edgecolor=SURFACE, linewidth=0.15, zorder=1)
    t[t["low_volume"]].plot(ax=ax, facecolor="none", edgecolor=GRID, linewidth=0.3, zorder=2)
    footprint_overlays(ax, d, fp)
    handles = swatches(DIVERGING, DIV_LABELS) + [
        Patch(facecolor=SURFACE, edgecolor=AXIS, linewidth=0.5,
              label=f"Fewer than {s.LOW_VOLUME_THRESHOLD} market loans (not shaded)"),
        branch_handle(f"{s.LENDER_LABEL} branch")]
    legend_below(ax, handles, ncol=2, title=f"{s.LENDER_LABEL} share vs. its {s.FOOTPRINT_LABEL} "
                                             f"average ({d['base']:.2%})")
    header(fig, f"{s.LENDER_LABEL} share of {s.SCORING_YEAR} mortgage originations, by tract",
           f"{s.FOOTPRINT_LABEL} counties. Red: below {s.LENDER_LABEL}'s own average; blue: above it.",
           "Source: HMDA (CFPB), conventional first-lien purchase and refinance originations, all "
           "lenders; Census TIGER 2024 tracts; NCUA branch list.")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.17)
    save(fig, "map_footprint_share.png")
    return len(t), int(t["low_volume"].sum())


def map_footprint_opportunity(d):
    fig, ax = plt.subplots(figsize=(8.5, 9.6))
    fp = footprint_frame(ax, d)
    t = d["tract_geo"][d["tract_geo"]["footprint_flag"] == 1]
    t.plot(ax=ax, color=classes(t["opportunity_score"], OPP_EDGES, OPP_COLORS, zero_class=True),
           edgecolor=SURFACE, linewidth=0.15, zorder=1)
    footprint_overlays(ax, d, fp)
    top = t[t["opportunity_rank"] <= TOP_N]
    for _, r in top.iterrows():
        p = r.geometry.representative_point()
        ax.text(p.x, p.y, str(int(r["opportunity_rank"])), fontsize=7, color=INK, ha="center",
                va="center", fontweight="bold" if r["stable_top25"] else "normal", zorder=7,
                path_effects=halo(2.8))
    handles = swatches(OPP_COLORS, OPP_LABELS) + [branch_handle(f"{s.LENDER_LABEL} branch")]
    legend_below(ax, handles, ncol=3, title="Loans a year gained if the tract reached the "
                                            f"{s.FOOTPRINT_LABEL} average")
    header(fig, f"Where {s.LENDER_LABEL} is below its own {s.FOOTPRINT_LABEL} average, by tract",
           f"Numbers: the top {TOP_N} tracts by opportunity score ({s.SCORING_YEAR}). Bold: also top "
           f"{TOP_N} using {s.SCORING_YEAR - 1}-{s.SCORING_YEAR} share (stable).",
           "Opportunity score = tract market originations x the gap to the footprint average. "
           "Source: HMDA (CFPB), Census TIGER 2024, NCUA.")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.17)
    save(fig, "map_footprint_opportunity.png")
    return len(t)


def map_statewide(d):
    cg = d["county_geo"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 8.2))
    for ax in (a1, a2):
        ax.set_axis_off()
    low = cg["market_all"] < s.LOW_VOLUME_THRESHOLD
    colors = np.where(low, SURFACE, classes(cg["share_all"] / d["base"], DIV_EDGES, DIVERGING))
    cg.plot(ax=a1, color=colors, edgecolor=SURFACE, linewidth=0.4)
    cg[low].plot(ax=a1, facecolor="none", edgecolor=AXIS, linewidth=0.5)
    cg[cg["footprint_flag"] == 1].dissolve().boundary.plot(ax=a1, color=INK, linewidth=1.0)
    a1.set_title(f"{s.LENDER_LABEL} share by county vs. its {s.FOOTPRINT_LABEL} average", pad=4)
    legend_below(a1, swatches(DIVERGING, DIV_LABELS) + [
        Patch(facecolor=SURFACE, edgecolor=AXIS, linewidth=0.5,
              label=f"Fewer than {s.LOW_VOLUME_THRESHOLD} market loans (not shaded)"),
        Line2D([], [], color=INK, linewidth=1.0, label=f"{s.FOOTPRINT_LABEL} boundary")], ncol=2)

    outside = cg[cg["footprint_flag"] == 0]
    outside.plot(ax=a2, color=classes(outside["expansion_gain"], EXP_EDGES, EXP_COLORS),
                 edgecolor=SURFACE, linewidth=0.4)
    cg[cg["footprint_flag"] == 1].plot(ax=a2, color=AXIS, edgecolor=SURFACE, linewidth=0.4)
    named = outside[outside["growth_cluster"].fillna("") != ""]
    if len(named):
        groups = named.dissolve(by="growth_cluster", as_index=False)
        groups.boundary.plot(ax=a2, color=INK, linewidth=1.3)
        for _, r in groups.iterrows():
            p = r.geometry.representative_point()
            a2.text(p.x, p.y, r["growth_cluster"], fontsize=8.5, fontweight="bold", color=INK,
                    ha="center", va="center", path_effects=halo(3))
    for _, r in outside.nlargest(3, "expansion_gain").iterrows():
        p = r.geometry.representative_point()
        a2.text(p.x, p.y, f"{r['county_name']}\n{r['expansion_gain']:.0f}", fontsize=7, color=INK,
                ha="center", va="center", path_effects=halo(2.5))
    a2.set_title(f"Loans a year if {s.LENDER_LABEL} reached {s.EXPANSION_TARGET_SHARE:.0%} in a new county",
                 pad=4)
    legend_below(a2, swatches(EXP_COLORS, EXP_LABELS) + [
        Patch(facecolor=AXIS, edgecolor=AXIS, label=f"Current {s.FOOTPRINT_LABEL}"),
        Line2D([], [], color=INK, linewidth=1.3, label="Growth cluster (fast-growing neighbors)")], ncol=2)
    header(fig, f"{s.LENDER_LABEL} across the state: share today, and the expansion upside",
           f"{s.SCORING_YEAR}. Expansion gain is an upper bound: new counties take years to reach "
           "the footprint's share.",
           f"Source: HMDA (CFPB); Census population estimates (Vintage {s.PEP_YEAR}) and county adjacency. "
           f"Growth cluster = neighboring non-footprint counties all growing faster than "
           f"{s.CLUSTER_GROWTH_MULTIPLE:g}x the state's rate.")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.87, bottom=0.17, wspace=0.05)
    save(fig, "map_statewide.png")


# ---------------------------------------------------------------- interactive map (R1, R6)

def rounded_geojson(gdf, digits=4):  # 4 decimals of a degree is about 10 m
    data = json.loads(gdf.to_json())

    def rnd(x):
        return [rnd(v) for v in x] if isinstance(x, list) else round(x, digits)
    for f in data["features"]:
        f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
    return data


def fmt(v, spec, missing="n/a"):
    return missing if pd.isna(v) else format(v, spec)


def html_map(d):
    t = d["tract_geo"].to_crs(4326)
    # Simplify for the browser: about 40 m inside the footprint, 120 m elsewhere.
    inside = t["footprint_flag"] == 1
    t["geometry"] = t.geometry.simplify(0.0012, preserve_topology=True).where(
        ~inside, t.geometry.simplify(0.0004, preserve_topology=True))
    t["Tract"] = t["census_tract"]
    t["County"] = t["county_name"]
    t["Market loans"] = t["market_all"].map(lambda v: fmt(v, ",.0f"))
    t[f"{s.LENDER_LABEL} loans"] = t["lender_all"].map(lambda v: fmt(v, ",.0f"))
    t[f"{s.LENDER_LABEL} share"] = t["share_all"].map(lambda v: fmt(v, ".1%"))
    t["vs. average"] = (t["share_all"] / d["base"]).map(lambda v: fmt(v, ".2f") + "x" if pd.notna(v) else "n/a")
    t["Opportunity"] = t["opportunity_score"].map(lambda v: fmt(v, ".1f", "outside footprint"))
    t["Rank"] = t["opportunity_rank"].map(lambda v: fmt(v, ".0f", "-"))
    t["Households"] = t["households"].map(lambda v: fmt(v, ",.0f"))
    t["Households / sq mi"] = t["household_density"].map(lambda v: fmt(v, ",.0f"))
    t["Loans per 1,000 owner homes"] = t["penetration"].map(lambda v: fmt(v, ".0f"))
    t["Nearest branch"] = t["nearest_branch_scoring_year"]
    t["Miles"] = t["branch_miles_scoring_year"].map(lambda v: fmt(v, ".1f"))
    tip = ["Tract", "County", "Market loans", f"{s.LENDER_LABEL} loans", f"{s.LENDER_LABEL} share",
           "vs. average", "Opportunity", "Rank", "Households", "Households / sq mi",
           "Loans per 1,000 owner homes", "Nearest branch", "Miles"]

    share = classes(t["share_all"] / d["base"], DIV_EDGES, DIVERGING)
    t["fill_share"] = np.where(t["low_volume"], SURFACE, share)
    t["fill_opp"] = classes(t["opportunity_score"], OPP_EDGES, OPP_COLORS, zero_class=True)
    t["fill_density"] = classes(t["household_density"], DEN_EDGES, DEN_COLORS)

    m = folium.Map(location=[33.85, -84.35], zoom_start=9, tiles=None, control_scale=True)
    # No-key basemap; a commercial product would need its own basemap license (productize phase).
    folium.TileLayer("Esri.WorldGrayCanvas", name="Base map", control=False).add_to(m)

    def layer(name, gdf, fill, fields, show):
        group = folium.FeatureGroup(name=name, overlay=False, show=show)
        folium.GeoJson(
            rounded_geojson(gdf[fields + [fill, "geometry"]]),
            style_function=lambda f: {"fillColor": f["properties"][fill], "color": SURFACE,
                                      "weight": 0.3, "fillOpacity": 0.78},
            highlight_function=lambda f: {"weight": 2, "color": INK},
            tooltip=folium.GeoJsonTooltip(fields=fields, sticky=True)).add_to(group)
        group.add_to(m)

    layer(f"{s.LENDER_LABEL} share vs. {s.FOOTPRINT_LABEL} average", t, "fill_share", tip, True)
    layer("Opportunity score (footprint tracts)", t[t["footprint_flag"] == 1], "fill_opp", tip, False)
    layer("Household density (footprint tracts)", t[t["footprint_flag"] == 1], "fill_density", tip, False)

    c = d["county_geo"].to_crs(4326)
    c["geometry"] = c.geometry.simplify(0.0008, preserve_topology=True)
    c["County"] = c["county_name"]
    c["In footprint"] = np.where(c["footprint_flag"] == 1, "yes", "no")
    c[f"{s.LENDER_LABEL} share"] = c["share_all"].map(lambda v: fmt(v, ".2%"))
    c[f"Gain at {s.EXPANSION_TARGET_SHARE:.0%}"] = c["expansion_gain"].map(lambda v: fmt(v, ".1f", "-"))
    c["Growth cluster"] = c["growth_cluster"].fillna("")
    c["fill_exp"] = np.where(c["footprint_flag"] == 1, AXIS,
                             classes(c["expansion_gain"], EXP_EDGES, EXP_COLORS))
    layer(f"Expansion gain at {s.EXPANSION_TARGET_SHARE:.0%} (counties)", c, "fill_exp",
          ["County", "In footprint", f"{s.LENDER_LABEL} share", f"Gain at {s.EXPANSION_TARGET_SHARE:.0%}",
           "Growth cluster"], False)

    lines = folium.FeatureGroup(name="County lines", overlay=True, show=True)
    # Lines only (no fill), so hovering reaches the tract layer underneath.
    folium.GeoJson(rounded_geojson(c[["county_name", "geometry"]]),
                   style_function=lambda f: {"fill": False, "color": INK_2, "weight": 0.7}).add_to(lines)
    lines.add_to(m)
    branches = folium.FeatureGroup(name=f"{s.LENDER_LABEL} branches", overlay=True, show=True)
    for _, b in d["branches"].iterrows():
        folium.CircleMarker([b["lat"], b["lon"]], radius=4, color=SURFACE, weight=1.5, fill=True,
                            fill_color=INK, fill_opacity=1, tooltip=b["site_name"]).add_to(branches)
    branches.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    def block(title, colors, labels):
        rows = "".join(f'<div><span style="display:inline-block;width:12px;height:12px;'
                       f'background:{col};border:1px solid {AXIS};margin-right:6px;vertical-align:-2px">'
                       f'</span>{lab}</div>' for col, lab in zip(colors, labels))
        return f'<div style="margin-top:6px;font-weight:600">{title}</div>{rows}'
    legend = (
        f'<div style="position:fixed;bottom:24px;left:12px;z-index:9999;background:{SURFACE};'
        f'color:{INK};padding:10px 12px;border-radius:6px;font:12px system-ui,-apple-system,'
        f'\'Segoe UI\',sans-serif;box-shadow:0 1px 4px rgba(11,11,11,0.15);max-width:260px">'
        f'<div style="font-weight:700">{s.LENDER_LABEL} mortgage map, {s.SCORING_YEAR}</div>'
        f'<div style="color:{INK_2}">Hover a tract or county for its numbers.</div>'
        + block(f"Share vs. {s.FOOTPRINT_LABEL} average ({d['base']:.2%})", DIVERGING + [SURFACE],
                DIV_LABELS + [f"Fewer than {s.LOW_VOLUME_THRESHOLD} market loans"])
        + block("Opportunity score", OPP_COLORS, OPP_LABELS)
        + block("Household density", DEN_COLORS, DEN_LABELS)
        + block(f"Expansion gain at {s.EXPANSION_TARGET_SHARE:.0%}", EXP_COLORS + [AXIS],
                EXP_LABELS + [f"Current {s.FOOTPRINT_LABEL}"])
        + "</div>")
    m.get_root().html.add_child(folium.Element(legend))
    m.save(str(OUT / "mortgage_map.html"))
    return {"share": len(t), "opportunity": int((t["footprint_flag"] == 1).sum()), "density": int((t["footprint_flag"] == 1).sum()),
            "counties": len(c), "mb": (OUT / "mortgage_map.html").stat().st_size / 1e6}


# ---------------------------------------------------------------- charts (R3a, R4, R5)

def chart_trend(d):
    t = d["trend"][d["trend"]["scope"] == "fom"].sort_values("year")
    years = t["year"].to_numpy()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.6, 6.2), sharex=True,
                                 gridspec_kw={"height_ratios": [2.3, 1], "hspace": 0.35})
    for col, color, label in [("share_purchase", SLOT_1, "Purchase"),
                              ("share_refinance", SLOT_2, "Refinance")]:
        a1.plot(years, 100 * t[col], color=color, linewidth=2, marker="o", markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=1.6, label=label, solid_capstyle="round")
    p = 100 * t["share_purchase"].to_numpy()
    a1.annotate(f"{p[0]:.2f}%", (years[0], p[0]), xytext=(0, -15), textcoords="offset points",
                ha="center", color=INK_2, fontsize=8.5)
    a1.annotate(f"{p[-1]:.2f}%", (years[-1], p[-1]), xytext=(9, 0), textcoords="offset points",
                va="center", color=INK, fontsize=9, fontweight="bold")
    a1.set_ylim(0, 100 * t[["share_purchase", "share_refinance"]].to_numpy().max() * 1.18)
    a1.set_ylabel("Share of originations (%)")
    a1.set_title(f"{s.LENDER_LABEL} share in its {s.FOOTPRINT_LABEL} counties")
    a1.legend(loc="upper left", ncol=2)
    mix = 100 * t["market_refi_mix"].to_numpy()
    a2.bar(years, mix, width=0.42, color=MUTED)
    for x, v in zip(years, mix):
        a2.text(x, v + 1.2, f"{v:.0f}%", ha="center", va="bottom", color=INK_2, fontsize=8.5)
    a2.set_ylim(0, mix.max() * 1.3)
    a2.set_ylabel("% of originations")
    a2.set_title("Market refinance mix (refinances as a share of all originations)")
    a2.grid(axis="x", visible=False)
    a2.set_xticks(years, [f"{y}\n(tail of the 2020-21\nrefi boom)" if y == 2022 else str(y) for y in years])
    header(fig, f"{s.LENDER_LABEL} purchase share went from {p[0]:.2f}% to {p[-1]:.2f}%",
           f"{s.FOOTPRINT_LABEL} counties, {years[0]}-{years[-1]}. Refinance share swings with the "
           "refi market, so purchase is the cleaner trend.")
    fig.subplots_adjust(top=1 - 0.95 / fig.get_figheight())
    save(fig, "chart_share_trend.png")


def chart_distance(d):
    order = ["0-2", "2-5", "5-10", "10+"]
    raw = d["bands"][d["bands"]["scope"] == "fom"].set_index("band").loc[order]
    adj = d["bands"][d["bands"]["scope"] == "fom_county_adjusted"].set_index("band").loc[order]
    x = np.arange(len(order))
    ticks = ["0-2", "2-5", "5-10", "10+"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.4, 4.0), gridspec_kw={"wspace": 0.3})
    v = 100 * raw["share_all"].to_numpy()
    a1.bar(x, v, width=0.5, color=SLOT_1)
    for xi, vi in zip(x, v):  # inside the bar top, clear of the average line
        a1.text(xi, vi - 0.08, f"{vi:.2f}%", ha="center", va="top", fontsize=8.5, color="#ffffff",
                fontweight="bold")
    a1.axhline(100 * d["base"], color=INK_2, linewidth=1)
    a1.text(len(order) - 0.55, 100 * d["base"] + 0.06, f"{s.FOOTPRINT_LABEL} average",
            ha="right", va="bottom", fontsize=8, color=INK_2)
    a1.set_xticks(x, ticks)
    a1.set_xlabel("Miles from tract to nearest branch")
    a1.set_ylabel("Share of originations (%)")
    a1.set_ylim(0, v.max() * 1.25)
    a1.set_title("Raw share")
    a1.grid(axis="x", visible=False)
    r = adj["vs_county_average"].to_numpy()
    a2.bar(x, r - 1, bottom=1, width=0.5, color=SLOT_1)
    for xi, ri in zip(x, r):
        a2.text(xi, ri + (0.008 if ri >= 1 else -0.008), f"{ri:.2f}x", ha="center",
                va="bottom" if ri >= 1 else "top", fontsize=8.5, color=INK)
    a2.axhline(1, color=INK_2, linewidth=1)
    a2.set_xticks(x, ticks)
    a2.set_xlabel("Miles from tract to nearest branch")
    a2.set_ylabel("x the tract's own county average")
    a2.set_ylim(0.8, 1.2)
    a2.set_title("Compared with each tract's own county")
    a2.grid(axis="x", visible=False)
    header(fig, "Being close to a branch helps, but mostly within the same county",
           f"{s.FOOTPRINT_LABEL} tracts, {s.SCORING_YEAR}. Most of the raw drop-off is a difference "
           "between counties, not distance.")
    fig.subplots_adjust(top=1 - 0.95 / fig.get_figheight())
    save(fig, "chart_share_by_distance.png")


def chart_depth_vs_expansion(d):
    lad = d["ladder"].set_index("rung")
    cl = d["clusters"][d["clusters"]["touches_footprint"]].sort_values("expansion_gain", ascending=False)
    rows = [(f"Base: {s.FOOTPRINT_LABEL} average ({lad.loc['base', 'share']:.2%})", lad.loc["base", "depth"], "depth"),
            (f"Stretch: {lad.loc['stretch', 'reference']} level ({lad.loc['stretch', 'share']:.2%})",
             lad.loc["stretch", "depth"], "depth"),
            (f"Ceiling: top-quarter counties ({lad.loc['ceiling', 'share']:.2%})", lad.loc["ceiling", "depth"], "depth"),
            (f"All {len(d['scorecard'])} non-{s.FOOTPRINT_LABEL} counties at {s.EXPANSION_TARGET_SHARE:.0%}",
             d["scorecard"]["expansion_gain"].sum(), "expansion")]
    for _, r in cl.iterrows():
        names = r["county_names"].split(", ")
        label = ", ".join(names) if len(names) <= 3 else f"{len(names)} counties ({names[0]} ... {names[-1]})"
        rows.append((f"Cluster {r['growth_cluster']}: {label}", r["expansion_gain"], "expansion"))
    labels, values, kinds = zip(*rows)
    y = np.arange(len(rows))[::-1].astype(float)
    y[3:] -= 0.6  # a gap between the depth and expansion groups
    fig, ax = plt.subplots(figsize=(9.2, 4.9))
    colors = [SLOT_1 if k == "depth" else SLOT_2 for k in kinds]
    ax.barh(y, values, height=0.5, color=colors)
    for yi, v in zip(y, values):
        ax.text(v + 25, yi, f"{v:,.0f}", va="center", ha="left", fontsize=9, color=INK)
    current = d["county_year"].query("year == @s.SCORING_YEAR and footprint_flag == 1")["lender_all"].sum()
    ax.axvline(current, color=INK_2, linewidth=1)
    ax.text(current + 18, y.max() + 0.55, f"today: {current:,.0f} {s.FOOTPRINT_LABEL} loans",
            fontsize=8, color=INK_2, va="bottom")
    ax.set_yticks(y, labels)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, max(values) * 1.12)
    ax.set_xlabel("Added loans a year")
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[Patch(color=SLOT_1, label=f"Depth: lagging {s.FOOTPRINT_LABEL} tracts rise to the benchmark"),
                       Patch(color=SLOT_2, label=f"Expansion: a new county reaches {s.EXPANSION_TARGET_SHARE:.0%} "
                                                 "(upper bound)")],
              loc="lower right")
    header(fig, f"Deeper share inside the {s.FOOTPRINT_LABEL} outweighs the expansion upside",
           f"Added originations a year, {s.SCORING_YEAR} market. Clusters shown are the growth "
           f"clusters that border the {s.FOOTPRINT_LABEL}.")
    fig.subplots_adjust(top=0.84)
    save(fig, "chart_depth_vs_expansion.png")


# ---------------------------------------------------------------- tables

def pct(series, digits=2):
    return (100 * series).round(digits)


def tables(d):
    top = d["top25"].merge(d["tracts"][["census_tract", "households", "household_density", "penetration",
                                        "nearest_branch_scoring_year", "branch_miles_scoring_year",
                                        "distance_band"]], on="census_tract", how="left")
    top["household_density"] = top["household_density"].round(0)
    top["penetration"] = top["penetration"].round(1)
    top["branch_miles_scoring_year"] = top["branch_miles_scoring_year"].round(1)
    top = top.rename(columns={"nearest_branch_scoring_year": "nearest_branch",
                              "branch_miles_scoring_year": "miles_to_branch"})
    top.to_csv(OUT / "opportunity_top25.csv", index=False)

    lc = d["ladder_county"][["county_fips", "in_top_quarter", "depth_stretch", "depth_ceiling"]]
    branches = d["branches"].groupby("ncua_county").size()
    depth = d["depth"].merge(lc, on="county_fips", how="left")
    depth = depth.merge(d["county_ctx"][["county_fips", "branch_miles_hh_weighted"]], on="county_fips",
                        how="left")
    depth["branches"] = depth["county_name"].map(branches).fillna(0).astype(int)
    out = pd.DataFrame({
        "depth_rank": depth["rank"], "county_name": depth["county_name"],
        "market_loans": depth["market_all"], "lender_loans": depth["lender_all"],
        "lender_share_pct": pct(depth["share_all"]), "in_top_quarter": depth["in_top_quarter"],
        "depth_base": depth["opportunity"].round(1), "depth_stretch": depth["depth_stretch"].round(1),
        "depth_ceiling": depth["depth_ceiling"].round(1),
        "depth_base_contestable": depth["opportunity_contestable"].round(1),
        "top25_tracts": depth["top25_tracts"], "stable_top25_tracts": depth["stable_top25_tracts"],
        "branches": depth["branches"], "household_weighted_miles_to_branch": depth["branch_miles_hh_weighted"].round(1),
        "competitor_1": depth["competitor_1"], "competitor_2": depth["competitor_2"],
        "competitor_3": depth["competitor_3"]})
    out.to_csv(OUT / "depth_by_county.csv", index=False)

    sc = d["scorecard"].copy()
    for col in ["current_share", "pop_growth", "pop_growth_recent", "purchase_market_change"]:
        sc[f"{col}_pct"] = pct(sc[col], 2 if col == "current_share" else 1)
    sc = sc.drop(columns=["current_share", "pop_growth", "pop_growth_recent", "purchase_market_change"])
    for col in ["expansion_gain", "household_density", "land_sq_mi", "branch_miles_hh_weighted"]:
        sc[col] = sc[col].round(1)
    sc.to_csv(OUT / "expansion_scorecard.csv", index=False)
    cl = d["clusters"].copy()
    cl["pop_growth_pct"] = pct(cl.pop("pop_growth"), 1)
    cl["expansion_gain"] = cl["expansion_gain"].round(1)
    cl.to_csv(OUT / "growth_clusters.csv", index=False)
    return top, out


# ---------------------------------------------------------------- key numbers (R7)

def key_numbers(d, depth_table):
    rows = []

    def add(key, value, display, source, description):
        rows.append({"key": key, "value": value, "display": display, "source": source,
                     "description": description})

    cur = d["county_year"][d["county_year"]["year"] == s.SCORING_YEAR]
    fp = cur[cur["footprint_flag"] == 1]
    add("footprint_counties", len(fp), f"{len(fp)}", "county_year_metrics.csv", "footprint counties")
    add("footprint_market_loans", fp["market_all"].sum(), f"{fp['market_all'].sum():,}",
        "county_year_metrics.csv", f"market originations in the footprint, {s.SCORING_YEAR}")
    add("footprint_lender_loans", fp["lender_all"].sum(), f"{fp['lender_all'].sum():,}",
        "county_year_metrics.csv", f"subject-lender originations in the footprint, {s.SCORING_YEAR}")
    add("footprint_share", d["base"], f"{d['base']:.2%}", "county_year_metrics.csv", "footprint share")

    tr = d["trend"][d["trend"]["scope"] == "fom"].set_index("year")
    first = s.YEARS[0]
    for col, name in [("share_purchase", "purchase"), ("share_refinance", "refinance")]:
        for y in (first, s.SCORING_YEAR):
            add(f"{name}_share_{y}", tr.loc[y, col], f"{tr.loc[y, col]:.2%}", "trend_summary.csv",
                f"footprint {name} share, {y}")
    lt = d["lender_trend"]
    rank = int(lt.loc[lt["lei"] == s.LENDER_LEI, f"footprint_rank_{s.SCORING_YEAR}"].iloc[0])
    add("lender_rank_footprint", rank, f"#{rank}", "lender_trend_fom.csv",
        f"subject lender's rank among footprint lenders, {s.SCORING_YEAR}")

    lad = d["ladder"].set_index("rung")
    top_names = lad.loc["ceiling", "reference"]
    add("top_quarter_counties", top_names, top_names, "benchmark_ladder.csv", "top-quarter counties")
    add("top_quarter_count", len(top_names.split(", ")), f"{len(top_names.split(', '))}",
        "benchmark_ladder.csv", "number of top-quarter counties")
    for rung in ["base", "stretch", "ceiling"]:
        add(f"ladder_{rung}_share", lad.loc[rung, "share"], f"{lad.loc[rung, 'share']:.2%}",
            "benchmark_ladder.csv", f"{rung} rung share")
        add(f"ladder_{rung}_depth", lad.loc[rung, "depth"], f"{lad.loc[rung, 'depth']:,.0f}",
            "benchmark_ladder.csv", f"depth at the {rung} rung, loans a year")
    add("ladder_stretch_county", lad.loc["stretch", "reference"], lad.loc["stretch", "reference"],
        "benchmark_ladder.csv", "county that sets the stretch rung")

    st = d["structure"].set_index("group")
    for g, tag in [("top quarter", "top"), ("rest of footprint", "rest")]:
        add(f"{tag}_share", st.loc[g, "lender_share"], f"{st.loc[g, 'lender_share']:.2%}",
            "market_structure.csv", f"subject-lender share, {g}")
        add(f"{tag}_hhi", st.loc[g, "county_hhi"], f"{st.loc[g, 'county_hhi']:.0f}",
            "market_structure.csv", f"county HHI, {g}")
        add(f"{tag}_broker_share", st.loc[g, "broker_submitted_share"],
            f"{st.loc[g, 'broker_submitted_share']:.0%}", "market_structure.csv",
            f"broker-submitted share of originations, {g}")
        add(f"{tag}_lenders_per_100", st.loc[g, "lenders_per_100_loans"],
            f"{st.loc[g, 'lenders_per_100_loans']:.0f}", "market_structure.csv",
            f"median lenders per 100 loans in a tract, {g}")
    add("lender_broker_share", st["lender_broker_submitted_share"].max(),
        f"{st['lender_broker_submitted_share'].max():.0%}", "market_structure.csv",
        "subject lender's broker-submitted share")
    rest_broker = st.loc["rest of footprint", "market_loans"] * st.loc["rest of footprint", "broker_submitted_share"]
    add("rest_broker_loans", rest_broker, f"{rest_broker:,.0f}", "market_structure.csv",
        "approx. broker-submitted originations outside the top quarter")
    pc = d["peers"]
    for g, tag in [("top quarter", "top"), ("rest of footprint", "rest")]:
        v = pc.loc[pc["group"] == g, "lender_share"]
        add(f"peer_{tag}_min", v.min(), f"{v.min():.1%}", "peer_comparison.csv", f"lowest band share, {g}")
        add(f"peer_{tag}_max", v.max(), f"{v.max():.1%}", "peer_comparison.csv", f"highest band share, {g}")

    dt = depth_table.sort_values("depth_base", ascending=False)
    top6 = dt.head(6)
    add("depth_top6_share", top6["depth_base"].sum() / dt["depth_base"].sum(),
        f"{top6['depth_base'].sum() / dt['depth_base'].sum():.0%}", "depth_by_county.csv",
        f"share of base depth in the top 6 counties ({', '.join(top6['county_name'])})")
    no_branch = dt[dt["branches"] == 0]["county_name"].tolist()
    add("branchless_counties", len(no_branch), f"{len(no_branch)}", "depth_by_county.csv",
        f"footprint counties with no public branch: {', '.join(sorted(no_branch))}")
    add("contestable_depth", dt["depth_base_contestable"].sum(), f"{dt['depth_base_contestable'].sum():,.0f}",
        "depth_by_county.csv", "base depth on the contestable (non-builder) market")

    bands = d["bands"]
    adj = bands[bands["scope"] == "fom_county_adjusted"].set_index("band")
    raw = bands[bands["scope"] == "fom"].set_index("band")
    add("near_vs_county", adj.loc["0-2", "vs_county_average"], f"{adj.loc['0-2', 'vs_county_average']:.2f}x",
        "share_by_distance.csv", "tracts within 2 miles vs. their county's average")
    add("near_share_raw", raw.loc["0-2", "share_all"], f"{raw.loc['0-2', 'share_all']:.2%}",
        "share_by_distance.csv", "raw share within 2 miles")
    add("near_band_miles", s.DISTANCE_BANDS[1], f"{s.DISTANCE_BANDS[1]:g}", "config/settings.py",
        "edge of the nearest distance band, miles")
    add("far_band_miles", s.DISTANCE_BANDS[-2], f"{s.DISTANCE_BANDS[-2]:g}", "config/settings.py",
        "start of the farthest distance band, miles")
    add("far_share_raw", raw.loc["10+", "share_all"], f"{raw.loc['10+', 'share_all']:.2%}",
        "share_by_distance.csv", "raw share 10+ miles")

    sc = d["scorecard"]
    add("expansion_counties", len(sc), f"{len(sc)}", "expansion_scorecard.csv", "non-footprint counties")
    add("expansion_target", s.EXPANSION_TARGET_SHARE, f"{s.EXPANSION_TARGET_SHARE:.0%}", "config/settings.py",
        "expansion target share")
    add("expansion_total", sc["expansion_gain"].sum(), f"{sc['expansion_gain'].sum():,.0f}",
        "expansion_scorecard.csv", "expansion gain, all non-footprint counties (upper bound)")
    best = sc.sort_values("expansion_gain", ascending=False).iloc[0]
    add("expansion_top_county", best["county_name"], best["county_name"], "expansion_scorecard.csv",
        "non-footprint county with the largest gain")
    add("expansion_top_gain", best["expansion_gain"], f"{best['expansion_gain']:.0f}", "expansion_scorecard.csv",
        "its gain, loans a year")
    add("expansion_top_miles", best["branch_miles_hh_weighted"], f"{best['branch_miles_hh_weighted']:.0f}",
        "expansion_scorecard.csv", "its household-weighted miles to the nearest branch")
    for _, r in d["clusters"].iterrows():
        cid = r["growth_cluster"]
        add(f"cluster_{cid}_gain", r["expansion_gain"], f"{r['expansion_gain']:.0f}", "growth_clusters.csv",
            f"cluster {cid} ({r['county_names']}) gain; touches footprint: {r['touches_footprint']}")
        add(f"cluster_{cid}_counties", r["counties"], f"{r['counties']}", "growth_clusters.csv",
            f"cluster {cid} county count")
        add(f"cluster_{cid}_growth", r["pop_growth"], f"{r['pop_growth']:.1%}", "growth_clusters.csv",
            f"cluster {cid} population growth")
    mismatches = int((~d["recon"]["match"]).sum())
    add("reconciliation_mismatches", mismatches, f"{mismatches}", "phase2_checks/dccu_api_reconciliation.csv",
        "subject-lender totals vs. HMDA API, mismatches")
    add("builder_lenders_included", d["builders_included"], f"{d['builders_included']}",
        "config/builder_lenders.csv", "builder-owned lenders in the contestable-market rule")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- checks

NUMBER = re.compile(r"(?<![\w.#$/-])[$#]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:%|x|×)?(?![\w])")


def norm(token):
    return re.sub(r"[$#,%x×]", "", token)


def check_findings(keys):
    if not FINDINGS.exists():
        return {"exists": False, "words": 0, "unmatched": []}
    text = FINDINGS.read_text(encoding="utf-8")
    words = len([w for w in re.split(r"\s+", text.replace("|", " ")) if re.search(r"[A-Za-z0-9]", w)])
    body = re.sub(r"\]\([^)]*\)", "]", text)                 # drop link targets
    body = re.sub(r"(?m)^\s*(?:\*\*)?\d+\.\s", " ", body)    # drop list and section numbers
    known = {norm(v) for v in keys["display"].astype(str)}
    found = [t for t in NUMBER.findall(body) if not re.fullmatch(r"20[1-3]\d", norm(t))]
    unmatched = sorted({t for t in found if norm(t) not in known})
    return {"exists": True, "words": words, "unmatched": unmatched}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    style()
    d = load()

    n_share, n_low = map_footprint_share(d)
    n_opp = map_footprint_opportunity(d)
    map_statewide(d)
    html = html_map(d)
    chart_trend(d)
    chart_distance(d)
    chart_depth_vs_expansion(d)
    top, depth_table = tables(d)
    keys = key_numbers(d, depth_table)
    keys.to_csv(OUT / "key_numbers.csv", index=False)

    # Ties between files (key numbers must agree with the stages that made them).
    k = keys.set_index("key")["value"]
    size = d["market_size"].query("year == @s.SCORING_YEAR and scope == 'fom'").iloc[0]
    ladder = d["ladder"].set_index("rung")
    ties = pd.DataFrame([
        ("footprint market loans = Phase 2 market size", k["footprint_market_loans"], size["market_originations"]),
        ("footprint lender loans = Phase 2 market size", k["footprint_lender_loans"], size["dccu_originations"]),
        ("base rung = footprint share", ladder.loc["base", "share"], d["base"]),
        ("base depth = sum of opportunity scores", ladder.loc["base", "depth"],
         d["tracts"].loc[d["tracts"]["footprint_flag"] == 1, "opportunity_score"].sum()),
        ("ceiling depth = sum over counties", ladder.loc["ceiling", "depth"], d["ladder_county"]["depth_ceiling"].sum()),
        ("expansion total = scorecard sum", k["expansion_total"], d["scorecard"]["expansion_gain"].sum()),
        ("depth table base = Phase 3 depth", depth_table["depth_base"].sum(), d["depth"]["opportunity"].sum()),
    ], columns=["tie", "ours", "source"])
    ties["match"] = np.isclose(ties["ours"].astype(float), ties["source"].astype(float), atol=0.6)
    if not ties["match"].all():
        raise ValueError(f"Key numbers don't tie to their sources:\n{ties[~ties['match']]}")

    blanks = int(top[["household_density", "miles_to_branch", "competitor_1"]].isna().any(axis=1).sum())
    findings = check_findings(keys)
    reqs = [("R1", "tract map of share (footprint + statewide)",
             ["map_footprint_share.png", "map_statewide.png", "mortgage_map.html"]),
            ("R2", "top 25 tracts with top 3 competitors", ["opportunity_top25.csv", "map_footprint_opportunity.png"]),
            ("R3", "inside vs. outside footprint", ["../data/processed/trend_summary.csv"]),
            ("R3a", "depth vs. expansion scorecard", ["depth_by_county.csv", "expansion_scorecard.csv",
                                                      "chart_depth_vs_expansion.png"]),
            ("R3b", "expansion rankings and clusters", ["growth_clusters.csv", "../data/processed/expansion_groups.csv",
                                                        "map_statewide.png"]),
            ("R4", "share by distance band", ["../data/processed/share_by_distance.csv", "chart_share_by_distance.png"]),
            ("R5", "share trend 2022 onward", ["../data/processed/trend_summary.csv",
                                               "../data/processed/county_year_metrics.csv", "chart_share_trend.png"]),
            ("R6", "household density on map and table", ["mortgage_map.html", "opportunity_top25.csv"]),
            ("R7", "FINDINGS.md and DATA_QUALITY.md", ["../FINDINGS.md", "../DATA_QUALITY.md"])]
    checklist = pd.DataFrame([{"requirement": r, "what": w, "files": ", ".join(f.replace("../", "") for f in fs),
                               "present": all((OUT / f).resolve().exists() for f in fs)} for r, w, fs in reqs])

    sections = [
        f"### 1. Maps\nFootprint maps draw **{n_share:,}** footprint tracts (share map) and **{n_opp:,}** "
        f"(opportunity map); {n_low:,} low-volume tracts are left unshaded, matching the `low_volume` flag. "
        f"Interactive map layers: share {html['share']:,} tracts, opportunity {html['opportunity']:,}, "
        f"density {html['density']:,}, counties {html['counties']}; file size {html['mb']:.1f} MB "
        "(geometry simplified to about 40 m inside the footprint and 120 m elsewhere).",
        f"### 2. Top {TOP_N} table\n{len(top)} rows; rows with a blank density, branch distance or top "
        f"competitor: **{blanks}**.",
        "### 3. Key numbers tie to their sources\n" + md_table(ties.round(4)),
        "### 4. FINDINGS.md\n" + (
            f"{findings['words']} words (limit about {FINDINGS_WORD_LIMIT}, one page). Numbers not found in "
            f"`outputs/key_numbers.csv`: " + (", ".join(findings["unmatched"]) or "**none**") + "."
            if findings["exists"] else "Not written yet."),
        "### 5. Definition of done (v1)\n" + md_table(checklist)
        + f"\n\nSubject-lender totals vs. the HMDA API: **{k['reconciliation_mismatches']:.0f}** mismatches "
        "(tolerance: exact match). The full pipeline rebuilds with `python src/run_all.py`.",
    ]
    write_data_quality("phase5_outputs", "Phase 5: map, table and findings", sections)
    print(f"Maps: {n_share} footprint tracts, {n_low} low-volume; HTML {html['mb']:.1f} MB")
    print(f"Key numbers: {len(keys)}; ties all match: {ties['match'].all()}")
    print(f"FINDINGS: {findings}")
    print(checklist.to_string(index=False))


if __name__ == "__main__":
    main()
