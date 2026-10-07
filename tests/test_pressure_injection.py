"""Offline unit tests for pressure_service.py's injection scope (#144) and
fetch-freshness stamp (#172), S82b.

The #144 half: the old code backfilled BOTH `pressure` (station) and
`altimeter` with the fetched sea-level value. Those are different quantities —
at any nonzero elevation the archive's station-pressure column was carrying
sea-level numbers (hlf#302). Honest nulls instead (DEC-0006): only
`barometer`, the quantity actually fetched, is injected.

The DEC-0209 half (S150, eaglehunt-ops#357): `pressure` is injected again, but
as a MEASURED value this time — WeatherLink's `bar_absolute`, the raw sensor
reading from the same record as `bar_sea_level`. `altimeter` is still never
injected; weewx derives it from the measured `pressure`. Without
`bar_absolute` in the response, `pressure` stays None (and weewx keeps
deriving it, as it did all along — INTERFACES §1).

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
    cfg = {'DavisPressure': {'api_key': 'YOUR_API_KEY', 'api_secret': 'YOUR_API_SECRET',
                             'station_id': '1'}}
    return ps.DavisPressureFetcher(engine=None, config_dict=cfg)


def _event(**packet):
    return types.SimpleNamespace(packet=packet)


def test_barometer_injected_but_not_pressure_or_altimeter_without_bar_absolute():
    """The #144 flip: before S82b this exact fixture came back with all three
    keys carrying the same sea-level number. With no bar_absolute fetched yet
    (DEC-0209), pressure still stays None — never the borrowed sea-level."""
    f = _make_fetcher()
    f.last_pressure = 29.92
    f.last_station_pressure = None
    f.last_fetch = ps.time.time()               # throttle: no fetch this packet
    ev = _event(barometer=None, pressure=None, altimeter=None)
    f.new_loop_packet(ev)
    assert ev.packet['barometer'] == 29.92
    assert ev.packet['pressure'] is None, \
        "station pressure must stay an honest null, not borrowed sea-level"
    assert ev.packet['altimeter'] is None, \
        "altimeter must stay an honest null, not borrowed sea-level"


def test_measured_station_pressure_injected_but_never_altimeter():
    """DEC-0209: bar_absolute lands as `pressure`, its own number, distinct
    from the sea-level barometer. altimeter is still weewx's to derive."""
    f = _make_fetcher()
    f.last_pressure = 30.04
    f.last_station_pressure = 29.46
    f.last_fetch = ps.time.time()
    ev = _event(barometer=None, pressure=None, altimeter=None)
    f.new_loop_packet(ev)
    assert ev.packet['barometer'] == 30.04
    assert ev.packet['pressure'] == 29.46
    assert ev.packet['pressure'] != ev.packet['barometer'], \
        "the #144 bug was these two being the same number"
    assert ev.packet['altimeter'] is None, \
        "altimeter is never injected; weewx derives it from the measured pressure"


def test_existing_barometer_is_not_overwritten():
    f = _make_fetcher()
    f.last_pressure = 29.92
    f.last_fetch = ps.time.time()
    ev = _event(barometer=30.10)
    f.new_loop_packet(ev)
    assert ev.packet['barometer'] == 30.10


def test_existing_pressure_is_not_overwritten():
    """Same prefer_hardware courtesy as barometer: a value already in the
    packet is the hardware's, not ours to replace."""
    f = _make_fetcher()
    f.last_pressure = 30.04
    f.last_station_pressure = 29.46
    f.last_fetch = ps.time.time()
    ev = _event(barometer=None, pressure=29.50)
    f.new_loop_packet(ev)
    assert ev.packet['pressure'] == 29.50


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
            return {'sensors': [{'data': [{'bar_sea_level': 29.87, 'bar_absolute': 29.30}]}]}

    fake_requests = types.SimpleNamespace(get=lambda url, timeout: _Resp())
    monkeypatch.setattr(ps, "requests", fake_requests, raising=False)
    monkeypatch.setattr(ps, "REQUESTS_AVAILABLE", True)

    assert f.last_success is None
    before = ps.time.time()
    f.fetch_pressure()
    assert f.last_pressure == 29.87
    assert f.last_station_pressure == 29.30
    assert f.last_success is not None and f.last_success >= before
    assert f._warned_no_absolute is False


def _fetch(f, monkeypatch, sensors):
    class _Resp:
        @staticmethod
        def json():
            return {'sensors': sensors}

    monkeypatch.setattr(ps, "requests",
                        types.SimpleNamespace(get=lambda url, timeout: _Resp()), raising=False)
    monkeypatch.setattr(ps, "REQUESTS_AVAILABLE", True)
    f.fetch_pressure()


def test_fetch_without_bar_absolute_leaves_station_pressure_none(monkeypatch):
    """DEC-0209's fallback: the sea-level relay still works, pressure stays
    None (weewx derives it, the pre-DEC-0209 state), and the one-time warning
    is armed."""
    f = _make_fetcher()
    _fetch(f, monkeypatch, [{'data': [{'bar_sea_level': 29.87}]}])
    assert f.last_pressure == 29.87
    assert f.last_station_pressure is None
    assert f._warned_no_absolute is True


def test_bar_absolute_is_read_from_the_sea_level_record_only(monkeypatch):
    """A bar_absolute in some OTHER record is another sensor's reading. The
    pair must come from one record, or the two pressures could disagree
    about which instrument they describe."""
    f = _make_fetcher()
    _fetch(f, monkeypatch, [
        {'data': [{'bar_sea_level': 29.87}]},
        {'data': [{'bar_absolute': 29.30}]},
    ])
    assert f.last_pressure == 29.87
    assert f.last_station_pressure is None


def test_bar_fallback_record_also_yields_bar_absolute(monkeypatch):
    """The legacy `bar` key (no bar_sea_level) is still the sea-level relay,
    and bar_absolute beside it is still read."""
    f = _make_fetcher()
    _fetch(f, monkeypatch, [{'data': [{'bar': 29.90, 'bar_absolute': 29.33}]}])
    assert f.last_pressure == 29.90
    assert f.last_station_pressure == 29.33


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
