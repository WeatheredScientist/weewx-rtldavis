# weewx uploader for Windy.com Stations API v2
# Uses weewx RESTThread pattern for reliable non-blocking operation
# SPDX-License-Identifier: GPL-3.0-or-later

import queue
import urllib.parse
import weewx
import weewx.restx
import weewx.units
import weewx.manager
from weewx.restx import StdRESTbase, RESTThread, get_site_dict
import logging

log = logging.getLogger(__name__)

STATION_URL = 'https://stations.windy.com/api/v2/observation/update'


class Windy(StdRESTbase):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        site_dict = get_site_dict(config_dict, 'Windy', 'station_id', 'password')
        if site_dict is None:
            return
        site_dict['manager_dict'] = weewx.manager.get_manager_dict_from_config(
            config_dict, 'wx_binding')
        self.archive_queue = weewx.restx.get_queue(config_dict, 'Windy', 'archive') \
            if hasattr(weewx.restx, 'get_queue') else queue.Queue()
        self.archive_thread = WindyThread(self.archive_queue, **site_dict)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        log.info("Windy: station_id=%s", site_dict['station_id'])

    def new_archive_record(self, event):
        self.archive_queue.put(event.record)


class WindyThread(RESTThread):
    def __init__(self, queue, station_id, password, manager_dict,
                 server_url=STATION_URL,
                 post_interval=300, max_backlog=6, stale=1800,
                 log_success=True, log_failure=True,
                 timeout=10, max_tries=3, retry_wait=5,
                 skip_upload=False):
        super().__init__(queue,
                         protocol_name='Windy',
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
        self.station_id = station_id
        self.password = password
        self.server_url = server_url

    def format_url(self, record):
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
        return self.server_url + '?' + urllib.parse.urlencode(params)

    def check_response(self, response):
        for line in response:
            if line.strip():
                log.debug("Windy response: %s", line.strip())
