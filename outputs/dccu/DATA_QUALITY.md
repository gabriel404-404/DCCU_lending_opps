# Data quality log: Delta Community Credit Union

Checks for this lender. Market-wide checks (Phases 1-2: downloads, tracts, market definition) are in the repo's DATA_QUALITY.md.

<!-- phase1_lender:start -->
## Phase 1: lender presence and branches

### 2–3. DCCU presence and reconciliation
`filers_count` is DCCU's Georgia HMDA record count from the filers API (all action types). It should equal `records_in_ga` from the nationwide LEI download. Records outside GA are loans on out-of-state properties.

|   year | in_filers_list   | filers_name                  |   filers_count |   records_downloaded |   records_in_ga |   records_in_footprint |   ga_records_no_county |   originations |   originations_in_footprint | reconciles   |
|-------:|:-----------------|:-----------------------------|---------------:|---------------------:|----------------:|-----------------------:|-----------------------:|---------------:|----------------------------:|:-------------|
|   2022 | True             | DELTA COMMUNITY CREDIT UNION |           6971 |                 7697 |            6971 |                   6581 |                      0 |           4210 |                        3653 | True         |
|   2023 | True             | DELTA COMMUNITY CREDIT UNION |           5799 |                 6399 |            5799 |                   5484 |                      0 |           3473 |                        3006 | True         |
|   2024 | True             | DELTA COMMUNITY CREDIT UNION |           5947 |                 6668 |            5947 |                   5579 |                      0 |           3626 |                        3053 | True         |
|   2025 | True             | DELTA COMMUNITY CREDIT UNION |           5508 |                 6201 |            5508 |                   5143 |                      0 |           3188 |                        2655 | True         |

### 8. DCCU branches (NCUA `call-report-data-2026-06.zip`)
Charter 66357 (`DELTA COMMUNITY` in NCUA). Branch records: 36. **No lat/long columns: branches need geocoding in Phase 4.**

### Known limitations
- The FOM list is today's 20 counties, applied to every year. A lender that added counties over time has its early-year footprint share understated for the newer counties.
<!-- phase1_lender:end -->

<!-- phase2_lender:start -->
## Phase 2: lender within the market definition

### Product filter: conventional (`loan_types` ['1'])
DCCU's market is every lender's conventional loans, so the filter applies to competitors too. Below: DCCU's own GA originations by loan type, after the other market filters (`phase2_checks/product_filter.csv`). A large share left out would mean the config misses part of DCCU's lending.

|   year |   conventional |   FHA |   VA |   USDA |   lender_originations |   kept |   kept_share |
|-------:|---------------:|------:|-----:|-------:|----------------------:|-------:|-------------:|
|   2022 |           1305 |     0 |    0 |      0 |                  1305 |   1305 |            1 |
|   2023 |            537 |     0 |    0 |      0 |                   537 |    537 |            1 |
|   2024 |            930 |     0 |    0 |      0 |                   930 |    930 |            1 |
|   2025 |           1154 |     0 |    0 |      0 |                  1154 |   1154 |            1 |

### DCCU through the market filters (2025; all years in `phase2_checks/filter_waterfall.csv`)
The same filters apply to every lender. `conventional` is DCCU's product filter; `_all` columns count the market as DCCU defines it, `_lender` columns DCCU's own rows. Each row is the count after every filter above it.

| step                             |   rows_all |   originations_all |   rows_lender |   originations_lender |   originations_removed |
|:---------------------------------|-----------:|-------------------:|--------------:|----------------------:|-----------------------:|
| start: all GA rows with a county |     511121 |             241969 |          5508 |                  2867 |                      0 |
| exclude_purchased                |     447297 |             241969 |          5508 |                  2867 |                      0 |
| conventional                     |     305450 |             166984 |          5508 |                  2867 |                      0 |
| first_lien                       |     204657 |             117839 |          2507 |                  1437 |                   1430 |
| units_1_to_4                     |     203451 |             116888 |          2507 |                  1437 |                      0 |
| site_built                       |     183778 |             112444 |          2507 |                  1437 |                      0 |
| principal_residence              |     146107 |              89940 |          2366 |                  1379 |                     58 |
| purchase_or_refi                 |     128938 |              82934 |          1991 |                  1219 |                    160 |
| closed_end                       |     124968 |              80858 |          1868 |                  1154 |                     65 |
| not_reverse                      |     124790 |              80758 |          1868 |                  1154 |                      0 |
| not_business                     |     124660 |              80682 |          1868 |                  1154 |                      0 |

