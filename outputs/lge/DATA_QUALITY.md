# Data quality log: LGE Community Credit Union

Checks for this lender. Market-wide checks (Phases 1-2: downloads, tracts, market definition) are in the repo's DATA_QUALITY.md.

<!-- phase1_lender:start -->
## Phase 1: lender presence and branches

### 2–3. LGE presence and reconciliation
`filers_count` is LGE's Georgia HMDA record count from the filers API (all action types). It should equal `records_in_ga` from the nationwide LEI download. Records outside GA are loans on out-of-state properties.

|   year | in_filers_list   | filers_name                |   filers_count |   records_downloaded |   records_in_ga |   records_in_footprint |   ga_records_no_county |   originations |   originations_in_footprint | reconciles   |
|-------:|:-----------------|:---------------------------|---------------:|---------------------:|----------------:|-----------------------:|-----------------------:|---------------:|----------------------------:|:-------------|
|   2022 | True             | LGE COMMUNITY              |            520 |                  664 |             520 |                    449 |                      0 |            322 |                         273 | True         |
|   2023 | True             | LGE COMMUNITY CREDIT UNION |            921 |                  921 |             921 |                    802 |                      0 |            567 |                         499 | True         |
|   2024 | True             | LGE COMMUNITY CREDIT UNION |           1131 |                 1134 |            1131 |                    947 |                      0 |            763 |                         637 | True         |
|   2025 | True             | LGE COMMUNITY CREDIT UNION |           1058 |                 1059 |            1058 |                    916 |                      0 |            744 |                         643 | True         |

### 8. LGE branches (NCUA `call-report-data-2026-06.zip`)
Charter 68581 (`LGE COMMUNITY` in NCUA). Branch records: 19. **No lat/long columns: branches need geocoding in Phase 4.**

### Known limitations
- The FOM list is today's 15 counties, applied to every year. A lender that added counties over time has its early-year footprint share understated for the newer counties.
<!-- phase1_lender:end -->

<!-- phase2_lender:start -->
## Phase 2: lender within the market definition

### Product filter: conventional (`loan_types` ['1'])
LGE's market is every lender's conventional loans, so the filter applies to competitors too. Below: LGE's own GA originations by loan type, after the other market filters (`phase2_checks/product_filter.csv`). A large share left out would mean the config misses part of LGE's lending.

|   year |   conventional |   FHA |   VA |   USDA |   lender_originations |   kept |   kept_share |
|-------:|---------------:|------:|-----:|-------:|----------------------:|-------:|-------------:|
|   2022 |            180 |     0 |    0 |      0 |                   180 |    180 |            1 |
|   2023 |             90 |     0 |    0 |      0 |                    90 |     90 |            1 |
|   2024 |            207 |     0 |    0 |      0 |                   207 |    207 |            1 |
|   2025 |            346 |     0 |    0 |      0 |                   346 |    346 |            1 |

### LGE through the market filters (2025; all years in `phase2_checks/filter_waterfall.csv`)
The same filters apply to every lender. `conventional` is LGE's product filter; `_all` columns count the market as LGE defines it, `_lender` columns LGE's own rows. Each row is the count after every filter above it.

| step                             |   rows_all |   originations_all |   rows_lender |   originations_lender |   originations_removed |
|:---------------------------------|-----------:|-------------------:|--------------:|----------------------:|-----------------------:|
| start: all GA rows with a county |     511121 |             241969 |          1058 |                   743 |                      0 |
| exclude_purchased                |     447297 |             241969 |          1058 |                   743 |                      0 |
| conventional                     |     305450 |             166984 |          1058 |                   743 |                      0 |
| first_lien                       |     204657 |             117839 |           545 |                   418 |                    325 |
| units_1_to_4                     |     203451 |             116888 |           543 |                   416 |                      2 |
| site_built                       |     183778 |             112444 |           541 |                   414 |                      2 |
| principal_residence              |     146107 |              89940 |           526 |                   400 |                     14 |
| purchase_or_refi                 |     128938 |              82934 |           457 |                   346 |                     54 |
| closed_end                       |     124968 |              80858 |           457 |                   346 |                      0 |
| not_reverse                      |     124790 |              80758 |           457 |                   346 |                      0 |
| not_business                     |     124660 |              80682 |           457 |                   346 |                      0 |

