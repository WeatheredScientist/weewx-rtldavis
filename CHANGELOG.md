# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S169] — 2026-10-26 — v2.0.21 build gate: `user.influx` import restored (DEC-0219 correction)

- Building v2.0.21 on marvin showed the image had no importable `user.influx` (the venv `user` package shadows `weewx-data/bin/user`); the Dockerfile copies the root `influx.py` into the venv again, `test_dockerfile_pins.py` pins it and `smoke_image.sh` imports it. Baked config sha `ee62b7a2…` to `f67762d9…` is only the three Influx placeholders. Not yet released.

## [S168] — 2026-10-26 — DEC-0221, `loop_interval_s` per dash's asks on #473 (design only)

- DEC-0221 (accepted, not built) amends DEC-0220 item 5: `loop_interval_s` is the gap between successful writes of `loop-data.txt`, reported from the first gap, omitted outside [1, 3600] s; INTERFACES section 1's liveness paragraph moves to `max(30, 3 × loop_interval_s)` (dash DEC-0404) with the 1.1.0 build.

## [S167] — 2026-10-25 — closeout for S164–S166

- `BOOT.md` Resume block rewritten (S166 → S167): S164's ERR-0011, #474 released, #473 designed, #475 parked, #481 filed; job 1c corrected (the `influx-v0.20+ws.2` release exists). Filed #473–#475 from dash#936 section A; dash's duplicates #476–478 closed in their favor.

## [S166] — 2026-10-25 — DEC-0220, the loop-JSON writer's extra_fields design (#473, design only)

- DEC-0220 (accepted, not built): opt-in `[LoopJsonWriter] extra_fields` emitted under weewx-influx2's names, refusing per-packet deltas (any observation whose accumulator extractor is `sum`), plus `loop_interval_s`; contract `loop_json_writer/1.1.0`. Filed #481 (the driver drops message 9's 10-minute gust).
## [S165] — 2026-10-25 — influx.py ships as a WeeWX extension (#474, DEC-0219; PR #479, not released)

- `extensions/influx/`, `scripts/build_influx_zip.sh`, `scripts/prove_influx.sh`, `.github/workflows/influx.yml`: CI builds `weewx-influx-VERSION.zip`, installs it into WeeWX 5.5.2 with the Simulator driver and builds the service from the installed config; an `influx-vVERSION` tag publishes it (`--latest=false`). Replaces upstream's `influx` extension in place; file unchanged at `0.20+ws.2`.
- Dockerfile installs the extension from the root `influx.py`; the weewx-influx2 download and `INFLUX2_*` pins are gone. mypy gate gains `--explicit-package-bases` (two `install.py` files).

## [S164] — 2026-10-23 — ERR-0011, the 2026-10-22 marvin outage gap

