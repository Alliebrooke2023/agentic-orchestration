#!/usr/bin/env bash
# driftrack/start.sh  -  Linux/macOS launcher:  ./start.sh  (add --empty to skip demo data)
cd "$(dirname "$0")" || exit 1
if [ "$1" = "--empty" ]; then exec python3 app.py; fi
exec python3 app.py --seed
