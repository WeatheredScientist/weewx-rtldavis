# weewx-rtldavis

A Docker image for running [weewx](https://weewx.com/) with the [rtldavis](https://github.com/lheijst/weewx-rtldavis) driver, enabling a Davis Vantage weather station to upload data to multiple online weather services using an RTL-SDR USB dongle — no proprietary Davis hardware required.

> **Developed and tested on:** Davis Vantage Pro 2 Plus ISS · Synology DS918+ NAS · DSM 7.3.2-86009 Update 3  
> **Base image:** Ubuntu 26.04 LTS · Python 3.14 · weewx 5.3.1  
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
# Note: bus and device numbers will vary by system; 0bda:2838 is the common Realtek RTL2832U chip ID
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
  -v /dev/bus/usb:/dev/bus/usb \
  -v /your/path/weewx-data:/opt/weewx-data \
  -v /your/path/logs:/var/log/weewx \
  weatheredscientist/weewx-rtldavis:latest
```
> `--privileged` is required for USB device access.

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

Posting too frequently causes HTTP 429 (rate limit) errors. These are the tested safe intervals:

| Service | Recommended | Maximum | Notes |
|---------|------------|---------|-------|
| WU Rapidfire | 2.5 sec | 2.5 sec | Every LOOP packet |
| WU PWS archive | 60 sec | 60 sec | Every archive record |
| PWSweather | 60 sec | 60 sec | No hard limit documented |
| CWOP | 300 sec | 300 sec | MADIS samples every 5 min |
| WOW | 300 sec | 300 sec | 429 error confirmed if < 5 min |
| AWEKAS | 300 sec | 300 sec | Account minimum |
| WeatherCloud | 600 sec | 60 sec* | *60 sec requires paid Pro/Premium plan |
| Windy | 300 sec | 300 sec | Documented 5 min interval |
| OWM | 60 sec | 60 sec | Matches finest aggregation bucket |

> ⚠️ **WOW (Met Office) is being decommissioned in late 2026.** Consider WOW-BE as an alternative.

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
1. Register at [wxqa.com](http://wxqa.com) to get a CW/DW/GW station number
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
> ⚠️ Being decommissioned late 2026. Consider WOW-BE instead.
1. Register at [wow.metoffice.gov.uk](https://wow.metoffice.gov.uk)
2. In `weewx.conf`:
```ini
[[WOW]]
    enable = true
    station = YOUR_STATION_UUID
    password = "YOUR_AWS_PIN"
    post_interval = 300
```

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

## Synology NAS: USB Watchdog & Email Alerts

The included `weewx_monitor.py` runs on the NAS host (outside Docker) and:
- Detects rtldavis stalls and automatically resets the USB dongle
- Sends email alerts when any service has been down beyond its threshold
- Sends recovery emails when services resume
- Repeats alerts every 2 hours for ongoing outages

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
```bash
cat > /volume1/docker/weewx-rtldavis/monitor.env << 'EOF'
ALERT_FROM=your_gmail@gmail.com
ALERT_TO=your_alert_destination@example.com
GMAIL_PASS="your_gmail_app_password"
EOF
```
> Gmail app password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (requires 2FA enabled)

4. **Update Task Scheduler script** (Control Panel → Task Scheduler → edit `weewx_monitor`, set User to `root`):
```bash
# Add sudoers rule for weewx-monitor (recreated on each boot in case of DSM update)
echo 'weewx-monitor ALL=(root) NOPASSWD: /volume1/docker/weewx-rtldavis/usb_reset.sh' >> /etc/sudoers

# Start monitor as weewx-monitor user
set -a
source /volume1/docker/weewx-rtldavis/monitor.env
set +a
rm -f /volume1/docker/weewx-rtldavis/logs/weewx_monitor.pid
sudo -u weewx-monitor -E python3 -u /volume1/docker/weewx-rtldavis/weewx_monitor.py >> /volume1/docker/weewx-rtldavis/logs/weewx_monitor.log 2>&1 &
```

> **Note:** The USB device path `1-3` in `usb_reset.sh` is specific to the DS918+. Check your path with `lsusb` and update accordingly.

### Alert Thresholds

Default thresholds in `weewx_monitor.py`:

| Service | Alert after |
|---------|------------|
| Wunderground-RF | 10 min |
| PWSweather | 60 min |
| CWOP | 60 min |
| WOW | 60 min |
| AWEKAS | 60 min |
| Windy | 60 min |
| WeatherCloud | 30 min |
| OWM | 60 min |


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

**HTTP 429 rate limit errors**
- Add or reduce `post_interval` for the affected service — see rate table above
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
| `weewx_monitor.py` | NAS-side USB watchdog and service alert monitor |
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

## Credits

- [weewx](https://weewx.com/) — Tom Keffer and Matthew Wall
- [weewx-rtldavis driver](https://github.com/weewx-contrib/weewx-rtldavis) — Vince Skahan
- [rtldavis Go binary](https://github.com/lheijst/rtldavis) — Luc Heijst (fork of bemasher/rtldavis)
- [librtlsdr](https://github.com/steve-m/librtlsdr) — Steve Markgraf

---

## License

GPL v3
# weewx-rtldavis

A Docker image for running [weewx](https://weewx.com/) with the [rtldavis](https://github.com/lheijst/weewx-rtldavis) driver, enabling a Davis Vantage weather station to upload data to multiple online weather services using an RTL-SDR USB dongle — no proprietary Davis hardware required.

> **Developed and tested on:** Davis Vantage Pro 2 Plus ISS · Synology DS918+ NAS · DSM 7.3.2-86009 Update 3  
> **Base image:** Ubuntu 22.04 LTS · Python 3.10 · weewx 5.3.1  
> **Looking for the latest image?** See weewx-rtldavis-latest (Ubuntu 26.04 · Python 3.14) — coming soon

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
# Note: bus and device numbers will vary by system; 0bda:2838 is the common Realtek RTL2832U chip ID
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
  -v /dev/bus/usb:/dev/bus/usb \
  -v /your/path/weewx-data:/opt/weewx-data \
  -v /your/path/logs:/var/log/weewx \
  weatheredscientist/weewx-rtldavis:latest
```
> `--privileged` is required for USB device access.

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

Posting too frequently causes HTTP 429 (rate limit) errors. These are the tested safe intervals:

| Service | Recommended | Maximum | Notes |
|---------|------------|---------|-------|
| WU Rapidfire | 2.5 sec | 2.5 sec | Every LOOP packet |
| WU PWS archive | 60 sec | 60 sec | Every archive record |
| PWSweather | 60 sec | 60 sec | No hard limit documented |
| CWOP | 300 sec | 300 sec | MADIS samples every 5 min |
| WOW | 300 sec | 300 sec | 429 error confirmed if < 5 min |
| AWEKAS | 300 sec | 300 sec | Account minimum |
| WeatherCloud | 600 sec | 60 sec* | *60 sec requires paid Pro/Premium plan |
| Windy | 300 sec | 300 sec | Documented 5 min interval |
| OWM | 60 sec | 60 sec | Matches finest aggregation bucket |

> ⚠️ **WOW (Met Office) is being decommissioned in late 2026.** Consider WOW-BE as an alternative.

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
1. Register at [wxqa.com](http://wxqa.com) to get a CW/DW/GW station number
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
> ⚠️ Being decommissioned late 2026. Consider WOW-BE instead.
1. Register at [wow.metoffice.gov.uk](https://wow.metoffice.gov.uk)
2. In `weewx.conf`:
```ini
[[WOW]]
    enable = true
    station = YOUR_STATION_UUID
    password = "YOUR_AWS_PIN"
    post_interval = 300
```

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

## Synology NAS: USB Watchdog & Email Alerts

The included `weewx_monitor.py` runs on the NAS host (outside Docker) and:
- Detects rtldavis stalls and automatically resets the USB dongle
- Sends email alerts when any service has been down beyond its threshold
- Sends recovery emails when services resume
- Repeats alerts every 2 hours for ongoing outages

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
```bash
cat > /volume1/docker/weewx-rtldavis/monitor.env << 'EOF'
ALERT_FROM=your_gmail@gmail.com
ALERT_TO=your_alert_destination@example.com
GMAIL_PASS="your_gmail_app_password"
EOF
```
> Gmail app password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (requires 2FA enabled)

4. **Update Task Scheduler script** (Control Panel → Task Scheduler → edit `weewx_monitor`, set User to `root`):
```bash
# Add sudoers rule for weewx-monitor (recreated on each boot in case of DSM update)
echo 'weewx-monitor ALL=(root) NOPASSWD: /volume1/docker/weewx-rtldavis/usb_reset.sh' >> /etc/sudoers

# Start monitor as weewx-monitor user
set -a
source /volume1/docker/weewx-rtldavis/monitor.env
set +a
rm -f /volume1/docker/weewx-rtldavis/logs/weewx_monitor.pid
sudo -u weewx-monitor -E python3 -u /volume1/docker/weewx-rtldavis/weewx_monitor.py >> /volume1/docker/weewx-rtldavis/logs/weewx_monitor.log 2>&1 &
```

> **Note:** The USB device path `1-3` in `usb_reset.sh` is specific to the DS918+. Check your path with `lsusb` and update accordingly.

### Alert Thresholds

Default thresholds in `weewx_monitor.py`:

| Service | Alert after |
|---------|------------|
| Wunderground-RF | 10 min |
| PWSweather | 60 min |
| CWOP | 60 min |
| WOW | 60 min |
| AWEKAS | 60 min |
| Windy | 60 min |
| WeatherCloud | 30 min |
| OWM | 60 min |


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

**No data / rtldavis stalled**
- Ensure antenna is vertical and fully extended
- Use a USB extension cable (1–3m) away from the NAS
- Check log: `tail -f /your/path/logs/weewx.log`
- The USB watchdog will auto-reset after 150 seconds of no data

**HTTP 429 rate limit errors**
- Add or reduce `post_interval` for the affected service — see rate table above
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
| `weewx_monitor.py` | NAS-side USB watchdog and service alert monitor |
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

## Credits

- [weewx](https://weewx.com/) — Tom Keffer and Matthew Wall
- [weewx-rtldavis driver](https://github.com/weewx-contrib/weewx-rtldavis) — Vince Skahan
- [rtldavis Go binary](https://github.com/lheijst/rtldavis) — Luc Heijst (fork of bemasher/rtldavis)
- [librtlsdr](https://github.com/steve-m/librtlsdr) — Steve Markgraf

---

## License

GPL v3
# weewx-rtldavis
Dockerized weewx weather station for wireless Davis ISS using RTL-SDR dongle

A ready-to-run Docker container for a Davis Vantage Vue or Vantage Pro 2 weather station using an RTL-SDR USB dongle and [weewx](https://weewx.com). No Davis console or WeatherLink subscription required.

## What it does
- Receives data directly from your Davis ISS transmitter via RTL-SDR dongle
- Runs weewx to process and upload weather data
- Posts to Weather Underground (rapidfire), WOW, CWOP, and PWSweather
- Calculates and caches dewpoint across packets
- Optionally fetches pressure from Davis WeatherLink cloud API (free tier, once/hour)

## Requirements
- Davis Vantage Vue or Vantage Pro 2 ISS
- RTL-SDR Blog V3 dongle (or compatible RTL2838)
- Docker host with native Linux USB access (Synology NAS, Linux PC, Raspberry Pi)
- **Note:** WSL2 and VirtualBox USB passthrough do not work reliably with this dongle due to I2C timing issues

## Quick Start

### 1. Pull the image
docker pull weatheredscientist/weewx-rtldavis

### 2. Copy config out of image
mkdir -p ~/weewx-data
docker run --rm -v ~/weewx-data:/backup weatheredscientist/weewx-rtldavis cp -r /opt/weewx-data/. /backup/

### 3. Edit configuration
Edit `~/weewx-data/weewx.conf` and set:
- Station location, latitude, longitude, altitude
- Weather Underground station ID and key
- WOW, CWOP, PWSweather credentials as needed

### 4. Run
docker run -d 
--name weewx-rtldavis 
--privileged 
--restart unless-stopped 
-v /dev/bus/usb:/dev/bus/usb 
-v ~/weewx-data:/opt/weewx-data 
weatheredscientist/weewx-rtldavis

## Optional: Pressure via Davis WeatherLink API

If you have a Davis WeatherLink account (free tier), you can fetch pressure once per hour. Add this to `weewx.conf`:
[DavisPressure]
api_key = YOUR_API_KEY
api_secret = YOUR_API_SECRET
station_id = YOUR_STATION_ID
fetch_interval = 3600

Get your free API credentials at [weatherlink.com](https://weatherlink.com) → Account → Generate v2 Token.

To find your station ID, use the Davis v2 API stations endpoint with your credentials.

## Synology NAS Notes
Plug the RTL-SDR dongle directly into a USB port on the NAS. No driver installation needed — the container handles everything.

## License
GPL v3
