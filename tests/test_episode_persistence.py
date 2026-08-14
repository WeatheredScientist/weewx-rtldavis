"""Offline unit tests for the S82b episode-state mirror (weewx_monitor.py, #180).

EP is module memory, and a monitor restart mid-episode (every deploy is one)
used to silently lose the open episode: no episodes.log row -- the
pre-registered LNA-verdict datum -- no RECEPTION RECOVERY line for
rx_experiment.sh's fast resume path, and the ALERT email never got its
RECOVERY pair. episode_persist()/episode_load() mirror the open episode to
EPISODE_STATE so a restart resumes it instead.

Same import pattern as test_episode_ledger.py: weewx_monitor writes a pidfile
at import; '--test-alert' in argv bypasses that guard.

Run:  python3 -m pytest tests/   OR   python3 tests/test_episode_persistence.py
"""
import json
import os
import sys

sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402


def _fresh_episode_state():
    wm.EP.update({'onset': 0.0, 'stalls': 0, 'resets': 0, 'respawns': 0,
                  'droughts': 0, 'worst_avg': 100.0, 'last_cmd': ''})


def _use_paths(tmp_path, monkeypatch):
    state = tmp_path / "monitor_episode.state"
    ledger = tmp_path / "episodes.log"
    monkeypatch.setattr(wm, "EPISODE_STATE", str(state))
    monkeypatch.setattr(wm, "EPISODES_LOG", str(ledger))
    monkeypatch.setattr(wm, "log", lambda m: None)
    return state, ledger


def test_open_writes_the_mirror(tmp_path, monkeypatch):
    state, _ = _use_paths(tmp_path, monkeypatch)
    _fresh_episode_state()
    wm.episode_open(avg=12.0, now=1_700_000_000.0)
    saved = json.loads(state.read_text())
    assert saved['onset'] == 1_700_000_000.0
    assert saved['worst_avg'] == 12.0


def test_restart_mid_episode_restores_it(tmp_path, monkeypatch):
    """The defect this exists for: open an episode, accumulate counters,
    simulate a monitor restart (fresh EP), and the load must bring the whole
    episode back so the eventual close writes one honest row."""
    state, ledger = _use_paths(tmp_path, monkeypatch)
    _fresh_episode_state()
    wm.episode_open(avg=9.0, now=1_700_000_000.0)
    wm.EP['stalls'] = 2
    wm.EP['last_cmd'] = "/usr/local/bin/rtldavis -gain 372 -v"
    wm.episode_persist()

    _fresh_episode_state()                      # the restart: memory gone
    assert wm.EP['onset'] == 0.0
    assert wm.episode_load() is True
    assert wm.EP['onset'] == 1_700_000_000.0
    assert wm.EP['stalls'] == 2
    assert wm.EP['last_cmd'].endswith("-gain 372 -v")

    wm.episode_close(now=1_700_002_000.0)       # recovery after the restart
    rows = ledger.read_text().strip().split("\n")
    assert len(rows) == 1
    assert rows[0].split("|")[2] == "2000"      # duration spans the dead gap


def test_close_removes_the_mirror_after_writing_the_row(tmp_path, monkeypatch):
    """Row-first, then clear: a crash between the two duplicates at worst,
    never loses."""
    state, ledger = _use_paths(tmp_path, monkeypatch)
    _fresh_episode_state()
    wm.episode_open(avg=20.0, now=100.0)
    assert state.exists()
    wm.episode_close(now=200.0)
    assert ledger.exists(), "the ledger row must be written"
    assert not state.exists(), "the mirror must be gone once the row is safe"


def test_load_with_no_file_is_a_noop(tmp_path, monkeypatch):
    _use_paths(tmp_path, monkeypatch)
    _fresh_episode_state()
    assert wm.episode_load() is False
    assert wm.EP['onset'] == 0.0


def test_load_with_corrupt_file_is_swallowed(tmp_path, monkeypatch):
    """A corrupt mirror must not stop the monitor -- it IS the watchdog
    (DEC-0074)."""
    state, _ = _use_paths(tmp_path, monkeypatch)
    logged = []
    monkeypatch.setattr(wm, "log", logged.append)
    state.write_text("{not json")
    _fresh_episode_state()
    assert wm.episode_load() is False
    assert wm.EP['onset'] == 0.0
    assert any("load failed" in m for m in logged)


def test_counter_persist_survives_restart(tmp_path, monkeypatch):
    """Counters mutate outside episode_open/close (the dispatch loop calls
    episode_persist() after each increment); a persist-reload cycle must not
    lose them."""
    _use_paths(tmp_path, monkeypatch)
    _fresh_episode_state()
    wm.episode_open(avg=30.0, now=500.0)
    wm.EP['droughts'] += 1
    wm.episode_persist()
    wm.episode_note_avg(4.0)                    # persists via its own call

    _fresh_episode_state()
    assert wm.episode_load() is True
    assert wm.EP['droughts'] == 1
    assert wm.EP['worst_avg'] == 4.0


def test_persist_failure_never_raises(tmp_path, monkeypatch):
    logged = []
    monkeypatch.setattr(wm, "EPISODE_STATE",
                        str(tmp_path / "no-such-dir" / "episode.state"))
    monkeypatch.setattr(wm, "log", logged.append)
    _fresh_episode_state()
    wm.EP['onset'] = 100.0
    wm.episode_persist()                        # must swallow the OSError
    assert any("persist failed" in m for m in logged)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
