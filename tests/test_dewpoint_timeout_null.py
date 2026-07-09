"""Offline tests for the DewpointCacher carry-forward timeout (DEC-0022, S33).

The change: the temp/humidity/radiation/UV cache still bridges the ISS
message-type rotation (absent-this-packet is normal, not a failure), but a
cached value now expires after CACHE_TIMEOUT_SECONDS of sensor silence --
the field then stays an honest null instead of substituting a stale reading
forever (the DEC-0006 violation that masked failed sensors and hid the
night-time humidity glitches nulled upstream). dewpoint/heatindex are
likewise computed only from fresh values.

weewx is not installed in the test/CI environment, so we stub the weewx
modules in sys.modules before importing dewpoint_service (same pattern as
test_dewpoint_wind_honest_null.py).

Run:  python3 -m pytest tests/   OR   python3 tests/test_dewpoint_timeout_null.py
"""
import os
import sys
import types


# --- stub the weewx deps so dewpoint_service.py imports without weewx ---
def _pkg(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m


def _mod(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m


weewx = _pkg("weewx")
weewx.NEW_LOOP_PACKET = "NEW_LOOP_PACKET"

weewx_engine = _mod("weewx.engine")


class _StdService:
    def __init__(self, engine, config_dict):
        pass

    def bind(self, *a, **k):
        pass


weewx_engine.StdService = _StdService
weewx.engine = weewx_engine

weewx_wxformulas = _mod("weewx.wxformulas")
weewx_wxformulas.dewpointF = lambda t, h: round(t - (100 - h) / 5.0, 2)
weewx_wxformulas.heatindexF = lambda t, h: t
weewx.wxformulas = weewx_wxformulas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dewpoint_service  # noqa: E402
from dewpoint_service import CACHE_TIMEOUT_SECONDS  # noqa: E402

T0 = 1_700_000_000  # arbitrary packet epoch


class _Event:
    def __init__(self, packet):
        self.packet = packet


def _cacher():
    return dewpoint_service.DewpointCacher(engine=None, config_dict={})


def _run(cacher, ts, **fields):
    packet = {"dateTime": ts}
    packet.update(fields)
    cacher.new_loop_packet(_Event(packet))
    return packet


def test_rotation_gap_still_bridged():
    # a reading 30 s old is normal rotation traffic and must be substituted
    c = _cacher()
    _run(c, T0, outTemp=70.0)
    pkt = _run(c, T0 + 30)
    assert pkt["outTemp"] == 70.0, "fresh cache must bridge the rotation gap"


def test_stale_value_not_substituted_after_timeout():
    # THE change: sensor silent past the timeout -> honest null, not a stale copy
    c = _cacher()
    _run(c, T0, outTemp=70.0, outHumidity=50.0, radiation=800.0, UV=5.0)
    pkt = _run(c, T0 + CACHE_TIMEOUT_SECONDS + 60)
    for field in ("outTemp", "outHumidity", "radiation", "UV"):
        assert pkt.get(field) is None, "%s: stale value was substituted" % field


def test_dewpoint_only_from_fresh_values():
    c = _cacher()
    _run(c, T0, outTemp=70.0, outHumidity=50.0)
    pkt = _run(c, T0 + 30)
    assert "dewpoint" in pkt and "heatindex" in pkt
    stale = _run(c, T0 + CACHE_TIMEOUT_SECONDS + 60)
    assert "dewpoint" not in stale, "dewpoint computed from stale temp/humidity"
    assert "heatindex" not in stale


def test_sensor_recovery_reseeds_cache():
    c = _cacher()
    _run(c, T0, outHumidity=50.0)
    _run(c, T0 + CACHE_TIMEOUT_SECONDS + 60)               # expired
    _run(c, T0 + CACHE_TIMEOUT_SECONDS + 90, outHumidity=55.0)  # sensor back
    pkt = _run(c, T0 + CACHE_TIMEOUT_SECONDS + 120)
    assert pkt["outHumidity"] == 55.0


def test_present_reading_always_wins_over_cache():
    c = _cacher()
    _run(c, T0, outTemp=70.0)
    pkt = _run(c, T0 + 30, outTemp=71.0)
    assert pkt["outTemp"] == 71.0


def test_wind_filter_untouched_by_cache_change():
    # regression guard: the wind path (honest-null since v2.0.3) is separate
    c = _cacher()
    c.last_wind_speed = 5.0
    pkt = _run(c, T0, windSpeed=None, windGust=None, windDir=None)
    assert pkt["windSpeed"] is None


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    for n, f in fns:
        f()
        print("  [PASS] %s" % n)
    print("%d tests passed" % len(fns))
