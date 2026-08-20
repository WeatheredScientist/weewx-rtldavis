"""Unit-system regression tests for DewpointCacher (S96, issue #224).

`dewpoint_service.py` had no `usUnits` check anywhere: it called
`weewx.wxformulas.dewpointF`/`heatindexF` unconditionally, and compared the
packet's wind against two thresholds documented in mph. Under
`target_unit=METRIC`/`METRICWX` -- both documented options in this repo's own
`weewx.conf.example` -- `outTemp` arrives in degC and wind in km/h or m/s.
Masked in production only by the shipped default (`target_unit=US`).

The wind half is the interesting one, because it failed in BOTH directions and
each direction is silent:

  * as m/s, MAX_PLAUSIBLE_WIND_SPEED=200 is ~447 mph -- the guard is INERT and
    corrupt readings sail through;
  * as km/h it is ~124 mph -- the guard is OVER-TIGHT and nulls real weather.

Tests 5-8 below are written as that pair: each asserts the new behaviour AND
names what the pre-fix code did with the same input, so the regression is legible
without re-deriving the arithmetic.

SEVEN of the ten were confirmed to fail against the pre-fix file -- measured, not
assumed. (Method, because the obvious one is a trap: the fixed file was copied
aside and `git show HEAD:dewpoint_service.py` swapped in. NOT `git checkout`,
which restores from the INDEX and would have silently wiped the uncommitted fix.)
The pre-fix run's own log line is the bug stating itself:
`rejecting windSpeed 105.0 mph (delta 100.0 mph from last 5.0 mph)` -- on a packet
whose wind was km/h.

The three that pass either way are deliberate and labelled inline: the two US
cases (the shipped default, which this fix must not disturb) and the
gust-below-speed guard (a same-system comparison that needs no conversion).

The fix branches on `usUnits` the way WeeWX's own `wxxtypes.py` does, rather than
converting via `weewx.units.to_US()`. That matters: `loop_json_writer.py` uses
to_US legitimately because it EMITS US-suffixed fields, but this service writes
into the live packet, so a to_US fix without a return trip would write degF into
a metric packet -- the same bug one layer along.

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing dewpoint_service (same pattern as the other tests).

Run:  python3 -m pytest tests/   OR   python3 tests/test_dewpoint_units_224.py
"""
import contextlib
import os
import sys
import types


# --- stub the weewx deps so dewpoint_service.py imports without weewx installed ---
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
# Unit systems. dewpoint_service builds module-level lookup tables keyed on these
# AT IMPORT TIME, so they must exist before the import below. Values mirror
# weewx's own; the service compares symbolically and never depends on them.
weewx.US = 1
weewx.METRIC = 16
weewx.METRICWX = 17

weewx_engine = _mod("weewx.engine")


class _StdService:
    def __init__(self, engine, config_dict):
        pass

    def bind(self, *a, **k):
        pass


weewx_engine.StdService = _StdService
weewx.engine = weewx_engine

# Sentinel returns, so a test can prove WHICH formula was reached rather than
# inferring it from a plausible-looking number.
DEW_F, DEW_C = -111.0, -222.0
HI_F, HI_C = -333.0, -444.0

weewx_wxformulas = _mod("weewx.wxformulas")
weewx_wxformulas.dewpointF = lambda t, h: DEW_F
weewx_wxformulas.heatindexF = lambda t, h: HI_F
weewx_wxformulas.dewpointC = lambda t, h: DEW_C
weewx_wxformulas.heatindexC = lambda t, h: HI_C
weewx.wxformulas = weewx_wxformulas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dewpoint_service  # noqa: E402

# Read the unit constants back off the module under test rather than using our own
# stub's, for the same shared-sys.modules reason described in _sentinel_formulas:
# these can be different module objects depending on collection order. They agree
# on values today; reading them from here means this file stays correct if they
# ever stop agreeing.
US = dewpoint_service.weewx.US
METRIC = dewpoint_service.weewx.METRIC
METRICWX = dewpoint_service.weewx.METRICWX

T0 = 1000.0


def _cacher():
    return dewpoint_service.DewpointCacher(engine=None, config_dict={})


def _seeded(speed, when=T0):
    """A cacher with an already-warmed baseline, in the PACKET's own units."""
    c = _cacher()
    c.last_wind_speed = speed
    c.last_wind_time = when
    return c


def _evt(packet):
    e = types.SimpleNamespace()
    e.packet = packet
    return e


_MISSING = object()


