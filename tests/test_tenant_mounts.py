"""Offline tests for ops/tenant_mounts.py — the ops#288 restore-list deriver.

The tool's whole value rests on two things staying correct: parsing every
`-v SRC:DST[:MODE]` out of a unit's (possibly backslash-continued, possibly
multi-ExecStart=) file text, and classifying each SRC against THIS repo's own
git tree (TRACKED / IGNORED / UNDOCUMENTED). `classify()` is deliberately
tested against real paths in this checkout rather than a stubbed git, the same
way stall_baseline.py's tests use real measured timestamps — the git tree
itself is the fixture, and a path's classification changing unexpectedly
(e.g. `.gitignore` losing a pattern) is exactly the kind of drift these tests
should catch.

Run:  .venv/bin/python -m pytest tests/test_tenant_mounts.py
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ops"))
import tenant_mounts as tm  # noqa: E402


# --- _join_execstart --------------------------------------------------------

def test_join_execstart_handles_backslash_continuation() -> None:
    """weewx-influxdb.service's real shape: one ExecStart=, six continuation
    lines."""
    text = (
        "[Unit]\n"
        "Description=x\n"
        "[Service]\n"
        "ExecStart=/usr/bin/docker run --rm --name weewx-influxdb \\\n"
        "    --user 996:986 \\\n"
        "    -v /srv/docker/weewx/influxdb/data:/var/lib/influxdb2 \\\n"
        "    influxdb:2.7.12\n"
    )
    joined = tm._join_execstart(text)
    assert joined.count("ExecStart=") == 1
    assert "-v /srv/docker/weewx/influxdb/data:/var/lib/influxdb2" in joined
    assert "\\" not in joined


def test_join_execstart_handles_multiple_execstart_blocks() -> None:
    """weewx-rx-experiment.service's real shape: two separate ExecStart=
    lines (tick, guard), neither continued -- both must survive, not just the
    first."""
    text = (
        "[Service]\n"
        "ExecStart=/srv/docker/weewx/rx_experiment.sh tick\n"
        "ExecStart=/srv/docker/weewx/rx_experiment.sh guard\n"
    )
    joined = tm._join_execstart(text)
    assert "tick" in joined
    assert "guard" in joined
    assert joined.count("ExecStart=") == 2


def test_join_execstart_ignores_non_execstart_lines() -> None:
    text = (
        "# a comment mentioning ExecStart= in prose, not a directive\n"
        "Description=weewx-influxdb consistent pre-backup dump\n"
        "ExecStart=/usr/bin/docker exec weewx-influxdb influx backup /x\n"
    )
    joined = tm._join_execstart(text)
    assert joined.count("ExecStart=") == 1
    assert "docker exec" in joined


# --- parse_mounts ------------------------------------------------------------

def test_parse_mounts_extracts_src_dst_mode() -> None:
    line = ("ExecStart=/usr/bin/docker run --rm -v /srv/docker/weewx/logs:/var/log/weewx "
            "-v /srv/docker/weewx/influx.py:/opt/x/influx.py:ro image:tag")
    mounts = tm.parse_mounts(line)
    assert mounts == [
        ("/srv/docker/weewx/logs", "/var/log/weewx", "rw"),
        ("/srv/docker/weewx/influx.py", "/opt/x/influx.py", "ro"),
    ]


def test_parse_mounts_empty_when_no_dash_v() -> None:
    line = "ExecStart=/usr/bin/docker exec weewx-influxdb influx backup /x"
    assert tm.parse_mounts(line) == []


def test_parse_mounts_ignores_non_bind_flags() -> None:
    """`--mount type=tmpfs,...` and `-p host:container` must not be mistaken
    for `-v` bind mounts -- eh-proxy.service's real ExecStart carries both."""
    line = ("ExecStart=/usr/bin/docker run -p 8389:8389 "
            "--mount type=tmpfs,destination=/app/secrets,readonly "
            "-v /srv/docker/dashboard:/app:ro image:tag")
    mounts = tm.parse_mounts(line)
    assert mounts == [("/srv/docker/dashboard", "/app", "ro")]


# --- classify — against this repo's OWN real git tree -----------------------

def test_classify_tracked_file() -> None:
    assert tm.classify(f"{tm.TENANT_ROOT}/influx.py") == "TRACKED"


def test_classify_tracked_file_loop_json_writer() -> None:
    assert tm.classify(f"{tm.TENANT_ROOT}/loop_json_writer.py") == "TRACKED"


def test_classify_ignored_directory_weewx_data() -> None:
    assert tm.classify(f"{tm.TENANT_ROOT}/weewx-data") == "IGNORED (known data)"


def test_classify_ignored_directory_logs() -> None:
    assert tm.classify(f"{tm.TENANT_ROOT}/logs") == "IGNORED (known data)"


def test_classify_ignored_vendored_dependency() -> None:
    """sortedcontainers/ is a real .gitignore entry (line 54) -- deliberately
    excluded, same class as weewx-data/logs, not an oversight."""
    assert tm.classify(f"{tm.TENANT_ROOT}/sortedcontainers") == "IGNORED (known data)"


def test_classify_undocumented_matches_dec0151_shape() -> None:
    """The exact DEC-0151 failure: influxdb/ is neither tracked nor ignored --
    nobody told git, so nobody told the old hand-maintained restore list
    either. This is the case the tool exists to surface."""
    assert tm.classify(f"{tm.TENANT_ROOT}/influxdb/data") == "UNDOCUMENTED"
    assert tm.classify(f"{tm.TENANT_ROOT}/influxdb/config") == "UNDOCUMENTED"


def test_classify_undocumented_for_unknown_path() -> None:
    assert tm.classify(f"{tm.TENANT_ROOT}/no-such-thing-here") == "UNDOCUMENTED"


def test_classify_not_applicable_outside_tenant_root() -> None:
    """A path outside /srv/docker/weewx (e.g. a cross-tenant mount source
    accidentally passed in) must never be silently classified as this repo's
    own concern."""
    assert tm.classify("/srv/docker/dashboard/secrets/proxy.env") == "N/A"
    assert tm.classify("/etc/passwd") == "N/A"


# --- the unit lists themselves, sanity-pinned --------------------------------

def test_own_units_names_weewx_service() -> None:
    """A silent edit dropping weewx.service from OWN_UNITS would make the
    tool report a clean restore list while checking nothing real."""
    assert "weewx.service" in tm.OWN_UNITS
    assert "weewx-influxdb.service" in tm.OWN_UNITS


def test_external_units_is_never_empty_by_accident() -> None:
    """Both known cross-tenant consumers (eh-proxy, hlf-api) stay listed --
    an empty EXTERNAL_UNITS reads as 'no dependents' silently, which is a
    much worse failure than a stale name."""
    assert "eh-proxy.service" in tm.EXTERNAL_UNITS
    assert "hlf-api.service" in tm.EXTERNAL_UNITS
