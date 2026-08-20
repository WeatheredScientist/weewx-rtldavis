"""Regression tests for the DewpointCacher wind-filter redesign (S94, issue #223).

Issue #223 bundled four facets of one design gap: `_filter_wind` did not apply the
resync-on-reject + co-null pattern that `rtldavis.py`'s `SensorQC` had already
established as correct in this same repo. The fix ports that pattern locally (kept
local, not imported, so this service keeps its zero coupling to the driver --
docs/INTERFACES.md), and turns on the distinction the driver already draws:

  * a BOUNDS reject is positive proof of corruption -> learn nothing, baseline
    untouched;
  * a DELTA reject may be a genuine step -> always resync the baseline, so the
    next reading is judged against current reality.

Every test below except `test_bounds_reject_leaves_baseline_untouched` (a
convention lock, correct before and after) was confirmed to FAIL against the
pre-fix file via `git stash`.

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing dewpoint_service (same pattern as the other tests).

Run:  python3 -m pytest tests/   OR   python3 tests/test_dewpoint_wind_filter_223.py
"""
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
# Unit systems (#224). dewpoint_service builds module-level lookup tables keyed on
# these AT IMPORT TIME, so the stub has to carry them or the import fails.
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

weewx_wxformulas = _mod("weewx.wxformulas")
weewx_wxformulas.dewpointF = lambda t, h: 0.0
weewx_wxformulas.heatindexF = lambda t, h: 0.0
weewx_wxformulas.dewpointC = lambda t, h: 0.0   # #224: both pairs must exist
weewx_wxformulas.heatindexC = lambda t, h: 0.0
weewx.wxformulas = weewx_wxformulas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dewpoint_service  # noqa: E402


# Fixed clock: these tests reason about baseline AGE, so a real wall clock would
# make the TTL cases nondeterministic.
T0 = 1000.0


def _seeded(speed=5.0, when=T0):
    """A cacher with an already-warmed, freshly-timestamped baseline."""
    c = dewpoint_service.DewpointCacher(engine=None, config_dict={})
    c.last_wind_speed = speed
    c.last_wind_time = when
    return c


# --- Item 1: the permanent-null deadlock -------------------------------------

def test_delta_reject_resyncs_baseline_no_deadlock():
    # THE deadlock repro. A storm arrives as a step beyond MAX_WIND_DELTA from a
    # stale baseline: that first reading is rejected (correct), but the baseline
    # must move to it, so the NEXT genuine reading is accepted. Pre-fix the
    # baseline stayed frozen at 5.0 and every later reading rejected against it
    # forever -- real wind nulled until the weewx process restarted.
    c = _seeded(5.0)

    first = {"windSpeed": 100.0, "windGust": 100.0, "windDir": 90.0}
    c._filter_wind(first, now=T0 + 1)
    assert first["windSpeed"] is None, "the implausible step should be rejected"
    assert c.last_wind_speed == 100.0, "baseline must resync even on reject"

    second = {"windSpeed": 102.0, "windGust": 105.0, "windDir": 90.0}
    c._filter_wind(second, now=T0 + 2)
    assert second["windSpeed"] == 102.0, "deadlock: real wind still being rejected"
    print("  [PASS] test_delta_reject_resyncs_baseline_no_deadlock")


def test_stale_baseline_is_reseeded_not_used():
    # Second, independent escape from a frozen baseline: after a reception gap
    # longer than the TTL the old reading describes different weather, so it is
    # reseeded rather than used as a delta reference. Pre-fix there was no TTL at
    # all and this jump was rejected.
    c = _seeded(5.0)
    packet = {"windSpeed": 90.0, "windGust": 95.0, "windDir": 90.0}
    c._filter_wind(packet, now=T0 + dewpoint_service.WIND_BASELINE_TTL_SECONDS + 1)
    assert packet["windSpeed"] == 90.0, "stale baseline should be reseeded, not enforced"
    assert c.last_wind_speed == 90.0
    print("  [PASS] test_stale_baseline_is_reseeded_not_used")


def test_fresh_baseline_still_filters():
    # The TTL must not become a hole in the filter: inside the window, an
    # implausible step is still rejected.
    c = _seeded(5.0)
    packet = {"windSpeed": 150.0, "windGust": 150.0, "windDir": 90.0}
    c._filter_wind(packet, now=T0 + 10)
    assert packet["windSpeed"] is None
    print("  [PASS] test_fresh_baseline_still_filters")


