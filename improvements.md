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

## 2026-10-26: King's Favorites tracking
- picks.history.json entries now carry `favorite` (bool) and `favorite_source` ('logged' = flagged at lock time by build.py; 'reconstructed' = backfilled with the green rule). Tracks the board until the ticket locks, then frozen: favorite = green at lock time.
- picks.json `favorites_record` has won/lost/pending/win_pct, `by_legs`, and per-ticket legs. Daily review should grade green tickets from these fields.

## 2026-10-27 (daily review #2)

**Record (graded through 2026-10-27 06:54 UTC)**
- Main legs: 212 graded, 81.1% hit vs 82.7% predicted (Brier .124). By date: 10-24 97.3% (37), 10-25 80.5% (123), 10-26 71.2% (52). Spread 78.8% (85, pred 85.4%); total 91.5% (94); alt spread 83.6% (61, pred 91.6%); NHL 66.7% (33).
- Ladder tickets: 10-25 won 5 of 27 (expected 8.7 by logged est, 5.6 by raw est); 10-26 lost all 13 graded (sizes 4-16; expected 5.6 logged, 3.6 raw); tickets 1-3 still pending on 10-27 soccer. 5+ leg ladder tickets: won 1 of 35 (logged expected 10.75, raw expected 5.9).
- Lottery 10-26: 0 of 16 graded. CLV: avg -0.08 pts over 334 legs (74 beat close, 76 worse), so neutral.
- King's Favorites, after the backfill below: 4-7 with 6 pending. 2-leg 2-0, 3-leg 1-0, 4-leg 1-1, 5-leg 0-2, 6-leg 0-2, 7-leg 0-2.
- Extra tabs:
  - Live legs 60.5% vs 62.0% (1039). Live 7-leg tickets 3/29, 8-10 legs 0/41.
  - Props legs 75.0% vs 78.4% (577); rebounds 62.9% vs 76.2%.
  - NBA 3s/reb 68.3% vs 75.4% (221); rebounds 60.8% vs 72.8%.
  - TD 41.4% vs 41.2% (58).

**Mistakes and root causes**
1. The calibration boost is wrong and can't fix itself. The 85-90% bucket factor (x1.10, now x1.07) came from 32 legs logged on 10-24 (93.8% hit). Every boosted leg then moves out of that bucket (to 0.91-0.99), so the bucket can never be updated. I recovered true raw probs for 974 board legs from the picks.json git history. Raw 0.85-0.90 legs hit 86.1% (108 history legs, raw .871, shown .948) and 86.0% (228 shadow legs). The raw model is calibrated; the boost adds about 7.5 pts per leg. Raw never reaches 0.90 (max .8997), so the 90-95 x0.85 and 95-100 factors never fire. Ranking is not inverted, but every multi-leg estimate is inflated.
2. Because of (1), green favorites drifted into 5-7 leg tickets whose true chance was 32-48% (for example, 10-25 6-leg est .501 vs raw .356, and 7-leg .516 vs .321). Those went 0-6, while 2-4 leg favorites went 4-1.
3. Grading bug: favorites were not frozen at lock. In the run where a ticket locked, the flag was recomputed from the post-start board, and at date rollover every unlocked ticket was cleared. As a result, all 10-26 favorites were missing from the record.
4. NHL high-probability legs: top leg per game was 6/11 for NHL vs 68/71 for all other sports. NHL legs at 0.85+ went 6/12. The sample is too small to act on, so I'm watching it.
5. Tracking: small ladder tickets aren't locked when the board's first game starts, because they get rebuilt from the remaining games. So 10-26 tickets 1-3 ended up on next-day soccer, and the graded version is the last rebuild. Not changed today (see proposals).

**Backtests**
- Ranking by raw instead of boosted probs (ladder sim on graded shadow, current construction C):
  - 10-25: 10 wins vs 16 for boosted. 10-26: 3 vs 3. 5+ leg wins: 6 vs 12 (10-25), 1 vs 1 (10-26).
  - Re-use penalty 0.10/0.20 changed little.
  - So the ladder ranking is NOT changed.
