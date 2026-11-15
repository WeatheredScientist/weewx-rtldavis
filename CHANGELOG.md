# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S203] — 2026-11-15 — The NAS second-receiver run is pre-registered (DEC-0236, ops#440); readout `ops/ab_frames.py`

- No prod change. Opus 5.5 throughout, no `/model` switch. DEC-0236 (accepted by the owner in chat, both questions): the run answers whether the NAS + V4L stream can be a reference receiver, never V4L against v3. Both sides log every frame (`debug_rtld` 2 plus a scoped `user.rtldavis` DEBUG logger, DEC-0060; one prod live-config edit and restart in the burn-in, reverted after). A pass needs coverage of prod's frames ≥ 0.90, ≤ 1 byte disagreement per 10,000 paired slots, zero NAS stalls and restarts, peak memory < 200 MB; one arm at gain 372; 24 h burn-in, seven days. heartofgold's 5-point bar is kept as a secondary figure.
- `ops/ab_frames.py` + 17 tests (positive controls: the driver's own `data:` format, the offset step); six mutants killed, one of which exposed a real bug (a slot was classified from the wrong candidate). Found while writing the setup: the seeded config logs to `/var/log/weewx`, outside the data mount, so the NAS run needs a log bind mount. Posted on ops#440; PR #582. ROADMAP's V4L line notes DEC-0236. Green gate: ruff and mypy clean, 1034 passed, 27 skipped; secret gate positive-controlled (credential and identifier plants both exit 1). Rolled S200 to the archive.

## [S202] — 2026-11-14 — ROADMAP full reconciliation; the NAS's second stick is a V4L (ops#440): librtlsdr 2.0.3 test tags on Hub

- No prod change. Sonnet 5.5 throughout, no bare `/model`. ROADMAP reconciliation (due S202, on time): six lines fixed (#536's clear window and DEC-0230, phase 2's owed image and the V4L, phase 4's `BOOT.md` job number, the freeze row's #579 and USB-hang shapes, the banner, the guardrail); next check S212. No DEC logged.
- ops#440: the owner's second stick is an RTL-SDR Blog V4L (R828S), not a V4. The image's librtlsdr (osmocom v2.0.2+2) does not support it (generic R820T, "PLL not locked", a stall-and-retry loop); osmocom v2.0.3 does (`0204c9c`: the R828 VCO reference and the UHF input). Branch `s202-v4l-test` (local, unpushed) swaps the bundled librtlsdr for v2.0.3 and adds rtl_433 25.12, each pinned by commit and sha256. Built on marvin in `builds-v4l-test/` beside the live checkout, pushed with `marvinctl push`: `v2.4.0-v4l-test` (`b599bf27…`) and `v2.4.0-v4l-rtl433-test` (`ac19bbe2…`), amd64, not for prod. The V4L decodes on the NAS with the first. DEC-0235's "no image change" holds for a V4, not a V4L.
- `v2.4.0` starts as uid 0 with `--cap-drop ALL`, `--network none`, 256m (Mac, Simulator; heartofgold proved one device node on DSM). Ten ops#440 comments posted; two corrections owned there (the seed carries an Influx stanza at localhost; a V4L is not "a v3 on the bundled library").
- Gate read 11-12 19:43 to 11-13 23:10 ET: no `gate` line, no archive gap (3,296 stamps, largest step 60 s); the 11-07 drop was the positive control. The first AcuRite listens (11-14) decoded nothing. Green gate on the closeout tree: ruff clean, 1017 passed and 27 skipped, mypy clean (111 files), secret scan 0 with a planted positive control. The NAS A/B pre-registration is owed before the measured run. Rolled S199.

## [S201] — 2026-11-13 — loopjson 1.2.0 in prod (DEC-0234); V4 support and device pinning on `dev` (DEC-0235); ops#440 answered

- **Prod change:** `loopjson` 1.2.0. Tag `loopjson-v1.2.0` on `5da8171` published the zip, `check_contract.py` and the schema; `marvinctl pull` moved the tenant checkout `694938f`→`e2124d3` and `restart weewx.service` ran at 2026-11-12 22:42:25 ET. Verified: writer sha `8c2365d6…` = `dev`, log `LoopJsonWriter 1.2.0 (contract 1.2)`, both feed files pass the checker (17 keys incl. `windGust10_mph`), archive records continue, no traceback. Rides along inert: baked files (next image) and the monitor's message-only edit (next monitor restart).
- Opus 5.5 children on the owner's ask: S201b built DEC-0234 (PR #577, squash `5da8171`); S201a found the image's librtlsdr already drives a Blog V4 and that the Go decoder ignored `-d`, and built DEC-0235's devsel patch, `RTLSDR_DEVICE` and `doctor` listing (PR #578, squash `e2124d3`; baked, next image). Both ops#440 answers posted on the owner's go; #579 filed (dongle loss never exits the container). Both PRs merged on the owner's go after all checks passed.
- Gate read 11-11 22:35 to 11-12 19:43 ET: no `gate` line, no archive gap (1,269 records). Green gate on `dev`: 1017 passed, 27 skipped. Session start on Sonnet 5.5; a bare `/model` to Opus, restored at close. Rolled S198 and S198b to the archive.
