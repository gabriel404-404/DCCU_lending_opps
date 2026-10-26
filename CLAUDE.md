# CLAUDE.md

## Project
Mortgage Growth Map for Delta Community Credit Union (DCCU): an outside-in analysis of public HMDA data showing where DCCU wins and loses mortgage share across the Atlanta metro, and whether growth should come from deeper share inside its field of membership, expansion into a new county, or both.

This is a personal project. It was not requested by DCCU and uses only public data.

**The PRD is the source of truth: [docs/PRD.md](docs/PRD.md).** Read it before starting any phase. If this file and the PRD disagree, follow the PRD and point out the conflict.

## About me
- I'm a data analyst and an executive. I manage data engineers and software engineers, but I've never worked in either role.
- **SQL: expert.** Skip SQL basics. When explaining pandas, compare it to the SQL equivalent (joins, group bys, window functions).
- **Python and git: amateur.** I'm eager to learn. Briefly explain new concepts, commands and library choices when they first come up, and say what each git step does before you run it.
- I'm strong on analysis and business framing. Challenge my analytical choices when you see a problem, and flag engineering trade-offs in plain terms so I can make the call.

## How we work
- **Plan before code.** Before each phase, write out the plan (inputs, outputs, files, checks) and wait for my approval.
- **Check in after each phase.** Summarize what was built, the key numbers, and any data-quality issues, then stop.
- Phases (PRD Appendix A):
  1. Download and validate
  2. Market definition
  3. Share, trend and opportunity metrics
  4. Households, density and branch distance
  5. Map, table and findings
- **Don't guess domain facts.** Look up DCCU's LEI with the `/view/filers` API, take the field-of-membership county list from DCCU's site, and confirm the latest HMDA year from the API. Ask me when something can't be confirmed.
- **Never drop data silently.** Log every exclusion, gap and reconciliation miss in `DATA_QUALITY.md`.

## Tech
- Python with pandas, geopandas and requests. Use matplotlib or folium for maps.
- Use a local virtual environment in `.venv/` (git-ignored) and record dependencies in `requirements.txt`.
- Windows machine. Use paths that work cross-platform (`pathlib`).

## Layout
```
config/           county lists (metro FIPS, FOM counties), small hand-maintained files
data/raw/         raw downloads, git-ignored, cached
data/processed/   cleaned, intermediate outputs
src/              one script per pipeline stage
outputs/          map, opportunity CSV, charts
docs/PRD.md       requirements
FINDINGS.md       ≤ 1 page, ends with a depth vs. expansion recommendation
DATA_QUALITY.md   every exclusion, gap and check result
```

## Pipeline rules
- **Cache downloads.** Never call an API again if the raw file already exists in `data/raw/`.
- **The full pipeline rebuilds from raw data with one command.** Keep that command documented in the README.
- **Each `src/` stage reads from the previous stage's outputs on disk**, not from in-memory state.
- **Keep the market fixed.** Filter by a fixed county FIPS list in `config/`, not by MSA code.
- **Use HMDA 2022 onward only** (2020 census tracts).
- **Apply the market definition (PRD Appendix A) to every lender, not just DCCU.**

## Definition of done (v1)
- Requirements R1–R7 from the PRD are met.
- DCCU's yearly totals reconcile to its published HMDA totals within a documented tolerance.
- From `FINDINGS.md`, the CLO could name three concrete actions.
