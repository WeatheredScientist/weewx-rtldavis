# SPDX-License-Identifier: GPL-3.0-or-later
#-----------------------------------------------------------------
#         WeeWX OgoXe uploader v1.0.1
#
#    Copyright (c) 2026 OgoXe developers <dev@ogoxe.com>
#
#    Copyright (c) 2026 Sigi Meisenbichler <s.meisen@icloud.com>
#
#    Copyright (c) 2025 Vince Skahan <vinceskahan@gmail.com>
#
# This is derived almost verbatim from smeisens/weewx-wundergroundlike (Github), weewx 5.2.0 restx.py 
# which is:
#
#    Copyright (c) 2009-2024 Tom Keffer <tkeffer@gmail.com>
#
# The upstream code this is based on uses a LICENSE.txt file
# that is present here for reference.
#
#-----------------------------------------------------------------
# 2026 patched by WeatheredScientist
#   github.com/WeatheredScientist/weewx-rtldavis
#
#   GPLv3 section 5(a) modification notice. Vendored from the OgoXe uploader
#   v1.0.1 and modified:
#
#   2026-07-05  a log.debug() reported _ambient_dict.get('server_url'), a key that
#               is never set (the URL is the hardcoded OGOXE_API_URL constant), so
#               it always logged None. It now logs the URL actually used.
#   2026-07-05  added the SPDX-License-Identifier line above.
#
#   See CHANGES-FROM-UPSTREAM.md.
#-----------------------------------------------------------------

import logging
import queue

import weewx.engine
import weewx.manager
import weewx.restx
from weeutil.weeutil import to_bool

log = logging.getLogger(__name__)

# Target Ogoxe Weather Platform Wunderground-like API URL
OGOXE_API_URL = 'https://application.ogoxe.com/upload-data'

#-----------------------------------------------------------------
#         OgoXe (Wunderground-like) uploader
#-----------------------------------------------------------------

class OgoxeUploader(weewx.restx.StdWunderground):
    """Custom class to upload data to OgoXe's Weather Underground compatible servers.

    Differences from the weewx Wunderground class:
    - default URL is hardcoded and immutable
    - explicitly point to weewx.restx.foo for a few items
    - slightly different logging output to reflect this class's name
    - slightly different/added logging
    - rapidfire is not supported (archive post only)

    For additional information, see:
        https://support.wunderground.com/article/Knowledge/How-do-I-upload-data-from-my-personal-weather-station-to-Weather-Underground
        http://wiki.wunderground.com/index.php/PWS_-_Upload_Protocol
    """

    def __init__(self, engine, config_dict):
        weewx.engine.StdService.__init__(self, engine, config_dict)

        # This uploader requires 'station', 'password'
        _ambient_dict = weewx.restx.get_site_dict(
            config_dict, 'OgoxeUploader', 'station', 'password')
        if _ambient_dict is None:
            log.error("OgoxeUploader: Missing required configuration. "
                      "Please ensure [StdRESTful][[OgoxeUploader]] is properly configured "
                      "with 'station', and 'password' in weewx.conf")
            return

        log.info("OgoxeUploader: Configuration loaded for station %s", 
                 _ambient_dict.get('station', 'UNKNOWN'))

        # server_url is hardcoded (OGOXE_API_URL below), not from get_site_dict
        log.debug("OgoxeUploader server_url: %s", OGOXE_API_URL)

        # Get the manager dictionary:
        _manager_dict = weewx.manager.get_manager_dict_from_config(
            config_dict, 'wx_binding')

        # Only archive post is supported (no rapidfire)
        _ambient_dict.pop('rapidfire', None)  # Remove if present in config
        do_archive_post = to_bool(_ambient_dict.pop('archive_post', True))

        if do_archive_post:
            # server_url is the hardcoded OGOXE_API_URL constant, passed explicitly below
            self.archive_queue = queue.Queue()
            self.archive_thread = weewx.restx.AmbientThread(
                self.archive_queue,
                _manager_dict,
                protocol_name="OgoxeUploader",
                server_url=OGOXE_API_URL,
                **_ambient_dict)
            self.archive_thread.start()
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
            log.info("OgoxeUploader: Data for station %s will be posted",
                     _ambient_dict.get('station', 'UNKNOWN'))

    def new_archive_record(self, event):
        """Puts new archive records in the archive queue"""
        self.archive_queue.put(event.record)
