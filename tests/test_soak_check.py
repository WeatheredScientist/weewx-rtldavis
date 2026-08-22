"""Offline tests for ops/soak_check.sh — the station's health gate.

Written after S87, when the soak reported

    FAIL  MONITOR LOG STALE   pid alive but log -82s old — wedged

against a watchdog that was polling perfectly on schedule, every 30 s, with no
gaps. The age was NEGATIVE and the script said "wedged" anyway.

Root cause: the remote block captured `now` at its top, then measured every age
against it at the bottom — after `docker logs`, a full weewx.log window read and
a `docker exec` sqlite loop. Every age was understated by the block's own runtime.
Historically that runtime was ~2 s and nothing showed; by 2026-08-17 it was 24-100 s
under load, so the monitor's 30 s poll always landed AFTER `now` and the age was
reliably negative. Ten days of a guaranteed false alarm on a healthy watchdog.

The quieter half was worse: the same stale clock fed record_age_s, the DEC-0036
freeze detector, whose 180 s threshold silently became 180+runtime — least
sensitive exactly when the box is loaded, which is when freezes happen.

These tests encode DEC-0039/DEC-0045's rule, the one this repo has had to relearn
six times on the secret gate: a passing test proves nothing without a POSITIVE
CONTROL. So every "it no longer cries wolf" assertion below is paired with a
"...and it still fires when it should" assertion. If the paired test ever goes
green by the check never firing, the fix has quietly disabled the check instead
of correcting it, and these tests have lost their teeth.

The script is driven for real, with `ssh` stubbed on PATH — so what is under test
is the deployed file, not a copy of its logic. HOME is redirected to a temp dir so
the real ~/.claude/nas.env cannot be sourced and no NAS is ever contacted.

Run:  .venv/bin/python -m pytest tests/test_soak_check.py
"""
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "ops" / "soak_check.sh"

# A fully healthy station. Individual tests override single keys to isolate one
# check at a time; everything else stays green so the assertion cannot be
# satisfied by unrelated noise.
HEALTHY = {
    "state": "running",
    "image": "weatheredscientist/weewx-rtldavis:v2.0.13",
    "restarts": "0",
    "started": "2026-08-17T22:07:18Z",
    "uptime_s": "3600",
    "since": "1787000000",
    "stdout_lines": "12",
    "stdout_logerr": "0",
    "banner": "1",
    "drv_ver": "0.20+ws.5",
    "qc_ok": "1",
    "hraw_on": "1",
    "hraw_n": "39",
    "stalls": "0",
    "tracebacks": "0",
    "criticals": "0",
    "published": "1551",
    "influx": "42",
    "last_record": "2026-08-17 19:12:00",
    "record_age_s": "55",
    "window_pct": "76",
    "rx_avg": "76",
    "rx_verdict": "OK",
    "mon_proc": "alive",
    "mon_log_age": "18",
    "mon_resets": "7",
    "mon_reset_bad": "0",
    "phantom_rain": "0",
    "archive_rows": "64",
    "remote_elapsed_s": "3",
    # Measured on the real box 2026-08-17: 33.61 MB archive, 3.69 GiB RAM = 0.9%.
    "db_bytes": "35241984",
    "mem_total_kb": "3866684",
}


def run_soak(tmp_path, **overrides):
    """Run the real script against a stubbed ssh. Returns its stdout."""
    payload = dict(HEALTHY, **overrides)
    blob = "".join(f"{k}={v}\n" for k, v in payload.items() if v is not None)

    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "ssh"
    # Ignores every argument and prints the canned k=v block, so the script's
    # single ssh round-trip is replaced wholesale. Nothing leaves this machine.
    stub.write_text("#!/usr/bin/env bash\ncat <<'SOAK_EOF'\n" + blob + "SOAK_EOF\n")
    stub.chmod(0o755)

    home = tmp_path / "home"
    home.mkdir(exist_ok=True)  # deliberately WITHOUT .claude/nas.env

    env = dict(os.environ)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env["HOME"] = str(home)
    env["NAS_PORT"], env["NAS_USER"], env["NAS_HOST"] = "22", "tester", "127.0.0.1"
    env["EXPECT_IMAGE"] = HEALTHY["image"]
    env["EXPECT_DRIVER"] = HEALTHY["drv_ver"]

    return subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=60
    ).stdout


def line_for(out, needle):
    """The single output line mentioning `needle`, or '' if absent."""
    return next((ln for ln in out.splitlines() if needle in ln), "")


# --- the S87 regression: a negative age is not a wedge ----------------------


def test_negative_monitor_age_is_not_reported_as_wedged(tmp_path):
    """The exact S87 symptom: -82 s reported as 'wedged' on a healthy watchdog."""
    out = run_soak(tmp_path, mon_log_age="-82")
    assert "MONITOR LOG STALE" not in out
    assert "wedged" not in out
    assert "clock skew" in line_for(out, "future")


