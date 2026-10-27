# PRD: Mortgage Growth Map for Delta Community Credit Union

## 1. Why (business case)
- **Business driver:** Mortgage lending is a share fight with thin margins. Growth for a credit union comes from winning share in specific places, not from a rising market.
- **Background:** Delta Community Credit Union (DCCU) is Georgia's largest credit union, with roughly 1,100 mortgage originations per year, conventional and jumbo only (no FHA/VA/USDA). Vendor analytics (e.g., Finastra's Mortgagebot Data Insights) benchmark a lender's own applicants against peers. That is an inward view.
- **Customer need:** The Chief Lending Officer (CLO) sets annual priorities: where to spend marketing dollars, where to place loan officers, which competitors to target. DCCU's own pipeline can't answer these questions, because the borrowers it loses never appear in its systems. The CLO needs an outside-in view of the market.

## 2. User and decision
- **User:** DCCU CLO.
- **Decision:** Where should DCCU focus mortgage growth next year, and against which competitors?
- **Strategic choice the outputs must inform:** build depth inside the current 20-county field of membership, expand the field of membership into another county, or both. Expansion is a real lever: DCCU applies to the Georgia Department of Banking and Finance for each new county and has expanded several times (11 → 14 → 16 → 20 counties).
- **Scope:** the data covers all of Georgia, split into two analyses:
  - **Depth (primary): the 20 FOM counties.** Each tract is held to DCCU's FOM-wide share, the standard where its strategy is already in place. Outcomes are near-term actions where DCCU already operates: marketing, loan officer placement, branch locations.
  - **Expansion (secondary): the 139 non-FOM counties.** How much loan volume would DCCU add if it entered a county and reached its FOM share there? Outcomes inform a long-term strategy: choose counties, apply to the regulator, build a presence. This is guidance for the CLO; real estate, site selection and the regulatory filing itself are out of scope.
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
7. As the CLO, I want expansion candidates ranked by metro area, by urban vs. rural, and by growth clusters, so I can shortlist counties for a field-of-membership filing.

## 3. Goals and success metrics
- The CLO can name **three concrete actions** from the outputs (the test for `FINDINGS.md`).
- `FINDINGS.md` ends with an explicit **depth vs. expansion vs. both** recommendation, with the numbers behind it.
- DCCU's yearly origination totals reconcile to its published HMDA totals, within a documented tolerance.
- The full pipeline rebuilds from raw downloads with one command.
- Every exclusion and gap is logged in `DATA_QUALITY.md`.

## 4. Requirements (v1)
| # | Requirement | Story |
|---|---|---|
| R1 | Tract map of DCCU share in the scoring year: FOM counties (primary) plus a statewide view | 1 |
| R2 | Opportunity table: top 25 FOM tracts by scoring-year opportunity score, top 3 competitors each (CSV), with a stability check | 2, 3 |
| R3 | Tag every tract as inside or outside DCCU's field-of-membership (FOM) counties. Compare DCCU share inside vs. outside to estimate how much the membership boundary suppresses share | 2, 6 |
| R3a | Depth vs. expansion comparison: total depth opportunity inside the FOM vs. a county scorecard for every non-FOM Georgia county (market volume, DCCU current share, expansion gain at the target share, market group, urban/rural tier, population growth, purchase-market change, households, distance to nearest branch, adjacency to FOM) | 6 |
| R3b | Expansion rankings: non-FOM counties ranked by market group (e.g., Savannah, Macon–Warner Robins), by urban/rural tier, and as growth clusters of neighboring growing counties | 7 |
| R4 | Share by distance band from nearest DCCU branch | 4 |
| R5 | Share trend 2022–2025, FOM-wide, statewide and per county: purchase, refinance and combined share, shown with each year's refinance/purchase mix. Label 2022 as the tail of the refi boom | 5 |
| R6 | Household density per tract (households per square mile) on the map and in the table | 1, 2 |
| R7 | `FINDINGS.md` (≤ 1 page, closing with the depth vs. expansion recommendation) and `DATA_QUALITY.md` | all |

