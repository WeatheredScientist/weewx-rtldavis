# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S211] — 2026-11-21 — #584 gust plausibility design drafted and measured (no DEC, no code)

- No prod change; ships with the next minor image (driver version unchanged until that release). DEC-0247, from an outside review: a failed thermistor decode is no reading (not 24 C), message 9's `wind_gust_10` only from the wind channel, the process sweep guarded per PID. Digital-sensor, ISS-only stations (prod) see no change.
- Outside review of the public repo triaged: docs fixes (#609: first-run check, v2.4.0 feed note, folder path, the `windGust10` claim) and DEC-0247 (#610); C1 held, C3 needs a design, C4 accepted (DEC-0229). BOOT: DEC-0238's `dongle:` check dropped, since the prod image predates that line.

- `docs/WINDGUST-PLAUSIBILITY-DESIGN.md`: Class A (a bad received sample, ERR-0012) vs Class B (a bad ISS 10-minute gust, #584); recommends B, a driver cross-check of `windGust10` against received wind; C is optional and reverses S187. Measured on a read-only copy of the live archive, 24 days: B's largest real diff +2 mph, C's next case +8 after ERR-0012's +26; no wind above 14 mph in the window, so the margin is `max(10 mph, 50%)` and fails open. Owner chose B by menu (DEC-0245, accepted, not built; re-measure after a 25 mph event first).
- Post-move partial read (14:04 to 15:01 ET): 58 of 58 archive records, no exits, PLL lines or stalls; a path note: the live log is `<tenant root>/logs/weewx.log`.
- 11-22 (to 9:54 AM ET): 595 records for 595 minutes, no gap over 90 s, mean `rxCheckPercent` 99.92%, no exits, PLL or stalls (a partial day, not the soak verdict). The 433 MHz AcuRite listens with the LNA inline on the V4L (bias tee on) decoded nothing (heartofgold, ops#440); the LNA is out and the dipole is back at 915 MHz (owner), so DEC-0236's hard stop is cleared. `weewx-v4ltest`'s Influx errors every archive interval are the seed's placeholder uploader with no network, harmless (ops#440). The 12-05 second-dongle reminder is dropped.
- **Prod change (11-23 7:58:14 AM ET, owner's go): DEC-0238's swap.** `:marvin-live` now points at `v2.4.0-v4l-test` (`b599bf27…`, librtlsdr v2.0.3 under the v3), `weewx.service` restarted, healthy, no PLL or exit lines in the first minute. (Corrected 11-24: this entry also claimed an R820T tuner line; none is in `weewx.log`, so the v3 is named by its USB port grant.) 11-22 was clean (1,440/1,440 records, rxCheck 99.94%). Settle to 11-24 7:58 AM; scored days 11-25 to 12-02. Posted on ops#440.
- 2026-11-24: DEC-0232 step 7 run on prod (11-21 daily summaries rebuilt, step 5's check read back); outside review S3: `CONSTANTS.md`'s hygiene sentence narrowed to match its rows.
- DEC-0248 (outside review C3): the rain cap stays 16 and DEC-0056's safety claim is withdrawn on 188 days of data; confirm-on-reject designed and modeled (`docs/RAIN-CAP-DESIGN.md`), no code.

## [S210] — 2026-11-21 — DEC-0232's `windGust10` column migrated on prod; #584 answered; coordinator plus S210a-d

- Prod change (data, no image or config): the archive gained `windGust10` (11:22 AM ET, restart 11:23), backfilled 22,395 cells from InfluxDB back to 10-28 through the proxy's JSON series call (raw Flux is closed, DEC-0440), day summaries 10-28 to 11-20 rebuilt; backup `weewx.sdb.pre-dec0232`. `docs/WINDGUST10-MIGRATION.md` corrected: `--dry-run` needs `-y` under `docker exec`, and step 6's CSV route. Left: the 11-21 day rebuild, the copy's deletion after 11-28.
- S210a: #584 answered (a bad ISS reading echoed by its Type 9 gust, not RF; reporter's nearby station saw nothing). S210b: one 4-min gap on 11-20 02:23 ET after a CRC-valid 83.6 mph frame the time gate passed (#536); four time-gate drops 11-18 to 11-21, none with a gap. S210c: ROADMAP diet, shipped text moved verbatim to `docs/ROADMAP-ARCHIVE.md` (#602). S210d: upstream threads re-read (#601). Owner calls: dashboard leaves derived `windGust10_mph` empty (ops#442); repo About and topics set; `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the owner's shell. ops#465/ops#440 answered. S207a-d rolled to the archive.

## [S209] — 2026-11-20 — DEC-0244: the image's starter runs the loop writer and DewpointCacher; `[[Influx]]` idles on `replace_me`; the mount's `bin/user` imports (#596, #597)

- No prod change; ships with the next minor image. `user_init.py` becomes the venv's `user/__init__.py` and appends `/opt/weewx-data/bin/user` to its search path (baked modules still win). The build installs the `loopjson` extension, copies the writer into the venv and inserts `DewpointCacher` after `StdWXCalculate`, asserting the final `process_services` line; `DavisPressureFetcher` stays out. `extensions/influx/install.py` writes `replace_me` for `org`/`bucket`/`token` (rides the untagged `0.20+ws.3`). `scripts/smoke_image.sh` checks the seeded file with WeeWX's `get_site_dict`, the mount import and a Simulator-written `feed/loop-data.txt`; `tests/test_starter_services.py` (9, positive-controlled). The secret gate allows whole-word `replace_me` (holes 62, 63 planted; 194 passed). Local arm64 build and full smoke passed; real WeeWX 5.5.2 control: `replace_me` skipped, `YOUR_` posts. Docs: QUICKSTART "What next", the influx README, the seed message, GOTCHAS. Gate: ruff clean, pytest 1048 passed / 28 skipped, mypy clean (116 files). Opus 5.5, no `/model` switch. S206 rolled.
