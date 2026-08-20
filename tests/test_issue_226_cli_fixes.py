"""Offline regression tests for issue #226 (S91 audit, "public-facing rough
edges"): four isolated bugs bundled as one tier:cheap fix.

  1. default_stanza's cmd line shipped a literal, never-substituted
     `[options]` token. A new user accepting the generated stanza as-is
     shipped that token into weewx.conf; Go's flag.Parse() then treats it
     as the first non-flag positional argument and stops parsing there,
     silently discarding the -tf/-tr ProcManager.startup() appends after
     it and falling back to 868MHz EU instead of 915MHz US -- zero error.
  2. ProcManager.startup() split the command line on cmd.split(' '), which
     breaks on a double space or a quoted, space-containing path.
  3. weewx.__version__ < "3" is a lexicographic string compare, not a
     numeric one -- "10.0.0" < "3" is True in Python, which would reject a
     genuinely newer weewx 10.x with the error meant for genuinely old ones.
  4. The --action show-packets CLI crashed on first use: get_stderr()
     yields possibly-empty lists (lines[0] raised IndexError on a queue
     timeout, an expected/frequent event), and get_stdout() returns a flat
     list of decoded strings rather than a list of 1-line lists (the
     analogous lines[0]/lines.pop(0) then raised AttributeError).

weewx is not installed in the test/CI environment, so we stub the weewx
modules in sys.modules before importing the driver (same pattern as
test_procmanager_reap.py / test_stderr_drain.py).

Run:  python3 -m pytest tests/   OR   python3 tests/test_issue_226_cli_fixes.py
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
_weewx.UnsupportedFeature = type("UnsupportedFeature", (Exception,), {})
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


# ── Item 1: default_stanza's literal [options] token ──────────────────────

def test_default_stanza_has_no_literal_options_token():
    stanza = rtldavis.RtldavisConfigurationEditor().default_stanza
    cmd_line = next(line for line in stanza.splitlines()
                    if line.strip().startswith("cmd"))
    assert "[options]" not in cmd_line
    assert cmd_line.strip() == "cmd = /home/pi/work/bin/rtldavis"


# ── Item 2: shlex.split, not cmd.split(' ') ────────────────────────────────

class _RecordingPopen:
    """Records the argv it was launched with; never spawns a real process.
    stderr/stdout are empty byte streams so AsyncReader's readline loop
    exits immediately instead of blocking."""
    last_args = None

    def __init__(self, args, **kwargs):
        _RecordingPopen.last_args = args
        import io
        self.stderr = io.BytesIO(b'')
        self.stdout = io.BytesIO(b'')

    def poll(self):
        return None


def test_startup_uses_shlex_split_not_naive_split(monkeypatch):
    """The regression this pins: a double space in the configured cmd used
    to produce an empty-string argv element ('/bin/x  y'.split(' ') ==
    ['/bin/x', '', 'y']), which a real binary's flag parser would choke on.
    shlex.split collapses it correctly."""
    monkeypatch.setattr(rtldavis.ProcManager, "get_pid", lambda self, name: [])
    monkeypatch.setattr(rtldavis.subprocess, "Popen", _RecordingPopen)
    rtldavis._SPAWNED_CHILDREN.clear()
    mgr = rtldavis.ProcManager()
    mgr.startup("/home/pi/work/bin/rtldavis  -gain 372")
    assert _RecordingPopen.last_args == [
        "/home/pi/work/bin/rtldavis", "-gain", "372"]
    rtldavis._SPAWNED_CHILDREN.clear()


def test_startup_splits_quoted_path_with_space(monkeypatch):
    """A path containing a space, quoted in the config, must survive as one
    argv element -- naive .split(' ') would break it into two."""
    monkeypatch.setattr(rtldavis.ProcManager, "get_pid", lambda self, name: [])
    monkeypatch.setattr(rtldavis.subprocess, "Popen", _RecordingPopen)
    rtldavis._SPAWNED_CHILDREN.clear()
    mgr = rtldavis.ProcManager()
    mgr.startup('"/home/pi/my bin/rtldavis" -gain 372')
    assert _RecordingPopen.last_args == ["/home/pi/my bin/rtldavis", "-gain", "372"]
    rtldavis._SPAWNED_CHILDREN.clear()


# ── Item 3: numeric version compare ────────────────────────────────────────

def test_check_weewx_version_accepts_double_digit_major():
    """The regression this pins: "10.0.0" < "3" is True under a bare string
    compare, wrongly rejecting a genuinely newer weewx 10.x."""
    rtldavis.check_weewx_version("10.0.0")  # must not raise


def test_check_weewx_version_accepts_weewx_3_exactly():
    rtldavis.check_weewx_version("3.0.0")  # must not raise


def test_check_weewx_version_still_rejects_weewx_2(monkeypatch):
    # rtldavis's module-global `weewx` name is bound to whichever test
    # file's stub happened to import rtldavis first in this pytest session
    # (sys.modules caching) -- monkeypatch the attribute directly rather
    # than assume this file won that race.
    monkeypatch.setattr(rtldavis.weewx, "UnsupportedFeature",
                        type("UnsupportedFeature", (Exception,), {}),
                        raising=False)
    with pytest.raises(rtldavis.weewx.UnsupportedFeature):
        rtldavis.check_weewx_version("2.7.0")


# ── Item 4: show_packets CLI loop ──────────────────────────────────────────

class _FakeMgr:
    """running() is True for exactly one pass through show_packets' while
    loop, so get_stderr()/get_stdout() are each driven once with the
    prescribed shape, then the loop exits on its own."""

    def __init__(self, stderr_yields, stdout_lines):
        self._stderr_yields = stderr_yields
        self._stdout_lines = stdout_lines
        self._alive = True

    def running(self):
        alive = self._alive
        self._alive = False
        return alive

    def get_stderr(self):
        for batch in self._stderr_yields:
            yield batch

    def get_stdout(self):
        return list(self._stdout_lines)


def test_show_packets_survives_empty_stderr_batch():
    """The regression this pins: get_stderr() yielding [] on a queue
    timeout (routine, frequent) used to crash on lines[0] with IndexError."""
    mgr = _FakeMgr(stderr_yields=[[], [], []], stdout_lines=[])
    rtldavis.show_packets(mgr)  # must not raise


def test_show_packets_prints_stderr_payload(capsys):
    mgr = _FakeMgr(stderr_yields=[["hello world\n"], []], stdout_lines=[])
    rtldavis.show_packets(mgr)
    assert "hello world" in capsys.readouterr().out


def test_show_packets_survives_flat_stdout_list():
    """The regression this pins: get_stdout()'s flat list of decoded
    strings used to be indexed like get_stderr()'s list-of-lists, raising
    AttributeError on lines.pop(0) for the first (string) element."""
    mgr = _FakeMgr(stderr_yields=[[]], stdout_lines=["one\n", "two\n"])
    rtldavis.show_packets(mgr)  # must not raise


def test_show_packets_prints_stdout_lines(capsys):
    mgr = _FakeMgr(stderr_yields=[[]], stdout_lines=["one\n", "two\n"])
    rtldavis.show_packets(mgr)
    out = capsys.readouterr().out
    assert "one" in out and "two" in out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
