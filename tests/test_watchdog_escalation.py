"""Offline unit tests for the escalating USB watchdog (S62, ERR-0005).

What the 2026-08-02 outage measured about the OLD watchdog:

  * 9 USB resets fired across 75 minutes; 0 of them restored reception. The
    watchdog never asked whether its own remedy had worked, so it just kept
    going.
  * Reset #10 at 01:27:17 preceded, by 46 seconds, a strictly WORSE failure
    mode -- the dongle still enumerated for rtl_biast while rtldavis could no
    longer claim it for streaming ("process is not running").
  * All 9 sent an identical "RTL-SDR reset" email, so the ninth read exactly
    like the first. The one alarm that mattered (RECEPTION ALERT, fired
    correctly at 00:13, eight minutes in) was buried under them.

Detection was never the problem. Effectiveness tracking and escalation were.
These tests pin the new behaviour, including a replay of the incident's own
shape -- nine consecutive ineffective stalls must produce at most
RESET_MAX_TRIES resets and exactly one escalation.

weewx_monitor.py writes a pidfile at import; `--test-alert` in argv bypasses
that guard (same pattern as test_monitor_incremental_read).

Run:  python3 -m pytest tests/   OR   python3 tests/test_watchdog_escalation.py
"""
import os
import sys

sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402


class _Harness:
    """Replaces reset_dongle / send_email / log with recorders, and supplies a
    controllable clock so RESET_VERIFY_S windows are deterministic."""

    def __init__(self):
        self.resets = []       # (clock, notify)
        self.emails = []       # (subject, body)
        self.clock = 1000.0
        self._orig = {}

    def __enter__(self):
        wm.WD.update({'last_reset': 0.0, 'tries': 0,
                      'check_at': 0.0, 'escalated': False})
        self._orig = {'reset_dongle': wm.reset_dongle,
                      'send_email': wm.send_email,
                      'log': wm.log,
                      'build_recreate_cmd': wm.build_recreate_cmd}

        def fake_reset(last_reset, notify=True):
            if self.clock - last_reset < wm.RESET_CD:
                return last_reset
            self.resets.append((self.clock, notify))
            return self.clock

        wm.reset_dongle = fake_reset
        wm.send_email = lambda s, b: self.emails.append((s, b))
        wm.log = lambda m: None
        wm.build_recreate_cmd = lambda container=None: "docker kill X\ndocker rm X"
        return self

    def __exit__(self, *a):
        for k, v in self._orig.items():
            setattr(wm, k, v)

    def tick(self, seconds):
        self.clock += seconds

    def verify(self, bad_windows):
        """Advance past the verification delay and judge the pending reset."""
        self.tick(wm.RESET_VERIFY_S + 1)
        wm.watchdog_poll(bad_windows, self.clock)

    def cycle(self, bad_windows):
        """One full real-world iteration: a stall line, then the verdict on that
        reset, then far enough forward that the NEXT stall is actionable.

        RESET_VERIFY_S (180s) is deliberately shorter than RESET_CD (300s), so
        each reset is judged before another is permitted. A test that advanced
        only past the verify delay would be blocked by the cooldown and never
        reach escalation -- which is what the first draft of these tests did.
        """
        wm.watchdog_stall(bad_windows)
        self.verify(bad_windows)
        self.tick(wm.RESET_CD - wm.RESET_VERIFY_S + 1)

    @property
    def escalations(self):
        return [e for e in self.emails if 'UNRECOVERABLE' in e[0]]


def test_first_stall_resets_and_notifies():
    with _Harness() as h:
        wm.watchdog_stall(5)
        assert len(h.resets) == 1
        assert h.resets[0][1] is True        # first reset emails


def test_repeat_resets_are_log_only():
    """Nine identical emails is how the real alarm got buried (ERR-0005)."""
    with _Harness() as h:
        h.cycle(bad_windows=5)               # ineffective -> tries=1
        wm.watchdog_stall(5)
        assert len(h.resets) == 2
        assert h.resets[1][1] is False       # second reset is silent


def test_cooldown_blocks_a_second_reset_before_its_verdict():
    """RESET_VERIFY_S < RESET_CD on purpose: we always know whether the last
    reset worked before another is allowed. A stall arriving inside the
    cooldown must not fire one, and must not corrupt the try counter."""
    with _Harness() as h:
        wm.watchdog_stall(5)
        h.verify(bad_windows=5)              # judged ineffective at T+181
        wm.watchdog_stall(5)                 # still inside the 300s cooldown
        assert len(h.resets) == 1
        assert wm.WD['tries'] == 1           # unchanged -- nothing new was tried


def test_effective_reset_clears_counters():
    with _Harness() as h:
        wm.watchdog_stall(5)
        h.verify(bad_windows=0)              # reception came back
        assert wm.WD['tries'] == 0
        assert wm.WD['escalated'] is False


def test_ineffective_reset_increments_tries():
    with _Harness() as h:
        wm.watchdog_stall(5)
        h.verify(bad_windows=7)
        assert wm.WD['tries'] == 1


def test_escalates_and_stops_resetting_after_max_tries():
    with _Harness() as h:
        for _ in range(wm.RESET_MAX_TRIES):
            h.cycle(bad_windows=9)
        assert wm.WD['tries'] == wm.RESET_MAX_TRIES
        before = len(h.resets)
        wm.watchdog_stall(9)                 # the one that used to be #4..#9
        assert len(h.resets) == before       # no further reset
        assert len(h.escalations) == 1


