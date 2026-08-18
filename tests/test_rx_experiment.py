"""Offline tests for ops/rx_experiment.sh — the DEC-0048 RX experiment apparatus.

This script autonomously rewrites the LIVE, credential-bearing weewx.conf 32
times over 8 days and restarts prod each time. That is the most dangerous thing
in this repo's ops/ directory, so it ships with its own test — DEC-0039's rule
that a gate ships with its planted-payload test, applied to a writer instead of
a scanner.

The lesson these tests encode (DEC-0045, and the four times the secret gate was
wrong): a passing test proves nothing without a POSITIVE CONTROL. So
test_old_global_regex_is_destructive deliberately runs the OLD ops/set_gain.sh
approach against the same fixture and asserts it corrupts it. If that test ever
goes green-by-passing (i.e. the old logic stops corrupting), the fixture has
lost its teeth and the surgical test below is no longer proving anything.

The tests drive the REAL shell functions by sourcing everything above the mode
dispatch, so what is under test is the deployed file, not a copy of its logic.

Run:  python -m pytest tests/test_rx_experiment.py
"""
import datetime
import hashlib
import os
import re
import subprocess
import textwrap
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "ops" / "rx_experiment.sh"

# A config shaped like the real one, carrying two traps a careless global
# substitution will spring: a "-gain <n>" in an unrelated section, and a
# "-gain <n>" inside a documentation comment.
FIXTURE = textwrap.dedent("""\
    [SomethingElse]
        canary = fixture-canary-must-survive
        note = a decoy -gain 999 inside another section

    [Rtldavis]
        # This section is for the rtldavis sdr-rtl USB receiver.

        cmd = /usr/local/bin/rtldavis -gain 372 -v -fc 0 -ppm 0
        # Options:
        # -gain = tuner gain in tenths of Db; default = 0 means "auto gain"
        # example: -gain 496 would be near max
        transceiver_frequency = US
        iss_channel = 5
    """)

TARGET = "    cmd = /usr/local/bin/rtldavis -gain 207 -v -fc 0 -ppm 0 -ex 50"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _call_write_arm(conf: Path, line: str):
    """Invoke the real write_arm() from the shipped script."""
    prog = (
        f'source <(sed "/^# ── Modes/,\\$d" {SCRIPT}); '
        f'CONF={conf}; write_arm "{line}"'
    )
    return subprocess.run(["bash", "-c", prog], capture_output=True, text=True)


def test_write_is_surgical(tmp_path):
    """Exactly one line changes; both decoys and the secret survive untouched."""
    conf = tmp_path / "weewx.conf"
    conf.write_text(FIXTURE)

    r = _call_write_arm(conf, TARGET)
    assert r.returncode == 0, r.stderr

    before, after = FIXTURE.split("\n"), conf.read_text().split("\n")
    changed = [(b, a) for b, a in zip(before, after) if b != a]
    assert len(changed) == 1, f"expected 1 changed line, got {changed}"
    assert changed[0][1] == TARGET

    text = conf.read_text()
    assert "-gain 999" in text, "decoy in another section was rewritten"
    assert "-gain 496" in text, "doc-comment example was rewritten"
    assert "fixture-canary-must-survive" in text, "unrelated value was touched"


def test_old_global_regex_is_destructive(tmp_path):
    """POSITIVE CONTROL: the old ops/set_gain.sh approach corrupts this fixture.

    If this test fails, the fixture no longer has teeth and
    test_write_is_surgical has stopped proving anything.
    """
    text = re.sub(r"-gain [0-9]+", "-gain 207", FIXTURE)  # the old set_gain.sh line
    assert "-gain 999" not in text, "fixture lost its cross-section decoy"
    assert "-gain 496" not in text, "fixture lost its doc-comment decoy"


def test_refuses_when_no_cmd_line(tmp_path):
    conf = tmp_path / "weewx.conf"
    conf.write_text("\n".join(line for line in FIXTURE.split("\n")
                              if "cmd = /usr/local/bin/rtldavis" not in line))
    sha = _sha(conf)
    r = _call_write_arm(conf, TARGET)
    assert r.returncode != 0
    assert "found 0" in (r.stdout + r.stderr)
    assert _sha(conf) == sha, "file was modified despite refusing"


def test_refuses_when_duplicate_cmd_lines(tmp_path):
    conf = tmp_path / "weewx.conf"
    conf.write_text(FIXTURE + "    cmd = /usr/local/bin/rtldavis -gain 100 -v\n")
    sha = _sha(conf)
    r = _call_write_arm(conf, TARGET)
    assert r.returncode != 0
    assert "found 2" in (r.stdout + r.stderr)
    assert _sha(conf) == sha, "file was modified despite refusing"


# --- the pre-registration itself is testable ---------------------------------

def _schedule_rows(src: str | None = None):
    src = SCRIPT.read_text() if src is None else src
    block = re.search(r'^SCHEDULE="\n(.*?)^"', src, re.S | re.M).group(1)
    return [tuple(row.split("|")) for row in block.strip().split("\n") if row]


def _schedule_state(rows, now: str) -> str:
    """The shipped block's three states (DEC-0096): 'stand-down' (empty — no
    campaign scheduled, the valid between-campaigns form), 'live' (terminator
    still ahead), 'stale' (fully elapsed — regenerate before the next launch)."""
    if not rows:
        return "stand-down"
    last_time, last_arm = rows[-1]
    assert last_arm == "BASELINE", "schedule must end with the self-terminator"
    return "live" if last_time > now else "stale"


