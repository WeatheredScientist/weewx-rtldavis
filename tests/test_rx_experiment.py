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
    """Each arm must visit each 6h slot exactly twice — that balance IS the
    control for time-of-day and diurnal drift. A typo here silently reintroduces
    the confound the whole design exists to remove, and nothing at runtime would
    notice."""
    rows = [r for r in _schedule_rows() if r[1] != "BASELINE"]
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
    """REGRESSION (S57). The health check's 18 tries (~90s) was too small BY
    CONSTRUCTION and aborted a live campaign 3 seconds early.

    A restart cannot produce an archive record faster than boot + up to a full
    archive interval + the post-boundary write lag. The arithmetic is asserted
    here rather than the bare number, so lowering the budget fails the test with
    the reason attached. Measured on the real failure: weewxd init 12:11:46,
    first record 12:13:30 = 104s, abort at 12:13:27.
    """
    src = SCRIPT.read_text()
    tries = int(re.search(r"^HEALTH_TRIES=(\d+)", src, re.M).group(1))
    sleep_s = int(re.search(
        r'for i in \$\(seq 1 "\$HEALTH_TRIES"\); do\s*\n\s*sleep (\d+)', src, re.M).group(1))

    boot_s, archive_interval_s, write_lag_s = 25, 60, 30   # observed on this station
    worst_case = boot_s + archive_interval_s + write_lag_s  # ~115s

    assert tries * sleep_s >= worst_case, (
        f"health budget {tries * sleep_s}s cannot cover the {worst_case}s worst case "
        f"(boot {boot_s} + archive interval {archive_interval_s} + write lag {write_lag_s})"
    )
