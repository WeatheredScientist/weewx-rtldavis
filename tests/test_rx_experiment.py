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
import hashlib
import os
import re
import subprocess
import textwrap
from pathlib import Path

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

def _schedule_rows():
    src = SCRIPT.read_text()
    block = re.search(r'^SCHEDULE="\n(.*?)^"', src, re.S | re.M).group(1)
    return [tuple(row.split("|")) for row in block.strip().split("\n")]


def test_schedule_is_a_balanced_latin_square():
    """Each square arm must visit each 6h slot exactly twice — that balance IS
    the control for time-of-day and diurnal drift. A typo here silently
    reintroduces the confound the whole design exists to remove, and nothing at
    runtime would notice. Pilot (P*) and hold (H) rows are campaign B's
    calibration prefix, not square blocks — they are excluded here and asserted
    by their own tests below."""
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
    first = _first_row_time()
    before = first[:-1] + str(int(first[-1]) - 1) if first[-1] != "0" else "2000-01-01T00:00"
    assert _call_schedule_started(before).returncode == 1


def test_schedule_started_when_first_row_has_passed():
    """The trap: first row in the past means we would join mid-flight."""
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
    """
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
    src = SCRIPT.read_text()
    body = re.search(r'SCHEDULE="\n(.*?)"', src, re.S).group(1)
    rows = [ln for ln in body.strip().split("\n") if ln]
    last_time, last_arm = rows[-1].split("|")
    assert last_arm == "BASELINE", "schedule must end with the self-terminator"
    assert last_time > now, (
        f"shipped SCHEDULE is fully elapsed (terminator {last_time} < now {now}) "
        f"-- regenerate it before the next launch"
    )
