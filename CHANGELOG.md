# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S188] — 2026-11-03 — #536 measured: a noise decode re-anchors the hop clock; DEC-0229 proposed

- #536 measured from 30 days of prod logs, no prod change (Fable 5.1, the picker left raised; BOOT asked Opus 5.5). Upstream `main.go` accepts any CRC-valid frame from an active ID, sets its last-visit time to the arrival time, resets the missed counter and hops at once; no arrival-time check. A noise decode at a random moment therefore costs 51 blind hops (143 s) and a re-init park of up to 149 s. 12 of the 15 garbage frames the driver rejected (10-04 to 11-02) were followed within seconds by that 2 to 5 min loss (40 archive records); 4 more gaps of the same shape had no driver line; the 3 rejected frames that lost nothing, and ERR-0012, were on-schedule bit-error frames. weewxd was never frozen. Posted on #536 (counts corrected once in place: 23 gap events over 29 rows, 6 restarts). Side finding: the crcstats slot label is stale during the re-init park. New instance recorded: 10-31 02:32:03 ET, message type 0xB then 4 min 14 s of silence.
- PR #541: DEC-0229 proposed (an arrival-time gate in Go, 100 ms, drop not accept-without-anchor, a fourth patch after the burst gate), index row, ROADMAP P1.9 reopened with step 4 and the P0 freeze line updated; `ops/garbage_gap_corr.py` (the correlation, re-runnable from `marvinctl grep` extracts). Nothing built.
- PR #540 (merged): `docs/UPSTREAM-THREADS.md` records weewx-contrib#2 closed by vinceskahan as not interested and weewx-packages#6 closed by hilman2 as fixed in 0.22.0 (crediting DEC-0203's message-type proof and the EU offsets), plus hilman2's 10-21 comments on lheijst/rtldavis#7 and lheijst/weewx-rtldavis#22.
- Watches clear through 11-03 04:27 ET; prod healthy. The crcstats line is lowercase, so `grep CRC` on the prod log is a false zero (`grep crc`).

## [S187] — 2026-11-02 — ops#439 passed, ops#442 already done, ERR-0012, #536 filed

- ops#439: HoG ran `weewx-439.sh` in a guest with a real USB stick (`154b:1006`) passed through; all three `docs/DEPLOY.md` checks pass (the unit starts unprivileged, the container sees and opens the bus node, `usb_reset.sh` refuses non-RTL ids and resets by id). Verdict posted; the owner closed it. S186's `NRestarts` prediction for check 1b was wrong (a manual restart resets the counter), not the unit.
- PR #534: DEPLOY.md pointed at Quick start steps that no longer exist. It now starts from `host-setup.sh`, adds a by-hand `seed_config.py` run with the location (the unit's `test -e` means the image never seeds under systemd; the command ops#439 proved), widens the udev rule to `0bda:2832`, and points the Synology section at the unit's `docker run` line.
- ops#442: `windGust10_mph` has been in every InfluxDB archive point since 2026-10-28 12:30 ET (the driver has no hardware archive, so the record comes from the accumulator, `last` extractor, and `influx.py` uploads every field); only SQLite lacks it. 926 of 1,440 minutes carry it (no message 9 = no field, never 0). No build; documented in `docs/INTERFACES.md` §2 (PR #537); the dashboard confirmed its Flux query; closed.
- ERR-0012 (PR #535): the 2026-10-31 10:04 EDT 30 mph gust at 150° in a 2 mph north breeze, one CRC-valid garbage frame (12.5 m/s jump, under the 20 m/s wind delta; reception 100%). Recorded, data left as is by the owner's call. The ISS gust read 4 mph.
- #536 filed (tier:frontier): ~400,000 CRC failures a day, so a few chance passes a day; on 10-30 13:10 EDT a rejected 187 mph frame was the last line before a silent 2 min 49 s gap (the S144 freeze-lead shape; the log can't tell a weewxd freeze from a lost station). Proposes measuring arrival offset against the expected slot before any timing check.
- Same day, targeted ROADMAP update (DEC-0057): P0.8 phase 1 closed; the P0 freeze line gained the 10-30 instance and #536. Corrected S187's first reading of 10-30: its 998 CRC failures span about 3 minutes (a normal rate, not 3.5 times), and "nothing was received" was unsupported; only "nothing reached WeeWX" is known.

## [S186] — 2026-11-01 — ROADMAP: two stale P0.8 lines fixed (targeted, DEC-0057)

- Session-start roadmap spotlight. Phase 2 still listed a v2.1.1 and moving `:latest` off `:v2.0.20` (v2.1.1's baked changes shipped as v2.2.0; `:latest` = `:v2.3.0`); phase 1 said ops#439 waited on marvin (heartofgold built `--usb-host` passthrough 11-01, MARVIN-DEC-0219; it now waits on the owner's flash drive). PR #533. ops#435 needs nothing more from weewx. Rolled S183 to S177 to the archive.
