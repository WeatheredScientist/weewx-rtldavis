"""Reception alerts must not depend on where the 5-minute log flush falls (#403).

main() empties wu_period_counts every WU_RF_LOG_INTERVAL (300 s) for the RECEPTION:
log line. classify_reception_alert() and both alert averages read "the last
WU_RF_SUSTAIN windows" from that same list, so the flush phase decided how many
windows they saw, from one to five. Windows 5,5,5,2,0 logged "FULL OUTAGE, avg 0%"
when the true average was 16% and only one window in five was empty.

DEC-0199's tests fed close_reception_window() alone and never the flush, which is
why nothing caught it. These tests run the REAL main() on a fake clock against a
scratch weewx.log, so the flush is exercised exactly as shipped. One poll is one
call to the fake sleep. It advances the clock 30 s, then runs the next scripted
step, so a 60 s window is two polls and a flush lands every fifth window.

weewx_monitor.py writes a pidfile at import; '--test-alert' bypasses that guard
(same pattern as test_reception_full_outage.py).
"""
import os
import re
import sys
import time as _real_time

import pytest

sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402

# Local time, early in a 6 h report block, so a run of a few hours never crosses
# the block boundary that would trigger the reception summary email.
T0 = _real_time.mktime((2026, 6, 15, 1, 10, 0, 0, 0, -1))
POLLS_PER_WINDOW = wm.WU_RF_WINDOW // wm.POLL
WINDOWS_PER_FLUSH = wm.WU_RF_LOG_INTERVAL // wm.WU_RF_WINDOW
# 5,5,5,2,0: every window below WU_RF_MIN_PCT, exactly one of them empty.
DEGRADED_RUN = [5] * (wm.WU_RF_SUSTAIN - 2) + [2, 0]
DEGRADED_AVG = 100.0 * sum(DEGRADED_RUN) / (wm.WU_RF_SUSTAIN * wm.WU_RF_EXPECTED)
BLIND_S = wm.INPUT_STALE_S * 10


class _Stop(BaseException):
    """Raised from the fake sleep to leave main()'s endless loop."""


class _FakeTime:
    """Stands in for the `time` module inside weewx_monitor. The clock moves only
    when main() sleeps; everything else (mktime, localtime, ...) is the real one."""

    def __init__(self, rig):
        self._rig = rig

    def time(self):
        return self._rig.now

    def sleep(self, seconds):
        self._rig.now += seconds
        self._rig.next_step()

    def __getattr__(self, name):
        return getattr(_real_time, name)


class Rig:
    """The real weewx_monitor.main() on a fake clock. Build a script of polls with
    windows(), rotate_after() and go_blind_after(), then run() it; the emails and
    log lines main() produced are collected on the rig."""

    def __init__(self, monkeypatch, tmp_path):
        assert wm.WU_RF_WINDOW % wm.POLL == 0
        assert wm.WU_RF_LOG_INTERVAL % wm.WU_RF_WINDOW == 0
        self.now = T0
        self.stale = 0.0        # how far the weewx log's mtime lags the clock
        self.emails, self.logs, self.opened = [], [], []
        self.steps = []
        self.epoch = 1_000_000
        self.weewx_log = tmp_path / "weewx.log"
        self.weewx_log.write_text("")
        monkeypatch.setattr(wm, "time", _FakeTime(self))
        monkeypatch.setattr(wm, "log", self.logs.append)
        monkeypatch.setattr(wm, "send_email", lambda s, b: self.emails.append((s, b)))
        monkeypatch.setattr(wm, "WEEWX_LOG_PATH", str(self.weewx_log))
        monkeypatch.setattr(wm, "log_mtime", lambda: self.now - self.stale)
        monkeypatch.setattr(wm, "EPISODE_STATE", str(tmp_path / "episode.state"))
        monkeypatch.setattr(wm, "episode_open", lambda avg, now: self.opened.append(avg))
        monkeypatch.setattr(wm, "episode_note_avg", lambda avg: None)
        monkeypatch.setattr(wm, "episode_close", lambda now: None)
        # Other tests leave these dirty (WD['escalated'] in particular would turn
        # every alert here into FULL OUTAGE), so each test gets its own.
        monkeypatch.setattr(wm, "WD", {'last_reset': 0.0, 'tries': 0,
                                       'check_at': 0.0, 'escalated': False})
        monkeypatch.setattr(wm, "BLIND", {'active': False, 'since': 0.0,
                                          'alerted_at': 0.0, 'last_line_ts': 0.0})

    def next_step(self):
        if not self.steps:
            raise _Stop
        self.steps.pop(0)()

    def publish(self, n):
        with open(self.weewx_log, "a") as f:
            for _ in range(n):
                self.epoch += 1
                f.write("Wunderground-RF: Published record 2026-06-15 01:10:00 EDT "
                        f"({self.epoch})\n")

    def windows(self, counts):
        """One 60 s window per count: the publish lines land on its first poll and
        the window closes on its last."""
        for n in counts:
            self.steps.append(lambda n=n: self.publish(n))
            self.steps.extend(lambda: None for _ in range(POLLS_PER_WINDOW - 1))
        return self

    def rotate_after(self, seconds):
        """logrotate a while later: the weewx log restarts empty."""
        def step():
            self.now += seconds
            self.weewx_log.write_text("")
        self.steps.append(step)
        return self

    def go_blind_after(self, seconds):
        def step():
            self.now += seconds
            self.stale = BLIND_S
        self.steps.append(step)
        return self

    def recover(self):
        def step():
            self.stale = 0.0
        self.steps.append(step)
        return self

    def run(self):
        try:
            wm.main()
        except _Stop:
            pass
        return self

    def lines(self, prefix):
        return [m for m in self.logs if m.startswith(prefix)]

    def subjects(self, fragment):
        return [s for s, _ in self.emails if fragment in s]


