# DCCU_lending_opps
Mortgage Growth Map: an outside-in analysis of public HMDA data showing where a lender wins and loses mortgage share, and whether its growth should come from deeper share in its current footprint, expansion into new markets, or both. It is meant to become a product for any lender; **Delta Community Credit Union (DCCU) is the illustrative example** used to build v1. DCCU did not request this.

Start with [FINDINGS.md](FINDINGS.md). Requirements: [docs/PRD.md](docs/PRD.md). Data issues and check results: [DATA_QUALITY.md](DATA_QUALITY.md).

## Setup (once)
Needs Python 3.13. From the repo root:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

`.venv/` is a private Python install for this project; on macOS/Linux use `.venv/bin/python`.

## Run the pipeline
```bash
.venv/Scripts/python src/run_all.py
```

This runs every stage in order and stops at the first failure:

- `01_download.py` fetches all raw data into `data/raw/` (about 820 MB, git-ignored). Files already on disk are never downloaded again; the first run takes roughly an hour.
- `02_validate.py` runs the Phase 1 checks, writes details to `data/processed/phase1_checks/`, and updates `DATA_QUALITY.md`.
- `03_market.py` applies the PRD's market definition to every lender and writes `data/processed/market_{year}.parquet` (git-ignored), `lenders.csv`, and the checks in `phase2_checks/`.
- `04_metrics.py` computes share, trend, depth opportunity and expansion gain, and writes the metric files below and the checks in `phase3_checks/`.
- `05_context.py` adds households, density, penetration, distance to the nearest DCCU branch, county population growth, adjacency and growth clusters, and completes the expansion scorecard; checks in `phase4_checks/`.
- `06_benchmarks.py` builds the benchmark ladder (footprint average, stretch, ceiling) and the market-structure evidence; checks in `phase5_checks/`.
- `07_outputs.py` draws the maps and charts, writes the final tables and `outputs/key_numbers.csv`, and checks `FINDINGS.md` against the key numbers.

Stages 06 and 07 are lender-neutral: the subject lender and its footprint come from `config/settings.py`.

Each stage can also be run on its own, e.g. `.venv/Scripts/python src/03_market.py`.

## Processed data
| File | Contents |
|---|---|
| `hmda_ga_{year}.parquet` | every Georgia HMDA row with a county, all columns as text |
| `market_{year}.parquet` | rows in the market definition, all outcomes, plus `county_fips`, `fom_flag`, `purpose_group`, `has_tract` |
| `lenders.csv` | LEI → latest lender name, and whether it came from the HMDA filers list or GLEIF |
| `tract_metrics.csv` | every Georgia tract, scoring year: market and DCCU loans, share, `low_volume`, opportunity score and rank (FOM tracts), `stable_top25`, contestable score, top 3 competitors |
| `depth_by_county.csv` | depth opportunity per FOM county (full and contestable market), with top 3 competitors |
| `trend_summary.csv` | DCCU share by year for FOM, non-FOM and statewide: purchase, refinance, combined, and refi mix |
| `county_year_metrics.csv` | every county × year: market and DCCU loans and share by purpose |
| `lender_trend_fom.csv` | FOM share by year for the top 10 FOM lenders and DCCU |
| `expansion_counties.csv` | non-FOM counties: scoring-year market, DCCU share, gain at the expansion target share |
| `expansion_groups.csv` | expansion gain by market group and by urban/rural tier |
| `branches.csv` | DCCU sites in the scoring-year and latest NCUA snapshots: coordinates, in-scope flag, exclusion reason |
| `tract_context.csv` | every tract: households, land area, household density, penetration, nearest branch and miles, distance band |
| `share_by_distance.csv` | R4: DCCU share by distance band (FOM, statewide, per FOM county, county-adjusted) |
| `county_context.csv` | every county: households, density, population and growth, FOM neighbors, household-weighted branch distance, growth cluster |
| `expansion_scorecard.csv` | R3a: the 139 non-FOM counties with expansion gain plus the county context |
| `growth_clusters.csv` | R3b: groups of neighboring fast-growing non-FOM counties |
| `opportunity_top25.csv` | R2: top 25 FOM tracts (stage 07 adds context for `outputs/`) |
| `benchmark_ladder.csv` | base / stretch / ceiling: rule, share and depth |
| `depth_ladder_by_county.csv` | depth at each benchmark rung, per footprint county |
| `market_structure.csv` | top-quarter footprint counties vs. the rest: concentration, lenders per loan, broker-submitted share |
| `peer_comparison.csv` | subject-lender share by loan size and by tract competition, top quarter vs. the rest |

Parquet files are git-ignored and rebuilt by `run_all.py`; the CSVs are small and kept in git.

## Outputs
| File | Contents |
|---|---|
| `map_footprint_share.png` | R1: footprint tracts by share vs. the footprint average |
| `map_footprint_opportunity.png` | R1, R2: footprint tracts by opportunity score, top 25 numbered |
| `map_statewide.png` | R1, R3b: county share, and expansion gain with growth clusters |
| `mortgage_map.html` | interactive map (open in a browser): share, opportunity, density, expansion; hover for numbers |
| `chart_share_trend.png` | R5: purchase and refinance share, with the market's refi mix |
| `chart_share_by_distance.png` | R4: share by distance band, raw and county-adjusted |
| `chart_depth_vs_expansion.png` | R3a: depth at three benchmarks vs. expansion |
| `opportunity_top25.csv` | R2, R6: top 25 tracts with competitors, density, penetration, nearest branch |
| `depth_by_county.csv` | depth per footprint county at each benchmark, with branches and competitors |
| `expansion_scorecard.csv`, `growth_clusters.csv` | R3a, R3b: the expansion scorecard and named clusters |
| `key_numbers.csv` | every number quoted in `FINDINGS.md`, with its source file |

## Data sources
| Source | Used for |
|---|---|
| HMDA Data Browser API (CFPB/FFIEC), 2022–2025, all Georgia counties | loan-level market and DCCU data |
| Census county list (2020) and OMB 2023 delineation | `config/ga_counties.csv` (FOM and Atlanta MSA flags, metro/micro/rural tier, market group) |
| Census TIGER/Line 2024, Georgia tracts (2020 boundaries) | tract shapes, land area, internal points |
| Census ACS 2020–2024 5-year, table B11001 | households per tract |
| NCUA quarterly call report (latest, and December of the scoring year) | DCCU branch addresses |
| Census Geocoder (batch) | branch coordinates; two hand-interpolated in `config/branch_coordinates_manual.csv` |
| Census Population Estimates, Vintage 2025 (county totals) | county population growth |
| Census county adjacency file, 2025 | adjacency to the FOM, growth clusters |
| Hand-maintained | `config/branch_exclusions.csv` (sites left out of branch distance, with reasons) |
| DCCU eligibility page | `config/fom_counties.csv` |
| GLEIF LEI registry | names for the few market LEIs missing from the HMDA filers lists |
| Hand-maintained, with the basis per row | `config/builder_lenders.csv` (builder-owned lenders, for the contestable market) |
| Esri World Light Gray Canvas | basemap tiles in `mortgage_map.html` (loaded by the viewer's browser) |
