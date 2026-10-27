"""Rain recovery after a rejected counter reading (#465, DEC-0218).

The driver resyncs its rain baseline to every reading, even a rejected one, so a
rejected step can never freeze it (DEC-0029, DEC-0103). The cost was a phantom on
recovery: 115 -> 114 -> 115 rejected the 114, then booked the climb back as 1 tip,
up to MAX_PLAUSIBLE_TIPS for a 16-tip dip. The fix judges each reading first
against the last ACCEPTED count, then falls back to the old check.

Two layers:
  * named sequences through the real `_data_to_packet` -- the first four fail on
    the pre-fix driver with the phantom they describe (proved at S160);
  * the exhaustive comparison behind the DEC, on the pure helper, so the claim
    "fixes every glitch-and-recover case, changes nothing for storm jumps, costs
    only low-count resets" is checked, not argued.

conftest.py imports rtldavis against its superset weewx fake, so no stub here.
"""
from rtldavis import (MAX_PLAUSIBLE_TIPS, RtldavisDriver, SensorQC,
                      rain_delta_tips)

TIP = 0.2   # mm per tip on the bare driver below


def _driver():
    drv = RtldavisDriver.__new__(RtldavisDriver)  # skip __init__ (ProcManager)
    drv.sensor_map = dict(RtldavisDriver.DEFAULT_SENSOR_MAP)
    drv.last_rain_count = None
    drv.last_accepted_rain_count = None
    drv.rain_per_tip = TIP
    drv._sensor_qc_enabled = True
    drv._sensor_qc = SensorQC()
    return drv


def _rain(counts):
    drv = _driver()
    return [drv._data_to_packet({'rain_count': c})['rain'] for c in counts]


# --- named sequences through _data_to_packet --------------------------------

def test_one_tip_dip_and_recovery_books_nothing():
    # pre-fix: [0.0, None, 0.2] -- the climb back to 115 booked as rain
    assert _rain([115, 114, 115]) == [0.0, None, 0.0]


def test_cap_sized_dip_and_recovery_books_nothing():
    # pre-fix: the climb back booked 16 tips, MAX_PLAUSIBLE_TIPS, 0.16"
    assert MAX_PLAUSIBLE_TIPS == 16
    assert _rain([115, 99, 115]) == [0.0, None, 0.0]


def test_dip_then_real_rain_books_only_the_real_tips():
    # truth went 115 -> 117; the 110 was a glitch. pre-fix booked 7 tips.
    assert _rain([115, 110, 117]) == [0.0, None, 2 * TIP]


def test_dip_across_the_wrap_and_recovery_books_nothing():
    # 2 -> 125 is +123 (a high-bit spike), rejected; back to 2 must book 0.
    # pre-fix read 125 -> 2 as a 127 -> 0 wraparound and booked 5 tips.
    assert _rain([2, 125, 2]) == [0.0, None, 0.0]


def test_storm_jump_over_the_cap_books_as_before():
    # a real 20-tip jump is rejected (lost, DEC-0056), then progress resumes
    # from the new count -- unchanged by DEC-0218
    assert _rain([100, 120, 122]) == [0.0, None, 2 * TIP]


def test_reset_to_zero_resumes_as_before():
    # ISS power cycle from a mid count: 50 -> 0 rejected, then 0 and 3 count
    assert _rain([50, 0, 0, 3]) == [0.0, None, 0.0, 3 * TIP]


def test_repeated_rejects_never_stall():
    # 114 and 90 are both rejected; 91 is plausible against 90 (the old
    # check), so it is accepted -- the fallback keeps DEC-0103's no-stall
    assert _rain([115, 114, 90, 91]) == [0.0, None, None, 1 * TIP]


def test_anchor_tracks_accepted_counts_only():
    drv = _driver()
    drv._data_to_packet({'rain_count': 115})
    drv._data_to_packet({'rain_count': 114})            # rejected
    assert drv.last_rain_count == 114, "baseline still resyncs (DEC-0103)"
    assert drv.last_accepted_rain_count == 115
    drv._data_to_packet({'rain_count': 116})            # 1 tip vs the anchor
    assert drv.last_rain_count == drv.last_accepted_rain_count == 116


def test_corrupt_frame_moves_neither_baseline():
    # DEC-0054's co-rejection path is untouched: a proven-corrupt frame's
    # counter changes neither the resync baseline nor the anchor
    drv = _driver()
    drv._data_to_packet({'rain_count': 10})
    p = drv._data_to_packet({'humidity': 144.9, 'rain_count': 77})
    assert p['rain'] is None
    assert drv.last_rain_count == drv.last_accepted_rain_count == 10


# --- the exhaustive comparison behind DEC-0218 --------------------------------

def _rejected_pairs():
    for anchor in range(128):
        for x in range(128):
            if rain_delta_tips(anchor, x) is None:
                yield anchor, x


def test_every_glitch_and_recovery_books_the_true_tips():
    from rtldavis import rain_tips_with_anchor
    cases = 0
    for anchor, x in _rejected_pairs():
        for k in range(MAX_PLAUSIBLE_TIPS + 1):
            y = (anchor + k) % 128
            assert rain_tips_with_anchor(anchor, x, y)[0] == k, (anchor, x, y)
            cases += 1
    assert cases == 241536


def test_storm_jumps_book_exactly_as_before():
    from rtldavis import rain_tips_with_anchor
    for anchor, x in _rejected_pairs():
        if not 17 <= (x - anchor) % 128 <= 60:
            continue
        for k in range(MAX_PLAUSIBLE_TIPS + 1):
            y = (x + k) % 128
            assert rain_tips_with_anchor(anchor, x, y)[0] == rain_delta_tips(x, y)


def test_only_low_count_resets_differ_from_before():
    # the documented cost: a real reset to 0-2 from an anchor of 18 or less,
    # with rain climbing back within the cap of the old count
    from rtldavis import rain_tips_with_anchor
    differ = []
    for anchor, x in _rejected_pairs():
        if x > 2:
            continue
        for k in range(MAX_PLAUSIBLE_TIPS + 1):
            y = (x + k) % 128
            if rain_tips_with_anchor(anchor, x, y)[0] != rain_delta_tips(x, y):
                differ.append(anchor)
    assert len(differ) == 408
    assert max(differ) == 18


def test_accepts_everything_the_old_check_accepts():
    # superset: the anchor path only ever adds acceptances, so no stall
    from rtldavis import rain_tips_with_anchor
    for anchor in range(0, 128, 3):
        for prev in range(128):
            for new in range(128):
                if rain_delta_tips(prev, new) is not None:
                    assert rain_tips_with_anchor(anchor, prev, new)[0] is not None


def test_no_pending_reject_is_the_old_check():
    from rtldavis import rain_tips_with_anchor
    for c in range(128):
        for new in range(128):
            assert rain_tips_with_anchor(c, c, new) == (rain_delta_tips(c, new), False)
    assert rain_tips_with_anchor(None, None, 42) == (0, False)   # cold start
