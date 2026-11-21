# SPDX-License-Identifier: GPL-3.0-or-later
"""weewx.conf.example ships every uploader off (DEC-0240, #587; source file corrected by DEC-0244).

weewx.conf.example is the full reference config that users copy sections from. It is NOT what the
image seeds: that starter is written by `weectl station create` at build time (#596), and
tests/test_starter_services.py plus scripts/smoke_image.sh cover it. A section copied from here
must not post until the user turns it on. weewx.restx.get_site_dict treats a section with no
'enable' key as on, so each section carries an explicit false.
"""
import os
import shutil

import pytest

configobj = pytest.importorskip("configobj")
import seed_config  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARTER = os.path.join(REPO, "weewx.conf.example")

# restful_services entry -> its [StdRESTful] section. A new uploader added to restful_services
# without a row here fails test_every_restful_service_has_a_known_section, on purpose.
SECTIONS = {
    "weewx.restx.StdStationRegistry": "StationRegistry",
    "weewx.restx.StdWunderground": "Wunderground",
    "weewx.restx.StdPWSweather": "PWSweather",
    "weewx.restx.StdCWOP": "CWOP",
    "weewx.restx.StdWOW": "WOW",
    "weewx.restx.StdWOWBE": "WOW-BE",
    "weewx.restx.StdAWEKAS": "AWEKAS",
    "user.wcloud.WeatherCloud": "WeatherCloud",
    "user.windy.Windy": "Windy",
    "user.owm.OWM": "OWM",
    "user.influx.Influx": "Influx",
    "user.ogoxeUploader.OgoxeUploader": "OgoxeUploader",
}


def restful_services(conf):
    raw = conf["Engine"]["Services"]["restful_services"]
    return [raw] if isinstance(raw, str) else list(raw)


def assert_all_off(conf):
    rest = conf["StdRESTful"]
    for service in restful_services(conf):
        section = SECTIONS[service]
        assert section in rest, "%s has no [[%s]] section" % (service, section)
        if section == "StationRegistry":
            assert rest[section].as_bool("register_this_station") is False
            continue
        assert "enable" in rest[section], \
            "[[%s]] has no enable line, which weewx reads as on" % section
        assert rest[section].as_bool("enable") is False, "[[%s]] ships enabled" % section


def test_every_restful_service_has_a_known_section():
    conf = configobj.ConfigObj(STARTER, encoding="utf-8", file_error=True)
    unknown = [s for s in restful_services(conf) if s not in SECTIONS]
    assert not unknown, "add these to SECTIONS: %s" % unknown


def test_starter_ships_every_uploader_off():
    assert_all_off(configobj.ConfigObj(STARTER, encoding="utf-8", file_error=True))


def test_every_stdrestful_section_is_off_even_if_not_in_restful_services():
    rest = configobj.ConfigObj(STARTER, encoding="utf-8", file_error=True)["StdRESTful"]
    for name in rest.sections:
        if name == "StationRegistry":
            continue
        assert rest[name].as_bool("enable") is False, "[[%s]] ships enabled" % name


def test_seeding_keeps_every_uploader_off(tmp_path):
    dist, data = tmp_path / "dist", tmp_path / "data"
    dist.mkdir()
    shutil.copy(STARTER, dist / "weewx.conf")
    env = {"WEEWX_DRIVER": "simulator", "WEEWX_LATITUDE": "40.0", "WEEWX_LONGITUDE": "-75.0",
           "WEEWX_ALTITUDE": "100,foot", "WEEWX_LOCATION": "Test", "RTLDAVIS_BAND": "US"}
    lines = []
    assert seed_config.seed(str(data), str(dist), env, out=lines.append) == 0
    assert any("no uploader posts until configured" in line for line in lines)
    assert_all_off(configobj.ConfigObj(str(data / "weewx.conf"), encoding="utf-8"))
