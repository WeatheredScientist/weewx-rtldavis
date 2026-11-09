# SPDX-License-Identifier: GPL-3.0-or-later
"""Print the last three archive records, one line each.

The archive half of ops/wxcheck.sh. It runs inside the weewx container, where
the archive is /opt/weewx-data/archive/weewx.sdb. The image does not bake it
in, so feed it over stdin:

    marvinctl --tenant weewx exec weewx-rtldavis-v2 -- /opt/weewx-venv/bin/python3 - < ops/wxcheck.py

Opens the database read-only (a wrong path errors instead of creating an
empty file). A missing value prints as 0.
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('file:/opt/weewx-data/archive/weewx.sdb?mode=ro', uri=True)
c = conn.cursor()
c.execute('SELECT dateTime, outTemp, outHumidity, barometer, windSpeed, windGust, windDir FROM archive ORDER BY dateTime DESC LIMIT 3')
for r in c.fetchall():
    print(datetime.fromtimestamp(r[0]), 'temp=%.1f' % (r[1] or 0), 'hum=%.0f' % (r[2] or 0), 'bar=%.2f' % (r[3] or 0), 'ws=%.1f' % (r[4] or 0), 'wg=%.1f' % (r[5] or 0), 'wd=%.0f' % (r[6] or 0))
