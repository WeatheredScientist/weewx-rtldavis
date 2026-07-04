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
        self.last_fetch = 0
        log.info("DavisPressureFetcher: api_key=%s station_id=%s", self.api_key[:8], self.station_id)
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
                        log.info("DavisPressureFetcher: got pressure %.3f", self.last_pressure)
                        return
                    if 'bar' in record and record['bar']:
                        self.last_pressure = record['bar']
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
            if packet.get('barometer') is None:
                packet['barometer'] = self.last_pressure
            if packet.get('pressure') is None:
                packet['pressure'] = self.last_pressure
            if packet.get('altimeter') is None:
                packet['altimeter'] = self.last_pressure