### LGE reconciliation with the HMDA API
LGE's GA originations with one market filter at a time, our data vs. the API's own count (the API allows at most two filters, so the full definition can't be checked in one query). Occupancy can't be checked: the API ignores that filter.

Mismatches: **0** of 24.

| filter               | api_applied_filter   |   lender_api |   lender_ours | match   |
|:---------------------|:---------------------|-------------:|--------------:|:--------|
| none                 | True                 |          743 |           743 | True    |
| loan_types           | True                 |          743 |           743 | True    |
| lien_statuses        | True                 |          418 |           418 | True    |
| total_units          | True                 |          741 |           741 | True    |
| construction_methods | True                 |          740 |           740 | True    |
| loan_purposes        | True                 |          440 |           440 | True    |

### Market size and LGE (conventional originations, after all filters)
|   year | scope     |   market_originations |   market_purchase |   market_refinance |   market_no_tract |   lenders |   lender_originations |   lender_purchase |   lender_refinance |   lender_no_tract |
|-------:|:----------|----------------------:|------------------:|-------------------:|------------------:|----------:|----------------------:|------------------:|-------------------:|------------------:|
|   2022 | statewide |                138169 |             85616 |              52553 |                61 |       875 |                   180 |                76 |                104 |                 0 |
|   2022 | footprint |                 48466 |             30533 |              17933 |                20 |       637 |                   147 |                59 |                 88 |                 0 |
|   2023 | statewide |                 76604 |             63173 |              13431 |                32 |       828 |                    90 |                70 |                 20 |                 0 |
|   2023 | footprint |                 26667 |             22558 |               4109 |                 8 |       575 |                    66 |                50 |                 16 |                 0 |
|   2024 | statewide |                 78334 |             61581 |              16753 |                20 |       781 |                   207 |               144 |                 63 |                 0 |
|   2024 | footprint |                 27338 |             22059 |               5279 |                 4 |       551 |                   145 |                99 |                 46 |                 0 |
|   2025 | statewide |                 80682 |             58062 |              22620 |                46 |       807 |                   346 |               185 |                161 |                 0 |
|   2025 | footprint |                 27645 |             20461 |               7184 |                11 |       586 |                   284 |               152 |                132 |                 0 |
<!-- phase2_lender:end -->

<!-- phase3:start -->
## Phase 3: share, trend and opportunity metrics

### 1. Totals reconcile
County sums match the Phase 2 market-size table for every year, scope and measure; scoring-year tracts plus unplaced rows match the totals. Mismatches: **0** of 52 (the script stops on any mismatch). Details: `phase3_checks/1_totals_reconciliation.csv`.

### 2. Benchmark
`footprint_share` (2025) = 284 / 27,645 = **1.03%**. Expansion uses `expansion.target_share` = 1.0% from the lender config (planning assumption).

### 3-4. Originations outside tract metrics (2025)
They stay in county, FOM and statewide figures but have no tract to score. All 2,796 TIGER tracts are in `tract_metrics.csv`; 14 FOM tracts had no 2025 originations and are kept with zeros.

| scope     |   no_tract_market |   no_tract_lender |   not_in_tiger_market |   not_in_tiger_tracts |
|:----------|------------------:|------------------:|----------------------:|----------------------:|
| statewide |                46 |                 0 |                     0 |                     0 |
| footprint |                11 |                 0 |                     0 |                     0 |

### 5. Minimum volume (FOM tracts, 2025)
No tract is dropped. Tracts under 20 market originations get `low_volume = True` (greyed out on the map, left out of share statistics). The top 25 all have 76+ market originations, so the rule doesn't affect the ranking.

| threshold         |   tracts |   market_loans |   lender_loans |   opportunity |   pct_of_opportunity |   tracts_share_over_10pct |
|:------------------|---------:|---------------:|---------------:|--------------:|---------------------:|--------------------------:|
| zero originations |       14 |              0 |              0 |           0   |                  0   |                         0 |
| < 10              |       72 |            417 |              2 |           4.1 |                  2.2 |                         2 |
| < 15              |      130 |           1116 |             12 |          10.2 |                  5.3 |                         3 |
| < 20              |      208 |           2424 |             24 |          21.7 |                 11.3 |                         4 |
| < 30              |      351 |           5918 |             50 |          52.5 |                 27.4 |                         5 |

### 6. Stability of the top 25
**20 of 25** tracts are in the top 25 both on 2025 share and on 2024-2025 combined share (`stable_top25 = True`). Most top tracts have zero or one LGE loan, so one loan more or less moves a tract many places. County totals are steadier: the largest move between the two county rankings is **2 place(s)** (`depth_by_county.csv`), so findings lead with counties and use tracts to say where within a county. Details: `phase3_checks/6_stability_top25.csv`.

### 7. Competitor ties
Ties on loan count are broken by the lender's FOM-wide 2025 volume. A tie decided the 3rd competitor in **6 of 25** top tracts (472 of 789 FOM tracts).

### 8. Lender merger review (open item 3)
35 non-LGE lenders were in the FOM top 25 in at least one year; **14** are flagged (a year with no loans, or FOM purchase share moving by more than 1.5x year over year). Review by hand for mergers. Full list: `phase3_checks/8_lender_merger_review.csv`.

| name                                  |   loans_2022 |   loans_2023 |   loans_2024 |   loans_2025 | top25_years            | years_with_no_loans   | purchase_share_jumps             |
|:--------------------------------------|-------------:|-------------:|-------------:|-------------:|:-----------------------|:----------------------|:---------------------------------|
| CROSSCOUNTRY MORTGAGE, INC.           |          221 |          260 |          361 |          502 | 2023, 2024, 2025       |                       | 2022->2023 x1.9                  |
| MOVEMENT MORTGAGE, LLC                |          899 |          650 |          748 |          478 | 2022, 2023, 2024, 2025 |                       | 2024->2025 x0.6                  |
| DELTA COMMUNITY CREDIT UNION          |          450 |          204 |          346 |          428 | 2022, 2024, 2025       |                       | 2022->2023 x1.5; 2023->2024 x1.6 |
| KIND LENDING, LLC                     |          134 |           89 |          183 |          269 | 2025                   |                       | 2023->2024 x2.0                  |
| ZILLOW HOME LOANS, LLC                |           77 |          167 |          254 |          263 | 2024, 2025             |                       | 2022->2023 x5.5; 2023->2024 x1.6 |
| PROVIDENT FUNDING ASSOCIATES, L.P.    |          153 |          225 |          242 |          231 | 2024                   |                       | 2022->2023 x3.1                  |
| GUARANTEED RATE, INC.                 |          306 |          446 |          368 |          227 | 2023, 2024             |                       | 2022->2023 x2.5; 2024->2025 x0.6 |
| SouthState Bank, National Association |          616 |          231 |          209 |          204 | 2022, 2023             |                       | 2022->2023 x0.7                  |
| DHI MORTGAGE COMPANY, LTD.            |          403 |          192 |          242 |          184 | 2024                   |                       | 2022->2023 x0.6                  |
| Broker Solutions, Inc.                |          554 |          149 |          230 |          148 | 2022                   |                       | 2022->2023 x0.5; 2023->2024 x1.5 |
| Synovus Bank                          |          414 |          295 |          127 |          131 | 2023                   |                       | 2023->2024 x0.4                  |
| AmeriSave Mortgage Corporation        |          522 |          101 |           50 |           86 | 2022                   |                       | 2022->2023 x0.2; 2023->2024 x0.3 |
| HOMESTAR FINANCIAL CORPORATION        |          962 |          309 |            0 |            0 | 2022, 2023             | 2024, 2025            | 2022->2023 x0.5                  |
| HOME POINT FINANCIAL CORPORATION      |          583 |            0 |            0 |            0 | 2022                   | 2023, 2024, 2025      |                                  |

### 9. Market groups and tiers
Hybrid rule (PRD Appendix A): CSA where one exists, else CBSA, except the CSA that holds the footprint's main metro area, which is split into its CBSAs. Main metro area: **Atlanta-Sandy Springs-Roswell, GA** (CBSA 12060), 6 of 15 FOM counties and 88.3% of FOM originations in 2025. Split CSA: Atlanta--Athens-Clarke County--Sandy Springs, GA-AL. Each county's group is in `counties.csv`.

| market_group                           | urban_rural_tier   |   counties |   footprint_counties | county_names                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|:---------------------------------------|:-------------------|-----------:|---------------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| (no metro/micro area)                  | rural              |         53 |                    0 | Appling, Bacon, Baker, Banks, Berrien, Bleckley, Calhoun, Candler, Charlton, Clay, Clinch, Cook, Dodge, Dooly, Early, Elbert, Emanuel, Fannin, Franklin, Gilmer, Glascock, Greene, Hancock, Hart, Irwin, Jeff Davis, Jefferson, Jenkins, Lamar, Macon, Miller, Mitchell, Pulaski, Putnam, Rabun, Randolph, Screven, Seminole, Taliaferro, Tattnall, Taylor, Telfair, Towns, Treutlen, Union, Warren, Washington, Webster, Wheeler, White, Wilcox, Wilkes, Wilkinson |
| Atlanta-Sandy Springs-Roswell, GA      | metro              |         29 |                    6 | Barrow, Bartow, Butts, Carroll, Cherokee, Clayton, Cobb, Coweta, Dawson, DeKalb, Douglas, Fayette, Forsyth, Fulton, Gwinnett, Haralson, Heard, Henry, Jasper, Lumpkin, Meriwether, Morgan, Newton, Paulding, Pickens, Pike, Rockdale, Spalding, Walton                                                                                                                                                                                                              |
| Macon-Bibb County--Warner Robins, GA   | metro              |          7 |                    0 | Bibb, Crawford, Houston, Jones, Monroe, Peach, Twiggs                                                                                                                                                                                                                                                                                                                                                                                                               |
| Columbus-Auburn-Opelika, GA-AL         | metro              |          6 |                    0 | Chattahoochee, Harris, Marion, Muscogee, Stewart, Talbot                                                                                                                                                                                                                                                                                                                                                                                                            |
| Savannah-Hinesville-Statesboro, GA     | metro              |          5 |                    0 | Bryan, Chatham, Effingham, Liberty, Long                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Augusta-Richmond County, GA-SC         | metro              |          5 |                    0 | Burke, Columbia, Lincoln, McDuffie, Richmond                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Chattanooga-Cleveland-Dalton, TN-GA-AL | metro              |          5 |                    5 | Catoosa, Dade, Murray, Walker, Whitfield                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Albany, GA                             | metro              |          4 |                    0 | Dougherty, Lee, Terrell, Worth                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Valdosta, GA                           | metro              |          4 |                    0 | Brooks, Echols, Lanier, Lowndes                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Athens-Clarke County, GA               | metro              |          4 |                    0 | Clarke, Madison, Oconee, Oglethorpe                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Savannah-Hinesville-Statesboro, GA     | micro              |          3 |                    0 | Bulloch, Evans, Wayne                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Brunswick-St. Simons, GA               | metro              |          3 |                    0 | Brantley, Glynn, McIntosh                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Americus, GA                           | micro              |          2 |                    0 | Schley, Sumter                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Tifton, GA                             | micro              |          2 |                    0 | Tift, Turner                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Vidalia, GA                            | micro              |          2 |                    0 | Montgomery, Toombs                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Thomasville, GA                        | micro              |          2 |                    0 | Grady, Thomas                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Waycross, GA                           | micro              |          2 |                    0 | Pierce, Ware                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Dublin, GA                             | micro              |          2 |                    0 | Johnson, Laurens                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Douglas, GA                            | micro              |          2 |                    0 | Atkinson, Coffee                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Calhoun, GA                            | micro              |          1 |                    1 | Gordon                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Jacksonville-Kingsland-Palatka, FL-GA  | micro              |          1 |                    0 | Camden                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Gainesville, GA                        | metro              |          1 |                    0 | Hall                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Fitzgerald, GA                         | micro              |          1 |                    0 | Ben Hill                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Eufaula, AL-GA                         | micro              |          1 |                    0 | Quitman                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Cordele, GA                            | micro              |          1 |                    0 | Crisp                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Cornelia, GA                           | micro              |          1 |                    0 | Habersham                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Cedartown, GA                          | micro              |          1 |                    1 | Polk                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Chattanooga-Cleveland-Dalton, TN-GA-AL | micro              |          1 |                    1 | Chattooga                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Moultrie, GA                           | micro              |          1 |                    0 | Colquitt                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Rome, GA                               | metro              |          1 |                    1 | Floyd                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| LaGrange, GA-AL                        | micro              |          1 |                    0 | Troup                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Milledgeville, GA                      | micro              |          1 |                    0 | Baldwin                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Jefferson, GA                          | micro              |          1 |                    0 | Jackson                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Thomaston, GA                          | micro              |          1 |                    0 | Upson                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Tallahassee-Bainbridge, FL-GA          | micro              |          1 |                    0 | Decatur                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Toccoa, GA                             | micro              |          1 |                    0 | Stephens                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

### 10. Expansion edge cases
Non-FOM counties where LGE is already at or above 1% (expansion gain 0): none.

### 11. Lenders missing from the HMDA filers lists
LEIs with market originations that are missing from every cached HMDA `/view/filers` list, named from GLEIF instead (Phase 2 builds `lenders.csv`). Any LEI GLEIF can't name shows as `LEI ... (no name in filers list)`. All originations are kept.

|   year |   originations |   footprint_originations | name                                 | name_source   |
|-------:|---------------:|-------------------------:|:-------------------------------------|:--------------|
|   2025 |             62 |                       39 | PRC MORTGAGE, LLC                    | gleif         |
|   2025 |             55 |                        0 | Landmark 24 Mortgage, LLC            | gleif         |
|   2025 |             38 |                        7 | BRIDGEWAY LENDING PARTNERS LLC       | gleif         |
|   2025 |             34 |                        8 | Loyal Trust Bank                     | gleif         |
|   2025 |             32 |                       11 | ADVANTAGEFIRST LENDING INC.          | gleif         |
|   2025 |              9 |                        1 | VERUS RESIDENTIAL LOANCO, LLC        | gleif         |
|   2025 |              8 |                        1 | ARDRI LLC                            | gleif         |
|   2025 |              5 |                        2 | Climate First Bank                   | gleif         |
|   2025 |              4 |                        2 | OBSIDIAN FINANCIAL SERVICES, INC.    | gleif         |
|   2025 |              3 |                        3 | AMERICAS MORTGAGE PROFESSIONALS, LLC | gleif         |
|   2025 |              2 |                        1 | ASPIRE HOME LOANS, LLC               | gleif         |
|   2025 |              2 |                        1 | THE LOCAL LENDER, LLC                | gleif         |
|   2025 |              1 |                        0 | Local Bank                           | gleif         |
|   2025 |              1 |                        0 | New Story Lending LLC                | gleif         |
|   2025 |              1 |                        0 | MARLIN MORTGAGE CAPITAL, LLC         | gleif         |

### 12. Builder-owned lenders (contestable market)
`config/builder_lenders.csv`, **pending your review**. Rows with `include = 1` are left out of the contestable market (`opportunity_score_contestable`); `include = 0` rows are candidates that show the builder pattern (almost no refinance, purchases packed into a few tracts) but are not confirmed. Included lenders made 630 of 27,645 FOM originations in 2025. Contestable `footprint_share` = **1.05%**. Depth opportunity: 191 loans on the full market, 193 on the contestable market.

| lender_name                        | builder                          |   include | basis                                                                               |   footprint_loans |   footprint_purchase_share_pct |
|:-----------------------------------|:---------------------------------|----------:|:------------------------------------------------------------------------------------|------------------:|-------------------------------:|
| DHI MORTGAGE COMPANY, LTD.         | D.R. Horton                      |         1 | builder-owned lender (DHI = D.R. Horton)                                            |               184 |                           0.9  |
| PULTE MORTGAGE LLC                 | PulteGroup                       |         1 | builder name in lender name                                                         |                71 |                           0.35 |
| LENNAR MORTGAGE, LLC               | Lennar                           |         1 | builder name in lender name                                                         |                99 |                           0.48 |
| TOLL BROTHERS MORTGAGE COMPANY     | Toll Brothers                    |         1 | builder name in lender name                                                         |               189 |                           0.92 |
| Taylor Morrison Home Funding, Inc. | Taylor Morrison                  |         1 | builder name in lender name                                                         |                47 |                           0.23 |
| NVR Mortgage Finance, Inc.         | NVR (Ryan Homes)                 |         1 | builder name in lender name                                                         |                32 |                           0.16 |
| INSPIRE HOME LOANS INC.            | Century Communities (to confirm) |         1 | believed builder-owned; data signature: 0% refi and 54% of GA purchases in 3 tracts |                 8 |                           0.04 |
| PRC MORTGAGE, LLC                  | unknown                          |         0 | data signature only: 2% refi and 80% of GA purchases in 3 tracts                    |                39 |                           0.19 |
| VICTORY MORTGAGE, L.L.C.           | unknown                          |         0 | data signature only: 1% refi and 60% of GA purchases in 3 tracts                    |                40 |                           0.2  |
| TRAILBLAZER MORTGAGE L.L.C.        | unknown                          |         0 | data signature only: 0% refi and 49% of GA purchases in 3 tracts                    |                42 |                           0.21 |
| Landmark 24 Mortgage, LLC          | unknown                          |         0 | data signature only: 0% refi and 45% of GA purchases in 3 tracts                    |                 0 |                           0    |
| First Heritage Mortgage, LLC       | unknown                          |         0 | data signature only: 4% refi and 42% of GA purchases in 3 tracts                    |               102 |                           0.48 |
| JET HOMELOANS, LP                  | unknown                          |         0 | data signature only: 0% refi and 27% of GA purchases in 3 tracts                    |                10 |                           0.05 |
<!-- phase3:end -->

<!-- phase4:start -->
## Phase 4: households, density, branch distance and growth

### 1. Branches and geocoding
NCUA snapshots: scoring year `2025-12` (share by distance) and current `2026-06` (expansion scorecard). In-scope Georgia branches: **18** and **18**. Excluded sites (`config/lenders/lge/branch_exclusions.csv`, plus out-of-state):

|   site_id | site_name   | state   | exclusion_reason                                                                                              |
|----------:|:------------|:--------|:--------------------------------------------------------------------------------------------------------------|
|     27758 | Home Office | GA      | corporate office without member services (NCUA: Corporate Office, MemberServices 0); not on LGE's branch list |

The Census Geocoder matched every in-scope branch except those below, whose coordinates are hand-placed in `config/lenders/lge/branch_coordinates.csv`, with the method for each (error a few hundred meters at most).

|   site_id | site_name   | address                |     lat |      lon | method                                                                                                                                                                                                     |
|----------:|:------------|:-----------------------|--------:|---------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|     27720 | Austell     | 2760 E West Connector  | 33.8664 | -84.6249 | Census Geocoder has no address range on East West Connector; OpenStreetMap (Nominatim) places LGE Community Credit Union at 2760 East-West Connector                                                       |
|     27726 | Acworth     | 3891 Cobb Pkwy NW      | 34.0498 | -84.7007 | Census Geocoder has no match for 3891 Cobb Pkwy NW; interpolated (0.95) between its matches for 3691 and 3901 Cobb Pkwy N                                                                                  |
|     27749 | East Cobb   | PROVIDENCE SQ SHPG CTR | 33.9796 | -84.434  | NCUA gives a shopping-center name, not an address; LGE's branch page gives 4101 Roswell Rd Ste 309, which the Census Geocoder doesn't match; interpolated between its matches for 4091 and 4111 Roswell Rd |
|     27759 | Towne Lake  | 936 Towne Lake Pkwy    | 34.1027 | -84.5354 | Neither the Census Geocoder nor OpenStreetMap matches 936 Towne Lake Pkwy; placed at OpenStreetMap's 950 Towne Lake Pkwy (Walgreens), the nearest numbered address on the same side of the street          |

Every geocoder-matched branch falls in the county NCUA lists. Hand-placed points outside NCUA's county (they sit on a county-line road; distances are unaffected): none. The farthest any branch's tract internal point is from its nearest branch is 7.18 mi. Branches flagged `ncua_no_member_services` but kept: none.

### 2. Branch changes between snapshots
Opened: none. Closed: none.

### 3-5. Tract coverage, penetration and distance
No tract is dropped; gaps are flags or blanks.

| check                                                    |   count |
|:---------------------------------------------------------|--------:|
| tracts                                                   |    2796 |
| missing households (no ACS row)                          |       0 |
| zero households                                          |      15 |
| high MOE households (CV > 30%)                           |       7 |
| zero land area (density blank)                           |       5 |
| missing or zero owner-occupied units (penetration blank) |      41 |
| missing distance                                         |       0 |

FOM tracts by distance band (2025-12 branches); farthest FOM tract: 46.5 mi.

| band   |   footprint_tracts |
|:-------|-------------------:|
| 0-2    |                101 |
| 2-5    |                267 |
| 5-10   |                156 |
| 10+    |                265 |

LGE share by band, FOM tracts (pooled: sum of LGE loans / sum of market loans):

| band   |   tracts |   households |   market_all |   lender_all |   share_all |   share_purchase |
|:-------|---------:|-------------:|-------------:|-------------:|------------:|-----------------:|
| 0-2    |      101 |       168305 |         4376 |           53 |      0.0121 |           0.0082 |
| 2-5    |      267 |       409760 |        11069 |          146 |      0.0132 |           0.009  |
| 5-10   |      156 |       241841 |         5626 |           57 |      0.0101 |           0.0072 |
| 10+    |      265 |       387139 |         6563 |           28 |      0.0043 |           0.0044 |

County-adjusted (`vs_county_average` = LGE loans / loans expected at the county's own share). This removes differences between counties, so it isolates proximity:

| band   |   tracts |   market_all |   lender_all |   expected_lender |   vs_county_average |
|:-------|---------:|-------------:|-------------:|------------------:|--------------------:|
| 0-2    |      101 |         4376 |           53 |             55.22 |                0.96 |
| 2-5    |      267 |        11069 |          146 |            143.69 |                1.02 |
| 5-10   |      156 |         5626 |           57 |             59.03 |                0.97 |
| 10+    |      265 |         6563 |           28 |             26.06 |                1.07 |

### 6. Population estimates (Vintage 2025)
County totals sum to the state row in every year used. Georgia grew **5.31%** from July 2020 to July 2025; counties above that are `growing`, and counties above 1.5x that (7.97%) are `fast_growing` (the bar for named clusters).

|   year |   state_row |   county_sum | match   |
|-------:|------------:|-------------:|:--------|
|   2020 |    10732595 |     10732595 | True    |
|   2023 |    11063669 |     11063669 | True    |
|   2025 |    11302748 |     11302748 | True    |

### 7. County adjacency
860 Georgia county pairs (both directions); 84 out-of-state neighbor pairs dropped. Asymmetric pairs: **0**. Counties with no Georgia neighbor: none.

### 8. Expansion scorecard
144 non-FOM counties, no blanks in households, household_density, pop_2025, pop_growth, branch_miles_hh_weighted; expansion gain total matches Phase 3 (468 loans). Growth clusters (2+ neighboring fast-growing non-FOM counties): **4**.

| growth_cluster   |   counties | county_names                                                                                                                                                               | touches_footprint   |   pop_growth |   expansion_gain |
|:-----------------|-----------:|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------|-------------:|-----------------:|
| C1               |         21 | Banks, Barrow, Dawson, Forsyth, Franklin, Greene, Habersham, Hall, Hart, Henry, Jackson, Jasper, Lamar, Madison, Monroe, Morgan, Newton, Oglethorpe, Pickens, Pike, Walton | True                |        0.133 |           126.05 |
| C2               |          3 | Carroll, Coweta, Haralson                                                                                                                                                  | True                |        0.095 |            21.8  |
| C3               |          3 | Bryan, Bulloch, Effingham                                                                                                                                                  | False               |        0.122 |            12.3  |
| C4               |          2 | Long, McIntosh                                                                                                                                                             | False               |        0.232 |             1.67 |
<!-- phase4:end -->

<!-- phase5_benchmarks:start -->
## Phase 5: benchmark ladder and market structure

### 1. Benchmark ladder (2025)
Rules in `config/settings.py`. 14 of 15 footprint counties have 100+ market originations (excluded: Chattooga). With at least 8 qualifying counties the ladder uses counties; otherwise it uses footprint tracts with 20+ market originations. **Unit used: county**; 14 qualifying counties, the top quarter is the top 4 by share. Top-quarter counties resting on a single LGE loan: **0** of 4. The base rung reproduces Phase 3's depth opportunity exactly, and the county breakdown sums to each rung's total.

| rung    | unit   | rule                              |   share_pct | reference                       |   depth |   depth_outside_top_quarter |   depth_vs_current_loans |
|:--------|:-------|:----------------------------------|------------:|:--------------------------------|--------:|----------------------------:|-------------------------:|
| base    | county | footprint average                 |        1.03 | all footprint counties          |  191.29 |                      174.88 |                     0.67 |
| stretch | county | weakest county in the top quarter |        1.57 | Bartow                          |  297.2  |                      270.58 |                     1.05 |
| ceiling | county | top quarter, pooled               |        2.22 | Floyd, Paulding, Gordon, Bartow |  435.66 |                      395.77 |                     1.53 |

The ladder both ways, by county and by tract (`phase5_checks/ladder_both_ways.csv`), so the tract rule runs on every lender's data. Tract shares are noisier: a top-quarter tract can rest on one loan.

| unit   | used   | rung    |   share_pct |   depth |   qualifying |   top_quarter |   top_quarter_on_one_loan |
|:-------|:-------|:--------|------------:|--------:|-------------:|--------------:|--------------------------:|
| county | True   | base    |        1.03 |   191.3 |           14 |             4 |                         0 |
| county | True   | stretch |        1.57 |   297.2 |           14 |             4 |                         0 |
| county | True   | ceiling |        2.22 |   435.7 |           14 |             4 |                         0 |
| tract  | False  | base    |        1.03 |   191.3 |          567 |           142 |                        74 |
| tract  | False  | stretch |        1.56 |   296   |          567 |           142 |                        74 |
| tract  | False  | ceiling |        3.43 |   720.9 |          567 |           142 |                        74 |

### 2. Channel field (`submission_of_application`)
Shares of broker-submitted loans use codes 1 and 2 only; exempt and other codes are left out.

|   code |   originations | meaning                              |
|-------:|---------------:|:-------------------------------------|
|      1 |          19957 | submitted directly to the lender     |
|      2 |           7077 | not submitted directly (e.g. broker) |
|   1111 |            611 | exempt                               |

Subject lender's codes: {'1111': 284}. LGE reports this field as exempt (HMDA's partial exemption for smaller filers), so its own broker-submitted share is unknown, not zero.

### 3. Like-for-like comparison
Smallest cell: **168** market originations. Originations without a tract have no tract-competition band and are left out of that dimension (11 loans).
<!-- phase5_benchmarks:end -->

<!-- phase5_outputs:start -->
## Phase 5: map, table and findings

### 1. Maps
Footprint maps draw **789** footprint tracts (share map) and **789** (opportunity map); 222 low-volume tracts are left unshaded, matching the `low_volume` flag. Interactive map layers: share 2,796 tracts, opportunity 789, density 789, counties 159; file size 5.8 MB (geometry simplified to about 40 m inside the footprint and 120 m elsewhere).

### 2. Top 25 table
25 rows; rows with a blank density, branch distance or top competitor: **0**.

### 3. Key numbers tie to their sources
| tie                                          |       ours |     source | match   |
|:---------------------------------------------|-----------:|-----------:|:--------|
| footprint market loans = Phase 2 market size | 27645      | 27645      | True    |
| footprint lender loans = Phase 2 market size |   284      |   284      | True    |
| base rung = footprint share                  |     0.0103 |     0.0103 | True    |
| base depth = sum of opportunity scores       |   191.288  |   191.288  | True    |
| ceiling depth = sum over counties            |   435.662  |   435.662  | True    |
| expansion total = scorecard sum              |   468.37   |   468.37   | True    |
| depth table base = Phase 3 depth             |   191.5    |   191.288  | True    |

### 4. FINDINGS.md
Not written yet.

### 5. Definition of done (v1)
| requirement   | what                                       | files                                                                                                               | present   |
|:--------------|:-------------------------------------------|:--------------------------------------------------------------------------------------------------------------------|:----------|
| R1            | tract map of share (footprint + statewide) | outputs/lge/map_footprint_share.png, outputs/lge/map_statewide.png, outputs/lge/mortgage_map.html                   | True      |
| R2            | top 25 tracts with top 3 competitors       | outputs/lge/opportunity_top25.csv, outputs/lge/map_footprint_opportunity.png                                        | True      |
| R3            | inside vs. outside footprint               | data/processed/lge/trend_summary.csv                                                                                | True      |
| R3a           | depth vs. expansion scorecard              | outputs/lge/depth_by_county.csv, outputs/lge/expansion_scorecard.csv, outputs/lge/chart_depth_vs_expansion.png      | True      |
| R3b           | expansion rankings and clusters            | outputs/lge/growth_clusters.csv, data/processed/lge/expansion_groups.csv, outputs/lge/map_statewide.png             | True      |
| R4            | share by distance band                     | data/processed/lge/share_by_distance.csv, outputs/lge/chart_share_by_distance.png                                   | True      |
| R5            | share trend 2022 onward                    | data/processed/lge/trend_summary.csv, data/processed/lge/county_year_metrics.csv, outputs/lge/chart_share_trend.png | True      |
| R6            | household density on map and table         | outputs/lge/mortgage_map.html, outputs/lge/opportunity_top25.csv                                                    | True      |
| R7            | FINDINGS.md and DATA_QUALITY.md            | outputs/lge/FINDINGS.md, outputs/lge/DATA_QUALITY.md                                                                | False     |

Subject-lender totals vs. the HMDA API: **0** mismatches (tolerance: exact match). The full pipeline rebuilds with `python src/run_all.py --lender lge`.
<!-- phase5_outputs:end -->

<!-- baseline:start -->
## Regression check against the saved baseline

### Result
43 comparisons against `tests/baseline/lge/`: **43 match**, **0 differ**; 0 file(s) superseded on purpose. Text must match exactly and numbers to 1e-9.

_none_

Every compared file matches.
<!-- baseline:end -->