def _require_campaign():
    """Structural tests assert the shape of a SCHEDULED campaign; in the
    stand-down state there is nothing to assert (and install refuses — tested
    in the stand-down section below)."""
    if not _schedule_rows():
        pytest.skip("stand-down: no campaign scheduled (DEC-0096)")


def test_schedule_is_a_balanced_latin_square():
    """Each square arm must visit each 6h slot exactly twice — that balance IS
    the control for time-of-day and diurnal drift. A typo here silently
    reintroduces the confound the whole design exists to remove, and nothing at
    runtime would notice. Pilot (P*) and hold (H) rows are campaign B's
    calibration prefix, not square blocks — they are excluded here and asserted
    by their own tests below."""
    _require_campaign()
    rows = [r for r in _schedule_rows() if r[1] in {"A", "B", "C", "D"}]
    assert len(rows) == 32, f"expected 32 blocks, got {len(rows)}"

    seen = {}
    for when, arm in rows:
        slot = when.split("T")[1]
        seen.setdefault(arm, {}).setdefault(slot, 0)
        seen[arm][slot] += 1

    assert set(seen) == {"A", "B", "C", "D"}
    for arm, slots in seen.items():
        assert set(slots) == {"00:05", "06:05", "12:05", "18:05"}, \
            f"arm {arm} missed a slot: {slots}"
        assert all(n == 2 for n in slots.values()), \
            f"arm {arm} is not balanced across slots: {slots}"


def test_schedule_self_terminates_to_baseline():
    """If everyone forgets this is running it must end on prod config, not an
    experimental arm."""
    _require_campaign()
    assert _schedule_rows()[-1][1] == "BASELINE"


# --- campaign B's calibration prefix (DEC-0064) -------------------------------

def _arm_gain(arm: str) -> int:
    out = subprocess.run(
        ["bash", "-c",
         f'source <(sed "/^# ── Modes/,\\$d" {SCRIPT}); arm_cmd {arm}'],
        capture_output=True, text=True)
    assert out.returncode == 0, f"arm {arm} has no command"
    return int(re.search(r"-gain (\d+)", out.stdout).group(1))


def test_pilot_runs_high_to_low_before_the_morning_notch():
    """The pilot's five gain blocks must (a) run strictly HIGH -> LOW, so an
    abort on a weak low arm still leaves the high arms harvested; (b) sit on a
    45-min cadence; and (c) finish before 06:00, clear of the site's hour-07
    reception notch (BACKLOG §Durable RF findings) — pilot numbers are bounding
    input and must not be depressed by a known site artifact."""
    _require_campaign()
    rows = _schedule_rows()
    pilot = [r for r in rows if r[1].startswith("P")]
    assert len(pilot) == 5, f"expected 5 pilot rows, got {len(pilot)}"
    assert rows[:5] == pilot, "pilot rows must open the schedule"

    gains = [_arm_gain(arm) for _, arm in pilot]
    assert gains == sorted(gains, reverse=True), \
        f"pilot gains must descend (cliff-detection ordering): {gains}"

    days = {when.split("T")[0] for when, _ in pilot}
    assert len(days) == 1, f"pilot must fit inside one night: {days}"
    times = [when.split("T")[1] for when, _ in pilot]
    assert all(t < "06:00" for t in times), \
        f"pilot must finish before the hour-07 notch: {times}"

    def _minutes(hhmm):
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)
    gaps = [_minutes(b) - _minutes(a) for a, b in zip(times, times[1:])]
    assert all(g == 45 for g in gaps), f"pilot cadence must be 45 min: {gaps}"


def test_hold_follows_pilot_and_matches_control_settings():
    """The H hold is the daylong no-LNA baseline-verification window. It must
    (a) directly follow the last pilot block, (b) carry the control arm A's
    exact settings under its own label — a distinct label so the hold harvests
    under its own tag and can never contaminate arm A's square samples, and
    (c) hand over to the square's first block at the NEXT day's 00:05 (the S57
    clean-day-boundary lesson)."""
    _require_campaign()
    rows = _schedule_rows()
    holds = [(i, r) for i, r in enumerate(rows) if r[1] == "H"]
    assert len(holds) == 1, f"expected exactly one hold row, got {holds}"
    idx, (when, _) = holds[0]

    assert rows[idx - 1][1].startswith("P"), "hold must directly follow the pilot"

    def _cmd(arm):
        out = subprocess.run(
            ["bash", "-c",
             f'source <(sed "/^# ── Modes/,\\$d" {SCRIPT}); arm_cmd {arm}'],
            capture_output=True, text=True)
        return out.stdout
    assert _cmd("H") == _cmd("A"), \
        "H must be arm A's settings under a distinct label"

    first_square = rows[idx + 1]
    assert first_square[1] in {"A", "B", "C", "D"}
    assert first_square[0].split("T")[1] == "00:05", \
        "square must start on a clean day boundary"
    assert first_square[0].split("T")[0] > when.split("T")[0], \
        "square must start the day after the pilot night"


