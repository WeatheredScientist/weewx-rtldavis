# weewx uploader for OpenWeatherMap Stations API 3.0
import threading
import urllib.request
import urllib.parse
import json
import weewx
import weewx.units
from weewx.engine import StdService
import logging

log = logging.getLogger(__name__)

STATION_URL = 'http://api.openweathermap.org/data/3.0/measurements'

class OWM(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        site_dict = config_dict.get('OWM', {})
        self.api_key = site_dict.get('api_key', '')
        self.station_id = site_dict.get('station_id', '')
        self.post_interval = int(site_dict.get('post_interval', 60))
        if not self.api_key or not self.station_id:
            log.error("OWM: missing api_key or station_id")
            return
        self.last_post = 0
        log.info("OWM: station_id=%s post_interval=%s", self.station_id, self.post_interval)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_archive_record(self, event):
        now = time.time()
        if now - self.last_post < self.post_interval:
            return
        self.last_post = now
        t = threading.Thread(target=self.post, args=(event.record,))
        t.daemon = True
        t.start()

    def post(self, record):
        try:
            record_m = weewx.units.to_METRIC(record)
            data = {'station_id': self.station_id,
                    'dt': int(record_m['dateTime'])}

            if record_m.get('outTemp') is not None:
                data['temperature'] = round(record_m['outTemp'], 1)
            if record_m.get('outHumidity') is not None:
                data['humidity'] = round(record_m['outHumidity'], 0)
            if record_m.get('barometer') is not None:
                data['pressure'] = round(record_m['barometer'], 1)
            if record_m.get('windSpeed') is not None:
                data['wind_speed'] = round(record_m['windSpeed'] / 3.6, 1)
            if record_m.get('windGust') is not None:
                data['wind_gust'] = round(record_m['windGust'] / 3.6, 1)
            if record_m.get('windDir') is not None:
                data['wind_deg'] = round(record_m['windDir'], 0)
            if record_m.get('dewpoint') is not None:
                data['dew_point'] = round(record_m['dewpoint'], 1)
            if record_m.get('heatindex') is not None:
                data['heat_index'] = round(record_m['heatindex'], 1)
            if record_m.get('hourRain') is not None:
                data['rain_1h'] = round(record_m['hourRain'], 2)
            if record_m.get('rain24') is not None:
                data['rain_24h'] = round(record_m['rain24'], 2)

            log.info("OWM: sending data: %s", json.dumps(data))
            url = STATION_URL + '?appid=' + self.api_key
            payload = json.dumps([data]).encode('utf-8')
            req = urllib.request.Request(url, data=payload,
                headers={'Content-Type': 'application/json'})
            resp = urllib.request.urlopen(req, timeout=10)
            status = resp.getcode()
            body = resp.read().decode('utf-8')
            log.info("OWM: published record %s, status=%s body=%s",
                     data['dt'], status, body if body else '(empty)')
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            log.error("OWM: HTTP error %s: %s", e.code, body)
        except Exception as e:
            log.error("OWM: failed to post: %s", e)
# weewx uploader for OpenWeatherMap Stations API 3.0
import threading
import time
import urllib.request
import urllib.parse
import json
import weewx
import weewx.units
from weewx.engine import StdService
import logging

log = logging.getLogger(__name__)

STATION_URL = 'http://api.openweathermap.org/data/3.0/measurements'

class OWM(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        site_dict = config_dict.get('OWM', {})
        self.api_key = site_dict.get('api_key', '')
        self.station_id = site_dict.get('station_id', '')
        if not self.api_key or not self.station_id:
            log.error("OWM: missing api_key or station_id")
            return
        log.info("OWM: station_id=%s", self.station_id)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_archive_record(self, event):
        t = threading.Thread(target=self.post, args=(event.record,))
        t.daemon = True
        t.start()

    def post(self, record):
        try:
            record_m = weewx.units.to_METRIC(record)
            data = {'station_id': self.station_id,
                    'dt': int(record_m['dateTime'])}

            if record_m.get('outTemp') is not None:
                data['temperature'] = round(record_m['outTemp'], 1)
            if record_m.get('outHumidity') is not None:
                data['humidity'] = round(record_m['outHumidity'], 0)
            if record_m.get('barometer') is not None:
                data['pressure'] = round(record_m['barometer'], 1)
            if record_m.get('windSpeed') is not None:
                # weewx metric is km/h, OWM wants m/s
                data['wind_speed'] = round(record_m['windSpeed'] / 3.6, 1)
            if record_m.get('windGust') is not None:
                data['wind_gust'] = round(record_m['windGust'] / 3.6, 1)
            if record_m.get('windDir') is not None:
                data['wind_deg'] = round(record_m['windDir'], 0)
            if record_m.get('dewpoint') is not None:
                data['dew_point'] = round(record_m['dewpoint'], 1)
            if record_m.get('heatindex') is not None:
                data['heat_index'] = round(record_m['heatindex'], 1)
            if record_m.get('hourRain') is not None:
                data['rain_1h'] = round(record_m['hourRain'], 2)
            if record_m.get('rain24') is not None:
                data['rain_24h'] = round(record_m['rain24'], 2)

            url = STATION_URL + '?appid=' + self.api_key
            payload = json.dumps([data]).encode('utf-8')
            req = urllib.request.Request(url, data=payload,
                headers={'Content-Type': 'application/json'})
            resp = urllib.request.urlopen(req, timeout=10)
            log.info("OWM: published record %s", data['dt'])
        except Exception as e:
            log.error("OWM: failed to post: %s", e)
