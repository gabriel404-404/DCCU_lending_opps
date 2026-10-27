# Data quality log

<!-- phase1:start -->
## Phase 1: download and validate

### 1. Completeness: rows downloaded vs. HMDA API counts
|   year |   rows_downloaded |   rows_api |   diff |   ga_total_api |   no_county_rows |   no_county_pct |
|-------:|------------------:|-----------:|-------:|---------------:|-----------------:|----------------:|
|   2022 |            594693 |     594693 |      0 |         603410 |             8717 |            1.44 |
|   2023 |            447600 |     447600 |      0 |         450495 |             2895 |            0.64 |
|   2024 |            475339 |     475339 |      0 |         478257 |             2918 |            0.61 |
|   2025 |            511121 |     511121 |      0 |         515746 |             4625 |            0.9  |

Year × county × action cells that don't match: **0** (details in `data/processed/phase1_checks/1_row_counts.csv`).

`no_county_rows` are Georgia records with no county code. Downloads are by county, so these rows are not in the raw data. They can't be placed in a tract either, so tract and county metrics are unaffected; statewide totals are understated by `no_county_pct`. DCCU's own no-county records are in the table below.

### 2–3. DCCU presence and reconciliation
`filers_count` is DCCU's Georgia HMDA record count from the filers API (all action types). It should equal `records_in_ga` from the nationwide LEI download. Records outside GA are loans on out-of-state properties.

|   year | in_filers_list   | filers_name                  |   filers_count |   records_downloaded |   records_in_ga |   records_in_fom |   ga_records_no_county |   originations |   originations_in_fom | reconciles   |
|-------:|:-----------------|:-----------------------------|---------------:|---------------------:|----------------:|-----------------:|-----------------------:|---------------:|----------------------:|:-------------|
|   2022 | True             | DELTA COMMUNITY CREDIT UNION |           6971 |                 7697 |            6971 |             6581 |                      0 |           4210 |                  3653 | True         |
|   2023 | True             | DELTA COMMUNITY CREDIT UNION |           5799 |                 6399 |            5799 |             5484 |                      0 |           3473 |                  3006 | True         |
|   2024 | True             | DELTA COMMUNITY CREDIT UNION |           5947 |                 6668 |            5947 |             5579 |                      0 |           3626 |                  3053 | True         |
|   2025 | True             | DELTA COMMUNITY CREDIT UNION |           5508 |                 6201 |            5508 |             5143 |                      0 |           3188 |                  2655 | True         |

### 4. Census tracts
Rows with missing/NA tract, by year (all lenders):

|   year |   rows |
|-------:|-------:|
|   2022 |   3048 |
|   2023 |   2710 |
|   2024 |   2618 |
|   2025 |   2552 |

Tract sets: HMDA 2,776, TIGER 2,796, ACS 2,796. Mismatches:

| in    | missing_from   |   tracts |
|:------|:---------------|---------:|
| acs   | hmda           |       20 |
| tiger | hmda           |       20 |

Tracts present in TIGER/ACS with no HMDA records are usually water, airport, park or institutional tracts (codes 98xxxx/99xxxx, near-zero households); list in `4_tract_coverage.csv`. Rows with no tract can't be mapped and are excluded from tract metrics (Phase 2 logs the count).

### 5. `Exempt` fields (partially exempt lenders)
405 lenders report `Exempt` in some fields. Top 10 by number of exempt values (rows × fields), all years; detail by field in `5_exempt_fields.csv`. Exempt fields are mostly pricing and underwriting details; v1 share metrics use only fields that can't be exempted.

| lei                  |   exempt_values | lender                      |
|:---------------------|----------------:|:----------------------------|
| 2549006MTEQ1VE0AAQ20 |           48230 | PINNACLE BANK               |
| 549300BTTIQWNC2CFA21 |           34916 | LGE COMMUNITY CREDIT UNION  |
| 25490033STXCA9YDXT42 |           21756 | Glennville Bank             |
| 549300ELFWNRX6MLE444 |           18690 | Farmers & Merchants Bank    |
| 254900VA7WQ1PZGYI558 |           18256 | Morris Bank                 |
| 549300FKW6LAHX0L9161 |           17808 | Georgia Community Bank      |
| 254900OPB6J0NM26JY33 |           16114 | Oconee State Bank           |
| 549300EA0U825E61X330 |           14210 | BankSouth                   |
| 54930095LY1EDFTWAG29 |           13902 | Builtwell Bank              |
| 549300ANE43ZL0O8VZ13 |           13132 | First State Bank of Blakely |

