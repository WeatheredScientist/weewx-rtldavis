"""Offline tests for ops/nas_build.py -- weewx's NAS-LEASE holder wrapper
(NAS-LEASE.md v1.4, DEC-0108).

This wraps a CROSS-TENANT courtesy protocol: a bug here doesn't just break
weewx's own build, it can strand or misattribute another tenant's read of
a shared lease file. The tests below pin the specific hazards the spec
calls out by name -- explicit fchmod against a hostile umask (v1.4's own
production near-miss), validity being flock-OR-unexpired rather than
either alone, and a stale break only ever firing when BOTH conditions
hold.

flock() is real POSIX and works the same on macOS as on the NAS's
Linux/btrfs, so these tests exercise the real locking primitive against a
tmp_path lease dir rather than mocking it.

Run:  python3 -m pytest tests/test_nas_build.py
"""
import fcntl
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ops"))
import nas_build as nb  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_lease_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(nb, "LEASE_DIR", str(tmp_path))
    return tmp_path


def _read_log_events(tmp_path):
    log_path = tmp_path / "heavy-io.log"
    if not log_path.exists():
        return []
    return [json.loads(line) for line in log_path.read_text().splitlines()]


def _write_foreign_lease(tmp_path, expires_at, tenant="coffee-radar",
                         job="stage-d-full-sweep"):
    body = {
        "schema": 1, "tenant": tenant, "job": job,
        "acquired_at": "2026-08-20T01:00:00Z",
        "expires_at": expires_at, "renewal_floor_s": 300,
    }
    path = tmp_path / "heavy-io.lease"
    path.write_text(json.dumps(body))
    return path


FAR_FUTURE = "2099-01-01T00:00:00Z"
FAR_PAST = "2020-01-01T00:00:00Z"


# ── acquire() ───────────────────────────────────────────────────────────

def test_acquire_creates_lease_with_correct_fields(tmp_path):
    fd = nb.acquire("nas-image-build", ttl_s=3600, renewal_floor_s=600)
    try:
        body = json.loads((tmp_path / "heavy-io.lease").read_text())
        assert body["schema"] == 1
        assert body["tenant"] == "weewx-rtldavis"
        assert body["job"] == "nas-image-build"
        assert body["renewal_floor_s"] == 600
        assert body["acquired_at"] < body["expires_at"]
    finally:
        nb.release(fd, "nas-image-build", "clean")


def test_acquire_sets_mode_0644_regardless_of_umask(tmp_path):
    """The regression this pins (NAS-LEASE.md Section 3, v1.4): a shell
    redirect or language default takes 0666 & ~umask, so a restrictive
    holder-side umask silently creates an unreadable lease -- every other
    tenant's probe then hits EACCES, read by Section 3 as "couldn't tell",
    never "free", which silently disables the downshift half for the
    whole hold. Explicit fchmod must win regardless of umask."""
    old_umask = os.umask(0o077)
    try:
        fd = nb.acquire("nas-image-build")
    finally:
        os.umask(old_umask)
    try:
        mode = os.stat(tmp_path / "heavy-io.lease").st_mode & 0o777
        assert mode == 0o644, "got %o -- umask leaked through fchmod" % mode
    finally:
        nb.release(fd, "nas-image-build", "clean")


