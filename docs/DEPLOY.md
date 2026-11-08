# Deploying weewx-rtldavis

Two ways to run it as a service. **systemd on a Linux host is the recommended one**: it is how the
maintainer's station runs, and the container stays unprivileged. A Synology NAS also works; the
station ran on one from May to August 2026, and those instructions are kept below.

Do step 1 of the README's [Quick start](../README.md#quick-start) first: `host-setup.sh` checks the
dongle, keeps the kernel's TV driver off it and offers to install Docker (the `~/weewx` folder it
creates isn't used here). The steps below replace Quick start steps 2–4: the location goes in when
the config is seeded, and systemd starts the container instead of Compose.

## Host preparation

`host-setup.sh` does these two things on Debian, Ubuntu and Raspberry Pi OS. On any other
distribution, do them by hand. Use the group your container user belongs to for `GROUP` in the
rule (the systemd steps below create `weewx`).

**1. Keep the kernel's TV driver off the dongle.** The kernel claims an RTL-SDR as a TV tuner
unless told not to. Put this in `/etc/modprobe.d/blacklist-rtl-sdr.conf`, then unload the modules
or reboot:

```
blacklist dvb_usb_rtl28xxu
install dvb_usb_rtl28xxu /bin/false
blacklist rtl2832
install rtl2832 /bin/false
blacklist rtl2830
install rtl2830 /bin/false
blacklist rtl2832_sdr
install rtl2832_sdr /bin/false
```

**2. Let a non-root user open the dongle.** Put this in `/etc/udev/rules.d/60-rtl-sdr.rules`
(`0bda:2838` and `0bda:2832` are the two IDs RTL-SDR dongles use), then run
`sudo udevadm control --reload-rules` and `sudo udevadm trigger`, and re-plug the dongle:

```
SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="2838", GROUP="weewx", MODE="0660"
SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="2832", GROUP="weewx", MODE="0660"
```

## systemd (recommended)

