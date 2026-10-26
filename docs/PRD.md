# PRD: Mortgage Growth Map for Delta Community Credit Union

## 1. Why (business case)
- **Business driver:** Mortgage lending is a share fight with thin margins. Growth for a credit union comes from winning share in specific places, not from a rising market.
- **Background:** Delta Community Credit Union (DCCU) is Georgia's largest credit union, with roughly 1,100 mortgage originations per year, conventional and jumbo only (no FHA/VA/USDA). Vendor analytics (e.g., Finastra's Mortgagebot Data Insights) benchmark a lender's own applicants against peers. That is an inward view.
- **Customer need:** The Chief Lending Officer (CLO) sets annual priorities: where to spend marketing dollars, where to place loan officers, which competitors to target. DCCU's own pipeline can't answer these questions, because the borrowers it loses never appear in its systems. The CLO needs an outside-in view of the market.

## 2. User and decision
- **User:** DCCU CLO.
- **Decision:** Where should DCCU focus mortgage growth next year, and against which competitors?
- **Strategic choice the outputs must inform:** build depth inside the current 20-county field of membership, expand the field of membership into another county, or both. Expansion is a real lever: DCCU applies to the Georgia Department of Banking and Finance for each new county and has expanded several times (11 → 14 → 16 → 20 counties).
- **Scope:** the data covers all of Georgia. **Primary focus: growth within the 20 FOM counties.** Secondary: opportunities anywhere else in Georgia.
- **Workflow stage:** annual/quarterly planning. A strategic tool, not an operational one; HMDA is annual and lagged.

### Key domain fact
Membership is defined by the **person** (lives or works in an eligible county, Delta employee or retiree, Select Employer Group, family member), not by the property or a branch. HMDA locates loans by **property** tract. So DCCU can and does lend on properties outside its membership counties. Tracts outside the footprint are reachable, just harder to reach.

### User stories
1. As the CLO, I want to see DCCU's share by neighborhood so I know where we're strong and weak.
2. As the CLO, I want a ranked list of high-volume areas where we underperform, so I can target marketing.
3. As the CLO, I want to know who wins in those areas, so I know whom we're competing against.
4. As the CLO, I want to see how share relates to branch proximity, so I can decide where to add loan officers or branches.
5. As the CLO, I want to see whether our position is improving or slipping, year over year.
6. As the CLO, I want to compare the growth available from deepening share inside our footprint against the growth from adding a county, so I can decide where to invest, or whether to file for a field-of-membership expansion.

## 3. Goals and success metrics
- The CLO can name **three concrete actions** from the outputs (the test for `FINDINGS.md`).
- `FINDINGS.md` ends with an explicit **depth vs. expansion vs. both** recommendation, with the numbers behind it.
- DCCU's yearly origination totals reconcile to its published HMDA totals, within a documented tolerance.
- The full pipeline rebuilds from raw downloads with one command.
- Every exclusion and gap is logged in `DATA_QUALITY.md`.

## 4. Requirements (v1)
| # | Requirement | Story |
|---|---|---|
| R1 | Tract map of DCCU share: FOM counties (primary) plus a statewide view | 1 |
| R2 | Opportunity table: top 25 tracts by opportunity score, top 3 competitors each (CSV) | 2, 3 |
| R3 | Tag every tract as inside or outside DCCU's field-of-membership (FOM) counties. Compare DCCU share inside vs. outside to estimate how much the membership boundary suppresses share | 2, 6 |
| R3a | Depth vs. expansion comparison: total opportunity inside the FOM vs. a county scorecard for every non-FOM Georgia county (market volume, DCCU share, households, distance to nearest branch, adjacency to FOM) | 6 |
| R4 | Share by distance band from nearest DCCU branch | 4 |
| R5 | Year-over-year share trend, FOM-wide, statewide and per tract, 2022 onward | 5 |
| R6 | Household density per tract (households per square mile) on the map and in the table | 1, 2 |
| R7 | `FINDINGS.md` (≤ 1 page, closing with the depth vs. expansion recommendation) and `DATA_QUALITY.md` | all |

## 5. Non-goals (v1)
Pricing/rate comparison, underserved-area analysis, fair-lending analysis, forecasting, interactive dashboards, Finastra/Mortgagebot data.

### Future phases (ideas, not commitments)
- **Underserved-area index:** tracts with little lending relative to potential demand. Candidate inputs: penetration (originations per 1,000 owner-occupied units), applications per 1,000 households, denial rates and reasons, lender count per tract, share of high-cost/nonbank lending, and Census renter households with incomes high enough to buy. Build on income and lending data, not neighborhood racial composition, and route through compliance review before it informs decisions (fair-lending/redlining risk).
- **Pricing:** HMDA includes interest rate, rate spread, total loan costs, discount points and lender credits for originated loans, so a partial comparison of DCCU vs. competitors is possible. Limits: annual and lagged; no credit score in public data, so comparisons can only control for loan-to-value, debt-to-income, loan amount and product; it shows what borrowers paid, not current rate sheets.

