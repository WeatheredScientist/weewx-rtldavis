# weewx uploader for windy.com stations API v2
import queue
import time
import weewx
import weewx.restx
import weewx.units
import weewx.manager
from weewx.engine import StdService
import logging
import urllib.request
import urllib.parse

log = logging.getLogger(__name__)

STATION_URL = 'https://stations.windy.com/api/v2/observation/update'

class Windy(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        site_dict = config_dict.get('Windy', {})
        self.station_id = site_dict.get('station_id', '')
        self.password = site_dict.get('password', '')
        if not self.station_id or not self.password:
            # try under StdRESTful
            site_dict = config_dict.get('StdRESTful', {}).get('Windy', {})
            self.station_id = site_dict.get('station_id', '')
            self.password = site_dict.get('password', '')
        if not self.station_id or not self.password:
            log.error("Windy: missing station_id or password")
            return
        log.info("Windy v2: station_id=%s", self.station_id)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_archive_record(self, event):
        import threading
        t = threading.Thread(target=self.post, args=(event.record,))
        t.daemon = True
        t.start()

    def post(self, record):
        try:
            record_m = weewx.units.to_METRIC(record)
            params = {'id': self.station_id, 'PASSWORD': self.password, 'time': 'now'}
            if record_m.get('outTemp') is not None:
                params['temp'] = '%.1f' % record_m['outTemp']
            if record_m.get('dewpoint') is not None:
                params['dewpoint'] = '%.1f' % record_m['dewpoint']
            if record_m.get('outHumidity') is not None:
                params['humidity'] = '%.0f' % record_m['outHumidity']
            if record_m.get('windSpeed') is not None:
                params['wind'] = '%.1f' % (record_m['windSpeed'] / 3.6)
            if record_m.get('windGust') is not None:
                params['gust'] = '%.1f' % (record_m['windGust'] / 3.6)
            if record_m.get('windDir') is not None:
                params['winddir'] = '%.0f' % record_m['windDir']
            if record_m.get('barometer') is not None:
                params['pressure'] = '%.0f' % (record_m['barometer'] * 100)
            if record_m.get('rain') is not None:
                params['precip'] = '%.2f' % record_m['rain']
            if record_m.get('UV') is not None:
                params['uv'] = '%.1f' % record_m['UV']
            if record_m.get('radiation') is not None:
                params['solarradiation'] = '%.1f' % record_m['radiation']

            url = STATION_URL + '?' + urllib.parse.urlencode(params)
            req = urllib.request.urlopen(url, timeout=10)
            resp = req.read().decode('utf-8')
            log.info("Windy: published record %s, response: %s",
                     weewx.units.to_std_system(record, weewx.US).get('dateTime', ''), resp.strip())
        except Exception as e:
            log.error("Windy: failed to post: %s", e)
