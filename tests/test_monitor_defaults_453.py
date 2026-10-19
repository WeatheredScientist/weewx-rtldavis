"""The monitor's defaults describe no particular host, and usb_reset.sh can only
reset an RTL-SDR (DEC-0217, #453).

Until DEC-0217 a monitor started with no environment got the original Synology
deployment: REMEDY_MODE=usb_reset, paths under /volume1, the maintainer's container
name, and a root script that unbound USB port 1-3 whatever was plugged in there.

  1. Defaults: REMEDY_MODE is none, BASE_DIR is the script's own directory, the
     helper scripts are found beside it, docker comes from PATH, and the container
     is the README's name.
  2. A monitor whose output directory is missing exits 2 with one line naming the
     variable to set, instead of a FileNotFoundError traceback.
  3. usb_reset.sh finds the dongle by USB id, refuses on zero or several matches,
     checks a pinned PORT the same way, and writes nothing to sysfs when it refuses.

Run:  .venv/bin/python -m pytest tests/test_monitor_defaults_453.py
"""
import importlib.util
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONITOR = os.path.join(ROOT, "weewx_monitor.py")
RESET = os.path.join(ROOT, "usb_reset.sh")

OVERRIDES = ("REMEDY_MODE", "WEEWX_RTLDAVIS_DIR", "WEEWX_CONTAINER", "DOCKER_BIN",
             "USB_RESET_SCRIPT", "USB_FORENSICS_SCRIPT", "MONITOR_LOG", "MONITOR_PIDFILE",
             "WEEWX_LOG", "WEEWX_ARCHIVE_DB")


