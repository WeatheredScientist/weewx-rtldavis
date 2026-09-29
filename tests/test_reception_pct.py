"""Offline unit tests for the reception-% denominator fix (S29).

The monitor turns a per-60s-window count of unique WU-RF records into a reception
percentage. Before S29 the denominator was a hardcoded 24 ("one post per 2.5s"),
but this station's ISS (Transmitter 4) transmits every ~2.8125s -> only ~21.3
records/min are physically sent. Dividing a full-reception window (~21-22 records)
by 24 read ~88-92% and made reception look worse than it was. The fix sets the
denominator to the real physical rate (WU_RF_EXPECTED, default 21, env-overridable)
and caps the reported percentage at 100 via wu_pct().

These once recorded results in a list and printed PASS/FAIL without ever asserting,
so pytest could not fail them (#410); they now assert. The cases assume the default
denominator, so they skip when WU_RF_EXPECTED is overridden in the environment.

Run:  python3 -m pytest tests/test_reception_pct.py
"""
import os
import sys

import pytest

# Bypass the module's PID guard so importing it doesn't touch a running monitor.
sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402

# Keyed on the environment, not on the module's value, so a regressed default
# still fails instead of being skipped.
pytestmark = pytest.mark.skipif(
    "WU_RF_EXPECTED" in os.environ,
    reason="cases assume the default denominator; WU_RF_EXPECTED is overridden")


def test_default_denominator_is_physical_rate():
    # 60 / 2.8125s = ~21.3; the fix rounds to 21 (was 24).
    assert wm.WU_RF_EXPECTED == 21


def test_full_reception_reads_near_100_not_92():
    # A 22-record window: old code -> 22/24 = 92%; fixed -> capped 100%.
    assert round(22 / 24 * 100) == 92     # sanity: what the old /24 denominator read
    assert wm.wu_pct(22) == 100.0         # capped 100%, not 92%
    assert round(wm.wu_pct(21)) == 100    # a 21-record window is ~100%


def test_pct_is_capped_at_100():
    assert wm.wu_pct(25) == 100.0         # an over-count window never reads >100
    assert wm.wu_pct(wm.WU_RF_EXPECTED + 5) == 100.0


def test_partial_reception_is_proportional():
    # Half the physical packets -> ~50%; a third -> a third (pins the denominator).
    assert round(wm.wu_pct(wm.WU_RF_EXPECTED / 2)) == 50
    assert wm.wu_pct(7) == pytest.approx(100 / 3)
    assert wm.wu_pct(0) == 0.0


def test_alert_threshold_now_means_real_loss():
    # 60% of the corrected denominator is a genuine, large packet loss: the alert
    # floor sits well under the physical rate (a >~35% loss).
    floor = wm.WU_RF_MIN_PCT / 100 * wm.WU_RF_EXPECTED
    assert floor < wm.WU_RF_EXPECTED * 0.65


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
