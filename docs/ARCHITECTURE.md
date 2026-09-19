# Architecture — weewx-rtldavis

**Status:** Source of truth
**Last updated:** 2026-09-19 (S139) — re-verified against live marvin state after sitting untouched
since S17; the deploy-layers table below is now a pointer to `CONSTANTS.md` rather than a second
copy, per STANDARD rule 5 (a second copy is a defect — this one drifted to a stale NAS path across
the DEC-0118 marvin move without anyone noticing until now).

How the system is built. For the *data contract* consumers depend on, see INTERFACES.md.

## 1. The signal chain

```
Davis 6263 VP2+ ISS  ──915 MHz FHSS──▶  RTL-SDR Blog v3 (bias-tee-capable; LNA currently OUT,
                                                          see CONSTANTS.md hardware timeline)
                                              │
                                              ▼
                        rtldavis (Go binary, /usr/local/bin/rtldavis)
                          spawned by the driver: `-gain 372 -v -fc 0 -ppm 0`
                                              │  (decoded packets on stdout)
                                              ▼
                     user/rtldavis.py  (WeeWX driver — parses packets, windDir null fix,
                                         auto-appends -tf/-tr to the cmd line)
                                              │  LOOP packets (~2.5 s, METRICWX)
                                              ▼
                                     WeeWX engine (5.5.0, verified live 2026-09-19)
             ┌───────────────┬────────────────┼───────────────────┬──────────────────┐
             ▼               ▼                 ▼                   ▼                  ▼
     data_services    process_services   xtype_services   archive_services   restful_services
     loop_json_writer  StdConvert/Cal/QC   StdWXXTypes      StdArchive        11 uploaders +
     (→ loop-data.txt)  dewpoint_service    PressureCooker   (→ SQLite)        influx + ogoxe
                        pressure_service    RainRater
```

**The driver spawns the Go binary; the Go binary owns the SDR.** Only one `rtldavis` process can
hold the USB dongle — this is why there is no trivial "dev" receiver (PRINCIPLES §5) and why we use
`docker kill` for a clean device handoff (DEC-0008).

## 2. Active WeeWX service topology (live, S16-verified)

From `weewx.conf [Engine][Services]`:

| Group | Services |
|-------|----------|
| `data_services` | `user.loop_json_writer.LoopJsonWriter` |
| `process_services` | `StdConvert, StdCalibrate, StdQC, StdWXCalculate, user.dewpoint_service.DewpointCacher, user.pressure_service.DavisPressureFetcher` |
| `xtype_services` | `StdWXXTypes, StdPressureCooker, StdRainRater, StdDelta` |
| `archive_services` | `StdArchive` |
| `restful_services` | `StationRegistry, Wunderground, PWSweather, CWOP, WOW, WOWBE, AWEKAS, user.wcloud.WeatherCloud, user.windy.Windy, user.owm.OWM, user.influx.Influx, user.ogoxeUploader.OgoxeUploader` |

> **Removed (S47):** `user.loopdata.LoopData` was never in any active list; the `loopdata.py` mount
> and the `[LoopData]` config section were dead weight, now removed from the live container and
> `weewx.conf` (DEC-0005). The dashboard feed is `loop_json_writer`, not loopdata.

## 3. Deployment: what's mounted vs baked

The image is built from the `Dockerfile` (multistage Ubuntu 26.04 / Py 3.14, DEC-0002). At runtime the
container **volume-mounts** the hot-iteration files over the baked ones (DEC-0004).

**The authoritative, currently-verified mount table lives in `CONSTANTS.md`'s "Deploy layers"
section — deliberately not duplicated here (STANDARD rule 5).** A copy lived in this file through
S138: it named NAS paths (`/volume1/docker/weewx-rtldavis/...`) that stopped being true at the
DEC-0118 marvin move (2026-08-28/29) and nobody caught the drift for three weeks, because
`CONSTANTS.md` had already been updated and this file hadn't. Check `CONSTANTS.md` for which layer
wins in prod per file, current mount source paths, and the "decoy" files whose repo copy is not
their real source.

**Baked into the image (changing these requires an image REBUILD):**
`rtldavis.py` (the driver), `dewpoint_service.py`, `owm.py`, `pressure_service.py`, `wcloud.py`,
`windy.py`, `entrypoint.sh`.

Plus bind mounts for config/DB/skins and logs — see `CONSTANTS.md` for current host paths.

> ⚠️ **Driver is BAKED, not mounted — corrected S30 (2026-07-05).** The published `docker-compose.yml`
> example *and* an earlier version of this table listed `rtldavis.py` as volume-mounted from
> `weewx-data/bin/user/rtldavis.py`. The **running container does not mount it** (confirmed via
> `docker inspect` — no bind for `rtldavis.py` or `dewpoint_service.py`). weewx imports `user.*` from the
> baked venv `site-packages/user/`, and `Dockerfile:101` had been **clobbering** the patched driver with
> the stock `weectl extension install` copy — so every image shipped the **stock** driver (no rain filter,
> no H1/H2/M3), and driver "hot-swaps" to `weewx-data/bin/user/` never took effect (that path is not
> imported). This is why `rxCheckPercent` was NULL and the July-4 phantom rain was not rejected. Fixed in
> v2.0.3 (clobber removed). **Consequence: driver + dewpoint changes require an image rebuild**, and the
> redeploy `docker run` must **not** re-introduce a mount over `rtldavis.py`/`dewpoint_service.py`.

