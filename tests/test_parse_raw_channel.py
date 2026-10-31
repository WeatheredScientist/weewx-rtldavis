"""Offline regression test for the unknown-channel error path (S24, finding H1).

The bug (H1): rtldavis.py's parse_raw() ended with
    logerr("unknown station with channel: %s, raw message: %s"
           % (data['channel'], raw))
but `raw` is never defined in parse_raw (the parameter is `pkt`). So a packet
arriving on a channel that matches none of the configured sensors raised
NameError *inside* genLoopPackets instead of logging the intended diagnostic --
turning a benign "unknown station" into a driver crash. This test drives that
exact path and asserts parse_raw returns cleanly (no NameError).

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing the driver (same pattern as test_rain_filter).

Run:  python3 -m pytest tests/ (pytest only)
"""

from rtldavis import RtldavisDriver  # noqa: E402
from conftest import DEFAULT_CHANNELS  # noqa: E402


class _FakeDriver:
    """Minimal stand-in carrying only what parse_raw reads: the channel map.
    All sensor channels but the ISS are 0 (not present), so a packet on any
    other channel falls through to the unknown-station else branch (H1)."""
    channels = dict(DEFAULT_CHANNELS)


def _pkt_on_channel(chan):
    # channel = (pkt[0] & 0x7) + 1  ->  pkt[0] low 3 bits = chan - 1
    b0 = (chan - 1) & 0x7
    return bytearray([b0, 0, 0, 0, 0, 0, 0, 0])


def test_unknown_channel_does_not_raise():
    """The H1 repro: channel 3 matches no configured sensor -> else branch.
    Before the fix this raised NameError('raw'); after, it logs and returns."""
    pkt = _pkt_on_channel(3)
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)   # must not raise
    assert data['channel'] == 3


def test_known_iss_channel_still_parses():
    """Guard against over-correcting: a normal ISS packet still parses.
    message_type 0xE (rain), rain_count in low 7 bits of pkt[3]."""
    pkt = bytearray([0xE0, 0, 0, 0x05, 0x05, 0, 0x9F, 0x3D])  # channel 1 = iss
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)
    assert data['channel'] == 1
    assert data.get('rain_count') == 5
