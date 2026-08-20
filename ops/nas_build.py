#!/usr/bin/env python3
"""ops/nas_build.py -- NAS-LEASE holder wrapper for weewx's rare heavy NAS
jobs: the NAS-native image build, and manual bulk historical analysis --
weewx's two named holder cases (NAS-LEASE.md Section 6).

weewx is a NON-RENEWING holder (Section 5, v1.4): a bare `docker build` --
or an analysis pass -- is one invocation with no natural mid-job
checkpoint, so this wraps acquire -> run -> release around it as a single
unit and never renews. renewal_floor_s is declared as the whole job's
expected duration, per Section 5's non-renewing-holder rule.

Usage:
    python3 ops/nas_build.py --job nas-image-build -- \\
        docker build -t weatheredscientist/weewx-rtldavis:v2.0.14 .

RENEWAL_FLOOR_S/TTL_S below are PROVISIONAL (DEC-0078's ~10 min v2.0.12
build) -- re-pin both against the real ~08-23 v2.0.14 build's measured
duration once it has actually run under this wrapper (DEC-0108).

Deliberately NOT built here (DEC-0108): the observer/downshift side
(Section 3's read protocol, checking OTHER tenants' leases) -- weewx has
no live downshift lever yet (the InfluxDB post_interval deferral needs
container access this host-side client doesn't have, Section 6), so a
courtesy check with nothing to act on has unclear benefit. This wrapper
only ever WRITES its own acquire/release events to the log; it never
reads anyone else's lease to decide its own behavior.

Lease mechanics are NAS-LEASE.md v1.4 (eaglehunt-ops, OPS-DEC-0110):
  - acquire: O_CREAT|O_EXCL, explicit fchmod 0644 (v1.4 -- don't trust
    umask), flock exclusive held for the job's duration.
  - stale foreign lease: broken (logged, named) iff flock is free AND
    expires_at has passed; otherwise this run DEFERS -- Section 6 designs
    weewx courtesy-first, so this wrapper never proceeds un-announced.
  - release: remove the lease file, log `released` with a truthful
    outcome; wrapped in try/finally so a crash still releases and logs
    rather than abandoning the file to sit until TTL expiry.
  - attribution log: append-only JSONL, its own brief O_APPEND flock,
    independent of the lease file's own lock.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

LEASE_DIR = "/volume1/docker/nas-lease/"
TENANT = "weewx-rtldavis"

# Provisional -- DEC-0078's ~10 min v2.0.12 NAS build. Re-pin both against
# the real ~08-23 v2.0.14 build's measured duration (DEC-0108).
RENEWAL_FLOOR_S = 600
TTL_S = 3600


class Deferred(Exception):
    """A valid foreign lease is held. Section 6 designs weewx courtesy-
    first: this wrapper never proceeds un-announced, so it defers instead."""


def _ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _lease_path():
    return os.path.join(LEASE_DIR, "heavy-io.lease")


def _log_path():
    return os.path.join(LEASE_DIR, "heavy-io.log")


def append_log_event(event):
    """Section 4: append-only JSONL, brief exclusive flock, O_APPEND.
    Kept world-writable (0666, v1.4) -- every tenant appends here."""
    fd = os.open(_log_path(), os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o666)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, (json.dumps(event) + "\n").encode())
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _read_lease(path):
    """None on ANY read/parse/shape problem -- Section 3's "couldn't tell",
    never treated as free. A torn write only ever tears the JSON body
    here; the file is written once by weewx's own non-renewing holder, or
    by another tenant under their own spec-compliant client."""
    try:
        with open(path, "rb") as f:
            lease = json.loads(f.read().decode())
        lease["expires_at"]
        return lease
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _probe_flock_free(path):
    """Section 3's non-blocking shared-flock probe. True = nobody holds an
    exclusive lock right now. Always releases what it took -- a probe,
    not a hold."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return True  # file vanished between the exists-check and here
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return True
    except OSError:
        return False
    finally:
        os.close(fd)


def _is_expired(lease, now):
    expires_at = datetime.strptime(lease["expires_at"], "%Y-%m-%dT%H:%M:%SZ")
    return expires_at.replace(tzinfo=timezone.utc) < now


