"""seed_config.py: first-start seeding of an empty data mount (DEC-0225).

The promise the image makes: an existing weewx.conf is never touched, an empty mount gets a full
starter tree, and a bad first-run value stops the start before anything is written.

Run:  python3 -m pytest tests/ (pytest only)
"""
import os
import stat
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

configobj = pytest.importorskip("configobj")
import seed_config  # noqa: E402

DIST_CONF = """\
# starter config
[Station]
    station_type = Rtldavis
    location = "YOUR_STATION_NAME"
    latitude = YOUR_LATITUDE
    longitude = YOUR_LONGITUDE
    altitude = YOUR_ALTITUDE, foot    # Choose 'foot' or 'meter'
[Rtldavis]
    cmd = /usr/local/bin/rtldavis -gain 0
    transceiver_frequency = US
    iss_channel = 1
    rain_bucket_type = 0
[Simulator]
    loop_interval = 2.5
    driver = weewx.drivers.simulator
"""


@pytest.fixture
def dirs(tmp_path):
    dist = tmp_path / "dist"
    (dist / "bin" / "user").mkdir(parents=True)
    (dist / "weewx.conf").write_text(DIST_CONF)
    (dist / "bin" / "user" / "extensions.py").write_text("# stock\n")
    data = tmp_path / "data"
    data.mkdir()
    return str(data), str(dist)


def run(dirs, env=None):
    lines = []
    code = seed_config.seed(dirs[0], dirs[1], env or {}, out=lines.append)
    return code, lines


def test_empty_mount_gets_the_starter_tree(dirs):
    code, lines = run(dirs, {"WEEWX_LATITUDE": "40.7", "WEEWX_LONGITUDE": "-74.0"})
    assert code == 0
    assert os.path.exists(os.path.join(dirs[0], "weewx.conf"))
    assert os.path.exists(os.path.join(dirs[0], "bin", "user", "extensions.py"))
    assert any("was empty" in ln for ln in lines)


def test_seeded_config_is_private(dirs):
    run(dirs)
    mode = stat.S_IMODE(os.stat(os.path.join(dirs[0], "weewx.conf")).st_mode)
    assert mode == 0o600


def test_existing_config_is_never_touched(dirs):
    conf = os.path.join(dirs[0], "weewx.conf")
    with open(conf, "w") as f:
        f.write("# mine\n")
    code, lines = run(dirs, {"WEEWX_LATITUDE": "40.7"})
    assert code == 0
    assert lines == []
    assert open(conf).read() == "# mine\n"
    assert not os.path.exists(os.path.join(dirs[0], "bin"))


def test_existing_files_survive_seeding(dirs):
    archive = os.path.join(dirs[0], "archive")
    os.makedirs(archive)
    with open(os.path.join(archive, "weewx.sdb"), "w") as f:
        f.write("data")
    stock = os.path.join(dirs[0], "bin", "user")
    os.makedirs(stock)
    with open(os.path.join(stock, "extensions.py"), "w") as f:
        f.write("# mine\n")
    run(dirs)
    assert open(os.path.join(archive, "weewx.sdb")).read() == "data"
    assert open(os.path.join(stock, "extensions.py")).read() == "# mine\n"


def test_environment_values_land_in_the_config_with_comments_kept(dirs):
    env = {
        "WEEWX_LOCATION": "My Back Yard",
        "WEEWX_LATITUDE": "40.7",
        "WEEWX_LONGITUDE": "-74.0",
        "WEEWX_ALTITUDE": "120,foot",
        "RTLDAVIS_BAND": "eu",
        "RTLDAVIS_ISS_CHANNEL": "3",
        "RTLDAVIS_RAIN_BUCKET": "1",
    }
    code, lines = run(dirs, env)
    assert code == 0
    text = open(os.path.join(dirs[0], "weewx.conf")).read()
    conf = configobj.ConfigObj(os.path.join(dirs[0], "weewx.conf"))
    assert conf["Station"]["location"] == "My Back Yard"
    assert conf["Station"]["latitude"] == "40.7"
    assert conf["Station"]["longitude"] == "-74.0"
    assert conf["Station"]["altitude"] == ["120", "foot"]
    assert conf["Rtldavis"]["transceiver_frequency"] == "EU"
    assert conf["Rtldavis"]["iss_channel"] == "3"
    assert conf["Rtldavis"]["rain_bucket_type"] == "1"
    assert "# starter config" in text
    assert conf["Rtldavis"]["cmd"] == "/usr/local/bin/rtldavis -gain 0"
    assert any("applied from the environment, once" in ln for ln in lines)


