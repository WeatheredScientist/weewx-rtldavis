# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S211] — 2026-11-21 — #584 gust plausibility design drafted and measured (no DEC, no code)

- `docs/WINDGUST-PLAUSIBILITY-DESIGN.md`: Class A (a bad received sample, ERR-0012) vs Class B (a bad ISS 10-minute gust, #584); recommends B, a driver cross-check of `windGust10` against received wind; C is optional and reverses S187. Measured on a read-only copy of the live archive, 24 days: B's largest real diff +2 mph, C's next case +8 after ERR-0012's +26; no wind above 14 mph in the window, so the margin is `max(10 mph, 50%)` and fails open. Owner's call on B/C/document-only.
- Post-move partial read (14:04 to 15:01 ET): 58 of 58 archive records, no exits, PLL lines or stalls; a path note: the live log is `<tenant root>/logs/weewx.log`.

## [S210] — 2026-11-21 — DEC-0232's `windGust10` column migrated on prod; #584 answered; coordinator plus S210a-d

- Prod change (data, no image or config): the archive gained `windGust10` (11:22 AM ET, restart 11:23), backfilled 22,395 cells from InfluxDB back to 10-28 through the proxy's JSON series call (raw Flux is closed, DEC-0440), day summaries 10-28 to 11-20 rebuilt; backup `weewx.sdb.pre-dec0232`. `docs/WINDGUST10-MIGRATION.md` corrected: `--dry-run` needs `-y` under `docker exec`, and step 6's CSV route. Left: the 11-21 day rebuild, the copy's deletion after 11-28.
- S210a: #584 answered (a bad ISS reading echoed by its Type 9 gust, not RF; reporter's nearby station saw nothing). S210b: one 4-min gap on 11-20 02:23 ET after a CRC-valid 83.6 mph frame the time gate passed (#536); four time-gate drops 11-18 to 11-21, none with a gap. S210c: ROADMAP diet, shipped text moved verbatim to `docs/ROADMAP-ARCHIVE.md` (#602). S210d: upstream threads re-read (#601). Owner calls: dashboard leaves derived `windGust10_mph` empty (ops#442); repo About and topics set; `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the owner's shell. ops#465/ops#440 answered. S207a-d rolled to the archive.

## [S209] — 2026-11-20 — DEC-0244: the image's starter runs the loop writer and DewpointCacher; `[[Influx]]` idles on `replace_me`; the mount's `bin/user` imports (#596, #597)

- No prod change; ships with the next minor image. `user_init.py` becomes the venv's `user/__init__.py` and appends `/opt/weewx-data/bin/user` to its search path (baked modules still win). The build installs the `loopjson` extension, copies the writer into the venv and inserts `DewpointCacher` after `StdWXCalculate`, asserting the final `process_services` line; `DavisPressureFetcher` stays out. `extensions/influx/install.py` writes `replace_me` for `org`/`bucket`/`token` (rides the untagged `0.20+ws.3`). `scripts/smoke_image.sh` checks the seeded file with WeeWX's `get_site_dict`, the mount import and a Simulator-written `feed/loop-data.txt`; `tests/test_starter_services.py` (9, positive-controlled). The secret gate allows whole-word `replace_me` (holes 62, 63 planted; 194 passed). Local arm64 build and full smoke passed; real WeeWX 5.5.2 control: `replace_me` skipped, `YOUR_` posts. Docs: QUICKSTART "What next", the influx README, the seed message, GOTCHAS. Gate: ruff clean, pytest 1048 passed / 28 skipped, mypy clean (116 files). Opus 5.5, no `/model` switch. S206 rolled.

## [S208] — 2026-11-20 — The install-package investigation with the dashboard (ops#465); DEC-0243, three defects filed

- No prod change, no image change. Answered the dashboard's install-package investigation on ops#465 from this repo: the non-Davis path, the loop contract's rules, the host assumptions. Reading the released `v2.4.0` image (read-only exec) for it found that an empty mount is seeded from `weectl`'s output, not `weewx.conf.example`: DEC-0240's change and test act on a file no image user receives, the seeded `[[Influx]]` has no `enable` line (#596), and the seeded `process_services` is stock, so a new install runs none of this repo's services and has no loop feed (#597). Neither is fixed.
- DEC-0243: `extensions/loopjson/README.md` states WeeWX 5.0 or later; a second CI job, `weewx-range`, runs the install-and-run proof on 5.0.0, 5.1.0, 5.2.0, 5.3.0 and 5.4.0 beside the existing 5.5.2 job. All pass locally on Python 3.12 and 3.14. `docs/ARCHITECTURE.md` §4 gives the `BIAS_TEE` default as 0 (#598). Fable 5.2, the desktop app's selected model; no `/model` switch. S205 rolled to the archive.