def test_schedule_is_chronological():
    stamps = [w for w, _ in _schedule_rows()]
    assert stamps == sorted(stamps), "schedule rows are out of order"


def test_every_arm_is_a_complete_literal_command():
    """Safety property #1: arms are whole literal strings, never assembled. Each
    must be a full, well-formed cmd line so a bug can only pick the wrong
    known-good arm, never synthesize a malformed one."""
    arms = {a for _, a in _schedule_rows() if a != "BASELINE"}
    for arm in sorted(arms):
        out = subprocess.run(
            ["bash", "-c",
             f'source <(sed "/^# ── Modes/,\\$d" {SCRIPT}); arm_cmd {arm}'],
            capture_output=True, text=True)
        assert out.returncode == 0, f"arm {arm} has no command"
        line = out.stdout.rstrip("\n")
        assert re.fullmatch(
            r"    cmd = /usr/local/bin/rtldavis -gain \d+ -v -fc 0 -ppm 0 -ex \d+",
            line), f"arm {arm} is not a well-formed literal: {line!r}"


# --- S57 regressions: the two defects that broke the first live campaign ------

def test_load_env_exports_to_child_processes(tmp_path):
    """REGRESSION (S57). Sourcing the env file set shell variables but did not
    EXPORT them, so send_mail's python3 heredoc -- a child process -- saw nothing
    and died on KeyError. Every alert this script could send was broken,
    including the abort notification: the campaign aborted for real on
    2026-07-29, restored the baseline correctly, and told nobody.

    This drives the real load_env() and asserts a CHILD process can see the
    value, which is the property that actually failed.
    """
    envfile = tmp_path / "fixture.env"
    envfile.write_text("ALERT_FROM=someone@example.invalid\n")

    prog = (
        f'source <(sed "/^# ── Modes/,\\$d" {SCRIPT}); '
        f"ENVFILE={envfile}; load_env; "
        f"""python3 -c "import os; print(os.environ['ALERT_FROM'])" """
    )
    r = subprocess.run(["bash", "-c", prog], capture_output=True, text=True)
    assert r.returncode == 0, f"child could not read the exported var: {r.stderr}"
    assert "someone@example.invalid" in r.stdout


def test_load_env_reports_failure_when_envfile_missing(tmp_path):
    prog = (
        f'source <(sed "/^# ── Modes/,\\$d" {SCRIPT}); '
        f'ENVFILE={tmp_path / "does-not-exist"}; load_env'
    )
    r = subprocess.run(["bash", "-c", prog], capture_output=True, text=True)
    assert r.returncode != 0, "load_env must fail loudly when the env file is absent"


def test_health_check_budget_covers_a_full_archive_interval():
    """REGRESSION (S57, extended S73). The health check's 18 tries (~90s) was too
    small BY CONSTRUCTION and aborted a live campaign 3 seconds early (S57:
    weewxd init 12:11:46, first record 12:13:30 = 104s, abort at 12:13:27).

    S73 found the corrected model STILL missing a term: RF ACQUISITION. After
    "Starting main packet loop" the driver can take ~0s to ~127s (measured, the
    2026-08-11 08:55 H swap) to sync the hop pattern and decode a first frame —
    no packets, no archive record, regardless of archive boundaries. The 180s
    budget expired seconds before a healthy driver's first record, aborting a
    live campaign. Again. The arithmetic is asserted here rather than the bare
    number, so lowering the budget fails the test with the reason attached.
    """
    src = SCRIPT.read_text()
    tries = int(re.search(r"^HEALTH_TRIES=(\d+)", src, re.M).group(1))
    sleep_s = int(re.search(
        r'for i in \$\(seq 1 "\$HEALTH_TRIES"\); do\s*\n\s*sleep (\d+)', src, re.M).group(1))

    boot_s, rf_acquire_s, archive_interval_s, write_lag_s = 25, 130, 60, 30
    worst_case = boot_s + rf_acquire_s + archive_interval_s + write_lag_s  # ~245s

    assert tries * sleep_s >= worst_case, (
        f"health budget {tries * sleep_s}s cannot cover the {worst_case}s worst case "
        f"(boot {boot_s} + rf acquire {rf_acquire_s} + archive interval "
        f"{archive_interval_s} + write lag {write_lag_s})"
    )


# ── Stale-schedule guard (S62, DEC-0066) ──────────────────────────────────────
# Campaign B was prepared with dates that went stale when the launch was held.
# due_arm() selects the LATEST row already passed, so a stale schedule does not
# fail loudly -- it silently starts mid-square, or past the last row reports the
# campaign complete without running it. Both look like success, which is exactly
# why this is a guard in the script and not a warning in a doc (DEC-0040).

def _call_schedule_started(now: str):
    prog = (
        f'source <(sed "/^# ── Modes/,\\$d" {SCRIPT}); '
        f'schedule_started "{now}"'
    )
    return subprocess.run(["bash", "-c", prog], capture_output=True, text=True)


def _first_row_time() -> str:
    return _schedule_rows()[0][0]


def test_schedule_not_started_when_first_row_is_future():
    """The normal case: a schedule whose first row is ahead of now installs."""
    _require_campaign()
    first = _first_row_time()
    before = first[:-1] + str(int(first[-1]) - 1) if first[-1] != "0" else "2000-01-01T00:00"
    assert _call_schedule_started(before).returncode == 1


