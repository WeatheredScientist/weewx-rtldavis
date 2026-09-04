"""Offline unit tests for the gain / receive-window hot swap (S103, DEC-0117).

Gain and -ex are startup-only CLI flags on the Go binary, so a hot swap is a
child respawn driven by a watched control file. Three things are worth pinning
here, and they are the three that would hurt in prod:

  1. The control file is a VALIDATED INTEGER CHANNEL, not a command string.
     `cmd` reaches shlex.split() -> Popen, so anything able to write that path
     would otherwise have arbitrary code execution inside the container.
     Unknown keys, non-integers and out-of-range values must all be refused.

  2. The splice must hit the right token and only that token -- including the
     append case, since DEFAULT_CMD carries neither -gain nor -ex.

  3. A swap must reset the stall watchdog and widen it to HOTSWAP_GRACE_S.
     A respawned child restarts its radio init period (US: 133s) against a
     150s watchdog whose timer was NOT reset by the swap -- the naive
     implementation tears the driver down mid-init, reintroducing exactly the
     abort-on-unhealthy-swap failure class the feature exists to retire.

weewx is not installed in the test/CI environment, so we stub it (same pattern
as test_procmanager_reap.py).

Run:  .venv/bin/python -m pytest tests/test_hotswap_control.py
"""
import os
import sys
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


# ── 1. the validated-integer boundary ────────────────────────────────────────

def test_parses_both_keys():
    assert rtldavis.parse_hotswap_control("gain = 496\nex = 50\n") == {
        "gain": 496, "ex": 50}


def test_either_key_alone_is_enough():
    assert rtldavis.parse_hotswap_control("gain = 372") == {"gain": 372}
    assert rtldavis.parse_hotswap_control("ex = 0") == {"ex": 0}


def test_comments_and_blank_lines_ignored():
    text = "# campaign arm B\n\n  gain = 496   # R820T max\n"
    assert rtldavis.parse_hotswap_control(text) == {"gain": 496}


def test_rejects_a_command_string():
    """The whole point of the design: this must never become a shell."""
    with pytest.raises(ValueError):
        rtldavis.parse_hotswap_control(
            "cmd = /usr/local/bin/rtldavis -gain 496; rm -rf /")


def test_rejects_unknown_key():
    with pytest.raises(ValueError, match="unknown key"):
        rtldavis.parse_hotswap_control("ppm = 3")


def test_rejects_non_integer():
    with pytest.raises(ValueError, match="wants an integer"):
        rtldavis.parse_hotswap_control("gain = high")


@pytest.mark.parametrize("text", ["gain = -1", "gain = 497", "ex = 1001"])
def test_rejects_out_of_range(text):
    with pytest.raises(ValueError, match="out of range"):
        rtldavis.parse_hotswap_control(text)


def test_rejects_malformed_and_empty():
    with pytest.raises(ValueError, match="malformed line"):
        rtldavis.parse_hotswap_control("gain 496")
    with pytest.raises(ValueError, match="no settings found"):
        rtldavis.parse_hotswap_control("# nothing but a comment\n")


# ── 2. the splice ────────────────────────────────────────────────────────────

BASE = "/usr/local/bin/rtldavis -gain 372 -v -fc 0 -ppm 0 -ex 0 -tf US -tr 1"


def test_splice_replaces_in_place_without_touching_neighbours():
    out = rtldavis.apply_hotswap_settings(BASE, {"gain": 496, "ex": 50})
    assert out == ("/usr/local/bin/rtldavis -gain 496 -v -fc 0 -ppm 0 "
                   "-ex 50 -tf US -tr 1")


def test_splice_appends_when_flag_absent():
    """DEFAULT_CMD carries neither flag."""
    out = rtldavis.apply_hotswap_settings(rtldavis.DEFAULT_CMD, {"gain": 496})
    assert out.endswith(" -gain 496")
    assert out.startswith(rtldavis.DEFAULT_CMD)


def test_splice_does_not_match_a_longer_flag():
    """-ex must not match inside -extra."""
    cmd = "/bin/rtldavis -extra 7 -ex 0"
    out = rtldavis.apply_hotswap_settings(cmd, {"ex": 50})
    assert out == "/bin/rtldavis -extra 7 -ex 50"


def test_splice_is_idempotent():
    once = rtldavis.apply_hotswap_settings(BASE, {"gain": 496})
    assert rtldavis.apply_hotswap_settings(once, {"gain": 496}) == once


# ── 3. the swap itself, against a fake ProcManager ───────────────────────────