### pyc-cache gotcha
After editing any mounted `.py` the venv imports, clear its compiled cache or WeeWX runs the stale
bytecode:
```
find /opt/weewx-venv -name "*.pyc" -path "*/user/*" -delete
```

## 4. The entrypoint chain

`Docker → entrypoint.sh (baked; changes need rebuild) → weewxd /data/weewx.conf`

`entrypoint.sh` reads `BIAS_TEE` (default `1`) and drives the RTL-SDR's bias-tee accordingly
(`rtl_biast -b 1` / `-b 0`) before launching `weewxd`; the off-branch drives the tee off explicitly
rather than relying on the power-on default, since tee state can survive a warm restart.
**Live value is currently `BIAS_TEE=0`** (verified in the running container's env, 2026-09-19) — the
LNA has been out of circuit since 2026-08-02 (DEC-0081/0083; see `CONSTANTS.md`'s hardware timeline).
Re-check this directly (`marvinctl --tenant weewx inspect weewx-rtldavis-v2` → `Config.Env`) rather
than trusting this line if the LNA is ever reinstalled.

## 5. Config vs image — what a change requires

| Change | Requires |
|--------|----------|
| gain / ppm / fc / a mounted `.py` / weewx.conf | container restart (`docker kill` + `docker start`) — no rebuild |
| a baked `.py` / `entrypoint.sh` / Dockerfile / the Go binary | **image rebuild** + retag + redeploy |

## 6. Image/build provenance

**The driver is BAKED, never mounted — this is the single most expensive trap in this repo.**
weewx imports `user.*` from the venv (`/opt/weewx-venv/lib/python3.14/site-packages/user/`), *not*
from `weewx-data/bin/user/`. Two separate mechanisms have each silently shipped the **stock** driver
(no rain filter, no SensorQC) while every version tag and log line insisted otherwise:

1. `Dockerfile` used to `cp weewx-data/bin/user/rtldavis.py` over the patched copy at build time —
   fixed in S30, and the file now carries an explicit "do NOT re-add this" note.
2. `docker-compose.yml` used to bind-mount that same host path over the baked driver at **run** time
   — found and removed in S36. This one shipped in the **public** compose file, so downstream users
   of the published image were running the stock driver too.

If a driver fix appears not to take effect, check these two before anything else. Verify what is
actually running with `docker exec <ctr> /opt/weewx-venv/bin/python3 -c "import user.rtldavis as m;
print(m.__file__, hasattr(m,'SensorQC'))"` — and confirm `docker inspect` shows **no** mount landing
on `.../site-packages/user/rtldavis.py`.

*(Resolved S30: the old `receiveWindow 300→350` sed patch was dropped from the Dockerfile, so builds
now ship the **upstream-default** receiveWindow. The rw350 experiment and its 24 h sweep remain
backlogged; the `rw250-test` tag is a retired misnomer kept only for rollback.)*
- The compiled `rtldavis` Go binary does **not** emit `FreqError`/`ChannelIdx` telemetry (confirmed via
  `strings`), so `-ppm`/`-fc` cannot be data-driven with the current binary — a source-rebuild
  investigation is backlogged (BACKLOG RF history).

## 7. Marvin-side (host, outside the container) — moved from the NAS at DEC-0118

`weewx_monitor.py` is a host-side daemon (not containerized), deployed as a real `dev` git checkout
at the tenant root (`/srv/docker/weewx/`) — self-service via `marvinctl --tenant weewx pull` plus a
**deliberate** `restart weewx-monitor.service` (a `pull` alone updates the on-disk file but not the
running process; see `CONSTANTS.md`'s Release mechanics row). It runs as systemd unit
`weewx-monitor.service` in `/weather.slice`, `User=t-weewx`/`Group=t-weewx` — **not** the NAS-era
DSM-Task `weewx-monitor` user this section used to describe. Credentials
(`ALERT_FROM`/`GMAIL_PASS`/`ALERT_TO`/`STATION_NAME`) live in gitignored `monitor.env` at the tenant
root (DEC-0009).

**`REMEDY_MODE=none` on marvin, on purpose** — the unit detects and escalates (RF reception,
uploader alerting, input-staleness watchdog) but takes no automatic remedy action yet. The
Foundation-era `usb_reset` remedy (`usb_reset.sh`, a driver unbind/rebind sudoers-scoped to a
hardcoded Synology bus path) is still `weewx_monitor.py`'s own module-level default for other
deployments, but is **not used on marvin**: its USB topology differs, and the script would either
no-op or reset a different tenant's device (MARVIN-DEC-0051; see the unit file's own comment). The
planned marvin remedy is a full container recreate (`restart_unit`, i.e. `weewx.service`'s own
`docker run --rm` + `ExecStartPre=docker rm -f` cycle) via a path-scoped sudo grant
(`sudo -n /usr/local/lib/marvin/marvin-own weewx restart weewx.service`, ops#274) — to be armed only
once the unit has run clean through at least one full day including a log rotation and a deliberate
restart (see the unit file's own comment for the exact bar).

**`weewx_monitor.py` guards the dongle** — it carries `reset_dongle()`/`watchdog_stall()` alongside
its alerting, and is the only thing that does; the standalone `usb_watchdog.sh` was a superseded
predecessor, retired at S67 (DEC-0074). RF sweep + backfill tooling lives in `ops/`.