def test_schedule_started_when_first_row_has_passed():
    """The trap: first row in the past means we would join mid-flight."""
    _require_campaign()
    assert _call_schedule_started("2099-01-01T00:00").returncode == 0


def test_install_refuses_a_started_schedule(tmp_path):
    """End-to-end: `install` must refuse rather than silently join mid-square."""
    env = dict(os.environ, BASE_DIR=str(tmp_path))
    prog = f'BASE_DIR={tmp_path} bash {SCRIPT} install'
    # Force "now" past the whole schedule by faking date(1) ahead of the script.
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "date").write_text('#!/bin/sh\necho "2099-01-01T00:00"\n')
    (fake / "date").chmod(0o755)
    env["PATH"] = f"{fake}:{env['PATH']}"
    r = subprocess.run(["bash", "-c", prog], capture_output=True, text=True, env=env)
    assert r.returncode == 1
    assert "REFUSING to install" in (r.stdout + r.stderr)


def test_current_schedule_is_not_fully_stale():
    """Guards the guard: a shipped schedule whose SELF-TERMINATOR has passed is
    dead weight — the next launch hits `install`'s refusal instead of running.

    S73 correction: the original assertion ("first row in the future") went red
    the morning the campaign legitimately launched and would have stayed red for
    all 9 days of it — conflating "campaign in flight" with "schedule stale."
    In flight (first row past, terminator future) is exactly the state the
    DEC-0066 refusal exists to protect; only a fully-elapsed window is stale.

    S88 (DEC-0096): an EMPTY block is the deliberate between-campaigns
    stand-down state and passes; the classification lives in _schedule_state
    so the stale branch stays positively controlled in the section below.
    """
    rows = _schedule_rows()
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
    state = _schedule_state(rows, now)
    assert state != "stale", (
        f"shipped SCHEDULE is fully elapsed (terminator {rows[-1][0]} < now {now}) "
        f"-- empty it (stand-down, DEC-0096) or regenerate it for the next launch"
    )


# ── Stand-down: the between-campaigns state (S88, DEC-0096) ──────────────────
# Once a campaign's terminator passes, the staleness guard above goes red on
# EVERY pull request (tests is a required check on dev and main) until the
# block is regenerated -- and between campaigns there is nothing honest to
# regenerate it to. The stand-down state is an EMPTY block: not-started to
# schedule_started(), NONE to due_arm(), refused by install, skipped by the
# structural tests, green to the staleness guard. A stale NON-empty schedule
# still fails exactly as before -- _schedule_state's stale branch is the
# positive control (DEC-0045).

def test_schedule_state_classifies_all_three_states():
    assert _schedule_state([], "2026-01-01T00:00") == "stand-down"
    live = [("2026-01-01T00:05", "A"), ("2026-01-02T00:05", "BASELINE")]
    assert _schedule_state(live, "2026-01-01T12:00") == "live"
    # positive control: fully elapsed must read STALE, never stand-down --
    # the gate keys on emptiness alone, so age can never slip through it.
    stale = [("2020-01-01T00:05", "A"), ("2020-01-02T00:05", "BASELINE")]
    assert _schedule_state(stale, "2026-01-01T00:00") == "stale"


def _empty_schedule_script(tmp_path) -> Path:
    """The real script with its SCHEDULE block emptied -- byte-for-byte the
    state a post-campaign stand-down commit ships."""
    src = SCRIPT.read_text()
    src, n = re.subn(r'^SCHEDULE="\n.*?^"', 'SCHEDULE="\n"', src,
                     flags=re.S | re.M)
    assert n == 1, "could not find the SCHEDULE block to empty"
    script = tmp_path / "rx_experiment.sh"
    script.write_text(src)
    script.chmod(0o755)
    return script


def test_empty_schedule_rows_parse_as_empty(tmp_path):
    """The real parser on the stand-down form is [] -- not [('',)] -- so every
    emptiness gate keys on the same parse the structural tests use."""
    script = _empty_schedule_script(tmp_path)
    assert _schedule_rows(script.read_text()) == []


def test_stand_down_reads_as_not_started_even_in_2099(tmp_path):
    script = _empty_schedule_script(tmp_path)
    prog = (f'source <(sed "/^# ── Modes/,\\$d" {script}); '
            f'schedule_started "2099-01-01T00:00"')
    r = subprocess.run(["bash", "-c", prog], capture_output=True, text=True)
    assert r.returncode == 1


def test_stand_down_due_arm_is_none(tmp_path):
    script = _empty_schedule_script(tmp_path)
    prog = f'source <(sed "/^# ── Modes/,\\$d" {script}); due_arm'
    r = subprocess.run(["bash", "-c", prog], capture_output=True, text=True)
    assert r.stdout.strip() == "NONE"


def test_install_refuses_when_no_campaign_scheduled(tmp_path):
    """End-to-end on the real script text: stand-down must refuse install
    loudly, never snapshot a baseline for a campaign that would never tick."""
    script = _empty_schedule_script(tmp_path)
    prog = f'BASE_DIR={tmp_path} bash {script} install'
    r = subprocess.run(["bash", "-c", prog], capture_output=True, text=True)
    assert r.returncode == 1
    out = r.stdout + r.stderr
    assert "REFUSING to install" in out
    assert "no campaign scheduled" in out


