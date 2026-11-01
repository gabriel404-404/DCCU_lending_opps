# Session notes

Read this at the start of each session. Newest entry first.

---

## 2026-11-01: productize P1 (lender config, neutral names, per-lender layout)

### Where we are
**Productize phase: P1 of 3 is done and on GitHub.** DCCU is now one lender configuration. A full rebuild reproduces v1 exactly: 50 of 50 baseline comparisons match, in about 70 seconds. Next are **P2**, then **P3** (PRD §7). Both were approved on 2026-11-01 as part of the productize plan. Per CLAUDE.md, Claude restates the P2 plan (inputs, files, checks) and waits for a go-ahead before coding.

To start next time, say: *"Read docs/SESSION_NOTES.md and start productize P2."*

### What changed in P1
| Piece | Where |
|---|---|
| Lender config (facts, with sources) | `config/lenders/dccu/`: `lender.toml`, `footprint.csv`, `branch_exclusions.csv`, `branch_coordinates.csv` |
| Config loader | `config/lender.py` (picks the lender from the `MGM_LENDER` variable; the default is dccu) |
| One command | `.venv/Scripts/python src/run_all.py --lender dccu` (or `all`) |
| Market vs. lender stages | 01–03 are shared and loop over every configured lender for its raw files and presence checks; 04–07 run per lender |
| Per-lender folders | `data/raw/lenders/<key>/`, `data/processed/<key>/`, `outputs/<key>/` (with `FINDINGS.md` and `DATA_QUALITY.md`) |
| Regression baseline | `tests/baseline/dccu/v1/` (48 v1 CSVs) and `src/check_baseline.py`, which runs automatically and translates v1 names |
| Names | `dccu_*` → `lender_*`, `fom_*` → `footprint_*`; scope values `footprint` / `non_footprint`; no lender hard-coded in `src/` |

Also in P1:
- NCUA branches are found by charter number (pulled forward from P2).
- Generated HTML maps are git-ignored.
- `BASEMAP` is a setting.
- The interactive map opens on the lender's footprint.

### Next: P2 (approved)
1. **Product filter per lender (P-R7).**
   - Stage 03 stops filtering on `loan_type`, so the market files keep all loan types.
   - `lender.toml` gets `[market] loan_types = ["1"]`, and the lender stages apply it.
   - The lender's Phase 2 waterfall and its API reconciliation (`API_CHECK_FILTERS["loan_types"]`) must use the lender's loan types.
   - Expect market files about 1.5× bigger; log the sizes.
   - **Baseline:** DCCU's lender files must still match. The root market tables (statewide market size and waterfall) change by design, because they now count all loan types. Decide in the P2 plan how `check_baseline.map_v1` handles them, and say so at check-in.
2. **Market groups (P-R8).** Replace the Atlanta special case (`s.ATLANTA_CBSA` in `01_download.county_tags`) with a general rule: split the CSA that holds the footprint's main metro area. `market_group` then depends on the lender, so compute it in the lender stages, not in `ga_counties.csv`. DCCU's groups must come out identical.
3. **Ladder fallback (P-R8).** In `06_benchmarks.build_ladder`, if the footprint has fewer than 8 qualifying counties, use the top quarter of qualifying tracts instead. DCCU (20 counties) is unchanged.

### Then: P3 (approved)
Associated Credit Union, built from facts:
- **LEI:** from HMDA's `/view/filers` list.
- **Footprint counties:** from its own website. Fall back to LGE Community Credit Union if Associated's membership isn't county-based.
- **NCUA charter:** from the FOICU file.

Add `config/lenders/<key>/`, run `--lender all`, then check in with its key numbers. No FINDINGS narrative unless asked.

### Open items (yours)
1. Builder-lender list review (`config/builder_lenders.csv`); rebuild afterwards.
2. Merger review: 15 flagged lenders in `outputs/dccu/DATA_QUALITY.md`, Phase 3 check 8.

