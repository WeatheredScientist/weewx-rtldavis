# Release notes, next minor image (proposed v2.5.0): DRAFT

**Held.** For the release after DEC-0238's soak passes (scored to 12-02 00:00 ET). Delete this file in the
release PR once the text is in the GitHub release. `TODO` marks what only release day can fill.

## Release text

A lost dongle now restarts the station instead of leaving it silent, two dongles can share a computer, and a new install posts nowhere until you say so. Start with [docs/QUICKSTART.md](https://github.com/WeatheredScientist/weewx-rtldavis/blob/main/docs/QUICKSTART.md) for a new install.

**Why 2.5.0:** a minor release. Users gain features, and some values and one failure behavior change; nothing needs an edit to an existing install.

**Changes for existing installs**
- **A decoder that cannot run now exits the container** (DEC-0237, #579). If the dongle disappears, the decoder exits on every retry; after three exits in a row with no packet between them the driver exits too, so `restart: unless-stopped` or systemd recreates the container with fresh device nodes. Expect recovery about 6 minutes after the loss. With no restart policy the container stops. Set `RTLDAVIS_EXIT_AFTER=0` for the old behavior (retry forever).
- **A failed thermistor is no reading** (DEC-0247). Analog outside-temperature sensors, soil and leaf stations: a failed decode used to publish 24 °C. The temperature is now left out, as is soil moisture, which is computed from it. Leaf wetness is unaffected. Digital outside sensors see no change.
- **The 10-minute gust comes only from the wind channel** (DEC-0247). With a separate anemometer transmitter, the ISS's own 10-minute gust is no longer published as `windGust10`. If the ISS carries your wind, nothing changes.
- **librtlsdr is now osmocom v2.0.3** (DEC-0238), which adds the RTL-SDR Blog V4L. It ran on the reference station's V3 for a seven-day soak: TODO result.
- **The bundled InfluxDB uploader is `0.20+ws.3`** (DEC-0242). `lease_dir` in `[[Influx]]` is ignored, with one INFO line. You can delete it.

**New**
- **`RTLSDR_DEVICE`** in `.env` names the station's dongle by serial when more than one is plugged in (DEC-0235). The decoder used to ignore `-d` and open whichever dongle the USB library listed first. The log's `dongle:` line says which one it opened.
- **`doctor` lists every dongle** with its port, maker, product and serial.
- **An extension installed into the mounted `bin/user` now imports** (DEC-0244). The image's own modules still win.

**New installs only**
- **Every uploader starts off** (DEC-0240, DEC-0244, #587, #596). The starter used to start uploaders against `YOUR_*` values. `[[Influx]]` waits until you replace its `replace_me` values.
- **The live JSON feed and the dewpoint service run from the first start** (DEC-0244, #597): `weewx-data/feed/loop-data.txt` and `current.json`.
- **The archive has a `windGust10` column** (DEC-0232). An existing archive is untouched. To add the column, back the database up, run `weectl database add-column windGust10` in the container and restart ([steps](https://github.com/WeatheredScientist/weewx-rtldavis/blob/main/docs/WINDGUST10-MIGRATION.md)).

**Not changed:** the radio settings, and the data contract the `loopjson` 1.2.0 extension already writes (1.2). Driver banner `0.20+ws.11`.

**Assets:** `host-setup.sh` (sha256 TODO), `docker-compose.yml`, `env.example` (save it as `.env.example`; GitHub renames dotfile assets).

**Docker Hub:** `weatheredscientist/weewx-rtldavis:v2.5.0`, multi-arch (amd64 and arm64).

Running v2.4.0? An existing `weewx.conf` is left alone. Check that your container has a restart policy.

## Release-day checklist

1. Soak PASS read and posted on ops#440; merge this branch. FAIL: drop the librtlsdr line and the pin; the rest still ships.
2. Bump in one PR: `Dockerfile:3`, `docker-compose.yml`, the README and QUICKSTART download URLs and banner lines, `DRIVER_VERSION` to `0.20+ws.11` with its header ledger row, and `CHANGES-FROM-UPSTREAM.md`'s driver row.
3. Build on marvin, then prove: `exec-ro` for `librtlsdr.so.2.0.3` and the driver sha; the start log's `dongle:` line names the v3 (the first image here that prints it).
4. `image-publish.yml`, `scripts/join_multiarch.sh`, the GitHub release and `:latest` as `docs/CONVENTIONS.md` says; DEC-0242's rollout in the same window.
5. After it is in prod, the owner sets `RTLSDR_DEVICE`. The S202 test tags join the cleanup in `BACKLOG.md`.
