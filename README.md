# DCCU_lending_opps
Mortgage Growth Map: an outside-in analysis of public HMDA data showing where a lender wins and loses mortgage share, and whether its growth should come from deeper share in its current footprint, expansion into new markets, or both. It is meant to become a product for any lender; **Delta Community Credit Union (DCCU) is the illustrative example** used to build v1. DCCU did not request this.

Start with DCCU's findings: [outputs/dccu/FINDINGS.md](outputs/dccu/FINDINGS.md). Requirements: [docs/PRD.md](docs/PRD.md). Data checks: [DATA_QUALITY.md](DATA_QUALITY.md) (market) and [outputs/dccu/DATA_QUALITY.md](outputs/dccu/DATA_QUALITY.md) (DCCU).

## Setup (once)
Needs Python 3.13. From the repo root:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

`.venv/` is a private Python install for this project; on macOS/Linux use `.venv/bin/python`.

## Run the pipeline
```bash
.venv/Scripts/python src/run_all.py --lender dccu
```

`--lender` takes a key under `config/lenders/`, or `all` for every configured lender (default: `dccu`). The market stages run once; the lender stages run once per lender. It stops at the first failure.

Market stages (shared by every lender):
- `01_download.py` fetches all raw data into `data/raw/` (about 820 MB, git-ignored), plus each configured lender's own files into `data/raw/lenders/<key>/`. Files already on disk are never downloaded again; the first run takes roughly an hour.
- `02_validate.py` runs the Phase 1 checks: market checks to `data/processed/phase1_checks/` and `DATA_QUALITY.md`, each lender's presence and branch checks to its own folder and log.
- `03_market.py` applies the PRD's market definition to every lender and writes `data/processed/market_{year}.parquet` (git-ignored), `lenders.csv`, and the checks in `phase2_checks/` (each lender's reconciliation with the HMDA API goes to its own folder).

Lender stages (run per lender; everything goes to `data/processed/<key>/` and `outputs/<key>/`):
- `04_metrics.py` computes share, trend, depth opportunity and expansion gain.
- `05_context.py` adds households, density, penetration, distance to the nearest branch, county population growth, adjacency and growth clusters, and completes the expansion scorecard.
- `06_benchmarks.py` builds the benchmark ladder (footprint average, stretch, ceiling) and the market-structure evidence.
- `07_outputs.py` draws the maps and charts, writes the final tables and `key_numbers.csv`, and checks the lender's `FINDINGS.md` against the key numbers.
- `check_baseline.py` (lenders with a saved baseline) compares every file with `tests/baseline/<key>/`; DCCU must reproduce v1 exactly.

Each stage can also be run on its own, e.g. `.venv/Scripts/python src/03_market.py`. For a lender stage, set the lender first: `MGM_LENDER=dccu .venv/Scripts/python src/04_metrics.py` (the default is dccu).

## Adding a lender
Each lender is a folder under `config/lenders/<key>/`:

| File | Contents |
|---|---|
| `lender.toml` | name, label, LEI, charter, NCUA charter number, footprint label, expansion target (TOML is a plain-text config format) |
| `footprint.csv` | the footprint's county FIPS codes and names, with the source and date checked |
| `branch_exclusions.csv` | branch sites left out of distance, with reasons |
| `branch_coordinates.csv` | hand-placed points for branch addresses the geocoder can't match |

Today the pipeline handles credit unions in Georgia; other charters and states are in the PRD's Future phases.

## Layout
| Path | Contents |
|---|---|
| `config/` | market config (`settings.py`, `ga_counties.csv`, `builder_lenders.csv`) and `lenders/<key>/` |
| `data/raw/` | raw downloads (git-ignored); `data/raw/lenders/<key>/` holds each lender's own files |
| `data/processed/` | market files shared by every lender: `market_{year}.parquet`, `lenders.csv`, Phase 1-2 checks |
| `data/processed/<key>/` | one lender's metrics, context, benchmarks and Phase 1-5 checks (CSVs, kept in git) |
| `outputs/<key>/` | one lender's maps, charts, final tables, `key_numbers.csv`, `FINDINGS.md`, `DATA_QUALITY.md` |
| `tests/baseline/<key>/` | saved outputs a lender's runs must reproduce |

Parquet files and the interactive HTML maps are git-ignored and rebuilt by `run_all.py`; the CSVs are small and kept in git.