def acquire(job_name, ttl_s=None, renewal_floor_s=None):
    """Returns an open fd holding an exclusive flock on a freshly-created
    lease file. Breaks a stale foreign lease first if one is found
    (Section 3), logging it as `broken`. Raises Deferred if a VALID
    foreign lease is held, or if an existing lease can't be read at all
    (couldn't-tell leans toward not breaking it)."""
    if ttl_s is None:
        ttl_s = TTL_S
    if renewal_floor_s is None:
        renewal_floor_s = RENEWAL_FLOOR_S
    path = _lease_path()
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            existing = _read_lease(path)
            if existing is not None and _probe_flock_free(path) and \
                    _is_expired(existing, datetime.now(timezone.utc)):
                append_log_event({
                    "ts": _ts(datetime.now(timezone.utc)),
                    "event": "broken",
                    "tenant": TENANT,
                    "job": job_name,
                    "broke_tenant": existing.get("tenant", "unknown"),
                    "broke_job": existing.get("job", "unknown"),
                })
                os.remove(path)
                continue  # retry the create against the now-clear slot
            raise Deferred(
                "a valid lease is held (or unreadable, couldn't-tell) -- "
                "deferring, per NAS-LEASE.md Section 6's courtesy-first "
                "design. Lease seen: %r" % existing)
        else:
            break

    try:
        os.fchmod(fd, 0o644)  # v1.4: explicit, never trust umask
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        now = datetime.now(timezone.utc)
        body = {
            "schema": 1,
            "tenant": TENANT,
            "job": job_name,
            "acquired_at": _ts(now),
            "expires_at": _ts(now + timedelta(seconds=ttl_s)),
            "renewal_floor_s": renewal_floor_s,
        }
        os.write(fd, json.dumps(body).encode())
        append_log_event({"ts": _ts(now), "event": "acquired",
                          "tenant": TENANT, "job": job_name,
                          "expires_at": body["expires_at"]})
    except BaseException:
        os.close(fd)
        raise
    return fd


def release(fd, job_name, outcome):
    """Section 3: remove the lease file, log `released`. Both happen
    regardless of outcome -- an honest failure record is the log's whole
    point (Section 4), not something to hide by skipping the release."""
    try:
        os.remove(_lease_path())
    except OSError:
        pass  # already gone -- broken by someone else, or a double-release
    append_log_event({
        "ts": _ts(datetime.now(timezone.utc)),
        "event": "released", "tenant": TENANT, "job": job_name,
        "outcome": outcome,
    })
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


def run_under_lease(job_name, cmd, log_path="build.log",
                    ttl_s=None, renewal_floor_s=None):
    """Acquire, run cmd teeing its output to log_path plus the existing
    BUILD-EXIT marker convention (CONSTANTS.md: verify by that marker,
    never a pipeline exit code -- subprocess.Popen's own returncode is
    the real one, no shell pipe involved), release, return cmd's exit
    code. `outcome` starts pessimistic and is only upgraded once the
    subprocess has actually completed, so any exception before that
    point -- including one from Popen itself -- releases as "crashed"
    rather than silently skipping the release."""
    fd = acquire(job_name, ttl_s=ttl_s, renewal_floor_s=renewal_floor_s)
    outcome = "crashed"
    returncode = None
    try:
        with open(log_path, "ab") as logf:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            for line in proc.stdout:
                sys.stdout.buffer.write(line)
                logf.write(line)
            proc.wait()
            returncode = proc.returncode
            logf.write(("BUILD-EXIT:%d\n" % returncode).encode())
        outcome = "clean" if returncode == 0 else "build-failed"
        return returncode
    finally:
        release(fd, job_name, outcome)


def main():
    ap = argparse.ArgumentParser(
        description="Run a command as a NAS-LEASE holder -- weewx's rare "
                    "heavy NAS jobs (image build, bulk historical "
                    "analysis).")
    ap.add_argument("--job", required=True,
                    help="job name for the lease/log, e.g. nas-image-build")
    ap.add_argument("--log", default="build.log",
                    help="path to tee the command's output + BUILD-EXIT "
                         "marker (default: build.log in cwd)")
    ap.add_argument("--ttl", type=int, default=None,
                    help="lease TTL in seconds (default: the provisional "
                         "TTL_S constant)")
    ap.add_argument("--floor", type=int, default=None,
                    help="declared renewal_floor_s -- expected whole-job "
                         "duration for this non-renewing holder shape "
                         "(default: the provisional RENEWAL_FLOOR_S "
                         "constant)")
    ap.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="the command to run under the lease, e.g. "
                         "-- docker build -t ... .")
    args = ap.parse_args()
    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        ap.error("no command given -- pass it after --")

    try:
        return run_under_lease(args.job, cmd, log_path=args.log,
                               ttl_s=args.ttl, renewal_floor_s=args.floor)
    except Deferred as e:
        print("DEFERRED: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