### Working notes for Claude
- `src/02_validate.py` has Windows (CRLF) line endings; keep them, or git shows every line as changed.
- For multi-line scripted edits, write a small script file in the scratchpad and run it. Long inline shell heredocs broke on quoting.
- The stages rewrite the `DATA_QUALITY.md` files: change the code, not the logs.
- Every DCCU run must pass the baseline check. If a change is intended (like P2's all-loan-types market), update `check_baseline.py`'s mapping on purpose and say so at check-in.

### Git, as practiced
Same as before: one commit per sub-phase after its check-in, with the session notes in their own commit.

---

## 2026-10-27 to 2026-10-30: Phases 3, 4 and 5 (v1 complete)

### Where we are
**v1 is done: all five phases are complete and on GitHub.** `FINDINGS.md` recommends **both, led by depth**, with three actions. The project is now framed as a **product for any lender, with DCCU as the illustrative example** (CLAUDE.md, PRD §1–2).

Next is the **productize phase** (PRD, Future phases): make the pipeline work for any lender, with DCCU as one configuration. Per CLAUDE.md, Claude writes that plan first and waits for approval. Finish the two reviews under Open items first.

To start next time, say something like: *"Read docs/SESSION_NOTES.md and write the productize plan."*

### What exists
| Piece | Where |
|---|---|
| One-page findings and recommendation | `FINDINGS.md` |
| Maps, charts, final tables, every quoted number | `outputs/` (`key_numbers.csv` backs FINDINGS) |
| Interactive map (double-click to open; needs internet for the basemap) | `outputs/mortgage_map.html` |
| Whole pipeline, one command (about 2 minutes once raw data is cached) | `.venv/Scripts/python src/run_all.py` |
| Stages | `src/01`–`07`; 06 and 07 are lender-neutral (lender comes from `config/settings.py`) |
| Hand-maintained lists | `config/builder_lenders.csv`, `config/branch_exclusions.csv`, `config/branch_coordinates_manual.csv` |
| Every check result | `DATA_QUALITY.md` (Phases 1–5) |

### Decisions made this session
- **Scoring year:** opportunity is scored on 2025 only; 2022–2025 feeds the trends.
- **Benchmark:** DCCU's FOM-wide share (1.96%), not its statewide share. Expansion target: 2%.
- **Trend:** per county, not per tract; purchase and refinance shown separately, with the market's refi mix.
- **Minimum volume:** no tract is dropped; tracts under 20 market loans get a `low_volume` flag.
- **Stability:** only 12 of the top 25 tracts survive the 2024–25 check, so findings lead with counties and the top 25 carries a `stable_top25` flag.
- **Builder-owned lenders:** a contestable-market score sits next to the main one; the list is pending your review.
- **Missing lender names:** looked up in GLEIF.
- **Branches:** the 28 public Georgia branches (behind-security, corporate-only and out-of-state sites excluded). The December 2025 snapshot is used for share by distance, the current one for the scorecard.
- **Market groups and tiers:** the hybrid OMB rule, with OMB's metro/micro/rural tiers.
- **Growth:** `growing` means above Georgia's 5.31%; named clusters need 1.5× that.
- **Benchmark ladder:** base = FOM average; stretch = the weakest top-quarter county (Spalding, 4.04%); ceiling = the top quarter pooled (6.17%).
- **Product framing:** new code, labels and outputs are lender-neutral.

### Key numbers (FOM, 2025)
- **DCCU:** 1,052 of 53,783 originations (1.96%), the #7 lender. Purchase share rose from 0.74% (2022) to 2.00%.
- **Top quarter vs. the rest:** 6.17% vs. 1.55% share. Market structure is similar, and the gap holds within like-for-like bands. Broker-submitted loans are 29% of the market in the weaker counties vs. 20% in the top quarter, and DCCU takes none.
- **Depth vs. expansion:** depth is 533 / 1,374 / 2,382 loans a year at base / stretch / ceiling. Expansion is at most 448 (all 139 non-FOM counties at 2%).
- **Proximity:** within a county, tracts within 2 miles of a branch run 1.14× the county average.

### Open items
1. **Builder-lender list** (`config/builder_lenders.csv`): confirm the 7 included lenders, and set `include` for the 6 data-signature candidates. Then rebuild; the contestable numbers update (FINDINGS quotes 529).
2. **Merger review:** 15 flagged lenders in DATA_QUALITY.md, Phase 3 check 8. HomeStar (no loans after 2023) and Home Point (none after 2022) are clear exits.
3. **Productize phase:**
   - a subject-lender config, and renaming the `dccu_*` columns (then dropping the `neutral()` helper)
   - footprint types and branch data by charter type (NCUA, FDIC)
   - product filters, and states beyond Georgia
   - a basemap license for commercial use
   - ladder rules that work for small footprints
4. **Repo size:** `outputs/mortgage_map.html` is 7 MB and committed, so each regenerated version adds to the git history. Consider git-ignoring it in the productize phase.

### Git, as practiced
Same as before: one commit per phase after the check-in, with the session notes in their own commit.

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
