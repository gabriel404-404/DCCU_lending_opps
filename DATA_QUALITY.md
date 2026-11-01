# Data quality log

Market-wide checks (Phases 1-2), shared by every lender. Each lender's own checks (presence in HMDA, branches, Phases 3-5 and the baseline check) are in `outputs/<lender>/DATA_QUALITY.md`.

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

`no_county_rows` are Georgia records with no county code. Downloads are by county, so these rows are not in the raw data. They can't be placed in a tract either, so tract and county metrics are unaffected; statewide totals are understated by `no_county_pct`. Lender checks 2, 3 and 8 (including each lender's own no-county records) are in `outputs/<lender>/DATA_QUALITY.md`.

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
<!-- phase1:end -->

<!-- phase2:start -->
## Phase 2: market definition

### Filter waterfall (2025; all years in `phase2_checks/filter_waterfall.csv`)
Filters run in order, so each row's count is after every filter above it. Rows with no county code (Phase 1, check 1) never enter, so the start is slightly below the statewide total. Each lender's own waterfall and reconciliation with the HMDA API are in `outputs/<lender>/DATA_QUALITY.md`.

| step                             |   rows_all |   originations_all |   originations_removed |
|:---------------------------------|-----------:|-------------------:|-----------------------:|
| start: all GA rows with a county |     511121 |             241969 |                      0 |
| exclude_purchased                |     447297 |             241969 |                      0 |
| conventional                     |     305450 |             166984 |                  74985 |
| first_lien                       |     204657 |             117839 |                  49145 |
| units_1_to_4                     |     203451 |             116888 |                    951 |
| site_built                       |     183778 |             112444 |                   4444 |
| principal_residence              |     146107 |              89940 |                  22504 |
| purchase_or_refi                 |     128938 |              82934 |                   7006 |
| closed_end                       |     124968 |              80858 |                   2076 |
| not_reverse                      |     124790 |              80758 |                    100 |
| not_business                     |     124660 |              80682 |                     76 |

### Exempt flags kept
Rows kept although the lender reported the field as exempt (`1111`), all years. Exempt lenders are small and rarely make these products.

| filter       | field                          |   rows_kept_with_exempt |
|:-------------|:-------------------------------|------------------------:|
| closed_end   | open-end_line_of_credit        |                   12023 |
| not_business | business_or_commercial_purpose |                   12008 |
| not_reverse  | reverse_mortgage               |                   12024 |

### Market size (originations, after all filters, statewide)
|   year |   market_originations |   market_purchase |   market_refinance |   market_no_tract |   lenders |
|-------:|----------------------:|------------------:|-------------------:|------------------:|----------:|
|   2022 |                138169 |             85616 |              52553 |                61 |       875 |
|   2023 |                 76604 |             63173 |              13431 |                32 |       828 |
|   2024 |                 78334 |             61581 |              16753 |                20 |       781 |
|   2025 |                 80682 |             58062 |              22620 |                46 |       807 |

### Rows without a census tract
`market_no_tract` originations stay in the market data (`has_tract = 0`) and count toward county and statewide totals, but can't be placed on the map or in tract metrics.

### Lenders
`data/processed/lenders.csv`: 1,863 LEIs with their latest reported name. Names come from the HMDA filers lists; market LEIs missing from every list are named from GLEIF (the global LEI registry).

| name_source   |   leis |
|:--------------|-------:|
| hmda_filers   |   1845 |
| gleif         |     18 |
<!-- phase2:end -->
