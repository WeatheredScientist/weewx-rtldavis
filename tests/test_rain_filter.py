"""Offline unit tests for the rain-counter glitch filter (DEC-0021, S18).

The false-rain bug: the driver treated ANY negative rain-counter delta as a
127->0 wraparound and added 128, turning a single-bit RF-decode glitch into
phantom rain. These tests exercise the REAL `rain_delta_tips` from rtldavis.py
against the exact counter signatures recorded in the two confirmed events, so
the deployed file is what's under test.

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing the driver. The function under test is pure
arithmetic and needs none of them.

Run:  python -m pytest tests/    OR    python tests/test_rain_filter.py
"""
import os
import sys
import types

# --- stub the weewx deps so rtldavis.py imports without weewx installed ---
# rtldavis.py imports: weewx.drivers, weewx.engine, weewx.units, weewx.crc16,
# weeutil.weeutil, weeutil.logger. None are needed by rain_delta_tips (pure
# arithmetic); we stub them so the module imports and we test the real function.
def _pkg(name):
    m = types.ModuleType(name)
    m.__path__ = []          # mark as a package so submodule imports resolve
    sys.modules[name] = m
    return m

def _mod(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

# distinct base classes (RtldavisDriver subclasses AbstractDevice AND StdService)
class _AbstractDevice:
    def __init__(self, *a, **k): pass
class _AbstractConfEditor:
    pass
class _StdService:
    def __init__(self, *a, **k): pass

_weewx = _pkg("weewx")
_weewx.__version__ = "5.3.1"                  # rtldavis.py version-checks at import
_weewx.METRICWX = 16                          # sentinel; unused by the function
_drivers = _mod("weewx.drivers")
_drivers.AbstractDevice = _AbstractDevice
_drivers.AbstractConfEditor = _AbstractConfEditor
_engine = _mod("weewx.engine")
_engine.StdService = _StdService
_units = _mod("weewx.units")
# rtldavis.py registers a custom 'group_frequency' unit at import time by
# mutating these dicts — provide them all as empty dicts.
for _d in ("obs_group_dict", "USUnits", "MetricUnits", "MetricWXUnits",
           "default_unit_format_dict", "default_unit_label_dict"):
    setattr(_units, _d, {})
_crc16 = _mod("weewx.crc16")
_crc16.crc16 = lambda *a, **k: 0
_weewx.drivers, _weewx.engine, _weewx.units, _weewx.crc16 = (
    _drivers, _engine, _units, _crc16)

_weeutil = _pkg("weeutil")
_wu = _mod("weeutil.weeutil")
_wu.tobool = lambda v: str(v).lower() in ("1", "true", "yes", "on")
_wlog = _mod("weeutil.logger")
_weeutil.weeutil, _weeutil.logger = _wu, _wlog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rtldavis import rain_delta_tips, MAX_PLAUSIBLE_TIPS  # noqa: E402


# (last_count, new_count, expected_tips, description)
CASES = [
    # --- confirmed real-event glitches: MUST be rejected (None) ---
    (70, 6,   None, "Jul-4 event: delta -64 (bit-6 glitch), NOT a wraparound -> reject"),
    (5, 133,  None, "May-25 event: delta +128 (bit-7 glitch, direct positive) -> reject"),
    (100, 36, None, "same -64 signature from a different base -> reject"),
    (0, 64,   None, "direct +64 positive glitch -> reject"),
    # --- genuine wraparounds: MUST pass (real ones observed were exactly -127) ---
    (127, 0,  1,   "real 127->0 wraparound, +1 tip"),
    (127, 5,  6,   "real wraparound with 5 concurrent tips at the boundary"),
    (120, 6,  14,  "real wraparound across a modest gap: 120->(wrap)->6 = 14 tips < cap"),
    # --- normal rain: MUST pass unchanged ---
    (None, 42, 0,  "first packet ever (no prior count) -> 0"),
    (40, 43,  3,   "normal light rain, +3 tips"),
    (40, 40,  0,   "no change, 0 tips"),
    (100, 107, 7,  "worst-ever REAL single minute (7 tips, 2026-06-14 storm) -> 2.3x headroom"),
    # --- the DEC-0056 boundary: cap is 16, and the check is `delta > max_tips` ---
    (0, 16,   16,  "exactly at the cap: worst-ever REAL 3-min accumulation (2026-06-14, "
                   "DEC-0056 evidence pass) is exactly 16 tips and MUST pass"),
    (0, 17,   None, "one tip over the cap (17) -> reject"),
    # --- cap-60-era cases that now reject: a genuine 18-tip delta needs a >72 s
    # reading gap (~4 s/tip ceiling); worst observed in-service gap during rain
    # is 60 s. If it ever really happens: loud log -> WeatherLink reconciliation
    # (DEC-0056 playbook), not silent acceptance of a possible glitch. ---
    (100, 118, None, "+18 in one delta -> reject under DEC-0056 (was allowed at cap 60)"),
    (120, 10, None,  "wraparound + 18-tip catch-up (120->wrap->10) -> reject under DEC-0056"),
]


def _check(last, new, expected, desc):
    got = rain_delta_tips(last, new)
    assert got == expected, f"{desc}: rain_delta_tips({last},{new}) = {got}, expected {expected}"


def test_cap_value():
    assert MAX_PLAUSIBLE_TIPS == 16, "MAX_PLAUSIBLE_TIPS should be 16 (0.16 in) per DEC-0056 (R2)"


def test_all_cases():
    for last, new, expected, desc in CASES:
        _check(last, new, expected, desc)


if __name__ == "__main__":
    passed = 0
    print(f"MAX_PLAUSIBLE_TIPS = {MAX_PLAUSIBLE_TIPS}\n")
    for last, new, expected, desc in CASES:
        got = rain_delta_tips(last, new)
        ok = (got == expected)
        passed += ok
        rain_in = "None" if got is None else f"{got * 0.01:.2f}in"
        print(f"  [{'PASS' if ok else 'FAIL'}] ({str(last):>4},{new:>3}) -> {str(got):>4} ({rain_in:>6})  {desc}")
    print(f"\n{passed}/{len(CASES)} passed")
    sys.exit(0 if passed == len(CASES) else 1)
