import hmac
import hashlib
import time
import threading
import weewx
import weewx.units
from weewx.engine import StdService
import logging

log = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    log.error("requests module not available")

class DavisPressureFetcher(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        pressure_dict = config_dict.get('DavisPressure', {})
        self.api_key = pressure_dict.get('api_key', '')
        self.api_secret = pressure_dict.get('api_secret', '')
        self.station_id = int(pressure_dict.get('station_id', 0))
        self.fetch_interval = int(pressure_dict.get('fetch_interval', 3600))
        self.last_pressure = None
        self.last_fetch = 0        # throttle stamp: set at every ATTEMPT, success or not
        self.last_success = None   # epoch of the last fetch that actually yielded a value (#172)
        # S57b: never log key material, not even a prefix. This line used to log
        # api_key[:8], putting 8 characters of the live WeatherLink key into
        # weewx.log -- and its 30 daily rotations -- on EVERY startup. weewx.log
        # is not covered by the DEC-0047 read-guard (which guards configs), so a
        # routine "tail the log to check the restart was clean" pulls it into an
        # agent transcript; that happened twice on 2026-07-29. The diagnostic
        # intent was "did the credentials load?" -- which this answers better,
        # since it now distinguishes WHICH one is missing, and leaks nothing.
        # The presence flags are resolved BEFORE the log call, so no credential
        # attribute appears in a log argument at all. That keeps the invariant
        # the test enforces simple and absolute -- "no credential in any log
        # call" -- instead of needing a checker that reasons about which uses
        # are safe. A checker with exceptions is a weaker checker.
        key_state = "present" if self.api_key else "MISSING"
        secret_state = "present" if self.api_secret else "MISSING"
        log.info("DavisPressureFetcher: api_key %s, api_secret %s, station_id=%s",
                 key_state, secret_state, self.station_id)
        if self.api_key and self.api_secret and self.station_id:
            self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)
            log.info("DavisPressureFetcher: bound to NEW_LOOP_PACKET")
        else:
            log.error("DavisPressureFetcher: missing credentials, not binding")

    def get_signature(self):
        t = int(time.time())
        params = f"api-key{self.api_key}station-id{self.station_id}t{t}"
        sig = hmac.new(self.api_secret.encode(), params.encode(), hashlib.sha256).hexdigest()
        return t, sig

    def fetch_pressure(self):
        if not REQUESTS_AVAILABLE:
            log.error("DavisPressureFetcher: requests not available")
            return
        try:
            t, sig = self.get_signature()
            url = (f"https://api.weatherlink.com/v2/current/{self.station_id}"
                   f"?api-key={self.api_key}&t={t}&api-signature={sig}")
            r = requests.get(url, timeout=10)
            data = r.json()
            for sensor in data.get('sensors', []):
                for record in sensor.get('data', []):
                    if 'bar_sea_level' in record and record['bar_sea_level']:
                        self.last_pressure = record['bar_sea_level']
                        self.last_success = time.time()
                        log.info("DavisPressureFetcher: got pressure %.3f", self.last_pressure)
                        return
                    if 'bar' in record and record['bar']:
                        self.last_pressure = record['bar']
                        self.last_success = time.time()
                        log.info("DavisPressureFetcher: got pressure %.3f", self.last_pressure)
                        return
            log.warning("DavisPressureFetcher: no pressure found in response")
        except Exception as e:
            log.error("DavisPressureFetcher: error fetching pressure: %s", e)

    def new_loop_packet(self, event):
        now = time.time()
        if now - self.last_fetch > self.fetch_interval:
            self.last_fetch = now
            log.info("DavisPressureFetcher: fetching pressure")
            t = threading.Thread(target=self.fetch_pressure)
            t.daemon = True
            t.start()
        if self.last_pressure is not None:
            packet = event.packet
            # barometer (sea-level, WeatherLink-corrected) is the quantity we
            # fetched -- inject it; that is this service's whole purpose.
            #
            # pressure (station) and altimeter are DIFFERENT quantities. The
            # old backfill wrote this same sea-level number into both, so the
            # archive's station-pressure column carried sea-level values at
            # any nonzero elevation (#144, hlf#302) -- not a reader trap but a
            # wrong number. Honest nulls instead (DEC-0006): the ISS never
            # provides them, so they stay None and the archive columns go NULL
            # rather than borrowed. DEC-0086 documents the passthrough itself.
            if packet.get('barometer') is None:
                packet['barometer'] = self.last_pressure
        if self.last_success is not None:
            # #172: the fetch's own freshness, distinct from last_fetch (a
            # throttle stamp that advances on FAILED attempts too). Stamped
            # into every packet; loop_json_writer publishes it verbatim so the
            # dashboard can see how stale the relayed barometer actually is.
            event.packet['barometer_fetch_epoch'] = int(self.last_success)