@pytest.fixture
def rig(monkeypatch, tmp_path):
    return Rig(monkeypatch, tmp_path)


def _healthy(n):
    return [wm.WU_RF_EXPECTED] * n


def _alert_line(avg, full_outage=False):
    """The exact RECEPTION ALERT log line; ops scripts and the ledger read it."""
    tag = "FULL OUTAGE -- " if full_outage else ""
    return (f"RECEPTION ALERT: {tag}{wm.WU_RF_SUSTAIN} consecutive windows below "
            f"{wm.WU_RF_MIN_PCT}%, avg {avg:.0f}%")


# --- the alert, at every phase of the flush ---

@pytest.mark.parametrize("lead", range(1, WINDOWS_PER_FLUSH + 1))
def test_degraded_run_alerts_low_with_the_true_average_at_every_phase(rig, lead):
    """`lead` healthy windows come first, so the five bad ones start at each of the
    five phases of the 5-minute cycle in turn. Only one phase used to be right."""
    rig.windows(_healthy(lead) + DEGRADED_RUN).run()

    assert rig.lines("RECEPTION ALERT") == [_alert_line(DEGRADED_AVG)]
    assert rig.opened == [pytest.approx(DEGRADED_AVG)]
    assert rig.subjects("RF reception") == [f"{wm.STATION_NAME}: RF reception LOW"]
    body = next(b for s, b in rig.emails if "RF reception" in s)
    assert f"Average over last {wm.WU_RF_SUSTAIN} windows: {DEGRADED_AVG:.0f}%" in body


@pytest.mark.parametrize("lead", range(1, WINDOWS_PER_FLUSH + 1))
def test_dead_run_is_full_outage_at_every_phase(rig, lead):
    """The positive control: five genuinely empty windows are still DOWN, wherever
    the flush falls. Guards the fix against over-correcting into never-DOWN."""
    rig.windows(_healthy(lead) + [0] * wm.WU_RF_SUSTAIN).run()

    assert rig.lines("RECEPTION ALERT") == [_alert_line(0.0, full_outage=True)]
    assert rig.subjects("RF reception") == [f"{wm.STATION_NAME}: RF reception DOWN"]


# --- the flush itself is unchanged ---

def test_five_minute_line_reports_its_own_period_and_never_exceeds_100(rig):
    """The RECEPTION: line (parsed by ops/rx_experiment.sh and ops/soak_check.sh)
    still averages just the windows since the previous flush. It now goes through
    wu_pct like every other reception %, so a period that caught extra phase-aligned
    transmissions reads 100 rather than 110."""
    over = wm.WU_RF_EXPECTED + 2
    rig.windows([over] * (2 * WINDOWS_PER_FLUSH)).run()

    assert rig.lines("RECEPTION:") == [
        f"RECEPTION: 100% avg over last {WINDOWS_PER_FLUSH} windows [OK] (bad windows: 0)"
    ] * 2


# --- a reset restarts the rolling record along with the period accounting ---

@pytest.mark.parametrize("reset", ["log rotation", "input recovered"])
def test_reset_restarts_the_rolling_record(rig, reset):
    """After a reset the accounting restarts, so a REPEAT due right afterwards
    averages the one window closed since, not four stale ones from before the gap."""
    rig.windows(_healthy(1) + [5] * wm.WU_RF_SUSTAIN)
    if reset == "log rotation":
        rig.rotate_after(wm.REPEAT + 100)
    else:
        rig.go_blind_after(wm.REPEAT + 100).recover()
    rig.windows([6]).run()

    assert len(rig.lines("RECEPTION ALERT")) == 1
    expected = 100.0 * 6 / wm.WU_RF_EXPECTED
    repeats = rig.lines("RECEPTION REPEAT")
    assert len(repeats) == 1 and re.fullmatch(
        rf"RECEPTION REPEAT: still low {expected:.0f}% after \d+min", repeats[0]), repeats
