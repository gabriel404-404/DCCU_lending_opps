# LGE baseline after the 2026-11-01 reviews (current)

Saved with `check_baseline.py --save p3-reviews` after three decided changes since `p3/`:
- Builder-lender review: all 13 rows in `config/builder_lenders.csv` included (was 7).
- Merger links in `config/lender_successors.csv` (merger review check only).
- Alpharetta branch excluded from the current NCUA snapshot (closed; kept for 2025). Expansion
  scorecard distances change, e.g. Gwinnett 16 -> 18 household-weighted miles.

Names are current. `p3/` stays as history; `../CURRENT` names this version. Do not edit these files.
