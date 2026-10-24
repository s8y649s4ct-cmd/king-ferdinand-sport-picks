#!/usr/bin/env bash
# Commit & push site changes to GitHub Pages only if something changed. Quiet, idempotent.
set -euo pipefail; cd "$(dirname "$0")"
git add -A
git diff --cached --quiet && exit 0
git -c user.name="KFSP Bot" -c user.email="kfsp@users.noreply.github.com" commit -qm "Refresh picks $(date -u '+%Y-%m-%d %H:%M UTC')"
git push -q origin main
