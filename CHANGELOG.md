# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S209] — 2026-11-20 — DEC-0244: the image's starter runs the loop writer and DewpointCacher; `[[Influx]]` idles on `replace_me`; the mount's `bin/user` imports (#596, #597)

- No prod change; ships with the next minor image. `user_init.py` becomes the venv's `user/__init__.py` and appends `/opt/weewx-data/bin/user` to its search path (baked modules still win). The build installs the `loopjson` extension, copies the writer into the venv and inserts `DewpointCacher` after `StdWXCalculate`, asserting the final `process_services` line; `DavisPressureFetcher` stays out. `extensions/influx/install.py` writes `replace_me` for `org`/`bucket`/`token` (rides the untagged `0.20+ws.3`). `scripts/smoke_image.sh` checks the seeded file with WeeWX's `get_site_dict`, the mount import and a Simulator-written `feed/loop-data.txt`; `tests/test_starter_services.py` (9, positive-controlled). The secret gate allows whole-word `replace_me` (holes 62, 63 planted; 194 passed). Local arm64 build and full smoke passed; real WeeWX 5.5.2 control: `replace_me` skipped, `YOUR_` posts. Docs: QUICKSTART "What next", the influx README, the seed message, GOTCHAS. Gate: ruff clean, pytest 1048 passed / 28 skipped, mypy clean (116 files). Opus 5.5, no `/model` switch. S206 rolled.

## [S208] — 2026-11-20 — The install-package investigation with the dashboard (ops#465); DEC-0243, three defects filed

- No prod change, no image change. Answered the dashboard's install-package investigation on ops#465 from this repo: the non-Davis path, the loop contract's rules, the host assumptions. Reading the released `v2.4.0` image (read-only exec) for it found that an empty mount is seeded from `weectl`'s output, not `weewx.conf.example`: DEC-0240's change and test act on a file no image user receives, the seeded `[[Influx]]` has no `enable` line (#596), and the seeded `process_services` is stock, so a new install runs none of this repo's services and has no loop feed (#597). Neither is fixed.
- DEC-0243: `extensions/loopjson/README.md` states WeeWX 5.0 or later; a second CI job, `weewx-range`, runs the install-and-run proof on 5.0.0, 5.1.0, 5.2.0, 5.3.0 and 5.4.0 beside the existing 5.5.2 job. All pass locally on Python 3.12 and 3.14. `docs/ARCHITECTURE.md` §4 gives the `BIAS_TEE` default as 0 (#598). Fable 5.2, the desktop app's selected model; no `/model` switch. S205 rolled to the archive.

## [S207d] — 2026-11-18 — DEC-0242: the dead NAS-LEASE yield leaves `influx.py` (#558)

- No prod change. `influx.py` `0.20+ws.3`: the courtesy yield (DEC-0111) is removed; `lease_dir` is popped and ignored with one INFO line, because the thread takes `**site_dict` and the key would otherwise stop weewxd (prod's conf and rx-baseline still set it). `ops/nas_build.py` and its 26 tests deleted; `tests/test_influx_lease_dir_ignored.py` (5, positive-controlled). Rollout after DEC-0238's soak: pull + restart, then the owner deletes the key from both conf files; tag `influx-v0.20+ws.3` after merge.

## [S207b] — 2026-11-18 — #561 closed: the two unreachable frequency-band `else:` branches in `rtldavis.py` removed

- No prod change; baked on `dev`, ships with the next image. `__init__` already raises unless the band is EU, US or NZ, so the `if self.frequency in [...]` guards in the v13 and v12 channel-packet parsers were always true. Behavior identical. The rest of #561 landed in #567 (S193).

## [S207c] — 2026-11-18 — #553: RX campaign apparatus kept and labeled (DEC-0241)

- No prod change. `ops/rx_experiment.sh`, `weewx-rx-experiment.service` and `.timer` headers now say stand-down (DEC-0096), the NAS default versus marvin's `RX_BASE`, and reference copy (heartofgold owns the deployed unit). Retirement deferred to the gain-campaign decision.

## [S207a] — 2026-11-18 — DEC-0240: the starter config ships every uploader off (#587)

- No prod change; ships with the next minor image. Eleven uploaders ran on a new install's first start, not eight: OWM, Windy and WeatherCloud had no `enable` line, which weewx 5.5.2 reads as on (`get_site_dict` skips only `replace_me`). All eleven now carry `enable = false`; a comment in `[StdRESTful]`, one seed line and QUICKSTART say how to turn one on. `tests/test_starter_uploaders_off.py` pins them off in the starter and after seeding, positive-controlled; real weewx 5.5.2 confirms 11 → 0. Opus 5.5, no `/model` switch. A side session of S206; nothing rolled.
