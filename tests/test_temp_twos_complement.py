"""Signed (two's complement) decode of the outside-temperature message (S54, R1).

THE BUG THIS FIXES
------------------
rtldavis.py decoded the 12-bit digital temperature field as UNSIGNED. Davis
encodes it as two's complement (confirmed against the sibling weewx-meteostick
driver and the DavisRFM69 protocol notes), so every sub-0 F reading came back
as ~+400 F. Consequence chain on the first hard freeze:

  -5.0 F  ->  raw 0xFCE  ->  unsigned 404.6 F = 207 C
          ->  SensorQC bounds (-40..65 C) trip
          ->  DEC-0054 co-rejects the WHOLE frame (wind + payload nulled)

i.e. genuine cold weather would read as positive proof of RF corruption and
blind the station for the duration of the cold snap. It had never fired only
because the station has not yet seen a winter (ops#105 audit, weewx S53).

DEVIATION FROM METEOSTICK (deliberate, one LSB)
-----------------------------------------------
meteostick uses -(temp_raw ^ 0xFFF)/10.0, which is ONE's complement: it maps
both 0xFFF and 0x000 to 0.0 F and cannot represent -0.1 F. We subtract 4096
(true two's complement), which is exact and keeps the truncation bias uniform
across zero. test_minus_point_one_is_representable is the case that
distinguishes the two.

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing the driver (same pattern as
test_parse_raw_channel).

Run:  python3 -m pytest tests/ (pytest only)
"""


def _FtoC(f):
    return (f - 32.0) * 5.0 / 9.0


from rtldavis import RtldavisDriver, SensorQC  # noqa: E402
from conftest import DEFAULT_CHANNELS  # noqa: E402


class _FakeDriver:
    """Minimal stand-in carrying only what parse_raw reads: the channel map.
    Only the ISS is present, so a type-8 frame on channel 1 lands in
    data['temperature'] rather than temp_1/temp_2."""
    channels = dict(DEFAULT_CHANNELS)


def _temp_frame(temp_raw, digital=True):
    """Build a type-8 (outside temperature) ISS frame carrying temp_raw.

    Layout the driver reads: temp_raw = (pkt[3] << 4) + (pkt[4] >> 4),
    digital-sensor flag = pkt[4] & 0x8.
    """
    b3 = (temp_raw >> 4) & 0xFF
    b4 = ((temp_raw & 0xF) << 4) | (0x8 if digital else 0x0)
    return bytearray([0x80, 0, 0, b3, b4, 0, 0, 0])


def _decode(temp_raw):
    """Return data['temperature'] (deg C) for a digital frame, or None."""
    pkt = _temp_frame(temp_raw)
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)
    return data.get('temperature')


def _f(temp_c):
    return temp_c * 9.0 / 5.0 + 32.0


def test_frame_builder_roundtrips():
    """Positive control: the helper really produces the raw value it claims,
    and sets the digital flag -- otherwise every assertion below is vacuous."""
    for raw in (0x000, 0x0FA, 0xE70, 0xFCE, 0xFF8, 0xFFC, 0xFFF):
        pkt = _temp_frame(raw)
        assert (pkt[3] << 4) + (pkt[4] >> 4) == raw
        assert pkt[4] & 0x8


def test_positive_temp_unchanged():
    """Regression guard: the fix must not disturb above-zero readings.
    0x0FA = 250 tenths = 25.0 F."""
    assert abs(_f(_decode(0x0FA)) - 25.0) < 1e-9


def test_zero_is_zero():
    assert abs(_f(_decode(0x000)) - 0.0) < 1e-9


def test_negative_temp_decodes_signed():
    """0xFCE = 4046; as 12-bit two's complement 4046 - 4096 = -50 -> -5.0 F.
    Decoded unsigned (the bug) this was 404.6 F."""
    assert abs(_f(_decode(0xFCE)) - (-5.0)) < 1e-9


def test_hard_freeze_decodes_signed():
    """0xE70 = 3696 -> 3696 - 4096 = -400 -> -40.0 F (= -40.0 C)."""
    assert abs(_f(_decode(0xE70)) - (-40.0)) < 1e-9


def test_minus_point_one_is_representable():
    """The case that distinguishes true two's complement from meteostick's
    one's complement: 0xFFF is -1 tenth = -0.1 F, NOT 0.0 F."""
    assert abs(_f(_decode(0xFFF)) - (-0.1)) < 1e-9


def test_sentinel_ffc_emits_nothing():
    """0xFFC = the long-standing 'no sensor' sentinel."""
    assert _decode(0xFFC) is None


def test_sentinel_ff8_emits_nothing():
    """0xFF8 = the second 'no sensor' sentinel this fix adds (meteostick
    checks it; our fork and upstream lheijst did not). Decoded as a signed
    value it would have become a plausible-looking -0.8 F."""
    assert _decode(0xFF8) is None


def test_subzero_frame_does_not_trip_bounds():
    """DEC-0054 co-rejection non-fire assertion.

    frame_corrupt is set when check_bounds() returns a reason for ANY field,
    which then nulls every same-frame weather key. A genuine sub-0 F reading
    must not do that. Sweeps the whole realistic cold range, not one point."""
    qc = SensorQC()
    for temp_f in (-0.1, -5.0, -10.0, -20.0, -39.9):
        raw = (int(round(temp_f * 10)) + 0x1000) & 0xFFF
        temp_c = _decode(raw)
        assert temp_c is not None, "raw 0x%03X decoded to None" % raw
        assert qc.check_bounds('temperature', temp_c) is None, (
            "%.1f F (raw 0x%03X, %.2f C) tripped bounds -> would co-reject "
            "the frame" % (temp_f, raw, temp_c))


def test_unsigned_decode_would_have_tripped_bounds():
    """Positive control on the test above: prove the bounds gate really does
    fire on the OLD unsigned decode, so the non-fire assertion is meaningful
    rather than testing a gate that never trips."""
    qc = SensorQC()
    unsigned_c = _FtoC(0xFCE / 10.0)              # the pre-fix -5.0 F path
    assert unsigned_c > 200.0
    assert qc.check_bounds('temperature', unsigned_c) is not None
