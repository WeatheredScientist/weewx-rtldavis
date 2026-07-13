# weewx-rtldavis

An unofficial Docker distribution of a Davis Vantage receiver stack: [weewx](https://weewx.com/) plus a **patched** version of Luc Heijst's [rtldavis](https://github.com/lheijst/weewx-rtldavis) driver. It intercepts a Davis Vantage station off the air with an RTL-SDR USB dongle and uploads to multiple weather services — no proprietary Davis hardware required.

> **This is not stock upstream.** The driver shipped here is a fork of rtldavis v0.20 and reports
> itself as `0.20+ws.1`. It carries a rain-counter glitch filter, a decode-layer sensor plausibility
> filter, and five bug fixes that do not exist upstream — see
> **[CHANGES-FROM-UPSTREAM.md](CHANGES-FROM-UPSTREAM.md)** for every divergence, why it is there, and
> whether it is headed upstream.
>
> This project is **not affiliated with or endorsed by** Luc Heijst, Vince Skahan, or the weewx
> project. It is built on their work (see [Credits](#credits)); its bugs are its own. GPLv3.

📦 **Docker Hub:** [`weatheredscientist/weewx-rtldavis`](https://hub.docker.com/r/weatheredscientist/weewx-rtldavis)
```bash
docker pull weatheredscientist/weewx-rtldavis:v2.0.7   # or :latest
```
Pin a version tag (`:v2.0.7`) for reproducible deploys; `:latest` always tracks the newest release.

> **Current version:** v2.0.7 — **upgrade if you are on any earlier tag.**
> **New in v2.0.7: the root logger is overridden** (DEC-0043). weewx's own defaults point the *root*
> logger at a syslog handler on `/dev/log` — a socket that does not exist in a container. Earlier images
> overrode only the `weewx` and `user` loggers, but `weewxd` and `weeutil.*` are in neither namespace, so
> they fell through to root and raised there: ~15 logging-error tracebacks to stderr on every start, and —
> the half that actually matters — **every startup diagnostic silently lost.** The version banner, the
> config path and the group list had never once reached `weewx.log`. They do now.
>
> Still carried from v2.0.6, and still the reason to upgrade from anything older: (1) **the driver you
> actually run** — earlier compose files bind-mounted the *stock* driver over the patched one, so the
> rain-glitch filter and SensorQC were silently inert; (2) **StdPrint removed** — weewx's default printed
> every LOOP packet to stdout, and (3) **the console log handler defaults to `WARNING`**. Both of those fed
> a container-freeze hazard: stdout is a pipe, and if the Docker log consumer stalls, the next write
> **blocks forever** — no crash, no traceback, and a container that still reports `Up`. That cost us a
> 7-hour outage. See the [CHANGELOG](CHANGELOG.md).  
> **Developed and tested on:** Davis Vantage Pro 2 Plus ISS · Synology DS918+ NAS · DSM 7.3.2-86009 Update 3  
> **Base image:** Ubuntu 26.04 LTS · Python 3.14 · weewx 5.4.0  
> **Previous version:** [v1.0-ubuntu22](https://github.com/weatheredscientist/weewx-rtldavis/releases/tag/v1.0-ubuntu22) — Ubuntu 22.04 · Python 3.10 (stable, frozen)

---

## What This Does

This image lets your Davis Vantage weather station upload live data to:

| Service | URL | Default interval |
|---------|-----|-----------------|
| Weather Underground | wunderground.com | Rapidfire (2.5s) + archive (1 min) |
| PWSweather | pwsweather.com | 1 min |
| CWOP/APRS | wxqa.com | 5 min — feeds NOAA/MADIS |
| WOW Met Office | wow.metoffice.gov.uk | 5 min — **being decommissioned late 2026** |
| WOW-BE | wow.meteo.be | 5 min — WOW successor |
| AWEKAS | awekas.at | 5 min |
| WeatherCloud | weathercloud.net | 10 min (Basic plan) |
| Windy | windy.com | 5 min |
| OpenWeatherMap | openweathermap.org | 1 min |

---

## Hardware Requirements

- **Davis Vantage Pro, Pro 2, or Vue** ISS transmitter
- **RTL-SDR USB dongle** — tested with RTL-SDR Blog V3 (Realtek RTL2838, USB ID 0bda:2838 or similar)
- A Linux-based computer or NAS to run Docker — tested on Synology DS918+

### ⚠️ Windows and macOS — potential USB limitations

The Davis ISS uses **frequency hopping spread spectrum (FHSS)** across 51 channels in the 915 MHz band. The rtldavis driver needs real-time, low-latency USB access to track these hops. On Windows, Docker Desktop passes USB through WSL2 which introduces timing jitter that can disrupt frequency hop tracking — this has been observed to cause failures. macOS has been confirmed working in some configurations despite similar USB virtualization. **Linux is the most reliable host** — either a Linux PC, server, or a Linux-based NAS such as Synology running Docker natively. Windows support is an open area of investigation; macOS may work depending on configuration.

### Antenna Tips
- Mount the antenna **vertically** — Davis ISS transmits with vertical polarization
- Use a **USB extension cable** (1–3m) to move the dongle away from your computer/NAS to reduce RF interference
- Avoid placing the dongle inside metal enclosures
- For challenging RF environments (long distances, walls), consider tuning the RTL-SDR gain manually: add `-gain 400` to the `cmd` line in `weewx.conf` under `[Rtldavis]`

---

## Quick Start

### 1. Install Docker
- **Synology NAS:** Install Container Manager from Package Center
- **Linux:** Install [Docker Engine](https://docs.docker.com/engine/install/)

### 2. Plug in your RTL-SDR dongle
Connect the dongle to a USB port. Verify it is detected:
```bash
lsusb | grep -i realtek
# Should show a line containing: ID 0bda:2838 Realtek Semiconductor Corp.
```

### 3. Create directories
```bash
mkdir -p /your/path/weewx-data
mkdir -p /your/path/logs
```
On Synology: `/volume1/docker/weewx-rtldavis/weewx-data` and `/volume1/docker/weewx-rtldavis/logs`

### 4. Run the container
```bash
docker run -d \
  --name weewx-rtldavis \
  --privileged \
  --restart unless-stopped \
  -e TZ=America/New_York \
  -v /dev/bus/usb:/dev/bus/usb \
  -v /your/path/weewx-data:/opt/weewx-data \
  -v /your/path/logs:/var/log/weewx \
  weatheredscientist/weewx-rtldavis:latest
```
> `--privileged` is required for USB device access. Set `TZ` to your local timezone (e.g. `America/Los_Angeles`, `Europe/London`) to ensure daily rain totals reset at local midnight.

### 5. Configure weewx
The container creates a default `weewx.conf` on first run. Edit it with your station details and credentials. A fully documented template is available: [weewx.conf.example](weewx.conf.example)

Key settings:
```ini
[Station]
    location = Your Town, State
    latitude = XX.XXXX
    longitude = -XX.XXXX
    altitude = XXX, foot

[Rtldavis]
    transceiver_frequency = US    # US, EU, or NZ
    iss_channel = 1               # Match your ISS DIP switch setting
    rain_bucket_type = 0          # 0 = 0.01 inch, 1 = 0.2 mm
```

### 6. Restart and verify
```bash
docker restart weewx-rtldavis
tail -f /your/path/logs/weewx.log
```
You should see lines like:
```
weewx.restx INFO Wunderground-RF: Published record ...
weewx.restx INFO CWOP: Published record ...
```

---

## Upload Rate Reference

| Service | Recommended | Maximum | Notes |
|---------|------------|---------|-------|
| WU Rapidfire | 2.5 sec | 2.5 sec | Every LOOP packet |
| WU PWS archive | 60 sec | 60 sec | Every archive record |
| PWSweather | 60 sec | 60 sec | No hard limit documented |
| CWOP | 300 sec | 300 sec | MADIS samples every 5 min |
| WOW | 300 sec | 300 sec | 429 error confirmed if < 5 min |
| WOW-BE | 300 sec | 300 sec | WOW successor |
| AWEKAS | 300 sec | 300 sec | Account minimum |
| WeatherCloud | 600 sec | 60 sec* | *60 sec requires paid Pro/Premium plan |
| Windy | 300 sec | 300 sec | Documented 5 min interval |
| OWM | 60 sec | 60 sec | Matches finest aggregation bucket |

> ⚠️ **WOW (Met Office) is being decommissioned in late 2026.** Use WOW-BE as the replacement.

---

## Enabling Weather Services

### Weather Underground
1. Register at [wunderground.com/member/devices](https://www.wunderground.com/member/devices)
2. In `weewx.conf`:
```ini
[[Wunderground]]
    enable = true
    station = YOUR_STATION_ID
    password = YOUR_API_KEY
    rapidfire = true
    archive_post = true
```

### PWSweather
1. Register at [pwsweather.com](https://pwsweather.com)
2. In `weewx.conf`:
```ini
[[PWSweather]]
    enable = true
    station = YOUR_STATION_ID
    password = YOUR_API_KEY
```

### CWOP (free, feeds NOAA/MADIS)
1. Register at [wxqa.com](http://wxqa.com)
2. In `weewx.conf`:
```ini
[[CWOP]]
    enable = true
    station = YOUR_CWOP_ID
    passcode = -1
    server_list = cwop.aprs.net:14580, cwop.aprs.net:23
    post_interval = 300
```

### WOW Met Office
> ⚠️ Being decommissioned late 2026. Use WOW-BE instead.
1. Register at [wow.metoffice.gov.uk](https://wow.metoffice.gov.uk)
2. In `weewx.conf`:
```ini
[[WOW]]
    enable = true
    station = YOUR_STATION_UUID
    password = "YOUR_AWS_PIN"
    post_interval = 300
```

### WOW-BE (Belgian Met Office — WOW successor)
1. Register at [wow.meteo.be](https://wow.meteo.be) — create an account and register your station
2. You will receive an email with your station ID (short and long UUID) and authentication key
3. In `weewx.conf`:
```ini
[[WOW-BE]]
    enable = true
    station = YOUR_STATION_UUID
    password = "YOUR_AUTH_KEY"
    post_interval = 300
```
> Requires weewx 5.2.0 or higher. The endpoint `https://wow.meteo.be/api/v2/send` is configured automatically.

### AWEKAS
1. Register at [awekas.at](https://www.awekas.at)
2. In `weewx.conf`:
```ini
[[AWEKAS]]
    enable = true
    username = YOUR_USERNAME
    password = YOUR_PASSWORD
    post_interval = 300
```

### WeatherCloud
1. Register at [app.weathercloud.net](https://app.weathercloud.net)
2. In `weewx.conf`:
```ini
[[WeatherCloud]]
    enable = true
    id = YOUR_DEVICE_ID
    key = YOUR_DEVICE_KEY
    post_interval = 600
```

### Windy
1. Register at [stations.windy.com](https://stations.windy.com)
2. In `weewx.conf`:
```ini
[[Windy]]
    enable = true
    station_id = YOUR_STATION_ID
    password = YOUR_API_KEY
    post_interval = 300
```

### OpenWeatherMap
1. Create account at [openweathermap.org](https://openweathermap.org)
2. Register your station via their [Stations API](https://openweathermap.org/api/stations)
3. In `weewx.conf`:
```ini
[[OWM]]
    enable = true
    api_key = YOUR_API_KEY
    station_id = YOUR_INTERNAL_STATION_ID
```

> See [weewx.conf.example](weewx.conf.example) for all services with full documentation and rate limit comments.

---

## Synology NAS: USB Watchdog, Email Alerts & Reception Monitoring

The included `weewx_monitor.py` runs on the NAS host (outside Docker) and:
- Detects rtldavis stalls and automatically resets the USB dongle
- Sends email alerts when any service has been down beyond its threshold
- Sends recovery emails when services resume
- Repeats alerts every 2 hours for ongoing outages
- Tracks WU Rapidfire RF reception quality — alerts when packet reception drops below threshold
- Sends a daily email summary of RF reception by hour

### RF Reception Monitoring

The monitor tracks how many WU Rapidfire packets are received per 60-second window (expected: ~24/min for Davis VP2). If reception drops below 60% for 5 consecutive minutes, an alert email is sent. A 5-minute summary is logged, and a full hourly breakdown is emailed daily at midnight.

Default alert thresholds:

| Service | Alert after |
|---------|------------|
| Wunderground-RF | 10 min |
| PWSweather | 60 min |
| CWOP | 60 min |
| WOW | 60 min |
| WOW-BE | 60 min |
| AWEKAS | 60 min |
| Windy | 60 min |
| WeatherCloud | 30 min |
| OWM | 60 min |
| RF reception | 5 consecutive minutes below 60% |

### Security Note

The monitor needs to reset the USB dongle, which requires root access to `/sys/bus/usb/drivers/usb/`. Rather than running the entire monitor as root, the recommended setup uses a **dedicated limited user** (`weewx-monitor`) that can only run the single USB reset script via `sudo` — nothing else.

The Task Scheduler script (which runs as root on boot) adds the narrow sudoers rule, then drops privileges to run the monitor as `weewx-monitor`. This means:
- A bug or exploit in the monitor cannot affect the rest of the NAS
- The only escalation possible is running `usb_reset.sh` — which only does the USB bind/unbind
- `usb_reset.sh` is owned by root and not writable by `weewx-monitor`

> Note: Synology DSM may overwrite `/etc/sudoers` on system updates. The Task Scheduler script recreates the sudoers rule on every boot, so it survives updates automatically.

### Setup

1. **Create a dedicated user** in DSM: Control Panel → User & Group → Create
   - Username: `weewx-monitor`
   - Group: `users` only (no admin, no docker, no http)
   - No shared folder permissions
   - No application permissions

2. **Grant write access to logs directory:**
```bash
sudo synoacltool -add /volume1/docker/weewx-rtldavis/logs "user:weewx-monitor:allow:rwxp-DaARWc--:fd--"
```

3. **Create credentials file** (never commit to git — it is gitignored):
```
ALERT_FROM=your_gmail@gmail.com
ALERT_TO=your_alert_destination@example.com
GMAIL_PASS="your_gmail_app_password"
STATION_NAME="My Weather Station"
```
Save as `/volume1/docker/weewx-rtldavis/monitor.env`

> Gmail app password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (requires 2FA enabled)

4. **Update Task Scheduler script** (Control Panel → Task Scheduler → edit `weewx_monitor`, set User to `root`):
```bash
echo 'weewx-monitor ALL=(root) NOPASSWD: /volume1/docker/weewx-rtldavis/usb_reset.sh' >> /etc/sudoers
set -a
source /volume1/docker/weewx-rtldavis/monitor.env
set +a
rm -f /volume1/docker/weewx-rtldavis/logs/weewx_monitor.pid
sudo -u weewx-monitor -E python3 -u /volume1/docker/weewx-rtldavis/weewx_monitor.py >> /volume1/docker/weewx-rtldavis/logs/weewx_monitor.log 2>&1 &
```

> **Note:** The USB device path `1-3` in `usb_reset.sh` is specific to the DS918+. Check your path with `lsusb` and update accordingly.

### Log Rotation (weewx_monitor.log)

The weewx log (`weewx.log`) is rotated automatically by weewx's built-in `TimedRotatingFileHandler` — no extra setup needed.

The monitor log (`weewx_monitor.log`) needs separate rotation. On Synology, use `logrotate` via DSM Task Scheduler:

1. **Create the logrotate config** (run once as root):
```bash
tee /etc/logrotate.d/weewx-monitor << 'LREOF'
/volume1/docker/weewx-rtldavis/logs/weewx_monitor.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
LREOF
```

2. **Add to DSM Task Scheduler** (Control Panel → Task Scheduler → Create → Scheduled Task):
   - **Task name:** `logrotate-weewx`
   - **Schedule:** Daily at 00:05
   - **User:** root
   - **Script:** `logrotate /etc/logrotate.d/weewx-monitor`

> `copytruncate` allows rotation without restarting the monitor process.

---

## Pressure Service (Davis WeatherLink API)

If your Davis station does not report barometric pressure via the ISS (e.g. ISS-only setups without a console), you can fetch pressure from the Davis WeatherLink Cloud API hourly.

1. Get API credentials at [weatherlink.com/develop](https://www.weatherlink.com/develop)
2. Add to `weewx.conf`:
```ini
[DavisPressure]
    api_key = YOUR_API_KEY
    api_secret = YOUR_API_SECRET
    station_id = YOUR_NUMERIC_STATION_ID
    fetch_interval = 3600
```
3. Add `user.pressure_service.DavisPressureFetcher` to `process_services` in `weewx.conf`

---

## Troubleshooting

**Switching between container versions**
When stopping one weewx-rtldavis container and starting another, the RTL-SDR USB device may not be released cleanly. Reset it first:
```bash
echo '1-3' | sudo tee /sys/bus/usb/drivers/usb/unbind
sleep 2
echo '1-3' | sudo tee /sys/bus/usb/drivers/usb/bind
sleep 2
```
> The device path `1-3` is specific to the Synology DS918+. Check yours with `lsusb`.

**No data / rtldavis stalled**
- Ensure antenna is vertical and fully extended
- Use a USB extension cable (1–3m) away from the NAS
- Check log: `tail -f /your/path/logs/weewx.log`
- The USB watchdog will auto-reset after 150 seconds of no data

**Low RF reception**
- Normal packet reception for Davis VP2 is ~24 packets/min at close range
- At longer distances or through walls, 60–75% reception is common and does not cause data gaps
- Try tuning RTL-SDR gain manually: add `-gain 400` to the `cmd` line in `[Rtldavis]`
- Ensure antenna is vertical and not inside a metal enclosure

**HTTP 429 rate limit errors**
- Reduce `post_interval` for the affected service — see rate table above
- WOW specifically requires `post_interval = 300`

**weewx.conf parse error on startup**
- Check for duplicate `enable =` lines
- Validate: `docker exec weewx-rtldavis /opt/weewx-venv/bin/python3 -c "import configobj; configobj.ConfigObj('/opt/weewx-data/weewx.conf', raise_errors=True)"`

**No WU rapidfire updates**
- Verify `rapidfire = true` is set under `[[Wunderground]]`

**Monitor not starting**
- Check `/your/path/logs/weewx_monitor.log` for errors
- Verify `monitor.env` exists and credentials are correct
- Verify `weewx-monitor` user has write access to logs directory

---

## Files

| File | Description |
|------|-------------|
| `Dockerfile` | Build instructions |
| `entrypoint.sh` | Container startup script |
| `weewx.conf.example` | Fully documented configuration template with rate limit comments |
| `dewpoint_service.py` | Dewpoint/heatindex calculation; caches sensor values across LOOP packets; wind spike filter |
| `pressure_service.py` | Fetches barometric pressure from Davis WeatherLink API |
| `wcloud.py` | WeatherCloud uploader |
| `windy.py` | Windy.com uploader |
| `owm.py` | OpenWeatherMap uploader |
| `weewx_monitor.py` | NAS-side USB watchdog, service alert monitor, and RF reception tracker |
| `usb_reset.sh` | USB dongle reset script — called via sudo by weewx_monitor.py |
| `monitor.env.example` | Template for monitor email credentials |

---

## Building from Source

```bash
git clone https://github.com/weatheredscientist/weewx-rtldavis
cd weewx-rtldavis
docker build -t weewx-rtldavis .
```

---

## Changelog

The full, session-tagged history lives in **[CHANGELOG.md](CHANGELOG.md)** (single source of truth), and
tagged releases with notes are on the **[GitHub Releases](https://github.com/WeatheredScientist/weewx-rtldavis/releases)**
page. Highlights of the latest release are summarized at the top of `CHANGELOG.md`.

## Credits

- [weewx](https://weewx.com/) — Tom Keffer and Matthew Wall
- [weewx-rtldavis weewx extension](https://github.com/lheijst/weewx-rtldavis) — Luc Heijst (driver and extension author)
- [rtldavis](https://github.com/lheijst/rtldavis) — Luc Heijst (RTL-SDR receiver for Davis weather stations)
- [weewx-rtldavis installer wrapper](https://github.com/weewx-contrib/weewx-rtldavis) — Vince Skahan
- [gortlsdr](https://github.com/jpoirier/gortlsdr) — Joseph Poirier (Go wrapper for librtlsdr)
- [librtlsdr](https://github.com/steve-m/librtlsdr) — Steve Markgraf (original author), Kacper Ludwinski (current maintainer)

Upstream component commits used in this image, as identified by Vince Skahan:

```
* librtlsdr - library to turn Realtek RTL2832 based DVB dongle into a SDR receiver
  from https://github.com/steve-m/librtlsdr.git
  commit ae0dd6d4f09088d13500a854091b45ad281ca4f0
  Author: Kacper Ludwinski <kac...@ludwinski.dev>
  Date:   Sun Nov 9 21:56:53 2025 +0000

* gortlsdr - 'go' wrapper around librtlsdr
  from https://github.com/jpoirier/gortlsdr.git
  commit 075e50ef422cf3ba193d1ba6d79a0efea89491e2
  Author: Joseph Poirier <jdpo...@gmail.com>
  Date:   Sat May 19 12:17:06 2018 -0500

* rtldavis - RTL-SDR receiver for Davis weather stations
  from https://github.com/lheijst/rtldavis
  commit b95d5d734e4666c90f3d7539d5e2acd9f80f7e43
  Author: Luc Heijst <ljm.h...@gmail.com>
  Date:   Fri Jun 5 08:43:42 2020 -0300

* weewx-rtldavis - the weewx extension as of 12/20/2025
  from https://github.com/lheijst/weewx-rtldavis/archive/master.zip
  commit 2f3b4b344fd70ab253aabfa837b0ffc76570c075
  Author: Luc Heijst <ljm.h...@gmail.com>
  Date:   Sat Jan 2 13:56:04 2021 -0300
```

---

## License

GPL v3
