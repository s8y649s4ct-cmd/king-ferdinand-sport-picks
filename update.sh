#!/usr/bin/env bash
# King Ferdinand Sport Picks refresh. Idempotent; concurrent runs skip via lock.
# Auto: ESPN scoreboards/injuries/boxscores, FanDuel public sportsbook JSON (all priced markets), open-meteo weather,
#   lines.history.json, picks.history.json (locks once games start, auto-grades), stats.json (calibration).
# Manual: model probs in legs.json "models", notes.json injuries, feature.json (Best Parlay breakdown).
set -euo pipefail; cd "$(dirname "$0")"
exec 9>.update.lock; flock -n 9 || { echo "another refresh running; skip"; exit 0; }
python3 build.py
./publish.sh
