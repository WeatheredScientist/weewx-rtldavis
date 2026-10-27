# SPDX-License-Identifier: GPL-3.0-or-later
"""
loop_json_writer.py
Eagle Hunt PWS — expanded LOOP packet JSON writer.
Writes all real-time fields to loop-data.txt on every LOOP packet (~2.5s
for Davis VP2+; a relative path resolves against WEEWX_ROOT, so the default is
/opt/weewx-data/loop-data.txt in the Docker image), and the same payload to a second path
(current.json) at a SLOWER, independent cadence. Atomic write via
tmp+rename on both.

THE TWO PATHS ARE NOT THE SAME KIND OF THING (DEC-0093, S84):

  loop-data.txt is a LIVE FEED. Its dateTime is a liveness signal behind a
  hard 30 s consumer gate -- the eh-proxy 503s past that and the dashboard
  reads the 503 as proof the station is down. Never throttle it, and never
  add "skip the write when nothing changed": on a calm night consecutive
  payloads are genuinely identical (wind_speed is set unconditionally, 0.0
  when calm), so suppression reports a healthy station as offline.

  current.json is a COLD-LOAD SNAPSHOT, read once at boot by a first-time
  visitor and replaced by the polling loop within one tick. Writing it per
  packet spent ~22,500 renames/day (half this service's total) refreshing a
  file nobody re-reads. Throttled to current_interval, default 60 s,
  confirmed by the consumer side in eaglehunt-weather-dashboard#430.

Set [LoopJsonWriter] current_interval = 0 to restore the old
write-on-every-packet behavior.

INSTALL: the WeeWX extension (extensions/loopjson/) puts this file in WeeWX's
  user directory and adds the service to process_services. Changing the file
  takes effect only after a WeeWX restart. If you run the published image and
  bind-mount your own copy over the one inside it, rebuilding the image does
  nothing: the image never copies this file, so update the mounted copy and
  restart the container.

Fields written (None → omitted, last known value used for sparse fields):
  windSpeed_mph, windGust_mph, windDir
  outTemp_F, dewpoint_F, outHumidity, heatindex_F, windchill_F
  barometer_inHg, rainRate_inch_per_hour
  radiation_Wpm2, UV, cloudbase_foot
  dateTime
  extra_fields (1.1.0, opt-in, DEC-0220): observations named in [LoopJsonWriter]
    extra_fields, written as <obs>_<unit label>; per-packet deltas are refused
  loop_interval_s (1.1.0, DEC-0221): median seconds between loop-data.txt writes
  barometer_fetch_epoch (#172 — passthrough, NOT cached/TTL'd; see new_loop)
  writer ("loop_json_writer/<__version__>", DEC-0211; semver against the
  contract: major = a key renamed, removed or given new units, minor = a new
  optional key, patch = a behavior fix)

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
import statistics
import time
from collections import deque
import weewx
import weewx.units
from weewx.engine import StdService

log = logging.getLogger(__name__)

# Contract version (DEC-0211), stamped into every write as the "writer" key.
# Keep it equal to extensions/loopjson/install.py's version; CI checks the pair
# against the release tag.
__version__ = '1.1.0'

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

# How often current.json is refreshed, INDEPENDENT of loop-data.txt (DEC-0093).
# current.json is a COLD-LOAD SNAPSHOT: the dashboard fetches it once at boot and
# the ~2.5 s /loopdata polling loop replaces it within one tick, so a first-time
# visitor's worst case is a first paint this many seconds stale. Writing it on
# every packet spent ~22,500 renames/day refreshing a file nobody re-reads.
# 60 s confirmed by the consumer side (eaglehunt-weather-dashboard#430).
#
# loop-data.txt is deliberately NOT throttled. Its dateTime is a LIVENESS signal
# sitting behind a hard 30 s consumer gate -- the eh-proxy 503s past that and the
# dashboard reads the 503 as proof the station is down -- so any delay there
# reports a healthy station as offline (INTERFACES §1). Do not reuse this knob
# for that path.
_CURRENT_INTERVAL_DEFAULT = 60

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

# Unit-label shortening for opt-in extra observations (DEC-0220). A copy of
# influx.py's UNIT_REDUCTIONS: this file ships as its own extension and cannot
# import it. tests/test_loop_json_extra_names.py fails if the two drift apart.
_UNIT_REDUCTIONS = {
    'degree_F': 'F',
    'degree_C': 'C',
    'inch': 'in',
    'mile_per_hour': 'mph',
    'mile_per_hour2': 'mph',
    'km_per_hour': 'kph',
    'km_per_hour2': 'kph',
    'knot': 'knot',
    'knot2': 'knot',
    'meter_per_second': 'mps',
    'meter_per_second2': 'mps',
    'degree_compass': None,
    'watt_per_meter_squared': 'Wpm2',
    'uv_index': None,
    'percent': None,
    'unix_epoch': None,
}


# Output keys an extra observation may not take: the writer stamps these itself.
_RESERVED_KEYS = frozenset(
    ['dateTime', 'writer', 'barometer_fetch_epoch', 'loop_interval_s'])


# loop_interval_s (DEC-0221): the median of up to this many gaps, reported inside the
# range the consumer accepts (dash DEC-0404).
_GAPS_KEPT = 32
_INTERVAL_MIN_S = 1
_INTERVAL_MAX_S = 3600

# Cumulative observations to suggest in place of a refused delta.
_CUMULATIVE_HINTS = {
    'lightning_strike_count': 'lightningcount',
    'rain': 'dayRain',
}


def _accumulator_defaults():
    """WeeWX's built-in [Accumulator] defaults ({} when weewx.accum is absent)."""
    try:
        import weewx.accum
        return weewx.accum.defaults_dict.get('Accumulator', {})
    except (ImportError, AttributeError):
        return {}


