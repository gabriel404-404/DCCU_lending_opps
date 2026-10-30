# Findings: where DCCU's mortgage growth is (2025)

*Sample customer: Delta Community Credit Union (DCCU). Outside-in view from public HMDA data: conventional first-lien purchase and refinance originations by all lenders. DCCU's totals reconcile to the HMDA API with 0 mismatches. Every number traces to [outputs/key_numbers.csv](outputs/key_numbers.csv).*

**1. Momentum is real.** In its 20 field-of-membership (FOM) counties, DCCU's purchase share rose from 0.74% in 2022 to 2.00% in 2025. It is now the #7 lender there, with 1,052 of 53,783 originations (1.96%). Refinance share (2.10% → 1.82%) moved with the refi market. ([trend](outputs/chart_share_trend.png))

**2. Two FOMs, and the weaker one is underpenetrated, not over-competed.** The top-quarter counties (Fayette, Coweta, Butts, Henry, Spalding) run 6.17% share; the rest of the FOM runs 1.55%. Market structure is similar (county HHI 345 vs. 329; 69 vs. 68 lenders per hundred loans in a tract), and the gap holds in like-for-like tracts: 5.0–8.1% vs. 1.2–1.8% at every loan size and every level of competition. The one real difference: 29% of loans in the weaker counties come through brokers (20% in the top quarter), and DCCU takes 0%. ([map](outputs/map_footprint_share.png))

**3. Depth is the bigger prize.** Added loans a year if every lagging FOM tract rose to each benchmark:

| Benchmark | Share | Added loans a year |
|---|---|---|
| FOM average | 1.96% | 533 |
| Stretch: Spalding, DCCU's weakest top-quarter county | 4.04% | 1,374 |
| Ceiling: top-quarter counties pooled | 6.17% | 2,382 |

Fulton, Gwinnett, Cobb, DeKalb, Cherokee and Forsyth hold 73% of the base opportunity. The ceiling reflects decades of history and probably DCCU's membership base; treat it as a ceiling, not a target. Leaving out builder-owned lenders barely changes the base (529). ([opportunity map](outputs/map_footprint_opportunity.png), [by county](outputs/depth_by_county.csv), [top tracts](outputs/opportunity_top25.csv))

**4. Branches help, but they don't explain the gap.** Raw share falls from 2.77% within 2 miles of a branch to 1.19% beyond 10, but most of that is a difference between counties. Within the same county, tracts within 2 miles run only 1.14x the county average. 8 FOM counties have no public branch. ([distance](outputs/chart_share_by_distance.png))

**5. Expansion is smaller and slower.** Reaching 2% in all 139 non-FOM counties would add at most 448 loans a year, and new counties take years to get there. The largest single prize, Chatham (Savannah), adds 40 but sits 196 miles from the nearest branch. The fast-growing clusters that border the FOM are modest: Bartow–Dawson–Pickens (29), Carroll–Haralson (13) and a 12-county east/northeast arc (31). ([statewide map](outputs/map_statewide.png), [scorecard](outputs/expansion_scorecard.csv))

## Recommendation: both, led by depth

Depth inside the FOM is worth more (533 a year at the average, 1,374 at the stretch rung) than every expansion county combined (448 at most), and it needs no regulatory filing.

1. **Set stretch targets in the weaker FOM counties**, starting with Gwinnett, Forsyth and Cherokee: purchase-focused marketing plus realtor and builder relationships, measured against Spalding's 4.04%.
2. **Test loan officers before new branches** in the low-share counties without a branch (Jackson, Barrow, Walton, Paulding). Proximity is worth about 1.14x within a county; it won't close a 6.17% vs. 1.55% gap on its own.
3. **File one contiguous expansion**: Bartow, Dawson and Pickens (29 loans a year at 2%, growing 13.9%), with Carroll and Haralson next. Defer Savannah.

Open question for the CLO: whether to reach the 29% of weaker-county borrowers who come through brokers.