@contextlib.contextmanager
def _sentinel_formulas():
    """Install the sentinel formulas on the module dewpoint_service ACTUALLY uses.

    The weewx stubs live in `sys.modules` and are therefore shared across every
    test file in this suite, so `dewpoint_service.weewx` is whichever stub instance
    was live when dewpoint_service was FIRST imported -- which depends on
    collection order, not on this file. Setting the sentinels on our own stub is
    enough when this file runs alone and silently does nothing when it does not,
    which is precisely the shape of test that passes in isolation and fails in the
    suite (it did, on the first run of this file).

    So patch through `dewpoint_service` itself, and restore afterwards so the
    neighbouring files' stubs -- which assert on their own formula values -- are
    left exactly as they were.
    """
    wx = dewpoint_service.weewx.wxformulas
    names = ("dewpointF", "heatindexF", "dewpointC", "heatindexC")
    saved = {n: getattr(wx, n, _MISSING) for n in names}
    wx.dewpointF = lambda t, h: DEW_F
    wx.heatindexF = lambda t, h: HI_F
    wx.dewpointC = lambda t, h: DEW_C
    wx.heatindexC = lambda t, h: HI_C
    try:
        yield
    finally:
        for n, v in saved.items():
            if v is _MISSING:
                delattr(wx, n)
            else:
                setattr(wx, n, v)