def test_stale_monitor_log_still_fails(tmp_path):
    """POSITIVE CONTROL for the test above.

    If this ever passes by NOT failing, the S87 fix disabled the wedge detector
    rather than correcting it, and the test above is proving nothing.
    """
    out = run_soak(tmp_path, mon_log_age="900")
    assert "MONITOR LOG STALE" in out
    assert "wedged" in out


def test_missing_monitor_log_is_distinct_from_wedged(tmp_path):
    """-1 is the 'no log file' sentinel, not an age. It has its own verdict."""
    out = run_soak(tmp_path, mon_log_age="-1")
    assert "MONITOR LOG MISSING" in out
    assert "MONITOR LOG STALE" not in out


def test_dead_monitor_still_fails(tmp_path):
    """POSITIVE CONTROL: the dead-watchdog branch survived the S87 rewrite."""
    out = run_soak(tmp_path, mon_proc="dead")
    assert "MONITOR/WATCHDOG DEAD" in out


def test_healthy_monitor_passes(tmp_path):
    out = run_soak(tmp_path)
    assert "monitor/watchdog alive" in out
    assert "MONITOR" not in line_for(out, "monitor/watchdog alive").upper().replace(
        "MONITOR/WATCHDOG ALIVE", ""
    )


# --- the root cause: ages must never be measured against a stale clock -------


def test_ages_are_measured_against_a_fresh_clock():
    """Guards the actual defect, not just its symptom.

    `now` is captured at the top of the remote block; any age computed against it
    is understated by however long the block takes. Both age measurements must
    read the clock at the point of measurement instead.
    """
    src = SCRIPT.read_text()
    for key in ("record_age_s", "mon_log_age"):
        line = next(ln for ln in src.splitlines() if f"{key}=" in ln and "echo" in ln)
        assert "date +%s" in line, f"{key} must read a fresh clock, got: {line.strip()}"
        assert not re.search(r"\bnow\s*-", line), (
            f"{key} is measured against the stale top-of-block `now`: {line.strip()}"
        )


def test_remote_runtime_is_reported():
    """The runtime corrupted every age silently. It is now surfaced, not hidden."""
    src = SCRIPT.read_text()
    assert "remote_elapsed_s" in src
    assert "remote probe took" in src


# --- reception: the monitor's own verdict, not a second threshold ------------


def test_baseline_reception_does_not_warn(tmp_path):
    """76% is ABOVE this station's measured 73.3% baseline (DEC-0059).

    The old check warned on it anyway, against a hardcoded 80% floor applied to a
    single 60 s window whose sd is ~9.7 pts — a warning on most healthy runs.
    """
    out = run_soak(tmp_path, rx_avg="76", rx_verdict="OK")
    assert "reception window low" not in out
    assert "PASS" in line_for(out, "reception")


def test_low_reception_still_warns(tmp_path):
    """POSITIVE CONTROL: genuinely low reception is still surfaced."""
    out = run_soak(tmp_path, rx_avg="41", rx_verdict="LOW")
    assert "reception LOW per monitor" in out
    assert "41%" in out


def test_missing_reception_verdict_falls_back_to_raw_window(tmp_path):
    """The aggregate only logs every 5 min; a fresh monitor has no verdict yet."""
    out = run_soak(tmp_path, rx_avg="", rx_verdict="")
    assert "no monitor reception verdict yet" in out
    assert "76%" in out


# --- the freeze detector must keep its teeth ---------------------------------


def test_archive_stall_still_fails(tmp_path):
    """POSITIVE CONTROL: DEC-0036's detector still fires past its 180 s threshold."""
    out = run_soak(tmp_path, record_age_s="400")
    assert "ARCHIVE STALLED" in out


def test_fresh_archive_record_passes(tmp_path):
    out = run_soak(tmp_path, record_age_s="55")
    assert "archive records still arriving" in out
    assert "ARCHIVE STALLED" not in out


# --- DEC-0095's retention tripwire: accept-and-monitor that actually executes ------


def test_todays_archive_is_within_budget(tmp_path):
    """The real 2026-08-17 measurement must sit comfortably inside the budget.

    If this ever fails at 33 MB against 3.69 GiB, the ratio arithmetic is wrong,
    not the station.
    """
    out = run_soak(tmp_path)
    line = line_for(out, "retention budget")
    assert "archive within retention budget" in line
    assert "0.9% of RAM" in line


def test_archive_over_ten_percent_of_ram_trips(tmp_path):
    """POSITIVE CONTROL: DEC-0095 ships its own reversal condition, so the condition
    has to be reachable. 400 MB against 3.69 GiB is 10.6% — just over.
    """
    out = run_soak(tmp_path, db_bytes=str(400 * 1024 * 1024))
    assert "ARCHIVE OVER RETENTION BUDGET" in out
    assert "DEC-0095" in out


