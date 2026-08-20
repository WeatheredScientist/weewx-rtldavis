"""Offline regression tests for issue #225 (S91 audit, QC-completeness
gaps): five findings, all dormant on this station's actual single-ISS
configuration, bundled as one tier:mid fix.

  1/2. temp_1/temp_2/humid_1/humid_2/rain_rate were listed in
       FRAME_WEATHER_KEYS (co-rejected when a frame is corrupt) but absent
       from SENSOR_QC_DEFAULTS -- a corrupted reading on any of them could
       never trigger its OWN bounds rejection.
  3. transm_to_store (which transmitter's freqError gets stored, meant to
     rotate every 2 days) was computed once before genLoopPackets' while
     loop and never recomputed inside it, so the rotation only ever
     happened across a process restart.
  4. The legacy v12 freqError decode has no Transmitter field to gate on
     (unlike v13), so with more than one active transmitter it silently
     mixed transmitters' freqError data into the same fields.
  5. pct_good per-transmitter storage tested `self.sensor_map[k] in data`
     where `data` had been rebound to a plain string -- substring
     containment, not the intended equality test.

weewx is not installed in the test/CI environment, so we stub the weewx
modules in sys.modules before importing the driver (same pattern as
test_sensor_qc.py / test_reception_stats.py).

Run:  python3 -m pytest tests/test_issue_225_qc_fixes.py
"""
import os
import sys
import time
import types

import pytest

