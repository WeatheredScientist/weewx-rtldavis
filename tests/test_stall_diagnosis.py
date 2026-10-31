"""Offline unit tests for the ws.5 stall/drought self-classification (S73).

S67-S73 spent seven sessions unable to tell three outage classes apart after
the fact: child mute (process/USB), child emitting but nothing decoding
(RF-quiet), and genuine reception collapse. ws.5 classifies at the source:

  - the 150s stall raise is preceded by a STALL DIAGNOSIS line whose
    raw-stderr count discriminates mute (0) from emitting (>0);
  - the RF-quiet case NEVER trips the 150s watchdog (hop-only packets reset
    it -- rtldavis.py line ~1401), so a periodic DATA DROUGHT line covers it.

The helpers are pure static methods so these tests pin the classification
logic without a live process. Same weewx-stub pattern as
test_procmanager_reap.py.

Run:  python3 -m pytest tests/ (pytest only)
"""

from rtldavis import ProcManager  # noqa: E402


# ── STALL DIAGNOSIS ──────────────────────────────────────────────────────────

def test_mute_child_classifies_as_process_usb():
    """Last night's shape: total silence for 150s -- zero raw lines."""
    msg = ProcManager.stall_diagnosis(0, 0)
    assert "raw_stderr_lines=0" in msg
    assert "process/USB class" in msg


def test_emitting_child_classifies_as_rf():
    msg = ProcManager.stall_diagnosis(42, 0)
    assert "raw_stderr_lines=42" in msg
    assert "RF class" in msg


def test_hop_count_is_reported_verbatim():
    msg = ProcManager.stall_diagnosis(10, 7)
    assert "hop_packets=7" in msg


def test_diagnosis_never_alters_the_stall_string():
    """The monitor greps weewx.log for the literal 'rtldavis process stalled'
    (weewx_monitor.py main dispatch); the diagnosis line must not collide
    with or contain it, so counting stalls stays exact."""
    for raw, hops in ((0, 0), (5, 3), (100, 99)):
        assert "rtldavis process stalled" not in ProcManager.stall_diagnosis(raw, hops)


# ── DATA DROUGHT pacing ──────────────────────────────────────────────────────

def test_drought_not_due_while_data_is_fresh():
    assert not ProcManager.drought_due(now=1000, last_data_ts=800,
                                       last_logged_ts=0, threshold=300)


def test_drought_due_after_threshold():
    assert ProcManager.drought_due(now=1301, last_data_ts=1000,
                                   last_logged_ts=0, threshold=300)


def test_drought_log_is_paced_not_spammed():
    """Once logged, the next line waits a full threshold."""
    assert not ProcManager.drought_due(now=1400, last_data_ts=1000,
                                       last_logged_ts=1301, threshold=300)
    assert ProcManager.drought_due(now=1601, last_data_ts=1000,
                                   last_logged_ts=1301, threshold=300)


def test_default_threshold_is_five_minutes():
    """300s is deliberate: longer than the 150s stall watchdog (a mute child
    stalls first, so a drought line always means the child was emitting) and
    short enough to catch an episode within its first guard window."""
    assert ProcManager.DROUGHT_S == 300
