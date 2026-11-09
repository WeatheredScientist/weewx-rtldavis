# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

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

## [S193] — 2026-11-08 — Audit chores, job 0(a): the doc and comment cruft from #554 to #564

- No prod change. Coordinator on Sonnet 5.5, then Opus 5.5 as the review gate (owner's switch); three Sonnet children in their own worktrees, combined on one branch. S193a: #554 (MANIFEST rows collapsed to classes, 4,972 to 4,506 chars, the private-script sentence dropped; the handoffs row made true: S36, S37, S38 and S71 are cited by path from DECISIONS-FULL and CHANGELOG-ARCHIVE, so the audit's "three orphans" was wrong and they stay), #555 (GOTCHAS §3's NAS-only entries moved verbatim to a "NAS era" subsection; the S126 ACL trap is marvin-era and stays), #556 (BACKLOG 935 to 382 lines; resolved and demoted bodies moved verbatim to the end of CHANGELOG-ARCHIVE, one-line conclusions left). S193b: #557 (README writer 1.1.0 and base-system line, CONTRIBUTING's drifted gate copy replaced by a CONVENTIONS pointer, a "Host preparation" section in DEPLOY matching `scripts/host-setup.sh`, two DATA_ERRATA anchors, INTERFACES tense), #560 (status lines on INSTALL-RESEARCH, ASSESSMENT; CHANGES-FROM-UPSTREAM recount, 1422 to 2703 lines; UPSTREAM-THREADS and ARCHITECTURE stamps; MANIFEST rows by the coordinator). S193c: #561 (driver header notice and the missing ws.8 ledger row, comments only in a baked file; `ENV_VARS` removed; Dockerfile comment; `weewx.conf.example` optional `[Rtldavis]` keys and the Ogoxe comment; monitor NAS wording), #562 (ops literals and banners), #564 (alias and `sys.path` boilerplate onto conftest).
- Left on purpose: the dead `else` branches in `rtldavis.py` (behavior in a baked file, needs design), `test_reception_layer_b.py`'s own `_make_driver` (not a mechanical swap), the `--test-alert` argv hack (load-bearing: it skips the monitor's pidfile flock at import; removable only by moving it into conftest once).
- Found and fixed: `ops/soak_check.sh`'s driver canary defaulted to `0.20+ws.7` and would have flagged a healthy `ws.10` station red; bumped. Gate: ruff clean, 833 passed / 24 skipped, mypy clean on 104 files, secret gate clean with both positive controls. Rolled S190 to the archive.