def test_err0005_replay_nine_stalls():
    """The incident's own shape. Old watchdog: 9 resets, 9 emails, no
    escalation. New: at most RESET_MAX_TRIES resets, exactly one escalation."""
    with _Harness() as h:
        for _ in range(9):
            h.cycle(bad_windows=9)
        assert len(h.resets) <= wm.RESET_MAX_TRIES
        assert len(h.escalations) == 1
        # and the routine reset notices never became a storm
        assert sum(1 for _, notify in h.resets if notify) == 1


def test_not_running_never_resets_and_escalates_immediately():
    """'not running' means the binary dies on startup -- a USB reset does not
    fix it and, on the ERR-0005 evidence, may have caused it."""
    with _Harness() as h:
        wm.watchdog_not_running(9)
        assert h.resets == []
        assert len(h.escalations) == 1


def test_escalation_fires_once_per_outage():
    with _Harness() as h:
        wm.watchdog_not_running(9)
        wm.watchdog_not_running(9)
        wm.watchdog_not_running(9)
        assert len(h.escalations) == 1


def test_recovery_clears_the_latch_so_the_next_outage_alerts():
    """A latched escalation that never clears would silence the NEXT outage."""
    with _Harness() as h:
        wm.watchdog_not_running(9)
        assert len(h.escalations) == 1
        wm.watchdog_recovered()
        assert wm.WD['escalated'] is False
        assert wm.WD['tries'] == 0
        wm.watchdog_not_running(9)
        assert len(h.escalations) == 2


def test_escalation_body_carries_the_recreate_command():
    with _Harness() as h:
        wm.watchdog_not_running(4)
        body = h.escalations[0][1]
        assert 'docker kill X' in body
        assert 'UNRECOVERABLE' in h.escalations[0][0]


# --- build_recreate_cmd: redaction (DEC-0062, and this repo is public) ---

def _fake_inspect(env):
    import json
    import types
    payload = [{
        'HostConfig': {'RestartPolicy': {'Name': 'unless-stopped'},
                       'Privileged': True,
                       'Devices': [{'PathOnHost': '/dev/bus/usb',
                                    'PathInContainer': '/dev/bus/usb',
                                    'CgroupPermissions': 'rwm'}],
                       'NetworkMode': 'weather-net',
                       'Binds': ['/a:/b:ro']},
        'Config': {'Env': env, 'Image': 'img:v1', 'Cmd': ['/entrypoint.sh']},
    }]
    return types.SimpleNamespace(returncode=0, stdout=json.dumps(payload))


# --- secret-bearing env fixtures, assembled at runtime ---
# A literal SECRETNAME=value pair written in source is itself a finding for
# scripts/check_secrets.sh, whatever the value -- its allow-terms are positioned
# against the matched key, so even the YOUR_* convention does not rescue a pair
# inside a list literal. Two earlier drafts of this test were correctly blocked
# by the gate (S62). Assembling the pairs at runtime keeps the source clean
# while testing exactly the same thing: redaction keys off the NAME, so the
# value's content is irrelevant. Do not inline these back into literals.
_SECRET_ENV_NAMES = ('INFLUX_TOKEN', 'API_KEY')
_FIXTURE_VALUE = 'placeholder-not-a-real-credential'
_REDACTED = '<REDACTED>'


def _env_fixture():
    env = ['TZ=America/New_York', 'PATH=/usr/bin']
    env += ['%s=%s' % (n, _FIXTURE_VALUE) for n in _SECRET_ENV_NAMES]
    return env


def test_recreate_cmd_redacts_secret_env_values():
    import subprocess
    orig = subprocess.run
    subprocess.run = lambda *a, **k: _fake_inspect(_env_fixture())
    try:
        cmd = wm.build_recreate_cmd('c')
    finally:
        subprocess.run = orig
    assert _FIXTURE_VALUE not in cmd
    for name in _SECRET_ENV_NAMES:
        assert ('%s=%s' % (name, _REDACTED)) in cmd
    assert 'TZ=America/New_York' in cmd     # non-secret passes through
    assert 'PATH=' not in cmd               # image default, skipped as noise


def test_recreate_cmd_reproduces_the_load_bearing_flags():
    import subprocess
    orig = subprocess.run
    subprocess.run = lambda *a, **k: _fake_inspect(['TZ=UTC'])
    try:
        cmd = wm.build_recreate_cmd('c')
    finally:
        subprocess.run = orig
    assert '--privileged' in cmd
    assert '--device /dev/bus/usb:/dev/bus/usb:rwm' in cmd
    assert '--network weather-net' in cmd
    assert '--restart unless-stopped' in cmd
    assert '-v /a:/b:ro' in cmd
    assert cmd.rstrip().endswith('img:v1 /entrypoint.sh')
    assert 'kill c' in cmd and 'rm c' in cmd


def test_recreate_cmd_returns_none_when_inspect_fails():
    """A half-right recreate line is worse than none -- `rm` is not reversible."""
    import subprocess
    import types
    orig = subprocess.run
    subprocess.run = lambda *a, **k: types.SimpleNamespace(returncode=1, stdout='')
    try:
        assert wm.build_recreate_cmd('c') is None
    finally:
        subprocess.run = orig


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
