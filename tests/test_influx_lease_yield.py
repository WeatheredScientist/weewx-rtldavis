"""NAS-LEASE courtesy yield in influx.py (S99, DEC-0111).

DEC-0099/DEC-0104 designed this and deliberately left it unbuilt (DEC-0108
scoped ops/nas_build.py to the holder side only). This tests the observer
side: while another tenant's lease is held and unexpired, InfluxThread's
post_interval should rise to LEASE_YIELD_POST_INTERVAL_S; otherwise it should
sit at whatever value weewx.conf configured. Off entirely unless lease_dir is
set (schema/parse/permission failures must never slow our own uploads -- the
fail-safe direction is "post normally", not "yield defensively").

weewx is not installed in the test/CI environment, so we stub the weewx
modules in sys.modules before importing influx (same pattern as the other
tests here, extended so the RESTThread stub actually implements
post_interval/lastpost/skip_this_post -- this test is specifically about that
interaction, so the stub can't be a no-op like test_owm_post_body.py's).

Run:  python3 -m pytest tests/   OR   python3 tests/test_influx_lease_yield.py
"""
import json
import os
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone

# --- stub the weewx deps so influx.py imports without weewx installed ---
def _pkg(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m


def _mod(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m


weewx = _pkg("weewx")
weewx.NEW_ARCHIVE_RECORD = "NEW_ARCHIVE_RECORD"
weewx.NEW_LOOP_PACKET = "NEW_LOOP_PACKET"
weewx.debug = 0
weewx.__version__ = "5.5.0"


class ViolatedPrecondition(Exception):
    pass


class UnknownBinding(Exception):
    pass


class UnsupportedFeature(Exception):
    pass


weewx.ViolatedPrecondition = ViolatedPrecondition
weewx.UnknownBinding = UnknownBinding
weewx.UnsupportedFeature = UnsupportedFeature

weewx_restx = _mod("weewx.restx")


class _StdRESTbase:
    def __init__(self, *a, **k):
        pass

    def bind(self, *a, **k):
        pass


class _RESTThread:
    """Real enough to test the interaction, not a no-op stand-in: implements
    the same post_interval/lastpost/skip_this_post shape as weewx 5.5.0's
    actual weewx/restx.py (verified against the real source, not recalled --
    see DEC-0111), since that interaction is exactly what's under test."""

    def __init__(self, queue, protocol_name=None, manager_dict=None,
                 post_interval=None, max_backlog=None, stale=None,
                 log_success=True, log_failure=True, max_tries=3,
                 timeout=60, retry_wait=5):
        self.queue = queue
        self.protocol_name = protocol_name
        self.post_interval = post_interval
        self.stale = stale
        self.lastpost = 0

    def skip_this_post(self, time_ts):
        if self.stale is not None and (time_ts - time_ts) > self.stale:
            return True  # unreachable with time_ts==time_ts; kept for shape parity
        if self.post_interval is not None:
            if (time_ts - self.lastpost) < self.post_interval:
                return True
        self.lastpost = time_ts
        return False


def _get_site_dict(config_dict, *args, **kwargs):
    return {}


weewx_restx.StdRESTbase = _StdRESTbase
weewx_restx.RESTThread = _RESTThread
weewx_restx.get_site_dict = _get_site_dict
weewx.restx = weewx_restx

weewx_units = _mod("weewx.units")
weewx_units.unit_constants = {}
weewx_units.to_std_system = lambda record, usn: record
weewx.units = weewx_units

weewx_manager = _mod("weewx.manager")
weewx_manager.get_manager_dict_from_config = lambda *a, **k: {}
weewx.manager = weewx_manager

weeutil_weeutil = _mod("weeutil.weeutil")
weeutil_weeutil.to_bool = lambda v: bool(v)
weeutil_weeutil.accumulateLeaves = lambda d: d
weeutil_pkg = _pkg("weeutil")
weeutil_pkg.weeutil = weeutil_weeutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import influx  # noqa: E402

TENANT = influx.TENANT
YIELD_S = influx.LEASE_YIELD_POST_INTERVAL_S


def _make_thread(lease_dir=None, post_interval=60):
    return influx.InfluxThread(
        queue=None, server_url="http://x", org="o", bucket="b", token="t",
        post_interval=post_interval, lease_dir=lease_dir)


def _write_lease(lease_dir, tenant="coffee-radar", seconds_from_now=1800):
    expires = datetime.now(timezone.utc) + timedelta(seconds=seconds_from_now)
    body = {
        "schema": 1, "tenant": tenant, "job": "test-job",
        "acquired_at": "2026-08-21T00:00:00Z",
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "renewal_floor_s": 600,
    }
    with open(os.path.join(lease_dir, "heavy-io.lease"), "w") as f:
        f.write(json.dumps(body))


def test_off_by_default_when_lease_dir_unset():
    t = _make_thread(lease_dir=None)
    assert t._foreign_lease_active() is False
    print("  [PASS] test_off_by_default_when_lease_dir_unset")


def test_missing_lease_file_is_not_active():
    with tempfile.TemporaryDirectory() as d:
        t = _make_thread(lease_dir=d)
        assert t._foreign_lease_active() is False
    print("  [PASS] test_missing_lease_file_is_not_active")


def test_corrupt_lease_file_is_not_active():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "heavy-io.lease"), "w") as f:
            f.write("{not valid json")
        t = _make_thread(lease_dir=d)
        assert t._foreign_lease_active() is False
    print("  [PASS] test_corrupt_lease_file_is_not_active")


