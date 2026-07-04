#!/bin/sh
echo "=== WU Rapidfire ==="
curl -s "https://api.weather.com/v2/pws/observations/current?stationId=${WU_STATION_ID}&format=json&units=e&apiKey=${WU_API_KEY}" | python3 -m json.tool | grep -i "winddir\|windSpeed\|windGust\|temp\|humidity\|pressure"
echo "=== weewx Archive (last 3) ==="
docker exec weewx-rtldavis-v2 /opt/weewx-venv/bin/python3 /opt/weewx-data/wxcheck.py
