"""Offline regression test for the post-mortem stderr drain (S62, ERR-0005).

The bug had two layers, and only the first was visible in the log.

Layer 1 -- genLoopPackets' "process is not running" branch ended with
    logerr("err: %s" % self._mgr.get_stderr())
get_stderr() is a GENERATOR function, so this formatted the generator's repr.
Every occurrence in weewx.log read literally
    ERROR err: <generator object ProcManager.get_stderr at 0x7fc44075f6a0>
and the real stderr was never read.

Layer 2 -- and iterating it would not have helped. get_stderr()'s loop is
gated on running():
    while self.running() and int(time.time()) - start_time < 10:
That branch executes precisely BECAUSE running() went false, so the generator
exits on its first condition check and yields nothing. The dying process's
last words sit in stderr_queue and are discarded.

During the 2026-08-02 outage (ERR-0005) this discarded the one piece of
evidence that would have shortened a 105-minute incident: rtldavis's own
reason for exiting immediately on startup.

drain_stderr() is the fix -- shaped like the already-correct get_stdout():
drain the queue, no running() gate, bounded. These tests pin both halves,
including the reason the sibling method exists, so nobody "simplifies" it
back into get_stderr() later.

weewx is not installed in the test/CI environment, so we stub the weewx
modules in sys.modules before importing the driver (same pattern as
test_parse_raw_channel / test_rain_filter).

Run:  python3 -m pytest tests/   OR   python3 tests/test_stderr_drain.py
"""
import inspect
import itertools
import os
import queue
import sys
import time
import types

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
from rtldavis import ProcManager, RtldavisDriver  # noqa: E402


class _DeadProcess:
    """poll() returning non-None is how Popen reports 'already exited',
    so ProcManager.running() is False -- the ERR-0005 state."""
    def poll(self):
        return 1


class _LiveProcess:
    def poll(self):
        return None


def _dead_mgr(lines=()):
    mgr = ProcManager()
    mgr._process = _DeadProcess()
    for line in lines:
        mgr.stderr_queue.put(line)
    return mgr


def test_drain_returns_stderr_after_process_died():
    """The whole point: a dead process's last words must still be readable."""
    mgr = _dead_mgr([b"rtldavis: cannot open device\n",
                     b"usb_claim_interface error -6\n"])
    out = mgr.drain_stderr()
    assert out == ["rtldavis: cannot open device",
                   "usb_claim_interface error -6"]


def test_get_stderr_yields_nothing_once_dead():
    """Layer 2, pinned. This is WHY drain_stderr exists -- if this ever starts
    returning the lines, get_stderr's running() gate changed and the hot path
    at genLoopPackets needs re-examining before this sibling is removed."""
    mgr = _dead_mgr([b"rtldavis: cannot open device\n"])
    assert list(mgr.get_stderr()) == []
    # and the line is still sitting in the queue, undelivered
    assert mgr.stderr_queue.qsize() == 1


def test_drain_returns_a_list_not_a_generator():
    """Layer 1, pinned. The original bug was formatting a generator's repr.
    Keeping the return a real list is what makes the call site's join() and
    its empty-check honest."""
    out = _dead_mgr([b"x\n"]).drain_stderr()
    assert isinstance(out, list)
    assert "generator object" not in ("%s" % out)


def test_drain_is_bounded():
    """A dying process must not be able to dump an unbounded log into
    weewx.log."""
    mgr = _dead_mgr([b"line %d\n" % i for i in range(120)])
    out = mgr.drain_stderr(max_lines=50)
    assert len(out) == 50
    assert out[0] == "line 0"


def test_drain_empty_queue_is_empty_list():
    """Reachability of the call site's 'no stderr captured' branch: an empty
    drain must be distinguishable from a failed one."""
    assert _dead_mgr([]).drain_stderr() == []


def test_running_reflects_poll():
    """Guards the premise of every test above."""
    mgr = ProcManager()
    mgr._process = _DeadProcess()
    assert mgr.running() is False
    mgr._process = _LiveProcess()
    assert mgr.running() is True


class _RecordingEmptyQueue:
    """Records every timeout it's called with; always raises queue.Empty
    immediately -- no real blocking. This test is about what timeout value
    get_stderr() PASSES, not about real queue/wall-clock timing."""
    def __init__(self):
        self.timeouts = []

    def get(self, block, timeout):
        self.timeouts.append(timeout)
        raise queue.Empty()


def test_get_stderr_budgets_remaining_time_not_a_fresh_10s(monkeypatch):
    """Finding #4 (issue #219): the while guard checked elapsed time BEFORE
    each blocking get(), but the call itself used a hardcoded 10s timeout --
    a quick arrival near the 10s boundary let the guard pass with e.g. 9s
    elapsed, then the hardcoded get(True, 10) could block a full second 10s,
    letting one get_stderr() call run up to ~20s. genLoopPackets' 150s stall
    watchdog and 300s drought log only re-check once per full get_stderr()
    exhaustion (rtldavis.py ~1457-1479), so this doubled how late those
    checks could fire.

    time.time() sequence: 0 (start_time), 9 (1st budget check -- 9s
    elapsed, 1s left), 10+ (2nd check -- budget exhausted, loop exits).
    Pre-fix, the recorded timeout is always the hardcoded 10, ignoring the
    1s actually left. Post-fix, it's budgeted down to 1."""
    times = iter(itertools.chain([0, 9], itertools.repeat(10)))
    monkeypatch.setattr(time, "time", lambda: next(times))
    mgr = ProcManager()
    mgr._process = _LiveProcess()
    fake_q = _RecordingEmptyQueue()
    mgr.stderr_queue = fake_q
    list(mgr.get_stderr())
    assert fake_q.timeouts == [1], (
        "get_stderr() must budget its blocking get() to the time left in "
        "its 10s cap, not a fresh 10s every call -- got %r" % fake_q.timeouts)


def test_get_stdout_not_wired_into_the_live_driver_path():
    """Fix #3 (issue #219): stdout_queue is safe to leave undrained only
    because nothing in the live driver path ever calls get_stdout() -- a
    documented, unpinned assumption (see the comment on ProcManager.
    get_stdout()). Tripwire, not a fix: if someone wires get_stdout() into
    genLoopPackets later, this fails and points back at that assumption
    instead of the queue growth showing up as a mystery leak first."""
    src = inspect.getsource(RtldavisDriver.genLoopPackets)
    assert "get_stdout" not in src


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
