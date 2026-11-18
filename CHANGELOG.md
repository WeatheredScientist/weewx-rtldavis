# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S205] — 2026-11-16 — ops#457 closed for good: tier caps gated in CI (DEC-0239); MANIFEST 879 tok

- No prod change. The ops tier sweep already read `dev` green (MANIFEST 984 tok, S204's trim) with 16 tok of headroom. `MANIFEST.md` 3938 → 3518 chars: doc instance rows folded into class globs (`docs/*RUNBOOK*`, `docs/*-MIGRATION.md`, `*RESEARCH*`); coverage sweep green in fixture mode, empty-MANIFEST positive control reports 58 holes. DEC-0239: `tests/test_tier_caps.py` fails any PR whose BOOT or MANIFEST crosses the sweep's exact character cap (boundary positive-controlled, 4,000 passes, 4,001 fails). Green gate: ruff clean, pytest 1037 passed / 27 skipped, mypy clean (114 files). Opus 5.5 throughout, no `/model` switch. Rolled S202.

## [S204z] — 2026-11-16 — A dev/test receiver on Zaphod is planned (#586); the starter conf's enabled uploaders filed (#587)

- No prod change; nothing built, nothing changed on any box. `docs/ZAPHOD-DEV-RECEIVER-DESIGN.md` (PR #585, merged to `dev` as `90e58bc`) plans the receiver: WSL2 with Debian's Docker Engine in a dedicated distro, usbipd-win reachable from WSL only (it has no listen-address setting, so a single firewall rule on WSL's adapter and a Manual service), no secrets, uploaders disabled before the first start. The owner chose the purpose (a dev/test receiver, closing the "no drop-in dev receiver" gap) and the radio (the V4L, after DEC-0236). Hyper-V, VirtualBox/Vagrant and Docker Desktop are rejected with reasons. WSL's weak isolation is stated as an accepted residual. The DEC is assigned when the plan is accepted. An independent review was folded in, and the starter-uploader line was corrected (Wunderground, not OWM; DavisPressure inert per #451).
- #587: `weewx.conf.example` ships AWEKAS, CWOP, PWSweather, WOW, WOW-BE, Wunderground, Influx and OgoXe with `enable = true` and `YOUR_*` placeholders, and the entrypoint seeds then starts `weewxd`, so a first start runs them all. Found by reading, not run. Secret gate clean on both commits, positive-controlled with a planted token. Opus 5.5, no `/model` switch. Nothing rolled (a side session).

## [S204] — 2026-11-16 — #579 decided (DEC-0237); librtlsdr v2.0.3 decided with a prod soak first (DEC-0238); MANIFEST under cap

- No prod change. DEC-0237 (#579, posted there): the driver counts consecutive decoder exits (stall raises not counted, any packet resets, module-level) and at `RTLDAVIS_EXIT_AFTER` (default 3, `0` off) raises `RtldavisDecoderFatal`, a plain `Exception` weewxd 5.5.2 does not retry, so the container exits and its supervisor restarts it. Read from upstream weewxd 5.5.2. Prod logged no stall or `WeeWxIOError` 11-04 to 11-15; the 10-22 62 min outage was two RF-class stalls, not #579's shape. The Opus re-check dropped the Sonnet draft's "count stalls" rule, which would have restarted the container in exactly that outage.
- DEC-0238: osmocom's diff from our pin (`ae0dd6d...797f814`) touches the v3's path only through `65f0658`; the V4L code is gated on product strings the v3 never matches. `v2.4.0-v4l-test` verified on marvin (`librtlsdr.so.2.0.3`, driver sha = prod's) and will soak as `:marvin-live` for seven days, after marvin's physical move and before DEC-0236 (agreed with heartofgold on ops#440, their A5/A9). Branch `s202-v4l-test` pushed as the record.
- `MANIFEST.md` 4026 → 3938 chars (ops#457): the reviews row is a class row; coverage sweep green in fixture mode, positive control included. Gate read to 11-16 09:24 ET: a third time-gate drop (11-14 06:36:24 ET, +640 ms), no archive gap. Green gate: ruff, mypy (113 files), pytest 1034 passed / 27 skipped. Sonnet start; a bare `/model` to Opus for the two DECs, restored at close. Rolled S201.

## [S203] — 2026-11-15 — The NAS second-receiver run is pre-registered (DEC-0236, ops#440); readout `ops/ab_frames.py`

- No prod change. Opus 5.5 throughout, no `/model` switch. DEC-0236 (accepted by the owner in chat, both questions): the run answers whether the NAS + V4L stream can be a reference receiver, never V4L against v3. Both sides log every frame (`debug_rtld` 2 plus a scoped `user.rtldavis` DEBUG logger, DEC-0060; one prod live-config edit and restart in the burn-in, reverted after). A pass needs coverage of prod's frames ≥ 0.90, ≤ 1 byte disagreement per 10,000 paired slots, zero NAS stalls and restarts, peak memory < 200 MB; one arm at gain 372; 24 h burn-in, seven days. heartofgold's 5-point bar is kept as a secondary figure.
- `ops/ab_frames.py` + 17 tests (positive controls: the driver's own `data:` format, the offset step); six mutants killed, one of which exposed a real bug (a slot was classified from the wrong candidate). Found while writing the setup: the seeded config logs to `/var/log/weewx`, outside the data mount, so the NAS run needs a log bind mount. Posted on ops#440; PR #582. ROADMAP's V4L line notes DEC-0236. Green gate: ruff and mypy clean, 1034 passed, 27 skipped; secret gate positive-controlled (credential and identifier plants both exit 1). Rolled S200 to the archive.
