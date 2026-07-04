# Architecture — weewx-rtldavis

**Status:** Source of truth
**Last updated:** 2026-07-04 (S17)

How the system is built. For the *data contract* consumers depend on, see INTERFACES.md.

## 1. The signal chain

```
Davis 6263 VP2+ ISS  ──915 MHz FHSS──▶  RTL-SDR Blog v3 + inline LNA (bias-tee powered)
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
                                     WeeWX engine (5.3.1)
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

> **Vestigial:** `user.loopdata.LoopData` is **not** in any active list, yet `loopdata.py` is still
> volume-mounted and a `[LoopData]` config section remains. Dead weight — cleanup backlogged
> (DEC-0005, BACKLOG). The dashboard feed is `loop_json_writer`, not loopdata.

## 3. Deployment: what's mounted vs baked

The image is built from the `Dockerfile` (multistage Ubuntu 26.04 / Py 3.14, DEC-0002). At runtime,
`docker-compose.yml` **volume-mounts** the hot-iteration files over the baked ones (DEC-0004):

| Volume-mounted `:ro` (edit + clear-pyc + restart — NO rebuild) | Source path on NAS |
|---|---|
| `rtldavis.py` (the driver) | `weewx-data/bin/user/rtldavis.py` ⚠️ *not* the stale root copy |
| `influx.py` | `/volume1/docker/weewx-rtldavis/influx.py` |
| `loop_json_writer.py` | `/volume1/docker/weewx-rtldavis/loop_json_writer.py` |
| `ogoxeUploader.py` | `weewx-data/bin/user/ogoxeUploader.py` |
| `loopdata.py` (vestigial) | `/volume1/docker/weewx-rtldavis/loopdata.py` |
| `sortedcontainers/` (pip dep) | `/volume1/docker/weewx-rtldavis/sortedcontainers` |

**Baked into the image (changing these requires an image REBUILD):**
`dewpoint_service.py`, `owm.py`, `pressure_service.py`, `wcloud.py`, `windy.py`, `entrypoint.sh`.

Plus bind mounts: `weewx-data/` → `/opt/weewx-data` (config, DB, skins) and `logs/` → `/var/log/weewx`.

### pyc-cache gotcha
After editing any mounted `.py` the venv imports, clear its compiled cache or WeeWX runs the stale
bytecode:
```
find /opt/weewx-venv -name "*.pyc" -path "*/user/*" -delete
```

## 4. The entrypoint chain

`Docker → entrypoint.sh (baked; changes need rebuild) → weewxd /data/weewx.conf`

The live `entrypoint.sh` (v2.0.2): enables the RTL-SDR bias-tee for the inline LNA
(`rtl_biast -b 1`), then launches `weewxd`. (The v2.0.1 GitHub copy pre-S16 still started `syslogd`
and lacked the bias-tee — reconciled in S16.)

## 5. Config vs image — what a change requires

| Change | Requires |
|--------|----------|
| gain / ppm / fc / a mounted `.py` / weewx.conf | container restart (`docker kill` + `docker start`) — no rebuild |
| a baked `.py` / `entrypoint.sh` / Dockerfile / the Go binary | **image rebuild** + retag + redeploy |

## 6. Known image/build provenance gaps (S16)

- Running image is tagged `rw250-test` (built 2026-06-01 14:20). The host `Dockerfile` patches the
  Go decoder `receiveWindow 300→350` — so the **committed Dockerfile is an rw350 experiment**, while
  the running binary is most likely **rw250**. `docker history` doesn't expose the value (patched in a
  discarded builder layer). A clean rebuild + a 24 h receiveWindow sweep is backlogged to settle this.
- The compiled `rtldavis` Go binary does **not** emit `FreqError`/`ChannelIdx` telemetry (confirmed via
  `strings`), so `-ppm`/`-fc` cannot be data-driven with the current binary — a source-rebuild
  investigation is backlogged (BACKLOG RF history).

## 7. NAS-side (outside the container)

`weewx_monitor.py` runs as limited user `weewx-monitor` (RF reception tracking, WOW-BE threshold,
daily summary email), sudo scoped to `usb_reset.sh`, credentials in gitignored `monitor.env`
(DEC-0009). `usb_watchdog.sh` guards the dongle. RF sweep + backfill tooling lives in `ops/`.