## Lender files (`data/processed/<key>/`)
| File | Contents |
|---|---|
| `tract_metrics.csv` | every Georgia tract, scoring year: market and lender loans, share, `low_volume`, opportunity score and rank (footprint tracts), `stable_top25`, contestable score, top 3 competitors |
| `depth_by_county.csv` | depth opportunity per footprint county (full and contestable market), with top 3 competitors |
| `trend_summary.csv` | lender share by year for the footprint, outside it and statewide: purchase, refinance, combined, and refi mix |
| `county_year_metrics.csv` | every county × year: market and lender loans and share by purpose |
| `lender_trend_footprint.csv` | footprint share by year for the top 10 footprint lenders and the subject lender |
| `expansion_counties.csv` | non-footprint counties: scoring-year market, lender share, gain at the expansion target share |
| `expansion_groups.csv` | expansion gain by market group and by urban/rural tier |
| `branches.csv` | the lender's sites in the scoring-year and latest NCUA snapshots: coordinates, in-scope flag, exclusion reason |
| `tract_context.csv` | every tract: households, land area, household density, penetration, nearest branch and miles, distance band |
| `share_by_distance.csv` | R4: lender share by distance band (footprint, statewide, per footprint county, county-adjusted) |
| `county_context.csv` | every county: households, density, population and growth, footprint neighbors, household-weighted branch distance, growth cluster |
| `expansion_scorecard.csv` | R3a: the non-footprint counties with expansion gain plus the county context |
| `growth_clusters.csv` | R3b: groups of neighboring fast-growing non-footprint counties |
| `opportunity_top25.csv` | R2: top 25 footprint tracts (stage 07 adds context for `outputs/`) |
| `benchmark_ladder.csv` | base / stretch / ceiling: rule, share and depth |
| `depth_ladder_by_county.csv` | depth at each benchmark rung, per footprint county |
| `market_structure.csv` | top-quarter footprint counties vs. the rest: concentration, lenders per loan, broker-submitted share |
| `peer_comparison.csv` | subject-lender share by loan size and by tract competition, top quarter vs. the rest |

## Lender outputs (`outputs/<key>/`)
| File | Contents |
|---|---|
| `map_footprint_share.png` | R1: footprint tracts by share vs. the footprint average |
| `map_footprint_opportunity.png` | R1, R2: footprint tracts by opportunity score, top 25 numbered |
| `map_statewide.png` | R1, R3b: county share, and expansion gain with growth clusters |
| `mortgage_map.html` | interactive map (open in a browser; rebuilt locally, not in git): share, opportunity, density, expansion; hover for numbers |
| `chart_share_trend.png` | R5: purchase and refinance share, with the market's refi mix |
| `chart_share_by_distance.png` | R4: share by distance band, raw and county-adjusted |
| `chart_depth_vs_expansion.png` | R3a: depth at three benchmarks vs. expansion |
| `opportunity_top25.csv` | R2, R6: top 25 tracts with competitors, density, penetration, nearest branch |
| `depth_by_county.csv` | depth per footprint county at each benchmark, with branches and competitors |
| `expansion_scorecard.csv`, `growth_clusters.csv` | R3a, R3b: the expansion scorecard and named clusters |
| `key_numbers.csv` | every number quoted in `FINDINGS.md`, with its source file |
| `FINDINGS.md`, `DATA_QUALITY.md` | the one-page findings, and the lender's own checks |

## Data sources
| Source | Used for |
|---|---|
| HMDA Data Browser API (CFPB/FFIEC), 2022–2025, all Georgia counties | loan-level market data; each lender's own records and API check counts |
| Census county list (2020) and OMB 2023 delineation | `config/ga_counties.csv` (metro/micro/rural tier, market group) |
| Census TIGER/Line 2024, Georgia tracts (2020 boundaries) | tract shapes, land area, internal points |
| Census ACS 2020–2024 5-year, table B11001 | households per tract |
| NCUA quarterly call report (latest, and December of the scoring year) | credit-union branch addresses, by charter number |
| Census Geocoder (batch) | branch coordinates; a few hand-placed in each lender's `branch_coordinates.csv` |
| Census Population Estimates, Vintage 2025 (county totals) | county population growth |
| Census county adjacency file, 2025 | adjacency to the footprint, growth clusters |
| Each lender's own website (e.g. DCCU's eligibility page) | `config/lenders/<key>/footprint.csv` |
| GLEIF LEI registry | names for the few market LEIs missing from the HMDA filers lists |
| Hand-maintained, with the basis per row | `config/builder_lenders.csv` (builder-owned lenders, for the contestable market) |
| Esri World Light Gray Canvas (`BASEMAP` in `config/settings.py`) | basemap tiles in `mortgage_map.html`, loaded by the viewer's browser; license a basemap before any paid delivery |
