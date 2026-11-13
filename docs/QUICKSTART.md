# Quick start

Needs image v2.3.0 or newer (DEC-0225/0227/0228).

Get a Davis Vantage weather station into WeeWX with a $35 USB radio instead of the console. Ten
minutes on a Raspberry Pi; the console, if you have one, keeps working.

## What you need

- A Davis Vantage Pro2, Pro2 Plus or Vue outdoor sensor suite (the ISS), within radio range.
  The factory setting (transmitter ID 1, DIP switches all off) is what this expects. Nothing on the
  ISS changes.
- An RTL-SDR Blog V3 or V4 dongle and a 915 MHz antenna, vertical, on a 1 to 3 m USB extension away
  from the computer. EU stations use 868 MHz, New Zealand 921 MHz; the antenna has to match. The V3
  is what this project runs. The image's librtlsdr also supports the V4; its first live run here is
  planned for December 2026. Test a V4 with `doctor` below, not with the host's own `rtl_test`:
  Debian 12 and Raspberry Pi OS 12 ship a librtlsdr too old for the V4.
- A Linux computer that stays on, with a free USB port: a Raspberry Pi 4 or 5 running the 64-bit
  OS, a mini PC, a home server, or a NAS that runs Docker. amd64 and arm64 both work. Windows and
  macOS do not: USB through a virtual machine adds timing jitter the radio cannot follow.

## 1. Prepare the computer

Download the setup script from the release page, read it, then run it:

```bash
curl -fsSLO https://github.com/WeatheredScientist/weewx-rtldavis/releases/download/v2.4.0/host-setup.sh
```

```bash
less host-setup.sh
```

```bash
bash host-setup.sh
```

