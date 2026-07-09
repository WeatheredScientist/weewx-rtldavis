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

    def _filter_wind(self, packet):
        """Apply consistency check and delta filter to wind fields."""
        ws = packet.get('windSpeed')
        wg = packet.get('windGust')

        # --- Consistency check: gust must be >= speed ---
        if ws is not None and wg is not None:
            if wg < ws:
                log.warning(
                    "DewpointCacher: windGust %.1f < windSpeed %.1f "
                    "— corrupt packet, nulling both", wg, ws
                )
                packet['windSpeed'] = None
                packet['windGust']  = None
                return

        # --- Delta filter ---
        if ws is not None:
            if self.last_wind_speed is not None:
                delta = abs(ws - self.last_wind_speed)
                if delta > MAX_WIND_DELTA:
                    log.warning(
                        "DewpointCacher: rejecting windSpeed %.1f mph "
                        "(delta %.1f mph from last %.1f mph)",
                        ws, delta, self.last_wind_speed
                    )
                    packet['windSpeed'] = None
                    packet['windGust']  = None
                    return
                self.last_wind_speed = ws
            else:
                # Cold-start: accumulate warmup buffer before trusting delta filter
                # Null windSpeed during warmup — clean gap is better than stuck/wrong data
                self.wind_warmup.append(ws)
                if len(self.wind_warmup) >= WIND_WARMUP_PACKETS:
                    self.last_wind_speed = sum(self.wind_warmup) / len(self.wind_warmup)
                    self.wind_warmup = []
                    # Warmup complete — let this packet through with real values
                else:
                    # Still warming up — null wind fields for clean gap
                    packet['windSpeed'] = None
                    packet['windGust']  = None
                    packet['windDir']   = None
        # If windSpeed is None, pass it through as null.
        # Do NOT substitute last_wind_speed — a null is correct when the ISS
        # stops reporting wind (e.g. failed vane potentiometer), and a stale
        # substituted value is misleading and harder to diagnose than an honest null.

    def new_loop_packet(self, event):
        packet = event.packet
        now = packet.get('dateTime') or time.time()

        # Apply wind filters
        self._filter_wind(packet)

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
