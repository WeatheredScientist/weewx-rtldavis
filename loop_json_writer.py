# SPDX-License-Identifier: GPL-3.0-or-later
"""
loop_json_writer.py
Eagle Hunt PWS — expanded LOOP packet JSON writer.
Writes all real-time fields to /opt/weewx-data/loop-data.txt on every
LOOP packet (~2.5s for Davis VP2+). Atomic write via tmp+rename.

Fields written (None → omitted, last known value used for sparse fields):
  windSpeed_mph, windGust_mph, windDir
  outTemp_F, dewpoint_F, outHumidity, heatindex_F
  barometer_inHg, rainRate_inch_per_hour
  radiation_Wpm2, UV, cloudbase_foot
  dateTime

NOTE: Packet is explicitly normalized to US (imperial) units before extraction
so that output key names (outTemp_F, barometer_inHg, etc.) always reflect
actual unit system, regardless of WeeWX's internal unit configuration.
"""
import json
import logging
import os
import weewx
import weewx.units
from weewx.engine import StdService

log = logging.getLogger(__name__)

# Fields to capture from each LOOP packet.
# Tuple: (packet_key, output_key)
# Packet is converted to US units first, so these mappings are always correct.
_FIELDS = [
    ('windSpeed',            'windSpeed_mph'),
    ('windGust',             'windGust_mph'),
    ('windDir',              'windDir'),
    ('outTemp',              'outTemp_F'),
    ('dewpoint',             'dewpoint_F'),
    ('outHumidity',          'outHumidity'),
    ('heatindex',            'heatindex_F'),
    ('barometer',            'barometer_inHg'),
    ('rainRate',             'rainRate_inch_per_hour'),
    ('radiation',            'radiation_Wpm2'),
    ('UV',                   'UV'),
    ('cloudbase',            'cloudbase_foot'),
]


class LoopJsonWriter(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        cfg = config_dict.get('LoopJsonWriter', {})
        self.path = cfg.get('path', '/opt/weewx-data/loop-data.txt')
        # Cache of last known good values — VP2+ rotates fields across packets
        # so not every field appears in every packet. We keep the most recent
        # non-None value for each field and include it in every write.
        self._cache = {}
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop)
        log.info('LoopJsonWriter: writing to %s' % self.path)

    def new_loop(self, event):
        pkt = event.packet

        # Normalize to US (imperial) units so output keys match their names.
        # to_US() is a no-op if the packet is already US; safe to always call.
        try:
            pkt = weewx.units.to_US(pkt)
        except Exception as e:
            log.warning('LoopJsonWriter: unit conversion failed, using raw packet: %s' % e)

        # Update cache with any non-None values from this packet
        for pkt_key, out_key in _FIELDS:
            val = pkt.get(pkt_key)
            if val is not None:
                self._cache[out_key] = val

        # Build output: cached values + current timestamp
        data = dict(self._cache)
        data['dateTime'] = pkt.get('dateTime')

        tmp = self.path + '.tmp'
        try:
            with open(tmp, 'w') as f:
                json.dump(data, f)
            os.replace(tmp, self.path)
        except Exception as e:
            log.error('LoopJsonWriter: failed to write %s: %s' % (self.path, e))
