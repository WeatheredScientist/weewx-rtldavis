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
