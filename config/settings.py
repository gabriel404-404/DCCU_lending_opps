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

# NCUA quarterly call report zip; the download script picks the latest quarter that exists.
NCUA_URL_TEMPLATE = "https://ncua.gov/files/publications/analysis/call-report-data-{yyyy}-{mm}.zip"
