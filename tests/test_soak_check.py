"""Offline tests for ops/soak_check.sh — the station's health gate.

Ported to the `marvinctl` transport (ops#287): the script used to make ONE ssh
round trip and get back a single k=v blob computed by a remote awk/grep script;
it now makes many small `marvinctl --tenant weewx <verb>` calls, each reading
one thing (inspect, a log file, a systemd unit, /proc/meminfo, a stat). The stub
below is a fake `marvinctl` that serves canned files out of a per-test scenario
directory, keyed by verb and (for cat/grep/stat) the basename of the path asked
for — the script's own windowing/counting logic runs for real against that
content, unlike the old ssh stub which returned pre-computed answers directly.

Still governed by DEC-0039/DEC-0045's rule: a passing test proves nothing
without a POSITIVE CONTROL, so most "it doesn't cry wolf" assertions below are
paired with an "...and it still fires when it should" one.

The script is driven for real, with `marvinctl` stubbed on PATH — what is under
test is the deployed file, not a copy of its logic. HOME is redirected to a temp
dir; nothing real is ever contacted.

Run:  .venv/bin/python -m pytest tests/test_soak_check.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "ops" / "soak_check.sh"


def _gnu_date_env() -> dict[str, str]:
    """Env whose PATH resolves `date` to a GNU-compatible `date -d`.

    The script assumes GNU date semantics -- true on every real target (Linux
    CI, marvin itself). macOS ships BSD date with no `-d` at all; shim it via
    Homebrew coreutils' `gdate` so this suite also runs locally.
    """
    env = dict(os.environ)
    probe = subprocess.run(["date", "-d", "yesterday", "+%s"], capture_output=True)
    if probe.returncode == 0:
        return env
    gdate = shutil.which("gdate")
    if not gdate:
        pytest.skip("no GNU-compatible `date -d` on PATH (install coreutils for gdate)")
    shim = Path(tempfile.mkdtemp()) / "bin"
    shim.mkdir()
    (shim / "date").symlink_to(gdate)
    env["PATH"] = f"{shim}{os.pathsep}{env['PATH']}"
    return env


DATE_ENV = _gnu_date_env()


def _date(*args: str) -> str:
    return subprocess.run(
        ["date", *args], capture_output=True, text=True, check=True, env=DATE_ENV
    ).stdout.strip()


def now_epoch() -> int:
    return int(_date("+%s"))


def _iso_utc(epoch: int) -> str:
    return _date("-u", "-d", f"@{epoch}", "+%Y-%m-%dT%H:%M:%SZ")


def _local(epoch: int) -> str:
    return _date("-d", f"@{epoch}", "+%Y-%m-%d %H:%M:%S")


def _local_offset(epoch: int) -> str:
    """This process's own UTC offset at `epoch` (e.g. "-0400") -- real `stat`
    always stamps the actual local offset, never a fixed one, so a crafted
    fixture that hardcodes "+0000" against a LOCAL wall-clock string silently
    mislabels the timestamp and throws the parsed epoch off by the offset."""
    return _date("-d", f"@{epoch}", "+%z")


STUB_MARVINCTL = """#!/usr/bin/env bash
set -u
shift 2  # drop "--tenant" "weewx"
verb="$1"; shift
S="$SCEN_DIR"
case "$verb" in
  inspect) cat "$S/inspect.json" ;;
  check-image)
    [ -f "$S/check_image_missing" ] && exit 1
    cat "$S/check_image_id.txt" ;;
  logs) cat "$S/container_logs.txt" ;;
  cat)
    f="$S/logs/$(basename "$1")"
    if [ -f "$f" ]; then cat "$f"
    else echo "marvinctl-remote: path '$1' does not exist" >&2; exit 1; fi ;;
  grep)
    f="$S/logs/$(basename "$2")"
    [ -f "$f" ] || exit 1
    grep -E "$1" "$f" ;;
  unit) cat "$S/unit.txt" ;;
  stat)
    f="$S/stat_$(basename "$1").txt"
    [ -f "$f" ] && cat "$f" || exit 1 ;;
  proc) cat "$S/meminfo.txt" ;;
  exec-ro) cat "$S/phantom.txt" ;;
  *) echo "stub marvinctl: unhandled verb $verb" >&2; exit 2 ;;