def test_lease_missing_expires_at_is_not_active():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "heavy-io.lease"), "w") as f:
            f.write(json.dumps({"schema": 1, "tenant": "coffee-radar"}))
        t = _make_thread(lease_dir=d)
        assert t._foreign_lease_active() is False
    print("  [PASS] test_lease_missing_expires_at_is_not_active")


def test_own_tenant_lease_is_not_active():
    with tempfile.TemporaryDirectory() as d:
        _write_lease(d, tenant=TENANT, seconds_from_now=1800)
        t = _make_thread(lease_dir=d)
        assert t._foreign_lease_active() is False
    print("  [PASS] test_own_tenant_lease_is_not_active")


def test_foreign_unexpired_lease_is_active():
    with tempfile.TemporaryDirectory() as d:
        _write_lease(d, tenant="coffee-radar", seconds_from_now=1800)
        t = _make_thread(lease_dir=d)
        assert t._foreign_lease_active() is True
    print("  [PASS] test_foreign_unexpired_lease_is_active")


def test_foreign_expired_lease_is_not_active():
    with tempfile.TemporaryDirectory() as d:
        _write_lease(d, tenant="coffee-radar", seconds_from_now=-60)
        t = _make_thread(lease_dir=d)
        assert t._foreign_lease_active() is False
    print("  [PASS] test_foreign_expired_lease_is_not_active")


def test_skip_this_post_raises_post_interval_while_held():
    with tempfile.TemporaryDirectory() as d:
        _write_lease(d, tenant="coffee-radar", seconds_from_now=1800)
        t = _make_thread(lease_dir=d, post_interval=60)
        t.skip_this_post(1000)
        assert t.post_interval == YIELD_S
    print("  [PASS] test_skip_this_post_raises_post_interval_while_held")


def test_skip_this_post_restores_base_once_lease_clears():
    with tempfile.TemporaryDirectory() as d:
        _write_lease(d, tenant="coffee-radar", seconds_from_now=1800)
        t = _make_thread(lease_dir=d, post_interval=60)
        t.skip_this_post(1000)
        assert t.post_interval == YIELD_S
        os.remove(os.path.join(d, "heavy-io.lease"))
        t.skip_this_post(2000)
        assert t.post_interval == 60
    print("  [PASS] test_skip_this_post_restores_base_once_lease_clears")


def test_skip_this_post_still_honors_base_interval_when_not_held():
    # End-to-end against the real (stubbed-real) RESTThread logic: with no
    # lease held, a record inside the configured post_interval is skipped,
    # exactly as unmodified weewx would.
    t = _make_thread(lease_dir=None, post_interval=60)
    assert t.skip_this_post(1000) is False  # first record always posts
    assert t.skip_this_post(1030) is True   # 30s < 60s post_interval -> skip
    assert t.skip_this_post(1070) is False  # 70s >= 60s -> posts
    print("  [PASS] test_skip_this_post_still_honors_base_interval_when_not_held")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
    print("\n%d/%d passed" % (len(tests), len(tests)))