class _FakeMgr:
    """Records the shutdown/startup sequence; can be told to fail a startup."""

    def __init__(self, fail_cmds=()):
        self.fail_cmds = set(fail_cmds)
        self.calls = []

    def shutdown(self):
        self.calls.append(("shutdown", None))

    def startup(self, cmd, path=None, ld_library_path=None):
        self.calls.append(("startup", cmd))
        if cmd in self.fail_cmds:
            raise rtldavis.weewx.WeeWxIOError("failed to start process: %s"
                                              % cmd)

    def started_cmds(self):
        return [c for kind, c in self.calls if kind == "startup"]


def _driver(tmp_path, mgr, cmd=BASE):
    """A bare driver object with only the hot-swap state populated.

    __new__ on purpose: the real __init__ spawns a child and needs a full
    weewx engine. What is under test is the swap logic, not construction.
    """
    d = rtldavis.RtldavisDriver.__new__(rtldavis.RtldavisDriver)
    d.cmd = cmd
    d.path = None
    d.ld_library_path = None
    d._mgr = mgr
    d._hotswap_path = str(tmp_path / "hotswap.conf")
    d._hotswap_ack_path = str(tmp_path / "hotswap.conf.ack")
    d._hotswap_mtime = None
    return d


def _write(driver, text):
    with open(driver._hotswap_path, "w") as f:
        f.write(text)
    # Force a distinct mtime regardless of filesystem timestamp granularity --
    # the poll is an mtime comparison, and a coarse clock would otherwise make
    # a legitimate second write look unchanged.
    bumped = os.stat(driver._hotswap_path).st_mtime + 10
    os.utime(driver._hotswap_path, (bumped, bumped))


def _ack(driver):
    with open(driver._hotswap_ack_path) as f:
        return f.read()


def test_no_control_file_configured_is_a_no_op(tmp_path):
    mgr = _FakeMgr()
    d = _driver(tmp_path, mgr)
    d._hotswap_path = None
    assert d._maybe_hotswap() is False
    assert mgr.calls == []


def test_absent_file_is_idle_not_an_error(tmp_path):
    mgr = _FakeMgr()
    d = _driver(tmp_path, mgr)
    assert d._maybe_hotswap() is False
    assert mgr.calls == []


def test_swap_respawns_with_the_new_command(tmp_path):
    mgr = _FakeMgr()
    d = _driver(tmp_path, mgr)
    _write(d, "gain = 496\nex = 50\n")
    assert d._maybe_hotswap() is True
    assert mgr.calls[0][0] == "shutdown"
    assert mgr.started_cmds() == [
        "/usr/local/bin/rtldavis -gain 496 -v -fc 0 -ppm 0 -ex 50 "
        "-tf US -tr 1"]
    assert d.cmd == mgr.started_cmds()[0]
    assert "status = applied" in _ack(d)
    assert "respawn_gap_s" in _ack(d)


def test_unchanged_mtime_does_not_respawn(tmp_path):
    mgr = _FakeMgr()
    d = _driver(tmp_path, mgr)
    _write(d, "gain = 496\n")
    assert d._maybe_hotswap() is True
    assert d._maybe_hotswap() is False          # same mtime, no second swap
    assert len(mgr.started_cmds()) == 1


def test_rewriting_the_same_values_is_a_no_op_swap(tmp_path):
    """A touched file whose values already match must not cost a respawn."""
    mgr = _FakeMgr()
    d = _driver(tmp_path, mgr)
    _write(d, "gain = 372\n")                   # BASE already runs 372
    assert d._maybe_hotswap() is False
    assert mgr.calls == []
    assert "status = no-op" in _ack(d)


def test_invalid_file_keeps_the_running_command(tmp_path):
    mgr = _FakeMgr()
    d = _driver(tmp_path, mgr)
    _write(d, "gain = 9999\n")
    assert d._maybe_hotswap() is False
    assert mgr.calls == []
    assert d.cmd == BASE
    assert "status = rejected" in _ack(d)


def test_failed_startup_rolls_back_to_the_last_known_good(tmp_path):
    """A bad value must not cost us the receiver."""
    bad = ("/usr/local/bin/rtldavis -gain 496 -v -fc 0 -ppm 0 -ex 0 "
           "-tf US -tr 1")
    mgr = _FakeMgr(fail_cmds=[bad])
    d = _driver(tmp_path, mgr)
    _write(d, "gain = 496\n")
    # True even on rollback: the child WAS replaced, so the caller still owes
    # the watchdog reset.
    assert d._maybe_hotswap() is True
    assert mgr.started_cmds() == [bad, BASE]
    assert d.cmd == BASE
    assert "status = rollback" in _ack(d)


def test_ack_is_written_atomically(tmp_path):
    """No .tmp left behind -- a reader must never catch a half-written ack."""
    mgr = _FakeMgr()
    d = _driver(tmp_path, mgr)
    _write(d, "gain = 496\n")
    d._maybe_hotswap()
    assert not os.path.exists(d._hotswap_ack_path + ".tmp")


