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
`data/processed/lenders.csv`: 1,845 LEIs with their latest reported name.
<!-- phase2:end -->
