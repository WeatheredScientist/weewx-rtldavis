# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S196] — 2026-11-09 — Status and roadmap evaluation; MANIFEST names the nine root modules again (ops#449)

- No prod change. Fable 5.2 (owner-named). Evaluation: prod healthy on v2.4.0, up 5 days; no `docs/ROADMAP.md` line is session-actionable until early December (its five open lines wait on hardware, a person, the 12-04 re-run, or have no done criterion). Found: ROADMAP is 97 KB with 349 lines of reconciliation log, open items sit under DONE and CLOSED headings, and the forward decisions (the December decoder A/B, Session C, the announcement, #558, #553) are in no roadmap line. A diet is proposed in `BOOT.md` job 0(e), not done.
- ops#449: S195's diet replaced nine root module names with a `*.py at the root` class row, which ops' coverage sweep does not accept (it wants a filename or an ancestor directory). The row names them again; `MANIFEST.md` 3,258 → 3,402 chars (~850 tok). Checked with the sweep's fixture hook: green, and the `dev` copy reproduces the 9-file hole.
- Gate read 11-08 21:14 to 11-09 19:08 ET: no time-gate drop, no gap (1440 of 1440 records on 11-08, 1149 of 1149 on 11-09 to 19:08), no watch line fired; uploader errors only (Windy and WOW 429s, one WU and one AWEKAS retry failure). PR #570 merged 11-09 00:13 ET; #550, #552, #554 and #559 were already closed with comments. Upstream threads unmoved since 10-29; cdavis289's #514 results not posted by 19:10 ET. Rolled S193 to the archive.

## [S195] — 2026-11-08 — Audit chores: #554 (MANIFEST under the cap) and #559 (wxcheck headers); stale S193 worktrees removed

- No prod change. Opus 5.5. PR #570: `MANIFEST.md` 4,506 → 3,258 chars (~815 tok), under the 1,000-token member cap, so OPS-DEC-0102's carry is no longer needed (#554). The two `ops/wxcheck.*` files get headers; the archive half pipes the repo copy through `marvinctl exec` over stdin and opens the database read-only (#559). The auto-mode classifier declined a live run of that route, so it is unexercised.
- The three S193 child worktrees held uncommitted edits byte-identical to `origin/dev` (PR #567 had landed them): removed with their branches, nothing lost.
- Gate read through 11-08 21:14 ET: no time-gate drop since 11-07, 1275 of 1275 records on 11-08. One `Go burst gate dropped a frame` pair at 19:50:07 ET (`240165B703014272` / `A48167B783014272`, +6 smp), kept per the watch. Every uploader failed together for about 30 s at 11:55 ET (an outbound blip, no gap). Rolled S192 to the archive.

## [S194] — 2026-11-08 — #552: CI fails the Go gate tests instead of skipping them; #550 in a child session

- No prod change. Opus 5.5. #552 (DEC-0230): the audit's premise was wrong, since CI already ran the Go gate tests (24 skips = 4 weewx + 17 campaign + 3 librtlsdr builds), but only because the runner ships go. Now `skip_or_fail` in `tests/test_crcstats_patch.py` fails instead of skipping under `REQUIRE_GO_TESTS=1`; `ci.yml` installs `librtlsdr-dev`, sets the flag and runs `pytest -rs`. Positive control: go hidden plus the flag gives 10 failed. #550 (CONSTANTS diet) runs in child session S194b.
- Gate read 11-08 12:01 to 18:13 ET: no drop line, 1093 of 1093 records for the day, no job-5 watch line fired. One WOW HTTP 429 at 13:04 ET (its own rate limit).
- PR #569 (S194b) merged 2026-11-08 20:10 ET; #568 rebased over it and carries this closeout. Rolled S191 to the archive.

## [S194b] — 2026-11-08 — #550: CONSTANTS.md diet, 36,010 → 9,830 chars (DEC-0231)

- No prod change (Opus 5.5, a child of S194). Each `CONSTANTS.md` row now holds its current value plus one "before it"; the rewritten sections moved verbatim to `CHANGELOG-ARCHIVE.md` [S194b]. Deploy layers, live-config deviations and the rollback chain stay always-load; DEC-0231 accepts a ~2,500-token carry against the 1,000 member cap. #554 (MANIFEST) left open.
