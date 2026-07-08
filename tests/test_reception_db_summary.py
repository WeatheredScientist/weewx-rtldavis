"""Offline unit tests for the archive-sourced reception summary (Layer A, S31).

The daily RF-reception email used to be built from a scrape of `Wunderground-RF:
Published` log lines. That count measures publish LIVENESS, not RF reception: it
runs ~21+/min (padded by freqError freq-hop publishes, DEC-0024) and reads ~100%
even when the driver's own decode metric shows ~75% packet reception (S31 audit).
The honest metric is the driver's rxCheckPercent -- good CRC-decoded packets /
theoretical max per archive period -- already stored per record in the archive DB.

These tests exercise the REAL `summarize_reception_rows` (pure math),
`db_reception_summary` (against a temp sqlite archive), and `format_db_daily_summary`
from weewx_monitor.py, so the deployed behaviour is under test:

  * mean %, min %, and DROPPED packets are computed from expected vs received;
  * NULL-rxCheckPercent records count as gaps, excluded from the totals;
  * rows group into local-hour buckets; an empty day yields None;
  * a real temp .sdb round-trips; a missing DB returns None without raising;
  * the formatted email actually reports "Packets dropped".

weewx_monitor.py writes a pidfile at import; `--test-alert` in argv bypasses that
guard, letting the module import cleanly without touching a running monitor.

Run:  python3 -m pytest tests/    OR    python3 tests/test_reception_db_summary.py
"""
import os
import sys
import sqlite3
import tempfile
from datetime import datetime

# Bypass the module's PID guard so importing it doesn't touch a running monitor.
sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402

# log() appends to a NAS-only path in prod; redirect it to a temp file so the
# error path (e.g. a missing DB) can log without failing off-target.
_logfd, _logpath = tempfile.mkstemp(prefix="weewx_test_", suffix=".log")
os.close(_logfd)
wm.LOG = _logpath


def test_basic_mean_min_and_dropped():
    # tx_per_min=20, interval=1 => 20 packets expected per record.
    # pcts [100, 50] -> received 20 + 10 = 30, expected 40, dropped 10, mean 75%.
    rows = [(100000, 1, 100.0), (100060, 1, 50.0)]
    s = wm.summarize_reception_rows(rows, 20.0)
    assert s['records'] == 2
    assert abs(s['expected'] - 40.0) < 1e-9
    assert abs(s['received'] - 30.0) < 1e-9
    assert abs(s['dropped'] - 10.0) < 1e-9
    assert abs(s['mean_pct'] - 75.0) < 1e-9
    hour = next(iter(s['hours'].values()))
    assert hour['min_pct'] == 50.0


def test_null_rows_are_gaps_excluded_from_totals():
    # A NULL rxCheckPercent carries no reception info -> counted as a gap, not a drop.
    rows = [(100000, 1, 80.0), (100060, 1, None), (100120, 1, None)]
    s = wm.summarize_reception_rows(rows, 20.0)
    assert s['records'] == 1          # only the one non-null record
    assert s['gaps'] == 2
    assert abs(s['expected'] - 20.0) < 1e-9   # gaps not in expected
    assert abs(s['dropped'] - 4.0) < 1e-9     # 20 * (1 - 0.80)


def test_rows_group_into_local_hour_buckets():
    # Two timestamps 2h apart fall in different local hours regardless of TZ.
    rows = [(100000, 1, 90.0), (100000 + 7200, 1, 70.0)]
    s = wm.summarize_reception_rows(rows, 20.0)
    assert len(s['hours']) == 2


def test_empty_day_returns_none():
    assert wm.summarize_reception_rows([], 20.0) is None


def test_db_reception_summary_reads_temp_sdb():
    fd, path = tempfile.mkstemp(prefix="weewx_test_", suffix=".sdb")
    os.close(fd)
    try:
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE archive (dateTime INTEGER, interval INTEGER, "
                    "rxCheckPercent REAL)")
        # Three records in one known local day; one in the day before (must be excluded).
        base = int(datetime(2026, 7, 6, 12, 0, 0).timestamp())
        con.executemany(
            "INSERT INTO archive VALUES (?,?,?)",
            [(base, 1, 100.0), (base + 60, 1, 50.0), (base + 120, 1, None),
             (base - 86400, 1, 10.0)])
        con.commit()
        con.close()

        day = datetime(2026, 7, 6).date()
        s = wm.db_reception_summary(day, db_path=path)
        assert s is not None
        assert s['records'] == 2      # two non-null in-day rows; prior day excluded
        assert s['gaps'] == 1
        # mean over the two in-day rows = (100 + 50) / 2 = 75% (packet-weighted, equal expected)
        assert abs(s['mean_pct'] - 75.0) < 1e-6
        assert s['dropped'] > 0
    finally:
        os.unlink(path)


def test_db_reception_summary_missing_db_returns_none():
    assert wm.db_reception_summary(datetime(2026, 7, 6).date(),
                                   db_path="/nonexistent/weewx.sdb") is None


def test_format_reports_dropped_and_mean():
    rows = [(100000, 1, 100.0), (100060, 1, 50.0)]
    s = wm.summarize_reception_rows(rows, 20.0)
    out = wm.format_db_daily_summary(s, "2026-07-06")
    assert "Packets dropped (est):" in out
    assert "Daily mean reception:" in out
    assert "rxCheckPercent" in out


ALL_TESTS = [
    test_basic_mean_min_and_dropped,
    test_null_rows_are_gaps_excluded_from_totals,
    test_rows_group_into_local_hour_buckets,
    test_empty_day_returns_none,
    test_db_reception_summary_reads_temp_sdb,
    test_db_reception_summary_missing_db_returns_none,
    test_format_reports_dropped_and_mean,
]


if __name__ == "__main__":
    passed = 0
    for t in ALL_TESTS:
        try:
            t()
            passed += 1
            print(f"  [PASS] {t.__name__}")
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
    print(f"\n{passed}/{len(ALL_TESTS)} passed")
    sys.exit(0 if passed == len(ALL_TESTS) else 1)