# --- stub the weewx deps so rtldavis.py imports without weewx installed ---
def _pkg(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m

def _mod(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

class _AbstractDevice:
    def __init__(self, *a, **k): pass
class _AbstractConfEditor:
    pass
class _StdService:
    def __init__(self, *a, **k): pass

_weewx = _pkg("weewx")
_weewx.__version__ = "5.3.1"
_weewx.METRICWX = 16
_drivers = _mod("weewx.drivers")
_drivers.AbstractDevice = _AbstractDevice
_drivers.AbstractConfEditor = _AbstractConfEditor
_engine = _mod("weewx.engine")
_engine.StdService = _StdService
_units = _mod("weewx.units")
for _d in ("obs_group_dict", "USUnits", "MetricUnits", "MetricWXUnits",
           "default_unit_format_dict", "default_unit_label_dict"):
    setattr(_units, _d, {})
_crc16 = _mod("weewx.crc16")
_crc16.crc16 = lambda *a, **k: 0
_weewx.drivers, _weewx.engine, _weewx.units, _weewx.crc16 = (
    _drivers, _engine, _units, _crc16)

_weeutil = _pkg("weeutil")
_wu = _mod("weeutil.weeutil")
_wu.tobool = lambda v: str(v).lower() in ("1", "true", "yes", "on")
_wlog = _mod("weeutil.logger")
_weeutil.weeutil, _weeutil.logger = _wu, _wlog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rtldavis import (  # noqa: E402
    CHANNELPacket, RtldavisDriver, SensorQC)

T0 = 1_000_000.0  # arbitrary epoch for the fake clock


# ── Items 1/2: SENSOR_QC_DEFAULTS gains the 4 extra-sensor fields + rain_rate

@pytest.mark.parametrize("key,bad_value", [
    ("temp_1", 200.0),
    ("temp_2", -200.0),
    ("humid_1", 150.0),
    ("humid_2", -10.0),
    ("rain_rate", 1000.0),
])
def test_previously_unchecked_field_now_bounds_rejected(key, bad_value):
    v, why = SensorQC().check(key, bad_value, T0)
    assert v is None and "range" in why


def test_humid_1_and_2_share_humiditys_bounds_exactly():
    qc = SensorQC()
    assert qc.limits["humid_1"] == qc.limits["humidity"]
    assert qc.limits["humid_2"] == qc.limits["humidity"]


def test_temp_1_and_2_share_temperatures_bounds_exactly():
    qc = SensorQC()
    assert qc.limits["temp_1"] == qc.limits["temperature"]
    assert qc.limits["temp_2"] == qc.limits["temperature"]


def test_rain_rate_matches_the_stdqc_backstop_upper_bound():
    # weewx.conf.example's StdQC backstop: rainRate = 0, 16, inch_per_hour
    # -- 16 in/h * 25.4 mm/in, this driver's internal rain_rate unit.
    lo, hi, _max_delta = SensorQC().limits["rain_rate"]
    assert lo == 0.0
    assert hi == pytest.approx(16 * 25.4)


# ── Item 5: pct_good storage, equality not substring containment ──────────

def _make_driver(active_tr_ids):
    """Bare object carrying just the state new_archive_record touches.
    __init__ is skipped (it spawns a subprocess)."""
    d = RtldavisDriver.__new__(RtldavisDriver)
    RtldavisDriver._init_stats(d)
    for i, tr_id in enumerate(active_tr_ids):
        d.stats["activeTrIds"][i] = tr_id
    return d


def test_pct_good_storage_uses_equality_not_substring_containment():
    """The regression this pins: an empty sensor_map value (a plausible
    user config typo) is a substring of every 'pct_good_N' string, so
    under `in` it would match and get overwritten on every transmitter
    iteration instead of never matching at all."""
    d = _make_driver(active_tr_ids=[0, 1])
    d._save_pct_good_per_transmitter = True
    d.tr_count = 2
    d.sensor_map = {"bogusField": ""}  # never a real "pct_good_N" value

    # Period 1: establish baselines.
    d.stats["curr_cnt"][0] = 20
    d.stats["curr_cnt"][1] = 20
    RtldavisDriver._update_summaries(d)
    RtldavisDriver._reset_stats(d)

    # Period 2: both transmitters report real, DIFFERENT counts.
    d.stats["curr_cnt"][0] = 40
    d.stats["curr_cnt"][1] = 60
    d.stats["last_ts"] = int(time.time()) - 60
    event = types.SimpleNamespace(record={})
    RtldavisDriver.new_archive_record(d, event)

    assert "bogusField" not in event.record, (
        "empty sensor_map value matched every transmitter's pct_good "
        "string under substring containment -- got %r"
        % event.record.get("bogusField"))


def test_pct_good_storage_still_stores_a_real_exact_match():
    """The fix must not just stop storing everything -- a genuine exact
    'pct_good_N' mapping still has to work."""
    d = _make_driver(active_tr_ids=[0, 1])
    d._save_pct_good_per_transmitter = True
    d.tr_count = 2
    d.sensor_map = {"extraTemp2": "pct_good_1"}  # a real DEFAULT_SENSOR_MAP entry

    d.stats["curr_cnt"][0] = 20
    d.stats["curr_cnt"][1] = 20
    RtldavisDriver._update_summaries(d)
    RtldavisDriver._reset_stats(d)

    d.stats["curr_cnt"][0] = 40
    d.stats["curr_cnt"][1] = 60
    d.stats["last_ts"] = int(time.time()) - 60

    # Peek at the value _update_summaries computes this period -- idempotent
    # against unchanged curr_cnt/last_cnt/last_ts, so the second call inside
    # new_archive_record below reproduces the same number. Needed because
    # new_archive_record's own _reset_stats() nulls stats['pct_good'] again
    # before this function gets a chance to read it back.
    RtldavisDriver._update_summaries(d)
    expected = d.stats["pct_good"][1]
    assert expected is not None

    event = types.SimpleNamespace(record={})
    RtldavisDriver.new_archive_record(d, event)

    assert event.record.get("extraTemp2") == expected


# ── Item 3: transm_to_store rotates while the driver keeps running ────────

def test_genloop_source_recomputes_transm_to_store_inside_the_loop():
    """genLoopPackets is a long-lived generator (weewx calls it once and
    pulls from it forever) -- the regression this pins is a computation
    that only ran before the `while` loop started, so it could never
    change again for the life of the process. Asserting on the source
    (rather than driving the whole generator, which needs a live
    ProcManager) pins that the assignment lives INSIDE the loop body."""
    import inspect
    src = inspect.getsource(RtldavisDriver.genLoopPackets)
    while_idx = src.index("while self._mgr.running():")
    assign_idx = src.index("self.transm_to_store = new_transm_to_store")
    assert assign_idx > while_idx, (
        "self.transm_to_store's assignment must be inside the while loop, "
        "not computed once before it")


# ── Item 4: legacy v12 freqError has no per-transmitter gate ──────────────

class _FakeLines(list):
    """CHANNELPacket.parse_text takes (self, payload, lines) and calls
    lines.pop(0) -- a real driver instance isn't needed since parse_text
    only reads self.frequency and self.transm_to_store."""


def _channel_stub(frequency="US", tr_count=1):
    stub = types.SimpleNamespace(frequency=frequency, transm_to_store=0,
                                 tr_count=tr_count)
    return stub


def test_v12_freqerror_not_stored_with_multiple_active_transmitters():
    """The regression this pins: PATTERNv12 has no Transmitter field, so
    with tr_count > 1 there is no way to know which transmitter a v12
    freqError came from -- it must not be stored at all rather than
    silently mixed into whichever transmitter's field happens to match
    the channel index."""
    stub = _channel_stub(tr_count=2)
    line = "chan: 13:44:13 Hop: {ChannelIdx:0 ChannelFreq:868437250 FreqError:431}"
    pkt = CHANNELPacket.parse_text(stub, line, _FakeLines([line]))
    assert "freqError0" not in pkt


def test_v12_freqerror_still_stored_with_a_single_transmitter():
    """Single-transmitter stations (this one, tr_count=1) are unambiguous
    even without a Transmitter field -- must keep working."""
    stub = _channel_stub(tr_count=1)
    line = "chan: 13:44:13 Hop: {ChannelIdx:0 ChannelFreq:868437250 FreqError:431}"
    pkt = CHANNELPacket.parse_text(stub, line, _FakeLines([line]))
    assert pkt.get("freqError0") == 431


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
