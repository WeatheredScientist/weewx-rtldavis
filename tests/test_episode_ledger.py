"""Offline unit tests for the S73 episode ledger (weewx_monitor.py).

One pipe-delimited row per reception episode (ALERT -> RECOVERY), written at
recovery, so the LNA verdict and post-campaign analysis read one file instead
of re-deriving episodes from three logs. Fields:

  onset_iso|recovery_iso|duration_s|stalls|resets|respawns|droughts|worst_avg_pct|last_cmd

Same import pattern as test_watchdog_escalation.py: weewx_monitor writes a
pidfile at import; '--test-alert' in argv bypasses that guard.

Run:  python3 -m pytest tests/   OR   python3 tests/test_episode_ledger.py
"""
import os
import sys

sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402


def _fresh_episode_state():
    wm.EP.update({'onset': 0.0, 'stalls': 0, 'resets': 0, 'respawns': 0,
                  'droughts': 0, 'worst_avg': 100.0, 'last_cmd': ''})


def _use_ledger(tmp_path, monkeypatch):
    path = tmp_path / "episodes.log"
    monkeypatch.setattr(wm, "EPISODES_LOG", str(path))
    monkeypatch.setattr(wm, "log", lambda m: None)
    return path


def test_open_then_close_writes_one_row(tmp_path, monkeypatch):
    ledger = _use_ledger(tmp_path, monkeypatch)
    _fresh_episode_state()
    wm.episode_open(avg=9.0, now=1_700_000_000.0)
    wm.EP['stalls'] = 2
    wm.EP['resets'] = 1
    wm.EP['respawns'] = 3
    wm.EP['droughts'] = 4
    wm.EP['last_cmd'] = "/usr/local/bin/rtldavis -gain 449 -v"
    wm.episode_close(now=1_700_001_500.0)

    rows = ledger.read_text().strip().split("\n")
    assert len(rows) == 1
    f = rows[0].split("|")
    assert len(f) == 9
    assert f[2] == "1500"                       # duration_s
    assert f[3:7] == ["2", "1", "3", "4"]       # stalls|resets|respawns|droughts
    assert f[7] == "9"                          # worst_avg_pct
    assert f[8].endswith("-gain 449 -v")
    assert wm.EP['onset'] == 0.0                # cleared


def test_close_without_open_is_a_noop(tmp_path, monkeypatch):
    ledger = _use_ledger(tmp_path, monkeypatch)
    _fresh_episode_state()
    wm.episode_close(now=1_700_000_000.0)
    assert not ledger.exists()


def test_worst_avg_tracks_the_minimum(tmp_path, monkeypatch):
    _use_ledger(tmp_path, monkeypatch)
    _fresh_episode_state()
    # A real epoch: onset 0.0 is the no-open-episode sentinel (as in WD),
    # so opening "at epoch zero" would read as closed. Cannot occur live.
    wm.episode_open(avg=40.0, now=1_700_000_000.0)
    wm.episode_note_avg(12.0)
    wm.episode_note_avg(55.0)                   # higher -- must not regress
    assert wm.EP['worst_avg'] == 12.0


def test_note_avg_without_open_episode_is_ignored():
    _fresh_episode_state()
    wm.episode_note_avg(1.0)
    assert wm.EP['worst_avg'] == 100.0


def test_ledger_write_failure_never_raises(tmp_path, monkeypatch):
    """The ledger is telemetry; a write failure must not take the monitor
    down with it (the monitor is the watchdog -- DEC-0074)."""
    monkeypatch.setattr(wm, "EPISODES_LOG",
                        str(tmp_path / "no-such-dir" / "episodes.log"))
    logged = []
    monkeypatch.setattr(wm, "log", logged.append)
    _fresh_episode_state()
    wm.episode_open(avg=5.0, now=100.0)
    wm.episode_close(now=200.0)                 # must swallow the OSError
    assert any("ledger write failed" in m for m in logged)
    assert wm.EP['onset'] == 0.0


def test_open_resets_counters_from_prior_episode(tmp_path, monkeypatch):
    _use_ledger(tmp_path, monkeypatch)
    _fresh_episode_state()
    wm.EP['stalls'] = 7
    wm.EP['last_cmd'] = "stale"
    wm.episode_open(avg=30.0, now=50.0)
    assert wm.EP['stalls'] == 0
    assert wm.EP['last_cmd'] == ""
    assert wm.EP['worst_avg'] == 30.0


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
