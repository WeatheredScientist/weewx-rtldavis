"""Pin weewx.conf.example's diode-floor StdCalibrate lines (DEC-0080 radiation, DEC-0200 UV).

The example file is the versioned anti-regression artifact for both corrections (the live
weewx.conf is never committed, DEC-0012), so this evaluates each line the way weewx 5.5's
StdCalibrate does -- ``eval(compile(expr, 'StdCalibrate', 'eval'), {'math': math}, packet)``,
with only ``option_as_list(value)[0]`` kept as the expression -- over every code the driver
can emit, and asserts exactly which codes each line zeroes.
"""

import math
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "weewx.conf.example"
DRIVER = ROOT / "rtldavis.py"

# The driver's decodes (rtldavis.py): message type 4 and message type 6.
UV_DECODE = "uv_raw / 50.0"
SR_DECODE = "sr_raw * 1.757936"


def _corrections():
    """key -> expression for the [StdCalibrate] [[Corrections]] scalars, ConfigObj-style:
    an unquoted value loses its inline ' # comment'."""
    text = EXAMPLE.read_text()
    section = text.split("[StdCalibrate]", 1)[1].split("[[Corrections]]", 1)[1]
    section = re.split(r"^\s*\[", section, maxsplit=1, flags=re.M)[0]
    out = {}
    for line in section.splitlines():
        m = re.match(r"^\s*(\w+)\s*=\s*(.*?)\s*(#.*)?$", line)
        if m and not line.lstrip().startswith("#"):
            out[m.group(1)] = m.group(2)
    return out


def _apply(expr, obs_type, value):
    """One StdCalibrate LOOP-packet application, as weewx 5.5 does it."""
    packet = {obs_type: value}
    return eval(compile(expr, "StdCalibrate", "eval"), {"math": math}, packet)


def _zeroed_codes(expr, obs_type, decode, codes):
    return {code for code in codes
            if (v := decode(code)) != _apply(expr, obs_type, v)}


def test_driver_decodes_are_the_ones_this_test_assumes():
    src = DRIVER.read_text()
    assert UV_DECODE in src
    assert SR_DECODE in src


@pytest.mark.parametrize("obs_type", ["radiation", "UV"])
def test_line_present_and_survives_configobj_list_split(obs_type):
    # weewx keeps only option_as_list(value)[0]; ConfigObj turns an unquoted value
    # with a comma into a list, which would silently truncate the expression.
    expr = _corrections()[obs_type]
    assert "," not in expr


def test_uv_line_zeroes_exactly_codes_1_and_2():
    expr = _corrections()["UV"]
    codes = range(0, 0x3FF)                        # 0x3FF = no sensor, never decoded
    assert _zeroed_codes(expr, "UV", lambda c: c / 50.0, codes) == {1, 2}


def test_radiation_line_zeroes_exactly_code_1():
    expr = _corrections()["radiation"]
    codes = range(0, 0x3FE)                        # 0x3FE/0x3FF never decoded
    assert _zeroed_codes(expr, "radiation", lambda c: c * 1.757936, codes) == {1}


@pytest.mark.parametrize("obs_type", ["radiation", "UV"])
def test_none_passes_through(obs_type):
    assert _apply(_corrections()[obs_type], obs_type, None) is None


@pytest.mark.parametrize("obs_type", ["radiation", "UV"])
def test_absent_field_raises_the_name_error_weewx_swallows(obs_type):
    # Most LOOP packets carry neither field (ISS message rotation); StdCalibrate
    # catches this NameError and leaves the packet untouched.
    expr = _corrections()[obs_type]
    with pytest.raises(NameError):
        eval(compile(expr, "StdCalibrate", "eval"), {"math": math}, {})


def test_zeroed_value_is_numeric_zero():
    assert _apply(_corrections()["UV"], "UV", 2 / 50.0) == 0
    assert _apply(_corrections()["UV"], "UV", 3 / 50.0) == pytest.approx(0.06)
