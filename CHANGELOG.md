# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S191] — 2026-11-07 — Watch session: the gate's second drop, no gaps

- No prod change (Opus 5.5, the picker left raised from S190). Second live drop 11-07 09:04:56 ET, frame `DC5774E5D9795EF5`, +1036.2 ms, no archive gap, recorded on #536. `ops/garbage_gap_corr.py` over 11-05 00:00 to 11-07 12:01 ET: 3,602 records, 0 driver rejections, 0 gaps. All other watches clear; the 9 ERROR lines are uploader failures.
- Upstream threads unmoved. #514: cdavis289 started a 72-hour Go vs Python run on real hardware, results expected about 11-09; BOOT's job 7 carries it.
- After S191's close: weewx-monitor restarted 2026-11-07 13:43:18 ET onto the on-disk file (`2f8a1eda…`, S179's refactor; the process had run since 10-22). `Remedy armed: no automatic remedy`, startup email sent, polling resumed. Its windows of about 80% are unchanged by v2.4.0 (79.3% on 11-04, 79.5% on 11-06), so the gate shows no cost in real frames.

## [S190] — 2026-11-04 — v2.4.0: the arrival-time gate in prod (DEC-0229)

- PR #542 merged 11-03; PR #543: image tag v2.4.0 everywhere, banner `0.20+ws.10` (Opus 5.5). Built on marvin from `dev`@`694938f` (image `82220200…`, baked driver `7b6fb60a…` = `dev`'s), restarted 2026-11-04 18:36:38 ET, first record 18:39:00, 2 records lost. Rollback `:v2.3.0-prod-pre-v2.4.0`; `-tolerance 0` is the off switch.
- `tolerance=` and `crc_stats` are not in the log at `debug_rtld = 1`, so S189's two verification strings could not pass; DEC-0229's deployment notes say what proves the gate instead.
- The watch fired before the deploy: 11-04 12:53:00 ET, message type 0xF, 3 records lost, station back 12:57. That makes 13 of 16 garbage frames with a gap. Upstream threads and #514 unmoved since 10-30.
- Released: `v2.4.0` and `prod-baseline-20261104` on `c376037` (PR #545), the GitHub release, and Hub's multi-arch `:v2.4.0` (`2b146586…`). `:latest` moved to it by the owner, 2026-11-06 01:52 ET. A dropped session between the go and the closeout commit delayed this by a day; nothing had landed, and prod was unaffected.
- First live drop 11-05 05:06:39 ET, +725.6 ms, no archive gap; through 11-05 22:01 ET the only gap is the deploy's own.

## [S189] — 2026-11-03 — DEC-0229 accepted and built: the arrival-time gate, unreleased

- PR #542: `patch/rtldavis-timegate.patch`, the fourth Go patch, after the burst gate (Opus 5.5). Once synced, a CRC-valid frame more than `-tolerance` ms (default 100, 0 is off) from the nearest slot of its transmitter's schedule is dropped before anything is booked; `offschedule packet:` logged, `offsched=N` in `crc_stats`, the slot label reset on re-init. The driver sums the count, adds `off-schedule frames this period:`, and logs each drop as `Go time gate dropped a frame:`. Dockerfile guard, static audit, Go unit tests, a replay through the real `Demodulate` and `Parse` with a gate-off positive control. CI's amd64 and arm64 image builds pass. Not run on a live radio, not released.
- DEC-0229 Build notes: the offset folds to the nearest slot rather than `chNextVisits` (two transmitters would otherwise lose real frames), the off switch, `offsched` under one a day rather than a few, and the failure modes the gate adds. ROADMAP P1.9 step 4 updated. Rolled S186 to the archive.
