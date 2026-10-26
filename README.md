# DCCU_lending_opps
Combining public datasets to created a geographic opportunity analysis for Delta Community Credit Union.  This is a personal experiment, not requested by DCCU.

Requirements: [docs/PRD.md](docs/PRD.md). Data issues and check results: [DATA_QUALITY.md](DATA_QUALITY.md).

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

Each stage can also be run on its own, e.g. `.venv/Scripts/python src/03_market.py`.

## Processed data
| File | Contents |
|---|---|
| `hmda_ga_{year}.parquet` | every Georgia HMDA row with a county, all columns as text |
| `market_{year}.parquet` | rows in the market definition, all outcomes, plus `county_fips`, `fom_flag`, `purpose_group`, `has_tract` |
| `lenders.csv` | LEI → latest lender name |

Parquet files are git-ignored and rebuilt by `run_all.py`.

## Data sources
| Source | Used for |
|---|---|
| HMDA Data Browser API (CFPB/FFIEC), 2022–2025, all Georgia counties | loan-level market and DCCU data |
| Census county list (2020) and OMB 2023 delineation | `config/ga_counties.csv` (FOM and Atlanta MSA flags) |
| Census TIGER/Line 2024, Georgia tracts (2020 boundaries) | tract shapes, land area, internal points |
| Census ACS 2020–2024 5-year, table B11001 | households per tract |
| NCUA quarterly call report | DCCU branch locations |
| DCCU eligibility page | `config/fom_counties.csv` |
