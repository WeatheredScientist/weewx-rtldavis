"""Offline unit tests for the RF-reception dedup key (DEC-0024, S22).

The bug: the RF-reception summary read ~150% (above the 100% ceiling). Root
cause (DEC-0024): the driver publishes freqError freq-hop channel packets as
extra dataless loop packets, so each real reading is posted to Wunderground
several times under the SAME record epoch. `weewx_monitor.py` counted raw
"Wunderground-RF ... Published" log LINES, so it over-read reception.

Layer A fix: count UNIQUE record epochs per window instead of raw lines. These
tests exercise the REAL `wu_record_key` from weewx_monitor.py against the exact
publish lines recorded live on 2026-07-05, so the deployed file is under test.

weewx_monitor.py writes a pidfile at import; `--test-alert` in argv bypasses
that guard (its intended non-invasive path), letting the module import cleanly.

Run:  python3 -m pytest tests/    OR    python3 tests/test_reception_dedup.py
"""
import os
import sys

# Bypass the module's PID guard so importing it doesn't touch a running monitor.
sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from weewx_monitor import wu_record_key  # noqa: E402


# Exact lines recorded live 2026-07-05 08:58 (single active transmitter). Each
# real reading appears TWICE under one epoch -- the freqError shadow (DEC-0024).
LIVE_SAMPLE = [
    "2026-07-05 08:58:16,989 weewx.restx INFO Wunderground-RF: Published record 2026-07-05 08:58:17 EDT (1783256297)",
    "2026-07-05 08:58:17,049 weewx.restx INFO Wunderground-RF: Published record 2026-07-05 08:58:17 EDT (1783256297)",
    "2026-07-05 08:58:19,865 weewx.restx INFO Wunderground-RF: Published record 2026-07-05 08:58:20 EDT (1783256300)",
    "2026-07-05 08:58:20,066 weewx.restx INFO Wunderground-RF: Published record 2026-07-05 08:58:20 EDT (1783256300)",
    "2026-07-05 08:58:22,612 weewx.restx INFO Wunderground-RF: Published record 2026-07-05 08:58:23 EDT (1783256303)",
    "2026-07-05 08:58:22,680 weewx.restx INFO Wunderground-RF: Published record 2026-07-05 08:58:23 EDT (1783256303)",
    "2026-07-05 08:58:25,426 weewx.restx INFO Wunderground-RF: Published record 2026-07-05 08:58:25 EDT (1783256305)",
    "2026-07-05 08:58:25,476 weewx.restx INFO Wunderground-RF: Published record 2026-07-05 08:58:25 EDT (1783256305)",
]
LIVE_EXPECTED_EPOCHS = {"1783256297", "1783256300", "1783256303", "1783256305"}


def test_key_is_trailing_epoch():
    line = LIVE_SAMPLE[0]
    assert wu_record_key(line) == "1783256297"


def test_duplicate_lines_collapse():
    # 8 raw publish lines -> 4 unique records: the exact ~2x over-read (DEC-0024).
    keys = {wu_record_key(ln) for ln in LIVE_SAMPLE}
    assert keys == LIVE_EXPECTED_EPOCHS
    assert len(LIVE_SAMPLE) == 8 and len(keys) == 4


def test_dedup_would_have_fixed_the_metric():
    # Raw-line count over-reads; unique-epoch count is the true reading.
    raw = len(LIVE_SAMPLE)                       # what the OLD code counted
    unique = len({wu_record_key(ln) for ln in LIVE_SAMPLE})  # what the NEW code counts
    assert raw > unique                          # the over-count existed
    assert unique == 4                           # and dedup gives the real number


def test_trailing_whitespace_and_newline_tolerated():
    assert wu_record_key(LIVE_SAMPLE[0] + "\n") == "1783256297"
    assert wu_record_key(LIVE_SAMPLE[0] + "   ") == "1783256297"


def test_unparseable_falls_back_to_whole_line():
    # No trailing "(epoch)": fall back to the whole line so we never over-collapse
    # distinct records, and identical malformed lines still dedup.
    a = "Wunderground-RF: Published record (no epoch here)"
    b = "Wunderground-RF: Published record something else"
    assert wu_record_key(a) == a
    assert wu_record_key(b) == b
    assert len({wu_record_key(a), wu_record_key(b), wu_record_key(a)}) == 2


def test_only_trailing_parens_group_used():
    # Parenthesised text earlier in the line must not be mistaken for the epoch.
    line = "INFO (retry) Wunderground-RF: Published record 2026-07-05 (1783256999)"
    assert wu_record_key(line) == "1783256999"


ALL_TESTS = [
    test_key_is_trailing_epoch,
    test_duplicate_lines_collapse,
    test_dedup_would_have_fixed_the_metric,
    test_trailing_whitespace_and_newline_tolerated,
    test_unparseable_falls_back_to_whole_line,
    test_only_trailing_parens_group_used,
]


if __name__ == "__main__":
    passed = 0
    raw, unique = len(LIVE_SAMPLE), len({wu_record_key(ln) for ln in LIVE_SAMPLE})
    print(f"live sample: {raw} raw publish lines -> {unique} unique records "
          f"({raw / unique:.2f}x over-read before the fix)\n")
    for t in ALL_TESTS:
        try:
            t()
            passed += 1
            print(f"  [PASS] {t.__name__}")
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
    print(f"\n{passed}/{len(ALL_TESTS)} passed")
    sys.exit(0 if passed == len(ALL_TESTS) else 1)
