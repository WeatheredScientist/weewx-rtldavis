"""Offline unit tests for the rain-counter glitch filter (DEC-0021, S18).

The false-rain bug: the driver treated ANY negative rain-counter delta as a
127->0 wraparound and added 128, turning a single-bit RF-decode glitch into
phantom rain. These tests exercise the REAL `rain_delta_tips` from rtldavis.py
against the exact counter signatures recorded in the two confirmed events, so
the deployed file is what's under test.

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing the driver. The function under test is pure
arithmetic and needs none of them.

Run:  python -m pytest tests/ (pytest only)
"""

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
