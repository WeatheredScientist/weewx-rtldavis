# SPDX-License-Identifier: GPL-3.0-or-later
"""
loop_json_writer.py
Eagle Hunt PWS — expanded LOOP packet JSON writer.
Writes all real-time fields to /opt/weewx-data/loop-data.txt on every
LOOP packet (~2.5s for Davis VP2+), and atomically to a second path
(current.json) that the dashboard fetches first at boot so a first-time
visitor doesn't see em-dashes (Cold-load Fix B). Both writes carry identical
content; only the destination path differs. Atomic write via tmp+rename.

Fields written (None → omitted, last known value used for sparse fields):
  windSpeed_mph, windGust_mph, windDir
  outTemp_F, dewpoint_F, outHumidity, heatindex_F, windchill_F
  barometer_inHg, rainRate_inch_per_hour
  radiation_Wpm2, UV, cloudbase_foot
  dateTime

NOTE: Packet is explicitly normalized to US (imperial) units before extraction
so that output key names (outTemp_F, barometer_inHg, etc.) always reflect
actual unit system, regardless of WeeWX's internal unit configuration.

CACHE EXPIRY (DEC-0006, added S48 from the issue #45 provenance audit): the
cached-forward value for a field is BOUNDED. Every write stamps the *current*
packet's dateTime, so a field served from cache is implicitly claiming to be
current. With an unbounded cache a dead -- or SensorQC-rejected -- sensor kept
emitting its last value forever, indistinguishable from a live reading, on the
surface the dashboard actually reads. That is the same "a stale substituted
value masks that indefinitely" failure dewpoint_service.py fixed for the
archive path at S33/DEC-0022. Past its TTL a field is OMITTED rather than
served stale; consumers already must treat any field as possibly-missing
(INTERFACES §1), so this is contract-compatible.
"""
import json
import logging
import os
import time
import weewx
import weewx.units
from weewx.engine import StdService

log = logging.getLogger(__name__)

# How long a cached value may stand in for a missing reading. The ISS rotates
# its sensors across message types (one reading each ~25-60 s at this station's
# reception), so a short cache bridges rotation gaps -- "absent this packet" is
# normal. 300 s matches dewpoint_service.CACHE_TIMEOUT_SECONDS, which has run
# in prod over exactly these fields since S33.
_TTL_DEFAULT_SECONDS = 300

# barometer is NOT on the ISS rotation -- it comes from DavisPressureFetcher's
# periodic WeatherLink API fetch (fetch_interval, default 3600 s), so the
# default TTL would blank it for most of every hour and regress Cold-load Fix B.
# Derived from that service's own config so the two cannot drift apart.
_BAROMETER_KEY = 'barometer_inHg'
_BAROMETER_TTL_FACTOR = 2
_BAROMETER_FETCH_DEFAULT = 3600

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
    ('windchill',            'windchill_F'),
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
        self.current_path = cfg.get('current_path', '/opt/weewx-data/current.json')
        self.ttl_default = int(cfg.get('ttl_default', _TTL_DEFAULT_SECONDS))
        fetch_interval = int(config_dict.get('DavisPressure', {}).get(
            'fetch_interval', _BAROMETER_FETCH_DEFAULT))
        self.ttls = {_BAROMETER_KEY: _BAROMETER_TTL_FACTOR * fetch_interval}
        # Cache of last known good values — VP2+ rotates fields across packets
        # so not every field appears in every packet. We keep the most recent
        # non-None value for each field, with the time we saw it, and include it
        # in every write until it exceeds its TTL (see module docstring).
        self._cache = {}      # out_key -> (value, timestamp last seen)
        self._expired = set()  # out_keys currently expired, for one-shot logging
        # out_keys whose current expiry was the benign calm-windDir case
        # (issue #74): logged at DEBUG, so the matching recovery line must
        # be DEBUG too or the noise just moves down a level
        self._expired_calm = set()
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop)
        log.info('LoopJsonWriter: writing to %s and %s (cache TTL %d s, %s %d s)'
                 % (self.path, self.current_path, self.ttl_default,
                    _BAROMETER_KEY, self.ttls[_BAROMETER_KEY]))

    def _ttl(self, out_key):
        """Seconds a cached value for out_key may still be served."""
        return self.ttls.get(out_key, self.ttl_default)

    def _calm(self, now):
        """True when the current (unexpired) windSpeed reading is 0.0 —
        the calm-windDir expiry case of issue #74. An expired or absent
        windSpeed is NOT calm: that is a real dropout and deserves the
        WARNING."""
        cached = self._cache.get('windSpeed_mph')
        if cached is None:
            return False
        val, seen = cached
        return val == 0.0 and (now - seen) <= self._ttl('windSpeed_mph')

    def new_loop(self, event):
        pkt = event.packet

        # Normalize to US (imperial) units so output keys match their names.
        # to_US() is a no-op if the packet is already US; safe to always call.
        try:
            pkt = weewx.units.to_US(pkt)
        except Exception as e:
            log.warning('LoopJsonWriter: unit conversion failed, using raw packet: %s' % e)

        # Clock: the packet's own time, falling back to wall clock — the same
        # idiom dewpoint_service.py uses, so the two caches age identically.
        now = pkt.get('dateTime') or time.time()

        # Update cache with any non-None values from this packet
        for pkt_key, out_key in _FIELDS:
            val = pkt.get(pkt_key)
            if val is not None:
                self._cache[out_key] = (val, now)
                if out_key in self._expired:
                    self._expired.discard(out_key)
                    if out_key in self._expired_calm:
                        # benign calm-expiry (issue #74): wind picked back up
                        self._expired_calm.discard(out_key)
                        log.debug('LoopJsonWriter: %s recovered, serving live '
                                  'values again' % out_key)
                    else:
                        log.info('LoopJsonWriter: %s recovered, serving live '
                                 'values again' % out_key)

        # Build output: unexpired cached values + current timestamp. A field
        # past its TTL is omitted, never served stale under a live dateTime.
        data = {}
        for out_key, (val, seen) in self._cache.items():
            age = now - seen
            if age <= self._ttl(out_key):
                data[out_key] = val
            elif out_key not in self._expired:
                self._expired.add(out_key)
                if out_key == 'windDir' and self._calm(now):
                    # issue #74: the driver deliberately reports wind_dir =
                    # None while calm (no direction exists without wind), so
                    # any >= TTL calm stretch expires windDir by design --
                    # a healthy sensor correctly omitting, not a fault.
                    # windDir expiry with nonzero windSpeed stays a WARNING.
                    self._expired_calm.add(out_key)
                    log.debug('LoopJsonWriter: windDir expired after %.0f s '
                              '(TTL %d s) during calm (windSpeed 0.0) — '
                              'no direction exists without wind (#74)'
                              % (age, self._ttl(out_key)))
                else:
                    log.warning('LoopJsonWriter: %s expired after %.0f s (TTL %d s) — '
                                'omitting rather than serving a stale value under a '
                                'live timestamp; sensor may be failing or rejected'
                                % (out_key, age, self._ttl(out_key)))
        data['dateTime'] = pkt.get('dateTime')

        for path in (self.path, self.current_path):
            tmp = path + '.tmp'
            try:
                with open(tmp, 'w') as f:
                    json.dump(data, f)
                os.replace(tmp, path)
            except Exception as e:
                log.error('LoopJsonWriter: failed to write %s: %s' % (path, e))
