"""Offline unit tests for the reception-% denominator fix (S29).

The monitor turns a per-60s-window count of unique WU-RF records into a reception
percentage. Before S29 the denominator was a hardcoded 24 ("one post per 2.5s"),
but this station's ISS (Transmitter 4) transmits every ~2.8125s -> only ~21.3
records/min are physically sent. Dividing a full-reception window (~21-22 records)
by 24 read ~88-92% and made reception look worse than it was. The fix sets the
denominator to the real physical rate (WU_RF_EXPECTED, default 21, env-overridable)
and caps the reported percentage at 100 via wu_pct().

Run:  python3 tests/test_reception_pct.py    OR    python3 -m pytest tests/
"""
import os
import sys

# Bypass the module's PID guard so importing it doesn't touch a running monitor.
sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402

CASES = []


def check(cond, label):
    CASES.append((bool(cond), label))
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")


def test_default_denominator_is_physical_rate():
    # 60 / 2.8125s = ~21.3; the fix rounds to 21 (was 24).
    check(wm.WU_RF_EXPECTED == 21,
          f"default denominator is the physical TX rate 21 (got {wm.WU_RF_EXPECTED})")


def test_full_reception_reads_near_100_not_92():
    # A 22-record window: old code -> 22/24 = 92%; fixed -> capped 100%.
    old_pct = 22 / 24 * 100
    check(round(old_pct) == 92, "sanity: the old /24 denominator read a full window as 92%")
    check(wm.wu_pct(22) == 100.0, "a 22-record window now reports 100% (capped), not 92%")
    check(round(wm.wu_pct(21)) == 100, "a 21-record window reports ~100%")


def test_pct_is_capped_at_100():
    check(wm.wu_pct(25) == 100.0, "an over-count window is capped at 100, never >100")
    check(wm.wu_pct(WU := wm.WU_RF_EXPECTED + 5) == 100.0, f"count {WU} caps at 100")


def test_partial_reception_is_proportional():
    # Half the physical packets -> ~50%.
    check(round(wm.wu_pct(wm.WU_RF_EXPECTED / 2)) == 50,
          "half the physical rate reports ~50%")
    check(wm.wu_pct(0) == 0.0, "zero records reports 0%")


def test_alert_threshold_now_means_real_loss():
    # 60% of the corrected denominator is a genuine, large packet loss.
    floor = wm.WU_RF_MIN_PCT / 100 * wm.WU_RF_EXPECTED
    check(floor < wm.WU_RF_EXPECTED * 0.65,
          f"alert floor ({floor:.1f} records/min) is a real >~35% loss vs the physical rate")


if __name__ == "__main__":
    for name in sorted(n for n in dir() if n.startswith("test_")):
        globals()[name]()
    passed = sum(1 for ok, _ in CASES if ok)
    print(f"\n{passed}/{len(CASES)} passed")
    sys.exit(0 if passed == len(CASES) else 1)