def test_acquire_holds_a_real_exclusive_flock(tmp_path):
    fd = nb.acquire("nas-image-build")
    try:
        probe_fd = os.open(tmp_path / "heavy-io.lease", os.O_RDONLY)
        try:
            with pytest.raises(OSError):
                fcntl.flock(probe_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(probe_fd)
    finally:
        nb.release(fd, "nas-image-build", "clean")


def test_acquire_logs_the_acquired_event(tmp_path):
    fd = nb.acquire("nas-image-build")
    try:
        events = _read_log_events(tmp_path)
        assert len(events) == 1
        assert events[0]["event"] == "acquired"
        assert events[0]["tenant"] == "weewx-rtldavis"
        assert events[0]["job"] == "nas-image-build"
    finally:
        nb.release(fd, "nas-image-build", "clean")


def test_acquire_defers_on_a_valid_unexpired_foreign_lease(tmp_path):
    _write_foreign_lease(tmp_path, FAR_FUTURE)
    with pytest.raises(nb.Deferred):
        nb.acquire("nas-image-build")
    # deferring must not touch the foreign lease at all
    assert (tmp_path / "heavy-io.lease").exists()
    assert _read_log_events(tmp_path) == []


def test_acquire_breaks_a_stale_expired_unflocked_foreign_lease(tmp_path):
    """Section 3: stale iff flock is free AND expires_at has passed.
    Nobody holds a flock on this file in this test -- it's just sitting
    there, unexpired timestamp aside -- so both conditions hold."""
    _write_foreign_lease(tmp_path, FAR_PAST, tenant="coffee-radar",
                         job="stage-d-full-sweep")
    fd = nb.acquire("nas-image-build")
    try:
        body = json.loads((tmp_path / "heavy-io.lease").read_text())
        assert body["tenant"] == "weewx-rtldavis"  # the stale one is gone

        events = _read_log_events(tmp_path)
        assert [e["event"] for e in events] == ["broken", "acquired"]
        assert events[0]["broke_tenant"] == "coffee-radar"
        assert events[0]["broke_job"] == "stage-d-full-sweep"
    finally:
        nb.release(fd, "nas-image-build", "clean")


def test_acquire_does_not_break_an_expired_but_still_flocked_lease(tmp_path):
    """The regression this pins: validity is flock-held OR unexpired, not
    "unexpired" alone -- a holder alive but past its own declared TTL
    (wedged, or just slow) must not be broken out from under it."""
    _write_foreign_lease(tmp_path, FAR_PAST)
    holder_fd = os.open(tmp_path / "heavy-io.lease", os.O_RDONLY)
    fcntl.flock(holder_fd, fcntl.LOCK_EX)
    try:
        with pytest.raises(nb.Deferred):
            nb.acquire("nas-image-build")
        assert (tmp_path / "heavy-io.lease").exists()
        assert _read_log_events(tmp_path) == []
    finally:
        fcntl.flock(holder_fd, fcntl.LOCK_UN)
        os.close(holder_fd)


def test_acquire_treats_a_torn_lease_as_couldnt_tell_not_free(tmp_path):
    (tmp_path / "heavy-io.lease").write_text("{not valid json")
    with pytest.raises(nb.Deferred):
        nb.acquire("nas-image-build")
    assert (tmp_path / "heavy-io.lease").exists()  # not broken on a guess


# ── release() ───────────────────────────────────────────────────────────

def test_release_removes_lease_and_logs_outcome(tmp_path):
    fd = nb.acquire("nas-image-build")
    nb.release(fd, "nas-image-build", "clean")
    assert not (tmp_path / "heavy-io.lease").exists()
    events = _read_log_events(tmp_path)
    assert events[-1] == {
        "ts": events[-1]["ts"], "event": "released",
        "tenant": "weewx-rtldavis", "job": "nas-image-build",
        "outcome": "clean",
    }


def test_release_survives_the_lease_already_being_gone(tmp_path):
    fd = nb.acquire("nas-image-build")
    os.remove(tmp_path / "heavy-io.lease")  # simulate an out-of-band break
    nb.release(fd, "nas-image-build", "clean")  # must not raise
    events = _read_log_events(tmp_path)
    assert events[-1]["event"] == "released"


# ── run_under_lease() ───────────────────────────────────────────────────

def test_run_under_lease_happy_path(tmp_path):
    log_path = str(tmp_path / "build.log")
    rc = nb.run_under_lease("nas-image-build",
                            [sys.executable, "-c", "print('hello')"],
                            log_path=log_path)
    assert rc == 0
    assert not (tmp_path / "heavy-io.lease").exists()
    log_text = open(log_path).read()
    assert "hello" in log_text
    assert "BUILD-EXIT:0" in log_text
    events = _read_log_events(tmp_path)
    assert [e["event"] for e in events] == ["acquired", "released"]
    assert events[-1]["outcome"] == "clean"


def test_run_under_lease_reports_the_real_exit_code_not_a_pipeline_code(tmp_path):
    """The reason this wrapper reads returncode off subprocess.Popen
    directly instead of a shell pipeline: `cmd | tee log; echo $?` would
    report tee's exit code, not the wrapped command's."""
    log_path = str(tmp_path / "build.log")
    rc = nb.run_under_lease(
        "nas-image-build",
        [sys.executable, "-c", "import sys; sys.exit(3)"],
        log_path=log_path)
    assert rc == 3
    assert "BUILD-EXIT:3" in open(log_path).read()
    events = _read_log_events(tmp_path)
    assert events[-1]["event"] == "released"
    assert events[-1]["outcome"] == "build-failed"


def test_run_under_lease_still_releases_when_the_command_cannot_start(tmp_path):
    """A crash before the subprocess ever reports an exit code must still
    release and log truthfully, not abandon the lease until TTL expiry."""
    log_path = str(tmp_path / "build.log")
    with pytest.raises(OSError):
        nb.run_under_lease("nas-image-build",
                           ["/no/such/binary/here"], log_path=log_path)
    assert not (tmp_path / "heavy-io.lease").exists()
    events = _read_log_events(tmp_path)
    assert events[-1]["event"] == "released"
    assert events[-1]["outcome"] == "crashed"


def test_run_under_lease_defers_without_running_the_command(tmp_path):
    """The command must never execute at all when a valid foreign lease
    blocks acquisition -- proven here via a command whose only effect is
    creating a marker file."""
    _write_foreign_lease(tmp_path, FAR_FUTURE)
    marker = tmp_path / "should-not-exist"
    with pytest.raises(nb.Deferred):
        nb.run_under_lease(
            "nas-image-build",
            [sys.executable, "-c",
             "open(%r, 'w').close()" % str(marker)])
    assert not marker.exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
