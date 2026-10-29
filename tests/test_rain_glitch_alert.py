"""Offline unit tests for the rain-glitch email-alert detection (weewx_monitor.py).

Tests parse_rain_glitch() against real driver-log signatures and non-matching
lines. Does not send email (send_email is exercised end-to-end via the
`weewx_monitor.py --test-alert` mode on the host that holds the Gmail creds).

weewx_monitor.py runs the PID guard + emails at import; we set --test-alert in
argv so the module imports cleanly (guard bypassed) and reads env-less creds
harmlessly (send_email is not called during import).

Run:  python -m pytest tests/ (pytest only)
"""
import os
import sys

sys.argv = [sys.argv[0], "--test-alert"]   # bypass PID guard on import
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


def test_marker_matches_driver_source():
    """Cross-module contract (DEC-0056): the monitor's marker must appear
    verbatim in rtldavis.py's rejection logerr. If the driver message is ever
    reworded, the rejection tripwire dies silently -- this test is what breaks
    instead. (The alert is the agreed detection path for a false reject, so
    its coupling to the driver's exact wording is load-bearing.)"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "rtldavis.py")) as f:
        src = f.read()
    assert wm.RAIN_GLITCH_MARKER in src, \
        "monitor marker no longer present in rtldavis.py -- alert is dead"
    assert 'rain: rejecting implausible counter delta last=' in src, \
        "driver rejection message shape changed -- update parse_rain_glitch and this test together"
