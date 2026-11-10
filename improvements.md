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

## 2026-10-31 (daily review #6, ~3:10 AM ET)
Record: all tickets 37-217 graded. Ladder 35 of 158 graded (10-30: 2 of 23, 4.18 expected, 2 pending). Best Parlay still 0 wins (10-30 pending). Main legs 720 graded: 72.8% hit vs 75.9% predicted (Brier .159); 10-30 alone 73.3% vs 81.8% (overconfident).
Main mistakes 10-30: Lakers +11.5/+12.5/+13.5 at GSW, Hornets +13.5/+14.5, Kraken +1.5/+2.5, Villarreal DNB/Over 1.5, Tulane-Charlotte Unders, UCF +18.5/+19.5. Mostly NBA/CFB alt lines with blowouts or shootouts; same-game ladder stacking amplified the Lakers/Kraken losses.
Calibration (shadow 1717 graded): v1 Brier .1659, v2 .1639, sharp .1628. NBA spread/total and CFB alt lines ~4-6 pts overrated (even by sharp no-vig); NHL slightly underrated; soccer top legs 88% vs 83% est. Top pick per game: v1 86.1% vs v2 85.4% -> v2 not recommended.
Backtests (shadow, ladder rebuilt per day, 6 days):
- Per-sport recalibration fit leave-one-day-out (K=50/100/200): ladder wins 22/23/25 vs baseline 30 -> REJECTED (third time NBA/CFB haircuts lose wins out of sample).
- Same-game penalty 0.15 -> 0.1/0.2/0.25/0.3/0.35/0.5: 27/29/31/33/31/30 wins vs 30; gain driven by one day (10-25) and not monotonic -> REJECTED as noise. Per-game cap and alt-window 0.02 also no better.
Changes: none. v1 stays live; live_model/allow_switch untouched. Retest the same-game penalty once 10+ graded days exist.

## 2026-10-31 feature: Best 2-Leg Parlays + enhanced Track record (user request t52u)
- twoleg.py: 2-leg pregame tickets only when both legs are their game's top v1 leg, from different games, each calibrated >= 92% (sport + 2.5-pt bucket from graded shadow legs, shrink weight 15, NHL 85%+ capped at 80% first) and joint >= 85%. Each leg used once; no padding.
- Backtest (leave-one-day-out, 6 graded days): 92% bar 7/7; 90% 7/8; 88% 7/9; 86% 10/15; 80% 43/59. Strictest bar adopted. Small sample.
- record.py: every graded ticket gets leg results, final scores/margins, reason tags (blowout, shootout, line move, same-game stack) and a lesson tied to the reviews. No model change; v1 stays live.

