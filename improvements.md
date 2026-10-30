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

## 2026-10-28 (daily review #3)
Backups: /workspace/kfsp_backups/2026-10-28/. v1 stays live (legs.json untouched).

**Record (graded through 2026-10-28 06:55 UTC)**
- Main legs: 321 graded, 76.9% hit vs 76.7% predicted (raw probs; Brier .138). 10-27: 70.5% vs 73.4% (105). Raw buckets calibrated: 75-80 80% (25), 80-85 84.6% (39), 85-90 86.3% (117).
- Ladder tickets: 17 of 91 (10-24 6/27, 10-25 5/27, 10-26 1/16, 10-27 5/21 vs 4.98 expected - first day on honest estimates, on target). 5+ leg ladder: 5 of 75 (10-27 5- and 6-leg tickets won).
- King's Favorites 6-11 overall; 10-27 went 2-1 (2-leg and 4-leg won, 3-leg lost on NHL Over 3.5), Best 5-leg pending (Serie A today).
- Lottery 2 of 53. Live legs ~61% vs 62% (1438). Props 74% vs 78%; NBA 3s/reb 69% vs 75%; TD 41.4% vs 41.2%.
- v1 vs v2 shadow (775 graded): Brier .155 vs .153, LL .495 vs .485; top pick per game v1 65/73 (89.0%) vs v2 59/73 (80.8%). v2 NOT recommended.

**Mistakes and root causes**
1. Rebound props are overrated in both tabs and even FanDuel's no-vig overrates them: props tab overs 66.7% vs 79.3% (63), unders 46.7% vs 64.5% (15); nba3r overs 68.3% vs 74.9% (104), unders 54.5% vs 63.7% (33). Consistent on 3 days (215 legs). Made threes also low: 75.0% vs 79.5% (108) and 73.0% vs 77.8% (159). Points, assists, shots are calibrated.
2. Grading bug: once a ticket lost, its other legs were never graded, so leg stats skipped legs that only sat in losing tickets (10-27 had 56 graded legs; 105 after the fix).
3. 10-27 ladder losses: Under 4.5 goals in Cagliari-Roma (est .83) sank 11 of 16 losing tickets; NBA Portland-Lakers went over every alt under (9 legs, one game). Single-game variance, not systematic. No change.
4. NHL 10-27 spreads 59% vs 62% pred (34) - calibrated after the trim; keep watching.

**Changes**
- extra.py (Player Props): rebounds -8 pts (unders -10), made threes -3 pts haircut on the estimate; FD-gap filter checks the pre-haircut number so legs stay eligible but rank honestly. Rule text updated.
- extra2.py (NBA 3s & rebounds): rebounds -6 (unders -8), threes -3. Same filter logic. Rule text updated.
- build.py: legs in a lost ticket keep getting graded (stats only; ticket results unchanged).
- Haircuts are about 2/3 of the observed gap to avoid overfitting. Rationale: swapping 65% rebound legs for ~77-80% points/assists/shots legs raises expected leg and ticket hit rate on those tabs.

