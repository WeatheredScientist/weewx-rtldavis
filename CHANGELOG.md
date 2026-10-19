# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

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
