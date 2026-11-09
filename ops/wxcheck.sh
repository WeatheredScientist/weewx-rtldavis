#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
#
# wxcheck.sh: a manual side-by-side spot check. Prints Weather Underground's
# current observation for the station above the last three archive records
# prod wrote, to eyeball a sensor or upload disagreement. Read-only both ways.
#
# Run from a checkout on a machine that has the marvinctl wrapper:
#   WU_STATION_ID=... WU_API_KEY=... sh ops/wxcheck.sh
# The two values come from your shell (the gitignored local-infra doc holds
# them); never write them into this file or a commit. Without them the WU half
# is skipped and the archive half still runs.
#
# The archive half pipes this checkout's ops/wxcheck.py into the running
# container over stdin, so the repo copy is what runs. A file named
# weewx-data/wxcheck.py on marvin is an older, separate copy this no longer
# uses.

if [ -n "${WU_STATION_ID:-}" ] && [ -n "${WU_API_KEY:-}" ]; then
    echo "=== WU current ==="
    curl -s "https://api.weather.com/v2/pws/observations/current?stationId=${WU_STATION_ID}&format=json&units=e&apiKey=${WU_API_KEY}" | python3 -m json.tool | grep -i "winddir\|windSpeed\|windGust\|temp\|humidity\|pressure"
else
    echo "=== WU current: skipped (set WU_STATION_ID and WU_API_KEY) ==="
fi
echo "=== weewx archive (last 3) ==="
marvinctl --tenant weewx exec weewx-rtldavis-v2 -- /opt/weewx-venv/bin/python3 - < "$(dirname "$0")/wxcheck.py"
