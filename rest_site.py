# Shared base for the site uploaders owm.py and windy.py (S180a, audit 23)
# Uses weewx RESTThread pattern for reliable non-blocking operation
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The service subclass names its weewx.conf section, the credential keys it requires
# and its thread class. The thread subclass names its field map and builds its own
# URL and body from fields(). Logging goes to the subclass's module logger, so log
# lines keep their user.owm / user.windy names.

import queue
import logging
import weewx
import weewx.manager
from weewx.restx import StdRESTbase, RESTThread, get_site_dict


class SiteService(StdRESTbase):
    SITE = ''           # weewx.conf section, also the protocol name in the log
    REQUIRED = ()       # keys get_site_dict must find in that section
    THREAD = RESTThread

    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        site_dict = get_site_dict(config_dict, self.SITE, *self.REQUIRED)
        if site_dict is None:
            return
        site_dict['manager_dict'] = weewx.manager.get_manager_dict_from_config(
            config_dict, 'wx_binding')
        self.archive_queue = queue.Queue()
        self.archive_thread = self.THREAD(self.archive_queue, **site_dict)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        logging.getLogger(type(self).__module__).info(
            "%s: station_id=%s", self.SITE, site_dict['station_id'])

    def new_archive_record(self, event):
        self.archive_queue.put(event.record)


class SiteThread(RESTThread):
    # (API name, observation type, conversion from the to_METRIC value or None,
    # decimal places), in the order the API receives them.
    FIELDS = ()

    def __init__(self, queue, protocol_name, manager_dict, server_url,
                 post_interval, max_backlog=6, stale=1800,
                 log_success=True, log_failure=True,
                 timeout=10, max_tries=3, retry_wait=5,
                 skip_upload=False):
        super().__init__(queue,
                         protocol_name=protocol_name,
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
        self.server_url = server_url

    def fields(self, record_m):
        """Yield (API name, value, decimal places) for each field present in the
        to_METRIC record, converted to the API's unit. A None field is left out;
        0.0 is a reading and is kept.

        The conversion stays on to_METRIC with the arithmetic the uploaders always
        used. to_METRICWX would give m/s and mm directly, but its factors round
        differently at the last bit (weewx's km/h to m/s factor is 0.277777778, not
        1/3.6), which moves a value sitting on a rounding boundary to the other side
        and changes the bytes sent (S180a, measured against weewx 5.5.2).
        """
        for name, obs_type, convert, places in self.FIELDS:
            value = record_m.get(obs_type)
            if value is not None:
                yield name, value if convert is None else convert(value), places
