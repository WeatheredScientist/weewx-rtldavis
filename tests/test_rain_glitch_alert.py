"""Offline unit tests for the rain-glitch email-alert detection (weewx_monitor.py).

Tests parse_rain_glitch() against real driver-log signatures and non-matching
lines. Does not send email (send_email is exercised end-to-end via the
`weewx_monitor.py --test-alert` mode on the NAS, where the Gmail creds live).

weewx_monitor.py runs the PID guard + emails at import; we set --test-alert in
argv so the module imports cleanly (guard bypassed) and reads env-less creds
harmlessly (send_email is not called during import).

Run:  python -m pytest tests/    OR    python tests/test_rain_glitch_alert.py
"""
import os
import sys

sys.argv = [sys.argv[0], "--test-alert"]   # bypass PID guard on import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402


# real driver log lines (weewx prepends "TS logger LEVEL " to our logerr text)
JUL4 = ("2026-07-04 03:03:45 user.rtldavis ERROR rain: rejecting implausible "
        "counter delta last=70 new=6 (RF glitch, not rain -- DEC-0021)")
MAY25 = ("2026-05-25 23:22:10 user.rtldavis ERROR rain: rejecting implausible "
         "counter delta last=5 new=133 (RF glitch, not rain -- DEC-0021)")

NON_MATCHES = [
    "2026-07-04 03:03:45 user.rtldavis INFO Wunderground-RF: Published record",
    "2026-07-04 03:03:45 weewx.engine INFO Starting main packet loop",
    "2026-07-04 03:03:45 user.rtldavis INFO rain counter wraparound detected rain_count=-127",
    "",
]


def test_detects_jul4_glitch():
    g = wm.parse_rain_glitch(JUL4)
    assert g is not None
    ts, detail, phantom_in = g
    assert ts == "2026-07-04 03:03:45"
    assert detail == "last=70 new=6"
    assert phantom_in == 0.64, f"Jul-4 -64 -> +128 = +64 tips = 0.64in, got {phantom_in}"


def test_detects_may25_glitch():
    g = wm.parse_rain_glitch(MAY25)
    assert g is not None
    _, detail, phantom_in = g
    assert detail == "last=5 new=133"
    assert phantom_in == 1.28, f"May-25 +128 tips = 1.28in, got {phantom_in}"


def test_ignores_non_glitch_lines():
    for line in NON_MATCHES:
        assert wm.parse_rain_glitch(line) is None, f"false positive on: {line!r}"


if __name__ == "__main__":
    cases = [
        ("Jul-4 glitch detected", lambda: wm.parse_rain_glitch(JUL4) is not None),
        ("Jul-4 phantom = 0.64in", lambda: wm.parse_rain_glitch(JUL4)[2] == 0.64),
        ("May-25 phantom = 1.28in", lambda: wm.parse_rain_glitch(MAY25)[2] == 1.28),
        ("real wraparound NOT flagged", lambda: wm.parse_rain_glitch(NON_MATCHES[2]) is None),
        ("upload line NOT flagged", lambda: wm.parse_rain_glitch(NON_MATCHES[0]) is None),
        ("empty line NOT flagged", lambda: wm.parse_rain_glitch("") is None),
    ]
    passed = 0
    for name, fn in cases:
        ok = False
        try:
            ok = bool(fn())
        except Exception as e:
            name += f" (raised {e!r})"
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n{passed}/{len(cases)} passed")
    sys.exit(0 if passed == len(cases) else 1)
