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


def _body(monkeypatch):
    sent = []
    monkeypatch.setattr(wm, 'send_email', lambda subject, body: sent.append(body))
    wm.send_rain_glitch_alert(*wm.parse_rain_glitch(JUL4), JUL4)
    return sent[0]


def test_email_says_to_check_the_log_before_reconciling(monkeypatch):
    """DEC-0249: a catch-up is already booked, so a hand correction would double it."""
    body = _body(monkeypatch)
    order = [body.index(x) for x in (
        'Before adding any rain by hand', "'rain: counter move confirmed'",
        'Do not add it again', "'rain: counter recovered'", 'Add nothing',
        'Neither, once later rain readings', 'WeatherLink console', 'DEC-0056 playbook')]
    assert order == sorted(order)


def test_email_reads_right_before_the_next_reading_and_on_an_older_image(monkeypatch):
    body = _body(monkeypatch)
    assert 'this email can go out before they are written' in body
    assert 'driver versions that have it' in body


def test_email_quotes_the_driver_lines_it_names(monkeypatch):
    """The two lines the reader greps for are the driver's, and neither is the marker."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "rtldavis.py")) as f:
        src = f.read()
    body = _body(monkeypatch)
    for line in ('rain: counter move confirmed', 'rain: counter recovered'):
        assert line in body and 'loginf("' + line in src


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
