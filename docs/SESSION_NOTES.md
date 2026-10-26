# Session notes

Read this at the start of each session. Newest entry first.

---

## 2026-10-26: setup, Phase 1 and Phase 2

### Where we are
**Phases 1 and 2 of 5 are done and on GitHub.** Next is **Phase 3: share, trend and opportunity metrics.** Per CLAUDE.md, Claude writes the Phase 3 plan first and waits for approval.

To start next time, open a session in `C:\Users\gabri\code\DCCU_lending_opps` and say something like: *"Read docs/SESSION_NOTES.md and write the Phase 3 plan."*

### What exists
| Piece | Where |
|---|---|
| Requirements (source of truth) | `docs/PRD.md` |
| Working rules for Claude, and About me | `CLAUDE.md` |
| Whole pipeline, one command | `.venv/Scripts/python src/run_all.py` |
| Raw downloads (820 MB, not in git, re-downloadable) | `data/raw/` |
| Market data, one file per year (not in git, rebuilt by run_all) | `data/processed/market_{year}.parquet` |
| Every check result and data issue | `DATA_QUALITY.md` |

### Decisions made so far
- **Scope:** all 159 Georgia counties. Primary focus is depth inside DCCU's **20 field-of-membership (FOM) counties**; secondary is opportunities elsewhere in Georgia.
- **Years:** 2022–2025 (2025 is the latest HMDA year; all on 2020 tract boundaries).
- **FOM list:** today's 20 counties from DCCU's eligibility page, applied to every year (logged as a limitation).
- **Atlanta MSA:** OMB 2023 list, used only as a map tag, not to define the market.
- **Market definition:** conventional, first lien, 1–4 units, site-built, principal residence, purchase or refinance (refinance includes cash-out), closed-end only (HELOCs excluded), no reverse or business loans. Purchased loans excluded. Lenders reporting these flags as exempt are kept.
- **HMDA download:** all outcomes kept (denials etc.) for future phases; share uses originations only.

### Key numbers
| Originations | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| GA market | 138,169 | 76,604 | 78,334 | 80,682 |
| FOM market | 95,442 | 51,884 | 53,033 | 53,783 |
| DCCU in GA | 1,305 | 537 | 930 | 1,154 |
| DCCU in FOM | 1,199 | 487 | 851 | 1,052 |

All DCCU counts reconcile exactly to the HMDA API.

### Open items for Phase 3
1. **Opportunity benchmark (decision needed):** the PRD scores opportunity against DCCU's overall share, but with a statewide market that share is diluted by counties where DCCU barely lends. Claude's recommendation: benchmark to DCCU's FOM-wide share.
2. **Purchase vs. refinance trend:** DCCU's 2022→2023 drop was almost all refinance (793 → 76) while purchase held steady. Claude will propose reading the year-over-year trend (R5) separately for purchase and refinance.
3. **Competitor mergers:** names are tracked by LEI, but a merger that retires an LEI isn't detected automatically. Check the top competitors by hand.

### Later phases, already known
- **Phase 4:** NCUA lists DCCU's 33 branches by address only, so they need geocoding (the Census geocoder is free).
- **Phase 4:** 15 tracts have zero households and 7 have unreliable ACS counts; flag them in density metrics.

### Git, as practiced so far
Edit and save → `git add` (stage) → `git commit` (snapshot with a message) → `git push` (upload to GitHub). One commit per idea; one push can carry several commits. Edit locally (Claude or VS Code), not on GitHub's website, to avoid the two copies drifting apart.
