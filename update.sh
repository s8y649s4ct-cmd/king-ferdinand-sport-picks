#!/usr/bin/env bash
# King Ferdinand Sport Picks refresh. Idempotent; concurrent runs skip via lock.
# Auto: ESPN scoreboards/injuries/boxscores, FanDuel public sportsbook JSON (all priced markets), open-meteo weather,
#   lines.history.json, picks.history.json (locks once games start, auto-grades), stats.json (calibration).
# extra.py: Live in-game picks + pregame player props -> extra.json, extra.history.json (graded separately). A failure there never blocks the main board.
# extra2.py: NFL anytime-TD tab + NBA 3s & rebounds tab -> extra2.json, extra2.history.json (graded separately).
# twoleg.py: Best 2-Leg Parlays (strict calibrated bar) -> twoleg.json, twoleg.history.json. record.py: enhanced Track record -> record.json.
# bt_ev.py + bt_cal.py: out-of-sample backtests -> backtest.json. ledger.py: ROI ledger -> ledger.json. ev.py (called by build.py): EV fields + Value singles.
# oddsrule.py: hard odds rule (-950..+1,000,000 legs and tickets), enforced before publish.
# Manual: model probs in legs.json "models", notes.json injuries, feature.json (Best Parlay breakdown).
set -euo pipefail; cd "$(dirname "$0")"
exec 9>.update.lock; flock -n 9 || { echo "another refresh running; skip"; exit 0; }
python3 build.py
timeout 300 python3 extra.py || echo "extra.py failed; live/props board left as-is"
timeout 300 python3 extra2.py || echo "extra2.py failed; TD / NBA 3s & rebounds board left as-is"
timeout 120 python3 twoleg.py || echo "twoleg.py failed; 2-leg board left as-is"
timeout 300 python3 record.py || echo "record.py failed; enhanced record left as-is"
timeout 120 python3 bt_ev.py || echo "bt_ev.py failed; backtest left as-is"
timeout 120 python3 ledger.py || echo "ledger.py failed; ROI ledger left as-is"
timeout 120 python3 md.py || echo "md.py failed; Maryland links left as-is"
python3 oddsrule.py --enforce || { echo "odds rule check failed; not publishing"; exit 1; }  # 2026-11-15 hard rule: legs/tickets -950..+1,000,000
./publish.sh
