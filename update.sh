#!/usr/bin/env bash
# King Ferdinand Sport Picks refresh. Idempotent; concurrent runs skip via lock.
# Auto: ESPN scoreboards/injuries/boxscores, FanDuel public sportsbook JSON (all priced markets), open-meteo weather,
#   lines.history.json, picks.history.json (locks once games start, auto-grades), stats.json (calibration).
# extra.py: Live in-game picks + pregame player props -> extra.json, extra.history.json (graded separately). A failure there never blocks the main board.
# extra2.py: NFL anytime-TD tab + NBA 3s & rebounds tab -> extra2.json, extra2.history.json (graded separately).
# Manual: model probs in legs.json "models", notes.json injuries, feature.json (Best Parlay breakdown).
set -euo pipefail; cd "$(dirname "$0")"
exec 9>.update.lock; flock -n 9 || { echo "another refresh running; skip"; exit 0; }
python3 build.py
timeout 300 python3 extra.py || echo "extra.py failed; live/props board left as-is"
timeout 300 python3 extra2.py || echo "extra2.py failed; TD / NBA 3s & rebounds board left as-is"
./publish.sh