### DCCU reconciliation with the HMDA API
DCCU's GA originations with one market filter at a time, our data vs. the API's own count (the API allows at most two filters, so the full definition can't be checked in one query). Occupancy can't be checked: the API ignores that filter.

Mismatches: **0** of 24.

| filter               | api_applied_filter   |   lender_api |   lender_ours | match   |
|:---------------------|:---------------------|-------------:|--------------:|:--------|
| none                 | True                 |         2867 |          2867 | True    |
| loan_types           | True                 |         2867 |          2867 | True    |
| lien_statuses        | True                 |         1437 |          1437 | True    |
| total_units          | True                 |         2867 |          2867 | True    |
| construction_methods | True                 |         2867 |          2867 | True    |
| loan_purposes        | True                 |         1667 |          1667 | True    |

### Market size and DCCU (conventional originations, after all filters)
|   year | scope     |   market_originations |   market_purchase |   market_refinance |   market_no_tract |   lenders |   lender_originations |   lender_purchase |   lender_refinance |   lender_no_tract |
|-------:|:----------|----------------------:|------------------:|-------------------:|------------------:|----------:|----------------------:|------------------:|-------------------:|------------------:|
|   2022 | statewide |                138169 |             85616 |              52553 |                61 |       875 |                  1305 |               512 |                793 |                 0 |
|   2022 | footprint |                 95442 |             59373 |              36069 |                54 |       736 |                  1199 |               442 |                757 |                 0 |
|   2023 | statewide |                 76604 |             63173 |              13431 |                32 |       828 |                   537 |               461 |                 76 |                 0 |
|   2023 | footprint |                 51884 |             43987 |               7897 |                23 |       667 |                   487 |               414 |                 73 |                 0 |
|   2024 | statewide |                 78334 |             61581 |              16753 |                20 |       781 |                   930 |               757 |                173 |                 0 |
|   2024 | footprint |                 53033 |             42938 |              10095 |                11 |       633 |                   851 |               686 |                165 |                 0 |
|   2025 | statewide |                 80682 |             58062 |              22620 |                46 |       807 |                  1154 |               873 |                281 |                 0 |
|   2025 | footprint |                 53783 |             39785 |              13998 |                19 |       654 |                  1052 |               797 |                255 |                 0 |
<!-- phase2_lender:end -->

<!-- phase3:start -->
## Phase 3: share, trend and opportunity metrics

### 1. Totals reconcile
County sums match the Phase 2 market-size table for every year, scope and measure; scoring-year tracts plus unplaced rows match the totals. Mismatches: **0** of 52 (the script stops on any mismatch). Details: `phase3_checks/1_totals_reconciliation.csv`.

### 2. Benchmark
`footprint_share` (2025) = 1,052 / 53,783 = **1.96%**. Expansion uses `expansion.target_share` = 2.0% from the lender config (planning assumption).

### 3-4. Originations outside tract metrics (2025)
They stay in county, FOM and statewide figures but have no tract to score. All 2,796 TIGER tracts are in `tract_metrics.csv`; 24 FOM tracts had no 2025 originations and are kept with zeros.

| scope     |   no_tract_market |   no_tract_lender |   not_in_tiger_market |   not_in_tiger_tracts |
|:----------|------------------:|------------------:|----------------------:|----------------------:|
| statewide |                46 |                 0 |                     0 |                     0 |
| footprint |                19 |                 0 |                     0 |                     0 |

### 5. Minimum volume (FOM tracts, 2025)
No tract is dropped. Tracts under 20 market originations get `low_volume = True` (greyed out on the map, left out of share statistics). The top 25 all have 83+ market originations, so the rule doesn't affect the ranking.

| threshold         |   tracts |   market_loans |   lender_loans |   opportunity |   pct_of_opportunity |   tracts_share_over_10pct |
|:------------------|---------:|---------------:|---------------:|--------------:|---------------------:|--------------------------:|
| zero originations |       24 |              0 |              0 |           0   |                  0   |                         0 |
| < 10              |      153 |            872 |             15 |          15.3 |                  2.9 |                        14 |
| < 15              |      252 |           2068 |             40 |          33.7 |                  6.3 |                        17 |
| < 20              |      386 |           4330 |             91 |          65   |                 12.2 |                        27 |
| < 30              |      651 |          10785 |            207 |         146.1 |                 27.4 |                        29 |

### 6. Stability of the top 25
**12 of 25** tracts are in the top 25 both on 2025 share and on 2024-2025 combined share (`stable_top25 = True`). Most top tracts have zero or one DCCU loan, so one loan more or less moves a tract many places. County totals are steadier: the largest move between the two county rankings is **2 place(s)** (`depth_by_county.csv`), so findings lead with counties and use tracts to say where within a county. Details: `phase3_checks/6_stability_top25.csv`.

### 7. Competitor ties
Ties on loan count are broken by the lender's FOM-wide 2025 volume. A tie decided the 3rd competitor in **3 of 25** top tracts (849 of 1,457 FOM tracts).

### 8. Lender merger review (open item 3)
35 non-DCCU lenders were in the FOM top 25 in at least one year; **15** are flagged (a year with no loans, or FOM purchase share moving by more than 1.5x year over year). Review by hand for mergers. Full list: `phase3_checks/8_lender_merger_review.csv`.

| name                                      |   loans_2022 |   loans_2023 |   loans_2024 |   loans_2025 | top25_years            | years_with_no_loans   | purchase_share_jumps                              |
|:------------------------------------------|-------------:|-------------:|-------------:|-------------:|:-----------------------|:----------------------|:--------------------------------------------------|
| JPMorgan Chase Bank, National Association |         1388 |          959 |         1505 |         1317 | 2022, 2023, 2024, 2025 |                       | 2023->2024 x1.5                                   |
| CROSSCOUNTRY MORTGAGE, INC.               |          509 |          546 |          697 |         1030 | 2023, 2024, 2025       |                       | 2022->2023 x1.7; 2024->2025 x1.5                  |
| ZILLOW HOME LOANS, LLC                    |          190 |          330 |          505 |          585 | 2024, 2025             |                       | 2022->2023 x4.6; 2023->2024 x1.6                  |
| PROVIDENT FUNDING ASSOCIATES, L.P.        |          388 |          579 |          623 |          486 | 2023, 2024, 2025       |                       | 2022->2023 x2.8                                   |
| NEWREZ LLC                                |          799 |          255 |          365 |          456 | 2025                   |                       | 2022->2023 x3.1; 2023->2024 x1.8                  |
| GUILD MORTGAGE COMPANY                    |          138 |           53 |          382 |          442 | 2025                   |                       | 2023->2024 x7.9                                   |
| Associated Credit Union                   |          222 |          201 |          391 |          430 | 2025                   |                       | 2022->2023 x2.8; 2023->2024 x2.1                  |
| GUARANTEED RATE, INC.                     |          641 |          685 |          620 |          420 | 2023, 2024             |                       | 2022->2023 x1.9; 2024->2025 x0.6                  |
| DHI MORTGAGE COMPANY, LTD.                |         1035 |          802 |          668 |          397 | 2022, 2023, 2024       |                       | 2024->2025 x0.6                                   |
| Broker Solutions, Inc.                    |         1412 |          425 |          585 |          386 | 2022, 2024             |                       | 2022->2023 x0.5                                   |
| First Option Mortgage, LLC                |          801 |          660 |          673 |          344 | 2023, 2024             |                       | 2024->2025 x0.5                                   |
| FREEDOM MORTGAGE CORPORATION              |          880 |          145 |          183 |          201 | 2022                   |                       | 2022->2023 x1.8; 2023->2024 x1.6; 2024->2025 x0.3 |
| AmeriSave Mortgage Corporation            |         1101 |          221 |          103 |          154 | 2022                   |                       | 2022->2023 x0.3; 2023->2024 x0.2                  |
| HOMESTAR FINANCIAL CORPORATION            |         2037 |          604 |            0 |            0 | 2022, 2023             | 2024, 2025            | 2022->2023 x0.4                                   |
| HOME POINT FINANCIAL CORPORATION          |         1058 |            0 |            0 |            0 | 2022                   | 2023, 2024, 2025      |                                                   |

### 9. Market groups and tiers
Hybrid rule (PRD Appendix A): CSA where one exists, else CBSA, except the CSA that holds the footprint's main metro area, which is split into its CBSAs. Main metro area: **Atlanta-Sandy Springs-Roswell, GA** (CBSA 12060), 18 of 20 FOM counties and 94.2% of FOM originations in 2025. Split CSA: Atlanta--Athens-Clarke County--Sandy Springs, GA-AL. Each county's group is in `counties.csv`.

| market_group                           | urban_rural_tier   |   counties |   footprint_counties | county_names                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|:---------------------------------------|:-------------------|-----------:|---------------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| (no metro/micro area)                  | rural              |         53 |                    0 | Appling, Bacon, Baker, Banks, Berrien, Bleckley, Calhoun, Candler, Charlton, Clay, Clinch, Cook, Dodge, Dooly, Early, Elbert, Emanuel, Fannin, Franklin, Gilmer, Glascock, Greene, Hancock, Hart, Irwin, Jeff Davis, Jefferson, Jenkins, Lamar, Macon, Miller, Mitchell, Pulaski, Putnam, Rabun, Randolph, Screven, Seminole, Taliaferro, Tattnall, Taylor, Telfair, Towns, Treutlen, Union, Warren, Washington, Webster, Wheeler, White, Wilcox, Wilkes, Wilkinson |
| Atlanta-Sandy Springs-Roswell, GA      | metro              |         29 |                   18 | Barrow, Bartow, Butts, Carroll, Cherokee, Clayton, Cobb, Coweta, Dawson, DeKalb, Douglas, Fayette, Forsyth, Fulton, Gwinnett, Haralson, Heard, Henry, Jasper, Lumpkin, Meriwether, Morgan, Newton, Paulding, Pickens, Pike, Rockdale, Spalding, Walton                                                                                                                                                                                                              |
| Macon-Bibb County--Warner Robins, GA   | metro              |          7 |                    0 | Bibb, Crawford, Houston, Jones, Monroe, Peach, Twiggs                                                                                                                                                                                                                                                                                                                                                                                                               |
| Columbus-Auburn-Opelika, GA-AL         | metro              |          6 |                    0 | Chattahoochee, Harris, Marion, Muscogee, Stewart, Talbot                                                                                                                                                                                                                                                                                                                                                                                                            |
| Savannah-Hinesville-Statesboro, GA     | metro              |          5 |                    0 | Bryan, Chatham, Effingham, Liberty, Long                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Augusta-Richmond County, GA-SC         | metro              |          5 |                    0 | Burke, Columbia, Lincoln, McDuffie, Richmond                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Chattanooga-Cleveland-Dalton, TN-GA-AL | metro              |          5 |                    0 | Catoosa, Dade, Murray, Walker, Whitfield                                                                                                                                                                                                                                                                                                                                                                                                                            |
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
| Calhoun, GA                            | micro              |          1 |                    0 | Gordon                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Jacksonville-Kingsland-Palatka, FL-GA  | micro              |          1 |                    0 | Camden                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Gainesville, GA                        | metro              |          1 |                    1 | Hall                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Fitzgerald, GA                         | micro              |          1 |                    0 | Ben Hill                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Eufaula, AL-GA                         | micro              |          1 |                    0 | Quitman                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Cordele, GA                            | micro              |          1 |                    0 | Crisp                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Cornelia, GA                           | micro              |          1 |                    0 | Habersham                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Cedartown, GA                          | micro              |          1 |                    0 | Polk                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Chattanooga-Cleveland-Dalton, TN-GA-AL | micro              |          1 |                    0 | Chattooga                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Moultrie, GA                           | micro              |          1 |                    0 | Colquitt                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Rome, GA                               | metro              |          1 |                    0 | Floyd                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| LaGrange, GA-AL                        | micro              |          1 |                    0 | Troup                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Milledgeville, GA                      | micro              |          1 |                    0 | Baldwin                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Jefferson, GA                          | micro              |          1 |                    1 | Jackson                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Thomaston, GA                          | micro              |          1 |                    0 | Upson                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Tallahassee-Bainbridge, FL-GA          | micro              |          1 |                    0 | Decatur                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Toccoa, GA                             | micro              |          1 |                    0 | Stephens                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

### 10. Expansion edge cases
Non-FOM counties where DCCU is already at or above 2% (expansion gain 0): Jasper (2.1%), Pike (4.5%), Lamar (5.8%), Meriwether (3.5%), Wilkinson (3.7%).

### 11. Lenders missing from the HMDA filers lists
LEIs with market originations that are missing from every cached HMDA `/view/filers` list, named from GLEIF instead (Phase 2 builds `lenders.csv`). Any LEI GLEIF can't name shows as `LEI ... (no name in filers list)`. All originations are kept.

|   year |   originations |   footprint_originations | name                                 | name_source   |
|-------:|---------------:|-------------------------:|:-------------------------------------|:--------------|
|   2025 |             62 |                       47 | PRC MORTGAGE, LLC                    | gleif         |
|   2025 |             55 |                        0 | Landmark 24 Mortgage, LLC            | gleif         |
|   2025 |             38 |                       36 | BRIDGEWAY LENDING PARTNERS LLC       | gleif         |
|   2025 |             34 |                       29 | Loyal Trust Bank                     | gleif         |
|   2025 |             32 |                       19 | ADVANTAGEFIRST LENDING INC.          | gleif         |
|   2025 |              9 |                        8 | VERUS RESIDENTIAL LOANCO, LLC        | gleif         |
|   2025 |              8 |                        8 | ARDRI LLC                            | gleif         |
|   2025 |              5 |                        3 | Climate First Bank                   | gleif         |
|   2025 |              4 |                        3 | OBSIDIAN FINANCIAL SERVICES, INC.    | gleif         |
|   2025 |              3 |                        3 | AMERICAS MORTGAGE PROFESSIONALS, LLC | gleif         |
|   2025 |              2 |                        2 | ASPIRE HOME LOANS, LLC               | gleif         |
|   2025 |              2 |                        2 | THE LOCAL LENDER, LLC                | gleif         |
|   2025 |              1 |                        0 | Local Bank                           | gleif         |
|   2025 |              1 |                        0 | New Story Lending LLC                | gleif         |
|   2025 |              1 |                        1 | MARLIN MORTGAGE CAPITAL, LLC         | gleif         |

### 12. Builder-owned lenders (contestable market)
`config/builder_lenders.csv`, **pending your review**. Rows with `include = 1` are left out of the contestable market (`opportunity_score_contestable`); `include = 0` rows are candidates that show the builder pattern (almost no refinance, purchases packed into a few tracts) but are not confirmed. Included lenders made 1,791 of 53,783 FOM originations in 2025. Contestable `footprint_share` = **2.02%**. Depth opportunity: 533 loans on the full market, 529 on the contestable market.

| lender_name                        | builder                          |   include | basis                                                                               |   footprint_loans |   footprint_purchase_share_pct |
|:-----------------------------------|:---------------------------------|----------:|:------------------------------------------------------------------------------------|------------------:|-------------------------------:|
| DHI MORTGAGE COMPANY, LTD.         | D.R. Horton                      |         1 | builder-owned lender (DHI = D.R. Horton)                                            |               397 |                           1    |
| PULTE MORTGAGE LLC                 | PulteGroup                       |         1 | builder name in lender name                                                         |               375 |                           0.94 |
| LENNAR MORTGAGE, LLC               | Lennar                           |         1 | builder name in lender name                                                         |               198 |                           0.5  |
| TOLL BROTHERS MORTGAGE COMPANY     | Toll Brothers                    |         1 | builder name in lender name                                                         |               308 |                           0.77 |
| Taylor Morrison Home Funding, Inc. | Taylor Morrison                  |         1 | builder name in lender name                                                         |               259 |                           0.65 |
| NVR Mortgage Finance, Inc.         | NVR (Ryan Homes)                 |         1 | builder name in lender name                                                         |                85 |                           0.21 |
| INSPIRE HOME LOANS INC.            | Century Communities (to confirm) |         1 | believed builder-owned; data signature: 0% refi and 54% of GA purchases in 3 tracts |               169 |                           0.42 |
| PRC MORTGAGE, LLC                  | unknown                          |         0 | data signature only: 2% refi and 80% of GA purchases in 3 tracts                    |                47 |                           0.12 |
| VICTORY MORTGAGE, L.L.C.           | unknown                          |         0 | data signature only: 1% refi and 60% of GA purchases in 3 tracts                    |                92 |                           0.23 |
| TRAILBLAZER MORTGAGE L.L.C.        | unknown                          |         0 | data signature only: 0% refi and 49% of GA purchases in 3 tracts                    |               134 |                           0.34 |
| Landmark 24 Mortgage, LLC          | unknown                          |         0 | data signature only: 0% refi and 45% of GA purchases in 3 tracts                    |                 0 |                           0    |
| First Heritage Mortgage, LLC       | unknown                          |         0 | data signature only: 4% refi and 42% of GA purchases in 3 tracts                    |               135 |                           0.33 |
| JET HOMELOANS, LP                  | unknown                          |         0 | data signature only: 0% refi and 27% of GA purchases in 3 tracts                    |                27 |                           0.07 |
<!-- phase3:end -->

<!-- phase4:start -->
## Phase 4: households, density, branch distance and growth

### 1. Branches and geocoding
NCUA snapshots: scoring year `2025-12` (share by distance) and current `2026-06` (expansion scorecard). In-scope Georgia branches: **28** and **28**. Excluded sites (`config/lenders/dccu/branch_exclusions.csv`, plus out-of-state):

|   site_id | site_name                                     | state   | exclusion_reason                         |
|----------:|:----------------------------------------------|:--------|:-----------------------------------------|
|     21597 | Atlanta (Hartsfield-Jackson Int'l Airport)    | GA      | behind airport security (Concourse A)    |
|     22977 | Florence, Ky (Cincinnati Metro)               | KY      | out of state                             |
|     22992 | Southlake, TX (Dallas Metro)                  | TX      | out of state                             |
|     23001 | Atlanta (Technical Operations Center)         | GA      | behind Delta security                    |
|     23010 | Atlanta (World Headquaters)                   | GA      | behind Delta security                    |
|     27079 | Salt Lake City (Salt Lake City Int'l Airport) | UT      | out of state                             |
|     52473 | Office Location- Riverwood 100                | GA      | corporate office without member services |
|     52474 | Office Location - Riverwood 200               | GA      | corporate office without member services |

The Census Geocoder matched every in-scope branch except those below, whose coordinates are hand-placed in `config/lenders/dccu/branch_coordinates.csv`, with the method for each (error a few hundred meters at most).

|   site_id | site_name                    | address                |     lat |      lon | method                                                                                                                        |
|----------:|:-----------------------------|:-----------------------|--------:|---------:|:------------------------------------------------------------------------------------------------------------------------------|
|     22909 | Peachtree City (Wisdom Road) | 315 Highway 74 N       | 33.4135 | -84.6029 | Census Geocoder has no match for 315 Highway 74 N; interpolated between its matches for 300 and 320 Highway 74 N              |
|     52464 | Johns Creek                  | 6700 McGinnis Ferry Rd | 34.0775 | -84.1827 | Census Geocoder has no match for 6700 McGinnis Ferry Rd; interpolated between its matches for 6550 and 6900 McGinnis Ferry Rd |

Every geocoder-matched branch falls in the county NCUA lists. Hand-placed points outside NCUA's county (they sit on a county-line road; distances are unaffected): Johns Creek (NCUA Fulton, point in Forsyth). The farthest any branch's tract internal point is from its nearest branch is 1.73 mi. Branches flagged `ncua_no_member_services` but kept: Conyers.

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

FOM tracts by distance band (2025-12 branches); farthest FOM tract: 28.8 mi.

| band   |   footprint_tracts |
|:-------|-------------------:|
| 0-2    |                191 |
| 2-5    |                665 |
| 5-10   |                497 |
| 10+    |                104 |

DCCU share by band, FOM tracts (pooled: sum of DCCU loans / sum of market loans):

| band   |   tracts |   households |   market_all |   lender_all |   share_all |   share_purchase |
|:-------|---------:|-------------:|-------------:|-------------:|------------:|-----------------:|
| 0-2    |      191 |       313272 |         6970 |          193 |      0.0277 |           0.0279 |
| 2-5    |      665 |       990392 |        23434 |          481 |      0.0205 |           0.0209 |
| 5-10   |      497 |       763665 |        17461 |          308 |      0.0176 |           0.0182 |
| 10+    |      104 |       180829 |         5899 |           70 |      0.0119 |           0.0122 |

County-adjusted (`vs_county_average` = DCCU loans / loans expected at the county's own share). This removes differences between counties, so it isolates proximity:

| band   |   tracts |   market_all |   lender_all |   expected_lender |   vs_county_average |
|:-------|---------:|-------------:|-------------:|------------------:|--------------------:|
| 0-2    |      191 |         6970 |          193 |            169.16 |                1.14 |
| 2-5    |      665 |        23434 |          481 |            473.5  |                1.02 |
| 5-10   |      497 |        17461 |          308 |            335.06 |                0.92 |
| 10+    |      104 |         5899 |           70 |             74.28 |                0.94 |

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
139 non-FOM counties, no blanks in households, household_density, pop_2025, pop_growth, branch_miles_hh_weighted; expansion gain total matches Phase 3 (448 loans). Growth clusters (2+ neighboring fast-growing non-FOM counties): **5**.

| growth_cluster   |   counties | county_names                                                                                       | touches_footprint   |   pop_growth |   expansion_gain |
|:-----------------|-----------:|:---------------------------------------------------------------------------------------------------|:--------------------|-------------:|-----------------:|
| C1               |         12 | Banks, Franklin, Greene, Habersham, Hart, Jasper, Lamar, Madison, Monroe, Morgan, Oglethorpe, Pike | True                |        0.116 |            30.78 |
| C3               |          3 | Bartow, Dawson, Pickens                                                                            | True                |        0.139 |            28.86 |
| C2               |          3 | Bryan, Bulloch, Effingham                                                                          | False               |        0.122 |            25.6  |
| C4               |          2 | Carroll, Haralson                                                                                  | True                |        0.098 |            13.12 |
| C5               |          2 | Long, McIntosh                                                                                     | False               |        0.232 |             3.34 |
<!-- phase4:end -->

<!-- phase5_benchmarks:start -->
## Phase 5: benchmark ladder and market structure

### 1. Benchmark ladder (2025)
Rules in `config/settings.py`. 20 of 20 footprint counties have 100+ market originations (excluded: none). With at least 8 qualifying counties the ladder uses counties; otherwise it uses footprint tracts with 20+ market originations. **Unit used: county**; 20 qualifying counties, the top quarter is the top 5 by share. Top-quarter counties resting on a single DCCU loan: **0** of 5. The base rung reproduces Phase 3's depth opportunity exactly, and the county breakdown sums to each rung's total.

| rung    | unit   | rule                              |   share_pct | reference                               |   depth |   depth_outside_top_quarter |   depth_vs_current_loans |
|:--------|:-------|:----------------------------------|------------:|:----------------------------------------|--------:|----------------------------:|-------------------------:|
| base    | county | footprint average                 |        1.96 | all footprint counties                  |  532.92 |                      519.02 |                     0.51 |
| stretch | county | weakest county in the top quarter |        4.04 | Spalding                                | 1374.31 |                     1335.69 |                     1.31 |
| ceiling | county | top quarter, pooled               |        6.17 | Fayette, Coweta, Butts, Henry, Spalding | 2381.88 |                     2301.81 |                     2.26 |

The ladder both ways, by county and by tract (`phase5_checks/ladder_both_ways.csv`), so the tract rule runs on every lender's data. Tract shares are noisier: a top-quarter tract can rest on one loan.

| unit   | used   | rung    |   share_pct |   depth |   qualifying |   top_quarter |   top_quarter_on_one_loan |
|:-------|:-------|:--------|------------:|--------:|-------------:|--------------:|--------------------------:|
| county | True   | base    |        1.96 |   532.9 |           20 |             5 |                         0 |
| county | True   | stretch |        4.04 |  1374.3 |           20 |             5 |                         0 |
| county | True   | ceiling |        6.17 |  2381.9 |           20 |             5 |                         0 |
| tract  | False  | base    |        1.96 |   532.9 |         1047 |           262 |                        85 |
| tract  | False  | stretch |        3.33 |  1066   |         1047 |           262 |                        85 |
| tract  | False  | ceiling |        5.79 |  2193.2 |         1047 |           262 |                        85 |

### 2. Channel field (`submission_of_application`)
Shares of broker-submitted loans use codes 1 and 2 only; exempt and other codes are left out.

|   code |   originations | meaning                              |
|-------:|---------------:|:-------------------------------------|
|      1 |          37967 | submitted directly to the lender     |
|      2 |          15041 | not submitted directly (e.g. broker) |
|   1111 |            775 | exempt                               |

Subject lender's codes: {'1': 1052}.

### 3. Like-for-like comparison
Smallest cell: **543** market originations. Originations without a tract have no tract-competition band and are left out of that dimension (19 loans).
<!-- phase5_benchmarks:end -->

<!-- phase5_outputs:start -->
## Phase 5: map, table and findings

### 1. Maps
Footprint maps draw **1,457** footprint tracts (share map) and **1,457** (opportunity map); 410 low-volume tracts are left unshaded, matching the `low_volume` flag. Interactive map layers: share 2,796 tracts, opportunity 1,457, density 1,457, counties 159; file size 7.2 MB (geometry simplified to about 40 m inside the footprint and 120 m elsewhere).

### 2. Top 25 table
25 rows; rows with a blank density, branch distance or top competitor: **0**.

### 3. Key numbers tie to their sources
| tie                                          |       ours |     source | match   |
|:---------------------------------------------|-----------:|-----------:|:--------|
| footprint market loans = Phase 2 market size | 53783      | 53783      | True    |
| footprint lender loans = Phase 2 market size |  1052      |  1052      | True    |
| base rung = footprint share                  |     0.0196 |     0.0196 | True    |
| base depth = sum of opportunity scores       |   532.918  |   532.918  | True    |
| ceiling depth = sum over counties            |  2381.88   |  2381.88   | True    |
| expansion total = scorecard sum              |   448.04   |   448.04   | True    |
| depth table base = Phase 3 depth             |   533      |   532.918  | True    |

### 4. FINDINGS.md
533 words (limit about 550, one page). Numbers not found in `outputs/dccu/key_numbers.csv`: **none**.

### 5. Definition of done (v1)
| requirement   | what                                       | files                                                                                                                  | present   |
|:--------------|:-------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------|:----------|
| R1            | tract map of share (footprint + statewide) | outputs/dccu/map_footprint_share.png, outputs/dccu/map_statewide.png, outputs/dccu/mortgage_map.html                   | True      |
| R2            | top 25 tracts with top 3 competitors       | outputs/dccu/opportunity_top25.csv, outputs/dccu/map_footprint_opportunity.png                                         | True      |
| R3            | inside vs. outside footprint               | data/processed/dccu/trend_summary.csv                                                                                  | True      |
| R3a           | depth vs. expansion scorecard              | outputs/dccu/depth_by_county.csv, outputs/dccu/expansion_scorecard.csv, outputs/dccu/chart_depth_vs_expansion.png      | True      |
| R3b           | expansion rankings and clusters            | outputs/dccu/growth_clusters.csv, data/processed/dccu/expansion_groups.csv, outputs/dccu/map_statewide.png             | True      |
| R4            | share by distance band                     | data/processed/dccu/share_by_distance.csv, outputs/dccu/chart_share_by_distance.png                                    | True      |
| R5            | share trend 2022 onward                    | data/processed/dccu/trend_summary.csv, data/processed/dccu/county_year_metrics.csv, outputs/dccu/chart_share_trend.png | True      |
| R6            | household density on map and table         | outputs/dccu/mortgage_map.html, outputs/dccu/opportunity_top25.csv                                                     | True      |
| R7            | FINDINGS.md and DATA_QUALITY.md            | outputs/dccu/FINDINGS.md, outputs/dccu/DATA_QUALITY.md                                                                 | True      |

Subject-lender totals vs. the HMDA API: **0** mismatches (tolerance: exact match). The full pipeline rebuilds with `python src/run_all.py --lender dccu`.
<!-- phase5_outputs:end -->

<!-- baseline:start -->
## Regression check against the saved baseline

### Result
47 comparisons against `tests/baseline/dccu/`: **47 match**, **0 differ**; 1 file(s) superseded on purpose. Text must match exactly and numbers to 1e-9. The v1 files use pre-productize names and paths, which the check translates. Decided changes (`src/check_baseline.py`): superseded files, and columns added later (`data/processed/benchmark_ladder.csv`: ['unit'], `data/processed/depth_ladder_by_county.csv`: ['top_quarter_tracts'], `outputs/depth_by_county.csv`: ['top_quarter_tracts']), which are allowed while every v1 column still matches.

| baseline                                              | now   |   rows | result                                                                                                             |
|:------------------------------------------------------|:------|-------:|:-------------------------------------------------------------------------------------------------------------------|
| v1/data/processed/phase2_checks/exempt_flags_kept.csv |       |      0 | superseded: P2: the market files keep all loan types, so this market-wide count now includes FHA, VA and USDA rows |

Every compared file matches.
<!-- baseline:end -->
