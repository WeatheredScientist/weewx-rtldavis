"""Regression tests for the archive-level reception-quality wind guard
(docs/DATA_ERRATA.md ERR-0004/ERR-0006, docs/BACKLOG.md's proposed fix).

Neither the bounds check (0-200 mph) nor MAX_WIND_DELTA (75 mph/packet) in
`_filter_wind` can distinguish a mid-magnitude phantom wind reading from a
genuine squall gust of the same size -- both incidents are the exact same
blind spot recurring independently. This guard uses a different signal instead:
rxCheckPercent, measured uncorrelated with genuine high wind at this station
(see dewpoint_service.py's RXCHECK_COLLAPSE_PCT/COLLAPSE_WIND_GUST_MPH comments
for the full measurement). Runs on NEW_ARCHIVE_RECORD, not NEW_LOOP_PACKET,
because rxCheckPercent isn't final until the interval closes.

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing dewpoint_service (same pattern as the other
dewpoint_service tests).

Run:  python3 -m pytest tests/   OR   python3 tests/test_dewpoint_archive_rxcheck_guard.py
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
weewx.NEW_ARCHIVE_RECORD = "NEW_ARCHIVE_RECORD"
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
weewx_wxformulas.dewpointC = lambda t, h: 0.0
weewx_wxformulas.heatindexC = lambda t, h: 0.0
weewx.wxformulas = weewx_wxformulas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dewpoint_service  # noqa: E402


class _Event:
    def __init__(self, record):
        self.record = record


def _cacher():
    return dewpoint_service.DewpointCacher(engine=None, config_dict={})


def _record(**overrides):
    """A plausible, fully-populated archive record; overrides layer on top."""
    r = {
        'dateTime': 1000, 'windSpeed': 2.0, 'windGust': 3.0, 'windDir': 180.0,
        'windGustDir': 180.0, 'rxCheckPercent': 72.7, 'ET': 0.0001,
        'appTemp': 70.0, 'windrun': 0.05, 'usUnits': weewx.US,
    }
    r.update(overrides)
    return r


# --- Positive controls: the two real incidents, replayed verbatim ------------

def test_err0006_replay_nulls_wind():
    # 2026-08-20 11:12 EDT, epoch 1787238720: windGust=37, windSpeed=3.64,
    # rxCheckPercent=9.195402298850574. Verbatim values from the corrected row.
    c = _cacher()
    rec = _record(windSpeed=3.6363636363636362, windGust=37.0, windDir=172.11062253466312,
                   windGustDir=175.2687747035573, rxCheckPercent=9.195402298850574,
                   ET=4.387921088309261e-05, appTemp=74.39694514971873, windrun=0.0606060606060606)
    c.new_archive_record(_Event(rec))
    assert rec['windSpeed'] is None
    assert rec['windGust'] is None
    assert rec['windDir'] is None
    assert rec['windGustDir'] is None
    assert rec['ET'] is None
    assert rec['appTemp'] is None
    assert rec['windrun'] is None
    print("  [PASS] test_err0006_replay_nulls_wind")


def test_err0004_replay_nulls_wind():
    # 2026-07-27 18:56 EDT, epoch 1785178560: windGust=39, windSpeed=2.87,
    # rxCheckPercent=13.2 (docs/DATA_ERRATA.md ERR-0004).
    c = _cacher()
    rec = _record(windSpeed=2.87, windGust=39.0, windDir=209.0, windGustDir=209.0,
                  rxCheckPercent=13.2)
    c.new_archive_record(_Event(rec))
    assert rec['windGust'] is None
    assert rec['windSpeed'] is None
    print("  [PASS] test_err0004_replay_nulls_wind")


# --- Must NOT null: genuine high wind at normal reception --------------------

def test_genuine_high_gust_normal_reception_not_nulled():
    # The station's actual current day-max (19 mph @ rxCheckPercent 72.7%,
    # post-ERR-0006 correction) must survive untouched.
    c = _cacher()
    rec = _record(windSpeed=8.0, windGust=19.0, rxCheckPercent=72.72727272727273)
    c.new_archive_record(_Event(rec))
    assert rec['windGust'] == 19.0, "a genuine gust at normal reception was nulled"
    assert rec['windSpeed'] == 8.0
    print("  [PASS] test_genuine_high_gust_normal_reception_not_nulled")


def test_moderate_gust_just_above_threshold_reception_not_nulled():
    # rxCheckPercent just OUTSIDE the collapse threshold (25%, vs the 20% bound)
    # with a real-looking moderate gust: must not be treated as suspect.
    c = _cacher()
    rec = _record(windSpeed=9.0, windGust=15.0, rxCheckPercent=25.0)
    c.new_archive_record(_Event(rec))
    assert rec['windGust'] == 15.0
    print("  [PASS] test_moderate_gust_just_above_threshold_reception_not_nulled")


# --- Must NOT null: severe collapse with genuinely calm wind -----------------

def test_collapse_with_calm_wind_not_nulled():
    # The observed pattern for 87 of 89 historical rxCheckPercent<20% intervals:
    # reception collapsed, but the wind stayed calm (0-4 mph) -- nothing to guard.
    c = _cacher()
    rec = _record(windSpeed=0.0, windGust=2.0, rxCheckPercent=6.2)
    c.new_archive_record(_Event(rec))
    assert rec['windGust'] == 2.0, "a calm reading during a benign collapse was nulled"
    assert rec['windSpeed'] == 0.0
    print("  [PASS] test_collapse_with_calm_wind_not_nulled")


def test_collapse_with_gust_at_threshold_not_nulled():
    # Exactly AT the gust threshold must not trigger (strict '>', matching the
    # bounds-check convention elsewhere in this file).
    c = _cacher()
    rec = _record(windGust=10.0, rxCheckPercent=9.2)
    c.new_archive_record(_Event(rec))
    assert rec['windGust'] == 10.0
    print("  [PASS] test_collapse_with_gust_at_threshold_not_nulled")


def test_rxcheck_at_threshold_not_nulled():
    # Exactly AT the rxCheckPercent threshold must not trigger (strict '<').
    c = _cacher()
    rec = _record(windGust=37.0, rxCheckPercent=20.0)
    c.new_archive_record(_Event(rec))
    assert rec['windGust'] == 37.0
    print("  [PASS] test_rxcheck_at_threshold_not_nulled")


# --- Absent data: nothing to guard, must not crash ---------------------------

def test_missing_rxcheckpercent_no_action():
    c = _cacher()
    rec = _record(windGust=37.0, rxCheckPercent=None)
    c.new_archive_record(_Event(rec))
    assert rec['windGust'] == 37.0
    print("  [PASS] test_missing_rxcheckpercent_no_action")


def test_missing_windgust_no_action():
    c = _cacher()
    rec = _record(windGust=None, rxCheckPercent=9.2)
    c.new_archive_record(_Event(rec))
    assert rec['windGust'] is None  # unchanged, still None -- no crash
    print("  [PASS] test_missing_windgust_no_action")


# --- Units: the threshold is stated in mph, converted at point of use (#224) -

def test_metricwx_units_converted_before_threshold_check():
    # 37 mph corrupt gust, expressed in m/s (METRICWX), must still trigger --
    # left unconverted this would read as ~37 m/s (~83 mph) and still trigger,
    # but the REVERSE bug (thinking a small m/s value is already mph) must not
    # let a real corrupt event slip through. Use a value that only crosses the
    # 10 mph line AFTER conversion: 37 mph == 16.541 m/s.
    c = _cacher()
    rec = _record(windGust=16.541, rxCheckPercent=9.2, usUnits=weewx.METRICWX)
    c.new_archive_record(_Event(rec))
    assert rec['windGust'] is None, "m/s reading was not converted before the mph threshold check"
    print("  [PASS] test_metricwx_units_converted_before_threshold_check")


def test_metricwx_calm_wind_not_nulled():
    # 2 mph in calm conditions, expressed in m/s (~0.894 m/s) -- must not trigger
    # even during a collapse, confirming the conversion doesn't inflate a small
    # calm reading past the threshold.
    c = _cacher()
    rec = _record(windGust=0.894, rxCheckPercent=6.2, usUnits=weewx.METRICWX)
    c.new_archive_record(_Event(rec))
    assert rec['windGust'] == 0.894
    print("  [PASS] test_metricwx_calm_wind_not_nulled")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
    print("\n%d/%d passed" % (len(tests), len(tests)))