class _RecordingLog:
    """Captures warnings so the once-per-run rule can be asserted, without
    pytest's caplog -- these files must also run standalone."""

    def __init__(self):
        self.warnings = []

    def warning(self, msg, *args, **kwargs):
        self.warnings.append(msg % args if args else msg)

    def info(self, *a, **k):
        pass

    def debug(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


# --- 1-4: which formula pair gets reached -----------------------------------

def test_us_packet_uses_fahrenheit_pair():
    # Convention lock: correct before and after the fix.
    with _sentinel_formulas():
        c = _cacher()
        pkt = {"dateTime": T0, "usUnits": US, "outTemp": 70.0, "outHumidity": 50.0}
        c.new_loop_packet(_evt(pkt))
        assert pkt["dewpoint"] == DEW_F, "US packets must use the Fahrenheit pair"
        assert pkt["heatindex"] == HI_F
    print("  [PASS] test_us_packet_uses_fahrenheit_pair")


def test_metric_packet_uses_celsius_pair():
    # Pre-fix: dewpointF(21.1 degC) -- degC read as degF, silently wrong, while
    # usUnits still correctly advertised METRIC to every consumer.
    with _sentinel_formulas():
        c = _cacher()
        pkt = {"dateTime": T0, "usUnits": METRIC, "outTemp": 21.1, "outHumidity": 50.0}
        c.new_loop_packet(_evt(pkt))
        assert pkt["dewpoint"] == DEW_C, "METRIC packets must use the Celsius pair"
        assert pkt["heatindex"] == HI_C
    print("  [PASS] test_metric_packet_uses_celsius_pair")


def test_metricwx_packet_uses_celsius_pair():
    # METRICWX differs from METRIC only in wind/rain units; outTemp is degC in
    # both, so they share the Celsius branch.
    with _sentinel_formulas():
        c = _cacher()
        pkt = {"dateTime": T0, "usUnits": METRICWX, "outTemp": 21.1, "outHumidity": 50.0}
        c.new_loop_packet(_evt(pkt))
        assert pkt["dewpoint"] == DEW_C, "METRICWX packets must use the Celsius pair"
        assert pkt["heatindex"] == HI_C
    print("  [PASS] test_metricwx_packet_uses_celsius_pair")


def test_missing_usunits_falls_back_to_us_and_warns_once():
    # A packet with no usUnits is a contract violation by whatever produced it.
    # Falling back to US reproduces pre-#224 behaviour exactly, so the fix cannot
    # regress the shipped default -- but it must be said out loud, and exactly
    # once: a LOOP-rate warning is its own outage (DEC-0043's class).
    c = _cacher()
    original, dewpoint_service.log = dewpoint_service.log, _RecordingLog()
    try:
        recorder = dewpoint_service.log
        with _sentinel_formulas():
            for i in range(3):
                pkt = {"dateTime": T0 + i, "outTemp": 70.0, "outHumidity": 50.0}
                c.new_loop_packet(_evt(pkt))
                assert pkt["dewpoint"] == DEW_F, "missing usUnits must behave as US"
        unit_warnings = [w for w in recorder.warnings if "usUnits" in w]
        assert len(unit_warnings) == 1, (
            "expected exactly one usUnits warning across 3 packets, got %d"
            % len(unit_warnings)
        )
    finally:
        dewpoint_service.log = original
    print("  [PASS] test_missing_usunits_falls_back_to_us_and_warns_once")


# --- 5-8: the wind thresholds, failing in both directions --------------------

def test_bounds_metricwx_catches_reading_the_old_code_waved_through():
    # 100 m/s = 223.7 mph, past the 6410's 200 mph spec ceiling -> must be nulled.
    # PRE-FIX: 100 <= 200 compared as bare numbers, so the guard was INERT and a
    # corrupt reading became published weather.
    c = _seeded(98.0)
    pkt = {"usUnits": METRICWX, "windSpeed": 100.0, "windGust": 100.0, "windDir": 90.0}
    c._filter_wind(pkt, now=T0 + 1)
    assert pkt["windSpeed"] is None, "223.7 mph as m/s must be rejected by bounds"
    assert pkt["windDir"] is None, "the whole triple co-nulls"
    print("  [PASS] test_bounds_metricwx_catches_reading_the_old_code_waved_through")


def test_bounds_metric_accepts_reading_the_old_code_wrongly_nulled():
    # 250 km/h = 155.3 mph, comfortably inside the 200 mph ceiling -> must pass.
    # PRE-FIX: 250 > 200 as bare numbers, so real weather was nulled and the
    # whole wind triple discarded.
    c = _seeded(248.0)
    pkt = {"usUnits": METRIC, "windSpeed": 250.0, "windGust": 250.0, "windDir": 90.0}
    c._filter_wind(pkt, now=T0 + 1)
    assert pkt["windSpeed"] == 250.0, "155.3 mph as km/h must survive the bounds test"
    print("  [PASS] test_bounds_metric_accepts_reading_the_old_code_wrongly_nulled")


def test_delta_metricwx_catches_step_the_old_code_waved_through():
    # A 40 m/s step = 89.5 mph, past the 75 mph delta ceiling -> must be rejected.
    # PRE-FIX: 40 <= 75 as bare numbers, so an implausible jump was accepted.
    c = _seeded(5.0)
    pkt = {"usUnits": METRICWX, "windSpeed": 45.0, "windGust": 45.0, "windDir": 90.0}
    c._filter_wind(pkt, now=T0 + 1)
    assert pkt["windSpeed"] is None, "an 89.5 mph step as m/s must be rejected"
    assert c.last_wind_speed == 45.0, "delta rejects still resync the baseline (DEC-0054)"
    print("  [PASS] test_delta_metricwx_catches_step_the_old_code_waved_through")


def test_delta_metric_accepts_step_the_old_code_wrongly_rejected():
    # A 100 km/h step = 62.1 mph, inside the 75 mph ceiling -> must be accepted.
    # PRE-FIX: 100 > 75 as bare numbers, so a real gust front was nulled.
    c = _seeded(5.0)
    pkt = {"usUnits": METRIC, "windSpeed": 105.0, "windGust": 105.0, "windDir": 90.0}
    c._filter_wind(pkt, now=T0 + 1)
    assert pkt["windSpeed"] == 105.0, "a 62.1 mph step as km/h must be accepted"
    print("  [PASS] test_delta_metric_accepts_step_the_old_code_wrongly_rejected")


# --- 9-10: US unchanged, and the unit-independent guard ----------------------

def test_us_wind_behaviour_unchanged():
    # Convention lock: the mph path must be byte-for-byte the same as before, since
    # US is the shipped default and this fix must not touch production behaviour.
    c = _seeded(5.0)
    pkt = {"usUnits": US, "windSpeed": 250.0, "windGust": 250.0, "windDir": 90.0}
    c._filter_wind(pkt, now=T0 + 1)
    assert pkt["windSpeed"] is None, "250 mph is still past the 200 mph ceiling"
    print("  [PASS] test_us_wind_behaviour_unchanged")


def test_gust_below_speed_still_caught_under_metric():
    # This comparison is between two fields of the SAME unit system, so it needs
    # no conversion -- asserting that it was not "fixed" into something unit-aware
    # by accident.
    c = _seeded(50.0)
    pkt = {"usUnits": METRIC, "windSpeed": 60.0, "windGust": 40.0, "windDir": 90.0}
    c._filter_wind(pkt, now=T0 + 1)
    assert pkt["windSpeed"] is None, "gust below speed is corrupt in any unit system"
    print("  [PASS] test_gust_below_speed_still_caught_under_metric")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\nAll #224 unit-system tests passed.")
