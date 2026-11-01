# Quick start

Written as it reads once DEC-0225's image items ship in v2.2.0 (proposals A to D and G in
`docs/INSTALL-RESEARCH.md`). Lines marked `[A]`, `[B]`, `[C]`, `[D]`, `[G]` depend on that item; until
then the README's current six steps apply. v2.2.0 builds A, B and G; C and D are in the repository.
Three things below are written ahead of a later release: the `healthy` state, `doctor`, and
`WEEWX_DRIVER=simulator` (proposals E and F, DEC-0225 option 1). Do not rely on them until the
changelog says they shipped.

---

Get a Davis Vantage weather station into WeeWX with a $35 USB radio instead of the console. Ten
minutes on a Raspberry Pi; the console, if you have one, keeps working.

## What you need

- A Davis Vantage Pro2, Pro2 Plus or Vue outdoor sensor suite (the ISS), within radio range.
  The factory setting (transmitter ID 1, DIP switches all off) is what this expects. Nothing on the
  ISS changes.
- An RTL-SDR Blog V3 dongle and a 915 MHz antenna, vertical, on a 1 to 3 m USB extension away from
  the computer. EU stations use 868 MHz, New Zealand 921 MHz; the antenna has to match.
- A Linux computer that stays on, with a free USB port: a Raspberry Pi 4 or 5 running the 64-bit
  OS, a mini PC, a home server, or a NAS that runs Docker. amd64 and arm64 both work. Windows and
  macOS do not: USB through a virtual machine adds timing jitter the radio cannot follow.

## 1. Prepare the computer `[C]`

Download the setup script from the release page, read it, then run it:

```bash
curl -fsSLO https://github.com/WeatheredScientist/weewx-rtldavis/releases/download/v2.2.0/host-setup.sh
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

## 2. Tell it where you are `[B] [D]`

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

## 3. Start it `[A] [D]`

```bash
cd weewx && docker compose up -d
```

The first start copies a complete `weewx.conf` into `weewx-data/` and applies your `.env`. Every
start after that uses the file as it is.

## 4. Check it

```bash
docker compose logs --tail 30
```

You should see the driver line, `driver version is 0.20+ws.9 (fork of 0.20, patched by
WeatheredScientist -- not stock upstream)`, then `rtldavis: US band, ISS channel 1 …`, and within
about three minutes the first `LOOP` line with real readings. `docker compose ps` shows `healthy`
once readings are flowing. The full log is `weewx/logs/weewx.log`.

That is the install. WeeWX now records to `weewx-data/archive/weewx.sdb` every five minutes.

## No hardware yet?

Set `WEEWX_DRIVER=simulator` in `.env` before the first start for made-up weather, so you can wire
up uploads or a dashboard now. With no USB device on the computer at all, also comment out the
`devices:` lines in `docker-compose.yml`. When the radio arrives, delete `weewx-data/weewx.conf`,
remove the line, and start again.

## Something wrong?

| You see | Do |
|---|---|
| `not a device node` and the container restarts | No USB device on the host at all. Plug the dongle in; a VM needs a USB controller with it attached |
| `usb_claim_interface error -6` or `Device or resource busy` | The TV driver has the dongle. Re-run the setup script, then reboot |
| `Permission denied` opening the dongle | The udev rule did not apply. Unplug and re-plug; check `PUID`/`PGID` in `.env` match `id -u` and `id -g` |
| Driver line appears, no `LOOP` after ten minutes | Radio, not software. Antenna vertical and away from the computer; band and channel match the ISS; try `-gain 0` (auto) in `[Rtldavis]` |
| `weewx.conf` not found | Rare now; `docker compose run --rm weewx doctor` reports what is missing |

`docker compose run --rm weewx doctor` checks the dongle, the kernel driver and permissions in one
go and names the row above that applies.

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