def test_empty_variables_count_as_unset(dirs):
    code, _ = run(dirs, {"WEEWX_LATITUDE": "", "RTLDAVIS_BAND": "  "})
    assert code == 0
    conf = configobj.ConfigObj(os.path.join(dirs[0], "weewx.conf"))
    assert conf["Station"]["latitude"] == "YOUR_LATITUDE"
    assert conf["Rtldavis"]["transceiver_frequency"] == "US"


@pytest.mark.parametrize("env", [
    {"WEEWX_LATITUDE": "north"},
    {"WEEWX_LATITUDE": "91"},
    {"WEEWX_LONGITUDE": "-181"},
    {"WEEWX_ALTITUDE": "120"},
    {"WEEWX_ALTITUDE": "120,feet"},
    {"RTLDAVIS_BAND": "AU"},
    {"RTLDAVIS_ISS_CHANNEL": "9"},
    {"RTLDAVIS_ISS_CHANNEL": "x"},
    {"RTLDAVIS_RAIN_BUCKET": "2"},
    {"WEEWX_LOCATION": "two\nlines"},
    {"WEEWX_DRIVER": "davis"},
])
def test_a_bad_value_stops_the_start_and_writes_nothing(dirs, env):
    code, lines = run(dirs, env)
    assert code == 1
    assert any("ERROR" in ln for ln in lines)
    assert os.listdir(dirs[0]) == []


def test_every_bad_value_is_reported_not_just_the_first(dirs):
    code, lines = run(dirs, {"WEEWX_LATITUDE": "x", "RTLDAVIS_BAND": "AU"})
    assert code == 1
    assert sum("ERROR" in ln for ln in lines) == 2


def test_missing_coordinates_warn(dirs):
    _, lines = run(dirs)
    assert any("WARNING" in ln and "WEEWX_LATITUDE" in ln for ln in lines)


def test_a_key_the_config_lacks_removes_the_half_seeded_config(dirs):
    with open(os.path.join(dirs[1], "weewx.conf"), "w") as f:
        f.write("[Station]\n    location = x\n")
    code, lines = run(dirs, {"RTLDAVIS_BAND": "US"})
    assert code == 1
    assert not os.path.exists(os.path.join(dirs[0], "weewx.conf"))
    assert any("half-seeded" in ln for ln in lines)


@pytest.mark.parametrize("value", ["simulator", "Simulator", " SIMULATOR "])
def test_simulator_driver_lands_case_insensitively(dirs, value):
    code, lines = run(dirs, {"WEEWX_DRIVER": value})
    assert code == 0
    conf = configobj.ConfigObj(os.path.join(dirs[0], "weewx.conf"))
    assert conf["Station"]["station_type"] == "Simulator"
    assert any("WeeWX Simulator" in ln for ln in lines)


@pytest.mark.parametrize("value", ["rtldavis", "RtlDavis"])
def test_rtldavis_driver_is_a_no_op(dirs, value):
    code, lines = run(dirs, {"WEEWX_DRIVER": value})
    assert code == 0
    conf = configobj.ConfigObj(os.path.join(dirs[0], "weewx.conf"))
    assert conf["Station"]["station_type"] == "Rtldavis"
    assert not any("Simulator" in ln for ln in lines)


def test_a_dist_config_without_a_simulator_stanza_is_rejected(dirs):
    with open(os.path.join(dirs[1], "weewx.conf"), "w") as f:
        f.write("[Station]\n    station_type = Rtldavis\n")
    code, lines = run(dirs, {"WEEWX_DRIVER": "simulator"})
    assert code == 1
    assert not os.path.exists(os.path.join(dirs[0], "weewx.conf"))
    assert any("[Simulator] driver" in ln for ln in lines)


@pytest.mark.skipif(os.getuid() == 0, reason="root can write anywhere")
def test_unwritable_mount_says_which_user_needs_it(dirs):
    os.chmod(dirs[0], 0o500)
    try:
        code, lines = run(dirs)
    finally:
        os.chmod(dirs[0], 0o700)
    assert code == 1
    assert any("not writable by uid %d" % os.getuid() in ln for ln in lines)


def test_missing_dist_is_reported(dirs):
    lines = []
    code = seed_config.seed(dirs[0], dirs[1] + "-gone", {}, out=lines.append)
    assert code == 1
    assert any("missing from this image" in ln for ln in lines)