def _fresh(monkeypatch, name, **env):
    """A private copy of weewx_monitor imported with none of the overrides set,
    except those passed in env."""
    monkeypatch.setattr(sys, "argv", ["weewx_monitor.py", "--test-alert"])
    for k in OVERRIDES:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    spec = importlib.util.spec_from_file_location(name, MONITOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- 1. defaults ---

def test_unset_environment_gives_host_neutral_defaults(monkeypatch):
    mod = _fresh(monkeypatch, "wm_defaults_453")
    assert mod.REMEDY_MODE == "none"
    assert mod.BASE_DIR == ROOT
    assert mod.USB_RESET_SCRIPT == os.path.join(ROOT, "usb_reset.sh")
    assert mod.USB_FORENSICS_SCRIPT == os.path.join(ROOT, "usb_forensics.sh")
    assert mod.CONTAINER == "weewx-rtldavis"
    for name in ("LOG", "PIDFILE", "CAMPAIGN_INHIBIT", "EPISODES_LOG", "EPISODE_STATE",
                 "ARCHIVE_DB", "WEEWX_LOG_PATH", "USB_RESET_SCRIPT", "USB_FORENSICS_SCRIPT"):
        value = getattr(mod, name)
        assert value.startswith(ROOT + os.sep), f"{name}={value} is not under BASE_DIR"


def test_base_dir_override_still_wins(monkeypatch, tmp_path):
    mod = _fresh(monkeypatch, "wm_base_override_453", WEEWX_RTLDAVIS_DIR=str(tmp_path))
    assert mod.BASE_DIR == str(tmp_path)
    assert mod.LOG == f"{tmp_path}/logs/weewx_monitor.log"
    assert mod.USB_RESET_SCRIPT == f"{tmp_path}/usb_reset.sh"


def test_docker_comes_from_path(monkeypatch, tmp_path):
    fake = tmp_path / "docker"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    mod = _fresh(monkeypatch, "wm_docker_path_453")
    assert mod.DOCKER_BIN == str(fake)


def test_docker_falls_back_to_the_synology_path(monkeypatch, tmp_path):
    """Synology's docker is /usr/local/bin/docker, off the default PATH."""
    monkeypatch.setenv("PATH", str(tmp_path))     # an empty directory: no docker
    mod = _fresh(monkeypatch, "wm_docker_fallback_453")
    assert mod.DOCKER_BIN == "/usr/local/bin/docker"


def test_docker_override_still_wins(monkeypatch):
    mod = _fresh(monkeypatch, "wm_docker_env_453", DOCKER_BIN="/opt/x/docker")
    assert mod.DOCKER_BIN == "/opt/x/docker"


# --- 2. a missing output directory is one clear line ---

def test_missing_base_dir_exits_with_a_message(tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in OVERRIDES}
    env["WEEWX_RTLDAVIS_DIR"] = str(tmp_path / "nowhere")
    r = subprocess.run([sys.executable, MONITOR], env=env,
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 2, r.stderr
    assert "WEEWX_RTLDAVIS_DIR" in r.stderr
    assert "Traceback" not in r.stderr
    assert not (tmp_path / "nowhere").exists(), "the refusal must not create anything"


def test_missing_output_dirs_lists_only_absent_ones(monkeypatch, tmp_path):
    (tmp_path / "logs").mkdir()
    mod = _fresh(monkeypatch, "wm_outdirs_453", WEEWX_RTLDAVIS_DIR=str(tmp_path),
                 MONITOR_PIDFILE=str(tmp_path / "run" / "m.pid"))
    assert mod.missing_output_dirs() == [str(tmp_path / "run")]


# --- the monitor reads the port the script found ---

def test_do_reset_logs_the_discovered_device(monkeypatch):
    import types
    mod = _fresh(monkeypatch, "wm_do_reset_453")
    logged, mailed = [], []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: types.SimpleNamespace(
        returncode=0, stdout="usb_reset: port=5-1 id=0bda:2838\n", stderr=""))
    monkeypatch.setattr(mod, "log", logged.append)
    monkeypatch.setattr(mod, "send_email", lambda s, b: mailed.append(b))
    mod.do_reset(notify=True)
    assert "RESET: done, device=0bda:2838 at port 5-1" in logged
    assert "0bda:2838 at port 5-1" in mailed[0]


# --- 3. usb_reset.sh discovery ---

RTL = ("0bda", "2838")
GENERIC_RTL = ("0bda", "2832")
MOUSE = ("046d", "c52b")


def _sysfs(d, devices):
    root = os.path.join(d, "sysfs")
    os.makedirs(os.path.join(root, "drivers", "usb"))
    for port, ids in devices.items():
        dev = os.path.join(root, "devices", port)
        os.makedirs(dev)
        if ids:
            for fname, value in zip(("idVendor", "idProduct"), ids):
                with open(os.path.join(dev, fname), "w") as f:
                    f.write(value + "\n")
    return root


def _run_reset(tmp_path, devices, port=""):
    """Run a copy of usb_reset.sh against a fake sysfs. Returns (result, unbind, bind)
    where unbind/bind are what was written to the driver files, or None."""
    root = _sysfs(str(tmp_path), devices)
    src = open(RESET).read()
    assert "\nSYSFS=/sys/bus/usb\n" in src and '\nPORT=""\n' in src
    script = tmp_path / "reset.sh"
    script.write_text(src.replace("\nSYSFS=/sys/bus/usb\n", f"\nSYSFS={root}\n")
                         .replace('\nPORT=""\n', f'\nPORT="{port}"\n')
                         .replace("sleep 3", "true"))
    env = {**os.environ, "USB_FORENSICS_SCRIPT": str(tmp_path / "absent.sh")}
    r = subprocess.run(["/bin/sh", str(script)], env=env,
                       capture_output=True, text=True, timeout=30)

    def written(name):
        p = os.path.join(root, "drivers", "usb", name)
        return open(p).read().strip() if os.path.exists(p) else None
    return r, written("unbind"), written("bind")


def test_finds_the_dongle_on_any_port(tmp_path):
    r, unbind, bind = _run_reset(tmp_path, {"5-1": RTL, "1-3": MOUSE, "1-4": None})
    assert r.returncode == 0, r.stderr
    assert (unbind, bind) == ("5-1", "5-1")
    assert "usb_reset: port=5-1 id=0bda:2838" in r.stdout


def test_accepts_a_generic_rtl2832u(tmp_path):
    r, unbind, _ = _run_reset(tmp_path, {"2-1.4": GENERIC_RTL})
    assert r.returncode == 0, r.stderr
    assert unbind == "2-1.4"


def test_skips_interfaces_and_root_hubs(tmp_path):
    """Only a device directory names a port; an interface (1-3:1.0) or a root hub
    (usb1) written to the unbind file would be wrong even with a matching id."""
    r, unbind, _ = _run_reset(tmp_path, {"1-3": RTL, "1-3:1.0": RTL, "usb1": RTL})
    assert r.returncode == 0, r.stderr
    assert unbind == "1-3"


def test_refuses_when_no_dongle_is_present(tmp_path):
    """The old script's failure: port 1-3 holds some other device. It used to be
    unbound as root."""
    r, unbind, bind = _run_reset(tmp_path, {"1-3": MOUSE})
    assert r.returncode == 3
    assert "USB RESET REFUSED" in r.stderr and "no RTL2832U" in r.stderr
    assert unbind is None and bind is None


def test_refuses_two_dongles_and_names_both(tmp_path):
    r, unbind, bind = _run_reset(tmp_path, {"1-3": RTL, "2-1": GENERIC_RTL})
    assert r.returncode == 3
    assert "1-3" in r.stderr and "2-1" in r.stderr and "set PORT" in r.stderr
    assert unbind is None and bind is None


def test_pinned_port_picks_one_of_two(tmp_path):
    r, unbind, bind = _run_reset(tmp_path, {"1-3": RTL, "2-1": GENERIC_RTL}, port="2-1")
    assert r.returncode == 0, r.stderr
    assert (unbind, bind) == ("2-1", "2-1")


def test_pinned_port_must_still_be_a_dongle(tmp_path):
    r, unbind, bind = _run_reset(tmp_path, {"1-3": MOUSE, "2-1": RTL}, port="1-3")
    assert r.returncode == 3
    assert "046d:c52b" in r.stderr
    assert unbind is None and bind is None


@pytest.mark.parametrize("bad", ["../1-3", "1-3/..", "abc", "1-3;id", "13", "-1", "1-"])
def test_pinned_port_must_be_a_port_name(tmp_path, bad):
    r, unbind, bind = _run_reset(tmp_path, {"1-3": RTL}, port=bad)
    assert r.returncode == 3, (bad, r.stdout, r.stderr)
    assert "not a USB port name" in r.stderr
    assert unbind is None and bind is None


def test_port_and_sysfs_are_not_inputs():
    """The sudoers grant is scoped to the script's path with no arguments. Any input
    the monitor's user controls would let it unbind any device as root, so PORT and
    SYSFS are assigned only inside the script and never read from $1 or the
    environment."""
    src = open(RESET).read()
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    assert re.findall(r"^[ \t]*PORT=.*$", code, re.M) == ['PORT=""', "    PORT=${FOUND# }"]
    assert re.findall(r"^[ \t]*SYSFS=.*$", code, re.M) == ["SYSFS=/sys/bus/usb"]
    assert "${PORT:-" not in code and "${SYSFS:-" not in code
    assert not re.search(r'\$\{?1\b', code.replace('"$1"', "").replace("$1/", "")), \
        "only capture()'s phase and usb_id()'s directory may use $1"


# --- usb_forensics.sh records the port it was given ---

def test_forensics_records_the_passed_port(tmp_path):
    forensics = os.path.join(ROOT, "ops", "usb_forensics.sh")
    env = {**os.environ, "USB_RESET_PORT": "5-1", "USB_FORENSICS_DIR": str(tmp_path)}
    r = subprocess.run(["/bin/sh", forensics, "unit"], env=env,
                       capture_output=True, text=True, timeout=60)
    out = r.stdout.strip()
    assert out and os.path.exists(out), r.stderr
    assert "port=5-1 " in open(out).read().splitlines()[0]


def test_forensics_without_a_port_never_guesses_1_3(tmp_path):
    """On a host without exactly one RTL2832U (this test host has none), the header
    says unknown rather than the old Synology port."""
    if any(os.path.exists(f"/sys/bus/usb/devices/{p}") for p in ("1-3",)):
        pytest.skip("host has a real USB tree")
    forensics = os.path.join(ROOT, "ops", "usb_forensics.sh")
    env = {k: v for k, v in os.environ.items() if k != "USB_RESET_PORT"}
    env["USB_FORENSICS_DIR"] = str(tmp_path)
    r = subprocess.run(["/bin/sh", forensics, "unit"], env=env,
                       capture_output=True, text=True, timeout=60)
    out = r.stdout.strip()
    assert out and os.path.exists(out), r.stderr
    assert "port=unknown " in open(out).read().splitlines()[0]