It checks that the dongle is plugged in, stops the kernel's TV driver from claiming it, lets your
user open it, installs Docker if you do not have it (it asks first), and creates the `weewx/`
folder with a `docker-compose.yml` and a `.env` file inside. Unplug and re-plug the dongle when it
says so. Debian, Ubuntu and Raspberry Pi OS are supported; on anything else do the two manual
steps in [docs/DEPLOY.md](DEPLOY.md#host-preparation).

## 2. Tell it where you are

Edit `weewx/.env`. Five lines matter:

```
TZ=America/New_York
WEEWX_LOCATION="My Back Yard"
WEEWX_LATITUDE=40.7
WEEWX_LONGITUDE=-74.0
WEEWX_ALTITUDE=120,foot
```

Outside the US, also set `RTLDAVIS_BAND=EU` (or `NZ`) and `RTLDAVIS_RAIN_BUCKET=1` for a 0.2 mm
bucket. If you moved the ISS off transmitter ID 1, set `RTLDAVIS_ISS_CHANNEL`. These are read once,
on the first start, and written into `weewx-data/weewx.conf`; edit that file for anything later.

## 3. Start it

```bash
cd weewx && docker compose up -d
```

The first start copies a complete `weewx.conf` into `weewx-data/` and applies your `.env`. Every
start after that uses the file as it is.

## 4. Check it

```bash
docker compose logs --tail 30
```

You should see the driver line, `driver version is 0.20+ws.10 (fork of 0.20, patched by
WeatheredScientist -- not stock upstream)`, then `rtldavis: US band, ISS channel 1 …`, and within
about three minutes the first `LOOP` line with real readings. `docker compose ps` shows `healthy`
while WeeWX keeps writing its log and `unhealthy` after ten quiet minutes; nothing restarts on it.
The full log is `weewx/logs/weewx.log`.

That is the install. WeeWX records to `weewx-data/archive/weewx.sdb` every five minutes.

## No hardware yet?

Set `WEEWX_DRIVER=simulator` in `.env` before the first start: made-up weather, so you can wire up
uploads or a dashboard now. With no USB device at all, also comment out the `devices:` lines in
`docker-compose.yml`. When the radio arrives, delete `weewx-data/weewx.conf`, remove the line, and
start again.

## Something wrong?

| You see | Do |
|---|---|
| `not a device node` and the container restarts | The container sees no RTL2832U. Plug the dongle in; with `docker run`, pass `--device /dev/bus/usb`; a VM needs a USB controller with the dongle attached |
| `usb_claim_interface error -6` or `Device or resource busy` | The kernel TV driver has the dongle. Re-run the setup script, then reboot. If `doctor` says another program holds it, stop that program |
| `Permission denied` opening the dongle | The udev rule did not apply. Re-run the setup script, unplug and re-plug; check `PUID`/`PGID` in `.env` match `id -u` and `id -g` |
| Driver line appears, no `LOOP` after ten minutes | Radio, not software. Check the USB cable and re-plug; antenna vertical and away from the computer; band and channel match the ISS; try `-gain 0` (auto) in `[Rtldavis]` |
| `weewx.conf` not found | Rare now: the first start writes it, and `doctor` says `not seeded yet` until then |
| `more than one dongle`, or `dongle: ... matches the serial of 2 dongles` | Two RTL-SDRs are plugged in and the station cannot tell which is its own. See "More than one dongle" below |
| A V4 found as `R828D` with poor or no reception on the host's `rtl_test` | The host's librtlsdr predates the V4 (Debian 12, Pi OS 12). The container's does not: check with `doctor` |

Stop the station first (`docker compose stop`; one program can hold the dongle), then run:

```bash
docker compose run --rm weewx-rtldavis doctor
```

It lists every RTL-SDR it sees (USB port, maker, product, serial, and whether it is a Blog V4).
Then it checks the one the station uses: the kernel driver, permissions and the radio. It prints
band, channel and gain from `weewx.conf`, and on a failure names the row above that applies.

### More than one dongle

Needs an image newer than v2.4.0. Say you plug in a second RTL-SDR, such as an ADS-B stick or a V4
next to a V3. Tell the station which one is its own. Otherwise it opens whichever dongle the USB
library lists first, and that can change at a reboot. Run `doctor`, copy the serial of the
station's dongle from its list, and put it in `.env`:

```
RTLSDR_DEVICE=<that serial>
```

On every start the decoder opens that dongle and logs `dongle: using …` with its serial. The bias
tee (`BIAS_TEE`) acts on the same dongle.

RTL-SDR dongles often leave the factory with the same serial, so two of them cannot be told apart.
`doctor` says so when that happens, and the station refuses to guess. Give one of them its own
serial:

1. Stop the station.
2. Plug in only that dongle.
3. Run this inside the container. On any other computer with a recent `rtl-sdr` installed, the
   part from `rtl_eeprom` on does the same.

   ```bash
   docker compose run --rm weewx-rtldavis rtl_eeprom -d 0 -s WX2
   ```

4. It prints the dongle's current settings and asks before writing. Check that it shows the dongle
   you meant, then answer `y`.
5. Unplug the dongle and plug it back in.

Put a letter in the serial: the `rtl_*` tools read a serial made only of digits as a position in
the list. On a Blog V4, change only the serial. Never pass `-m`, `-p` or `-g`: the V4 is recognized
by its maker and product strings.

## What next

- Uploads (Weather Underground, CWOP, Windy, OpenWeatherMap, WeatherCloud, InfluxDB): each has a
  section in `weewx-data/weewx.conf` with its registration link; enable it and
  `docker compose restart`.
- A dashboard: the live JSON feed in `weewx-data/feed/` and the InfluxDB uploader are the data
  contract, described in [docs/INTERFACES.md](INTERFACES.md).
- Run it as a system service with a dedicated user, or on a Synology: [docs/DEPLOY.md](DEPLOY.md).
- Update: change the tag in `docker-compose.yml`, then `docker compose pull && docker compose up -d`.
  Tags follow SemVer against the data you read from the image; a patch or minor never breaks a
  consumer.

## Not a Davis owner?

Two pieces of this repository work with any WeeWX driver and need no Docker: the live JSON feed
([extensions/loopjson](../extensions/loopjson/README.md)) and the InfluxDB 2 uploader
([extensions/influx](../extensions/influx/README.md)). Install either with
`weectl extension install <release zip URL>`. For non-Davis radio stations (Acurite, Ecowitt,
LaCrosse and most 433 MHz brands) use `weewx-sdr` with `rtl_433`; this image only decodes Davis.
