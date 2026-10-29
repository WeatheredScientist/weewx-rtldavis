"""Offline regression test for the battery-low dispatch drop (issue #220).

DATAPacket.IDENTIFIER's 2nd hex digit used to be restricted to [0-7] -- the
low nibble of payload byte 0, whose bit 3 is the battery-low flag (pkt[0] >>
3) & 0x1 in parse_raw()). Any transmitter reporting low battery flipped that
nibble into 8-F, failing the dispatch gate in PacketFactory.parse_text and
silently dropping the ENTIRE frame -- wind, temp, humidity, rain, not just
battery status -- while PATTERN (the actual decode regex) matched fine
throughout. Channel 1 = iss, message type 0xE = rain, matching the known-good
fixture test_parse_raw_channel.py already validates for that combination.

weewx is not installed in the test/CI environment, so we stub it (same
pattern as test_parse_raw_channel.py / test_procmanager_reap.py).

Run:  python3 -m pytest tests/ (pytest only)
"""

from rtldavis import DATAPacket, PacketFactory, RtldavisDriver  # noqa: E402

# channel 1 (iss), message type 0xE (rain), rain_count=5 -- the exact byte
# shape test_parse_raw_channel.py's test_known_iss_channel_still_parses
# already validates as a known-good rain frame, just with byte0's battery
# bit (bit 3) flipped: 0xE0 (clear) -> 0xE8 (set). Channel and message type
# both survive the flip (they live in different bits).
_BATTERY_CLEAR_LINE = "20:31:04.102918 E000000505009F3D 9 0 0 0"
_BATTERY_SET_LINE = "20:31:04.102918 E800000505009F3D 9 0 0 0"


class _FakeDriver:
    """Same minimal stand-in as test_parse_raw_channel.py's .channels, plus
    the real parse_raw: DATAPacket.parse_text calls self.parse_raw(self,
    raw_pkt) on whatever "self" PacketFactory.create() was handed, so the
    fake needs the actual implementation reachable, not a stub of it.
    parse_raw is @staticmethod but takes `self` explicitly (documented at
    its definition, rtldavis.py ~1546) -- wrapping it in staticmethod()
    here too keeps it unbound so the explicit-self call matches, same as a
    real RtldavisDriver instance would resolve it."""
    channels = {'iss': 1, 'anemometer': 0, 'leaf_soil': 0,
                'temp_hum_1': 0, 'temp_hum_2': 0, 'wind_channel': 1}
    parse_raw = staticmethod(RtldavisDriver.parse_raw)


def test_identifier_matches_regardless_of_battery_bit():
    """The exact regression: pre-fix, only the battery-clear line matched.
    IDENTIFIER is a dispatch gate, not a decoder -- it must not care about a
    data bit PATTERN never restricted."""
    assert DATAPacket.IDENTIFIER.search(_BATTERY_CLEAR_LINE)
    assert DATAPacket.IDENTIFIER.search(_BATTERY_SET_LINE), (
        "battery-low frame failed the dispatch gate -- issue #220 regression")


def test_pattern_always_matched_both():
    """Documents the issue's own diagnostic: PATTERN (decode) was never the
    problem, only IDENTIFIER (dispatch) was -- true before and after the fix."""
    assert DATAPacket.PATTERN.search(_BATTERY_CLEAR_LINE)
    assert DATAPacket.PATTERN.search(_BATTERY_SET_LINE)


def test_battery_low_frame_is_not_dropped_by_dispatch():
    """End-to-end: a battery-low frame must reach parse_raw and come back as
    a real packet, not silently disappear (the actual failure scenario --
    wind/temp/humidity/rain all went dark, not just battery status)."""
    lines = [_BATTERY_SET_LINE]
    packets = list(PacketFactory.create(_FakeDriver(), lines))
    assert len(packets) == 1, "battery-low frame was dropped, not dispatched"
    assert packets[0]['channel'] == 1
    assert packets[0]['bat_iss'] == 1
    assert packets[0].get('rain_count') == 5
