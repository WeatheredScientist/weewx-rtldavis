import hmac
import hashlib
import re
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

# S91: requests/urllib3 embed the full request URL -- credential and all --
# in the string form of any connection-level exception (ConnectionError,
# SSLError, MaxRetryError). fetch_pressure() puts api-key and api-signature
# in that URL's query string, so an ordinary DNS blip or WeatherLink outage
# put the live key into weewx.log at ERROR level -- a channel DEC-0047's
# read-guard does not cover. Redact by query-param NAME, not by a known
# value: get_signature() can itself raise before `sig` is ever bound, so
# there is no local variable guaranteed to be in scope at the failure point.
_SECRET_PARAM_RE = re.compile(r'(api-key|api-signature)=[^&\s]*')


def _redact_secrets(text):
    return _SECRET_PARAM_RE.sub(r'\1=REDACTED', text)


class DavisPressureFetcher(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        pressure_dict = config_dict.get('DavisPressure', {})
        self.api_key = pressure_dict.get('api_key', '')
        self.api_secret = pressure_dict.get('api_secret', '')
        self.station_id = int(pressure_dict.get('station_id', 0))
        self.fetch_interval = int(pressure_dict.get('fetch_interval', 3600))
        self.last_pressure = None
        # DEC-0209 (eaglehunt-ops#357): WeatherLink's bar_absolute, the raw
        # sensor reading -- the only MEASURED station pressure this station
        # has, since the ISS never transmits pressure. Taken from the same
        # record as the sea-level value, never from a different sensor.
        self.last_station_pressure = None
        self._warned_no_absolute = False
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
                    sea_level = record.get('bar_sea_level') or record.get('bar')
                    if not sea_level:
                        continue
                    self.last_pressure = sea_level
                    self.last_success = time.time()
                    # bar_absolute sits beside bar_sea_level in the barometer
                    # sensor's record (DEC-0209). Read it from THIS record only:
                    # a value from another record would be another sensor's.
                    absolute = record.get('bar_absolute')
                    if absolute:
                        self.last_station_pressure = absolute
                        log.info("DavisPressureFetcher: got pressure %.3f, station pressure %.3f",
                                 sea_level, absolute)
                    else:
                        log.info("DavisPressureFetcher: got pressure %.3f", sea_level)
                        if not self._warned_no_absolute:
                            self._warned_no_absolute = True
                            log.warning("DavisPressureFetcher: no bar_absolute in the barometer "
                                        "record; pressure stays weewx-derived (DEC-0209)")
                    return
            log.warning("DavisPressureFetcher: no pressure found in response")
        except Exception as e:
            log.error("DavisPressureFetcher: error fetching pressure: %s", _redact_secrets(str(e)))

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
            # DEC-0086 documents the passthrough itself.
            #
            # pressure (station) and altimeter are DIFFERENT quantities. The
            # old backfill wrote this same sea-level number into both, so the
            # archive's station-pressure column carried sea-level values at
            # any nonzero elevation (#144, hlf#302) -- not a reader trap but a
            # wrong number. DEC-0091 stopped that and left both keys None.
            # That did NOT make the columns NULL (INTERFACES §1, corrected
            # S146): StdWXCalculate's prefer_hardware computes any key that is
            # None, so weewx derived pressure by reversing the sea-level value
            # and altimeter from that.
            if packet.get('barometer') is None:
                packet['barometer'] = self.last_pressure
        if self.last_station_pressure is not None:
            # pressure IS measured now: WeatherLink's bar_absolute, from the
            # same fetch (DEC-0209, eaglehunt-ops#357). Injected as a hardware
            # value, so prefer_hardware keeps it and derives altimeter from a
            # measurement instead of a reversed reduction. altimeter is never
            # injected: the station does not measure it.
            if event.packet.get('pressure') is None:
                event.packet['pressure'] = self.last_station_pressure
        if self.last_success is not None:
            # #172: the fetch's own freshness, distinct from last_fetch (a
            # throttle stamp that advances on FAILED attempts too). Stamped
            # into every packet; loop_json_writer publishes it verbatim so the
            # dashboard can see how stale the relayed barometer actually is.
            event.packet['barometer_fetch_epoch'] = int(self.last_success)
