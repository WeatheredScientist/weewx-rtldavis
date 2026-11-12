# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S200] — 2026-11-12 — PR #575 (DEC-0233) landed; gate read to 11-11 22:35 ET; branches cleaned

- No prod change. Sonnet 5.5 throughout, no bare `/model`. PR #575's image and tests jobs had failed on a runner DNS error (`ports.ubuntu.com` unresolvable); `gh run rerun --failed` turned all seven checks green, and the owner's go merged it (squash `960107d`, 2026-11-12 08:51 ET). `s199-interfaces-spec` (remote, local, worktree) deleted after a clean-tree check: only `dev` and `main` remain. Rolled S197 to the archive; `BOOT.md` rewritten to 9,488 chars (ops#452 measured it at 2,649 tokens over the 2,500 cap).
- Gate read 11-10 19:45 to 11-11 22:35 ET: no `gate` line, no `rejecting implausible` or `unknown message type`, no archive gap (1,611 records, none over 90 s); the `Added` grep returned records, so the empty `gate` grep is a real zero.

## [S199] — 2026-11-11 — INTERFACES.md becomes a specification (DEC-0233, PR #575); #551 closed; branch cleanup

- No prod change. Sonnet 5.5 for the start and chores, then Opus 5.5 (owner's switch) for the decision. On the owner's go, DEC-0233 adopts the S197 audit's eight parts; parts 1 to 4 and 8 are written: `docs/INTERFACES.md` now specifies three surfaces (loop JSON, InfluxDB, and the SQLite archive as §3), a §0 table of rules and meanings, a row per field (only `dateTime` required; InfluxDB's 36 live fields as 17 contract, 12 written-optional, 7 diagnostics outside the contract), contract version 1.1 and one owner. The station history moved verbatim to Appendix A (checked by script); the old §1/§2 headings stay for the README anchors. Two audit claims corrected: `ET` is a per-record increment, and the loop file serves a cached `windDir` through calm until its TTL. ROADMAP P3 updated, with a `loopjson` 1.2.0 line for parts 5 to 7. PR #575 carries the change and this closeout; not merged.
- #551 closed with a comment on the owner's word (local `main` already equals `origin/main`). Deleted, all with merged PRs: nine `origin/` branches, four local branches and the S198b worktree; only `dev` and `main` remain.
- Gate read 11-10 19:45 to 11-11 08:55 ET: no time-gate drop and no archive gap (1440 of 1440 records on 11-10); the `Added` grep was the positive control. Rolled S196 to the archive. `BOOT.md` was over its 10,000-char cap (10,597); trimmed to 9,966, with job 6's carry-forward list moved verbatim to `BACKLOG.md`.

## [S198] — 2026-11-11 — Replied on weewx-packages#15 (CRC-valid gusts); DEC-0232 built by child S198b and merged (PR #573)

- No prod change. Opus 5.5. Issue #15 had nothing new since S197; posted a 109-word reply on the owner's go: ERR-0012 as a CRC-valid phantom gust, and the message-9 `windGust10` cross-check as a flag that discards nothing. `docs/UPSTREAM-THREADS.md` records it and cdavis289's diagnostics fork. On the owner's ask, started child S198b (Opus 5.5, medium, own worktree) for a `windGust10` SQLite column; design approved by the owner in its chat; PR #573 squash-merged 2026-11-11 08:28 ET after all CI checks passed. The prod migration and the dashboard ops note wait on the owner (`BOOT.md` job 00). Gate results since 11-10 19:45 ET not read. Rolled S195 to the archive.

## [S198b] — 2026-11-10 — windGust10 gets a SQLite archive column (DEC-0232); prod migration plan written, not run

- No prod change. Opus 5.5, a child session of S198. Design agreed in chat, then built: new installs create the column from `user.rtldavis.schema` (wview_extended plus `windGust10` `REAL` and its daily summary), which the Dockerfile writes into the starter config; ships with the next image. Prod needs no image or config, only `weectl database add-column windGust10` and a restart: owner-run plan in `docs/WINDGUST10-MIGRATION.md`, with `ops/windgust10_check.sql` to verify and `ops/backfill_windgust10.py` to copy InfluxDB's `windGust10_mph` (12,100 points since 2026-10-28 12:30 ET, read live through the proxy) into NULL cells only. The SQLite to InfluxDB backfills now carry the column. `tests/test_windgust10_archive.py`, with a real-WeeWX 5.5.2 CI step proving the image's schema and `add-column` give the same archive. Dashboard DEC-0442's adapter reads the column by `PRAGMA table_info` (helps); its planned `MAX(windGust)` fallback would re-admit ERR-0012, to raise via ops.