# ── RF-dead pause/resume (S79) ────────────────────────────────────────────────
# The guard's 30-min-mean reception floor used to go straight to trip_abort()
# (sticky STOP, revert to baseline, email) for every cause. That is still
# correct for a bad config write or an unhealthy post-swap check (tick's own
# abort calls, untested end-to-end here same as before this change -- they need
# a real docker + a real health_ok timing loop, out of scope for a fast unit
# suite). RF-dead reception dips now PAUSE instead: no config/container touch,
# auto-clears on weewx_monitor.py's own RECOVERY line, escalates to the
# unchanged trip_abort() only past a ceiling with no recovery.

BASELINE_FIXTURE = FIXTURE.replace("-gain 372", "-gain 207")
assert BASELINE_FIXTURE != FIXTURE, "fixture must actually differ from the live config"


def _rx_base(tmp_path):
    """A minimal installed campaign: baseline snapshotted, arm A live for an
    hour (clear of SETTLE_SECS), ready for `guard` to evaluate reception."""
    conf = tmp_path / "weewx-data" / "weewx.conf"
    conf.parent.mkdir(parents=True)
    conf.write_text(FIXTURE)
    baseline = tmp_path / "weewx.conf.rx-baseline"
    baseline.write_text(BASELINE_FIXTURE)
    logs = tmp_path / "logs"
    logs.mkdir()
    state = tmp_path / "rx_experiment.state"
    state.write_text(f"A|{int(time.time()) - 3600}|2026-01-01 00:00:00\n")
    return conf, baseline, logs


def _call_guard(tmp_path):
    env = dict(os.environ, RX_BASE=str(tmp_path))
    return subprocess.run(["bash", str(SCRIPT), "guard"], capture_output=True, text=True, env=env)


def _reception_lines(pct: int, n: int = 6) -> str:
    now = datetime.datetime.now()
    return "\n".join(
        f"{(now - datetime.timedelta(minutes=5 * (n - i))).strftime('%Y-%m-%d %H:%M:%S')} "
        f"RECEPTION: {pct}% avg over last 5 windows [LOW] (bad windows: {i})"
        for i in range(n)
    ) + "\n"


def test_guard_pauses_instead_of_aborting_on_reception_floor(tmp_path):
    conf, baseline, logs = _rx_base(tmp_path)
    (logs / "weewx_monitor.log").write_text(_reception_lines(30))

    r = _call_guard(tmp_path)
    assert r.returncode == 0
    assert (tmp_path / "rx_experiment.PAUSE").exists(), "should pause, not silently do nothing"
    assert not (tmp_path / "rx_experiment.STOP").exists(), "must not hard-abort on first trip"
    assert conf.read_text() == FIXTURE, "a pause must not touch the live config"
    xlog = (logs / "rx_experiment.log").read_text()
    assert "PAUSE:" in xlog and "arm A" in xlog


def test_guard_does_nothing_when_reception_is_healthy(tmp_path):
    conf, baseline, logs = _rx_base(tmp_path)
    (logs / "weewx_monitor.log").write_text(_reception_lines(75))

    r = _call_guard(tmp_path)
    assert r.returncode == 0
    assert not (tmp_path / "rx_experiment.PAUSE").exists()
    assert not (tmp_path / "rx_experiment.STOP").exists()
    assert conf.read_text() == FIXTURE


