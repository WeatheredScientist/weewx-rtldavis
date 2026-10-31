# weewx uploader for OpenWeatherMap Stations API 3.0
# Uses weewx RESTThread pattern for reliable non-blocking operation
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import weewx.units

try:
    from user.rest_site import SiteService, SiteThread
except ImportError:  # outside the image, where rest_site.py is a top-level module
    from rest_site import SiteService, SiteThread

STATION_URL = 'http://api.openweathermap.org/data/3.0/measurements'


class OWMThread(SiteThread):
    FIELDS = (
        ('temperature', 'outTemp', None, 1),
        ('humidity', 'outHumidity', None, 0),
        ('pressure', 'barometer', None, 1),
        ('wind_speed', 'windSpeed', lambda v: v / 3.6, 1),
        ('wind_gust', 'windGust', lambda v: v / 3.6, 1),
        ('wind_deg', 'windDir', None, 0),
        ('dew_point', 'dewpoint', None, 1),
        ('heat_index', 'heatindex', None, 1),
        # to_METRIC rain is centimeters; the Stations API takes millimeters (#405).
        ('rain_1h', 'hourRain', lambda v: v * 10, 2),
    )

    def __init__(self, queue, api_key, station_id, manager_dict,
                 server_url=STATION_URL, post_interval=60, **kwargs):
        super().__init__(queue, 'OWM', manager_dict, server_url, post_interval,
                         **kwargs)
        self.api_key = api_key
        self.station_id = station_id

    def format_url(self, record):
        # The OWM Stations API takes the API key on the query string; the
        # measurement itself travels in the JSON POST body (see get_post_body).
        return self.server_url + '?appid=' + self.api_key

    def get_post_body(self, record):
        """Build the OWM Stations measurement POST body.

        Returns ``(body, content_type)`` per the RESTThread contract. Handing
        the body back to RESTThread (instead of the old hand-rolled run_loop)
        lets the superclass own the retry/backoff/stale/post_interval/skip_upload
        loop, so a transient network failure is retried instead of dropping the
        record (S24 U1/U2).
        """
        record_m = weewx.units.to_METRIC(record)
        data = {'station_id': self.station_id,
                'dt': int(record_m['dateTime'])}
        for name, value, places in self.fields(record_m):
            data[name] = round(value, places)
        return json.dumps([data]), 'application/json'


class OWM(SiteService):
    SITE = 'OWM'
    REQUIRED = ('api_key', 'station_id')
    THREAD = OWMThread