- `docs/DATA_ERRATA.md` ERR-0011: 62 archive minutes absent (marvin's own host outage, `eaglehunt-ops#429`); 3 minutes backfilled from WU history (backup `weewx.sdb.bak-S164-preBackfill-20261023`), `rebuild-daily` for 2026-10-22; the other ~59 minutes stay empty (PR #472).

## [S163] — 2026-10-22 — v2.0.21 prep (not cut, not deployed)

- Dockerfile: the seed-config backups are removed after the last `weectl` call (#468, a plain POSIX glob), and the two brace-expansion `rm -rf` lines, no-ops under dash (audit 15), are now explicit paths. `/usr/share/doc` stays for the Debian copyright files and `/var/lib/dpkg` for the package record. Two tests in `test_dockerfile_pins.py`. Driver banner `0.20+ws.6` → `ws.7` in `rtldavis.py`, README, `ops/soak_check.sh` and `CHANGES-FROM-UPSTREAM.md`. Before the tag: build, compare the baked config's sha before and after, then the release mechanics.

## [S162] — 2026-10-22 — quickstart's container half proven on arm64

- README Quick start steps 3, 5 and 6 run against `:v2.0.20` as `linux/arm64` on the owner's Mac (no dongle): seed copy gives a `weewx.conf`, the unprivileged container writes `archive/weewx.sdb` and `weewx.log`, the log carries the `0.20+ws.6` banner, and it retries every 60 s on "No supported devices found". Filed #468 (two stray `weewx.conf.<timestamp>` backups in the seeded directory) and ops#427 (a disposable Debian VM from marvin for the host steps).

## [S161] — 2026-10-21 — deploy of #464's `influx.py`

- `marvinctl pull` to `dev` `1d96587`, then `weewx.service` restart at 23:14:42 ET. Live `influx.py` sha `526d2ac6…` = `dev`'s (was `23f21235…`); the pull also carried `loop_json_writer.py` (docstring only). Soak 19/0/0 after the first record. #465/#466 had already merged and #465 was closed with comments. No image change.

## [S160] — 2026-10-21 — rain recovery judged against the last accepted count (#465, DEC-0218)

- **#465 (DEC-0218):** a rain reading after a rejected one is judged first against the last
  accepted counter value, then against the resync baseline as before
  (`rain_tips_with_anchor()`). A counter that dipped and came back (115 → 114 → 115) used to book
  the climb back as rain, up to 16 tips (0.16 in), on a clean frame, unlogged. Everything the old
  check accepted is still accepted, so no stall. Exhaustive check: all 241,536 glitch-and-recover
  cases now book the true tips, storm jumps are unchanged, and the only cost is an undercount after
  a counter reset from a count of 18 or less. An INFO line marks each recovery. 14 tests in
  `tests/test_rain_anchor_465.py`; the four phantom cases fail on the pre-fix driver with the
  predicted 1, 16, 7 and 5 tips. Baked driver: ships with the next image release. Prompted by the
  weewx-packages continuation's reply on lheijst#22; the four upstream replies need no answer.

## [S159] — 2026-10-19 — monitor defaults and USB discovery (#453, DEC-0217); tests that cannot fail and two bugs (#456)

- **#453 (PR #463, DEC-0217):** `weewx_monitor.py` defaults describe no host. `REMEDY_MODE` defaults
  to `none` (logged at startup when unset), `WEEWX_RTLDAVIS_DIR` to the script's own directory (a
  missing `logs/` exits 2 with one line), helper scripts sit beside it, docker comes from PATH, the
  container is `weewx-rtldavis`. `usb_reset.sh` resets the one RTL2832U it finds by USB id and
  refuses on none or several, instead of unbinding port `1-3`; the port is never an input. Synology
  installs must now set `REMEDY_MODE=usb_reset` (`docs/DEPLOY.md`). Prod pins every value: no effect.
- **#456 (PR #464):** the dedup guard and the duplicate and repeat counters are tested through the
  real `genLoopPackets` (deleting any of them used to leave 14 tests green); audit items 36 and 38
  fixed; 29, 33 and 34 had shipped at S145. **Audit 32:** every driver start now gets the 240 s init
  grace a hot swap had (`INIT_GRACE_S`): Go's US init waits up to 51 loop periods, 143 s for ID 5 and
  153 s for ID 8, against a 150 s watchdog; prod's 9 retained starts took 10-134 s. Baked, so it
  rides v2.0.21. **Audit 20:** `influx.py`'s lease check no longer kills the upload thread on JSON
  that is not an object (mounted: needs its own deploy).
- Watches: the `frame failed message-type proof` line fired for the first time (2026-10-10, 10-13,
  10-18); measured `pressure` steady; no freeze since 10-11; `loopjson` logged no ERROR since its
  10-14 restart. WOW and Windy rate-limit rejections noted in `BACKLOG.md`.

## [S158] — 2026-10-18 — P0.8 phase 1, the cheap items (#451, #452, #454, #455; ops#423)

- **#451:** `pressure_service.py` no longer crashes WeeWX on `station_id = YOUR_STATION_ID`: a
  non-numeric id takes the existing "missing ... not binding" path. The fetched inHg value is
  converted to mbar for METRIC and METRICWX packets. Tests in `tests/test_pressure_injection.py`. A
  baked file, so it rides v2.0.21; prod (US units, numeric id) is unaffected.
- **#452:** `weewx.conf.example` starts at auto gain, says 5.5.2, drops the dead top-level
  `[LoopData]`, `[WeatherCloud]`, `[Windy]` and `[OWM]` sections, gains `[LoopJsonWriter]`, the four
  missing `qc_*_max_delta` keys and `hotswap_ack_file`, and recommends `fetch_interval = 300`.
- **#454:** `CHANGES-FROM-UPSTREAM.md` recounted (`rtldavis.py` **+1316 / −167**, 1422 → 2571 at
  `c57a964`), rows 19–26 added (#219–#222, #233, DEC-0056, Layer B, `dup_count`), the upstreaming
  table lists the unoffered fixes, `wcloud.py` and `influx.py` edits recorded, the CRC patch noted.
- **#455:** `loop_json_writer.py`'s deploy block is generic; "this NAS" wording reworded; a one-line
  RETIRED header on the NAS-era ops scripts; `ruff.toml` now lints `influx.py` (E402/F401 ignored for
  upstream's imports) and `ogoxeUploader.py` (clean). Comment and config edits only.
- **ops#423:** `MANIFEST.md` folded into classes, 6399 → 3985 characters (cap 1000 tokens).
- Not done: #453 (design first), #456, the fresh-host quickstart proof.

## [S157] — 2026-10-18 — CRC failures counted in the Go decoder, measurement only (#458, DEC-0216)

- `patch/rtldavis-crcstats.patch` (applied after `rtldavis-dupgate.patch`) counts every CRC failure
  per receiver hop slot and how many fall within 100 ms of an accepted frame, either order, and
  prints `crc_stats: crc_fail=N near=M slots=…` once a minute. The driver sums it per archive period
  and logs `crc failures this period` at INFO beside the duplicate and repeat counts. **Log only:**
  no accept, drop or hop decision reads it. Not deployed; rides the next release.
- Proofs: `tests/test_crcstats_patch.py` (the patch removes one line and adds only counters; the
  real `Parse` returns byte-identical messages patched and unpatched, with a positive control) and
  `tests/go/crcstat_test.go` (the tracker against a brute-force oracle; four mutations caught).
- Found on the way: `main.go` builds against the **vendored** `protocol` package, so the top-level
  `protocol/` directory is dead code for this build.