def test_guard_resumes_when_monitor_logs_recovery(tmp_path):
    conf, baseline, logs = _rx_base(tmp_path)
    pause_started = datetime.datetime.now() - datetime.timedelta(minutes=5)
    (tmp_path / "rx_experiment.PAUSE").write_text(
        f"{int(pause_started.timestamp())}|{pause_started.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    recovery_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
    (logs / "weewx_monitor.log").write_text(
        f"{recovery_time.strftime('%Y-%m-%d %H:%M:%S')} RECEPTION RECOVERY: 62% avg after 9min\n"
    )

    r = _call_guard(tmp_path)
    assert r.returncode == 0
    assert not (tmp_path / "rx_experiment.PAUSE").exists(), "recovery must clear the pause"
    assert not (tmp_path / "rx_experiment.STOP").exists()
    assert conf.read_text() == FIXTURE, "resume must not touch config either"
    assert "RESUME:" in (logs / "rx_experiment.log").read_text()


def test_guard_does_not_resume_on_a_recovery_line_before_the_pause_started(tmp_path):
    """The recovery must be NEWER than the pause, or a stale RECOVERY line from
    a previous, already-handled episode could clear a pause that never actually
    recovered."""
    conf, baseline, logs = _rx_base(tmp_path)
    pause_started = datetime.datetime.now() - datetime.timedelta(minutes=5)
    (tmp_path / "rx_experiment.PAUSE").write_text(
        f"{int(pause_started.timestamp())}|{pause_started.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    stale_recovery = pause_started - datetime.timedelta(minutes=30)
    (logs / "weewx_monitor.log").write_text(
        f"{stale_recovery.strftime('%Y-%m-%d %H:%M:%S')} RECEPTION RECOVERY: 62% avg after 9min\n"
    )

    r = _call_guard(tmp_path)
    assert r.returncode == 0
    assert (tmp_path / "rx_experiment.PAUSE").exists(), "a stale recovery must not clear a live pause"


def test_guard_resumes_from_a_periodic_ok_line_even_without_a_recovery_line(tmp_path):
    """End-to-end version of the 2026-08-14 incident fix: reception reads
    healthy on the monitor's ordinary periodic line, no ALERT/RECOVERY pair
    ever fires, and the guard must still auto-resume rather than sit paused
    until the 120-min ceiling escalates to a needless hard abort."""
    conf, baseline, logs = _rx_base(tmp_path)
    pause_started = datetime.datetime.now() - datetime.timedelta(minutes=30)
    (tmp_path / "rx_experiment.PAUSE").write_text(
        f"{int(pause_started.timestamp())}|{pause_started.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    ok_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
    (logs / "weewx_monitor.log").write_text(
        f"{ok_time.strftime('%Y-%m-%d %H:%M:%S')} RECEPTION: 71% avg over last 5 windows [OK] "
        "(bad windows: 0)\n"
    )

    r = _call_guard(tmp_path)
    assert r.returncode == 0
    assert not (tmp_path / "rx_experiment.PAUSE").exists(), "a healthy periodic read must resume"
    assert not (tmp_path / "rx_experiment.STOP").exists()
    assert "RESUME:" in (logs / "rx_experiment.log").read_text()


def test_guard_escalates_to_full_abort_past_the_ceiling(tmp_path):
    conf, baseline, logs = _rx_base(tmp_path)
    pause_started = datetime.datetime.now() - datetime.timedelta(seconds=7300)  # > 7200s ceiling
    (tmp_path / "rx_experiment.PAUSE").write_text(
        f"{int(pause_started.timestamp())}|{pause_started.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    (logs / "weewx_monitor.log").write_text("")  # no recovery ever logged

    r = _call_guard(tmp_path)
    assert r.returncode == 1
    assert not (tmp_path / "rx_experiment.PAUSE").exists(), "escalation must clear the pause marker"
    stop = tmp_path / "rx_experiment.STOP"
    assert stop.exists(), "must fall through to the real sticky abort"
    assert "exceeded" in stop.read_text() and "120min" in stop.read_text()
    assert conf.read_text() == baseline.read_text(), "escalation restores baseline like any other abort"


def test_guard_ignores_pause_when_stop_is_already_present(tmp_path):
    """STOP still short-circuits before any pause logic runs -- a manual/escalated
    halt is never silently reinterpreted as an ordinary pause."""
    conf, baseline, logs = _rx_base(tmp_path)
    (tmp_path / "rx_experiment.STOP").write_text("2026-01-01 00:00:00 some earlier abort\n")
    (tmp_path / "rx_experiment.PAUSE").write_text(f"{int(time.time())}|2026-01-01 00:00:00\n")

    r = _call_guard(tmp_path)
    assert r.returncode == 0
    assert (tmp_path / "rx_experiment.PAUSE").exists(), "STOP exits before the pause branch is reached"


# --- recovered_since() in isolation -------------------------------------------

def _call_recovered_since(monlog: Path, since: str):
    prog = (
        f'source <(sed "/^# ── Modes/,\\$d" {SCRIPT}); '
        f'MONLOG={monlog}; recovered_since "{since}"'
    )
    return subprocess.run(["bash", "-c", prog], capture_output=True, text=True)


def test_recovered_since_true_when_recovery_line_is_after_pause_start(tmp_path):
    mon = tmp_path / "mon.log"
    mon.write_text("2026-08-13 01:51:33 RECEPTION RECOVERY: 62% avg after 9min\n")
    assert _call_recovered_since(mon, "2026-08-13 01:40:00").returncode == 0


def test_recovered_since_false_when_recovery_line_is_before_pause_start(tmp_path):
    mon = tmp_path / "mon.log"
    mon.write_text("2026-08-13 01:51:33 RECEPTION RECOVERY: 62% avg after 9min\n")
    assert _call_recovered_since(mon, "2026-08-13 02:00:00").returncode != 0


def test_recovered_since_true_from_a_periodic_ok_line_even_without_a_recovery_line(tmp_path):
    """The actual 2026-08-14 incident, reproduced: a healthy periodic [OK] read
    with no RECOVERY line at all (because reception never dropped low enough
    again to re-trigger a fresh ALERT) must still count as recovered -- this
    exact fixture used to assert the opposite, which is why the pause rode the
    full 120-min ceiling into a needless hard abort that night.
    """
    mon = tmp_path / "mon.log"
    mon.write_text(
        "2026-08-13 01:51:33 RECEPTION: 62% avg over last 5 windows [OK] (bad windows: 0)\n"
    )
    assert _call_recovered_since(mon, "2026-08-13 01:00:00").returncode == 0


def test_recovered_since_false_when_periodic_line_is_below_the_pause_floor(tmp_path):
    """40% is below ABORT_PCT (50) — still paused. (S82 renamed this from
    'low_not_ok': the resume criterion is now the pause floor itself, not the
    monitor's [OK] tag, so what keeps this red is 40 < 50, not the [LOW] tag.)"""
    mon = tmp_path / "mon.log"
    mon.write_text(
        "2026-08-13 01:51:33 RECEPTION: 40% avg over last 5 windows [LOW] (bad windows: 3)\n"
    )
    assert _call_recovered_since(mon, "2026-08-13 01:00:00").returncode != 0


def test_recovered_since_false_when_only_ok_line_is_stale_before_pause(tmp_path):
    """An [OK] read that predates the pause is exactly as stale as a predating
    RECOVERY line (already covered above) -- it must not clear a pause that
    started after the station was already fine and has said nothing since."""
    mon = tmp_path / "mon.log"
    mon.write_text(
        "2026-08-13 00:30:00 RECEPTION: 70% avg over last 5 windows [OK] (bad windows: 0)\n"
    )
    assert _call_recovered_since(mon, "2026-08-13 01:00:00").returncode != 0


def test_recovered_since_false_when_monlog_has_neither_line_type(tmp_path):
    mon = tmp_path / "mon.log"
    mon.write_text("")
    assert _call_recovered_since(mon, "2026-08-13 01:00:00").returncode != 0


# ── S82 state-machine audit fixes ─────────────────────────────────────────────
# Five defects from the S82 audit of this script's guard/tick/abort/pause/resume
# machine, each with its regression test: (1) the resume criterion was stricter
# than the pause floor (a [50,60) trap band that rode the ceiling into a
# needless abort); (2) recovered_since() and the guard's floor mean read only
# the live monitor log, which rotates at 00:05 -- the exact swap minute;
# (3) a scheduled swap force-cleared an active pause and swapped INTO the
# episode, converting the soft pause back into the hard abort; (4) the guard
# never stood down after the BASELINE self-terminator; (5) tick/guard had no
# mutual exclusion although a full-budget health_ok outlives the 5-min cron
# period (both interleavings are in the 2026-08-11 02:05:03 log).


def test_recovered_since_true_at_the_pause_floor_even_when_tagged_low(tmp_path):
    """The S82 flip: 55% is >= ABORT_PCT (50), so a pause must end -- even
    though the monitor tags anything under 60% [LOW]. Under the old
    [OK]-required rule this exact fixture stayed paused and would have ridden
    the 120-min ceiling into a needless abort, the DEC-0089 failure one band
    lower. Reception genuinely sat in this band on 08-13/14 (52-58% reads)."""
    mon = tmp_path / "mon.log"
    mon.write_text(
        "2026-08-13 01:51:33 RECEPTION: 55% avg over last 5 windows [LOW] (bad windows: 2)\n"
    )
    assert _call_recovered_since(mon, "2026-08-13 01:00:00").returncode == 0


def test_recovered_since_false_just_below_the_pause_floor(tmp_path):
    """Boundary: 49 < 50 stays paused. Entry and exit share ABORT_PCT exactly."""
    mon = tmp_path / "mon.log"
    mon.write_text(
        "2026-08-13 01:51:33 RECEPTION: 49% avg over last 5 windows [LOW] (bad windows: 2)\n"
    )
    assert _call_recovered_since(mon, "2026-08-13 01:00:00").returncode != 0


def test_recovered_since_reads_the_rotated_monitor_log(tmp_path):
    """weewx_monitor.log rotates daily at 00:05 -- the exact minute of every
    swap slot. A recovery that landed just before rotation lives in .log.1;
    the single-file read went blind on it (harvest() and soak_check.sh both
    already read the pair; recovered_since() had not)."""
    mon = tmp_path / "mon.log"
    mon.write_text("")  # fresh post-rotation file, nothing in it yet
    (tmp_path / "mon.log.1").write_text(
        "2026-08-13 01:51:33 RECEPTION: 71% avg over last 5 windows [OK] (bad windows: 0)\n"
    )
    assert _call_recovered_since(mon, "2026-08-13 01:00:00").returncode == 0


def test_guard_floor_reads_the_rotated_monitor_log(tmp_path):
    """The pause floor needs ABORT_SAMPLES periodic lines; after rotation the
    live log holds fewer than six for ~30 minutes -- nightly, at the hour the
    episode cluster lives. Three lines either side of the rotation must still
    add up to a quorum (pre-S82 this fixture produced no pause: n=3 < 6)."""
    conf, baseline, logs = _rx_base(tmp_path)
    (logs / "weewx_monitor.log.1").write_text(_reception_lines(30, n=3))
    (logs / "weewx_monitor.log").write_text(_reception_lines(30, n=3))

    r = _call_guard(tmp_path)
    assert r.returncode == 0
    assert (tmp_path / "rx_experiment.PAUSE").exists(), \
        "six low lines split across the rotation must still trip the floor"


def _fake_date(tmp_path, env, now: str):
    """Prepend a PATH shim so date(1) always answers NOW (the install-test
    trick, reused). Only for paths that never reach acquire_lock's arithmetic."""
    fake = tmp_path / "bin"
    fake.mkdir(exist_ok=True)
    (fake / "date").write_text(f'#!/bin/sh\necho "{now}"\n')
    (fake / "date").chmod(0o755)
    env["PATH"] = f"{fake}:{env['PATH']}"
    return env


def _call_tick(tmp_path, fake_now=None):
    env = dict(os.environ, RX_BASE=str(tmp_path))
    if fake_now:
        env = _fake_date(tmp_path, env, fake_now)
    return subprocess.run(["bash", str(SCRIPT), "tick"],
                          capture_output=True, text=True, env=env)


def test_tick_defers_swap_while_paused(tmp_path):
    """A due swap must WAIT out an active reception pause, not clear it and
    swap into the episode: health_ok waits on archive records, records stop
    during RF-dead episodes (DEC-0069/0077), so the old supersede rule
    converted DEC-0087's soft pause straight back into the hard sticky abort.
    Schedule-agnostic: pins now to the last real arm row, whatever the
    regenerated dates say."""
    conf, baseline, logs = _rx_base(tmp_path)
    when, arm = _schedule_rows()[-2]          # last non-BASELINE row
    assert arm != "BASELINE"
    have = "H" if arm != "H" else "A"
    (tmp_path / "rx_experiment.state").write_text(
        f"{have}|{int(time.time()) - 3600}|2026-01-01 00:00:00\n")
    (tmp_path / "rx_experiment.PAUSE").write_text(
        f"{int(time.time()) - 300}|2026-01-01 00:00:00\n")
    sha_before = _sha(conf)

    r = _call_tick(tmp_path, fake_now=when)
    assert r.returncode == 0
    assert (tmp_path / "rx_experiment.PAUSE").exists(), "the pause must survive the tick"
    assert _sha(conf) == sha_before, "a deferred swap must not touch the config"
    state = (tmp_path / "rx_experiment.state").read_text()
    assert state.startswith(f"{have}|"), "a deferred swap must not advance the state"
    xlog = (logs / "rx_experiment.log").read_text()
    assert "deferred" in xlog and f"-> {arm}" in xlog


def test_tick_baseline_supersedes_pause(tmp_path):
    """The self-terminator is exempt from deferral: ending on prod config must
    never wait on RF (safety property #5), and it runs no health check an
    episode could fail. A pause present at campaign end is cleared, baseline
    restored, completion recorded."""
    conf, baseline, logs = _rx_base(tmp_path)
    (tmp_path / "rx_experiment.PAUSE").write_text(
        f"{int(time.time()) - 300}|2026-01-01 00:00:00\n")

    r = _call_tick(tmp_path, fake_now="2099-01-01T00:00")
    assert r.returncode == 0
    assert not (tmp_path / "rx_experiment.PAUSE").exists(), \
        "BASELINE must clear the pause, not defer to it"
    assert conf.read_text() == baseline.read_text(), "prod must end on the baseline config"
    assert (tmp_path / "rx_experiment.state").read_text().startswith("BASELINE|")
    xlog = (logs / "rx_experiment.log").read_text()
    assert "CAMPAIGN COMPLETE" in xlog


def test_guard_stands_down_after_baseline_self_termination(tmp_path):
    """After the campaign self-terminates the guard must go quiet. It used to
    stay armed forever (the scheduler entries deliberately persist between
    campaigns), so the first long episode after a clean campaign end would
    pause, ride the ceiling, restart prod for nothing and email 'campaign
    halted' about a campaign that no longer existed."""
    conf, baseline, logs = _rx_base(tmp_path)
    (tmp_path / "rx_experiment.state").write_text(
        f"BASELINE|{int(time.time()) - 3600}|2026-01-01 00:00:00\n")
    (logs / "weewx_monitor.log").write_text(_reception_lines(30))  # would pause if armed

    r = _call_guard(tmp_path)
    assert r.returncode == 0
    assert not (tmp_path / "rx_experiment.PAUSE").exists(), \
        "no pause after self-termination -- the campaign is over"
    assert not (tmp_path / "rx_experiment.STOP").exists()


def test_second_instance_skips_while_lock_is_held_by_a_live_process(tmp_path):
    """Mutual exclusion: while a live holder works, the next pass skips --
    and must NOT dismantle the holder's lock on its way out."""
    conf, baseline, logs = _rx_base(tmp_path)
    (logs / "weewx_monitor.log").write_text(_reception_lines(30))  # would pause if it ran
    lock = tmp_path / "rx_experiment.lock"
    lock.mkdir()
    (lock / "pid").write_text(str(os.getpid()))  # this test process: alive

    r = _call_guard(tmp_path)
    assert r.returncode == 0
    assert not (tmp_path / "rx_experiment.PAUSE").exists(), "a skipped pass must do nothing"
    assert lock.exists(), "a live holder's lock must survive the skipped pass"
    assert "holds the lock" in (logs / "rx_experiment.log").read_text()


def test_stale_lock_from_a_dead_holder_is_broken(tmp_path):
    """A crashed holder must not wedge the campaign: a lock whose pid is dead
    is broken loudly and the pass proceeds (a silently-skipped tick forever
    would be the due_arm() no-op trap wearing a new hat)."""
    conf, baseline, logs = _rx_base(tmp_path)
    (logs / "weewx_monitor.log").write_text(_reception_lines(30))
    proc = subprocess.Popen(["true"])
    proc.wait()                                # reaped: pid is dead
    lock = tmp_path / "rx_experiment.lock"
    lock.mkdir()
    (lock / "pid").write_text(str(proc.pid))

    r = _call_guard(tmp_path)
    assert r.returncode == 0
    xlog = (logs / "rx_experiment.log").read_text()
    assert "breaking stale lock" in xlog
    assert (tmp_path / "rx_experiment.PAUSE").exists(), \
        "after breaking the stale lock the pass must actually run"
    assert not lock.exists(), "the pass must release the lock it took over"
