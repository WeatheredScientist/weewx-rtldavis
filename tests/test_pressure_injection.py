"""Offline unit tests for pressure_service.py's injection scope (#144) and
fetch-freshness stamp (#172), S82b.

The #144 half: the old code backfilled BOTH `pressure` (station) and
`altimeter` with the fetched sea-level value. Those are different quantities —
at any nonzero elevation the archive's station-pressure column was carrying
sea-level numbers (hlf#302). Honest nulls instead (DEC-0006): only
`barometer`, the quantity actually fetched, is injected.

The #172 half: `last_fetch` is a throttle stamp that advances on FAILED
attempts too, so it cannot answer "how fresh is this relayed value?". A new
`last_success` is set only when a fetch yields a value, and stamped into every
packet as `barometer_fetch_epoch` for loop_json_writer to publish.

weewx is stubbed before import, same pattern as test_loop_json_writer.py.

Run:  python3 -m pytest tests/   OR   python3 tests/test_pressure_injection.py
"""
import os
import sys
import types

# --- stub the weewx deps so pressure_service.py imports without weewx installed ---
def _pkg(name):
    m = sys.modules.get(name) or types.ModuleType(name)
    m.__path__ = getattr(m, "__path__", [])
    sys.modules[name] = m
    return m

def _mod(name):
    m = sys.modules.get(name) or types.ModuleType(name)
    sys.modules[name] = m
    return m

class _StdService:
    def __init__(self, *a, **k):
        pass

    def bind(self, event_type, handler):
        self._bound = (event_type, handler)


weewx = _pkg("weewx")
weewx.NEW_LOOP_PACKET = getattr(weewx, "NEW_LOOP_PACKET", "NEW_LOOP_PACKET")
weewx_engine = _mod("weewx.engine")
# Another test file's stub may already occupy sys.modules (they all stub, each
# with only what IT needs -- test_parse_raw_channel's StdService has no bind()).
# Reuse whatever is there, but guarantee the one method our service calls.
if not hasattr(getattr(weewx_engine, "StdService", None), "bind"):
    weewx_engine.StdService = _StdService
weewx_units = _mod("weewx.units")
weewx_units.to_US = getattr(weewx_units, "to_US", lambda pkt: pkt)
weewx.engine, weewx.units = weewx_engine, weewx_units

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pressure_service as ps  # noqa: E402


def _make_fetcher():
    cfg = {'DavisPressure': {'api_key': 'test-key', 'api_secret': 'test-secret',
                             'station_id': '1'}}
    return ps.DavisPressureFetcher(engine=None, config_dict=cfg)


def _event(**packet):
    return types.SimpleNamespace(packet=packet)


def test_barometer_injected_but_not_pressure_or_altimeter():
    """The #144 flip: before S82b this exact fixture came back with all three
    keys carrying the same sea-level number."""
    f = _make_fetcher()
    f.last_pressure = 29.92
    f.last_fetch = ps.time.time()               # throttle: no fetch this packet
    ev = _event(barometer=None, pressure=None, altimeter=None)
    f.new_loop_packet(ev)
    assert ev.packet['barometer'] == 29.92
    assert ev.packet['pressure'] is None, \
        "station pressure must stay an honest null, not borrowed sea-level"
    assert ev.packet['altimeter'] is None, \
        "altimeter must stay an honest null, not borrowed sea-level"


def test_existing_barometer_is_not_overwritten():
    f = _make_fetcher()
    f.last_pressure = 29.92
    f.last_fetch = ps.time.time()
    ev = _event(barometer=30.10)
    f.new_loop_packet(ev)
    assert ev.packet['barometer'] == 30.10


def test_fetch_epoch_stamped_once_a_fetch_has_succeeded():
    f = _make_fetcher()
    f.last_pressure = 29.92
    f.last_success = 1_700_000_000.7
    f.last_fetch = ps.time.time()
    ev = _event(barometer=None)
    f.new_loop_packet(ev)
    assert ev.packet['barometer_fetch_epoch'] == 1_700_000_000


def test_no_fetch_epoch_before_first_success():
    """A throttle attempt is not a success: last_fetch advancing must not
    manufacture a freshness claim."""
    f = _make_fetcher()
    f.last_pressure = None
    f.last_success = None
    f.last_fetch = ps.time.time()
    ev = _event(barometer=None)
    f.new_loop_packet(ev)
    assert 'barometer_fetch_epoch' not in ev.packet


def test_successful_fetch_sets_last_success(monkeypatch):
    """Drive the real fetch_pressure() against a canned WeatherLink response
    and assert last_success moves only then."""
    f = _make_fetcher()

    class _Resp:
        @staticmethod
        def json():
            return {'sensors': [{'data': [{'bar_sea_level': 29.87}]}]}

    fake_requests = types.SimpleNamespace(get=lambda url, timeout: _Resp())
    monkeypatch.setattr(ps, "requests", fake_requests, raising=False)
    monkeypatch.setattr(ps, "REQUESTS_AVAILABLE", True)

    assert f.last_success is None
    before = ps.time.time()
    f.fetch_pressure()
    assert f.last_pressure == 29.87
    assert f.last_success is not None and f.last_success >= before


def test_failed_fetch_leaves_last_success_untouched(monkeypatch):
    f = _make_fetcher()

    class _Resp:
        @staticmethod
        def json():
            return {'sensors': []}             # no pressure in the response

    fake_requests = types.SimpleNamespace(get=lambda url, timeout: _Resp())
    monkeypatch.setattr(ps, "requests", fake_requests, raising=False)
    monkeypatch.setattr(ps, "REQUESTS_AVAILABLE", True)

    f.last_success = 1_600_000_000.0
    f.fetch_pressure()
    assert f.last_success == 1_600_000_000.0, \
        "a fetch that yielded nothing must not refresh the freshness stamp"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
