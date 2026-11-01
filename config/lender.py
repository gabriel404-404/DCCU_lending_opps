"""The subject lender for a run, read from config/lenders/<key>/lender.toml.

The MGM_LENDER environment variable picks the lender (run_all.py sets it from --lender);
the default is the illustrative example, dccu. Lender stages use LENDER; market stages,
which cover every configured lender, loop over configured() with load().
TOML is a plain-text config format; Python reads it with the built-in tomllib.
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from config import settings as s

LENDERS = s.CONFIG / "lenders"
DEFAULT = "dccu"


@dataclass(frozen=True)
class Lender:
    key: str
    name: str
    label: str
    lei: str
    charter: str
    ncua_charter: str | None
    loan_types: tuple             # HMDA loan_type codes in the lender's product filter
    footprint_label: str
    footprint_name: str
    footprint_file: Path
    footprint: frozenset          # county FIPS codes in the footprint
    branch_exclusions: Path
    branch_coordinates: Path
    expansion_target_share: float

    @property
    def raw(self):
        return s.RAW / "lenders" / self.key

    @property
    def processed(self):
        return s.PROCESSED / self.key

    @property
    def outputs(self):
        return s.OUTPUTS / self.key

    @property
    def data_quality(self):
        return self.outputs / "DATA_QUALITY.md"

    @property
    def findings(self):
        return self.outputs / "FINDINGS.md"

    @property
    def product_label(self):
        """Loan types in words, e.g. "conventional" or "conventional, FHA and VA"."""
        names = [s.LOAN_TYPES[t] for t in self.loan_types]
        return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]

    @property
    def product_step(self):
        """The product filter's name in the lender's waterfall, e.g. "conventional"."""
        return "_or_".join(s.LOAN_TYPES[t].lower() for t in self.loan_types)

    @property
    def api_check_filters(self):
        """HMDA API reconciliation filters: the lender's loan types, then the market's."""
        return {"loan_types": ("loan_type", list(self.loan_types))} | s.API_CHECK_FILTERS


def load(key=None):
    key = key or os.environ.get("MGM_LENDER", DEFAULT)
    folder = LENDERS / key
    with open(folder / "lender.toml", "rb") as f:
        c = tomllib.load(f)
    footprint_file = folder / c["footprint"]["counties"]
    counties = pd.read_csv(footprint_file, dtype=str)["county_fips"]
    loan_types = tuple(c["market"]["loan_types"])
    if not loan_types or set(loan_types) - set(s.LOAN_TYPES):
        raise ValueError(f"{key}: loan_types {list(loan_types)} must be HMDA codes in {list(s.LOAN_TYPES)}")
    return Lender(
        key=key, name=c["lender"]["name"], label=c["lender"]["label"], lei=c["lender"]["lei"],
        charter=c["lender"]["charter"], ncua_charter=c["lender"].get("ncua_charter"),
        loan_types=loan_types, footprint_label=c["footprint"]["label"], footprint_name=c["footprint"]["name"],
        footprint_file=footprint_file, footprint=frozenset(counties),
        branch_exclusions=folder / c["branches"]["exclusions"],
        branch_coordinates=folder / c["branches"]["coordinates"],
        expansion_target_share=float(c["expansion"]["target_share"]))


def configured():
    """Every configured lender (a folder under config/lenders/ with a lender.toml)."""
    return [load(p.name) for p in sorted(LENDERS.iterdir()) if (p / "lender.toml").exists()]


LENDER = load()
