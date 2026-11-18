# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S207d] — 2026-11-18 — DEC-0242: the dead NAS-LEASE yield leaves `influx.py` (#558)

- No prod change. `influx.py` `0.20+ws.3`: the courtesy yield (DEC-0111) is removed; `lease_dir` is popped and ignored with one INFO line, because the thread takes `**site_dict` and the key would otherwise stop weewxd (prod's conf and rx-baseline still set it). `ops/nas_build.py` and its 26 tests deleted; `tests/test_influx_lease_dir_ignored.py` (5, positive-controlled). Rollout after DEC-0238's soak: pull + restart, then the owner deletes the key from both conf files; tag `influx-v0.20+ws.3` after merge.

## [S207b] — 2026-11-18 — #561 closed: the two unreachable frequency-band `else:` branches in `rtldavis.py` removed

- No prod change; baked on `dev`, ships with the next image. `__init__` already raises unless the band is EU, US or NZ, so the `if self.frequency in [...]` guards in the v13 and v12 channel-packet parsers were always true. Behavior identical. The rest of #561 landed in #567 (S193).

## [S207c] — 2026-11-18 — #553: RX campaign apparatus kept and labeled (DEC-0241)

- No prod change. `ops/rx_experiment.sh`, `weewx-rx-experiment.service` and `.timer` headers now say stand-down (DEC-0096), the NAS default versus marvin's `RX_BASE`, and reference copy (heartofgold owns the deployed unit). Retirement deferred to the gain-campaign decision.

## [S207a] — 2026-11-18 — DEC-0240: the starter config ships every uploader off (#587)

- No prod change; ships with the next minor image. Eleven uploaders ran on a new install's first start, not eight: OWM, Windy and WeatherCloud had no `enable` line, which weewx 5.5.2 reads as on (`get_site_dict` skips only `replace_me`). All eleven now carry `enable = false`; a comment in `[StdRESTful]`, one seed line and QUICKSTART say how to turn one on. `tests/test_starter_uploaders_off.py` pins them off in the starter and after seeding, positive-controlled; real weewx 5.5.2 confirms 11 → 0. Opus 5.5, no `/model` switch. A side session of S206; nothing rolled.

## [S206] — 2026-11-17 — DEC-0237 built: a lost dongle exits the container after three decoder exits (#579)

- No prod change; baked on `dev`, ships with the next minor image. `rtldavis.py`: `RtldavisDecoderFatal` (a plain `Exception`, so weewxd exits instead of retrying), `RTLDAVIS_EXIT_AFTER` (default 3, `0` off, junk falls back to 3 with a log line), a module-level consecutive count that any received packet resets and a stall never touches. 18 unit tests with positive controls (`tests/test_decoder_exit_after.py`; `conftest.py` resets the count per test). `scripts/exit_after_image.sh` runs a stub decoder in two containers: the default exited 1 after 121 s, `=0` ran five minutes through 6 decoder exits; `image.yml` runs it on both architectures. `.env.example` documents the setting. Gate: ruff clean, pytest 1060 passed / 27 skipped, mypy clean (115 files). Sonnet 5.5, no `/model` switch. Checks since 11-16 09:24 ET: no archive gap through 11-18 01:57 ET (the logs are in `/srv/docker/weewx/logs`, not under `weewx-data`); heartofgold has not posted the move's gap times on ops#440. Rolled S204.

## [S205] — 2026-11-16 — ops#457 closed for good: tier caps gated in CI (DEC-0239); MANIFEST 879 tok

- No prod change. The ops tier sweep already read `dev` green (MANIFEST 984 tok, S204's trim) with 16 tok of headroom. `MANIFEST.md` 3938 → 3518 chars: doc instance rows folded into class globs (`docs/*RUNBOOK*`, `docs/*-MIGRATION.md`, `*RESEARCH*`); coverage sweep green in fixture mode, empty-MANIFEST positive control reports 58 holes. DEC-0239: `tests/test_tier_caps.py` fails any PR whose BOOT or MANIFEST crosses the sweep's exact character cap (boundary positive-controlled, 4,000 passes, 4,001 fails). Green gate: ruff clean, pytest 1037 passed / 27 skipped, mypy clean (114 files). Opus 5.5 throughout, no `/model` switch. Rolled S202.

## [S204z] — 2026-11-16 — A dev/test receiver on Zaphod is planned (#586); the starter conf's enabled uploaders filed (#587)

- No prod change; nothing built, nothing changed on any box. `docs/ZAPHOD-DEV-RECEIVER-DESIGN.md` (PR #585, merged to `dev` as `90e58bc`) plans the receiver: WSL2 with Debian's Docker Engine in a dedicated distro, usbipd-win reachable from WSL only (it has no listen-address setting, so a single firewall rule on WSL's adapter and a Manual service), no secrets, uploaders disabled before the first start. The owner chose the purpose (a dev/test receiver, closing the "no drop-in dev receiver" gap) and the radio (the V4L, after DEC-0236). Hyper-V, VirtualBox/Vagrant and Docker Desktop are rejected with reasons. WSL's weak isolation is stated as an accepted residual. The DEC is assigned when the plan is accepted. An independent review was folded in, and the starter-uploader line was corrected (Wunderground, not OWM; DavisPressure inert per #451).
- #587: `weewx.conf.example` ships AWEKAS, CWOP, PWSweather, WOW, WOW-BE, Wunderground, Influx and OgoXe with `enable = true` and `YOUR_*` placeholders, and the entrypoint seeds then starts `weewxd`, so a first start runs them all. Found by reading, not run. Secret gate clean on both commits, positive-controlled with a planted token. Opus 5.5, no `/model` switch. Nothing rolled (a side session).
