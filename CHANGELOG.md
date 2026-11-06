# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S190] — 2026-11-04 — v2.4.0: the arrival-time gate in prod (DEC-0229)

- PR #542 merged 11-03; PR #543: image tag v2.4.0 everywhere, banner `0.20+ws.10` (Opus 5.5). Built on marvin from `dev`@`694938f` (image `82220200…`, baked driver `7b6fb60a…` = `dev`'s), restarted 2026-11-04 18:36:38 ET, first record 18:39:00, 2 records lost. Rollback `:v2.3.0-prod-pre-v2.4.0`; `-tolerance 0` is the off switch.
- `tolerance=` and `crc_stats` are not in the log at `debug_rtld = 1`, so S189's two verification strings could not pass; DEC-0229's deployment notes say what proves the gate instead.
- The watch fired before the deploy: 11-04 12:53:00 ET, message type 0xF, 3 records lost, station back 12:57. That makes 13 of 16 garbage frames with a gap. Upstream threads and #514 unmoved since 10-30.
- Released: `v2.4.0` and `prod-baseline-20261104` on `c376037` (PR #545), the GitHub release, and Hub's multi-arch `:v2.4.0` (`2b146586…`). `:latest` moved to it by the owner, 2026-11-06 01:52 ET. A dropped session between the go and the closeout commit delayed this by a day; nothing had landed, and prod was unaffected.
- First live drop 11-05 05:06:39 ET, +725.6 ms, no archive gap; through 11-05 22:01 ET the only gap is the deploy's own.

## [S189] — 2026-11-03 — DEC-0229 accepted and built: the arrival-time gate, unreleased

- PR #542: `patch/rtldavis-timegate.patch`, the fourth Go patch, after the burst gate (Opus 5.5). Once synced, a CRC-valid frame more than `-tolerance` ms (default 100, 0 is off) from the nearest slot of its transmitter's schedule is dropped before anything is booked; `offschedule packet:` logged, `offsched=N` in `crc_stats`, the slot label reset on re-init. The driver sums the count, adds `off-schedule frames this period:`, and logs each drop as `Go time gate dropped a frame:`. Dockerfile guard, static audit, Go unit tests, a replay through the real `Demodulate` and `Parse` with a gate-off positive control. CI's amd64 and arm64 image builds pass. Not run on a live radio, not released.
- DEC-0229 Build notes: the offset folds to the nearest slot rather than `chNextVisits` (two transmitters would otherwise lose real frames), the off switch, `offsched` under one a day rather than a few, and the failure modes the gate adds. ROADMAP P1.9 step 4 updated. Rolled S186 to the archive.

## [S188] — 2026-11-03 — #536 measured: a noise decode re-anchors the hop clock; DEC-0229 proposed

- #536 measured from 30 days of prod logs, no prod change (Fable 5.1, the picker left raised; BOOT asked Opus 5.5). Upstream `main.go` accepts any CRC-valid frame from an active ID, sets its last-visit time to the arrival time, resets the missed counter and hops at once; no arrival-time check. A noise decode at a random moment therefore costs 51 blind hops (143 s) and a re-init park of up to 149 s. 12 of the 15 garbage frames the driver rejected (10-04 to 11-02) were followed within seconds by that 2 to 5 min loss (40 archive records); 4 more gaps of the same shape had no driver line; the 3 rejected frames that lost nothing, and ERR-0012, were on-schedule bit-error frames. weewxd was never frozen. Posted on #536 (counts corrected once in place: 23 gap events over 29 rows, 6 restarts). Side finding: the crcstats slot label is stale during the re-init park. New instance recorded: 10-31 02:32:03 ET, message type 0xB then 4 min 14 s of silence.
- PR #541: DEC-0229 proposed (an arrival-time gate in Go, 100 ms, drop not accept-without-anchor, a fourth patch after the burst gate), index row, ROADMAP P1.9 reopened with step 4 and the P0 freeze line updated; `ops/garbage_gap_corr.py` (the correlation, re-runnable from `marvinctl grep` extracts). Nothing built.
- PR #540 (merged): `docs/UPSTREAM-THREADS.md` records weewx-contrib#2 closed by vinceskahan as not interested and weewx-packages#6 closed by hilman2 as fixed in 0.22.0 (crediting DEC-0203's message-type proof and the EU offsets), plus hilman2's 10-21 comments on lheijst/rtldavis#7 and lheijst/weewx-rtldavis#22.
- Watches clear through 11-03 04:27 ET; prod healthy. The crcstats line is lowercase, so `grep CRC` on the prod log is a false zero (`grep crc`).
