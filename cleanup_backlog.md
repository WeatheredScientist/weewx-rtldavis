# Eagle Hunt PWS — Cleanup & Optimization Backlog
Last updated: May 27, 2026

## weewx.conf
- [x] Remove `[StdReport]` FTP/RSYNC sections — decided to keep for user reference ✅
- [x] WOW-BE — credentials configured, posting confirmed ✅
- [x] Fix duplicate `handlers = rotate,` lines — confirmed not duplicates, correct as-is ✅
- [x] Clean up placeholder credentials — removed leaked WU password from FTP section ✅
- [x] Set `debug = 0` ✅
- [x] Report generation disabled (StdReport removed from report_services) ✅
- [x] FTP and RSYNC disabled ✅
- [x] WOW post_interval = 300 (fixed 429 errors) ✅
- [x] windSpeed QC ceiling = 120 mph (spurious spikes handled by acceleration filter) ✅

## Docker image (v1 — frozen at v1.0-ubuntu22)
- ~~Remove `busybox` from Dockerfile~~ — addressed in v2 (multistage build, build deps not in runtime) ✅
- ~~Remove `pkg-config` if not needed at runtime~~ — addressed in v2 (multistage) ✅
- ~~Remove redundant files in `/opt/weewx-data/bin/user/`~~ — addressed in v2 (multistage) ✅
- [x] Update entrypoint.sh — syslogd removed ✅
- [x] Rebuild and push Docker image with windy.py, owm.py (RESTThread), entrypoint.sh ✅
- [x] Update Dockerfile on GitHub ✅
- ~~Rebuild v1 with dewpoint_service.py MAX_WIND_DELTA=75~~ — baked into v2 instead; v1 frozen ✅

## Docker image (v2 — Ubuntu 26.04, Python 3.14, multistage)
- [x] New Dockerfile written — multistage, no restx.py patches, librtlsdr from src.tgz ✅
- [x] logging.additions created — file + stdout logging ✅
- [x] dewpoint_service.py MAX_WIND_DELTA=75 included ✅
- [x] Build succeeds — 278MB (72% reduction from v1) ✅
- [x] Tested on NAS — all 8 services confirmed posting ✅
- [x] Push as weatheredscientist/weewx-rtldavis:v2-ubuntu26 ✅
- [x] Tagged as latest ✅
- [x] GitHub release v2.0-ubuntu26 created ✅
- [x] docker-compose.yml added to GitHub ✅
- [x] README updated for v2 (Ubuntu 26.04, Python 3.14, multistage, stdout logging) ✅

## weewx_monitor.py
- [x] Fix log rotation false alerts ✅
- [x] Move credentials to environment variables (monitor.env) ✅
- [x] Add .gitignore and monitor.env.example to GitHub ✅
- [x] Remove unused `subprocess` import — now reads log directly from NAS ✅
- [x] Remove unused `USB_DEV` constant ✅
- [x] USB reset via sudo usb_reset.sh (security hardening) ✅
- [x] Monitor runs as weewx-monitor (limited user, not root) ✅
- [x] usb_reset.sh created, root-owned, added to GitHub ✅
- [x] WU-RF reception tracking added — 60s windows, 60% alert threshold, 5-min summary log, daily email summary ✅
- [x] Duplicate content bug fixed — clean single copy ✅
- [x] Pushed to GitHub ✅

## dewpoint_service.py
- [x] MAX_WIND_DELTA raised from 25 to 75 mph/sample ✅
- [x] Updated on GitHub ✅
- [x] Copied to running container ✅

## Services
- [x] Windy — rewritten using RESTThread, now stable ✅
- [x] OWM — rewritten using RESTThread, now stable ✅
- [x] WOW — post_interval = 300, no more 429 errors ✅
- [x] WOW-BE — credentials configured, posting confirmed ✅
- [ ] Verify OWM measurements appear in their API over time

## rtldavis stability
- [x] USB extension cable added ✅
- [x] Antenna rotated vertical ✅
- [x] Report generation disabled (was causing CPU contention) ✅
- [x] debug = 0 (was causing log flooding) ✅
- [x] RTL-SDR gain tuned to -gain 400 (improved reception baseline) ✅
- ~~Consider upgrading to RTL-SDR Blog V4 with TCXO~~ (V4 discontinued, PPM drift not significant)
- [ ] Monitor long-term stability

## Security
- [x] weewx_monitor.py runs as dedicated limited user (weewx-monitor) ✅
- [x] USB reset scoped to usb_reset.sh via sudo — no other root access ✅
- [x] usb_reset.sh root-owned, not writable by weewx-monitor ✅
- [x] Sudoers rule recreated on every boot via Task Scheduler ✅
- [x] Monitor credentials in monitor.env (gitignored) ✅
- [x] Document dedicated user setup in README ✅

## GitHub / Docker Hub
- [x] Tag current image as v1.0-ubuntu22 on Docker Hub ✅
- [x] Tag GitHub repo as v1.0-ubuntu22 release ✅
- [x] Build and test v2 image (Ubuntu 26.04, Python 3.14, multistage) ✅
- [x] Push v2 as weatheredscientist/weewx-rtldavis:v2-ubuntu26 ✅
- [x] Tag v2 as latest ✅
- [x] GitHub release v2.0-ubuntu26 created ✅
- [x] Same repo, tags differentiate versions ✅
- [x] weewx.conf.example with documented upload rates ✅
- [x] weewx.conf.example updated with correct windSpeed comment ✅
- [x] README.md pushed to GitHub — v2 specs ✅
- [x] docker-compose.yml added to GitHub ✅
- [x] logging.additions added to GitHub ✅
- [x] weewx_monitor.py — reception tracking, clean single copy pushed ✅
- [x] weewx.conf.example — duplicate content fixed, credentials scrubbed ✅
- [x] docker-compose.yml — duplicate content fixed ✅
- [x] README.md — WOW-BE setup, reception monitoring section added ✅
- [ ] Update README with Windows/macOS Docker Desktop USB investigation findings

## Reception Monitoring
- [x] WU-RF reception tracking added to weewx_monitor.py ✅
- [x] 60s windows, alert after 5 consecutive windows below 60% threshold ✅
- [x] 5-min summary logged (OK/LOW + avg %) ✅
- [x] Daily email summary at midnight (hourly breakdown table) ✅
- [x] RTL-SDR gain tuned to -gain 400 ✅
- [x] Baseline established: ~70% avg at 150ft through walls — expected for environment ✅
- [x] WOW-BE added to monitor thresholds ✅

## Monitoring
- [x] USB watchdog auto-reset via unbind/rebind ✅
- [x] Email alerting with recovery and repeat ✅
- [x] Task Scheduler startup on boot ✅
- [x] Windy station visible on map ✅
- [x] weewx_monitor.log rotation via logrotate (daily, 30 days, DSM Task Scheduler) ✅
- [x] Fix monitor false alarm on startup — last_seen initialized to 0, countdown starts after first post seen ✅
- [x] WOW-BE monitoring added ✅

## Hardware (future)
- [ ] Investigate Windows/macOS Docker Desktop USB support for FHSS — document findings, possibly add workaround instructions
- [ ] ESP32 sensor node: lightning (AS3935), pressure (BMP390), air quality (SEN55)
- [ ] Solar power for ESP32 node — shopping list done
- [ ] Consider Blitzortung System Blue (lightning detection network) — longer term
