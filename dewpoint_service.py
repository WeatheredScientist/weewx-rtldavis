import time

import weewx
from weewx.engine import StdService
import weewx.wxformulas
import logging

log = logging.getLogger(__name__)

# Maximum plausible wind speed change per LOOP packet (2.5 seconds)
# Based on Davis anemometer response time and worst-case meteorological events
# 75 mph/sample = 1800 mph/min -- already well beyond any real event
# STATED IN MPH: readings are converted to mph before the test (#224, _WIND_TO_MPH),
# because under target_unit=METRIC/METRICWX the packet carries km/h or m/s.
MAX_WIND_DELTA = 75.0

# Number of packets to collect before trusting last_wind_speed for delta filter
# Prevents cold-start acceptance of corrupted first packet after a gap
WIND_WARMUP_PACKETS = 3

# Absolute plausibility bound for a single wind reading, mph -- the 6410's own
# spec ceiling (rtldavis.py's SENSOR_QC_DEFAULTS carries the same limit, stated
# there as 89.4 m/s). This is a BOUNDS test, not a delta test, and the two are
# deliberately different things: a reading outside this range is positive proof
# of corruption and carries no information, whereas a large delta may be a
# genuine gust front. Only the former is safe to treat as "learn nothing from
# this packet" (DEC-0054, and SensorQC.check()'s same split).
# STATED IN MPH, converted at the point of use (#224). Left uncorrected this
# bound fails in BOTH directions: read as m/s it is ~447 mph and the guard is
# inert, read as km/h it is ~124 mph and the guard starts nulling real readings.
MAX_PLAUSIBLE_WIND_SPEED = 200.0

# How long last_wind_speed may serve as a delta baseline before it is treated as
# absent and reseeded from the current reading with no delta test. Mirrors
# rtldavis.py's QC_RESEED_SECONDS (300) and this file's own CACHE_TIMEOUT_SECONDS:
# after a reception gap that long, the "last" reading describes a different
# weather situation, and judging a new reading against it is measuring the wrong
# thing. Without this, a stale baseline plus a rejected step deadlocks the filter.
WIND_BASELINE_TTL_SECONDS = 300

# How long a cached temp/humidity/radiation/UV value may substitute for a
# missing reading before it expires to an honest null (DEC-0022, S33). The
# ISS rotates these sensors across message types (one reading each ~25-60 s
# at this station's reception), so a short cache bridges rotation gaps --
# "absent this packet" is normal, not a failure. But a sensor silent for
# longer than this IS failing (or its readings are being rejected), and a
# stale substituted value masks that indefinitely (the DEC-0006 violation
# that hid night-time humidity glitches nulled by StdQC). After the timeout
# the field goes null and dewpoint/heatindex stop being computed from it.
CACHE_TIMEOUT_SECONDS = 300

# LOOP fields bridged across the ISS message-type rotation
CACHED_FIELDS = ('outTemp', 'outHumidity', 'radiation', 'UV')

# --- Unit systems (#224) ----------------------------------------------------
# This service runs in process_services, AFTER StdConvert, so every packet
# arrives already in the configured target_unit: US (degF, mph), METRIC (degC,
# km/h) or METRICWX (degC, m/s). Nothing below may assume US. `target_unit` is a
# documented option in this repo's own weewx.conf.example, and the shipped
# default (US) is the only reason an unconditional Fahrenheit assumption
# survived here as long as it did.
#
# Comparisons against these keys are SYMBOLIC (`weewx.US`, never the integer) so
# this file never depends on weewx's constant VALUES -- which is also what lets
# the offline test stubs pick their own without the code noticing.
#
# StdConvert normalises every packet to one system for the life of the process,
# so `last_wind_speed` (held in packet units) cannot go mixed-unit mid-run:
# changing target_unit is a config edit and needs a restart.

# Factor converting a packet's windSpeed/windGust to mph -- the unit the two
# wind thresholds are documented in, and the unit the 6410's spec ceiling is
# quoted in. Converting the READING rather than the thresholds keeps ONE
# documented constant set instead of three that would have to be kept in sync.
_WIND_TO_MPH = {
    weewx.US:       1.0,        # already mph
    weewx.METRIC:   0.621371,   # km/h -> mph
    weewx.METRICWX: 2.2369363,  # m/s  -> mph
}

