# weewx uploader for Windy.com Stations API v2
# Uses weewx RESTThread pattern for reliable non-blocking operation
# SPDX-License-Identifier: GPL-3.0-or-later

import urllib.parse
import weewx.units
import logging

try:
    from user.rest_site import SiteService, SiteThread
except ImportError:  # outside the image, where rest_site.py is a top-level module
    from rest_site import SiteService, SiteThread

log = logging.getLogger(__name__)

STATION_URL = 'https://stations.windy.com/api/v2/observation/update'


class WindyThread(SiteThread):
    FIELDS = (
        ('temp', 'outTemp', None, 1),
        ('dewpoint', 'dewpoint', None, 1),
        ('humidity', 'outHumidity', None, 0),
        ('wind', 'windSpeed', lambda v: v / 3.6, 1),
        ('gust', 'windGust', lambda v: v / 3.6, 1),
        ('winddir', 'windDir', None, 0),
        ('pressure', 'barometer', lambda v: v * 100, 0),
        # Windy wants the last hour in millimeters. to_METRIC rain is centimeters,
        # and 'rain' covers only one archive interval (#405).
        ('precip', 'hourRain', lambda v: v * 10, 2),
        ('uv', 'UV', None, 1),
        ('solarradiation', 'radiation', None, 1),
    )

    def __init__(self, queue, station_id, password, manager_dict,
                 server_url=STATION_URL, post_interval=300, **kwargs):
        super().__init__(queue, 'Windy', manager_dict, server_url, post_interval,
                         **kwargs)
        self.station_id = station_id
        self.password = password

    def format_url(self, record):
        record_m = weewx.units.to_METRIC(record)
        params = {'id': self.station_id, 'PASSWORD': self.password, 'time': 'now'}
        for name, value, places in self.fields(record_m):
            params[name] = '%.*f' % (places, value)
        return self.server_url + '?' + urllib.parse.urlencode(params)

    def check_response(self, response):
        for line in response:
            if line.strip():
                log.debug("Windy response: %s", line.strip())


class Windy(SiteService):
    SITE = 'Windy'
    REQUIRED = ('station_id', 'password')
    THREAD = WindyThread
