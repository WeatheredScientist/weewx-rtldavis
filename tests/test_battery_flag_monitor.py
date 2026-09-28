"""Offline unit tests for the monitor's ISS low-battery flag (#394, DEC-0203).

The driver archives the ISS battery-low bit as txBatteryStatus. Through
2026-09-28 it was set in exactly 10 archived minutes, each a lone minute at a
freeze or reception-collapse onset (rxCheckPercent 2-19%): corrupt frames, not a
battery. These tests pin the gate that keeps those out of an alert while a real
weak battery (the flag on minute after minute of healthy reception) gets through:

  * the 10 real flagged minutes, replayed, never alert;
  * any number of flagged minutes with collapsed reception never alert (the gate
    itself, not just the count threshold);
  * BATTERY_LOW_MIN_MINUTES healthy flagged minutes do, and one fewer does not;
  * the one-shot email fires once, holds through 'watch' blocks, re-arms only
    after a fully clear block;
  * a temp .sdb round-trips; a missing DB or a schema without the column returns
    None without raising.

weewx_monitor.py writes a pidfile at import; `--test-alert` in argv bypasses that
guard, letting the module import cleanly without touching a running monitor.

Run:  python3 -m pytest tests/    OR    python3 tests/test_battery_flag_monitor.py
"""
import os
import sys
import sqlite3
import tempfile

# Bypass the module's PID guard so importing it doesn't touch a running monitor.
sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402

# log() appends to a host-only path in prod; redirect it to a temp file.
_logfd, _logpath = tempfile.mkstemp(prefix="weewx_test_", suffix=".log")
os.close(_logfd)
wm.LOG = _logpath

T0 = 1_790_000_000
N = wm.BATTERY_LOW_MIN_MINUTES

# rxCheckPercent of each of the 10 real flagged minutes (08-30 -> 09-25), in order.
REAL_FLAG_RX = [3.51, 1.98, 18.18, 16.19, 19.10, 13.41, 9.28, 10.75, 13.51, 15.69]


def _block(flags, rx=100.0, minutes=360):
    """A 6 h block of clean minutes, then FLAGS as (rx, flag) minutes."""
    rows = [(T0 + 60 * i, rx, 0.0) for i in range(minutes)]
    rows += [(T0 + 60 * (minutes + i), r, f) for i, (r, f) in enumerate(flags)]
    return rows


def test_real_flag_history_never_alerts():
    # the worst real block held one flagged minute; replay each in its own block
    for rx in REAL_FLAG_RX:
        b = wm.summarize_battery_rows(_block([(rx, 1.0)]))
        assert not b['low'] and b['flagged_healthy'] == 0
        assert b['flagged_other'] == 1


def test_collapsed_reception_flags_never_alert_even_many():
    # the gate, not the count: ten corrupt-frame minutes in one block stay out
    b = wm.summarize_battery_rows(_block([(rx, 1.0) for rx in REAL_FLAG_RX]))
    assert b['flagged_other'] == 10
    assert b['flagged_healthy'] == 0 and not b['low']


def test_threshold_boundary():
    below = wm.summarize_battery_rows(_block([(100.0, 1.0)] * (N - 1)))
    at = wm.summarize_battery_rows(_block([(100.0, 1.0)] * N))
    assert below['flagged_healthy'] == N - 1 and not below['low']
    assert at['flagged_healthy'] == N and at['low']


def test_sustained_weak_battery_alerts():
    # a weak cell flags every packet, so most healthy minutes carry the flag
    b = wm.summarize_battery_rows([(T0 + 60 * i, 100.0, 1.0) for i in range(300)])
    assert b['low'] and b['flagged_healthy'] == 300 and b['healthy'] == 300


def test_healthy_gate_is_inclusive_and_null_rx_is_not_healthy():
    b = wm.summarize_battery_rows([
        (T0, float(wm.BATTERY_HEALTHY_RX_PCT), 1.0),        # exactly at the gate
        (T0 + 60, wm.BATTERY_HEALTHY_RX_PCT - 0.1, 1.0),    # just under
        (T0 + 120, None, 1.0),                              # restart partial
    ])
    assert b['healthy'] == 1 and b['flagged_healthy'] == 1
    assert b['flagged_other'] == 2


def test_null_flag_rows_skipped_and_all_null_is_none():
    assert wm.summarize_battery_rows([(T0, 100.0, None), (T0 + 60, 90.0, None)]) is None
    assert wm.summarize_battery_rows([]) is None
    b = wm.summarize_battery_rows([(T0, 100.0, None), (T0 + 60, 100.0, 0.0)])
    assert b['healthy'] == 1 and b['flagged_healthy'] == 0


def test_format_battery_line_states():
    ok = wm.format_battery_line(wm.summarize_battery_rows(_block([])))
    assert ok.startswith("ISS battery: OK") and "360" in ok
    watch = wm.format_battery_line(wm.summarize_battery_rows(_block([(100.0, 1.0)])))
    assert watch.startswith("ISS battery: watch") and "alert at %d" % N in watch
    low = wm.format_battery_line(wm.summarize_battery_rows(_block([(100.0, 1.0)] * N)))
    assert low.startswith("ISS battery: LOW")
    aside = wm.format_battery_line(wm.summarize_battery_rows(_block([(9.28, 1.0)])))
    assert aside.startswith("ISS battery: OK") and "set aside" in aside


def test_alert_hysteresis():
    low = {'low': True, 'flagged_healthy': N}
    watch = {'low': False, 'flagged_healthy': 1}
    clear = {'low': False, 'flagged_healthy': 0}
    alerted = False
    sent = []
    for b in (low, low, watch, low, None, clear, watch, low):
        send, alerted = wm.battery_alert_decision(b, alerted)
        sent.append(send)
    # fires on the first LOW; holds through LOW/watch/None; a clear block re-arms;
    # a watch block after that does not fire; the next LOW does
    assert sent == [True, False, False, False, False, False, False, True]


def _temp_sdb(columns, rows):
    fd, path = tempfile.mkstemp(prefix="weewx_test_", suffix=".sdb")
    os.close(fd)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE archive (%s)" % columns)
    con.executemany("INSERT INTO archive VALUES (%s)" %
                    ",".join("?" * len(rows[0])), rows)
    con.commit()
    con.close()
    return path


def test_db_battery_summary_reads_temp_sdb():
    rows = [(T0 + 60 * i, 1, 100.0, 1.0) for i in range(N)]      # in window, flagged
    rows += [(T0 + 60 * N, 1, 9.28, 1.0)]                         # collapse artifact
    rows += [(T0 - 86400, 1, 100.0, 1.0)]                         # outside the window
    path = _temp_sdb("dateTime INTEGER, interval INTEGER, rxCheckPercent REAL, "
                     "txBatteryStatus REAL", rows)
    try:
        b = wm.db_battery_summary(T0, T0 + 6 * 3600, db_path=path)
        assert b['flagged_healthy'] == N and b['flagged_other'] == 1 and b['low']
    finally:
        os.unlink(path)


def test_db_battery_summary_missing_db_or_column_returns_none():
    assert wm.db_battery_summary(0, 86400, db_path="/nonexistent/weewx.sdb") is None
    path = _temp_sdb("dateTime INTEGER, interval INTEGER, rxCheckPercent REAL",
                     [(T0, 1, 100.0)])
    try:
        assert wm.db_battery_summary(T0, T0 + 60, db_path=path) is None
    finally:
        os.unlink(path)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