### 6. Lender name changes across years
223 LEIs reported more than one name; 117 differ in wording (renames, rebrands), the rest only in case or punctuation (`6_lender_name_changes.csv`). The analysis keys on LEI and displays the latest name, so renames don't split a lender. Mergers that retire an LEI are not detected here; review the top competitors by hand in Phase 3.

### 7. ACS household reliability
ACS 2020–2024 5-year, table B11001. CV = (MOE / 1.645) / estimate; flag when CV > 30%.

| flag            |   tracts |
|:----------------|---------:|
| ok              |     2774 |
| zero_households |       15 |
| high_moe        |        7 |

### 8. DCCU branches (NCUA `call-report-data-2026-06.zip`)
Charter: 66357. Branch records: 36. **No lat/long columns: branches need geocoding in Phase 4.**

### Known limitations
- The FOM list is DCCU's current 20 counties, applied to every year. DCCU added counties over time, so early-year FOM share may be understated for recently added counties.
<!-- phase1:end -->

<!-- phase2:start -->
## Phase 2: market definition

### Filter waterfall (2025; all years in `phase2_checks/filter_waterfall.csv`)
Filters run in order, so each row's count is after every filter above it. Rows with no county code (Phase 1, check 1) never enter, so the start is slightly below the statewide total.

| step                             |   rows_all |   originations_all |   rows_dccu |   originations_dccu |   originations_removed |
|:---------------------------------|-----------:|-------------------:|------------:|--------------------:|-----------------------:|
| start: all GA rows with a county |     511121 |             241969 |        5508 |                2867 |                      0 |
| exclude_purchased                |     447297 |             241969 |        5508 |                2867 |                      0 |
| conventional                     |     305450 |             166984 |        5508 |                2867 |                  74985 |
| first_lien                       |     204657 |             117839 |        2507 |                1437 |                  49145 |
| units_1_to_4                     |     203451 |             116888 |        2507 |                1437 |                    951 |
| site_built                       |     183778 |             112444 |        2507 |                1437 |                   4444 |
| principal_residence              |     146107 |              89940 |        2366 |                1379 |                  22504 |
| purchase_or_refi                 |     128938 |              82934 |        1991 |                1219 |                   7006 |
| closed_end                       |     124968 |              80858 |        1868 |                1154 |                   2076 |
| not_reverse                      |     124790 |              80758 |        1868 |                1154 |                    100 |
| not_business                     |     124660 |              80682 |        1868 |                1154 |                     76 |

### Exempt flags kept
Rows kept although the lender reported the field as exempt (`1111`), all years. Exempt lenders are small and rarely make these products.

| filter       | field                          |   rows_kept_with_exempt |
|:-------------|:-------------------------------|------------------------:|
| closed_end   | open-end_line_of_credit        |                   12023 |
| not_business | business_or_commercial_purpose |                   12008 |
| not_reverse  | reverse_mortgage               |                   12024 |

