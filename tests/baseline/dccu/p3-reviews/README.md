# DCCU baseline after the 2026-11-01 reviews (current)

Saved with `check_baseline.py --save p3-reviews` after two decided changes, so DCCU no longer
reproduces v1 on these files:
- Builder-lender review: all 13 rows in `config/builder_lenders.csv` included (was 7). Contestable
  depth 529 -> 527.
- Merger links in `config/lender_successors.csv` (Academy -> Guild, Caliber -> NewRez,
  Home Point -> The Loan Store): changes the merger review check only.

Names are current. `v1/` stays as history; `../CURRENT` names this version. Do not edit these files.
