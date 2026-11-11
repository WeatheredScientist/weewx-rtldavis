# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S197] — 2026-11-10 — INTERFACES generalization audit (P3); #563 finished; cdavis289's Go vs Python results read

- No prod change. Sonnet 5.5 for the start and chores, then Fable 5.2 (owner-named) for the audit. PR #572: `docs/INTERFACES-AUDIT-S197.md` answers ROADMAP P3's question, whether `docs/INTERFACES.md` is enough for a non-Davis WeeWX or CumulusMX producer. 16 findings, among them: the InfluxDB section has no field table (36 live fields, 19 documented nowhere, seven of those driver internals under borrowed column names); the loop table has no required or optional column and lists two keys prod never emits; the SQLite archive is a third surface that HLF reads and the document disowns; one NaN takes the feed "offline"; `writer` names an implementation, not a contract version. An eight-part decision is proposed, not logged: it needs the owner's go. Nothing was posted to another repo. S196's "no ROADMAP line is session-actionable until December" was wrong about this line. `MANIFEST.md` 3,483 chars, coverage sweep green.
- #563 finished and closed on the owner's word: 29 merged `origin/` branches, the `backfill-v2.0.20` tag and three merged local branches deleted. PR #571 (S196) merged 2026-11-10 19:44 ET; #572 merged `dev` and carries this closeout.
- Gate read 11-09 19:08 to 11-10 19:45 ET: no time-gate or burst-gate drop, no gap (1186 of 1186 records on 11-10), no watch line fired; uploader errors only (AWEKAS retries, two Windy 429s). cdavis289 posted the 72-hour results on 11-10 18:48 ET as weewx-packages/weewx-rtldavis#15: mean reception Python 99.851%, Go 99.558% over 1,186 five-minute intervals, on different dongles, with two Python sync losses; a dongle crossover is next. Summary in `docs/UPSTREAM-THREADS.md`. Rolled S194 and S194b to the archive.

## [S196] — 2026-11-09 — Status and roadmap evaluation; MANIFEST names the nine root modules again (ops#449)

- No prod change. Fable 5.2 (owner-named). Evaluation: prod healthy on v2.4.0, up 5 days; no `docs/ROADMAP.md` line is session-actionable until early December (its five open lines wait on hardware, a person, the 12-04 re-run, or have no done criterion). Found: ROADMAP is 97 KB with 349 lines of reconciliation log, open items sit under DONE and CLOSED headings, and the forward decisions (the December decoder A/B, Session C, the announcement, #558, #553) are in no roadmap line. A diet is proposed in `BOOT.md` job 0(e), not done.
- ops#449: S195's diet replaced nine root module names with a `*.py at the root` class row, which ops' coverage sweep does not accept (it wants a filename or an ancestor directory). The row names them again; `MANIFEST.md` 3,258 → 3,402 chars (~850 tok). Checked with the sweep's fixture hook: green, and the `dev` copy reproduces the 9-file hole.
- Gate read 11-08 21:14 to 11-09 19:08 ET: no time-gate drop, no gap (1440 of 1440 records on 11-08, 1149 of 1149 on 11-09 to 19:08), no watch line fired; uploader errors only (Windy and WOW 429s, one WU and one AWEKAS retry failure). PR #570 merged 11-09 00:13 ET; #550, #552, #554 and #559 were already closed with comments. Upstream threads unmoved since 10-29; cdavis289's #514 results not posted by 19:10 ET. Rolled S193 to the archive.

## [S195] — 2026-11-08 — Audit chores: #554 (MANIFEST under the cap) and #559 (wxcheck headers); stale S193 worktrees removed

- No prod change. Opus 5.5. PR #570: `MANIFEST.md` 4,506 → 3,258 chars (~815 tok), under the 1,000-token member cap, so OPS-DEC-0102's carry is no longer needed (#554). The two `ops/wxcheck.*` files get headers; the archive half pipes the repo copy through `marvinctl exec` over stdin and opens the database read-only (#559). The auto-mode classifier declined a live run of that route, so it is unexercised.
- The three S193 child worktrees held uncommitted edits byte-identical to `origin/dev` (PR #567 had landed them): removed with their branches, nothing lost.
- Gate read through 11-08 21:14 ET: no time-gate drop since 11-07, 1275 of 1275 records on 11-08. One `Go burst gate dropped a frame` pair at 19:50:07 ET (`240165B703014272` / `A48167B783014272`, +6 smp), kept per the watch. Every uploader failed together for about 30 s at 11:55 ET (an outbound blip, no gap). Rolled S192 to the archive.
