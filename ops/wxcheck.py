import sqlite3
from datetime import datetime
conn = sqlite3.connect('/opt/weewx-data/archive/weewx.sdb')
c = conn.cursor()
c.execute('SELECT dateTime, outTemp, outHumidity, barometer, windSpeed, windGust, windDir FROM archive ORDER BY dateTime DESC LIMIT 3')
for r in c.fetchall():
    print(datetime.fromtimestamp(r[0]), 'temp=%.1f' % (r[1] or 0), 'hum=%.0f' % (r[2] or 0), 'bar=%.2f' % (r[3] or 0), 'ws=%.1f' % (r[4] or 0), 'wg=%.1f' % (r[5] or 0), 'wd=%.0f' % (r[6] or 0))