## 2026-10-31 10:30 AM ET intraday review
Status: 8 of 25 ladder tickets already locked (games from 8:30 AM ET onward); not changed. Early results: Chelsea 2-0 Man United final (our Over 1.5 cashed); Atletico at Levante 83', Monza-Bologna 41', five Bundesliga 10:30 AM games underway.
Research (~10:45 AM ET): NBA ESPN report: PHI on 2nd night of back-to-back with LeBron (rest) day-to-day and Embiid likely to sit one of the pair (PHI only -1.5 at depleted CHA); HOU on back-to-back, Sengun and Sheppard (back) day-to-day; MEM Pippen Jr./Jerome questionable; UTA Markkanen questionable; POR Morant out 4 weeks; OKC without Holmgren, J. Williams, Wallace, Caruso (already priced, HOU -166 -> -142); NOP Poole and Missi out; SAS Harris out; CLE Tyson out. CFB: K-State QB Knuth ruled out Friday night (third starter in 3 weeks; KSU -162 -> +124); Rutgers QB Lonergan out vs Michigan; Ohio State without Sayin at USC; Miss St without Taylor at Texas (all priced). Weather fine except showers at Colorado (wind 4 mph).
Problem found: main-board player-prop legs had no injury filter (the Props tab does). Reed Sheppard 2+ assists (back, day-to-day) was on tickets 11 and 25.
Changes (backups /workspace/kfsp_backups/2026-10-31-am/):
- build.py: main-board prop legs for players ESPN lists Out/Doubtful/Questionable/Day-To-Day (NBA/NHL), or named in news_adj "players", are dropped (57 legs removed today). Same rule the Props tab already uses.
- legs.json news_adj (today only, -2.5 pts on side/ML legs): PHI, HOU, MEM, UTA (questionable stars, tickets lock before the NBA status update) and Kansas State (QB change; research form edge was from games with other QBs). Effect: K-State +18.5 left ticket 16; PHI +15.5 drops 90.0% -> 87.5% and left the 1-leg ticket.
- Tickets 11 and 25 had already locked with the Sheppard leg; left as-is (FanDuel voids a player prop if he doesn't play).
v1 stays live; v2 switch_ready already reported, not re-proposed. Published c500b7b.

## 2026-10-31 3:00 PM ET intraday review
Status: all 25 ladder tickets (main board and green favorites) locked earlier today; reviewed, not changed.
Graded so far today: 11 of 14 finished soccer legs won. Misses: Brighton 1-0 at Man City (Over 1.5, 81%), Paderborn 0-0 at Gladbach (Over 1.5, 82%), Stuttgart 4-2 at Leverkusen (Leverkusen-or-draw, 76%). Tickets 12, 13, 19, 23 and 25 lost; 40 tickets still pending. Live at ~3:05 PM ET: Philadelphia-Cincinnati 0-0 at halftime (Over 1.5 is on 6 tickets, the biggest risk), Bruins +1.5 tied 2-2 after 2, Blues +2.5 down 2 in the 3rd. All CFB Unders and spreads from the noon games are well ahead.
Pattern: today's losses were all low-scoring soccer Overs and one upset; soccer Over 1.5 legs at 81-82% are close to their historical rate (soccer top legs ran 88% vs 83% est through 10-30). One day, not acted on.
Research (~3:05 PM ET): ESPN NBA report now has LeBron James and Joel Embiid both OUT for PHI at CHA (market moved PHI +13.5 from -900 to -670); HOU has Sheppard, VanVleet, Adams OUT, Sengun no longer listed; MIN Gobert day-to-day (Edwards out); MEM Pippen Jr./Jerome still day-to-day. NHL goalies: Ottawa confirmed Samuel Ersson (0-3-1, .849) with Ullmark on IR; Calgary starting call-up Arsenii Sergeev (2nd career start) at Colorado; Buffalo starter unclear (ESPN Ellis, Daily Faceoff projects Luukkonen). Weather: rain at Washington-Nebraska, thunderstorms at ULM, showers at BYU/Memphis/Boise (supports the Unders on those boards).
Changes (backups /workspace/kfsp_backups/2026-10-31-pm/):
- legs.json news_adj (today only, -2.5 pts on side/ML legs): added Ottawa Senators (weak backup goalie) and Calgary Flames (call-up goalie); PHI and HOU reasons updated to the 3 PM report. Same size as the existing questionable-key-player rule. Effect is on the unlocked Best Parlay and lottery tickets, which re-price every refresh (Ottawa -1.5 was on two lottery tickets).
- Locked legs on Reed Sheppard props (2 tickets) will be voided by FanDuel since he is OUT; nothing to change.
v1 stays live; v2 switch_ready already reported, not re-proposed.

## 2026-11-01 3:00 PM ET intraday review
Status: all 25 ladder tickets (main board and green favorites) locked at the morning first kickoff; reviewed, not changed. (The 3 AM and 10:30 AM runs today failed, so this is the first logged review of 11-01.)
Graded so far today: 10 ladder tickets lost, 0 won, all from two soccer legs that each sat on 7 tickets: Venezia 0-1 Como (Over 1.5) and Sevilla 1-3 Getafe (Under 3.5). 1 PM NFL games and Jets-Hurricanes were in progress at ~3 PM ET.
Pattern check (all graded legs, deduped): soccer totals are roughly calibrated overall (Serie A Overs 60% vs 64% est, 15 legs; La Liga Overs 3 of 5); NFL Unders 22 of 23 (95.7% vs 93.1%); NBA sides 77.3% vs 80.6%. The real problem today was one leg repeated across many ladder tickets (max leg reuse 9), but the same-game/reuse penalty backtest on 10-31 was rejected as noise, so no model change; retest once 10+ graded days exist.
Research (~3:00 PM ET): ESPN NBA report has Stephen Curry (rest) and Draymond Green (back) OUT for GSW vs LAC, with Butler, Porzingis and Moody also out; Clippers without Beal and Strus. Pacers: Haliburton, Zubac, McConnell out, Toppin questionable, Nesmith probable. Celtics rest Mitchell Robinson. Raptors without Kawhi Leonard. NFL late inactives: Chargers six players out (WR Wease, Thompson; CBs Shelley, Jackson, Leonard); Patriots without A.J. Brown and TreVeyon Henderson; Eagles without DeVonta Smith, Wicks, Covey, J. Campbell, Jonathan Jones (Barkley active); Commanders lose DT Daron Payne (season-ending). Lines: Rams -192 -> -290, Patriots -325 -> -345, Celtics -258 -> -298. Weather: thunderstorms in Miami (supports our NE-MIA Unders), showers in Denver, fine elsewhere. NHL goalies: Wallstedt vs Thompson, Vladar vs Vejmelka (expected), Garand vs Tomkins (both backups), Brossoit vs Ottawa backup Jonas Johansson (expected) on Ottawa's back-to-back.
Changes (backups /workspace/kfsp_backups/2026-11-01-pm/):
- legs.json news_adj (today only, -2.5 pts on side/ML legs): Golden State (Curry and Green out, form edge stale) and Ottawa (backup goalie on a back-to-back). Players list: Curry, Green. Same size as the existing rule. Effect: Warriors +6.5/+9.5/+13.5 left the Best Parlay and every lottery (replaced by game Unders and other legs); Ottawa legs drop ~2.5 pts and stay only on the long-shot lotteries.
v1 stays live; v2 switch_ready already reported, not re-proposed. Locked tickets untouched.

## 2026-11-02 (daily review #7, ~3:00 AM ET)
Record (all graded tickets): 54 won, 289 lost. Ladder 50-160 (11-01: 8 of 25 vs 5.39 expected; 10-31: 5 of 25 vs 6.24). Best Parlay 1-7. Lottery 3-122 (11-01: 0 of 18 vs 2.07 expected). Green favorites 18-20. 2-leg board: no ticket has qualified yet. Main legs 1,101 graded: 75.1% hit vs 76.2% predicted (Brier .146).
Calibration: the main 90-95% bucket is 44 of 57 (77%) but all 13 misses came on 10-25/10-26, before the calibration boost was dropped; 44 of 44 since. NBA main legs 77.4% vs 82.6% est (368), NHL 63.0% vs 66.6% (192), CFB 86.3% vs 83.2% (205). Props tab 74.1% vs 77.2% (2,246 legs), overconfident every single day (8 of 8), worst in the 85% bucket (78.4% vs 87.1%). NBA 3s & rebounds 70.9% vs 73.9% (740). TD scorers 43.5% vs 40.8% (131). Live 61.9% vs 62.7%, model no better than FanDuel no-vig.
Root cause found: on props, legs where our estimate was 3-10 pts above FanDuel's no-vig chance hit only 72% (est 79%), while legs at or below FanDuel hit 78%. The model's edge over the market is not predictive (same finding as the main board on 10-30).
Change (backup /workspace/kfsp_backups/2026-11-02/): extra.py caps each player-prop estimate at FanDuel's no-vig chance. Backtest on graded props: Brier .1891 -> .1875; best 20 legs per day (one per player) 79.4% -> 81.2% (better on 4 days, equal 2, worse 2); best 40 per day 77.2% -> 81.6%. Same cap tested on the NBA 3s & rebounds tab (already capped at FD +3): no gain in top picks, not adopted.
2-leg board backtest now 13 of 19 (68%) vs 88.8% average joint estimate, so the 92% bar is not loosened (loosening would add weaker tickets).
Shadow (2,963 graded legs): v2 Brier .1538 vs v1 .1550; top pick per game v2 86.5% vs v1 85.1% (289 games). v2 now leads on both, but v1 stays live (live_model/allow_switch untouched); recommended to the user only.
Published 49bce9a.

## 2026-11-02 10:30 AM ET intraday review
Status: v1 live (live_model/allow_switch untouched). 25 games today (25 FanDuel-matched). No ladder ticket locked yet at review time (first kickoff Fiorentina-Sassuolo 12:30 PM ET).
Graded: nothing new since 3 AM (no game finished today yet). Only two 11-01 Lottery tickets with today's soccer legs remain open. Record unchanged: ladder 50-160, Best 1-7, Lottery 3-122, green 18-20, 2-leg board 0-0.
Research (NBA official injury report 10:30 AM ET; 8 teams not yet submitted: IND, BKN, ORL, BOS, LAL, GSW, TOR, LAC): Kyrie Irving Q (DAL), Joel Embiid Q (PHI, FanDuel Research lists out; PHI ML -650 to -537), Jalen Johnson Q (ATL, ML -298 to -199), Scotty Pippen Jr. D + Quinten Post Q (MEM, ML -250 to -196), Alex Sarr Q (WSH; ORL ML -120 to -155). Curry/Green day-to-day (we are on PHX side, favorable). NHL (Daily Faceoff, 0 of 8 confirmed): Tarasov vs Markstrom (FLA goalie penalty already applied), Hart vs Swayman, Blackwood vs Knight, Wolf vs Askarov. MNF CHI@SEA: ~50F, wind 2 mph, no weather factor; SEA without LT Charles Cross and Shaheed, Nwosu doubtful; SEA ML -218 to -180, spread -3 and total 46.5 unchanged at FanDuel. Other moves: MIN -345 to -470, SA -800 to -1180, GSW -180 to -149, SJ +2.5 -800 to -650.
Changes (backup /workspace/kfsp_backups/2026-11-02-am/): legs.json news_adj (today only) -2.5 pts on DAL, PHI, ATL, MEM, WSH side/ML legs; Irving, Embiid, Jalen Johnson, Pippen Jr., Sarr, Post added to players list (their props excluded). Effect: those teams' side legs on ladder/best/lottery tickets fell from ~72 slots to 17 (only deep cushions such as ATL +11.5, MEM +11.5 remain). Best Parlay swapped ATL +4.5 and MEM +4.5 for CHI-PHI Under 251.5 and MIA-LAL Under 249.5 (est 24.5% -> 23.8%, still 4.33x). Dallas +1.5 removed from all 7 Lottery tickets. Ladder tickets 2-25 re-priced before lock. Published 97f09d2.
Pattern check (graded unique ladder legs): hit rates are flat across leg types (NBA spreads 87.0% vs 90.0% est, NBA totals 86.6% vs 89.4%, soccer totals 87.1% vs 81.0%, NHL totals 86.0% vs 80.2%, NHL puck lines 82.9% vs 79.7%, CFB 89%). NBA ladder legs run ~3 pts overconfident (243 legs, z~1.6, not significant) but since real hit rates are equal across types, a re-weight would not raise ticket win rate. No model change.
Problems: Open-Meteo 503 for Atalanta coordinates; Osasuna-Deportivo weather reads 87.7F (likely bad geocode, not a factor in picks); ESPN NHL gamelog 404s.
v1 note: v2 still leads in shadow (recommended to user only, not switched).

## 2026-11-02 3:00 PM ET intraday review
Status: v1 live (live_model/allow_switch untouched). Ladder tickets lock one by one as their first game starts: 19 of 25 locked at review time (17 before the rebuild, 2 more locked by the 3 PM soccer kickoffs); none unlocked. Unlocked: ladder 1-5 and 8, Best Parlay, 8 Lottery tickets.
Graded since 10:30 AM: Fiorentina 4-2 at Sassuolo, Over 1.5 won (on 12 tickets). An 11-01 6-leg best-chance Lottery ticket cashed (Lottery now 4-123); the other open 11-01 Lottery lost. In progress at ~3:05 PM ET: Parma-Atalanta and Brest-Lorient 0-0 at 14' (Over 1.5 on 10 tickets; Under 3.5 on 15), Everton-Newcastle and Osasuna-Deportivo just kicked off (Unders on 17 and 19 tickets). No new losing legs today, so no new pattern to act on.
Research: NBA official injury report 3:00 PM ET (LAL, GSW, TOR, LAC not yet submitted). Indiana now without Siakam (rest), Nembhard, Nesmith, Haliburton, McConnell, Zubac (ATL ML -298 -> -408). Kyrie Irving Q -> DOUBTFUL; Alex Sarr Q -> OUT; Embiid still Q; Pippen Jr. D, Post Q; Jalen Johnson still Q. New: Paul George OUT (rest) for BOS at HOU (HOU also without Adams, Capela; Sheppard Q); Zach LaVine Q, Keegan Murray out (SAC); Dejounte Murray Q (NOP); LaMelo Ball and T. Shannon Jr. Q (MIN, Edwards out). NHL (Daily Faceoff, 5 of 8 confirmed): Tarasov vs Markstrom (returns from injury), Swayman confirmed vs Hart (unconfirmed), Wolf vs Askarov (likely), Colorado projected backup Wedgewood (.889) vs Knight; Avs +1.5 drifted -750 -> -650. MNF CHI@SEA: SEA ML -218 -> -175, no new weather factor.
Changes (backup /workspace/kfsp_backups/2026-11-02-pm/), legs.json news_adj today only, same -2.5 pt rule:
- Added Indiana, Boston, Sacramento, New Orleans and Colorado (backup goalie). Removed the 10:30 AM Atlanta penalty: Johnson is still Q but Indiana lost three more starters and the market swung hard to ATL, so the penalty pointed the wrong way.
- Reasons updated for DAL, WSH, PHI, MEM. Players list (props excluded): George, Sheppard, LaVine, D. Murray, Ball, Shannon Jr., Toppin, Watson, Alvarado, Diallo, Nance Jr. (117 main-board prop legs injury-excluded this build).
- Effect on unlocked tickets: ladder 1 is now Atlanta +6.5 (90%); Atlanta +1.5 replaced other legs on 6 Lottery tickets; Best Parlay unchanged (VGK +1.5, DET +3.5, HOU +3.5, TOR +3.5, Under 242.5; 24.5%, 4.38x). HOU +3.5 kept: Boston is the team losing a starter.
No model change (no backtest-backed fix today). v2 still leads in shadow; recommended to the user only, not switched.

## 2026-11-03 (daily review #8, ~3:00 AM ET)
Record (all graded tickets): 65 won, 324 lost (16.7%) vs 73.9 expected. Ladder 58-177 (11-02: 8 of 25), Best Parlay 1-8, Lottery 6-139 (11-02: 2 of 18), green favorites 21-21, 2-leg board 0-0 (none qualified). Main legs 1,238 graded.
Calibration (stats.json): 85-90% bucket 87.1% vs 87.3% (519), 80-85% 82.9% vs 82.6%, 95%+ 94.5% vs 96.0%; 90-95% still 78% overall because of the 10-25/26 misses. NBA legs 76.1% vs 80.9% est (477) remain the most overconfident; NHL 62.6% vs 66.6%; CFB 86.3% vs 83.2%.
11-02 losses: Heat +17.5 at Lakers (on 9 tickets), NOP-MEM Unders 252.5/253.5/254.5 (16 slots), Sharks -1.5 (5), Booker prop (5). Same pattern as 11-01: one leg reused across many ladder tickets sinks several at once. Now 10 graded days exist, so a leg-reuse cap is due for a proper rebuild-based backtest; not adopted tonight without one (no quick simulation possible from ticket logs alone).
No model change. v1 stays live; v2 still leads in shadow (recommended to the user only).

## 2026-11-03 ~10:10 AM ET full backtest (user t54u: "do whatever works best"; 10:11 AM "still want good payouts")
Backup /workspace/kfsp_backups/2026-11-03/. Backtest: re-ran the ladder/Best/Lottery builders on every graded shadow leg, 9 graded days (10-25..11-02), scoring win rate AND payout/ROI per $1.
Baseline v1: ladder 1-4 legs 26/36 (1.3x, ROI -0.09); 5+ legs 33/177 (avg 11.6x, ROI +0.27); green 21/34; Best 1/9; Lottery (25-1000x) 1/34; top pick per game 83.7%.
- Leg-reuse cap 3/5/8: 5+ legs 21/139, 25/156, 25/169 (ROI -0.51/-0.15) -> REJECTED (fewer wins; sharing the best legs beats spreading to weaker ones).
- NBA shrink 10%/20%: 1-4 legs 25/36, 24/36; green 21/32, 15/27; Lottery 0/34 -> REJECTED.
- v2 live: top pick 84.9% vs 83.7%, but 1-4 legs 24/36, 5+ 27/176 (ROI -0.27), green 22/38, Lottery 0/34 -> REJECTED, v1 stays live. (v2+shrink+cap3 combo 30/142 ROI -0.19: worse ROI, cherry-picked, rejected.)
- Leg floor 0.85 on 5+ leg tickets: 5+ win rate 19% -> 31% (30/98) but avg payout 11.6x -> 3.5x, ROI +0.27 -> 0.00, and today's ladder would stop at 4 legs. 0.82: 29/134, 4.5x, ROI -0.11. REJECTED per payout requirement; code kept behind legs.json ladder_leg_floor_5plus=0 (off).
- Locked-ticket safety: a shorter ladder now keeps already-locked tickets instead of dropping them.
BUG FIXED: 0-candidate builds (published blank boards ~11:07 PM-12:44 AM, 5:03-5:45 AM, 9:30-9:32 AM ET) - FanDuel PA content page returned an empty event list (valid JSON, so no NJ fallback and it was cached). Now: empty event list -> NJ fallback; and if a build still has 0 candidates while games remain, build.py aborts (exit 3) so the last good board stays up.
Published 8027246 (site 200). Ladder 13 tickets.

## 2026-11-03 10:30 AM ET intraday review
Status: v1 live, no ladder locked (first puck drop 7:00 PM ET). Slate: 11 NHL, 2 CFB, no NBA/NFL. Graded: nothing new since 3 AM (record ladder 58-177, Best 1-8, Lottery 6-139, green 21-21).
Research (Daily Faceoff ~10:35 AM ET, 2 of 22 confirmed): Wedgewood (backup) confirmed for COL at CBJ; Bobrovsky confirmed for TOR vs UTA (3+ GA in 9 of 10); Lankinen projected for VAN (.807).
Change (backup /workspace/kfsp_backups/2026-11-03-am/): news_adj today -2.5 pts on COL, TOR, VAN side legs (same rule as 11-02). No model change; the 10:10 AM backtest already covered fixes (all rejected except the blank-board bug fix). v2 still behind v1 on ticket backtest, stays off.
Published 230f20a.

## 2026-11-03 3:00 PM ET intraday review
Status: v1 live, no ladder locked yet (first puck drop 7:00 PM ET). Graded: nothing new since 3 AM (ladder 58-177, Best 1-8, Lottery 6-139, green 21-21).
Research (Daily Faceoff ~3:05 PM ET, 16 of 22 confirmed): Cossa (.859) confirmed for UTA at TOR; Garand (.845 last 4, 0-4-0) for NYR vs STL; backup Brossoit for ANA at VAN; Wedgewood, Bobrovsky confirmed, Lankinen likely (already adjusted at 10:30). Strong starters: Wallstedt (MIN), Fowler (MTL), Oettinger (DAL), Hellebuyck (NJD), Kochetkov likely (CAR).
Change (backup /workspace/kfsp_backups/2026-11-03-pm/): news_adj today -2.5 pts on UTA, NYR, ANA side legs (same rule). No model change; no new evidence beyond the 10:10 AM backtest. v2 stays off.
Published bebec1a (site 200).

## 2026-11-04 (daily review #9, ~3:00 AM ET)
Record (all graded tickets): 67 won, 349 lost (16.1%) vs 80.9 expected. Ladder 59-189, Best 1-9, Lottery 7-151, green 21-24, 2-leg board 0-0. 11-03: 2 of 27 (all-NHL slate plus 2 CFB). Main legs 1,291 graded.
Calibration: 85-90% bucket 86.9% vs 87.3% (525), 80-85% 82.4% vs 82.6%; 90-95% still 78% (10-25/26 misses). NHL legs now 61.0% vs 66.2% est (246), the most overconfident sport; NBA 76.1% vs 80.9%. Props 22.7% vs 28.9%.
11-03 losses: wide spread of NHL totals (Over 6.5 and Under 5.5/6.5/7.5/8.5 both missed on various games), puck lines (NJD/CAR/MTL/ANA -1.5) and several +1.5 legs (DET, STL, PHI, COL, CAR); CFB Unders 60.5/61.5. Root cause: NHL volatility on a single-sport slate where every ticket was NHL-heavy, not one bad reused leg.
No model change tonight: the NHL trim the user pre-approved (Oct 27) needs a rebuild backtest that also checks payouts; flagged for the 10:30 AM review. v1 stays live; v2 not switched.

## 2026-11-04 10:30 AM ET intraday review
Status: v1 live; first games 7:00 PM ET (3 CFB, 14 NBA, 4 NHL). Graded: nothing new since 3 AM (ladder 59-189, Best 1-9, Lottery 7-151, green 21-24).
Research (~10:40 AM ET): NBA report: IND without Haliburton/Zubac/McConnell/Toppin; MIN without Edwards/DiVincenzo; OKC without Holmgren/J. Williams/Caruso; Tatum (rest) and Jalen Johnson questionable. Daily Faceoff 0 of 8 confirmed; Ersson (OTT, .866) and Wolf (CGY, .862) projected.
Change (backup /workspace/kfsp_backups/2026-11-04-am/): news_adj today -2.5 pts on IND, MIN, OKC, OTT, CGY side legs; 17 out players excluded from props. No model change; NHL trim still needs a payout-aware rebuild backtest (not run this window). v2 stays off.
Published after rebuild (site refresh 15:40 UTC = 10:40 AM ET).

## 2026-11-04 3:00 PM ET intraday review
Status: v1 live; no ladder locked (first games 7:00 PM ET). Graded: nothing new since 3 AM (ladder 59-189, Best 1-9, Lottery 7-151, green 21-24).
Research (~3:05 PM ET): VSiN 2:15 PM report: Tatum ruled out (rest), Pritchard and Jalen Johnson questionable; Tobias Harris, Nurkic, Mark Williams, Cason Wallace out. Daily Faceoff 3 of 8: Ersson confirmed (OTT), Askarov confirmed (SJ, .944 last 5) vs Kuemper likely (LAK, .877); Markstrom confirmed (FLA); Wolf unconfirmed.
Change (backup /workspace/kfsp_backups/2026-11-04-pm/): news_adj -2.5 pts on BOS and LAK side legs; 5 more out players excluded from props. No model change (no new backtest evidence); v2 stays off.

## 2026-11-05 (daily review #10, ~3:00 AM ET)
Record (all graded tickets): 76 won, 378 lost (16.7%) vs 90.3 expected. Ladder 64-205, Best 1-10, Lottery 11-163, green 23-26. 11-04: 9 of 38 (best day since 11-02 for Lottery: 4 hits).
Calibration (1,398 legs): 85-90% 87.2% vs 87.3% (594), 80-85% 82.4% vs 82.6%; 90-95% still 78% vs 93% (59, mostly 10-25/26). NHL 60.7% vs 66.4% (262) remains the most overconfident sport; NBA 76.7% vs 79.9%; spreads 73.0% vs 75.9%; props 26.3% vs 28.1%.
No model change tonight: tickets still trail expectation mainly through NHL legs; the NHL trim needs the payout-aware rebuild backtest, flagged again for the 10:30 AM review. v1 stays live; v2 not switched.

## 2026-11-05 10:30 AM ET intraday review
Status: v1 live; no ladder locked (first games 7:00 PM ET: 11 NHL, 2 CFB, JAX at BAL TNF, 2 NBA). Graded: nothing new since 3 AM (ladder 64-205, Best 1-10, Lottery 11-163, green 23-26).
Research (~10:45 AM ET): NFL: Lamar Jackson and Tyler Huntley OUT for BAL (JAX -10). NBA 9:30 AM report: ORL without Banchero, Suggs, Isaac; GSW without Butler, Moody, Porzingis; PHX without Mark Williams. Daily Faceoff 0 of 22 confirmed: Soderblom (CHI, .829), Bussi (CAR, .865), Dostal (ANA, .871) projected; Tarasov likely DET, Varlamov likely NYI, Skinner likely WPG.
Change (backup /workspace/kfsp_backups/2026-11-05-am/): news_adj -2.5 pts on BAL, ORL, CHI, CAR, ANA side legs; 13 out players excluded from props/TD. No model change; NHL trim payout-aware backtest not run this window. v2 stays off. Rebuilt and published.

## 2026-11-05 3:00 PM ET intraday review
Status: v1 live; no ladder locked yet (first puck drops 7:00 PM ET). Graded: nothing new since 3 AM / 10:30 AM (no games finished; ladder 64-205, Best 1-10, Lottery 11-163, green 23-26).
Research (~3:05–3:10 PM ET):
- NHL Daily Faceoff 10/22 confirmed: Soderblom Likely CHI (.829); Brossoit Likely ANA (.848, swapped from morning Dostal); Tomkins Likely EDM (Oilers site + DFO; Jarry sits); Binnington Confirmed STL (.846); Dobes Confirmed MTL (.853); Woll/Garand/Varlamov/Silovs/DeSmith/Talbot/Skinner/Blackwood confirmed. CAR: Bussi Unconfirmed (MatchWiz leans Kochetkov ~75%) — removed morning CAR penalty. CHI on B2B; Kane OUT.
- NBA 2:30 PM official report: ORL still without Banchero/Suggs/Isaac/Penda/Nelson; GSW without Butler/Moody/Porzingis/Santos; PHX/MIA not yet submitted. Giannis (wrist) DTD / rest risk on B2B after 41 OT minutes vs LAC. PHX: Mark Williams OUT; Goodwin and Fleming DTD.
- NFL TNF: Lamar + Huntley OUT; rookie Joe Fagnano starts. JAX -10 / total 39.5 (open BAL -4.5 / ~49.5). Our Unders 53.5/54.5 keep large cushion. Tuten, Walker, Wiggins Q.
- Weather: BAL cloudy 66F; FAU mostly clear 78F; JMU partly cloudy 65F — no weather haircut.
Change (backup /workspace/kfsp_backups/2026-11-05-pm/): legs.json news_adj today only, same -2.5 pt side/ML rule.
- Kept: BAL, ORL, CHI, ANA (reason updated to Brossoit).
- Added: EDM (Tomkins), STL (Binnington), MTL (Dobes), MIA (Giannis rest risk).
- Removed: CAR (weak-backup premise no longer clear).
- Players list expanded for props/TD exclusion (Giannis, Gardner, Goodwin, Fleming, Horford, Bassey, Brandon Williams, Kane, Poitras, Hall, Tuten, Walker, Wiggins, etc.).
No model change (no new backtest evidence; NHL trim payout-aware backtest still pending). v2 switch_ready still true, not re-reported. Locked tickets: none. Cleared stale .update.lock from 2:59 PM refresh, rebuilt via update.sh.
Published 2a4b5c4 (~3:10 PM ET). Site 200; servers 8080/8000 up. Counts: 16 ladder (33 unique legs), props 15, live 0, NBA 4, TD 2, 2-leg 0.

## 2026-11-06 daily review #11, ~3:00 AM ET
Record (all graded tickets): 86 won, 396 lost (17.8%) vs 97.6 expected. Ladder 69-216 (24.2%), Best Parlay 2-10 (first win since 10-30; 11-05 Best cashed at 4.47x), Lottery 15-170 (8.1%), green favorites 25-27 (48.1%), 2-leg board 0-0. 11-05: 10-18 (35.7%) — ladder 5/16 vs 5.02 expected (well calibrated day), Lottery 4-7, Best 1-0.
Calibration (1,472 main legs): Brier .146; 85-90% bucket 87.4% vs 87.3% (612), 80-85% 82.0% vs 82.5%; 90-95% still 78% vs 93.4% (59, legacy 10-25/26). by_sport: NHL 180/300 = 60.0% vs 66.4% pred (most overconfident on the main board); NBA 441/574 = 76.8% vs 79.8%; CFB 198/236 = 83.9% vs 82.2%; NFL 94/123 = 76.4% vs 74.2%. Shadow (4,015 graded): v1 Brier .1516 / top-pick 84.9% (309/364); v2 Brier .1500 / top-pick 87.1% (317/364). NHL top-pick shadow 73.2% v1 vs 82.9% v2. CLV ~flat (+0.06 pts). v1 stays live (Nov 3 ticket backtest still the deciding reject for switching; live_model/allow_switch untouched).
11-05 ladder losses: NHL short favorites reused across tickets — STL-NJ Under 8.5 (-750), PIT +2.5 (-650) / +1.5 (-330), DAL-CBJ and VGK-DET Over 3.5 (-750/-800); plus JMU-USM Under 76.5 (-900) and Desmond Bane 2+ assists (-900). Lottery longshot -1.5 puck lines also missed (DAL/UTA/PIT/NYR). No grading bug; no missed news that would have flipped a locked leg. Root cause is NHL variance on short-odds legs that still lose ~20-25% (main NHL odds <=-800: 31/41 = 75.6%).
NHL trim payout-aware rebuild backtest (PRIORITY, 12 graded shadow days 10-25..11-05; ladder/Best rebuilt per day; win rate + avg payout + ROI):
- baseline (current NHL_CAP=0.80 on 0.85+ legs): ladder 1-4 34/48 (70.8%, 1.30x, ROI -0.10); 5+ 41/215 (19.1%, 10.30x, ROI +0.16); top-pick 83.5%.
- no_trim: 5+ 36/215 (16.7%, ROI -0.10) -> current trim CONFIRMED better than removing it.
- stronger cap 0.75 / 0.70 / exclude 0.85+: 5+ 44/215 (20.5%, ROI +0.21). Leave-one-day-out and exclude-10-25/26 checks: gain is entirely from 10-25 (+2) and 10-26 (+1); after those early days, identical to baseline (23/180). NHL 0.85+ shadow sample still only 7 legs. REJECTED as overfit.
- across-the-board NHL -5 pts haircut: 5+ 33/215, ROI -0.41 -> REJECTED.
- drop NHL odds <=-500: 5+ 26/215, ROI -0.45 -> REJECTED (hurts payouts and absolute wins).
- drop NHL odds <=-700: 5+ 41/215 same wins, ROI slightly worse -> REJECTED.
- max 2 NHL legs per ladder ticket: higher win *rate* (22%) but fewer absolute wins (38/173) because NHL-heavy days truncate the ladder; leave-one-day-out always behind on wins -> REJECTED.
- NHL ranking penalty -0.03: +1 win but ROI +0.08 vs +0.16 -> REJECTED (payouts).
Changes: none to the model. Cleared legs.json news_adj (was dated 2026-11-05; 11-05 games finished). v1 stays live; v2 not switched. FanDuel links / King's Favorites / no-live pregame / update.sh preserved.

## 2026-11-06 10:45 AM ET intraday review (10:30 AM ET)
Status: v1 live; no ladder locked (first kickoffs soccer ~2:30 PM ET; NBA/NHL/CFB from 7:00 PM ET). Graded: nothing new since ~3 AM daily review (no game finished today yet). Record unchanged: ladder 69-216, Best 2-10, Lottery 15-170, green 25-27, 2-leg 0-0.
Research (~10:45 AM ET):
- NBA official 9:30 AM / VSiN 10:15 AM: MIN without Edwards (knee arthroscopy, multi-month) and DiVincenzo; Shannon Jr. Q. TOR: Barnes Q, Kawhi out. WAS: Anthony Davis Q (ankle). ATL: Jalen Johnson Q. OKC: Holmgren, Jalen Williams, Wallace, Jaylin Williams, Topic, Sorber out. SAC: Murray, Raynaud, Simmons out. CLE: Allen Q, Watson Q. POR: Morant/Sharpe/Krejci out (favors our LAL cushions). UTA: Jaren Jackson Jr. and Nurkic out (favors DAL). Embiid available for PHI@CLE; market flipped PHI -148 / CLE +124.
- NHL Daily Faceoff 0/6 confirmed: Greaves (.882) at BUF (Luukkonen Likely); Askarov vs Wallstedt; Dostal (.871) at Wolf.
- Soccer (first kickoffs): Everton without Grealish; Branthwaite expected; Coventry missing Amenda/Wright/Eccles/Woolfenden. Rain ~76% at Everton (supports our Under 4.5).
- CFB weather: VT-SMU 68F partly cloudy; USF-ECU showers 68F; NEB-ILL 40F clear; UNM-NEV 53F; TCU-ARI 63F cloudy — no weather haircut beyond research.
- Line moves: PHI/CLE flipped; SA -970→-1180; SMU -278→-225; Wild +1.5 -800→-700.
Change (backup /workspace/kfsp_backups/2026-11-06-am/): legs.json news_adj today only, same -2.5 pt side/ML rule on MIN, TOR, WAS, ATL, OKC, SAC, CLE, CBJ (Greaves), ANA (Dostal). 37 out/Q players excluded from props/TD. Effect: weakens Best/Lottery MIN +4.5 and TOR +1.5 exposure; deep cushions (WAS +23.5, MEM +19.5, LAL +13.5) stay; OKC +6.5 deprioritized.
No model change (overnight NHL trim payout-aware backtest already rejected stronger caps as overfit on 10-25/26; no new graded evidence this morning). v2 switch_ready still true, not re-reported. Locked tickets: none.

## 2026-11-06 3:00 PM ET intraday review
Status: v1 live (live_model/allow_switch untouched). Ladder: 16 of 23 already locked at first soccer kickoffs (~2:45–3:00 PM ET: Everton, Alavés-Sevilla, Udinese-Venezia, Strasbourg-Toulouse, Gladbach-Hamburg); unlocked: ladder 1–5, 7, 10 plus Best Parlay and unlocked Lottery tickets. None unlocked.
Graded: nothing finished since 10:45 AM / 3 AM (soccer still live early 0-0 / HSV 1-0 BMG at ~39'; no NBA/NHL/CFB tip yet). Record unchanged: ladder 69-216, Best 2-10, Lottery 15-170, green 25-27, 2-leg 0-0.
Research (~3:05–3:15 PM ET):
- NBA official 2:30 PM ET: Shannon Jr. upgraded Out (MIN); Quickley Q (hamstring) and Kyle Anderson Q (illness) NEW for TOR (Barnes still Q, Kawhi out); Diabate and Schroder Out for CHA (Knueppel/Grant Williams already out — favors our BOS cushions); AD / Jalen Johnson / Allen still Q; Embiid available PHI@CLE; Mamukelashvili Q (LAL); Pritchard Available (BOS).
- NHL Daily Faceoff 5/6 confirmed: Greaves CONFIRMED CBJ (.882); Luukkonen CONFIRMED BUF (.873 / 3.40); Askarov CONFIRMED SJ vs Wallstedt CONFIRMED MIN; Dostal still Unconfirmed ANA (.871), Wolf Confirmed CGY.
- Soccer live: EVE-COV 0-0, SEV-ALA 0-0, VEN-UDI 0-0, TOU-STR 0-0, HSV 1-0 BMG — Unders / DCs still live; no finished legs to grade.
- CFB weather: TCU@ARI clear ~64F / 4% rain at kick (afternoon storm window ends before tip) — no weather haircut. VT-SMU / USF-ECU / NEB-ILL / UNM-NEV unchanged vs morning.
- Line moves on board: SMU -278→-225; ARI -375→-285; NEB -218→-192; others mild.
Change (backup /workspace/kfsp_backups/2026-11-06-pm/): legs.json news_adj today only, same -2.5 pt side/ML rule.
- Kept: MIN, TOR, WAS, ATL, OKC, SAC, CLE, CBJ (Greaves now Confirmed), ANA (Dostal still Unconfirmed).
- Added: BUF (Luukkonen confirmed return with poor season form .873 / 3.40) — deprioritizes unlocked Lottery BUF -1.5 longshots; unlocked ladder tickets 1–5/7/10 have no BUF legs.
- Reasons updated for afternoon designations. Players list 39 (added Quickley, Kyle Anderson, Mamukelashvili; Bona/Schroder/Diabate/Knueppel already present). Effect on unlocked tickets: TOR +11.5 / MIN +12.5 already mostly on locked tickets; ATL +7.5 on unlocked #10 stays haircut; Best Parlay (LAL +6.5, Under 240.5 WAS-ATL, DAL +1.5, PHI +6.5, Under 241.5 TOR-MIL) re-priced with CLE/TOR/WAS haircuts on side legs only.
No model change (no new graded losses today; overnight NHL trim payout-aware backtest already rejected stronger caps). Cleared stale .update.lock from ~3:05 PM refresh before rebuild. Locked tickets preserved.
Published 3dfd6ba / 79e4864 (~3:10–3:11 PM ET). Site 200; servers 8080/8000 up. Counts: 23 ladder (68 unique legs; 16 locked / 7 unlocked), props 15, live 4, NBA 15, TD 0, 2-leg 0, Lottery 8. Best Parlay ~22.6% / 4.33x (LAL +5.5, Under 240.5 WAS-ATL, DAL +1.5, PHI +6.5, Under 241.5 TOR-MIL).

## 2026-11-07 daily review #12, ~3:10 AM ET
Record (all graded tickets through 11-06): 88 won, 420 lost (17.3%) vs 101.8 expected. Ladder 70-236 (22.9%), Best Parlay 2-10, Lottery 16-174 (8.4%), green favorites 25-28 (47.2%), 2-leg board 0-0. 11-06 graded so far: ladder 1/21 vs 3.7 expected (several late CFB / Sunday soccer / NHL tickets still pending including Best Parlay and greens 2-3). Main legs 1,545 graded: 1,142/1,545 = 73.9% hit vs 75.5% pred (Brier .1456). 11-06 legs alone 56/68 = 82.4% vs 86.2%.
Calibration (stats.json): 85-90% 87.0% vs 87.3% (667), 80-85% 81.9% vs 82.5%; 90-95% still 78.3% overall but 6/6 = 100% post-10-27 (legacy 10-25/26 only). by_sport: NHL 183/304 = 60.2% vs 66.6% pred (still most overconfident); NBA 471/612 = 77.0% vs 80.3%; CFB 215/256 = 84.0% vs 82.5%; NFL 94/123 = 76.4% vs 74.2%. CLV ~flat (+0.04 pts; 402 beat / 460 worse).
Extra tabs: Live 4,913/8,013 = 61.3% vs 62.4%; Props 2,560/3,456 = 74.1% vs 76.4% (post-11-02 FD-cap era 74.1% vs 75.1% — nearly calibrated); NBA 3s/reb 883/1,212 = 72.9% vs 73.7%; NFL TD 61/142 = 43.0% vs 40.6%.
Shadow (4,280 graded): v1 Brier .1498 / top-pick 391/470 = 83.2%; v2 Brier .1483 / top-pick 404/470 = 86.0%. NHL top-pick 68/95 = 71.6% v1 vs 79/95 = 83.2% v2. v1 stays live (ticket rebuild still worse for v2; live_model/allow_switch untouched).
11-06 ladder losses (root causes): Calgary Flames +1.5 (est .83) sat on 14 losing tickets — same reuse pattern as prior days; NHL +1.5 overall is calibrated (56/69 = 81.2% vs 79.7%), so this was variance amplified by reuse. Also PHI +11.5/+12.5/+13.5 and MEM +18.5/+19.5 (NBA blowouts), WAS-ATL Unders 248.5-250.5, VT-SMU Unders 74.5/75.5, Nevada +26.5. No grading bug; no missed news that would have flipped a locked leg. CFB Unders overall calibrated (133/151 = 88.1% vs 87.1%).
Payout-aware rebuild backtests (13 graded shadow days 10-25..11-06; ladder/Best rebuilt per day; win rate + avg payout + ROI):
- baseline (NHL_CAP=0.80): ladder 1-4 37/52 (71.2%, 1.30x, ROI -0.10); 5+ 45/233 (19.3%, 10.01x, ROI +0.13); top-pick 83.4%.
- no_trim: 5+ 40/233 (ROI -0.12) -> current trim still confirmed.
- cap75: 5+ 48/233 (ROI +0.17) but post-10-26 Δ = 0 (all gain on 10-25/26) -> REJECTED as overfit (same as 11-06).
- NHL -3 pts ranking haircut: 5+ same wins, ROI +0.03 vs +0.13 -> REJECTED (payouts).
- NHL +1.5 short-odds haircut (Calgary-style): +1 win total, helped 11-06 / hurt 11-05 -> noise, REJECTED.
- NBA underdog spreads 5-10 haircut/drop (main-board 72% vs 86% pred, n=72): 5+ 44/233, post-10-26 Δ = -4 -> REJECTED.
- NBA Unders -3/-5/-8 pts: win count flat-to-+2 but ROI +0.13 -> +0.06/+0.08/+0.09 -> REJECTED (trades payouts for short-odds safety; user rule).
- Leg-reuse cap 3/5: fewer absolute wins, worse ROI -> REJECTED (again).
- v2 live: top-pick 85.7% vs 83.4%, but 1-4 35/52, 5+ 37/232 (ROI -0.34) -> REJECTED for switch; recommend only.
Changes: cleared legs.json news_adj (was dated 2026-11-06; 11-06 games finished / pending tickets already locked). No model change. v1 stays live; v2 not switched. FanDuel links / King's Favorites / no-live pregame / update.sh preserved. Backups /workspace/kfsp_backups/2026-11-07/. Backtest detail /workspace/kfsp_review/r1107/bt.json.

## 2026-11-07 10:40 AM ET intraday review (10:30 AM ET)
Status: v1 live (live_model/allow_switch untouched). Ladder: 10 of 25 locked at early soccer kickoffs (7:30–10:00 AM ET: #11, 12, 13, 16, 18, 19, 20, 22, 23, 24); the rest (first kicks noon ET+) and Best Parlay / unlocked Lottery still follow the board. None unlocked.
Graded since 3 AM: one late 11-06 ladder ticket graded a win (~9:38 AM ET refresh). Record: ladder 71-236, Best 2-10, Lottery 16-174, green 25-28, 2-leg 0-0. No 11-07 game finished yet, so no new losing-leg pattern to study; no model change.
Research (~10:35 AM ET):
- NBA report 9:15 AM ET: IND without Haliburton/Furphy/Sheppard, Oubre + McConnell Q (helps our DEN legs; DEN-IND in Mexico City). GSW: Butler, Porzingis, Moody out; Draymond, Santos, Payton II Q. ORL: Banchero, Suggs, Isaac, Penda, Nelson out. NYK: Josh Hart out; CLE: Allen/Tyson/Merrill out. PHX: Mark Williams out. WAS@OKC, SAS@POR clean.
- NHL Daily Faceoff (3/24 confirmed): Thompson vs Schmid confirmed (FLA-WSH); TOR Bobrovsky likely (.889) vs MTL Fowler (.923) — supports Best MTL +1.5 (now off Best); MIN Pickard confirmed (.833, back-to-back) — supports Lottery TB legs; STL-NSH unconfirmed (Hofer/Saros).
- CFB: Wake Forest holding QB Gio Lopez (Pizzella starts vs Merrimack, Thamel 10:08 AM ET); Boise State QB Madsen out (Cutforth); Oregon without QB Moore + RB Davison at OSU; Northwestern QB Chiles out (helps Iowa +13.5 / Under); KSU 4th-string QB, Rutgers Lonergan + Wisconsin Joseph out, Syracuse Angeli Q (all support our Unders).
Change (backup /workspace/kfsp_backups/2026-11-07-am/): legs.json news_adj today only, same -2.5 pt side rule on Wake Forest, Boise State, Oregon, Golden State, NY Knicks; 38 out/Q players excluded from props/TD.
Effect: Wake Forest -31.5 and Boise State ML dropped from unlocked tickets; GSW +3.5 dropped from Best Parlay. New Best ~27.2% / 4.40x: Michigan State +21.5, NSH +1.5, DEN +1.5, SAS +3.5, Under 78.5. Locked #16 (GSW +8.5, Oregon +26.5) and #20 (Boise State ML) keep their legs as shown.
Published 66a73d06 (~10:35 AM ET). Site 200. v2 switch_ready still true, not re-reported.

## 2026-11-07 3:00 PM ET intraday review (~3:05–3:12 PM ET)
Status: v1 live (live_model/allow_switch untouched). Ladder: all 25 tickets locked (first kickoffs before 3 PM ET); none unlocked. Best Parlay and unlocked Lottery tickets still follow the board.
Graded since 10:40 AM: 5 ladder losses (#11, 18, 19, 20, 24), all early soccer: Over 1.5 Goals Frosinone@Cagliari (final 0-1, on #11/18/24), Over 1.5 Hull@Arsenal (0-1, #18), Man City And Draw at Nottingham Forest (1-3, #19/20). Record: ladder 71-241, Best 2-10, Lottery 16-174, green 25-28, 2-leg 0-0.
Pattern check: soccer Over 1.5 overall 49/58 = 84.5% hit vs 81.5% predicted, soccer DC 45/56 = 80.4% vs 78.7% -> calibrated; today's misses were 1-0 / upset variance, amplified by leg reuse. No model change.
BUG FOUND + FIXED (clear evidence): side_of() in build.py and extra.py returned 'home' whenever a runner name shared any token with the home team. Because 'state' is a stopword, "Michigan State" matched home "Michigan"; shared "Los Angeles"/"New" did the same for Lakers@Clippers (10-28), Chargers@Rams (10-31/11-01), Red Bulls@New England (10-28) and would have for NJ Devils@NY Islanders tonight. Those legs were priced and graded as the wrong team. Fix: score token overlap for both sides, tie-break by full-name similarity (tested: Michigan State/Michigan, New Jersey/New York, Boise State/Colorado State).
Regrade (backup /workspace/kfsp_backups/2026-11-07-pm/): history legs re-sided and regraded from finals — Lakers +1.5/+15.5/-9.5 loss->win (Lakers won 103-87), Chargers -2.5/+13.5 win->loss (lost 9-24), Red Bulls ML win->loss (2-3). No ticket result changed (each affected ticket had another decisive leg), so the record is unchanged. 4 locked ladder legs on Michigan State re-sided so tonight's grading uses MSU (picks/links unchanged; not unlocked).
Effect on board: Michigan State +3.5 (+300) was being rated ~57% (really ~25%) and sat on all 7 Lottery tickets; it is gone. MSU +21.5 left the Best Parlay; MSU +30.5 now 83% (was 94%).
Research (~3:05 PM ET): MSU 13 out (top 3 RBs, backup QB Fancher, TE Savoury), QB Milivojevic questionable (final report 5:30 PM ET), 6-game skid. NHL: TB starts backup Hildeby at MIN (Pickard for MIN); OTT Ersson (Ullmark out) vs UTA; MTL Fowler / TOR Bobrovsky; NJD Allen / NYI Sorokin; COL Blackwood; DAL Oettinger. NBA 12:45 PM report: HOU without Capela/Adams, PHX without M. Williams, Goodwin doubtful; SAS Harris DTD/Quaintance out, on a back-to-back at POR (Morant, Sharpe, Krejci out); GSW/NYK/ORL unchanged. CFB: WVU 3rd-string QB Hughley out (no top change), TTU WRs Jones/Simmons out; Hawaii QB Alejado cleared. Weather: Fort Collins 60F, Lubbock 52F partly cloudy, Ann Arbor 41F clear -> no weather haircut. Lines: LSU -180->-225, Ohio State -238->-305, Navy -310->-270.
news_adj added: Michigan State -2.5, Tampa Bay -2.5 (backup goalie); 17 players added to props/TD exclusion (55 total).
New Best Parlay ~21.7% / 4.42x: Under 76.5 WVU-TTU, Hawaii ML, Over 59.5 Boise-CSU, HOU +1.5, SAS +3.5.
Published 48b46ef0 (~3:10 PM ET). v2 switch_ready still true, not re-reported.

## 2026-11-08 daily review #13, ~3:00 AM ET
Record (all graded tickets through 11-07): 95 won, 451 lost (17.4%). Ladder 77-258 (23.0%), Best Parlay 2-11, Lottery 16-182 (8.1%), green favorites 25-34 (42.4%), 2-leg board 0-0. 11-07: 5-20 overall. Main legs 1,788 graded: 74.6% hit vs 76.3% pred (Brier .1457, log loss .465). 11-07 legs 168/201 = 83.6% vs 85.5%.
Calibration: 85-90% 86.1% vs 87.3% (818); 80-85% 82.8% vs 82.6%; 90-95% 79.0% vs 93.3% (62, mostly legacy 10-25/26). By sport: NHL 61.3% vs 67.1% (326, still most overconfident); NBA 77.6% vs 80.5%; CFB 80.5% vs 82.1%; NFL 74.8% vs 74.2%. Odds bands: <=-800 86.8% vs 87.6% (999); -300..-150 56.4% vs 66.9% (78, small).
Extra tabs: Live 61.7% vs 62.4% (11,172); Props 74.4% vs 76.3% (3,765); NBA 3s/reb 73.3% vs 73.7% (1,294); NFL TD 43.0% vs 40.6% (142). All close to calibrated; FanDuel's own price is about as good as the model on Live/Props.
Shadow (5,240 graded): v1 Brier .1539 / top-pick 84.7% (489); v2 Brier .1530 / top-pick 86.9%. v2 still better per leg and top pick, but rebuilt v2 tickets lose: ladder 1-4 36/56 vs 39/56, 5+ 40/261 (ROI -0.33) vs 46/261 (ROI +0.00). Recommend only; v1 stays live (live_model/allow_switch untouched).
11-07 losses (root cause): CFB scoring explosion. Deep alt Unders at -800..-1000 lost on Boise-CSU (102 pts vs Under 87.5-89.5), OKST-KSU (94 vs 83.5/84.5), WKU-MTSU (93 vs 71.5/72.5), WVU-TTU, Wyoming-UNLV, Tulsa-Tulane, ISU-Baylor, Temple-Navy, Oregon-OSU (69 vs 60.5/61.5); also Merrimack +63.5 (lost 0-77), Kentucky +23.5 (6-34), ORL-GSW Unders 241.5-243.5, early soccer Over 1.5s / Man City DC, NHL Under 8.5s and LA Kings +1.5. CFB Unders 63/82 on 11-07 vs 87.6% rated. Finals verified against ESPN: no grading bug, no missed news that would have flipped a locked leg.
Diagnosis: CFB total Unders priced -900 or shorter hit 183/216 = 84.7% vs 87.9% rated (85.5% before 11-07), so the model was overrating them by ~3 pts even before yesterday; -899..-700 band 78.2% vs 85.7% but those rarely make tickets.
Payout-aware rebuild backtest (14 graded shadow days 10-25..11-07; /workspace/kfsp_review/r1108/bt.json, bt2.json):
- baseline: ladder 1-4 39/56 (1.30x, ROI -0.13); 5+ 46/261 (10.10x, ROI +0.00); top-pick 83.7%.
- CFB deep Under (-900 or shorter) -2/-3/-4 pts: 1-4 41/56; 5+ 51/52/50 of 261 (ROI +0.16/+0.19/+0.14), avg payout unchanged (10.13x); with 11-07 excluded still +5/+4/+3 wins; up on 5 days, down on 2. ADOPTED -3 pts.
- all CFB Unders -3/-5, cap at 0.85, drop entirely, mid-band -4, blend with Pinnacle: all weaker or flat -> rejected.
- no NHL trim: 5+ 41/261 (ROI -0.22) -> NHL trim confirmed again.
Changes (backup /workspace/kfsp_backups/2026-11-08/): build.py CFB_DEEP_UNDER_HC=0.03 applied to CFB total Unders at -900 or shorter (after NHL trim, before v2 shadow, so future shadow v1 includes it). Cleared stale legs.json news_adj (dated 11-07). v1 stays live; FanDuel links / King's Favorites / no-live pregame / update.sh preserved.
Expected effect: deep CFB alt Unders rank a bit lower, so ladder/Best/Lottery lean on better-calibrated legs; backtest suggests roughly +1 to +2 ladder wins per CFB-heavy Saturday. Small sample, nothing guaranteed.

## 2026-11-08 10:30 AM ET intraday review
Status: v1 live (live_model/allow_switch untouched). Ladder tickets 5–25 are locked (early soccer kickoffs); tickets 1–4, Best Parlay, and Lottery still follow the board. None unlocked. 11-07 Best Parlay remains pending (includes DET ML at MIA today).
Graded since 3 AM: no new ticket results. Finished soccer so far: Lazio at Napoli 1-1 FT (6:30 AM ET) — locked Over 1.5 on tickets 10/14/17/20/23/25 already marked a win; Elche 0 Real Betis 2 FT (8:00 AM ET) — locked Over 1.5 on tickets 7/13/16/17/19/20/22/24/25 already marked a win. Several 9:00 AM ET leagues are still in progress (Brighton-Brentford 2-0 at 76', etc.). No new losing-leg pattern; soccer Over 1.5 hits today were the same calibrated market reviewed yesterday. No model change. CFB Under -3 haircut left in place (provisional).
Research (~10:40 AM ET):
- NFL injuries (ESPN): Shedeur Sanders starts at CLE; Deshaun Watson (concussion) Q and expected inactive after clearing protocol (Rapoport / Monken). Gardner Minshew is the confirmed ARI starter; Carson Beck is No. 2 (LaFleur / Rapoport). SEA QB Sam Darnold is out today (quad/ribs); Drew Lock expected to start (Schefter, updated this morning). Patriots WR A.J. Brown is listed on New England and is out (knee/ankle; Doug Kyed, Boston Herald) — historically a PHI name, but ESPN team assignment and the Patriots beat writer check out; PHI's DeVonta Smith is separately out (hamstring). Patriots RB TreVeyon Henderson is out (illness). Giants RB Cam Skattebo doubtful. Puka Nacua Active; Rams TE Parkinson and WR Whittington Q. GB DE Micah Parsons out (ACL). NYJ WR Garrett Wilson out. SF WRs Evans, Deebo, and Aiyuk out.
- Line: NYG@PHI flipped — Eagles opened -238 and are now +130 / NYG -3 (ESPN/DraftKings), matching FanDuel NYG -3, total 38.5. SEA shortened from -750 to -440 (still -8.5) after the Darnold news. CLE@NO remains NO -3 / 42.5.
- Weather (ESPN/AccuWeather on the scoreboard): SEA showers 57°F at Lumen; CHI mostly clear 53°F; NE mostly sunny 55°F; PHI mostly sunny 58°F; SF partly sunny 68°F; MIA 86°F; KC sunny 61°F; CAR sunny 65°F; WSH mostly sunny 59°F; SoFi mostly sunny 88°F. CLE@NO and DAL@IND indoor.
- NBA: Anthony Edwards out (knee surgery Thursday) for UTAH@MIN (line still MIN -11.5 — market has had three days). Luka Doncic (Lakers) questionable (back) at DET. Norman Powell (CHI) DTD/questionable (shoulder) but extra.py's roster field still said "none listed," so he was on the Props tab (15+ points, -340). Keegan Murray listed Out with a questionable comment vs MIA. Brandon Ingram out for LAC; Jalen Duren out for DET; Nic Claxton listed Out / comment Q for CHI. Embiid probable.
- NHL ESPN probable starters: FLA Markstrom vs BOS Swayman; VGK Carter Hart vs BUF Colten Ellis (Alex Lyon IR); TB Vasilevskiy vs WPG Stuart Skinner; NJ Connor Hellebuyck vs TOR Anthony Stolarz; PHI Dan Vladar vs CGY Dustin Wolf; PIT Arturs Silovs vs ANA Laurent Brossoit (Dostal not on the injury list).
Change (backup /workspace/kfsp_backups/2026-11-08-am/): legs.json news_adj today only — Anaheim Ducks -2.5 pts on side/ML (Brossoit probable starter); 20 out/Q/DTD players added to the exclusion list (Norman Powell plus effectively unavailable NFL/NBA names). Researched 2-leg board rewritten with re-verified FanDuel PA prices (A2 LV Under 68.5 -1000→-1100; C NYG Under 43.5 -245→-250; P1 McBride 5+ -650→-600; P2 White 1+ -1000→-950; P3 Nacua 60+ -500→-490 and McBride 40+ -380→-360). Notes corrected: A.J. Brown verified on NE; Minshew confirmed to start; Darnold out / Lock expected; Sanders starts rather than only "projected."
Effect: ANA +1.5 stayed on Best Parlay after the -2.5 pt haircut (79.16% -> 76.66%). New Best ~24.29% / 4.36x: Vegas Golden Knights +1.5, Anaheim Ducks +1.5, Dallas Mavericks +1.5, Under 250.5 (MIA@SAC), Under 238.5 (NOP@LAC). Previous fifth leg Under (59.5) LV@SF was replaced in the unlocked rebuild. Locked tickets untouched. No model/code change.
Published 3109a424 (~10:42 AM ET). Site 200. v2 switch_ready still true, not re-reported.

## 2026-11-09 daily review #14, ~3:05 AM ET
Record (all graded tickets through 11-08): 109 won, 488 lost (18.3%). Ladder 83-277 (23.1%), Best Parlay 3-12, Lottery 18-198 (8.3%), green favorites 28-36 (43.8%), researched 2-leg board 5-1. 11-08: 6-30 overall (ladder 6/25: tickets 1, 2, 3, 6, 11, 12 won). Main legs 1,944 graded: 75.2% hit vs 76.1% pred (Brier .1441, log loss .461). 11-08 legs 113/135 = 83.7% vs 78.5% pred (better than predicted).
Calibration: <=-800 86.9% vs 87.6% (1,065); -800..-500 82.0% vs 82.4%; -300..-150 58.8% vs 67.5% (85, small; rarely on tickets). By sport: NHL 63.5% vs 67.2% (351, still most overconfident but improving); NBA 78.0% vs 80.7%; CFB 80.5% vs 82.1%; NFL 73.7% vs 72.0%; soccer leagues mostly under-predicted. CLV flat (-0.01 pts; 483 beat / 579 worse).
Extra tabs: Live 61.8% vs 62.4% (11,673); Props 74.7% vs 76.3% (4,115); NBA 3s/reb 73.4% vs 73.7% (1,357); NFL TD 40.7% vs 40.6% (209). All near calibrated.
Shadow (5,670 graded): v1 Brier .1524 / top-pick 85.2% (539); v2 Brier .1517 / top-pick 87.4%. Rebuilt v2 tickets still lose: ladder 1-4 40/60 vs 45/60, 5+ 45/282 (ROI -0.23) vs 59/282 (ROI +0.28). Recommend only; v1 stays live.
11-08 losses (root cause): leg reuse on a few games that went wrong. Over 1.5 Goals Atalanta-Monza (on 7 tickets) and Rayo-Real Sociedad (on 6); NFL Unders HOU@LAC 55.5-56.5 and GB@NE 59.5-60.5 (-900..-1000); NOP +13.5/+14.5 and Unders 249.5/250.5 at LAC (NBA blowout); Lottery longshots PHI -1.5 / TB -1.5 puck lines and NFL plus-money spreads. Soccer Over 1.5 is actually under-predicted overall (69/82 = 84.1% vs 79.7%), NFL deep Unders calibrated (90.4% vs 89.4%), so these were variance concentrated by reuse, not a bad estimate. No grading bug found; no missed news that would have flipped a locked leg.
Watch list: NBA Unders 81.3% vs 87.3% (187) and NHL Unders 57.1% vs 70.5% (56) are overrated.
Payout-aware rebuild backtest (15 graded shadow days 10-25..11-08; /workspace/kfsp_review/r1109/bt.json):
- baseline (NHL trim + CFB deep Under -3): ladder 1-4 45/60 (1.30x, ROI -0.05); 5+ 59/282 (11.00x, ROI +0.28); top-pick 84.8%.
- no NHL trim: 5+ 50/282 (ROI +0.01) -> trim confirmed again.
- NBA Unders -2/-3 deep or -3 all: 1-4 43-44/60, 5+ 58/282, ROI +0.05 -> REJECTED (fewer wins, much lower ROI; same as 11-07).
- NHL Unders -5/-10: 1-4 46/60 (+1) but 5+ 54-55/282 (ROI +0.10/+0.11) -> REJECTED (net fewer wins).
- soccer Over 1.5 +2: 5+ 51/282 (ROI -0.21) -> REJECTED.
- combo NBA deep Under -3 + NHL Under -5: 1-4 45/60, 5+ 56/282 -> REJECTED.
- v2 live: REJECTED for switch.
Changes (backup /workspace/kfsp_backups/2026-11-09/): cleared stale legs.json news_adj (dated 11-08). No model change. v1 stays live (live_model/allow_switch untouched). FanDuel links / King's Favorites / no-live pregame / update.sh preserved.

## 2026-11-09 10:30 AM ET intraday review (~10:33–10:40 AM ET)
Status: v1 live (live_model/allow_switch untouched). Today's slate is all evening (first tip 7:00 PM ET), so none of the 12 ladder tickets has started; ladder, Best Parlay and Lottery still follow the board. Nothing unlocked.
Graded since 3 AM: no games finished (11-08 fully graded at 3 AM). Record unchanged: ladder 83-277, Best 3-12, Lottery 18-198, green 28-36, researched 2-leg 5-1. No new losing-leg pattern; no model change.
Research (~10:35 AM ET):
- NBA (ESPN injuries + team reports on X): Denver's whole starting five (Jokic elbow, Murray, Braun, Gordon, C. Johnson) plus DeRozan questionable after being stranded in Mexico City; line moved HOU -4.5 to -8.5, total 222.5 to 217.5. Toronto: Barnes and Quickley questionable, Kawhi Leonard and Bittle out. Lakers on a back-to-back, Luka sat Sunday, Monday report not filed yet. CLE Allen Q (Merrill/Tyson/Tomlin out); CHA without Miller, Knueppel, Schroder, G. Williams. WAS Anthony Davis Q. SAS Harris out, Vassell Q. IND Haliburton out, McConnell Q. DAL Lively out. GSW Butler/Porzingis/Moody/Richard out. HOU Capela/Adams out.
- NFL MNF BUF@MIN: Kyler Murray out, Carson Wentz starts; Jennings out; BUF Palmer out, Dawkins Q. FanDuel total 43.5 (lookahead 47.5). Indoors.
- NHL Daily Faceoff (0/6 confirmed): NYR Garand vs EDM Levi; PHI Woll likely vs VAN Lankinen (.804); NYI Sorokin vs SJS Askarov.
Change (backup /workspace/kfsp_backups/2026-11-09-am/): legs.json news_adj today only, -2.5 pts on Houston Rockets (Denver status unresolved; market already prices a shorthanded Denver) and Toronto Raptors (Barnes/Quickley Q); 20 Q/out players added to the props/TD exclusion list.
Effect: Toronto +5.5 left the Best Parlay; New Best ~22.3% / 4.33x: ATL +7.5, DAL +6.5, CLE-CHA Under 226.5, NOP-GSW Under 243.5, WAS-DET Under 229.5. Houston +7.5/+6.5 dropped from the top of the leg pool.
Researched 2-leg board rewritten for 11-09 (prices re-verified on FanDuel PA and MD event pages 15:36 UTC = 10:36 AM ET, all identical): A1 ATL +15.5 (-950) + BUF-MIN Under 59.5 (-1000) est. $1.22/$1, break-even 82.3%; A2 SAS +7.5 (-1000) + CLE +7.5 (-950) $1.22, 82.3%; A3 GSW +6.5 (-900) + DAL +12.5 (-900) $1.23, 81.0%; B ATL +10.5 (-400) + SAS +3.5 (-480) $1.51, 66.2%. Strict 2-leg board: no pair qualifies today (no leg reaches the 0.92 calibrated bar; best near miss MNF Under 59.5 at 0.887). Not strict-qualified; no edge over FanDuel demonstrated.

## 2026-11-09 3:00 PM ET intraday review (~3:06–3:12 PM ET)
Status: v1 live (live_model/allow_switch untouched). All of today's games start 7:00 PM ET or later, so no ladder ticket has locked; nothing unlocked.
Graded since 10:30 AM: no games finished. Record unchanged: ladder 83-277, Best 3-12, Lottery 18-198, green 28-36, researched 2-leg 5-1. No new losing-leg pattern; no model change (no backtest-proven fix pending).
Research (~3:05 PM ET):
- Denver: Jokic, Murray, Gordon, C. Johnson, Braun and DeRozan all upgraded to probable (ESPN, ~2:20 PM ET). FanDuel repriced fast: Houston ML -344 -> -182.
- Lakers: Luka Doncic off the injury report, expected to play (Dave McMenamin / NY Post 2:30 PM ET); Austin Reaves questionable (illness), Quentin Grimes out. Hawks ML only moved -125 -> -120.
- Other NBA: SAS Vassell now out; DET Isaiah Joe out; DAL Morez Johnson Q; GSW Payton II Q, Will Richard out; TOR Murray-Boyles Q (illness), Barnes/Quickley still Q; WAS Coulibaly Q, Davis Q; HOU Tshiebwe out; CHA Diabate doubtful.
- NHL (Daily Faceoff): Garand vs Levi confirmed; PHI Woll likely on a back-to-back vs VAN Merilainen; Sorokin likely vs Askarov (SJS third game in four nights).
- MNF: no change (Wentz starts; Murray, Jennings, Claiborne out; BUF Palmer out, Dawkins Q). Indoors.
Changes (backup /workspace/kfsp_backups/2026-11-09-pm/): removed the Houston -2.5 news_adj (Denver uncertainty resolved and already priced, so keeping it would double-count); kept Toronto -2.5 with updated reason. Props/TD exclusion list: removed Luka and the six Denver probables; added Reaves, Isaiah Joe, Morez Johnson Jr., Payton II, Murray-Boyles, Coulibaly, Tshiebwe, Will Richard, Landale, Goodwin (23 total). Researched 2-leg notes updated (Luka plays; Vassell out); no pair changed.
Effect: New Best ~22.0% / 4.39x: ATL +6.5, IND-DAL Over 214.5, CLE-CHA Under 226.5, HOU +4.5, WAS-DET Over 207.5 (DAL +5.5 and MEM-TOR Under 239.5 left). Published aed4cede (~3:08 PM ET), site 200. v2 switch_ready still true, not re-reported.

## 2026-11-10 daily review #15, ~3:00 AM ET
Record (all graded tickets through 11-09): 125 won, 502 lost (19.9%). Ladder 92-280 (24.7%), Best Parlay 3-13, Lottery 25-208 (10.7%), green favorites 30-38 (44.1%), researched 2-leg board 5-1. 11-09 was the best day yet: 16-14 overall; ladder 9 of 12 (tickets 1, 2, 4, 5, 6, 7, 9, 10, 12 won), Lottery 7 of 16 (2-, 3-, 4-, 5-, 6-, 8- and 9-leg best-chance tickets won). Main legs 2,007 graded: 75.0% hit vs 75.7% pred (Brier .1430, log loss .459).
Calibration: <=-800 87.2% vs 87.6% (1,094); -800..-500 82.3% vs 82.4%; 85-90% bucket 86.4% vs 87.3% (904). By sport: NHL 63.5% vs 67.1% (364, still most overconfident); NBA 77.6% vs 79.7%; CFB 80.5% vs 82.1%; NFL 74.3% vs 71.7%. Extra tabs: Live 61.8% vs 62.4% (11,807); Props 74.9% vs 76.3% (4,322); NBA 3s/reb 74.0% vs 73.7% (1,434); NFL TD 40.0% vs 40.6% (215). All near calibrated; FanDuel's own price still about as good as the model on Live/Props.
Shadow (5,870 graded): v1 Brier .1525 / top-pick 85.3% (551); v2 Brier .1520 / top-pick 87.1%. Rebuilt v2 tickets still lose badly: ladder 1-4 42/64 vs 48/64, 5+ 45/290 (ROI -0.25) vs 61/290 (ROI +0.26). Recommend only; v1 stays live.
11-09 losses (root cause, finals verified on ESPN): Cleveland +7.5 at Charlotte (-900, rated 88.9%) lost 112-124 to a short-handed Hornets team (Miller, Knueppel, Schroder, G. Williams out); it sank ladder 3, 8, 11 and Lottery 10-, 11-, 12-leg best-chance tickets. Upset variance, priced correctly by the market (-900), concentrated by reuse on 6 tickets. Best Parlay lost on two NHL Over 5.5s (NYI 2-3 SJ, PHI 3-1 VAN) at -160/-172. Long Lottery tickets lost on plus-money NHL -2.5 puck lines and NBA player props (expected). No grading bug, no missed news.
Backtest (16 graded shadow days 10-25..11-09; /workspace/kfsp_review/r1110/bt.py):
- baseline (NHL trim + CFB deep Under -3): ladder 1-4 48/64 (ROI -0.05); 5+ 61/290 (10.77x, ROI +0.26); top-pick 85.0%.
- no NHL trim: 5+ 52/290 (ROI -0.00) -> trim confirmed again.
- NBA Unders -2/-3: 1-4 46-47/64, 5+ 61/290, ROI +0.05 -> REJECTED (fewer wins, lower payouts).
- NHL Unders -5/-10: 1-4 49/64 (+1) but 5+ 56-57/290 (-4/-5) -> REJECTED (net fewer wins, lower ROI).
- soccer Over 1.5 +2, combo: REJECTED. v2 live: REJECTED.
Changes (backup /workspace/kfsp_backups/2026-11-10/): cleared stale legs.json news_adj (dated 11-09). No model change: nothing tested beats the current system on both win count and payout. v1 stays live (live_model/allow_switch untouched). FanDuel links / King's Favorites / no-live pregame / update.sh preserved.

## 2026-11-10 10:30 AM ET intraday review (~10:35–10:45 AM ET)
Status: v1 live (live_model/allow_switch untouched). Today's slate is all evening (first start 7:00 PM ET: three MAC games, six NBA, seven NHL), so no ladder ticket has locked; nothing unlocked.
Graded since 3 AM: no games finished (11-09 fully graded at 3 AM). Record unchanged: 627 tickets; ladder 92-280, Best 3-13, Lottery 25-208, green 30-38, researched 2-leg 5-1. No new losing-leg pattern; no model change (no backtest-proven fix pending).
Research (~10:35 AM ET):
- NBA (ESPN injuries): SAC Raynaud out, Sabonis (knee) and Keegan Murray (wrist) Q; ORL still without Banchero, Suggs, Isaac. UTA Keyonte George out, Markkanen Q, JJJ out; MIA Giannis probable (wrist). MIL Herro Q; NYK Hart Q. LAC Ingram, Beal, Niederhauser out, Christie Q; PHX M. Williams and Goodwin out. OKC Jaylin Williams out (plus Holmgren, Jalen Williams, Wallace); POR Morant, Krejci, Sharpe out. PHI Bona, Barlow, Hukporti out.
- NHL (Daily Faceoff, 1/14 confirmed): NJ Jake Allen confirmed vs WPG Nico Daws likely (backup); COL Blackwood vs TOR Bobrovsky; WSH Thompson vs OTT Ullmark; MIN Wallstedt vs MTL Fowler; FLA Markstrom vs CBJ Talbot; DET Gibson (day-to-day) vs STL Hofer; NSH Saros vs LA Kuemper. CBJ Garland out indefinitely.
- CFB weather (ESPN/AccuWeather): all three MAC games clear, 50-52F. Lines (ESPN/DK): WMU -14.5 (ML -600 to -675), Ohio flipped to -118.
- Line check: ESPN main lines NYK -15.5, BOS -1.5, PHX -3.5, MIA -8.5, ORL -6.5, OKC -1.5. No move that contradicts a ticket leg.
Assessment: no current ladder/Best/Lottery/Props leg is weakened by the news. Q/DTD players (Sabonis, K. Murray, Markkanen, Herro, Hart, Giannis, Christie) are already auto-excluded from Props/NBA tabs by ESPN status. Allen-in-net for NJ was confirmed yesterday afternoon and is already priced (NJ -155), so no news_adj (avoids the double-count lesson from 11-09 Houston). No legs.json change.
Researched 2-leg board rewritten for 11-10 (prices re-verified on FanDuel PA and MD event pages 15:36 UTC = 10:36 AM ET, all identical): A1 WMU +2.5 (-1000) + ORL +10.5 (-1000) est. $1.21/$1, break-even 82.6%; A2 NYK -1.5 (-900) + MIA +7.5 (-900) $1.23, 81.0%; A3 BOS +14.5 (-950) + Ohio +16.5 (-1000) $1.22, 82.3%; A4 LAC +18.5 (-950) + OKC +13.5 (-950) $1.22, 81.9%; B LAC +14.5 (-480) + ORL +5.5 (-390) $1.52, 65.9%. NHL legs left out on purpose. Strict 2-leg board: no pair qualifies (best near miss NJ +1.5 at 0.866 calibrated vs 0.92 bar). Not strict-qualified; no edge over FanDuel demonstrated. Backup /workspace/kfsp_backups/2026-11-10-am/.
Published f2a7a264 (~10:38 AM ET), site 200. Best Parlay after rebuild ~23.8% / 4.29x: OTT +1.5, BOS +7.5, LAC-PHX Under 236.5, OKC-POR Under 236.5, ORL +2.5. v2 switch_ready still true, not re-reported.

## 2026-11-10 3:00 PM ET intraday review (~3:11–3:20 PM ET)
Status: v1 live (live_model/allow_switch untouched). First start still 7:00 PM ET, so no ladder ticket has locked; nothing unlocked.
Graded since 10:30 AM: no games finished. Record unchanged: 627 tickets; ladder 92-280, Best 3-13, Lottery 25-208, green 30-38, researched 2-leg 5-1. No new losing-leg pattern; no backtest-proven fix pending, so no model change.
Research (~3:12 PM ET):
- NBA official injury report (2:15 PM ET) + ESPN: Markkanen now OUT (was Q), Nurkic and Simmons out; Josh Hart downgraded to DOUBTFUL (illness); Herro, Ware, Sabonis, K. Murray, da Silva, Christie Q; Giannis probable. Phoenix not yet filed. Market already moved (MIA ML -357 to -438, ORL -188 to -237). Markkanen out only strengthens our Miami spread and MIA-UTA Under legs; Q/DTD/Out players auto-excluded from Props/NBA tabs (props excl inj 5).
- NHL goalies (Daily Faceoff, 11/14 confirmed): OTT Ullmark still out, backup Ersson confirmed (.950 last 3); FanDuel already priced it (OTT ML -130 to -108, Ottawa +2.5 drifted -700 to -550). LA starts Forsberg instead of Kuemper; priced (LA -148 to -130, Kings +2.5 -700 steady). WPG Daws confirmed (backup), NJ Allen confirmed. Others: Blackwood/Bobrovsky, Wallstedt/Fowler, Markstrom/Talbot, Gibson/Hofer (likely); WSH Thompson and NSH Saros unconfirmed.
- CFB: all three MAC games clear, ~50F; WMU ML moved -600 to -750 (supports WMU +2.5/+1.5 legs).
Assessment: every news item is already reflected in FanDuel's current prices, which the model reads; adding a manual news_adj would double-count (11-09 Houston lesson). Ottawa +2.5 appears on 8 ladder tickets and Ottawa +1.5 is in the Best Parlay; both remain priced as favorites-to-cover after the goalie news, so kept. No legs.json change.
Rebuilt and published 0854a0a1 (~3:12 PM ET), site 200. Best Parlay ~22.2% / 4.27x: OTT +1.5, LAC-PHX Under 236.5, MIA-UTA Under 239.5, POR +9.5, BOS-PHI Over 206.5. Strict 2-leg board still empty (best near misses COL/NJ +1.5 at 0.866 vs 0.92 bar). v2 switch_ready still true, not re-reported.
