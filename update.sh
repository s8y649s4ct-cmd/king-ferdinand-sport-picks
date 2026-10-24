#!/usr/bin/env bash
# King Ferdinand Sport Picks refresh. Idempotent; safe for a scheduled job (e.g. every 5-15 min).
# Automatic: ESPN scoreboards (scores/status/DraftKings lines incl. auto CFB favourite legs),
#   ESPN injury feeds, weather (ESPN/AccuWeather, else open-meteo), lines.history.json snapshot,
#   picks.history.json (new parlays appended once, ML legs auto-graded when final).
# Manual/research (agent): FanDuel-verified prices, model probs & rationale in legs.json; X/official notes in notes.json.
#   Change "date" in legs.json for a new slate. Never invent odds.
set -euo pipefail; cd "$(dirname "$0")"; python3 build.py
./publish.sh