## 2026-10-29 (daily review #4)
Record: main legs 73.5% hit vs 76.5% predicted (505 graded, Brier .162); 10-28 legs 71.2% vs 74.6% (163). Ladder 10-28 5/25 (expected 5.57, on target); 5+ leg ladder 7 of 96 all-time. Best Parlay 0-5 (estimates 14-22%, ~1 win expected). Lottery 2/110. King's Favorites 8-14 (2-leg 4-1, 3-leg 2-2, 4-leg 2-4, 5+ 0-7), 4 pending. Props 74.2% vs 77.5% (1130); Live 59.8% vs 61.3% (1861); NFL TD 41.4% vs 41.2% (58).
Mistakes: (1) rebound UNDERS hit 9/20 (props tab) and 22/42 (NBA tab) vs ~63% estimated even after yesterday's haircut; (2) cross-sport matching bug: FanDuel NBA Magic @ Raptors (event 761906) was matched to MLS D.C. United at Toronto FC on the word "toronto", so 6 NBA legs were graded on the soccer score (all were actually wins; no ticket result changed); (3) NBA alt totals >=.75 hit 77% vs 87% (74 legs, clustered by game).
Backtests: NBA totals haircut -.03/-.05/-.08 gave 18/17/19 ladder wins vs 20 baseline -> rejected. CFB overs -.05: +1 win on 11 legs -> not adopted (overfit risk).
Changes: excluded rebound unders in extra.py and extra2.py (rule text updated); build.py now tags each FanDuel event with its sport and only matches ESPN games of the same sport (19/19 still matched); regraded the 6 mis-matched legs (history + shadow) as wins on the real 129-99 final.
Calibration after 10-28 haircuts: NBA-tab rebound overs 72.2% vs 72.8% (54), threes 71.9% vs 74.5% (96); props-tab points overs 73.8% vs 80.3% (80, one day - watch). NHL overs 55.6% vs 79.3% (18 shadow) - watch.
v1 vs v2 shadow (1250): Brier .1666 vs .1662, top pick per game v1 87.4% vs v2 82.9% -> v2 not recommended; v1 stays live.
Backups: /workspace/kfsp_backups/2026-10-29/. Published commit 49d4b04.

