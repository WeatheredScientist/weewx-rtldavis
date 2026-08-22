"""Offline unit tests for the ws.5 child-reaping fix (S73).

The 2026-08-11 forensics captures showed three rtldavis pids stacked under one
weewxd -- two of them zombies -- because every kill in ProcManager went through
pidof + os.kill with no wait(), and the engine builds a FRESH ProcManager on
each WeeWxIOError retry, so no instance ever held a handle to its
predecessor's corpse. ws.5 registers every spawned child in a module-level
list and reaps (poll()s) it on shutdown and before each startup.

These tests drive the real ProcManager against real short-lived child
processes (/bin/sleep), with get_pid monkeypatched out: pidof does not exist
on the dev machine, and the sweep's job (killing strays by name) is not what
is under test here -- reaping is.

weewx is not installed in the test/CI environment, so we stub it (same
pattern as test_duplicate_frame_counter.py).

Run:  python3 -m pytest tests/   OR   python3 tests/test_procmanager_reap.py
"""
import os
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
_weewx.WeeWxIOError = type("WeeWxIOError", (IOError,), {})
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
import rtldavis  # noqa: E402


def _quiet_manager(monkeypatch):
    """A ProcManager whose name-based kill sweep is inert (no pidof here)."""
    mgr = rtldavis.ProcManager()
    monkeypatch.setattr(rtldavis.ProcManager, "get_pid", lambda self, name: [])
    return mgr


def _raising_manager(monkeypatch):
    """A ProcManager whose get_pid ALWAYS raises -- the shape when pidof
    finds nothing, which is the common case (the child already exited on
    its own). Unlike _quiet_manager, get_pid here never returns quietly, so
    it can see the gap _quiet_manager's own docstring admits the suite was
    blind to (issue #219, finding #1)."""
    mgr = rtldavis.ProcManager()

    def _raise(self, name):
        raise rtldavis.subprocess.CalledProcessError(1, ["pidof", name])
    monkeypatch.setattr(rtldavis.ProcManager, "get_pid", _raise)
    return mgr


def _drain_registry():
    """Isolate each test from children other tests left registered."""
    rtldavis._SPAWNED_CHILDREN.clear()


def test_startup_registers_the_child(monkeypatch):
    _drain_registry()
    mgr = _quiet_manager(monkeypatch)
    mgr.startup("/bin/sleep 30")
    try:
        assert len(rtldavis._SPAWNED_CHILDREN) == 1
        assert rtldavis._SPAWNED_CHILDREN[0] is mgr._process
    finally:
        mgr._process.kill()
        mgr._process.wait(timeout=5)
        _drain_registry()


def test_shutdown_reaps_the_killed_child(monkeypatch):
    """The defect: SIGKILL with no wait() left a zombie. shutdown() must
    collect the corpse -- returncode set, registry empty."""
    _drain_registry()
    mgr = _quiet_manager(monkeypatch)
    mgr.startup("/bin/sleep 30")
    p = mgr._process
    # shutdown's pidof sweep is inert under the monkeypatch, so kill the
    # child the way the sweep would have, then let shutdown reap it.
    p.kill()
    mgr.shutdown()
    assert p.returncode is not None
    assert rtldavis._SPAWNED_CHILDREN == []


def test_startup_reaps_a_predecessors_corpse(monkeypatch):
    """The engine's retry path builds a NEW ProcManager; its startup() must
    reap what the previous instance's kill left behind."""
    _drain_registry()
    old = _quiet_manager(monkeypatch)
    old.startup("/bin/sleep 30")
    old_child = old._process
    old_child.kill()                       # die without ever being wait()ed
    # Give the kernel a beat to transition the child to zombie.
    deadline = time.time() + 5
    while old_child.poll() is None and time.time() < deadline:
        time.sleep(0.05)

    new = rtldavis.ProcManager()
    new.startup("/bin/sleep 30")
    try:
        assert old_child not in rtldavis._SPAWNED_CHILDREN
        assert old_child.returncode is not None
        assert len(rtldavis._SPAWNED_CHILDREN) == 1
    finally:
        new._process.kill()
        new._process.wait(timeout=5)
        _drain_registry()


def test_reap_returns_count_and_keeps_the_living(monkeypatch):
    _drain_registry()
    mgr = _quiet_manager(monkeypatch)
    mgr.startup("/bin/sleep 30")
    live = mgr._process
    dead = rtldavis.subprocess.Popen(["/bin/sleep", "0.01"])
    rtldavis._SPAWNED_CHILDREN.append(dead)
    dead.wait(timeout=5)                   # exits on its own; stays registered
    rtldavis._SPAWNED_CHILDREN.append(dead)  # duplicate entry must not crash
    try:
        reaped = rtldavis.reap_spawned_children()
        assert reaped >= 1
        assert live in rtldavis._SPAWNED_CHILDREN
        assert dead not in rtldavis._SPAWNED_CHILDREN
    finally:
        live.kill()
        live.wait(timeout=5)
        _drain_registry()


def test_shutdown_reaps_even_when_get_pid_raises(monkeypatch):
    """Finding #1 (issue #219): shutdown()'s get_pid() call was unguarded,
    unlike startup()'s identical call. The common trigger is the child
    already having exited on its own (a stall/reset) -- pidof then finds
    nothing and raises, which used to abort shutdown() BEFORE the wait()+
    reap below ever ran, silently skipping the S73/DEC-0081 zombie-reap fix
    for exactly the case it is most needed. Pre-fix this test fails with
    the natural CalledProcessError traceback; post-fix, shutdown() reaps."""
    _drain_registry()
    mgr = _raising_manager(monkeypatch)
    mgr.startup("/bin/sleep 0.1")
    p = mgr._process
    p.wait(timeout=5)          # let it genuinely exit before shutdown() runs
    mgr.shutdown()              # must NOT raise, even though get_pid() does
    assert p.returncode is not None
    assert rtldavis._SPAWNED_CHILDREN == []


def test_shutdown_kills_the_child_when_pidof_misses_it(monkeypatch):
    """The gap issue #233 describes: pidof matching nothing does not always
    mean the child already exited (that's _raising_manager's case above) --
    it can also mean pidof failed to MATCH a child that is still alive.
    Pre-fix, the pidof sweep was the only thing that ever signaled the
    child, so an empty match left shutdown() with nothing to kill: the
    wait(timeout=5) below just timed out over a still-running orphan.
    shutdown() must end the child via its own Popen handle regardless of
    what pidof found."""
    _drain_registry()
    mgr = _quiet_manager(monkeypatch)
    mgr.startup("/bin/sleep 30")
    p = mgr._process
    mgr.shutdown()          # pidof sweep is inert; nothing else may kill p
    assert p.returncode is not None
    assert rtldavis._SPAWNED_CHILDREN == []


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