# --- Item 2: windDir must not survive a rejected windSpeed -------------------

def test_delta_reject_nulls_winddir():
    # Pre-fix windDir survived both reject branches, so a direction with no speed
    # reached loop-JSON, InfluxDB and every uploader.
    c = _seeded(5.0)
    packet = {"windSpeed": 100.0, "windGust": 100.0, "windDir": 90.0}
    c._filter_wind(packet, now=T0 + 1)
    assert packet["windDir"] is None, "windDir outlived a rejected windSpeed"
    print("  [PASS] test_delta_reject_nulls_winddir")


def test_gust_inconsistency_nulls_winddir():
    c = _seeded(5.0)
    packet = {"windSpeed": 10.0, "windGust": 5.0, "windDir": 90.0}
    c._filter_wind(packet, now=T0 + 1)
    assert packet["windSpeed"] is None
    assert packet["windGust"] is None
    assert packet["windDir"] is None, "windDir outlived a corrupt-packet reject"
    print("  [PASS] test_gust_inconsistency_nulls_winddir")


# --- Item 3: the cold-start warmup buffer was unfiltered ---------------------

def test_warmup_rejects_out_of_range_sample():
    # An impossible reading during the ~3-packet warmup window must not reach the
    # averaging buffer -- pre-fix it did, and a wrong seeded baseline is exactly
    # what triggers the item-1 deadlock on the readings that follow.
    c = dewpoint_service.DewpointCacher(engine=None, config_dict={})
    packet = {"windSpeed": 300.0, "windGust": 300.0, "windDir": 90.0}
    c._filter_wind(packet, now=T0)
    assert c.wind_warmup == [], "an impossible reading seeded the warmup buffer"
    assert packet["windSpeed"] is None
    assert packet["windDir"] is None
    print("  [PASS] test_warmup_rejects_out_of_range_sample")


def test_warmup_still_seeds_from_plausible_samples():
    # The bounds gate must not break normal cold-start seeding.
    c = dewpoint_service.DewpointCacher(engine=None, config_dict={})
    for i in range(dewpoint_service.WIND_WARMUP_PACKETS):
        c._filter_wind({"windSpeed": 6.0, "windGust": 8.0, "windDir": 90.0},
                       now=T0 + i)
    assert c.last_wind_speed == 6.0
    assert c.last_wind_time == T0 + dewpoint_service.WIND_WARMUP_PACKETS - 1
    print("  [PASS] test_warmup_still_seeds_from_plausible_samples")


# --- Item 4: windGust unguarded when windSpeed is absent ---------------------

def test_gust_bounds_checked_without_speed():
    # Both guards were gated on `windSpeed is not None`, so a driver reporting a
    # gust with no speed got zero validation. Unreachable with today's driver, but
    # this service is driver-agnostic by design (docs/INTERFACES.md).
    c = _seeded(5.0)
    packet = {"windSpeed": None, "windGust": 500.0, "windDir": 90.0}
    c._filter_wind(packet, now=T0 + 1)
    assert packet["windGust"] is None, "an impossible gust passed through unguarded"
    print("  [PASS] test_gust_bounds_checked_without_speed")


# --- The bounds/delta split itself -------------------------------------------

def test_bounds_reject_leaves_baseline_untouched():
    # Convention lock (correct before AND after the fix, asserted so it stays
    # that way): a bounds reject is proof the packet is corrupt, so it teaches the
    # baseline nothing. Only a DELTA reject resyncs. Collapsing the two would let
    # garbage set the reference that real wind is judged against.
    c = _seeded(5.0)
    c._filter_wind({"windSpeed": 10.0, "windGust": 5.0, "windDir": 90.0},
                   now=T0 + 1)
    assert c.last_wind_speed == 5.0, "a corrupt packet moved the baseline"
    print("  [PASS] test_bounds_reject_leaves_baseline_untouched")


def test_good_reading_advances_baseline_and_clock():
    c = _seeded(5.0)
    packet = {"windSpeed": 6.0, "windGust": 8.0, "windDir": 90.0}
    c._filter_wind(packet, now=T0 + 5)
    assert packet["windSpeed"] == 6.0
    assert packet["windDir"] == 90.0, "a good reading must keep its direction"
    assert c.last_wind_speed == 6.0
    assert c.last_wind_time == T0 + 5
    print("  [PASS] test_good_reading_advances_baseline_and_clock")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
    print("\n%d/%d passed" % (len(tests), len(tests)))
