# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S192] — 2026-11-08 — Coordinator session: ROADMAP reconciled on time, cruft audit filed, gate clean

- No prod change. Fable 5.1 as coordinator by the owner's choice, two children in their own worktrees. PR #549 (S192b, Sonnet): ROADMAP full reconciliation, on time, six lines fixed (P0.8 phases 2 and 4, P1.9 step 4, #536, the P0 freeze row, P3's INTERFACES line), next check S202. PR #565 (S192a, Fable): `docs/CODE_REVIEW_S192.md`, a cruft audit over runtime code and tests, `ops/` and `scripts/`, docs and the tier files, and git; 18 items, 15 filed as #550 to #564 (3 high: CONSTANTS at nine times its cap, local `main` on pre-rewrite history, Go tests run nowhere in CI; 8 medium; 4 low), six enumerator claims dropped after verification, a deliberately-kept list; MANIFEST row added.
- Gate read 11-07 12:01 to 11-08 10:52 ET: no drop line, 1372 of 1372 records, no job-5 watch line fired. Latest minute 0 off-schedule frames, 242 CRC failures.
- Local hygiene in the main checkout (#551, #563's local half): `main` reset from the pre-rewrite `8d4fd05` (ahead 328) onto `origin/main` `c376037`; 16 merged local branches deleted; the `s189-timegate` worktree removed; garbage 0. Origin's 30 merged branches and the `backfill-v2.0.20` tag remain, owner-authorized pushes. Rolled S189 to the archive.

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
