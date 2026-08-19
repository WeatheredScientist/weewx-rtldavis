import time

import weewx
from weewx.engine import StdService
import weewx.wxformulas
import logging

log = logging.getLogger(__name__)

# Maximum plausible wind speed change per LOOP packet (2.5 seconds)
# Based on Davis anemometer response time and worst-case meteorological events
# 75 mph/sample = 1800 mph/min -- already well beyond any real event
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


class DewpointCacher(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        self.cache = {}              # field -> (value, time last seen)
        self.cache_timeout    = CACHE_TIMEOUT_SECONDS
        self.last_wind_speed  = None
        self.last_wind_time   = None # when last_wind_speed was accepted/resynced
        self.wind_warmup      = []   # short buffer for cold-start seeding
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

        # --- Bounds: each reading must be physically possible on its own ---
        # Checked independently per field, not gated on windSpeed being present:
        # this service is driver-agnostic by design (docs/INTERFACES.md), and a
        # driver that reports a gust without a speed must not go unguarded. The
        # current driver never does, so this is a contract guard, not a live path.
        for field, value in (('windSpeed', ws), ('windGust', wg)):
            if value is not None and not 0.0 <= value <= MAX_PLAUSIBLE_WIND_SPEED:
                log.warning(
                    "DewpointCacher: %s %.1f mph outside 0..%.0f "
                    "— corrupt packet, nulling wind", field, value,
                    MAX_PLAUSIBLE_WIND_SPEED
                )
                self._null_wind(packet)
                return

        # --- Bounds: gust must be >= speed ---
        if ws is not None and wg is not None and wg < ws:
            log.warning(
                "DewpointCacher: windGust %.1f < windSpeed %.1f "
                "— corrupt packet, nulling wind", wg, ws
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
            if delta > MAX_WIND_DELTA:
                log.warning(
                    "DewpointCacher: rejecting windSpeed %.1f mph "
                    "(delta %.1f mph from last %.1f mph)", ws, delta, last
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
            packet['dewpoint']  = weewx.wxformulas.dewpointF(temp, humidity)
            packet['heatindex'] = weewx.wxformulas.heatindexF(temp, humidity)