esac
"""


def build_scenario(
    tmp_path: Path,
    *,
    state: str = "running",
    image: str = "weatheredscientist/weewx-rtldavis:marvin-live",
    image_id: str = "sha256:aaaa",
    check_image_id: str | None = "sha256:aaaa",  # None => check-image "fails"
    restarts: str = "0",
    started_epoch: int | None = None,
    started_ago_s: int = 3600,
    record_age_s: int = 55,
    mon_log_mtime_offset_s: int = 18,  # negative => a FUTURE mtime (clock skew)
    mon_log_missing: bool = False,
    mon_active: bool = True,
    extra_restart_offsets_s: tuple[int, ...] = (),
    banner_in_today: bool = True,
    banner_in_yesterday: bool = False,
    drv_ver: str = "0.20+ws.5",
    qc_ok: bool = True,
    hraw_on: bool = True,
    hraw_n: int = 3,
    stalls: int = 0,
    tracebacks: int = 0,
    published: int = 1,
    influx: int = 1,
    window_pct: str | None = "76",
    rx_line: bool = True,
    rx_avg: str = "76",
    rx_verdict: str = "OK",
    mon_resets: int = 7,
    mon_reset_bad: int = 0,
    db_bytes: int = 35241984,
    mem_total_kb: int = 3866684,
    db_stat_missing: bool = False,
    meminfo_missing: bool = False,
    phantom_rain: int = 0,
    archive_rows: int = 64,
) -> Path:
    """A fully healthy scenario by default; each keyword isolates one check."""
    n = now_epoch()
    start = started_epoch if started_epoch is not None else n - started_ago_s

    scen = tmp_path / "scenario"
    logs = scen / "logs"
    logs.mkdir(parents=True)

    inspect = [{
        "State": {"Status": state, "StartedAt": _iso_utc(start)},
        "Config": {"Image": image},
        "Image": image_id,
        "RestartCount": restarts,
    }]
    (scen / "inspect.json").write_text(json.dumps(inspect))

    if check_image_id is not None:
        (scen / "check_image_id.txt").write_text(check_image_id + "\n")
    else:
        (scen / "check_image_missing").write_text("")

    (scen / "container_logs.txt").write_text("Starting weewx...\n")

    lines = [
        f"{_local(n - record_age_s)},000 weewx.manager INFO Added record x "
        "to database 'weewx.sdb'",
        f"{_local(n - 30)},000 user.rtldavis INFO driver version is {drv_ver} (fork)",
    ]
    if banner_in_today:
        lines.append(f"{_local(n - 30)},000 weewxd INFO Initializing weewxd version 5.5.0")
    if qc_ok:
        lines.append(f"{_local(n - 30)},000 user.rtldavis INFO sensor_qc True")
    if hraw_on:
        lines.append(f"{_local(n - 30)},000 user.rtldavis INFO log_humidity_raw True")
    lines += [f"{_local(n - 30)},000 user.rtldavis INFO humidity_raw=0x12"] * hraw_n
    lines += ["2026-01-01 00:00:00,000 weewxd CRITICAL Caught WeeWxIOError: "
              "rtldavis process stalled"] * stalls
    lines += ["Traceback (most recent call last):"] * tracebacks
    lines += [f"{_local(n - 30)},000 weewx.restx INFO Uploader: Published record x"] * published
    lines += [f"{_local(n - 30)},000 weewx.restx INFO Influx: wrote"] * influx
    for off in extra_restart_offsets_s:
        lines.append(f"{_local(n - off)},000 weewxd INFO Initializing weewxd version 5.5.0")
    (logs / "weewx.log").write_text("\n".join(lines) + "\n")

    if banner_in_yesterday:
        y = [f"{_local(start)},000 weewxd INFO Initializing weewxd version 5.5.0"]
        yesterday = _date("-d", "yesterday", "+%Y-%m-%d")
        (logs / f"weewx.log.{yesterday}").write_text("\n".join(y) + "\n")

    ml = []
    if window_pct is not None:
        ml.append(f"{_local(n - 30)} WINDOW: 16/21 ({window_pct}%)")
    if rx_line:
        ml.append(f"{_local(n - 30)} RECEPTION: {rx_avg}% avg over last 5 "
                  f"windows [{rx_verdict}] (bad windows: 1)")
    ml += [f"{_local(n - 30)} RESET: running"] * mon_resets
    ml += [f"{_local(n - 30)} RESET ineffective"] * mon_reset_bad
    (logs / "weewx_monitor.log").write_text("\n".join(ml) + "\n")
    (logs / "weewx_monitor.log.1").write_text("")

    if not mon_log_missing:
        mtime = n - mon_log_mtime_offset_s
        (scen / "stat_weewx_monitor.log.txt").write_text(
            f"  File: x\n  Size: 100\n"
            f"Modify: {_local(mtime)}.000000000 {_local_offset(mtime)}\n")

    (scen / "unit.txt").write_text(
        "Active: active (running) since x\n" if mon_active else "Active: inactive (dead)\n")

    if not meminfo_missing:
        (scen / "meminfo.txt").write_text(f"MemTotal:       {mem_total_kb} kB\n")
    if not db_stat_missing:
        (scen / "stat_weewx.sdb.txt").write_text(f"  File: x\n  Size: {db_bytes}  \tBlocks: 1\n")

    (scen / "phantom.txt").write_text(f"phantom_rain={phantom_rain}\narchive_rows={archive_rows}\n")
    return scen


def run_soak(tmp_path: Path, expect_image: str = "weatheredscientist/weewx-rtldavis:v2.0.16",
            **overrides) -> str:
    scen = build_scenario(tmp_path, **overrides)

    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "marvinctl"
    stub.write_text(STUB_MARVINCTL)
    stub.chmod(0o755)

    home = tmp_path / "home"
    home.mkdir(exist_ok=True)

    env = dict(DATE_ENV)
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    env["HOME"] = str(home)
    env["SCEN_DIR"] = str(scen)
    env["EXPECT_IMAGE"] = expect_image
    env["EXPECT_DRIVER"] = overrides.get("drv_ver", "0.20+ws.5")

    return subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=60
    ).stdout


def line_for(out: str, needle: str) -> str:
    return next((ln for ln in out.splitlines() if needle in ln), "")


# --- the S87 regression: a negative age is not a wedge -----------------------


def test_negative_monitor_age_is_not_reported_as_wedged(tmp_path):
    out = run_soak(tmp_path, mon_log_mtime_offset_s=-82)
    assert "MONITOR LOG STALE" not in out
    assert "wedged" not in out
    assert "clock skew" in line_for(out, "future")


def test_stale_monitor_log_still_fails(tmp_path):
    """POSITIVE CONTROL for the test above."""
    out = run_soak(tmp_path, mon_log_mtime_offset_s=900)
    assert "MONITOR LOG STALE" in out
    assert "wedged" in out


def test_missing_monitor_log_is_distinct_from_wedged(tmp_path):
    out = run_soak(tmp_path, mon_log_missing=True)
    assert "MONITOR LOG MISSING" in out
    assert "MONITOR LOG STALE" not in out


def test_dead_monitor_still_fails(tmp_path):
    out = run_soak(tmp_path, mon_active=False)
    assert "MONITOR/WATCHDOG DEAD" in out


def test_healthy_monitor_passes(tmp_path):
    out = run_soak(tmp_path)
    assert "monitor/watchdog alive" in out
    assert "MONITOR" not in line_for(out, "monitor/watchdog alive").upper().replace(
        "MONITOR/WATCHDOG ALIVE", ""
    )


# --- ages must never be measured against a stale clock (the S87 root cause) --


def test_ages_are_measured_against_a_fresh_clock():
    """Guards the actual defect, not just its symptom: record_age_s and
    mon_log_age must each read the clock at the point of measurement, not
    some earlier captured value."""
    src = SCRIPT.read_text()
    for key in ("record_age_s", "mon_log_age"):
        line = next(ln for ln in src.splitlines() if ln.strip().startswith(f"{key}="))
        assert "$DATECMD +%s" in line, f"{key} must read a fresh clock, got: {line.strip()}"
        assert "now_epoch" not in line, (
            f"{key} is measured against the stale top-of-script now_epoch: {line.strip()}"
        )


# --- the image-identity canary (ops#287's own finding) ------------------------


def test_image_identity_matches_by_id_not_tag_string(tmp_path):
    """marvin runs containers under a local alias tag ("marvin-live"), never
    the versioned tag EXPECT_IMAGE names -- a string compare would fail
    forever on a healthy station. The check must compare image IDs instead.
    """
    out = run_soak(tmp_path, image="weatheredscientist/weewx-rtldavis:marvin-live",
                   image_id="sha256:same", check_image_id="sha256:same")
    assert "image is the expected build" in out
    assert "IMAGE MISMATCH" not in out


def test_image_mismatch_still_fails(tmp_path):
    """POSITIVE CONTROL: a genuinely different running image is still caught."""
    out = run_soak(tmp_path, image_id="sha256:running", check_image_id="sha256:expected")
    assert "IMAGE MISMATCH" in out


def test_unresolvable_expect_image_warns_instead_of_lying(tmp_path):
    out = run_soak(tmp_path, check_image_id=None)
    assert "cannot resolve EXPECT_IMAGE locally" in out
    assert "IMAGE MISMATCH" not in out


# --- the restart-loop detector (S95, #245) ------------------------------------


def test_single_boot_is_not_a_restart_loop(tmp_path):
    out = run_soak(tmp_path)
    assert "no weewxd restart loop" in out


def test_tight_restarts_are_a_restart_loop(tmp_path):
    """POSITIVE CONTROL: the 2026-08-06 signature — several starts minutes apart."""
    out = run_soak(tmp_path, extra_restart_offsets_s=(300, 600, 900))
    assert "WEEWXD RESTART LOOP" in out


def test_scheduled_swap_spacing_is_not_a_loop(tmp_path):
    """Two starts ~hours apart (an attended deploy, or a campaign swap) must
    not be confused with the tight-spaced crash-loop signature."""
    out = run_soak(tmp_path, extra_restart_offsets_s=(5000,))
    assert "no weewxd restart loop" in out


# --- reception: the monitor's own verdict, not a second threshold ------------


def test_baseline_reception_does_not_warn(tmp_path):
    out = run_soak(tmp_path, rx_avg="76", rx_verdict="OK")
    assert "PASS" in line_for(out, "reception")


def test_low_reception_still_warns(tmp_path):
    out = run_soak(tmp_path, rx_avg="41", rx_verdict="LOW")
    assert "reception LOW per monitor" in out
    assert "41%" in out


def test_missing_reception_verdict_falls_back_to_raw_window(tmp_path):
    out = run_soak(tmp_path, rx_line=False, window_pct="76")
    assert "no monitor reception verdict yet" in out
    assert "76%" in out


# --- the freeze detector must keep its teeth ---------------------------------


def test_archive_stall_still_fails(tmp_path):
    out = run_soak(tmp_path, record_age_s=400)
    assert "ARCHIVE STALLED" in out


def test_fresh_archive_record_passes(tmp_path):
    out = run_soak(tmp_path, record_age_s=55)
    assert "archive records still arriving" in out
    assert "ARCHIVE STALLED" not in out


# --- DEC-0095's retention tripwire: accept-and-monitor that actually executes -


def test_todays_archive_is_within_budget(tmp_path):
    out = run_soak(tmp_path, db_bytes=35241984, mem_total_kb=3866684)
    line = line_for(out, "retention budget")
    assert "archive within retention budget" in line
    assert "0.9% of RAM" in line


def test_archive_over_ten_percent_of_ram_trips(tmp_path):
    """POSITIVE CONTROL: 400 MB against 3.69 GiB is 10.6% — just over."""
    out = run_soak(tmp_path, db_bytes=400 * 1024 * 1024, mem_total_kb=3866684)
    assert "ARCHIVE OVER RETENTION BUDGET" in out
    assert "DEC-0095" in out


def test_tripwire_says_so_when_it_cannot_measure(tmp_path):
    out = run_soak(tmp_path, db_stat_missing=True)
    assert "retention tripwire unmeasured" in out
    assert "unmonitored" in out


# --- #252: windowing must survive a midnight rotation, now via a real cat ----


def test_window_spans_midnight_into_yesterdays_rotated_log(tmp_path):
    """Container start at 23:50 predates midnight, so the startup banner
    lives only in yesterday's rotated file -- the default window ("since
    container start") must still find it there.
    """
    t0 = int(_date("-d", "yesterday 23:50:00", "+%s"))
    out = run_soak(tmp_path, started_epoch=t0, banner_in_today=False,
                   banner_in_yesterday=True, record_age_s=30)
    assert "PASS" in line_for(out, "startup banner")


def test_window_still_reports_no_banner_when_truly_absent(tmp_path):
    """POSITIVE CONTROL: with no banner in either file, the fix above must
    not have started reporting one unconditionally."""
    t0 = int(_date("-d", "yesterday 23:50:00", "+%s"))
    out = run_soak(tmp_path, started_epoch=t0, banner_in_today=False,
                   banner_in_yesterday=False, record_age_s=30)
    assert "no startup banner in window" in out
