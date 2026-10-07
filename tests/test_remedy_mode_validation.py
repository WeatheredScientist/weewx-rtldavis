"""An unrecognized REMEDY_MODE must never run the USB reset (#404).

reset_dongle() checked only `REMEDY_MODE == 'none'` and then ran
`do_restart_unit if REMEDY_MODE == 'restart_unit' else do_reset`. Any other string
therefore ran the Synology USB unbind script, which the marvin unit forbids. The
string could be a typo, 'NONE', 'systemd' or an empty `REMEDY_MODE=` line.
Meanwhile remedy_action() and the startup line said "no automatic remedy". Nothing
validated the value.

REMEDY_MODE is now validated once at import. Anything outside the three known modes
is logged loudly and treated as 'none' (fail safe, never toward a reset). Both the
dispatch and remedy_action() ask remedy_target(), so they cannot disagree.

The import-time cases load a private copy of weewx_monitor.py under a scratch name
with the environment they need, so the module the other tests share is never
reloaded. weewx_monitor.py writes a pidfile at import; '--test-alert' bypasses that
guard (same pattern as test_input_staleness.py).
"""
import importlib.util
import os
import sys

import pytest

sys.argv = ["weewx_monitor.py", "--test-alert"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import weewx_monitor as wm  # noqa: E402

VALID_MODES = ("usb_reset", "restart_unit", "none")
BAD_VALUES = [
    pytest.param("NONE", id="uppercase"),
    pytest.param("systemd", id="systemd"),
    pytest.param("usb-reset", id="hyphen-typo"),
    pytest.param("", id="empty"),
]


def _load(monkeypatch, tmp_path, remedy_mode=None):
    """Import weewx_monitor.py afresh, as a private module, with the environment
    variable REMEDY_MODE set to `remedy_mode` (removed when that is None).
    Returns (module, text of the log file it wrote at import)."""
    monkeypatch.setattr(sys, "argv", ["weewx_monitor.py", "--test-alert"])
    if remedy_mode is None:
        monkeypatch.delenv("REMEDY_MODE", raising=False)
    else:
        monkeypatch.setenv("REMEDY_MODE", remedy_mode)
    log_path = tmp_path / "monitor.log"
    monkeypatch.setenv("MONITOR_LOG", str(log_path))
    spec = importlib.util.spec_from_file_location(
        "weewx_monitor_remedy_probe", os.path.join(ROOT, "weewx_monitor.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, (log_path.read_text() if log_path.exists() else "")


def _dispatch(monkeypatch, mod):
    """Call mod.reset_dongle() once with every side effect replaced. Returns the
    callable it started on a thread, or None when it started nothing."""
    started = {}

    class _Thread:
        def __init__(self, target=None, kwargs=None, daemon=None):
            started['target'] = target

        def start(self):
            started['started'] = True

    monkeypatch.setattr("threading.Thread", _Thread)
    monkeypatch.setattr(mod, "log", lambda m: None)
    monkeypatch.setattr(mod, "campaign_inhibited", lambda: False)
    mod.reset_dongle(0.0, notify=False)
    return started['target'] if started.get('started') else None


# --- an unrecognized value fails safe at import ---

@pytest.mark.parametrize("bad", BAD_VALUES)
def test_unrecognized_value_behaves_as_none(monkeypatch, tmp_path, bad):
    mod, _ = _load(monkeypatch, tmp_path, bad)
    assert mod.REMEDY_MODE == "none"


@pytest.mark.parametrize("bad", BAD_VALUES)
def test_unrecognized_value_is_logged_loudly_once(monkeypatch, tmp_path, bad):
    """Silence is how this hid: the startup line read 'no automatic remedy' either
    way. The one line must name the offending value so the operator can fix it."""
    _, text = _load(monkeypatch, tmp_path, bad)
    lines = [ln for ln in text.splitlines() if f"REMEDY_MODE={bad!r}" in ln]
    assert len(lines) == 1, text
    assert "none" in lines[0] and "no automatic remedy" in lines[0], lines[0]


@pytest.mark.parametrize("bad", BAD_VALUES)
def test_unrecognized_value_never_dispatches_do_reset(monkeypatch, tmp_path, bad):
    """The bug itself: the USB reset ran for any string but the exact ones."""
    mod, _ = _load(monkeypatch, tmp_path, bad)
    started = _dispatch(monkeypatch, mod)
    assert started is None, (
        f"REMEDY_MODE={bad!r}: remedy_action() said {mod.remedy_action()!r} but "
        f"reset_dongle() started {getattr(started, '__name__', started)}")


# --- recognized values are untouched ---

@pytest.mark.parametrize("mode", VALID_MODES)
def test_recognized_value_loads_unchanged_and_quiet(monkeypatch, tmp_path, mode):
    mod, text = _load(monkeypatch, tmp_path, mode)
    assert mod.REMEDY_MODE == mode
    assert text == "", "a valid REMEDY_MODE must not log anything at import"


def test_unset_variable_keeps_the_legacy_default_and_is_quiet(monkeypatch, tmp_path):
    """Validation must not turn 'unset' into 'none': the default stays the published
    extension's Synology behavior (see test_input_staleness.py)."""
    mod, text = _load(monkeypatch, tmp_path, None)
    assert mod.REMEDY_MODE == "usb_reset"
    assert text == ""


# --- one mapping behind both the dispatch and the description ---

def test_accepted_values_are_exactly_the_three_documented_ones():
    assert set(wm.REMEDY_MODES) == set(VALID_MODES)


@pytest.mark.parametrize("mode", list(VALID_MODES) + ["NONE", "systemd", ""])
def test_dispatch_and_remedy_action_share_one_mapping(monkeypatch, mode):
    """Set straight on the module, bypassing the import check, so this also holds
    if a bad value ever gets past it. Anything that is not an action mode means no
    action and no claim of one."""
    monkeypatch.setattr(wm, "REMEDY_MODE", mode)
    target, text = wm.remedy_target(), wm.remedy_action()
    if mode == "usb_reset":
        assert target is wm.do_reset and wm.USB_RESET_ACTION in text
    elif mode == "restart_unit":
        assert target is wm.do_restart_unit and wm.REMEDY_UNIT in text
    else:
        assert target is None and "no automatic remedy" in text
    assert _dispatch(monkeypatch, wm) is target