## 5. Non-goals (v1)
Pricing/rate comparison, underserved-area analysis, fair-lending analysis, forecasting, interactive dashboards, Finastra/Mortgagebot data. For expansion: real estate, site selection, and the regulatory filing and compliance work.

### Future phases (ideas, not commitments)
- **Underserved-area index:** tracts with little lending relative to potential demand. Candidate inputs: penetration (originations per 1,000 owner-occupied units), applications per 1,000 households, denial rates and reasons, lender count per tract, share of high-cost/nonbank lending, and Census renter households with incomes high enough to buy. Build on income and lending data, not neighborhood racial composition, and route through compliance review before it informs decisions (fair-lending/redlining risk).
- **Pricing:** HMDA includes interest rate, rate spread, total loan costs, discount points and lender credits for originated loans, so a partial comparison of DCCU vs. competitors is possible. Limits: annual and lagged; no credit score in public data, so comparisons can only control for loan-to-value, debt-to-income, loan amount and product; it shows what borrowers paid, not current rate sheets.

## 6. Open questions
- ~~Exact current list of DCCU field-of-membership counties~~ Resolved 2026-10-26: 20 counties from DCCU's eligibility page, stored in `config/fom_counties.csv`. The current list is applied to all years (DCCU expanded over time; logged as a limitation).
- ~~Latest published HMDA year~~ Resolved 2026-10-26: 2025, so v1 covers 2022–2025.
- ~~Opportunity benchmark under a statewide market~~ Resolved 2026-10-27: benchmark to DCCU's FOM-wide share (`fom_share`), not statewide share. Statewide share is diluted by counties where most people can't join DCCU (2025: 1.43% statewide vs. 1.96% FOM). Expansion uses the same share, rounded to 2%.
- ~~Pool years for scoring?~~ Resolved 2026-10-27: no. Opportunity is scored on the latest year (2025), the closest thing to current state. 2022–2025 is used for trends.
- ~~Trend level~~ Resolved 2026-10-27: per county, not per tract. DCCU makes under one loan per FOM tract a year (2025: 823 of 1,433 FOM tracts had none), so tract-level year-over-year share is noise.
- ~~Expansion groupings~~ Resolved 2026-10-27: market groups use the hybrid OMB rule, urban/rural uses OMB's three tiers, growth uses Census population estimates with HMDA purchase volume as a cross-check (definitions in Appendix A).
- Minimum volume for tract scoring: the old ≥ 20 pooled threshold no longer applies. Set it in Phase 3 from 2025 volumes.

---

## Appendix A: Technical spec

### Data sources
- **HMDA loan-level data:** CFPB Data Browser API (`https://ffiec.cfpb.gov/v2/data-browser-api/view/csv`).
  - **Years:** every published year from 2022 onward. 2022+ uses 2020 census tract boundaries, so tracts are comparable across years. Do not pull 2018–2021 (2010 tracts).
  - **Geography:** the market is all 159 Georgia counties (state FIPS 13), kept as a fixed county list in `config/ga_counties.csv`. Each county is tagged `fom_flag` and `atlanta_msa_flag`. The Atlanta MSA tag comes from OMB's 2023 delineation (CBSA 12060) and is used for display only; it does not define the market. The same OMB file supplies each county's CBSA, CSA, `urban_rural_tier` and `market_group` (see Metrics).
  - Use `/view/filers` to map LEIs to lender names. Confirm DCCU's LEI there; do not hard-code a guess.
- **Households:** Census ACS 5-year, table B11001 (total households, `B11001_001E`), tract level. Use the latest 5-year release on 2020 tracts. Census API key optional at this volume.
- **Tract geometry and land area:** Census TIGER/Line or cartographic boundary files, Georgia, 2020 tracts. Use `ALAND` for density and internal points for distance.
- **Branch locations:** NCUA quarterly call report data (branch information file). Geocode addresses if lat/long is missing.
- **Field-of-membership counties:** DCCU website; store as a small config file.
- **County population:** Census Population Estimates Program, county totals from the 2020 base to the latest vintage. Confirm the latest vintage when downloading.
- **County adjacency:** Census county adjacency file, latest release.

