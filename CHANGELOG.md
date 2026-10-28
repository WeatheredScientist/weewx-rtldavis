# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S176] — 2026-10-28 — v2.1.0 deployed, on Hub, baseline tagged

- Prod had run an earlier v2.1.0-era build (`a1e6e94c…`) since 12:24 ET with no matching tag; retagged it `:v2.1.0-predeploy`, moved `:marvin-live` to `:v2.1.0` (`6e10c71b…`) and restarted at 15:40:40 ET (first records clean). Pushed `:v2.1.0-amd64` and joined `:v2.1.0` multi-arch (`881e6c43…`). Tagged `prod-baseline-20261028` on `main`. `:latest` untouched.

## [S175] — 2026-10-28 — v2.1.0 version strings; windGust10's uploader check

- Bumped the image tag to v2.1.0 in `Dockerfile`, `README.md`, `docker-compose.yml`, the systemd example, the `image-publish.yml` example and `CHANGES-FROM-UPSTREAM.md` (driver `0.20+ws.8`). Checked DEC-0224's open item: prod's `[[Influx]]` uploads every archive key, so InfluxDB gains `windGust10_mph`; the other uploaders read named keys only. Not built or deployed yet.

## [S174] — 2026-10-27 — #481 built: message 9's 10-minute gust is `windGust10` (DEC-0224)

- DEC-0224: `rtldavis.py` stores message 9's gust as `wind_gust_10` (m/s), maps it to `windGust10` (never `windGust`), registers `group_speed` so it comes out `windGust10_mph`, bounds-checks it (0..89.4, no delta) and co-rejects it with a condemned frame. Banner `0.20+ws.8`. 8 new tests in `tests/test_windgust10_481.py`. Not deployed; rides the next image with #459 as v2.1.0. Prod then needs `extra_fields = windGust10` in the mounted config.

## [S173] — 2026-10-27 — #459 burst gate designed and built (DEC-0223); #458 baseline recorded and closed

- #458 closed with its baseline (1,241 minutes of v2.0.21): 4.24 CRC failures/s, about 9,700/day near a burst beyond chance, roughly one CRC-valid phantom a week; Go's summary and the driver's period alias (one minute in three reads 0).
- DEC-0223: the burst gate keys on sample-stream position, not the hop slot. `patch/rtldavis-burstgate.patch` (own `burstgate/` package, applied after crcstats, asserted in the `Dockerfile`); the driver counts and logs its drops and the largest duplicate gap. Replay through the real demodulator: 2.7% of start offsets re-decode, at most 8 samples apart. Not deployed; rides the next image release.

## [S172] — 2026-10-27 — ROADMAP reconciliation (due S166); heartofgold's three late weewx rows; ops#435 answered

- `docs/ROADMAP.md` full reconciliation, six sessions late (PR #493): eight lines current (P0.8 phases 1–2, P0.7, P1.9's #458, P1's DEC-0218, P3's DEC-0219, #473 and INTERFACES lines); audit items 13, 14, 16, 18 placed in P0.8 phase 5; `docs/CODE_REVIEW_S145.md` status line corrected. Next check S182.
- heartofgold `CHANGELOG.md` gains the three weewx marvin changes it lacked: S161's `influx.py` (10-21), v2.0.21 (10-26), the writer 1.1.0 (10-27) (`a823a57`).
- eaglehunt-ops#435 (DST 11-01): both items fine by design (UTC-epoch archive keys; no job between 1 and 2 AM local); the 11-02 row count is owed.
- v2.1.0 deferred by owner call: cut with the next substantive image change, not as a label alone. `CHANGELOG.md` rolled: S157–S168 moved to the archive verbatim.

## [S171] — 2026-10-27 — #473 released and deployed: loopjson 1.1.0 in prod

- `loopjson-v1.1.0` released (tag on `12340a4`, zip attached). Prod's mounted writer updated by `marvinctl pull` (tenant checkout to `dev`@`a3f87c0`) and `restart weewx.service` at 09:16 ET; first feed read shows `loop_json_writer/1.1.0` and `loop_interval_s: 2.8`, no log errors, fixed fields unchanged. #473 closed with a comment; dash#936 notified. v2.1.0 not built: the image's only change since v2.0.21 is a Dockerfile comment, so whether to cut it as a contract label is S172's call. `BOOT.md` rewritten (S171 → S172).

## [S170] — 2026-10-27 — #473 built on a branch: loopjson 1.1.0 (`extra_fields`, `loop_interval_s`); #471 closed

- #471: README step 5 and DEPLOY.md say `--device /dev/bus/usb` needs a USB device present (PR #489). ops#427 answered.
- #473 / DEC-0220 + DEC-0221, steps 1 to 7, merged to `dev` as PR #490 (`12340a4`); release `loopjson-v1.1.0`, the prod deploy and v2.1.0 are S171's: `[LoopJsonWriter] extra_fields` with weewx-influx2's key names, `[[ttl]]`, refusal of `sum`-extractor deltas at the first packet, extras on the shared cache, `loop_interval_s`, version 1.1.0. Tests run against real WeeWX in `loopjson.yml` (`REQUIRE_REAL_WEEWX=1`); `prove_loopjson.sh` proves it end to end on the Simulator. INTERFACES §1 gains the class table and the cadence-aware liveness paragraph. BOOT.md rewritten under the ops cap (ops#433); GOTCHAS §1 gains three entries.

## [S169b] — 2026-10-26 — DEC-0222, image tags follow SemVer; the base OS is recorded, not versioned

- DEC-0222 (accepted, docs only): major = a break in what consumers read, minor = something added or a value's meaning changed, patch = the rest; v2.1.0 is the first release under the rule; no tag renumbered, no rename. README "Versions" rewritten as a table of the four independent numbers.

## [S169] — 2026-10-26 — v2.0.21 build gate: `user.influx` import restored (DEC-0219 correction)

- Building v2.0.21 on marvin showed the image had no importable `user.influx` (the venv `user` package shadows `weewx-data/bin/user`); the Dockerfile copies the root `influx.py` into the venv again, `test_dockerfile_pins.py` pins it and `smoke_image.sh` imports it. Baked config sha `ee62b7a2…` to `f67762d9…` is only the three Influx placeholders. v2.0.21 built on marvin from `dev`@`c9c5934` and in prod from 2026-10-26 18:16:14 ET (image `5ca44ede…`). `BOOT.md` rewritten and trimmed under its cap; `CONSTANTS.md` rows and the version pins in README, compose and the systemd example move to v2.0.21; GOTCHAS §4 gains the import-path trap. Then: `:v2.0.21-amd64` pushed, tag `v2.0.21` and the GitHub release on `a7bf7ec`, the multi-arch `:v2.0.21` joined on Hub (`e2177ffc…`), `dev` promoted to `main` (`prod-baseline-20261026`).
