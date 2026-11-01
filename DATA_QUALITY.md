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
Filters run in order, so each row's count is after every filter above it. Rows with no county code (Phase 1, check 1) never enter, so the start is slightly below the statewide total. Loan type is not a market filter: the market files keep all loan types, and each lender's product filter (`loan_types` in its `lender.toml`) is applied in its own stages. Each lender's waterfall (with its product filter), product check and reconciliation with the HMDA API are in `outputs/<lender>/DATA_QUALITY.md`.

| step                             |   rows_all |   originations_all |   originations_removed |
|:---------------------------------|-----------:|-------------------:|-----------------------:|
| start: all GA rows with a county |     511121 |             241969 |                      0 |
| exclude_purchased                |     447297 |             241969 |                      0 |
| first_lien                       |     346393 |             192791 |                  49178 |
| units_1_to_4                     |     345173 |             191828 |                    963 |
| site_built                       |     319554 |             184116 |                   7712 |
| principal_residence              |     281360 |             161342 |                  22774 |
| purchase_or_refi                 |     262121 |             153768 |                   7574 |
| closed_end                       |     257246 |             151194 |                   2574 |
| not_reverse                      |     257056 |             151088 |                    106 |
| not_business                     |     256851 |             150975 |                    113 |

### Market by loan type (originations, after all filters, statewide)
`phase2_checks/market_by_loan_type.csv` also splits purchase and refinance.

|   year |   conventional |   FHA |    VA |   USDA |    all |
|-------:|---------------:|------:|------:|-------:|-------:|
|   2022 |         138169 | 38291 | 30228 |   1904 | 208592 |
|   2023 |          76604 | 35903 | 20338 |   1086 | 133931 |
|   2024 |          78334 | 38328 | 25830 |   1100 | 143592 |
|   2025 |          80682 | 41118 | 28031 |   1144 | 150975 |

Market files (all loan types, all actions):

| file                |   rows |   mb |
|:--------------------|-------:|-----:|
| market_2022.parquet | 356030 | 14.8 |
| market_2023.parquet | 228316 |  9.9 |
| market_2024.parquet | 240155 | 10.3 |
| market_2025.parquet | 256851 | 10.9 |

### Exempt flags kept
Rows kept although the lender reported the field as exempt (`1111`), all years. Exempt lenders are small and rarely make these products.

| filter       | field                          |   rows_kept_with_exempt |
|:-------------|:-------------------------------|------------------------:|
| closed_end   | open-end_line_of_credit        |                   12782 |
| not_business | business_or_commercial_purpose |                   12758 |
| not_reverse  | reverse_mortgage               |                   12784 |

### Market size (originations, after all filters, statewide, all loan types)
|   year |   market_originations |   market_purchase |   market_refinance |   market_no_tract |   lenders |
|-------:|----------------------:|------------------:|-------------------:|------------------:|----------:|
|   2022 |                208592 |            132586 |              76006 |                64 |       907 |
|   2023 |                133931 |            105181 |              28750 |                40 |       869 |
|   2024 |                143592 |            104712 |              38880 |                25 |       824 |
|   2025 |                150975 |            103211 |              47764 |                55 |       848 |

### Rows without a census tract
`market_no_tract` originations stay in the market data (`has_tract = 0`) and count toward county and statewide totals, but can't be placed on the map or in tract metrics.

### Lenders
`data/processed/lenders.csv`: 1,863 LEIs with their latest reported name. Names come from the HMDA filers lists; market LEIs missing from every list are named from GLEIF (the global LEI registry).

| name_source   |   leis |
|:--------------|-------:|
| hmda_filers   |   1845 |
| gleif         |     18 |
<!-- phase2:end -->
