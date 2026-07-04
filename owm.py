# weewx uploader for OpenWeatherMap Stations API 3.0
# Uses weewx RESTThread pattern for reliable non-blocking operation

import json
import queue
import urllib.request
import weewx
import weewx.restx
import weewx.units
from weewx.restx import StdRESTbase, RESTThread, get_site_dict
import logging

log = logging.getLogger(__name__)

STATION_URL = 'http://api.openweathermap.org/data/3.0/measurements'

class OWM(StdRESTbase):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        site_dict = get_site_dict(config_dict, 'OWM', 'api_key', 'station_id')
        if site_dict is None:
            return
        site_dict['manager_dict'] = weewx.manager.get_manager_dict_from_config(
            config_dict, 'wx_binding')
        self.archive_queue = queue.Queue()
        self.archive_thread = OWMThread(self.archive_queue, **site_dict)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        log.info("OWM: station_id=%s", site_dict['station_id'])

    def new_archive_record(self, event):
        self.archive_queue.put(event.record)


class OWMThread(RESTThread):
    def __init__(self, queue, api_key, station_id, manager_dict,
                 server_url=STATION_URL,
                 post_interval=60, max_backlog=6, stale=1800,
                 log_success=True, log_failure=True,
                 timeout=10, max_tries=3, retry_wait=5,
                 skip_upload=False):
        super().__init__(queue,
                         protocol_name='OWM',
                         manager_dict=manager_dict,
                         post_interval=post_interval,
                         max_backlog=max_backlog,
                         stale=stale,
                         log_success=log_success,
                         log_failure=log_failure,
                         timeout=timeout,
                         max_tries=max_tries,
                         retry_wait=retry_wait,
                         skip_upload=skip_upload)
        self.api_key = api_key
        self.station_id = station_id
        self.server_url = server_url

    def format_url(self, record):
        return self.server_url + '?appid=' + self.api_key

    def post_request(self, request, data=None):
        record_m = weewx.units.to_METRIC(request) if isinstance(request, dict) else request
        # Build the URL from format_url was already called, get the record from request
        return super().post_request(request, data)

    def run_loop(self, dbmanager=None):
        """Override run_loop to handle JSON POST."""
        import time
        self.dbmanager = dbmanager
        while True:
            try:
                record = self.queue.get(timeout=60)
            except Exception:
                continue
            if record is None:
                break
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

                url = self.server_url + '?appid=' + self.api_key
                payload = json.dumps([data]).encode('utf-8')
                req = urllib.request.Request(url, data=payload,
                    headers={'Content-Type': 'application/json'})
                resp = urllib.request.urlopen(req, timeout=self.timeout)
                log.info("OWM: published record %s status=%s", data['dt'], resp.getcode())
            except Exception as e:
                log.error("OWM: failed to post: %s", e)