## 2026-10-29 10:30 AM ET intraday review
Slate: NFL Panthers @ Packers (8:15 PM ET), CFB FAU @ North Texas and Troy @ JMU (7:30 PM ET), NBA Cavs @ Hawks, Kings @ Pelicans (8 PM), Grizzlies @ Blazers (10 PM), 11 NHL games (7-10 PM), Serie A Lecce @ Frosinone (1:30 PM) and Atalanta @ Fiorentina (3:45 PM).
Research: Love has no designation; GB out C Rhyan, G Glover, LB Franklin, WR Golden questionable (props tabs already exclude him). GB moneyline drifted -325 to -198 (now ~-3.5), which helps our Panthers +18.5 leg. FAU-UNT total moved 70.5 to 77.5 on 89% of handle; our Under 99.5 still has 22 pts cushion and FD price is re-read each refresh. Troy QB Crowder hurt (Kilcrease may play) and JMU RB Pettaway out; both favor JMU unders. NBA: Poole (NOP, ankle) questionable, Missi out, Kings missing Murray/Raynaud/Cardwell/Simmons; Memphis clean; no props on questionable players (auto-excluded). NHL projected goalies have no surprises; WSH on 2nd night of a back-to-back (our leg is Nashville +2.5). Weather: Green Bay 53F partly cloudy, no wind issues.
Pulls/replacements: none needed; no current leg is weakened by the news.
Grading: nothing new since the 3 AM review (10-28 fully graded except one lottery that uses today's Serie A games).
Patterns checked: NHL alt overs >=.75 in shadow 18/26 (69%) vs ~79% est, but main board 9/11; clustered on 10-27. Not clear enough to change; keep watching.
Changes: none to the model. v1 stays live; v2 not proposed. Locked ladder tickets untouched.

## 2026-10-29 3:00 PM ET intraday review
Research (as of ~3:10 PM ET): Lecce @ Frosinone 3-0 at 74' (our Over 1.5 already cashed). Fiorentina-Atalanta (3:45 PM) official lineups out: Atalanta bench Scalvini and Rowe, Fiorentina start Pellegrino; no reason to change Over 1.5 (.83) or Atalanta ML (.35). NHL starters mostly confirmed: Skinner (WPG) vs Vasilevskiy, Silovs vs Vejmelka (expected), Greaves vs Kochetkov, Knight vs Gibson, Swayman vs Hofer, Thompson (WSH, 2nd night of back-to-back) vs Saros, Dobes vs Oettinger, Sorokin vs Wallstedt; Malkin and Chinakhov back for PIT. NBA 1 PM report: Poole downgraded to doubtful (NOP, ankle; NOP on a back-to-back), Tyson and Meleek Thomas (CLE) questionable, Sharpe out, POR two-ways questionable; NOP ML moved -192 to -238. Our Kings legs are +19.5 to +21.5 vs a ~6.5 spread and our unders sit 13-23 pts above the 235.5 total, and Poole out leans under. NFL: Keisean Nixon (GB CB) added as questionable today; Golden still questionable (already excluded from props); Bryce Young and Love fully available. No props on any doubtful/questionable player.
Pulls/replacements: none; no current leg on any tab is weakened by the news.
Grading: no games finished since 10:30 AM (Lecce-Frosinone ends ~3:25 PM ET and grades on the next refresh).
Changes: none to the model; v1 stays live, v2 not proposed; locked ladder tickets untouched. Rebuilt and published via update.sh.

## 2026-10-30 (daily review #5)
**Record (graded through 10-29)**
- Main legs 609: 72.9% hit vs 75.2% est (Brier .1548, LL .488); 10-29 alone 68.0% vs 70.1% (100). CLV ~flat (+0.03 pts; 186 beat close vs 204 worse).
- 10-29 ladder 11/19 won vs 5.15 expected (5, 8, 9, 10, 12, 15, 18-leg all won). Favorites 11-14 overall (2-leg 5-1, 3-leg 3-2, 4-leg 3-4, 5+ 0-7); 10-29 greens 3-0. Best Parlay 0-4 (0.78 exp). Lottery 2/83 vs 5.34 exp.
- Props 1382 legs 74.5% vs 77.2% (10-29 calibrated 75.7 vs 76.1); NBA 3s/reb 499 legs 69.9% vs 74.3% (10-29 73.8 vs 72.5); NFL TD 65 legs 44.6% vs 41.3%; Live 2334 legs 60.5% vs 61.5%.
- Shadow 1487 graded: v1 Brier .1642 / LL .514, v2 .1624 / .506, but top pick per game v1 115/130 (88.5%) vs v2 111/130 (85.4%). v2 still not recommended; v1 stays live (legs.json untouched).

**Mistakes found**
- Model edge over the market is not predictive: props legs 6+ pts above FD no-vig hit 70.9% vs 77.4% est (FD said 69.3%); nba3r 66.0% vs 73.8% (FD 65.0%). Main board shadow: legs with v1 4+ pts over sharp hit 86% vs 93% est (sharp 87%).
- The 25-leg best-edge lottery picked the max-edge leg per game: 164 legs hit 61.0% vs 68.9% est (winner's curse). Tier lotteries are calibrated (35.4% vs 36.4%, 99 legs).
- 10-29 lottery losses were mostly NHL -1.5 favorites; NHL negative puck lines 13/41 (31.7%) vs 39.5% est but implied 36.7% — about 1 SE, not acted on.
- NBA totals still overrated since 10-27 (53 legs 69.8% vs 86.3%, 19 games), but the ladder backtest with a 3/5/8-pt haircut again lost (26 wins -> 21-23, 5+ leg 13 -> 8-9). Not changed.

**Changes (backups in /workspace/kfsp_backups/2026-10-30/)**
- build.py: the 25-leg lottery now picks per game the leg with the best chance + 0.25 x edge (was pure edge) and is labelled "best-chance lottery". Shadow backtest: selected legs 84.2% vs 69.9% hit, fewer losing legs per ticket on 4 of 5 slates. Lower payout (today 21 legs, 18.55x, est 1.6%).
- extra2.py (NBA 3s/reb): chance capped at FanDuel no-vig + 3 pts. Backtest: Brier .2051 -> .2043 (10-28+: .1989 -> .1983); top-20/day 80 -> 82 of 100, top-40 146 -> 149 of 197. Rule text updated.
- Rejected: same cap on Player Props (top-20 selection 82 -> 76-82, no clear gain); NBA totals haircut (ladder lost wins); NHL -1.5 haircut (sample too small).
- Published commit 4f1ccc1. FD links, PA/MD, favorites, pregame-only rule and update.sh unchanged.

## 2026-10-30 10:30 AM ET intraday review
Slate: Ligue 1 PSG @ Le Havre and Rennes @ Nice (2 PM ET), Lens @ Lille (4:05 PM), Bundesliga Mainz @ Elversberg (3:30 PM), La Liga Espanyol @ Villarreal (4 PM); NHL NJ @ VGK (6 PM), WPG @ FLA (7 PM), SEA @ CGY (8 PM); 10 NBA games (7-10 PM); CFB Tulane @ Charlotte (7 PM), Baylor @ UCF (7:30 PM), Kent St @ Sacramento St (10:30 PM).
Research: PSG without Dembele, Kvaratskhelia, Marquinhos, Nuno Mendes (FD Over 1.5 still -900; kept). NBA report: Sengun (back) questionable and Smart/Sheppard out for HOU; Jaylen Brown (knee) questionable for PHI; Luka cleared for LAL; Zubac/Haliburton out for IND (our IND legs are +18.5 or more, market moved IND +130 -> +260). NHL goalies unconfirmed: Hellebuyck vs Allen toss-up for NJ, Hill likely for VGK (Hart day-to-day), Daws vs Schmid, Daccord/Grubauer vs Wolf/Cooley. Weather fine at all outdoor games (open-meteo still 429s on some). Big moves: BOS -575 -> -900 (our CHI +31.5/+32.5 have huge cushion), HOU -175 -> -238, LAL -115 -> -148.
Problem: ladder tickets lock at first kickoff (2 PM ET), hours before the NBA status updates, and research.py only penalizes questionable key players for QB/goalie positions.
Change: build.py now reads legs.json "news_adj" (same-day only, ignored on other slates) and adds a per-team adjustment to that team's side/ML legs. Set -2.5 pts (same size as the existing questionable-key-player rule) for Houston (Sengun) and Philadelphia (J. Brown). Effect: HOU +1.5/+2.5/+5.5/-11.5 and PHI +15.5/+16.5 left the tickets; replaced by Knicks +12.5/+13.5, Mavericks +21.5 and other ~86-88% legs. Houston +9.5 stays (86.4% after the cut).
Grading: nothing finished since the 3 AM review (10-29 pending tickets use today's soccer games).
v1 stays live; v2 switch_ready already reported to the user, not re-proposed. Locked tickets untouched (none locked yet). Backups /workspace/kfsp_backups/2026-10-30-am/. Published commit 60c6ccf.

## 2026-10-30 3:00 PM ET intraday review
Status: all 21 ladder tickets (the main board and green favorites) locked at the 2 PM ET first kickoff, so they were reviewed but not changed.
Live: PSG 2-1 at Le Havre and Nice 3-1 Rennes at halftime, so both Over 1.5 legs have already cashed; PSG-or-Le Havre (no draw) leg is on track. Mainz-Elversberg (3:30), Villarreal-Espanyol (4:00), Lille-Lens (4:05) have not started.
Research (~3:05 PM ET): Sengun and Smart (HOU) still questionable/game-time with HOU on a back-to-back vs OKC Saturday, so the -2.5 news_adj stays; Jaylen Brown (PHI) still questionable, -2.5 stays. Edwards (MIN) out after knee surgery Thursday, already priced in (MIN -360 -> -265); our MIN +8.5 and LAC +22.5 legs keep their estimates. Clowney (BKN) downgraded to questionable; Isaiah Joe (DET) questionable; Zubac and Haliburton out for IND (our IND +23.5/+24.5 have big cushion). NHL goalies: Schmid (FLA) and Wolf (CGY) confirmed; Hart (VGK), Hellebuyck (NJ), Daws (WPG), Grubauer (SEA) expected. CFB weather fine (Charlotte 73F clear, Orlando partly cloudy). No props or NBA-tab legs are on questionable/out players (11 auto-excluded).
Line moves since lock: all locked legs within 1.6 pts of their lock estimate; biggest drop DET-BKN Over 202.5 86.1% -> 84.5%, Villarreal 83.8% -> 82.8%; Mainz-Elversberg Over 1.5 up 78.8% -> 82.4%.
Pulls/replacements: none needed on the unlocked Best Parlay, lottery, Props or NBA tabs (they re-price every refresh).
Grading: nothing finished since 10:30 AM ET; soccer grades on the next refreshes.
Changes: none to the model. v1 stays live; v2 switch_ready already reported, not re-proposed. Published commit 52aaaf8.
