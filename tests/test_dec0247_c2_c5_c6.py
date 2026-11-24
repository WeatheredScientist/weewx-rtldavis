"""DEC-0247: three outside-review fixes (C2 process sweep, C5 message-9 channel gate, C6 thermistor).

Each test here fails on the pre-fix driver; the red/green evidence is in the PR.

weewx is not installed in CI; tests/conftest.py supplies the shared fake. Run: pytest only.
"""
import signal
from unittest import mock

import rtldavis as R
from rtldavis import RtldavisDriver, calculate_thermistor_temp


# --- C2: the sweep keeps going and the owned child is always reaped -------------------

def _manager():
    pm = R.ProcManager()
    pm._cmd = "rtldavis -x"
    pm.stderr_reader = mock.Mock()
    pm.stdout_reader = mock.Mock()
    pm._process = mock.Mock()
    return pm


def test_shutdown_survives_a_pid_that_vanished_and_still_reaps_the_child():
    pm = _manager()
    killed = []

    def fake_kill(pid, sig):
        if pid == 111:
            raise ProcessLookupError  # exited between pidof and kill
        killed.append((pid, sig))

    with mock.patch.object(R.ProcManager, 'get_pid', return_value=[111, 222]), \
         mock.patch.object(R.os, 'kill', side_effect=fake_kill):
        pm.shutdown()

    assert killed == [(222, signal.SIGKILL)], "the sweep must go on to the next PID"
    pm._process.kill.assert_called_once()
    pm._process.wait.assert_called_once()


def test_startup_kills_the_remaining_pids_when_one_vanished():
    pm = R.ProcManager()
    killed = []

    def fake_kill(pid, sig):
        if pid == 111:
            raise ProcessLookupError
        killed.append(pid)

    with mock.patch.object(R.ProcManager, 'get_pid', return_value=[111, 222]), \
         mock.patch.object(R.os, 'kill', side_effect=fake_kill), \
         mock.patch.object(R.subprocess, 'Popen'), \
         mock.patch.object(R, 'AsyncReader'), \
         mock.patch.object(R, 'reap_spawned_children', return_value=0):
        pm.startup("rtldavis -x")

    assert killed == [222]


def test_shutdown_still_kills_every_live_pid():
    """Positive control: with no failure every PID is signaled."""
    pm = _manager()
    killed = []
    with mock.patch.object(R.ProcManager, 'get_pid', return_value=[111, 222]), \
         mock.patch.object(R.os, 'kill', side_effect=lambda p, s: killed.append(p)):
        pm.shutdown()
    assert killed == [111, 222]


# --- C5: message 9 is gated on the wind channel like message 1 ------------------------

class _IssOnly:
    channels = {'iss': 1, 'anemometer': 0, 'leaf_soil': 0,
                'temp_hum_1': 5, 'temp_hum_2': 0, 'wind_channel': 1}


class _SeparateAnemometer:
    channels = {'iss': 1, 'anemometer': 2, 'leaf_soil': 0,
                'temp_hum_1': 5, 'temp_hum_2': 0, 'wind_channel': 2}


def _msg9(chan, gust_mph=40):
    return bytearray([0x90 | ((chan - 1) & 0x7), 0, 0, gust_mph, 0, 0, 0, 0])


def test_gust10_published_from_iss_when_iss_carries_the_wind():
    data = RtldavisDriver.parse_raw(_IssOnly(), _msg9(1))
    assert abs(data['wind_gust_10'] - 40 * R.MPH_TO_MPS) < 1e-9


def test_gust10_published_from_a_separate_anemometer_channel():
    data = RtldavisDriver.parse_raw(_SeparateAnemometer(), _msg9(2))
    assert abs(data['wind_gust_10'] - 40 * R.MPH_TO_MPS) < 1e-9


def test_gust10_not_published_from_the_iss_when_an_anemometer_owns_the_wind():
    data = RtldavisDriver.parse_raw(_SeparateAnemometer(), _msg9(1))
    assert 'wind_gust_10' not in data


def test_gust10_not_published_from_another_channel():
    for d in (_IssOnly(), _SeparateAnemometer()):
        assert 'wind_gust_10' not in RtldavisDriver.parse_raw(d, _msg9(5))


# --- C6: a failed thermistor decode is no reading, never 24 C -------------------------

class _WithLeafSoil:
    channels = {'iss': 1, 'anemometer': 0, 'leaf_soil': 3,
                'temp_hum_1': 5, 'temp_hum_2': 6, 'wind_channel': 1}


def _out_temp(chan, raw12):
    """Message 8 analog (pkt[4] bit 3 clear): 12-bit raw in pkt[3], pkt[4] high nibble."""
    return bytearray([0x80 | ((chan - 1) & 0x7), 0, 0, raw12 >> 4, (raw12 & 0xF) << 4, 0, 0, 0])


def test_thermistor_failure_returns_none_not_a_temperature():
    assert calculate_thermistor_temp(0) is None        # divide by zero
    assert calculate_thermistor_temp(1005) is None     # log of a negative resistance


def test_thermistor_normal_value_still_decodes():
    assert 30.0 < calculate_thermistor_temp(256) < 40.0


def test_failed_analog_outside_temp_is_omitted_on_every_channel():
    for chan, key in ((1, 'temperature'), (5, 'temp_1'), (6, 'temp_2')):
        for raw12 in (0, 4020):  # raw/4 = 0 and 1005
            data = RtldavisDriver.parse_raw(_WithLeafSoil(), _out_temp(chan, raw12))
            assert key not in data, (chan, raw12, data.get(key))


def test_good_analog_outside_temp_is_published():
    data = RtldavisDriver.parse_raw(_WithLeafSoil(), _out_temp(1, 1024))  # raw/4 = 256
    assert 30.0 < data['temperature'] < 40.0


def _leaf_soil(subtype, temp_raw, pot_byte=0x20):
    """Message F from channel 3, sensor 1. temp_raw is the 10-bit thermistor field."""
    return bytearray([0xF2, subtype, pot_byte, temp_raw >> 2, 0, (temp_raw & 3) << 6, 0, 0])


def test_failed_soil_thermistor_drops_the_temp_and_the_moisture_it_would_compensate():
    data = RtldavisDriver.parse_raw(_WithLeafSoil(), _leaf_soil(1, 0))
    assert 'soil_temp_1' not in data
    assert 'soil_moisture_1' not in data


def test_good_soil_thermistor_still_gives_temp_and_moisture():
    data = RtldavisDriver.parse_raw(_WithLeafSoil(), _leaf_soil(1, 256))
    assert 'soil_temp_1' in data and 'soil_moisture_1' in data


def test_failed_leaf_thermistor_drops_the_temp_but_keeps_wetness():
    """Leaf wetness is not temperature-compensated (norm_fact 0.0), so the failed
    temperature costs only itself."""
    data = RtldavisDriver.parse_raw(_WithLeafSoil(), _leaf_soil(2, 0))
    assert 'leaf_temp_1' not in data
    assert 'leaf_wetness_1' in data