def test_tripwire_says_so_when_it_cannot_measure(tmp_path):
    """An unmeasurable tripwire must announce itself, not silently read as green.

    The whole point of DEC-0095's monitor half is that it executes; a missing
    measurement that printed nothing would be the EXPECT_IMAGE failure again.
    """
    out = run_soak(tmp_path, db_bytes="0", mem_total_kb="0")
    assert "retention tripwire unmeasured" in out
    assert "unmonitored" in out


# --- #252: the remote-side window computation must survive a midnight rotation --
#
# Everything above stubs ssh and tests the CLIENT-side parsing of a canned k=v
# blob -- it never executes the bash that actually runs on the NAS, inside the
# ssh argument. That layer needs a different harness: the LY/both/ln/win block
# is pulled verbatim out of the deployed script and unescaped back to plain
# bash, then run directly against fake local log files. What's under test is
# still the real file's logic, just executed locally instead of over ssh.


def _extract_window_block():
    src = SCRIPT.read_text()
    start = src.index("\nLY=") + 1
    end = src.index('\necho \\"drv_ver=', start)
    return src[start:end].replace('\\$', '$').replace('\\"', '"')


WINDOW_BLOCK = _extract_window_block()


def _gnu_date_env():
    """Env whose PATH resolves `date` to a GNU-compatible `date -d`.

    The window block (like the rest of this script) assumes GNU date
    semantics -- true on every real target (Linux CI, the Synology NAS).
    macOS ships BSD date, which has no `-d` at all; shim it via Homebrew
    coreutils' `gdate` so this test also runs locally.
    """
    env = dict(os.environ)
    probe = subprocess.run(["date", "-d", "yesterday", "+%s"], capture_output=True)
    if probe.returncode == 0:
        return env  # system date is already GNU-compatible
    gdate = shutil.which("gdate")
    if not gdate:
        pytest.skip("no GNU-compatible `date -d` on PATH (install coreutils for gdate)")
    shim = Path(tempfile.mkdtemp()) / "bin"
    shim.mkdir()
    (shim / "date").symlink_to(gdate)
    env["PATH"] = f"{shim}{os.pathsep}{env['PATH']}"
    return env


DATE_ENV = _gnu_date_env()


def _date(*args):
    return subprocess.run(
        ["date", *args], capture_output=True, text=True, check=True, env=DATE_ENV
    ).stdout.strip()


def run_window_block(tmp_path, t0, today_lines, yesterday_lines):
    """Write fake today/yesterday logs and run the real window-computation
    block against them, returning the banner=/restart_times= lines it echoes."""
    L = tmp_path / "weewx.log"
    L.write_text("".join(ln + "\n" for ln in today_lines))
    LY = tmp_path / f"weewx.log.{_date('-d', 'yesterday', '+%Y-%m-%d')}"
    LY.write_text("".join(ln + "\n" for ln in yesterday_lines))
    script = f'L="{L}"\nnow=$(date +%s)\nt0={t0}\n{WINDOW_BLOCK}\n'
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, timeout=30, env=DATE_ENV
    ).stdout


def test_window_spans_midnight_into_yesterdays_rotated_log(tmp_path):
    """The #252 bug, reproduced: t0 (container start) at 23:50 predates
    midnight, so the startup banner lives only in yesterday's rotated file.
    Pre-fix, grep -n ran against today's file alone, found no match for
    yesterday's date-hour, and fell back to ln=1 -- "the whole of today's
    log" -- which does not contain the banner line at all.
    """
    t0 = int(_date("-d", "yesterday 23:50:00", "+%s"))
    banner_line = (
        _date("-d", f"@{t0}", "+%Y-%m-%d %H:%M:%S")
        + " weewxd 0.20+ws.5: Initializing weewxd version 5.3.1"
    )
    out = run_window_block(
        tmp_path, t0,
        today_lines=["2099-01-01 00:20:00 INFO weewx.engine: unrelated startup line"],
        yesterday_lines=[banner_line],
    )
    assert "banner=1" in out


def test_window_still_reports_no_banner_when_truly_absent(tmp_path):
    """POSITIVE CONTROL for the test above: with no banner line in either
    file, the fix must not have started reporting one unconditionally."""
    t0 = int(_date("-d", "yesterday 23:50:00", "+%s"))
    out = run_window_block(
        tmp_path, t0,
        today_lines=["2099-01-01 00:20:00 INFO weewx.engine: unrelated line"],
        yesterday_lines=[
            _date("-d", f"@{t0}", "+%Y-%m-%d %H:%M:%S") + " INFO weewx.engine: also unrelated"
        ],
    )
    assert "banner=0" in out
