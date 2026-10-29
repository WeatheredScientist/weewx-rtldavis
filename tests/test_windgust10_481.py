"""#481 / DEC-0224: message 9's 10-minute gust reaches the packet as windGust10.

The driver used to decode message type 9 and only log it. It now stores the value in
m/s as `wind_gust_10`, maps it to WeeWX's `windGust10` (never `windGust`: the value is a
10-minute maximum, and `windGust` feeds the archive's gust max), registers the unit
group the observation lacks so US conversion yields `windGust10_mph`, and bounds-checks
it like wind speed. The (0, 0) "no sensor" frame stays silent.
"""
import pytest

import rtldavis
from rtldavis import MPH_TO_MPS, RtldavisDriver, SensorQC
from conftest import DEFAULT_CHANNELS  # noqa: E402

CHANNELS = dict(DEFAULT_CHANNELS)


class _Parser:
    channels = CHANNELS


def _msg9(gust_mph, index=0):
    # message 9 on channel 1: pkt[0] = 0x90, gust in pkt[3], index in pkt[5] high nibble
    return bytearray([0x90, 0, 0, gust_mph, 0, index << 4, 0, 0])


def _parse(pkt):
    return RtldavisDriver.parse_raw(_Parser(), pkt)


def _bare_driver():
    drv = RtldavisDriver.__new__(RtldavisDriver)
    drv.sensor_map = dict(RtldavisDriver.DEFAULT_SENSOR_MAP)
    drv.last_rain_count = None
    drv.last_accepted_rain_count = None
    drv.rain_per_tip = 0.2
    drv._sensor_qc_enabled = True
    drv._sensor_qc = SensorQC()
    return drv


def test_message_9_decodes_to_metric_gust():
    data = _parse(_msg9(13, index=2))
    assert data['wind_gust_10'] == pytest.approx(13 * MPH_TO_MPS)


def test_message_9_no_sensor_frame_stays_silent():
    assert 'wind_gust_10' not in _parse(_msg9(0, index=0))


def test_default_sensor_map_carries_windgust10_and_never_windgust():
    assert RtldavisDriver.DEFAULT_SENSOR_MAP['windGust10'] == 'wind_gust_10'
    assert 'windGust' not in RtldavisDriver.DEFAULT_SENSOR_MAP


def test_packet_carries_windgust10():
    pkt = _bare_driver()._data_to_packet({'wind_gust_10': 13 * MPH_TO_MPS})
    assert pkt['windGust10'] == pytest.approx(13 * MPH_TO_MPS)
    assert 'windGust' not in pkt


def test_unit_group_registered_so_us_conversion_names_it_mph():
    units = rtldavis.weewx.units
    assert units.obs_group_dict['windGust10'] == 'group_speed'


def test_impossible_gust_is_nulled():
    pkt = _bare_driver()._data_to_packet({'wind_gust_10': 201 * MPH_TO_MPS})
    assert pkt['windGust10'] is None


def test_gust_at_the_spec_limit_passes():
    assert SensorQC().check('wind_gust_10', 89.4, 0.0)[1] is None


def test_condemned_frame_takes_the_gust_with_it():
    pkt = _bare_driver()._data_to_packet({'wind_gust_10': 10 * MPH_TO_MPS,
                                          'humidity': 144.9})
    assert pkt['windGust10'] is None