# So a rejection is logged in the units the reading was actually taken in.
_WIND_LABEL = {
    weewx.US:       'mph',
    weewx.METRIC:   'km/h',
    weewx.METRICWX: 'm/s',
}


class DewpointCacher(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        self.cache = {}              # field -> (value, time last seen)
        self.cache_timeout    = CACHE_TIMEOUT_SECONDS
        self.last_wind_speed  = None
        self.last_wind_time   = None # when last_wind_speed was accepted/resynced
        self.wind_warmup      = []   # short buffer for cold-start seeding
        self._warned_units    = False  # usUnits complaint is once-per-run, #224
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

    def _cache_get(self, field, now):
        """Cached value for field, or None if absent or older than the timeout."""
        entry = self.cache.get(field)
        if entry is None:
            return None
        value, seen = entry
        if now - seen > self.cache_timeout:
            return None
        return value

    def _packet_units(self, packet):
        """The packet's unit system, falling back to US if it is missing/unknown.

        Falling back to US reproduces the pre-#224 behaviour EXACTLY, so this fix
        cannot regress the shipped default (target_unit=US) even if a packet turns
        up without usUnits. That is a contract violation by whatever produced the
        packet, though, so it is said out loud -- once per run, because a LOOP-rate
        warning is its own outage (DEC-0043's logging-error class).
        """
        us = packet.get('usUnits')
        if us in _WIND_TO_MPH:
            return us
        if not self._warned_units:
            log.warning(
                "DewpointCacher: packet has no usable usUnits (%r) — assuming US. "
                "dewpoint/heatindex and the wind bounds are unit-sensitive (#224)",
                us
            )
            self._warned_units = True
        return weewx.US

    def _null_wind(self, packet):
        """Null the whole wind triple, direction included.

        Speed and direction ride adjacent bytes of the same reading, so whatever
        corrupted one is equally suspect in the other -- the convention the
        driver already applies both on QC rejection ("the same-packet direction
        byte is equally suspect", rtldavis.py) and at its calm-air gate. Leaving
        windDir behind publishes a bare heading with no speed to loop-JSON,
        InfluxDB and every uploader, which reads downstream as real wind.
        """
        packet['windSpeed'] = None
        packet['windGust']  = None
        packet['windDir']   = None

    def _filter_wind(self, packet, now=None):
        """Apply bounds and delta plausibility checks to the wind triple.

        Two classes of rejection, with deliberately different baseline handling
        -- the split rtldavis.py's SensorQC.check() and DEC-0054 already settled
        for the decode layer, ported here rather than imported so this service
        keeps its zero coupling to the driver (docs/INTERFACES.md):

          * BOUNDS -- an impossible reading (outside sensor range, or a gust
            below its own speed). Positive proof of corruption, so the value
            carries no information and the baseline is left UNTOUCHED.
          * DELTA -- an implausibly large step from the last accepted reading.
            The reading may be a genuine gust front, so the baseline ALWAYS
            resyncs to it: the step is rejected once, and the next reading is
            judged against current reality instead of a frozen past. Without
            that resync a rejected step freezes the baseline permanently and
            every later reading is rejected against it until weewx restarts.
        """
        if now is None:
            now = time.time()

        ws = packet.get('windSpeed')
        wg = packet.get('windGust')

        # Both thresholds are documented in mph, so every comparison below runs
        # on the mph-normalised value while the PACKET keeps its own units (#224).
        units  = self._packet_units(packet)
        to_mph = _WIND_TO_MPH[units]
        label  = _WIND_LABEL[units]

        # --- Bounds: each reading must be physically possible on its own ---
        # Checked independently per field, not gated on windSpeed being present:
        # this service is driver-agnostic by design (docs/INTERFACES.md), and a
        # driver that reports a gust without a speed must not go unguarded. The
        # current driver never does, so this is a contract guard, not a live path.
        for field, value in (('windSpeed', ws), ('windGust', wg)):
            if value is not None and not 0.0 <= value * to_mph <= MAX_PLAUSIBLE_WIND_SPEED:
                log.warning(
                    "DewpointCacher: %s %.1f %s outside 0..%.0f mph "
                    "— corrupt packet, nulling wind", field, value, label,
                    MAX_PLAUSIBLE_WIND_SPEED
                )
                self._null_wind(packet)
                return

        # --- Bounds: gust must be >= speed ---
        # No conversion needed: both sides are the same field's own unit system.
        if ws is not None and wg is not None and wg < ws:
            log.warning(
                "DewpointCacher: windGust %.1f < windSpeed %.1f %s "
                "— corrupt packet, nulling wind", wg, ws, label
            )
            self._null_wind(packet)
            return

        if ws is None:
            # Pass the null through untouched. Do NOT substitute last_wind_speed
            # -- a null is correct when the ISS stops reporting wind (e.g. failed
            # vane potentiometer), and a stale substituted value is misleading and
            # harder to diagnose than an honest null (DEC-0006).
            return

        # --- Delta ---
        if self.last_wind_speed is not None:
            # An unknown-age baseline counts as fresh: absent evidence it is
            # stale, keep filtering rather than waving the reading through.
            if (self.last_wind_time is not None
                    and now - self.last_wind_time > WIND_BASELINE_TTL_SECONDS):
                # Baseline outlived the TTL -- it describes an older weather
                # situation. Reseed from this reading with no delta test.
                self.last_wind_speed = ws
                self.last_wind_time  = now
                return
            last  = self.last_wind_speed
            delta = abs(ws - last)
            # Resync ALWAYS, before deciding: on reject too. A genuine sustained
            # step is then accepted on the very next reading (no deadlock).
            self.last_wind_speed = ws
            self.last_wind_time  = now
            if delta * to_mph > MAX_WIND_DELTA:
                log.warning(
                    "DewpointCacher: rejecting windSpeed %.1f %s "
                    "(delta %.1f from last %.1f, limit %.0f mph)",
                    ws, label, delta, last, MAX_WIND_DELTA
                )
                self._null_wind(packet)
            return

        # --- Cold start: seed the baseline from an averaged warmup buffer ---
        # Every sample reaching here has already passed the bounds test above, so
        # a reading impossible per sensor spec can no longer seed the baseline
        # and hand the delta filter a wrong reference to reject real wind against.
        self.wind_warmup.append(ws)
        if len(self.wind_warmup) >= WIND_WARMUP_PACKETS:
            self.last_wind_speed = sum(self.wind_warmup) / len(self.wind_warmup)
            self.last_wind_time  = now
            self.wind_warmup     = []
            # Warmup complete -- let this packet through with real values
        else:
            # Still warming up -- null the triple for a clean gap
            self._null_wind(packet)

    def new_loop_packet(self, event):
        packet = event.packet
        now = packet.get('dateTime') or time.time()

        # Apply wind filters -- same clock the field cache uses, so a replayed
        # or backfilled packet ages the wind baseline by its own dateTime
        self._filter_wind(packet, now)

        # Update cache with any new values
        for field in CACHED_FIELDS:
            if packet.get(field) is not None:
                self.cache[field] = (packet[field], now)

        # Inject cached values to bridge the message-type rotation -- but only
        # while fresh; after CACHE_TIMEOUT_SECONDS of sensor silence the field
        # stays an honest null instead of a stale substitute (DEC-0022)
        for field in CACHED_FIELDS:
            if packet.get(field) is None:
                cached = self._cache_get(field, now)
                if cached is not None:
                    packet[field] = cached

        # Calculate dewpoint and heatindex only from fresh values -- a stale
        # temp or humidity would fabricate a stale dewpoint too
        temp = self._cache_get('outTemp', now)
        humidity = self._cache_get('outHumidity', now)
        if temp is not None and humidity is not None:
            # Branch on the packet's unit system rather than converting it, the way
            # WeeWX's own wxxtypes.py does (#224). The tempting alternative --
            # loop_json_writer.py's weewx.units.to_US(pkt) -- does NOT transfer to
            # this file: that service EMITS US-suffixed fields and so never converts
            # back, whereas this one writes into the LIVE packet, which has to stay
            # in its own system. A to_US() fix that forgot the return trip would put
            # degF into a metric packet -- the same bug, moved one layer along.
            # METRIC and METRICWX both carry outTemp in degC, so they share a branch.
            if self._packet_units(packet) == weewx.US:
                packet['dewpoint']  = weewx.wxformulas.dewpointF(temp, humidity)
                packet['heatindex'] = weewx.wxformulas.heatindexF(temp, humidity)
            else:
                packet['dewpoint']  = weewx.wxformulas.dewpointC(temp, humidity)
                packet['heatindex'] = weewx.wxformulas.heatindexC(temp, humidity)
