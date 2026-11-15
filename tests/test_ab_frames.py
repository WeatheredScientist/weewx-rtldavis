"""Offline tests for ops/ab_frames.py, the DEC-0236 frame-pairing readout.

The readout decides whether the NAS receiver passes DEC-0236's bars. A wrong
pairing rule does not crash: it moves a coverage figure a decision rests on.

POSITIVE CONTROLS (DEC-0045, a passing test proves nothing if its assertion is wrong):

  * test_control_offset_correction_is_load_bearing: with a 1.5 s clock offset,
    pairing WITHOUT the offset step loses nearly every frame. If it ever stops
    doing so, the offset fixture has no teeth.
  * test_control_line_format_is_the_drivers: the log line the fixtures build must
    match the driver's own DATAPacket.IDENTIFIER, and the driver must still log
    `data: %s` at debug_rtld 2; otherwise the parser reads a format prod never writes.
"""

import gzip
import pathlib

import ab_frames as ab

PERIOD = 2.8125            # (41 + 4) / 16 s, ISS channel 5
DAY = "2026-11-21"


def _go(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return "%02d:%02d:%09.6f" % (h, m, s)


def _line(day, t, hexs, log_lag=0.003):
    lt = int(t + log_lag) % 86400
    return "%s %02d:%02d:%02d,105 user.rtldavis DEBUG data: %s %s 9 0 0 0\n" % (
        day, lt // 3600, lt % 3600 // 60, lt % 60, _go(t % 86400), hexs)


def _payload(i):
    return "%016X" % (0xE000000000000000 + i * 7919)


def _stream(n, start=3600.0, offset=0.0, drop=(), alter=(), day=DAY):
    out = []
    for i in range(n):
        if i in drop:
            continue
        hexs = _payload(i) if i not in alter else "%016X" % (0xA0 + i)
        out.append(_line(day, start + i * PERIOD + offset, hexs))
    return out


def test_bars_are_dec0236s():
    assert ab.COVERAGE_BAR == 0.90
    assert ab.DISAGREE_PER_10K_BAR == 1.0
    assert ab.MEM_BAR_MB == 200.0
    assert ab.PAIR_WINDOW_S == 1.0
    assert ab.OFFSET_WINDOW_S == 5.0


def test_control_line_format_is_the_drivers():
    import rtldavis
    line = _line(DAY, 3600.0, _payload(1))
    go_part = line.split(" data: ", 1)[1]
    assert rtldavis.DATAPacket.IDENTIFIER.match(go_part)
    assert rtldavis.DATAPacket.PATTERN.search(go_part)
    src = pathlib.Path(rtldavis.__file__).read_text()
    assert 'dbg_rtld(2, "data: %s" % lines[0])' in src


def test_identical_streams_pair_fully_with_zero_offset():
    side = ab.parse_lines(_stream(500))
    res = ab.pair(side.frames, side.frames)
    assert res.paired == 500 and not res.disagree
    assert res.coverage == 1.0 and res.offset == 0.0


def test_offset_is_measured_and_removed():
    prod = ab.parse_lines(_stream(500)).frames
    nas = ab.parse_lines(_stream(500, offset=1.5)).frames
    res = ab.pair(prod, nas)
    assert abs(res.offset - 1.5) < 1e-6
    assert res.paired == 500


def test_control_offset_correction_is_load_bearing(monkeypatch):
    prod = ab.parse_lines(_stream(500)).frames
    nas = ab.parse_lines(_stream(500, offset=1.5)).frames
    monkeypatch.setattr(ab, "estimate_offset", lambda p, n: (0.0, 0))
    res = ab.pair(prod, nas)
    assert res.paired < 25


def test_drops_count_against_coverage_both_ways():
    prod = ab.parse_lines(_stream(1000, drop=range(0, 1000, 50))).frames      # 20 lost
    nas = ab.parse_lines(_stream(1000, offset=0.2, drop=range(5, 1000, 10))).frames  # 100 lost
    res = ab.pair(prod, nas)
    assert res.prod_total == 980 and res.nas_total == 900
    assert res.paired == 880          # the 900 NAS frames minus the 20 prod also lost
    assert res.prod_only == 100 and res.nas_only == 20
    assert abs(res.coverage - 880 / 980) < 1e-9
    assert abs(res.reverse_coverage - 880 / 900) < 1e-9


def test_disagreement_is_found_and_listed():
    prod = ab.parse_lines(_stream(400)).frames
    nas = ab.parse_lines(_stream(400, offset=0.1, alter={17})).frames
    res = ab.pair(prod, nas)
    assert len(res.disagree) == 1 and res.paired == 399
    pf, nf = res.disagree[0]
    assert pf.hex == _payload(17) and nf.hex == "%016X" % (0xA0 + 17)
    assert abs(res.disagree_per_10k - 1e4 / 400) < 1e-9


def test_identical_bytes_win_over_a_nearer_garbage_frame():
    # A CRC-valid noise decode (ERR-0012's class) lands 0.05 s from prod's frame;
    # the real copy is 0.6 s away (after the 0.4 s offset is removed). The real
    # copy pairs; the noise is NAS-ONLY.
    prod = ab.parse_lines(_stream(50)).frames
    slot = 3600.0 + 20 * PERIOD
    garbage = _line(DAY, slot + 0.4 + 0.05, "%016X" % 0xBAD)
    late_real = _line(DAY, slot + 0.4 + 0.6, _payload(20))
    nas = ab.parse_lines(_stream(50, offset=0.4, drop={20}) + [garbage, late_real]).frames
    res = ab.pair(prod, nas)
    assert abs(res.offset - 0.4) < 1e-6
    assert res.paired == 50 and not res.disagree and res.nas_only == 1


def test_a_frame_two_slots_away_is_not_a_partner():
    # NAS lost slot 10 but has slot 11: slot 10 must be PROD-ONLY, not a disagreement.
    prod = ab.parse_lines(_stream(20)).frames
    nas = ab.parse_lines(_stream(20, drop={10})).frames
    res = ab.pair(prod, nas)
    assert res.prod_only == 1 and not res.disagree


def test_midnight_go_stamp_before_logged_after():
    # Go stamps 23:59:59.998, the logger writes it at 00:00:00 the next day.
    line = "2026-11-22 00:00:00,001 user.rtldavis DEBUG data: 23:59:59.998000 %s 9 0 0 0\n" % _payload(1)
    f = ab.parse_lines([line]).frames[0]
    assert ab._fmt(f.t) == "2026-11-21 23:59:59.998"


def test_duplicate_input_does_not_double_count():
    lines = _stream(100)
    assert len(ab.parse_lines(lines + lines).frames) == 100


def test_window_and_exclusion_apply_to_both_sides():
    side = ab.parse_lines(_stream(2000))           # 01:00 to about 02:33
    start = ab._when("%s 01:10" % DAY)
    end = ab._when("%s 02:00" % DAY)
    excl = [ab._window("%s 01:20,%s 01:30" % (DAY, DAY))]
    kept = ab.restrict(side, start, end, excl)
    assert all(start <= f.t < end for f in kept.frames)
    assert not any(excl[0][0] <= f.t < excl[0][1] for f in kept.frames)
    expected = round((40 * 60) / PERIOD)
    assert abs(len(kept.frames) - expected) <= 1


def test_stalls_and_restarts_are_counted():
    extra = [
        "%s 01:30:00,000 weewx.engine CRITICAL Caught WeeWxIOError: rtldavis process stalled\n" % DAY,
        "%s 01:31:00,000 user.rtldavis INFO rtldavis: US band, ISS channel 5, rain bucket 0, cmd x\n" % DAY,
    ]
    side = ab.parse_lines(_stream(10) + extra)
    assert len(side.stalls) == 1 and len(side.starts) == 1


def test_verdict_needs_memory_and_fails_on_stall():
    prod = ab.parse_lines(_stream(500)).frames
    res = ab.pair(prod, prod)
    clean = ab.Side(prod)
    assert ab.verdict(res, clean, None)[0] is False          # memory unread
    assert ab.verdict(res, clean, 150.0)[0] is True
    assert ab.verdict(res, clean, 250.0)[0] is False
    stalled = ab.Side(prod, stalls=[1.0])
    assert ab.verdict(res, stalled, 150.0)[0] is False


def test_verdict_fails_below_coverage_bar():
    prod = ab.parse_lines(_stream(1000)).frames
    nas = ab.parse_lines(_stream(1000, drop=range(0, 1000, 8))).frames  # 87.5 %
    res = ab.pair(prod, nas)
    assert res.coverage < ab.COVERAGE_BAR
    assert ab.verdict(res, ab.Side(nas), 150.0)[0] is False


def test_main_end_to_end_with_gz(tmp_path, capsys):
    p = tmp_path / "prod.log.gz"
    with gzip.open(p, "wt") as fh:
        fh.writelines(_stream(2000))
    n = tmp_path / "nas.log"
    n.write_text("".join(_stream(2000, offset=0.4, drop=range(0, 2000, 40))))
    rc = ab.main(["--prod", str(p), "--nas", str(n), "--start", "%s 01:00" % DAY,
                  "--end", "%s 03:00" % DAY, "--peak-mem-mb", "120"])
    out = capsys.readouterr().out
    assert rc == 0 and "verdict     PASS" in out
    assert "offset      +0.400 s" in out


def test_main_refuses_an_empty_side(tmp_path, capsys):
    p = tmp_path / "prod.log"
    p.write_text("".join(_stream(50)))
    n = tmp_path / "nas.log"
    n.write_text("%s 01:00:00,000 user.rtldavis INFO nothing here\n" % DAY)
    rc = ab.main(["--prod", str(p), "--nas", str(n), "--start", "%s 00:00" % DAY,
                  "--end", "%s 03:00" % DAY])
    assert rc == 2 and "debug_rtld 2" in capsys.readouterr().err