## 6. Open questions
- ~~Exact current list of DCCU field-of-membership counties~~ Resolved 2026-10-26: 20 counties from DCCU's eligibility page, stored in `config/fom_counties.csv`. The current list is applied to all years (DCCU expanded over time; logged as a limitation).
- ~~Latest published HMDA year~~ Resolved 2026-10-26: 2025, so v1 covers 2022–2025.
- Opportunity benchmark under a statewide market: `metro_share` (now statewide share) is diluted by counties where DCCU barely lends. Decide in Phase 3 whether to benchmark `opportunity_score` to DCCU's FOM-wide share instead.

---

## Appendix A: Technical spec

### Data sources
- **HMDA loan-level data:** CFPB Data Browser API (`https://ffiec.cfpb.gov/v2/data-browser-api/view/csv`).
  - **Years:** every published year from 2022 onward. 2022+ uses 2020 census tract boundaries, so tracts are comparable across years. Do not pull 2018–2021 (2010 tracts).
  - **Geography:** the market is all 159 Georgia counties (state FIPS 13), kept as a fixed county list in `config/ga_counties.csv`. Each county is tagged `fom_flag` and `atlanta_msa_flag`. The Atlanta MSA tag comes from OMB's 2023 delineation (CBSA 12060) and is used for display only; it does not define the market.
  - Use `/view/filers` to map LEIs to lender names. Confirm DCCU's LEI there; do not hard-code a guess.
- **Households:** Census ACS 5-year, table B11001 (total households, `B11001_001E`), tract level. Use the latest 5-year release on 2020 tracts. Census API key optional at this volume.
- **Tract geometry and land area:** Census TIGER/Line or cartographic boundary files, Georgia, 2020 tracts. Use `ALAND` for density and internal points for distance.
- **Branch locations:** NCUA quarterly call report data (branch information file). Geocode addresses if lat/long is missing.
- **Field-of-membership counties:** DCCU website; store as a small config file.

### Market definition (apply to the whole market, not just DCCU)
- Conventional loans only (DCCU offers no FHA/VA/USDA).
- First lien, 1–4 units, site-built, principal residence.
- Purchase and refinance, reported combined and split. Refinance includes cash-out refinance (`loan_purpose` 31 and 32).
- Closed-end loans only: exclude HELOCs (`open-end_line_of_credit = 1`), including first-lien HELOCs. Also exclude reverse mortgages and business-purpose loans.
- Rows where a lender reports these flags as exempt (`1111`) are kept and counted in `DATA_QUALITY.md`.
- Originations only (`action_taken = 1`) for share. Exclude purchased loans (`action_taken = 6`) everywhere.

### Metrics
- `tract_share` = DCCU originations ÷ market originations in the tract, per year and pooled across years.
- `metro_share` = DCCU's share across the full market.
- `opportunity_score` = tract market originations × max(0, metro_share − tract_share). Read it as "loans gained if this tract matched DCCU's own average." Compute on pooled years to reduce noise.
- `household_density` = households ÷ land area (sq mi). Raw household counts are not density, since tracts are drawn to similar population sizes.
- `penetration` = market originations per 1,000 owner-occupied units (HMDA tract field).
- Minimum volume: score only tracts with ≥ 20 pooled market originations. Tune and document.
- Branch distance: miles from tract internal point to nearest DCCU branch (haversine). Bands: 0–2, 2–5, 5–10, 10+.
- `fom_flag` = tract's county is in DCCU's FOM config list.
- **Depth opportunity** = sum of `opportunity_score` across FOM tracts.
- **Expansion opportunity (per non-FOM county)** = county market originations × (DCCU's FOM-wide share − DCCU's current share in that county). Read it as "loans gained if this county performed like the footprint after joining." Label it an upper bound: new counties rarely reach footprint share quickly.
- Compare depth and expansion in loans per year, side by side, in `FINDINGS.md`.

### Data quality checks (log results; never drop silently)
- Missing or `NA` census tract.
- Fields reported as `Exempt` (partially exempt lenders); note which competitors are affected.
- LEI and lender name changes across years (mergers, renames).
- Any tract present in HMDA but missing from TIGER or ACS, or vice versa.
- ACS margins of error on small tracts; flag high-MOE household counts.
- DCCU totals per year vs. published HMDA totals; investigate big misses.

### Tech and working agreements
- Python: pandas, geopandas, requests; matplotlib or folium for maps.
- Layout: `config/` (county lists), `data/raw/` (git-ignored), `data/processed/`, `src/` (one script per stage), `outputs/`.
- Phases, with a check-in after each: (1) download and validate, (2) market definition, (3) share, trend and opportunity metrics, (4) households, density and branch distance, (5) map, table and findings.
- Cache downloads; never re-hit an API if the raw file exists.
- Before coding each phase, state the plan and wait for approval.
