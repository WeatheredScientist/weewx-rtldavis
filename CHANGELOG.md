# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S198] — 2026-11-11 — Replied on weewx-packages#15 (CRC-valid gusts); DEC-0232 built by child S198b and merged (PR #573)

- No prod change. Opus 5.5. Issue #15 had nothing new since S197; posted a 109-word reply on the owner's go: ERR-0012 as a CRC-valid phantom gust, and the message-9 `windGust10` cross-check as a flag that discards nothing. `docs/UPSTREAM-THREADS.md` records it and cdavis289's diagnostics fork. On the owner's ask, started child S198b (Opus 5.5, medium, own worktree) for a `windGust10` SQLite column; design approved by the owner in its chat; PR #573 squash-merged 2026-11-11 08:28 ET after all CI checks passed. The prod migration and the dashboard ops note wait on the owner (`BOOT.md` job 00). Gate results since 11-10 19:45 ET not read. Rolled S195 to the archive.

## [S198b] — 2026-11-10 — windGust10 gets a SQLite archive column (DEC-0232); prod migration plan written, not run

- No prod change. Opus 5.5, a child session of S198. Design agreed in chat, then built: new installs create the column from `user.rtldavis.schema` (wview_extended plus `windGust10` `REAL` and its daily summary), which the Dockerfile writes into the starter config; ships with the next image. Prod needs no image or config, only `weectl database add-column windGust10` and a restart: owner-run plan in `docs/WINDGUST10-MIGRATION.md`, with `ops/windgust10_check.sql` to verify and `ops/backfill_windgust10.py` to copy InfluxDB's `windGust10_mph` (12,100 points since 2026-10-28 12:30 ET, read live through the proxy) into NULL cells only. The SQLite to InfluxDB backfills now carry the column. `tests/test_windgust10_archive.py`, with a real-WeeWX 5.5.2 CI step proving the image's schema and `add-column` give the same archive. Dashboard DEC-0442's adapter reads the column by `PRAGMA table_info` (helps); its planned `MAX(windGust)` fallback would re-admit ERR-0012, to raise via ops.

## [S197] — 2026-11-10 — INTERFACES generalization audit (P3); #563 finished; cdavis289's Go vs Python results read

- No prod change. Sonnet 5.5 for the start and chores, then Fable 5.2 (owner-named) for the audit. PR #572: `docs/INTERFACES-AUDIT-S197.md` answers ROADMAP P3's question, whether `docs/INTERFACES.md` is enough for a non-Davis WeeWX or CumulusMX producer. 16 findings, among them: the InfluxDB section has no field table (36 live fields, 19 documented nowhere, seven of those driver internals under borrowed column names); the loop table has no required or optional column and lists two keys prod never emits; the SQLite archive is a third surface that HLF reads and the document disowns; one NaN takes the feed "offline"; `writer` names an implementation, not a contract version. An eight-part decision is proposed, not logged: it needs the owner's go. Nothing was posted to another repo. S196's "no ROADMAP line is session-actionable until December" was wrong about this line. `MANIFEST.md` 3,483 chars, coverage sweep green.
- #563 finished and closed on the owner's word: 29 merged `origin/` branches, the `backfill-v2.0.20` tag and three merged local branches deleted. PR #571 (S196) merged 2026-11-10 19:44 ET; #572 merged `dev` and carries this closeout.
- Gate read 11-09 19:08 to 11-10 19:45 ET: no time-gate or burst-gate drop, no gap (1186 of 1186 records on 11-10), no watch line fired; uploader errors only (AWEKAS retries, two Windy 429s). cdavis289 posted the 72-hour results on 11-10 18:48 ET as weewx-packages/weewx-rtldavis#15: mean reception Python 99.851%, Go 99.558% over 1,186 five-minute intervals, on different dongles, with two Python sync losses; a dongle crossover is next. Summary in `docs/UPSTREAM-THREADS.md`. Rolled S194 and S194b to the archive.

## [S196] — 2026-11-09 — Status and roadmap evaluation; MANIFEST names the nine root modules again (ops#449)

- No prod change. Fable 5.2 (owner-named). Evaluation: prod healthy on v2.4.0, up 5 days; no `docs/ROADMAP.md` line is session-actionable until early December (its five open lines wait on hardware, a person, the 12-04 re-run, or have no done criterion). Found: ROADMAP is 97 KB with 349 lines of reconciliation log, open items sit under DONE and CLOSED headings, and the forward decisions (the December decoder A/B, Session C, the announcement, #558, #553) are in no roadmap line. A diet is proposed in `BOOT.md` job 0(e), not done.
- ops#449: S195's diet replaced nine root module names with a `*.py at the root` class row, which ops' coverage sweep does not accept (it wants a filename or an ancestor directory). The row names them again; `MANIFEST.md` 3,258 → 3,402 chars (~850 tok). Checked with the sweep's fixture hook: green, and the `dev` copy reproduces the 9-file hole.
- Gate read 11-08 21:14 to 11-09 19:08 ET: no time-gate drop, no gap (1440 of 1440 records on 11-08, 1149 of 1149 on 11-09 to 19:08), no watch line fired; uploader errors only (Windy and WOW 429s, one WU and one AWEKAS retry failure). PR #570 merged 11-09 00:13 ET; #550, #552, #554 and #559 were already closed with comments. Upstream threads unmoved since 10-29; cdavis289's #514 results not posted by 19:10 ET. Rolled S193 to the archive.