def _extra_key(obs):
    """Output key for an extra observation, by weewx-influx2's rule (DEC-0220):
    '<obs>_<label>', the label being the observation's US unit shortened by
    _UNIT_REDUCTIONS, and the bare name when the label reduces to None or the
    observation has no unit group. Read from the live registry, because drivers
    register their own groups (gw1000 adds luminosity)."""
    unit_type, _group = weewx.units.getStandardUnitType(weewx.US, obs)
    label = _UNIT_REDUCTIONS.get(unit_type, unit_type)
    return obs if label is None else '%s_%s' % (obs, label)


class LoopJsonWriter(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        cfg = config_dict.get('LoopJsonWriter', {})
        # Relative paths resolve against WEEWX_ROOT (always absolute at
        # runtime); an absolute path, as prod sets, passes through unchanged.
        root = config_dict.get('WEEWX_ROOT', '')
        self.path = os.path.join(root, cfg.get('path', 'loop-data.txt'))
        self.current_path = os.path.join(root, cfg.get('current_path', 'current.json'))
        for p in (self.path, self.current_path):
            out_dir = os.path.dirname(p)
            try:
                if out_dir:
                    os.makedirs(out_dir, exist_ok=True)
            except OSError as e:
                log.error('LoopJsonWriter: cannot create %s: %s' % (out_dir, e))
        self.ttl_default = int(cfg.get('ttl_default', _TTL_DEFAULT_SECONDS))
        # The long barometer TTL exists because DavisPressureFetcher refreshes
        # it only every fetch_interval. Without that section the barometer is
        # an ordinary loop field, so it takes ttl_default instead of a 7,200 s
        # default that would serve a dead barometer stale for two hours.
        self.ttls = {}
        if 'DavisPressure' in config_dict:
            fetch_interval = int(config_dict['DavisPressure'].get(
                'fetch_interval', _BAROMETER_FETCH_DEFAULT))
            self.ttls[_BAROMETER_KEY] = _BAROMETER_TTL_FACTOR * fetch_interval
        # current.json cadence (DEC-0093). 0 (or negative) restores the old
        # write-on-every-packet behavior, which is what shipped S43-S84.
        self.current_interval = int(cfg.get('current_interval',
                                            _CURRENT_INTERVAL_DEFAULT))
        self._current_last = None  # timestamp of last current.json write
        # Cache of last known good values — VP2+ rotates fields across packets
        # so not every field appears in every packet. We keep the most recent
        # non-None value for each field, with the time we saw it, and include it
        # in every write until it exceeds its TTL (see module docstring).
        self.extras = self._parse_extras(cfg)  # [(observation, out_key)]
        # StdArchive builds WeeWX's accumulator map after the process services
        # (this one) are constructed, so the delta check reads the site's own
        # [Accumulator] section from the config, at the first packet (DEC-0220).
        self._accumulator_cfg = config_dict.get('Accumulator', {})
        self._deltas_checked = False
        # loop_interval_s (DEC-0221): seconds between consecutive SUCCESSFUL
        # writes of loop-data.txt, on a monotonic clock, as the median of the
        # last _GAPS_KEPT gaps. A gap is known only after the write that ends
        # it, so the key first appears in the third file written.
        self._clock = time.monotonic
        self._last_write = None
        self._gaps = deque(maxlen=_GAPS_KEPT)
        self._cache = {}      # out_key -> (value, timestamp last seen)
        self._expired = set()  # out_keys currently expired, for one-shot logging
        # out_keys whose current expiry was the benign calm-windDir case
        # (issue #74): logged at DEBUG, so the matching recovery line must
        # be DEBUG too or the noise just moves down a level
        self._expired_calm = set()
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop)
        log.info('LoopJsonWriter: writing to %s every packet and %s every %s '
                 '(cache TTL %d s, %s %d s)'
                 % (self.path, self.current_path,
                    ('%d s' % self.current_interval)
                    if self.current_interval > 0 else 'packet',
                    self.ttl_default, _BAROMETER_KEY,
                    self._ttl(_BAROMETER_KEY)))

    def _parse_extras(self, cfg):
        """Read [LoopJsonWriter] extra_fields and [[ttl]] (DEC-0220 items 1-3).

        Returns [(observation, out_key)]. Every refusal is one WARNING (an
        ignored duplicate is INFO), never an exception: a typo in this opt-in
        list must not stop the 13 standard fields. A [[ttl]] entry lands in
        self.ttls under the output key, next to the barometer's."""
        names = cfg.get('extra_fields', [])
        if isinstance(names, str):
            names = [names]
        existing = {out_key for _pkt_key, out_key in _FIELDS}
        taken = {}      # out_key -> observation that claimed it
        extras = []
        for obs in (n.strip() for n in names):
            if not obs:
                continue
            try:
                out_key = _extra_key(obs)
            except Exception as e:
                log.warning('LoopJsonWriter: extra_fields %s skipped, cannot name '
                            'it: %s' % (obs, e))
                continue
            if out_key in _RESERVED_KEYS:
                log.warning('LoopJsonWriter: extra_fields %s skipped, %s is a key '
                            'the writer stamps itself' % (obs, out_key))
            elif out_key in existing:
                log.info('LoopJsonWriter: extra_fields %s ignored, %s is already '
                         'written' % (obs, out_key))
            elif out_key in taken:
                log.warning('LoopJsonWriter: extra_fields %s skipped, %s already '
                            'comes from %s' % (obs, out_key, taken[out_key]))
            else:
                taken[out_key] = obs
                extras.append((obs, out_key))
        by_obs = dict(extras)
        ttl_cfg = cfg.get('ttl', {})
        for obs in ttl_cfg:
            if obs not in by_obs:
                log.warning('LoopJsonWriter: [[ttl]] %s ignored, it is not a '
                            'configured extra field' % obs)
                continue
            try:
                self.ttls[by_obs[obs]] = int(ttl_cfg[obs])
            except (TypeError, ValueError):
                log.warning('LoopJsonWriter: [[ttl]] %s = %r is not a number of '
                            'seconds, using %d' % (obs, ttl_cfg[obs], self.ttl_default))
        return extras

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

    def _note_write(self):
        """Record a successful loop-data.txt write; the clock is read after
        os.replace returns, so a failed write adds no gap and resets nothing."""
        now = self._clock()
        if self._last_write is not None:
            self._gaps.append(now - self._last_write)
        self._last_write = now

    def _loop_interval(self):
        """The median gap rounded to one decimal, or None when no gap exists or
        the rounded value falls outside [1, 3600] s. Omitted, never clamped: a
        clamped value would state a cadence the station does not have, and the
        consumer (dash DEC-0404) already falls back for a missing key."""
        if not self._gaps:
            return None
        value = round(statistics.median(self._gaps), 1)
        if _INTERVAL_MIN_S <= value <= _INTERVAL_MAX_S:
            return value
        return None

    def _extractor(self, obs):
        """Accumulator extractor for obs: the site's [Accumulator] first, then
        WeeWX's own defaults, else None (the observation takes the 'last'
        default, a state)."""
        for table in (self._accumulator_cfg, _accumulator_defaults()):
            entry = table.get(obs)
            if hasattr(entry, 'get') and entry.get('extractor'):
                return entry.get('extractor')
        return None

    def _refuse_deltas(self):
        """Drop every extra whose extractor is 'sum' (DEC-0220 item 3).

        Such an observation is a per-packet delta (rain, lightning_strike_count,
        a driver's t_rain). The file is overwritten in place and read on the
        consumer's clock, so a delta would be counted twice or not at all."""
        kept = []
        for obs, out_key in self.extras:
            if self._extractor(obs) == 'sum':
                hint = _CUMULATIVE_HINTS.get(
                    obs, 'its cumulative counterpart, if the driver has one')
                log.warning('LoopJsonWriter: extra_fields %s refused, it is a '
                            'per-packet delta (accumulator extractor sum) that '
                            'this file cannot deliver exactly once; list %s '
                            'instead' % (obs, hint))
            else:
                kept.append((obs, out_key))
        self.extras = kept
        self._deltas_checked = True

    def new_loop(self, event):
        if not self._deltas_checked:
            self._refuse_deltas()
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

        # Update cache with any non-None values from this packet. The opt-in
        # extras (DEC-0220) share the cache, its TTLs and the expiry warning
        # with the 13 standard fields; there is no second code path.
        for pkt_key, out_key in _FIELDS + self.extras:
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
        # barometer_fetch_epoch (#172) bypasses the cache/TTL machinery on
        # purpose: barometer_inHg is a WeatherLink-API relay (INTERFACES §1),
        # and this is the epoch of the last fetch that actually succeeded --
        # its entire job is to REVEAL staleness, so omitting it for being old
        # would recreate the exact gap it exists to close. pressure_service
        # stamps it into every packet once one fetch has succeeded; absent
        # before then (consumers already treat every field as possibly-missing).
        fe = pkt.get('barometer_fetch_epoch')
        if fe is not None:
            data['barometer_fetch_epoch'] = fe
        data['dateTime'] = pkt.get('dateTime')
        data['writer'] = 'loop_json_writer/' + __version__
        interval = self._loop_interval()
        if interval is not None:
            data['loop_interval_s'] = interval

        # loop-data.txt on EVERY packet -- it carries the liveness signal.
        # current.json only when its interval has elapsed (DEC-0093). The first
        # packet of a run always writes it, so a restart has a snapshot
        # immediately rather than serving whatever the previous run left behind.
        paths = [self.path]
        if self._current_due(now):
            paths.append(self.current_path)

        for path in paths:
            tmp = path + '.tmp'
            try:
                with open(tmp, 'w') as f:
                    json.dump(data, f)
                os.replace(tmp, path)
                if path == self.path:
                    self._note_write()
                if path == self.current_path:
                    # only on success -- a failed write retries next packet
                    self._current_last = now
            except Exception as e:
                log.error('LoopJsonWriter: failed to write %s: %s' % (path, e))

    def _current_due(self, now):
        """True when current.json should be refreshed this packet.

        Writes when never written this run, when throttling is disabled, or
        when the interval has elapsed. A NEGATIVE elapsed also writes: packet
        clocks can step backwards (a corrected station clock, or the wall-clock
        fallback in new_loop), and treating that as 'not yet due' would stall
        the snapshot until real time caught up.
        """
        if self.current_interval <= 0 or self._current_last is None:
            return True
        elapsed = now - self._current_last
        return not (0 <= elapsed < self.current_interval)
