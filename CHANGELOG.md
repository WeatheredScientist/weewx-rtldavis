# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S207d] — 2026-11-18 — DEC-0242: the dead NAS-LEASE yield leaves `influx.py` (#558)

- No prod change. `influx.py` `0.20+ws.3`: the courtesy yield (DEC-0111) is removed; `lease_dir` is popped and ignored with one INFO line, because the thread takes `**site_dict` and the key would otherwise stop weewxd (prod's conf and rx-baseline still set it). `ops/nas_build.py` and its 26 tests deleted; `tests/test_influx_lease_dir_ignored.py` (5, positive-controlled). Rollout after DEC-0238's soak: pull + restart, then the owner deletes the key from both conf files; tag `influx-v0.20+ws.3` after merge.

## [S206] — 2026-11-17 — DEC-0237 built: a lost dongle exits the container after three decoder exits (#579)

- No prod change; baked on `dev`, ships with the next minor image. `rtldavis.py`: `RtldavisDecoderFatal` (a plain `Exception`, so weewxd exits instead of retrying), `RTLDAVIS_EXIT_AFTER` (default 3, `0` off, junk falls back to 3 with a log line), a module-level consecutive count that any received packet resets and a stall never touches. 18 unit tests with positive controls (`tests/test_decoder_exit_after.py`; `conftest.py` resets the count per test). `scripts/exit_after_image.sh` runs a stub decoder in two containers: the default exited 1 after 121 s, `=0` ran five minutes through 6 decoder exits; `image.yml` runs it on both architectures. `.env.example` documents the setting. Gate: ruff clean, pytest 1060 passed / 27 skipped, mypy clean (115 files). Sonnet 5.5, no `/model` switch. Checks since 11-16 09:24 ET: no archive gap through 11-18 01:57 ET (the logs are in `/srv/docker/weewx/logs`, not under `weewx-data`); heartofgold has not posted the move's gap times on ops#440. Rolled S204.

## [S205] — 2026-11-16 — ops#457 closed for good: tier caps gated in CI (DEC-0239); MANIFEST 879 tok

- No prod change. The ops tier sweep already read `dev` green (MANIFEST 984 tok, S204's trim) with 16 tok of headroom. `MANIFEST.md` 3938 → 3518 chars: doc instance rows folded into class globs (`docs/*RUNBOOK*`, `docs/*-MIGRATION.md`, `*RESEARCH*`); coverage sweep green in fixture mode, empty-MANIFEST positive control reports 58 holes. DEC-0239: `tests/test_tier_caps.py` fails any PR whose BOOT or MANIFEST crosses the sweep's exact character cap (boundary positive-controlled, 4,000 passes, 4,001 fails). Green gate: ruff clean, pytest 1037 passed / 27 skipped, mypy clean (114 files). Opus 5.5 throughout, no `/model` switch. Rolled S202.

## [S204z] — 2026-11-16 — A dev/test receiver on Zaphod is planned (#586); the starter conf's enabled uploaders filed (#587)

- No prod change; nothing built, nothing changed on any box. `docs/ZAPHOD-DEV-RECEIVER-DESIGN.md` (PR #585, merged to `dev` as `90e58bc`) plans the receiver: WSL2 with Debian's Docker Engine in a dedicated distro, usbipd-win reachable from WSL only (it has no listen-address setting, so a single firewall rule on WSL's adapter and a Manual service), no secrets, uploaders disabled before the first start. The owner chose the purpose (a dev/test receiver, closing the "no drop-in dev receiver" gap) and the radio (the V4L, after DEC-0236). Hyper-V, VirtualBox/Vagrant and Docker Desktop are rejected with reasons. WSL's weak isolation is stated as an accepted residual. The DEC is assigned when the plan is accepted. An independent review was folded in, and the starter-uploader line was corrected (Wunderground, not OWM; DavisPressure inert per #451).
- #587: `weewx.conf.example` ships AWEKAS, CWOP, PWSweather, WOW, WOW-BE, Wunderground, Influx and OgoXe with `enable = true` and `YOUR_*` placeholders, and the entrypoint seeds then starts `weewxd`, so a first start runs them all. Found by reading, not run. Secret gate clean on both commits, positive-controlled with a planted token. Opus 5.5, no `/model` switch. Nothing rolled (a side session).