### Market definition (apply to the whole market, not just DCCU)
- Conventional loans only (DCCU offers no FHA/VA/USDA).
- First lien, 1–4 units, site-built, principal residence.
- Purchase and refinance, reported combined and split. Refinance includes cash-out refinance (`loan_purpose` 31 and 32).
- Closed-end loans only: exclude HELOCs (`open-end_line_of_credit = 1`), including first-lien HELOCs. Also exclude reverse mortgages and business-purpose loans.
- Rows where a lender reports these flags as exempt (`1111`) are kept and counted in `DATA_QUALITY.md`.
- Originations only (`action_taken = 1`) for share. Exclude purchased loans (`action_taken = 6`) everywhere.

### Metrics
- `scoring_year` = the latest HMDA year (2025 in v1). Depth and expansion are scored on this year only; earlier years feed the trend.
- `tract_share` = DCCU originations ÷ market originations in the tract, per year.
- `fom_share` = DCCU originations ÷ market originations across all FOM counties in the scoring year (1.96% in 2025). Computed from the data each run, not hard-coded. It replaces `metro_share`, which a statewide market dilutes.
- `opportunity_score` (FOM tracts) = tract market originations × max(0, `fom_share` − `tract_share`), scoring year. Read it as "loans gained if this tract matched DCCU's FOM average."
- Stability check: rebuild the top 25 using tract share from the two latest years combined, and report the overlap with the single-year top 25. Heavy reshuffling means single-year scores are too noisy to rank on.
- `household_density` = households ÷ land area (sq mi). Raw household counts are not density, since tracts are drawn to similar population sizes.
- `penetration` = market originations per 1,000 owner-occupied units (HMDA tract field).
- Minimum volume: score only tracts with enough scoring-year market originations. Set the threshold in Phase 3 from 2025 volumes and document it.
- Branch distance: miles from tract internal point to nearest DCCU branch (haversine). Bands: 0–2, 2–5, 5–10, 10+.
- `fom_flag` = tract's county is in DCCU's FOM config list.
- `market_group` = the county's OMB 2023 combined statistical area (CSA) if it has one, else its CBSA. Exception: the Atlanta CSA is split back into its CBSAs, so Athens, Gainesville, Rome, LaGrange etc. stand alone, and the Atlanta MSA counties outside the FOM form one group. Counties in no CBSA have no market group; they rank in the rural tier.
- `urban_rural_tier` = metro, micro or rural: the county's OMB 2023 CBSA type, or rural if it is in no CBSA.
- `pop_growth` = county population change, 2020 to the latest estimate year (%).
- `purchase_market_change` = change in county purchase originations, 2023 → 2025. A cross-check on population growth; it mostly tracks interest rates.
- `growth_cluster` = neighboring counties (county adjacency file) that are all above a growth threshold. Set the threshold in Phase 4 and document it.
- **Depth opportunity** = sum of `opportunity_score` across FOM tracts, scoring year.
- **Expansion gain (per non-FOM county)** = county market originations × max(0, `expansion_target_share` − DCCU's current share in that county), scoring year. `expansion_target_share` = 2.0%, `fom_share` rounded: a named planning assumption in config. Read it as "loans added per year if DCCU entered this county and reached its FOM share there." Label it an upper bound: new counties take years to reach footprint share.
- **Trend** = DCCU share per year, 2022–2025, FOM-wide, statewide and per county; purchase, refinance and combined; shown with each year's market refinance/purchase mix. No per-tract trend: DCCU averages under one loan per FOM tract a year.
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
- Phases, with a check-in after each: (1) download and validate, (2) market definition, (3) share, trend and opportunity metrics, including expansion gain by market group and tier, (4) households, density, branch distance, population growth, adjacency and growth clusters, (5) map, table and findings.
- Cache downloads; never re-hit an API if the raw file exists.
- Before coding each phase, state the plan and wait for approval.
