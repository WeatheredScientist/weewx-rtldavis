# reception_service.py
# Calculates ISS packet reception rate over a 60-second rolling window
# and logs freqError values from the rtldavis driver.
#
# Injects rxCheckPercent into LOOP packets.
# Logs a warning when reception drops below 80%.
# Logs freqError values when non-zero.

import time
import weewx
from weewx.engine import StdService
import logging

log = logging.getLogger(__name__)

# Davis VP2 ISS transmits every 2.5 seconds = 24 packets/minute expected
EXPECTED_RATE = 1.0 / 2.5   # packets per second
WINDOW        = 60.0         # rolling window in seconds
WARN_THRESHOLD = 80.0        # warn when reception below this %


class ReceptionMonitor(StdService):
    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        self.packet_times = []   # timestamps of received packets
        self.last_log_time = 0
        self.start_time = time.time()
        log.info("ReceptionMonitor: started (window=%ss, threshold=%s%%)",
                 WINDOW, WARN_THRESHOLD)
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

    def new_loop_packet(self, event):
        packet = event.packet
        now = time.time()

        # --- Reception rate calculation ---
        self.packet_times.append(now)
        if len(self.packet_times) == 1:
            log.info("ReceptionMonitor: first packet received")
        # Trim to rolling window
        cutoff = now - WINDOW
        self.packet_times = [t for t in self.packet_times if t >= cutoff]

        # Don't evaluate until first full window has elapsed
        if now - self.start_time < WINDOW:
            return

        expected = EXPECTED_RATE * WINDOW
        received = len(self.packet_times)
        pct = min(100.0, (received / expected) * 100.0)

        packet['rxCheckPercent'] = round(pct, 1)

        # Log reception % every 5 minutes
        if (now - self.last_log_time) > 300:
            if pct < WARN_THRESHOLD:
                log.warning("ReceptionMonitor: reception %.1f%% (received %d/%d packets in last %ds)",
                            pct, received, int(expected), int(WINDOW))
            else:
                log.info("ReceptionMonitor: reception %.1f%% (received %d/%d packets in last %ds)",
                         pct, received, int(expected), int(WINDOW))
            self.last_log_time = now

        # --- freqError logging ---
        freq_errors = {}
        for i in range(5):
            field = f'freqError{i}'
            val = packet.get(field)
            if val is not None and val != 0:
                freq_errors[field] = val

        if freq_errors:
            log.warning("ReceptionMonitor: non-zero freqErrors: %s", freq_errors)