- Yesterday's ladder change (C) vs the old construction (A) on 10-26 shadow: 3 vs 4 wins of 15 (B 2, D 3). Over both slates C beats A 19 vs 12, but the 10-26 out-of-sample slate is a wash. Kept as is.
- Favorites rule using raw est >= 0.5 (same EV top-3) vs logged est, on final graded tickets:
  - 10-25: raw rule picks ladder 2, 3 (both won) vs actual 2, 6, 7 (1-2).
  - 10-26: raw rule picks 4, 2, 3 (4 lost, 2-3 pending) vs actual green 4, 5, 6, 7 (0-4).
  - Combined: 2-1 vs 1-6 (plus the Best Parlay in both).
- v1 vs v2 shadow (531 graded): Brier .1471 vs .1454, LL .479 vs .468. Top pick per game v1 47/52 (90.4%) vs v2 43/52 (82.7%). v2 is still not recommended; v1 stays live.

**Changes (build.py; backups in /workspace/kfsp_backups/2026-10-27/)**
- Every leg now carries `raw_prob` (pre-calibration). Ladder tickets carry `est_raw` (product of raw probs) and history legs store `raw_prob`. I backfilled 1256 history legs from the recovered git values. This lets the next review build calibration on raw probs and break the feedback loop.
- Green ladder favorites now require raw est >= 50%, ranked by raw est x payout. Best Parlay and the Kings Pick card stay green. The favorite_rule text is updated.
- Favorites freeze fix: a ticket that locks in this run keeps the flag it had on the board before its games started.
- I backfilled the 10-26 favorites from git: the last pre-lock version with the same legs was green for ladder 2, 3, 4, 5, 6, 7 and the Best Parlay.
- The leg/ticket probabilities used for picking are unchanged, so the picks themselves are the same.

**Expected effect**
- Green tickets on today's board: Best 5-leg plus ladder 2 (raw .79) and 3 (raw .69). The 5-leg (raw .48) is no longer green.
- Fewer but more reliable favorites. The green record now matches what was shown.

**Proposals for next review**
- (a) Once there are 30+ graded legs with raw_prob per bucket, compute calibration on raw, cap factors at 1.0 and make it monotone. Backtest the ladder before adopting, because the raw ranking lost on 10-25.
- (b) Lock ladder tickets at the board's first game start, or record each version that was shown.
- (c) NHL 0.85+ leg haircut if the pattern holds over more than 20 legs.

## 2026-10-27 approved changes (user OK, t41u)
Backups: /workspace/kfsp_backups/2026-10-27-approved/. v1 stays live.
1. **Calibration boost dropped.** All leg, ladder, Best Parlay, green and lottery estimates now use unboosted model probabilities. Evidence: raw 0.85-0.90 legs hit 86.1% (108 history) / 86.0% (228 shadow) vs ~95% shown with boost. Caveat: this morning's ladder re-rank sim on raw probs was 13 wins vs 19 boosted over 10-25/10-26 (all of the gap on 10-25; 10-26 tied), so watch ladder wins closely; estimates are now honest (e.g. today 4-leg est .51, 5-leg .37).
2. **Ladder tickets lock at first kickoff** of any of their games (ladder.lock.json). The shown ticket (legs, estimate, payout) is frozen and graded as shown; it no longer rebuilds onto later games.
3. **NHL trim:** NHL legs rated 0.85+ capped at 0.80. Backtest: NHL 0.85+ hit 5/10 (history raw) and 2/7 (shadow v1), vs other sports 117/128 (91.4%) and 209/237 (88.2%). NHL 0.80-0.85 legs were 5/5, so they are untouched. Replacing a 50% leg with a ~90% leg raises expected leg win rate. Revisit at 20+ graded NHL 0.85+ legs.
