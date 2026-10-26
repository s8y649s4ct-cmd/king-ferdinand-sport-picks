# KFSP improvements log

## 2026-10-26 (daily review #1)

**Record so far (graded, since site creation, all v1):**
- Main legs: 134/159 won (84.3%) vs 84.0% predicted (Brier 0.107). Totals 92% (78), spreads 82% (61), 3-way ML 40% (5), plus-money legs 40% (15).
- Main parlays: 11/77 won vs 16.1 expected (ladder 10/53 vs 13.9; lottery 1/23 vs 1.9, in line).
- Props tab legs 74.4% vs 78.3% pred; NBA 3s & rebounds 68.4% vs 75.8% (threes 75.6%, rebounds ~59%); NFL TD 40.4% vs 41.4% (calibrated, long shots by nature); Live legs 60.7% vs 62.3%.
- CLV: avg -0.08 pts, 52 beat close / 53 worse (no edge vs closing line yet).

**Main mistakes found:**
1. Ladder used second-tier alternate lines. Per game, the top-rated leg won 94.4% (36) while alternates within 5 pts of it won ~74-83%; same-market opposite-side alternates won only 58% (24). Ladder alt legs 61/69 vs top legs 24/25.
2. 90-95% bucket overconfident (77% actual, n=22) - not enough data yet for bucket calibration (needs 30).
3. Nested ladders share legs: one loss (Kraken +3.5 on 10-24) sank every ticket 7-27.
4. Long live tickets (7+ legs) won 3 vs ~13.8 expected, although their legs hit 83.6% vs 73.3% pred. Losses cluster in a few heavily reused legs during one busy slate (Sunday NFL window) - looks like clustering, not systematic. Monitoring, no change.
5. Grading gap: a board can list next-day games (PSG-Lyon on 10-25 board kicks off 10-26), which the grader would miss after the day passed.

**Backtests:**
- Ladder variants on 10-25 shadow slate (25 tickets): current 8 wins; top-leg-only 15 wins (36 unique legs); window 0.02 + no opposite-side same-market alternates 14 wins (62 unique legs); opposite-side exclusion only 11. -> ADOPTED variant C (keeps leg variety). Caveat: one slate.
- Per-sport/market calibration factors (leave-one-event-out): top-leg hits 34->32/36, log loss worse -> REJECTED.
- Props re-rank by FD no-vig or blend: no gain -> REJECTED. Rebounds weakness: contradictory evidence, one day -> monitor.
- v2 shadow: Brier tie, log loss slightly better (.492 vs .502) but top picks 30/36 (83%) vs v1 35/36 (97%) -> v2 NOT recommended. v1 stays live (legs.json untouched).

**Changes (backups in /workspace/kfsp_backups/2026-10-26/):**
- build.py ladder: alternates only within 0.02 of game's top leg, and never the opposite side of the same market type as the top leg.
- build.py grading: also fetch the day after each pending date so next-day games on a board get graded.
- Rebuilt and published (commit 3e049c7). Links (indexed, PA 742. IDs, max 25 legs), King's Favorites, pregame-only rule, update.sh unchanged.

**Expected effect:** higher ladder ticket win rate (backtest 8 -> 14 of 25 on one slate); unproven, re-check daily. Nothing guaranteed.
