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


class DewpointCacher(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        self.last_temp        = None
        self.last_humidity    = None
        self.last_radiation   = None
        self.last_uv          = None
        self.last_wind_speed  = None
        self.wind_warmup      = []   # short buffer for cold-start seeding
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

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
                self.wind_warmup.append(ws)
                if len(self.wind_warmup) >= WIND_WARMUP_PACKETS:
                    self.last_wind_speed = sum(self.wind_warmup) / len(self.wind_warmup)
                    self.wind_warmup = []
        elif self.last_wind_speed is not None:
            packet['windSpeed'] = self.last_wind_speed

    def new_loop_packet(self, event):
        packet = event.packet

        # Apply wind filters
        self._filter_wind(packet)

        # Update cache with any new values
        if packet.get('outTemp') is not None:
            self.last_temp = packet['outTemp']
        if packet.get('outHumidity') is not None:
            self.last_humidity = packet['outHumidity']
        if packet.get('radiation') is not None:
            self.last_radiation = packet['radiation']
        if packet.get('UV') is not None:
            self.last_uv = packet['UV']

        # Inject cached values
        if packet.get('outTemp') is None and self.last_temp is not None:
            packet['outTemp'] = self.last_temp
        if packet.get('outHumidity') is None and self.last_humidity is not None:
            packet['outHumidity'] = self.last_humidity
        if packet.get('radiation') is None and self.last_radiation is not None:
            packet['radiation'] = self.last_radiation
        if packet.get('UV') is None and self.last_uv is not None:
            packet['UV'] = self.last_uv

        # Calculate dewpoint and heatindex if we have both values
        if self.last_temp is not None and self.last_humidity is not None:
            packet['dewpoint']  = weewx.wxformulas.dewpointF(self.last_temp, self.last_humidity)
            packet['heatindex'] = weewx.wxformulas.heatindexF(self.last_temp, self.last_humidity)