### DCCU reconciliation with the HMDA API
DCCU's GA originations with one market filter at a time, our data vs. the API's own count (the API allows at most two filters, so the full definition can't be checked in one query). Occupancy can't be checked: the API ignores that filter.

Mismatches: **0** of 24.

| filter               | api_applied_filter   |   dccu_api |   dccu_ours | match   |
|:---------------------|:---------------------|-----------:|------------:|:--------|
| none                 | True                 |       2867 |        2867 | True    |
| loan_types           | True                 |       2867 |        2867 | True    |
| lien_statuses        | True                 |       1437 |        1437 | True    |
| total_units          | True                 |       2867 |        2867 | True    |
| construction_methods | True                 |       2867 |        2867 | True    |
| loan_purposes        | True                 |       1667 |        1667 | True    |

### Market size (originations, after all filters)
|   year | scope     |   market_originations |   market_purchase |   market_refinance |   market_no_tract |   lenders |   dccu_originations |   dccu_purchase |   dccu_refinance |   dccu_no_tract |
|-------:|:----------|----------------------:|------------------:|-------------------:|------------------:|----------:|--------------------:|----------------:|-----------------:|----------------:|
|   2022 | statewide |                138169 |             85616 |              52553 |                61 |       875 |                1305 |             512 |              793 |               0 |
|   2022 | fom       |                 95442 |             59373 |              36069 |                54 |       736 |                1199 |             442 |              757 |               0 |
|   2023 | statewide |                 76604 |             63173 |              13431 |                32 |       828 |                 537 |             461 |               76 |               0 |
|   2023 | fom       |                 51884 |             43987 |               7897 |                23 |       667 |                 487 |             414 |               73 |               0 |
|   2024 | statewide |                 78334 |             61581 |              16753 |                20 |       781 |                 930 |             757 |              173 |               0 |
|   2024 | fom       |                 53033 |             42938 |              10095 |                11 |       633 |                 851 |             686 |              165 |               0 |
|   2025 | statewide |                 80682 |             58062 |              22620 |                46 |       807 |                1154 |             873 |              281 |               0 |
|   2025 | fom       |                 53783 |             39785 |              13998 |                19 |       654 |                1052 |             797 |              255 |               0 |

### Rows without a census tract
`market_no_tract` originations stay in the market data (`has_tract = 0`) and count toward county and statewide totals, but can't be placed on the map or in tract metrics.

### Lenders
`data/processed/lenders.csv`: 1,863 LEIs with their latest reported name. Names come from the HMDA filers lists; market LEIs missing from every list are named from GLEIF (the global LEI registry).

| name_source   |   leis |
|:--------------|-------:|
| hmda_filers   |   1845 |
| gleif         |     18 |
<!-- phase2:end -->

<!-- phase3:start -->
## Phase 3: share, trend and opportunity metrics

### 1. Totals reconcile
County sums match the Phase 2 market-size table for every year, scope and measure; scoring-year tracts plus unplaced rows match the totals. Mismatches: **0** of 52 (the script stops on any mismatch). Details: `phase3_checks/1_totals_reconciliation.csv`.

### 2. Benchmark
`fom_share` (2025) = 1,052 / 53,783 = **1.96%**. Expansion uses `EXPANSION_TARGET_SHARE` = 2.0% (planning assumption).

### 3-4. Originations outside tract metrics (2025)
They stay in county, FOM and statewide figures but have no tract to score. All 2,796 TIGER tracts are in `tract_metrics.csv`; 24 FOM tracts had no 2025 originations and are kept with zeros.

| scope     |   no_tract_market |   no_tract_dccu |   not_in_tiger_market |   not_in_tiger_tracts |
|:----------|------------------:|----------------:|----------------------:|----------------------:|
| statewide |                46 |               0 |                     0 |                     0 |
| fom       |                19 |               0 |                     0 |                     0 |

### 5. Minimum volume (FOM tracts, 2025)
No tract is dropped. Tracts under 20 market originations get `low_volume = True` (greyed out on the map, left out of share statistics). The top 25 all have 83+ market originations, so the rule doesn't affect the ranking.

| threshold         |   tracts |   market_loans |   dccu_loans |   opportunity |   pct_of_opportunity |   tracts_share_over_10pct |
|:------------------|---------:|---------------:|-------------:|--------------:|---------------------:|--------------------------:|
| zero originations |       24 |              0 |            0 |           0   |                  0   |                         0 |
| < 10              |      153 |            872 |           15 |          15.3 |                  2.9 |                        14 |
| < 15              |      252 |           2068 |           40 |          33.7 |                  6.3 |                        17 |
| < 20              |      386 |           4330 |           91 |          65   |                 12.2 |                        27 |
| < 30              |      651 |          10785 |          207 |         146.1 |                 27.4 |                        29 |

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
Hybrid rule (PRD Appendix A): CSA where one exists, except the Atlanta CSA, which is split into its CBSAs.

| market_group                           | urban_rural_tier   |   counties |   fom_counties | county_names                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|:---------------------------------------|:-------------------|-----------:|---------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| (no metro/micro area)                  | rural              |         53 |              0 | Appling, Bacon, Baker, Banks, Berrien, Bleckley, Calhoun, Candler, Charlton, Clay, Clinch, Cook, Dodge, Dooly, Early, Elbert, Emanuel, Fannin, Franklin, Gilmer, Glascock, Greene, Hancock, Hart, Irwin, Jeff Davis, Jefferson, Jenkins, Lamar, Macon, Miller, Mitchell, Pulaski, Putnam, Rabun, Randolph, Screven, Seminole, Taliaferro, Tattnall, Taylor, Telfair, Towns, Treutlen, Union, Warren, Washington, Webster, Wheeler, White, Wilcox, Wilkes, Wilkinson |
| Atlanta-Sandy Springs-Roswell, GA      | metro              |         29 |             18 | Barrow, Bartow, Butts, Carroll, Cherokee, Clayton, Cobb, Coweta, Dawson, DeKalb, Douglas, Fayette, Forsyth, Fulton, Gwinnett, Haralson, Heard, Henry, Jasper, Lumpkin, Meriwether, Morgan, Newton, Paulding, Pickens, Pike, Rockdale, Spalding, Walton                                                                                                                                                                                                              |
| Macon-Bibb County--Warner Robins, GA   | metro              |          7 |              0 | Bibb, Crawford, Houston, Jones, Monroe, Peach, Twiggs                                                                                                                                                                                                                                                                                                                                                                                                               |
| Columbus-Auburn-Opelika, GA-AL         | metro              |          6 |              0 | Chattahoochee, Harris, Marion, Muscogee, Stewart, Talbot                                                                                                                                                                                                                                                                                                                                                                                                            |
| Savannah-Hinesville-Statesboro, GA     | metro              |          5 |              0 | Bryan, Chatham, Effingham, Liberty, Long                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Augusta-Richmond County, GA-SC         | metro              |          5 |              0 | Burke, Columbia, Lincoln, McDuffie, Richmond                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Chattanooga-Cleveland-Dalton, TN-GA-AL | metro              |          5 |              0 | Catoosa, Dade, Murray, Walker, Whitfield                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Albany, GA                             | metro              |          4 |              0 | Dougherty, Lee, Terrell, Worth                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Valdosta, GA                           | metro              |          4 |              0 | Brooks, Echols, Lanier, Lowndes                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Athens-Clarke County, GA               | metro              |          4 |              0 | Clarke, Madison, Oconee, Oglethorpe                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Savannah-Hinesville-Statesboro, GA     | micro              |          3 |              0 | Bulloch, Evans, Wayne                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Brunswick-St. Simons, GA               | metro              |          3 |              0 | Brantley, Glynn, McIntosh                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Americus, GA                           | micro              |          2 |              0 | Schley, Sumter                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Tifton, GA                             | micro              |          2 |              0 | Tift, Turner                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Vidalia, GA                            | micro              |          2 |              0 | Montgomery, Toombs                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Thomasville, GA                        | micro              |          2 |              0 | Grady, Thomas                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Waycross, GA                           | micro              |          2 |              0 | Pierce, Ware                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Dublin, GA                             | micro              |          2 |              0 | Johnson, Laurens                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Douglas, GA                            | micro              |          2 |              0 | Atkinson, Coffee                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Calhoun, GA                            | micro              |          1 |              0 | Gordon                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Jacksonville-Kingsland-Palatka, FL-GA  | micro              |          1 |              0 | Camden                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Gainesville, GA                        | metro              |          1 |              1 | Hall                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Fitzgerald, GA                         | micro              |          1 |              0 | Ben Hill                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Eufaula, AL-GA                         | micro              |          1 |              0 | Quitman                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Cordele, GA                            | micro              |          1 |              0 | Crisp                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Cornelia, GA                           | micro              |          1 |              0 | Habersham                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Cedartown, GA                          | micro              |          1 |              0 | Polk                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Chattanooga-Cleveland-Dalton, TN-GA-AL | micro              |          1 |              0 | Chattooga                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Moultrie, GA                           | micro              |          1 |              0 | Colquitt                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Rome, GA                               | metro              |          1 |              0 | Floyd                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| LaGrange, GA-AL                        | micro              |          1 |              0 | Troup                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Milledgeville, GA                      | micro              |          1 |              0 | Baldwin                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Jefferson, GA                          | micro              |          1 |              1 | Jackson                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Thomaston, GA                          | micro              |          1 |              0 | Upson                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Tallahassee-Bainbridge, FL-GA          | micro              |          1 |              0 | Decatur                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Toccoa, GA                             | micro              |          1 |              0 | Stephens                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

### 10. Expansion edge cases
Non-FOM counties where DCCU is already at or above 2% (expansion gain 0): Jasper (2.1%), Pike (4.5%), Lamar (5.8%), Meriwether (3.5%), Wilkinson (3.7%).

### 11. Lenders missing from the HMDA filers lists
LEIs with market originations that are missing from every cached HMDA `/view/filers` list, named from GLEIF instead (Phase 2 builds `lenders.csv`). Any LEI GLEIF can't name shows as `LEI ... (no name in filers list)`. All originations are kept.

|   year |   originations |   fom_originations | name                                 | name_source   |
|-------:|---------------:|-------------------:|:-------------------------------------|:--------------|
|   2025 |             62 |                 47 | PRC MORTGAGE, LLC                    | gleif         |
|   2025 |             55 |                  0 | Landmark 24 Mortgage, LLC            | gleif         |
|   2025 |             38 |                 36 | BRIDGEWAY LENDING PARTNERS LLC       | gleif         |
|   2025 |             34 |                 29 | Loyal Trust Bank                     | gleif         |
|   2025 |             32 |                 19 | ADVANTAGEFIRST LENDING INC.          | gleif         |
|   2025 |              9 |                  8 | VERUS RESIDENTIAL LOANCO, LLC        | gleif         |
|   2025 |              8 |                  8 | ARDRI LLC                            | gleif         |
|   2025 |              5 |                  3 | Climate First Bank                   | gleif         |
|   2025 |              4 |                  3 | OBSIDIAN FINANCIAL SERVICES, INC.    | gleif         |
|   2025 |              3 |                  3 | AMERICAS MORTGAGE PROFESSIONALS, LLC | gleif         |
|   2025 |              2 |                  2 | ASPIRE HOME LOANS, LLC               | gleif         |
|   2025 |              2 |                  2 | THE LOCAL LENDER, LLC                | gleif         |
|   2025 |              1 |                  0 | Local Bank                           | gleif         |
|   2025 |              1 |                  0 | New Story Lending LLC                | gleif         |
|   2025 |              1 |                  1 | MARLIN MORTGAGE CAPITAL, LLC         | gleif         |

### 12. Builder-owned lenders (contestable market)
`config/builder_lenders.csv`, **pending your review**. Rows with `include = 1` are left out of the contestable market (`opportunity_score_contestable`); `include = 0` rows are candidates that show the builder pattern (almost no refinance, purchases packed into a few tracts) but are not confirmed. Included lenders made 1,791 of 53,783 FOM originations in 2025. Contestable `fom_share` = **2.02%**. Depth opportunity: 533 loans on the full market, 529 on the contestable market.

| lender_name                        | builder                          |   include | basis                                                                               |   fom_loans |   fom_purchase_share_pct |
|:-----------------------------------|:---------------------------------|----------:|:------------------------------------------------------------------------------------|------------:|-------------------------:|
| DHI MORTGAGE COMPANY, LTD.         | D.R. Horton                      |         1 | builder-owned lender (DHI = D.R. Horton)                                            |         397 |                     1    |
| PULTE MORTGAGE LLC                 | PulteGroup                       |         1 | builder name in lender name                                                         |         375 |                     0.94 |
| LENNAR MORTGAGE, LLC               | Lennar                           |         1 | builder name in lender name                                                         |         198 |                     0.5  |
| TOLL BROTHERS MORTGAGE COMPANY     | Toll Brothers                    |         1 | builder name in lender name                                                         |         308 |                     0.77 |
| Taylor Morrison Home Funding, Inc. | Taylor Morrison                  |         1 | builder name in lender name                                                         |         259 |                     0.65 |
| NVR Mortgage Finance, Inc.         | NVR (Ryan Homes)                 |         1 | builder name in lender name                                                         |          85 |                     0.21 |
| INSPIRE HOME LOANS INC.            | Century Communities (to confirm) |         1 | believed builder-owned; data signature: 0% refi and 54% of GA purchases in 3 tracts |         169 |                     0.42 |
| PRC MORTGAGE, LLC                  | unknown                          |         0 | data signature only: 2% refi and 80% of GA purchases in 3 tracts                    |          47 |                     0.12 |
| VICTORY MORTGAGE, L.L.C.           | unknown                          |         0 | data signature only: 1% refi and 60% of GA purchases in 3 tracts                    |          92 |                     0.23 |
| TRAILBLAZER MORTGAGE L.L.C.        | unknown                          |         0 | data signature only: 0% refi and 49% of GA purchases in 3 tracts                    |         134 |                     0.34 |
| Landmark 24 Mortgage, LLC          | unknown                          |         0 | data signature only: 0% refi and 45% of GA purchases in 3 tracts                    |           0 |                     0    |
| First Heritage Mortgage, LLC       | unknown                          |         0 | data signature only: 4% refi and 42% of GA purchases in 3 tracts                    |         135 |                     0.33 |
| JET HOMELOANS, LP                  | unknown                          |         0 | data signature only: 0% refi and 27% of GA purchases in 3 tracts                    |          27 |                     0.07 |
<!-- phase3:end -->