**1. A dedicated user and directory.**

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin weewx
```

```bash
sudo mkdir -p /srv/weewx/weewx-data /srv/weewx/logs
```

```bash
sudo chown -R weewx:weewx /srv/weewx
```

Seed the starter config with the image's own seeder, putting your location in (the same four values
as Quick start step 2). The unit refuses to start without a `weewx.conf`, so this runs once, by
hand, before it:

```bash
sudo docker run --rm --user "$(id -u weewx):$(id -g weewx)" -e WEEWX_LOCATION="My Back Yard" -e WEEWX_LATITUDE=40.7 -e WEEWX_LONGITUDE=-74.0 -e WEEWX_ALTITUDE=120,foot -v /srv/weewx/weewx-data:/opt/weewx-data weatheredscientist/weewx-rtldavis:v2.4.0 /opt/weewx-venv/bin/python3 /opt/seed_config.py
```

It prints `seed: … wrote a starter weewx.conf` and does nothing if a `weewx.conf` is already there.
Outside the US, add `-e RTLDAVIS_BAND=EU` (or `NZ`).

**2. Give that user the dongle.** `host-setup.sh` wrote this rule for your own group; point it at
`weewx` instead:

```bash
printf 'SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="%s", GROUP="weewx", MODE="0660"\n' 2838 2832 | sudo tee /etc/udev/rules.d/60-rtl-sdr.rules
```

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

**3. Install the unit.** Copy
[examples/systemd/weewx-rtldavis.service](../examples/systemd/weewx-rtldavis.service), replace the
values its header lists (`id -u weewx` and `id -g weewx` give the uid and gid), then:

```bash
sudo install -m 0644 weewx-rtldavis.service /etc/systemd/system/
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now weewx-rtldavis
```

The unit runs the container with `--cap-drop ALL`, `no-new-privileges` and the `weewx` user's uid,
passes only the USB bus, and refuses to start without a `weewx.conf`. A config change needs
`sudo systemctl restart weewx-rtldavis`. A new image version is a tag change in the unit plus a
restart.

Logs are `/srv/weewx/logs/weewx.log`. WeeWX rotates it itself.

If the unit loops on exit 125 and `journalctl -u weewx-rtldavis` shows `not a device node`,
`/dev/bus/usb` is empty: the host has no USB device at all. Plug in the dongle (a VM needs a virtual
USB controller with one device attached). Creating the directory by hand does not help.

## Synology NAS (alternative)

Install Container Manager from Package Center, seed the config as in systemd step 1, then run the
unit's `docker run` line (its `ExecStart`) over SSH, with the paths under
`/volume1/docker/weewx-rtldavis/`. DSM ships no TV-tuner driver, so `host-setup.sh`'s blacklist
isn't needed. The station's Synology setup ran the container as root with
`--privileged`; the non-root setup above (`--user` plus a udev rule) is untested on DSM. If the
dongle won't open, drop `--user` and `--cap-drop ALL` and add `--privileged`.

Only one container can hold the dongle. When switching between containers, kill the old one first;
if the new one still can't open the dongle, reset the USB port (the path `1-3` was the DS918+'s
port; find yours under `/sys/bus/usb/devices/`):

```bash
echo '1-3' | sudo tee /sys/bus/usb/drivers/usb/unbind && sleep 2 && echo '1-3' | sudo tee /sys/bus/usb/drivers/usb/bind
```

## Monitoring

[`weewx_monitor.py`](../weewx_monitor.py) runs on the host and reads `weewx.log`. It emails when an
uploader stops publishing, when reception drops below 60% for five minutes (it counts Weather
Underground Rapidfire posts, so that check needs Rapidfire on), when the ISS
low-battery flag holds across healthy reception, and when the log itself goes quiet (so a broken
monitor input is reported, not mistaken for an outage). It also sends a periodic reception summary.

Credentials go in `monitor.env`, copied from [monitor.env.example](../monitor.env.example). It
uses a Gmail app password. Keep the file `0600` and never commit it.

### On systemd

Copy `weewx_monitor.py` and `monitor.env` to `/srv/weewx/`, then install
[examples/systemd/weewx-monitor.service](../examples/systemd/weewx-monitor.service) the same way as
the main unit. It starts in `REMEDY_MODE=none`: it detects and emails, and never acts. The unit's
comments explain `restart_unit`, which restarts the weewx service on a stall.

### On Synology

On Synology the monitor can reset the dongle's USB port on a stall (`REMEDY_MODE=usb_reset`; the
default is `none`, so set it in `monitor.env`). `usb_reset.sh` finds the dongle by its USB id and
refuses if it finds none or more than one, so it can't reset another device. The reset needs root,
so the monitor runs as a limited user that may run exactly one script as root:

1. In DSM, create a user `weewx-monitor`: group `users` only, no shared-folder or application
   permissions.
2. Let it write the logs directory:

   ```bash
   sudo synoacltool -add /volume1/docker/weewx-rtldavis/logs "user:weewx-monitor:allow:rwxp-DaARWc--:fd--"
   ```

3. Copy `weewx_monitor.py`, `usb_reset.sh` and `monitor.env` to `/volume1/docker/weewx-rtldavis/`.
   `usb_reset.sh` must be owned by root and writable only by root. Add `REMEDY_MODE=usb_reset` to
   `monitor.env`. With more than one RTL-SDR attached, set `PORT` at the top of `usb_reset.sh` to
   the one weewx uses.
4. In Control Panel → Task Scheduler, create a triggered task at boot, user `root`, with this
   script. DSM can rewrite `/etc/sudoers` on update, so the first line re-adds the grant at every
   boot.

   ```bash
   echo 'weewx-monitor ALL=(root) NOPASSWD: /volume1/docker/weewx-rtldavis/usb_reset.sh' >> /etc/sudoers
   set -a; . /volume1/docker/weewx-rtldavis/monitor.env; set +a
   rm -f /volume1/docker/weewx-rtldavis/logs/weewx_monitor.pid
   sudo -u weewx-monitor -E python3 -u /volume1/docker/weewx-rtldavis/weewx_monitor.py >> /volume1/docker/weewx-rtldavis/logs/weewx_monitor.log 2>&1 &
   ```

5. Optional: [`ops/usb_forensics.sh`](../ops/usb_forensics.sh) records the USB bus before and after
   each reset. Install it root-owned beside `usb_reset.sh`, which refuses to run a helper the
   monitor's user could rewrite, and which tells it the port it reset.

Rotate `weewx_monitor.log` with a daily DSM task running `logrotate` over a config that uses
`copytruncate`, so the monitor needn't restart.
