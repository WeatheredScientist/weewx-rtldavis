"""Offline regression test for the pct_good_all deadlock (S24, finding H2).

The bug (H2): _update_summaries computed the overall reception metric under
    if total_max_count > 0 and self.stats['pct_good_all'] is not None:
        self.stats['pct_good_all'] = 100.0 * total_count / total_max_count
but _init_stats and _reset_stats set pct_good_all to None every archive period,
so the guard could never pass. pct_good_all stayed None forever, and
new_archive_record therefore never wrote event.record['rxCheckPercent'] -- the
driver's native reception metric was silently dead.

These tests drive the REAL _update_summaries / _reset_stats / new_archive_record
across two archive periods and assert the metric is actually produced. They fail
on the pre-fix code (pct_good_all stays None) and pass after.

weewx is not installed in the test/CI environment, so we stub it (same pattern
as test_rain_filter / test_parse_raw_channel).

Run:  python3 -m pytest tests/ (pytest only)
"""
import time
import types

from rtldavis import RtldavisDriver  # noqa: E402
from conftest import make_driver  # noqa: E402


_make_driver = make_driver


def _run_period(d, curr_cnt0, period_s=60):
    """Simulate one archive period that received curr_cnt0 messages since
    startup, spanning period_s seconds, and close it via _update_summaries.

    S120/#317: the denominator is now slot-count (last_pkt_ts - prev_pkt_ts),
    not wall-clock last_ts. These tests never drive the real per-packet
    _update_stats(), so last_pkt_ts/prev_pkt_ts are seeded directly here to
    span period_s -- matching what a real receiver spanning that period would
    have produced via _update_stats().
    """
    d.stats['curr_cnt'][0] = curr_cnt0
    # backdate last_ts so _update_summaries sees a real elapsed period
    if d.stats['last_ts'] > 0:
        now = time.time()
        d.stats['last_ts'] = int(now) - period_s
        d.stats['prev_pkt_ts'][0] = now - period_s
        d.stats['last_pkt_ts'][0] = now
    RtldavisDriver._update_summaries(d)


def test_pct_good_all_is_computed_after_a_valid_period():
    d = _make_driver()
    # Period 1: first data since startup -> establishes the baseline count.
    _run_period(d, curr_cnt0=20)
    RtldavisDriver._reset_stats(d)          # normal end-of-period reset
    # Period 2: 20 more messages received over ~60s.
    _run_period(d, curr_cnt0=40)
    assert d.stats['pct_good_all'] is not None, \
        "pct_good_all stayed None -> the H2 deadlock is still present"
    assert 0 < d.stats['pct_good_all'] <= 200


def test_new_archive_record_stores_rxCheckPercent():
    d = _make_driver()
    _run_period(d, curr_cnt0=20)
    RtldavisDriver._reset_stats(d)
    # Second period arrives as a NEW_ARCHIVE_RECORD event.
    d.stats['curr_cnt'][0] = 40
    now = time.time()
    d.stats['last_ts'] = int(now) - 60
    d.stats['prev_pkt_ts'][0] = now - 60  # S120/#317: slot-count baseline
    d.stats['last_pkt_ts'][0] = now
    event = types.SimpleNamespace(record={'dateTime': int(time.time()),
                                           'usUnits': 16})
    RtldavisDriver.new_archive_record(d, event)
    assert 'rxCheckPercent' in event.record, \
        "rxCheckPercent was not written -> driver reception metric still dead"
    assert event.record['rxCheckPercent'] is not None
