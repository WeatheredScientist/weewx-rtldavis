import weewx
from weewx.engine import StdService
import weewx.wxformulas

class DewpointCacher(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        self.last_temp = None
        self.last_humidity = None
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

    def new_loop_packet(self, event):
        packet = event.packet

        # Update cache with any new values
        if packet.get('outTemp') is not None:
            self.last_temp = packet['outTemp']
        if packet.get('outHumidity') is not None:
            self.last_humidity = packet['outHumidity']

        # Inject cached values
        if packet.get('outTemp') is None and self.last_temp is not None:
            packet['outTemp'] = self.last_temp
        if packet.get('outHumidity') is None and self.last_humidity is not None:
            packet['outHumidity'] = self.last_humidity

        # Directly calculate dewpoint if we have both values
        if self.last_temp is not None and self.last_humidity is not None:
            packet['dewpoint'] = weewx.wxformulas.dewpointF(self.last_temp, self.last_humidity)
            packet['heatindex'] = weewx.wxformulas.heatindexF(self.last_temp, self.last_humidity)
