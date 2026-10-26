"""Project-wide settings: years, IDs, URLs and paths, kept in one place."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

# HMDA years on 2020 census tracts. 2025 confirmed as latest published year on 2026-10-26.
YEARS = [2022, 2023, 2024, 2025]

# Confirmed in the HMDA /view/filers API (2024, 2025). Validation re-checks every year.
DCCU_LEI = "549300Y4BSP3BSFW7J29"
DCCU_NAME = "DELTA COMMUNITY CREDIT UNION"

STATE_FIPS = "13"  # Georgia
STATE_ABBR = "GA"
ATLANTA_CBSA = "12060"  # Atlanta-Sandy Springs-Roswell, GA (OMB Bulletin 23-01, July 2023)

HMDA_API = "https://ffiec.cfpb.gov/v2/data-browser-api/view"
GA_COUNTIES_URL = "https://www2.census.gov/geo/docs/reference/codes2020/cou/st13_ga_cou2020.txt"
OMB_DELINEATION_URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/"
    "reference-files/2023/delineation-files/list1_2023.xlsx"
)
TIGER_TRACTS_URL = "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_13_tract.zip"

# ACS 5-year table-based summary file: no API key needed. 2020-2024 is the latest release.
ACS_YEAR = 2024
ACS_B11001_URL = (
    f"https://www2.census.gov/programs-surveys/acs/summary_file/{ACS_YEAR}/"
    f"table-based-SF/data/5YRData/acsdt5y{ACS_YEAR}-b11001.dat"
)

# Market definition (PRD Appendix A). Each filter is applied to every lender, in this order.
# Values are HMDA codes; see docs/PRD.md for the reasoning.
MARKET_FILTERS = [
    ("exclude_purchased", "action_taken", "!=", ["6"]),
    ("conventional", "loan_type", "in", ["1"]),
    ("first_lien", "lien_status", "in", ["1"]),
    ("units_1_to_4", "total_units", "in", ["1", "2", "3", "4"]),
    ("site_built", "construction_method", "in", ["1"]),
    ("principal_residence", "occupancy_type", "in", ["1"]),
    ("purchase_or_refi", "loan_purpose", "in", ["1", "31", "32"]),
    ("closed_end", "open-end_line_of_credit", "!=", ["1"]),
    ("not_reverse", "reverse_mortgage", "!=", ["1"]),
    ("not_business", "business_or_commercial_purpose", "!=", ["1"]),
]
EXEMPT_CODE = "1111"

# The HMDA API counts with at most two filters, so DCCU is reconciled one filter at a
# time (originations + that filter). API parameter name -> (HMDA field, values).
# occupancy_type is left out: the API silently ignores that filter.
API_CHECK_FILTERS = {
    "loan_types": ("loan_type", ["1"]),
    "lien_statuses": ("lien_status", ["1"]),
    "total_units": ("total_units", ["1", "2", "3", "4"]),
    "construction_methods": ("construction_method", ["1"]),
    "loan_purposes": ("loan_purpose", ["1", "31", "32"]),
}

# NCUA quarterly call report zip; the download script picks the latest quarter that exists.
NCUA_URL_TEMPLATE = "https://ncua.gov/files/publications/analysis/call-report-data-{yyyy}-{mm}.zip"
