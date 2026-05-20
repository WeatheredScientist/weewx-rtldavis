import hmac
import hashlib
import time
import threading
import weewx
from weewx.engine import StdService

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

class DavisPressureFetcher(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        # Read credentials from weewx.conf [DavisPressure] section
        pressure_dict = config_dict.get('DavisPressure', {})
        self.api_key = pressure_dict.get('api_key', '')
        self.api_secret = pressure_dict.get('api_secret', '')
        self.station_id = int(pressure_dict.get('station_id', 0))
        self.fetch_interval = int(pressure_dict.get('fetch_interval', 3600))
        self.last_pressure = None
        self.last_fetch = 0
        if self.api_key and self.api_secret and self.station_id:
            self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

    def get_signature(self):
        t = int(time.time())
        params = f"api-key{self.api_key}station-id{self.station_id}t{t}"
        sig = hmac.new(self.api_secret.encode(), params.encode(), hashlib.sha256).hexdigest()
        return t, sig

    def fetch_pressure(self):
        if not REQUESTS_AVAILABLE:
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
                        return
                    if 'bar' in record and record['bar']:
                        self.last_pressure = record['bar']
                        return
        except Exception:
            pass

    def new_loop_packet(self, event):
        now = time.time()
        if now - self.last_fetch > self.fetch_interval:
            self.last_fetch = now
            t = threading.Thread(target=self.fetch_pressure)
            t.daemon = True
            t.start()
        if self.last_pressure is not None:
            packet = event.packet
            if packet.get('barometer') is None:
                packet['barometer'] = self.last_pressure
            if packet.get('pressure') is None:
                packet['pressure'] = self.last_pressure
