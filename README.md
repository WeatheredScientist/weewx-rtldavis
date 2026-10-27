# weewx-rtldavis

Run a Davis Vantage weather station in [WeeWX](https://weewx.com/) with an inexpensive RTL-SDR USB
radio instead of a Davis console.

A Davis Vantage Pro2's outdoor sensor suite (the ISS) broadcasts its readings on 915 MHz. The
console is the only receiver Davis sells, but the broadcast is a plain radio signal. This project
packages WeeWX with Luc Heijst's [rtldavis](https://github.com/lheijst/weewx-rtldavis) decoder and
driver in one Docker image, so a dongle can stand in for the console and the data stays yours.

It is an unofficial distribution, and it is not stock upstream: the driver carries fixes and
data-quality filters that upstream does not have. Every divergence, and why, is in
[CHANGES-FROM-UPSTREAM.md](CHANGES-FROM-UPSTREAM.md). It is not affiliated with or endorsed by the
upstream authors (see [Credits](#credits)), and its bugs are its own. GPLv3.

**Docker Hub:** [`weatheredscientist/weewx-rtldavis`](https://hub.docker.com/r/weatheredscientist/weewx-rtldavis)

## What's different from stock rtldavis

- **Upstream bugs fixed.** Phantom rain from the rain-counter wraparound handler. Outside
  temperatures below 0 °F decoded as about +400 °F. A default config line that silently drops the
  radio to the EU band. A reception percentage that read about 73% on a healthy link, because the
  decoder booked the station's own repeat packets as misses. Leftover decoder processes after
  every stall.
- **The CRC is not trusted alone.** A corrupt frame can pass its CRC. Every reading is checked
  against the sensor's physical limits, and one impossible value discards the whole frame. A
  rejected reading becomes empty, never a substituted value.
- **Runs unprivileged.** No `--privileged`: it runs as a non-root user with every capability
  dropped.
- **Extras.** Uploaders for Windy, OpenWeatherMap and WeatherCloud; an InfluxDB 2 uploader with
  TLS verification on; a WeatherLink pressure fetch; a live JSON feed; a host-side monitor.

The bug fixes are offered upstream:
[lheijst/weewx-rtldavis#22](https://github.com/lheijst/weewx-rtldavis/pull/22) (rain),
[#23](https://github.com/lheijst/weewx-rtldavis/pull/23) (temperature),
[lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) (repeat packets),
[david-lutz/weewx-influx2#1](https://github.com/david-lutz/weewx-influx2/pull/1) (TLS).

## Requirements

- A Davis Vantage Pro, Pro2 or Vue ISS. US 915 MHz is what this is tested on; the driver also
  supports EU and NZ.
- An RTL-SDR dongle (tested: RTL-SDR Blog V3, USB id `0bda:2838`) and a vertical 915 MHz antenna.
- A Linux host with Docker, amd64 or arm64 (a Raspberry Pi pulls the same tag; multi-arch from
  v2.0.20). The arm64 image is built and smoke-tested on every change but has not yet run against a
  live radio. Windows and macOS pass USB through a VM, and the added timing jitter can break the
  radio's hop tracking.

## Quick start

**1. Plug in the dongle and check it.** `lsusb | grep 0bda:2838` should show it. On Debian and
Ubuntu the kernel's TV driver claims the dongle first; turn it off:

```bash
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtl-sdr.conf
```

```bash
sudo rmmod dvb_usb_rtl28xxu
```

**2. Let your user open the dongle**, so the container doesn't need root:

```bash
echo "SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0bda\", ATTR{idProduct}==\"2838\", GROUP=\"$(id -gn)\", MODE=\"0660\"" | sudo tee /etc/udev/rules.d/60-rtl-sdr.rules
```

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

**3. Copy the starter config out of the image.** A bind mount hides what the image has at that
path, so without this WeeWX starts with no `weewx.conf` at all.

```bash
mkdir -p ~/weewx/weewx-data ~/weewx/logs
```

```bash
docker create --name wx-seed weatheredscientist/weewx-rtldavis:v2.0.21
```

```bash
docker cp wx-seed:/opt/weewx-data/. ~/weewx/weewx-data/ && docker rm wx-seed
```

**4. Edit `~/weewx/weewx-data/weewx.conf`.** At minimum: `[Station]` (location, latitude,
longitude, altitude) and `[Rtldavis]` (`transceiver_frequency`, `iss_channel` to match the ISS's
DIP switches, `rain_bucket_type`). [weewx.conf.example](weewx.conf.example) documents every
setting, including each upload service.

**5. Run it.**

```bash
docker run -d --name weewx-rtldavis --restart unless-stopped --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges --device /dev/bus/usb -e HOME=/tmp -e TZ=America/New_York -e BIAS_TEE=0 -v ~/weewx/weewx-data:/opt/weewx-data -v ~/weewx/logs:/var/log/weewx weatheredscientist/weewx-rtldavis:v2.0.21
```

Set `TZ` to your own zone so daily rain resets at local midnight. `BIAS_TEE=0` leaves the
dongle's antenna power off; set it to `1` only if you run an LNA powered through the dongle.

**6. Check it.** `tail -f ~/weewx/logs/weewx.log` should show
`driver version is 0.20+ws.7 (fork of 0.20, patched by WeatheredScientist -- not stock upstream)`,
then `LOOP` data and, once uploads are enabled, `Published record` lines.

To run it as a system service, see [docs/DEPLOY.md](docs/DEPLOY.md). systemd is the recommended
path, and a Synology NAS works too.

## Uploads

Enable any of these in `weewx.conf`; each section in [weewx.conf.example](weewx.conf.example)
says where to register and what to set.

| Service | Suggested interval |
|---|---|
| Weather Underground | Rapidfire 2.5 s + archive 60 s |
| PWSweather, OpenWeatherMap | 60 s |
| CWOP (feeds NOAA MADIS), AWEKAS, Windy, WOW-BE | 5 min |
| WOW (Met Office; being decommissioned, use WOW-BE) | 5 min |
| WeatherCloud | 10 min (60 s needs a paid plan) |
| InfluxDB 2 | every archive record |

## Data for dashboards

Two outputs are the project's contract with anything that reads it, specified in
[docs/INTERFACES.md](docs/INTERFACES.md):

- **A live JSON feed** (`loop-data.txt` and `current.json`), rewritten on every reading. It also
  ships on its own as a WeeWX extension that works with any driver:
  [extensions/loopjson](extensions/loopjson/README.md).
- **An InfluxDB 2 time series**, one point per archive record. The uploader also ships on its own
  as a WeeWX extension, patched for Python 3.12+ and verified TLS:
  [extensions/influx](extensions/influx/README.md).

They were built for the Eagle Hunt Weather dashboard, and nothing in them is specific to it.

## Pressure

The ISS has no barometer; it is in the console. If you also have a Davis console reporting to
WeatherLink (a WeatherLink Live, for example), `pressure_service.py` reads sea-level and station
pressure from the WeatherLink v2 API. Get an API key at
[weatherlink.com/develop](https://www.weatherlink.com/develop), add a `[DavisPressure]` section (see
[weewx.conf.example](weewx.conf.example)), and add `user.pressure_service.DavisPressureFetcher` to
`process_services`. A `fetch_interval` of 300 s uses about 1% of the API's hourly allowance.

## Monitoring

`weewx_monitor.py` runs on the host, outside the container, and reads the WeeWX log. It emails
when an uploader stops publishing, when radio reception drops, when the ISS reports a low battery
across healthy reception, and when its own input goes stale. Setup is in
[docs/DEPLOY.md](docs/DEPLOY.md#monitoring).

## Versions

Four numbers move independently:

| What | Looks like | Moves when |
|---|---|---|
| Image tag | `v2.0.21` | every release, by the rule below |
| Driver | `0.20+ws.7` | upstream's 0.20 plus this project's patch level; rises with every driver behavior change. The startup line says which one is running |
| Data contract | `loop_json_writer/1.0.0` | the shape or meaning of `loop-data.txt` and `current.json` changes (the `writer` key in both files) |
| Extensions | `loopjson-v1.0.0`, `influx-v0.20+ws.2` | each extension releases on its own tag |

**Image tags follow [SemVer](https://semver.org) against what you read from the image**: the loop
JSON, the InfluxDB schema, the archive's columns and the documented run and mount layout. A major
bump breaks one of those, a minor bump adds something or changes what a value means, and a patch
changes none of them. Pin a tag. `:latest` moves only after a release has run in production.

The base system is recorded in each release's notes, not in the version number. v2.0.x runs Ubuntu 26.04,
Python 3.14 and WeeWX 5.5. Up to v2.0.21 the major number tracked the base system (v1 was Ubuntu 22),
and no earlier tag was renumbered; the rule above starts at v2.1.0.

Release notes are on the [Releases](https://github.com/WeatheredScientist/weewx-rtldavis/releases)
page.

## Troubleshooting

- **No data.** Check that `dvb_usb_rtl28xxu` isn't loaded (`lsmod`), the antenna is vertical, and
  the dongle sits on a 1–3 m USB extension, away from the computer. Gain is the `-gain` value on
  the `cmd` line in `[Rtldavis]`, in tenths of a dB.
- **`weewx.conf` not found, container restarting.** Step 3 was skipped.
- **Permission denied opening the dongle.** The udev rule (step 2) didn't apply. Re-plug the
  dongle.
- **HTTP 429 from a service.** Raise that service's `post_interval`.
- **Switching containers.** Only one process can hold the dongle. `docker kill` the old container
  before starting the new one.

## Building from source

```bash
git clone https://github.com/WeatheredScientist/weewx-rtldavis && cd weewx-rtldavis && docker build -t weewx-rtldavis .
```

The build fetches the decoder source from
[weewx-contrib/weewx-rtldavis](https://github.com/weewx-contrib/weewx-rtldavis) and applies
[patch/rtldavis-dupgate.patch](patch/rtldavis-dupgate.patch). If upstream's source has moved so the
patch no longer applies, the build fails rather than shipping an unpatched decoder.

## Contributing

Issues and pull requests are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md) and
[SECURITY.md](SECURITY.md). The repository also holds the maintainer's operating records
(`BOOT.md`, `docs/DECISIONS.md`, `ops/`). You don't need any of them to run the image.

## Credits

- [WeeWX](https://weewx.com/): Tom Keffer and Matthew Wall.
- The rtldavis [driver](https://github.com/lheijst/weewx-rtldavis) and
  [decoder](https://github.com/lheijst/rtldavis): Luc Heijst. The driver merges Matthew Wall's
  [weewx-sdr](https://github.com/matthewwall/weewx-sdr) and
  [weewx-meteostick](https://github.com/matthewwall/weewx-meteostick); the decoder descends from
  [bemasher's rtldavis](https://github.com/bemasher/rtldavis).
- Installer packaging: Vince Skahan ([weewx-contrib](https://github.com/weewx-contrib/weewx-rtldavis)).
- [librtlsdr](https://github.com/steve-m/librtlsdr): Steve Markgraf, maintained by Kacper
  Ludwinski. [gortlsdr](https://github.com/jpoirier/gortlsdr): Joseph Poirier.
- InfluxDB uploader: Matthew Wall's [weewx-influx](https://github.com/matthewwall/weewx-influx),
  ported to InfluxDB 2 by [David Lutz](https://github.com/david-lutz/weewx-influx2). WeatherCloud
  uploader: Matthew Wall. OgoXe uploader: the OgoXe developers, Sigi Meisenbichler and Vince Skahan.
  Wind calibration table: kobuki.
- LloydR, whose upstream reports on duplicate frames and the temperature sign pointed the way to
  two of the fixes here.

Full provenance, file by file: [CHANGES-FROM-UPSTREAM.md](CHANGES-FROM-UPSTREAM.md).

## License

GPLv3. See [LICENSE](LICENSE).