# ── 4. the watchdog grace, the hazard that motivated the design ──────────────

def test_grace_exceeds_the_us_init_period():
    """The reason a flat 150s was not good enough.

    A respawned child is legitimately silent for the US radio init period
    (133s). The normal watchdog leaves 17s of margin over that; the post-swap
    grace must leave a real one.
    """
    us_init_period = 133
    assert rtldavis.STALL_TIMEOUT_S - us_init_period < 20
    assert rtldavis.HOTSWAP_GRACE_S - us_init_period > 100


class _ClockMgr:
    """A ProcManager stand-in that advances a fake clock instead of blocking.

    get_stderr() is where the real loop spends its 10s per pass, so making it
    the thing that moves time keeps the loop's own structure honest.
    """

    def __init__(self, clock, step, alive_passes):
        self.clock = clock
        self.step = step
        self.alive_passes = alive_passes

    def running(self):
        if self.alive_passes <= 0:
            return False
        self.alive_passes -= 1
        return True

    def get_stderr(self):
        self.clock[0] += self.step
        return iter(())

    def drain_stderr(self, max_lines=50):
        return []


def _loop_driver(clock, step, alive_passes, swap_on_pass=None):
    """Driver stub whose hot swap fires on a chosen loop pass.

    The swap deliberately fires on a LATER pass, once the clock has already
    moved: if it fired on the first pass, time_last_received would happen to
    equal the swap time anyway and the test could not tell a real reset from a
    missing one.
    """
    d = rtldavis.RtldavisDriver.__new__(rtldavis.RtldavisDriver)
    d.cmd = BASE
    d._mgr = _ClockMgr(clock, step, alive_passes)
    d.tr_count = 1
    d.stats = {"activeTrIds": [1]}
    d._stderr_sample_count = 0
    d._hotswap_path = None
    passes = [0]

    def _maybe(_self=None):
        passes[0] += 1
        return passes[0] == swap_on_pass

    d._maybe_hotswap = _maybe
    return d


def _run(driver):
    for _ in driver.genLoopPackets():
        pass


def test_swap_resets_and_widens_the_stall_watchdog(monkeypatch):
    """The hazard: a respawned child inherits a stale time_last_received.

    200s of silence after a swap is inside the 240s grace, so the loop must
    survive it and exit only because the child stopped -- not by raising
    'stalled' mid-init.
    """
    clock = [1000.0]
    monkeypatch.setattr(rtldavis.time, "time", lambda: clock[0])
    d = _loop_driver(clock, step=200, alive_passes=4, swap_on_pass=2)
    with pytest.raises(rtldavis.weewx.WeeWxIOError, match="is not running"):
        _run(d)


def test_positive_control_same_silence_without_a_swap_does_stall(monkeypatch):
    """Proves the grace is what saved the test above, not the fake clock.

    Identical timing, no swap: 200s of silence must trip the normal 150s
    watchdog. If this ever stops raising 'stalled', the test above is
    measuring nothing.
    """
    clock = [1000.0]
    monkeypatch.setattr(rtldavis.time, "time", lambda: clock[0])
    d = _loop_driver(clock, step=200, alive_passes=4, swap_on_pass=None)
    with pytest.raises(rtldavis.weewx.WeeWxIOError, match="stalled"):
        _run(d)


def test_grace_is_released_once_the_child_speaks(monkeypatch):
    """The widened window is for the init period only, not permanently.

    After a swap AND a received packet, the threshold is back to 150s, so the
    same 200s of silence must stall again.
    """
    clock = [1000.0]
    monkeypatch.setattr(rtldavis.time, "time", lambda: clock[0])
    d = _loop_driver(clock, step=200, alive_passes=4, swap_on_pass=1)
    spoken = [False]

    def _create(_self, lines):
        if not spoken[0]:
            spoken[0] = True
            return [{"dateTime": int(clock[0]), "usUnits": 16}]
        return []

    # A hop-style packet (no curr_cnt0): enough to mark the child alive, which
    # is what releases the grace.
    monkeypatch.setattr(rtldavis.PacketFactory, "create", _create)
    monkeypatch.setattr(rtldavis.RtldavisDriver, "_cache_pending_freq_fields",
                        lambda self, data: None)

    def _speaking_get_stderr(_self=None):
        clock[0] += 200
        return iter([[]]) if not spoken[0] else iter(())

    d._mgr.get_stderr = _speaking_get_stderr
    with pytest.raises(rtldavis.weewx.WeeWxIOError, match="stalled"):
        _run(d)
