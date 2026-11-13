# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S201] — 2026-11-13 — loopjson 1.2.0 in prod (DEC-0234); V4 support and device pinning on `dev` (DEC-0235); ops#440 answered

- **Prod change:** `loopjson` 1.2.0. Tag `loopjson-v1.2.0` on `5da8171` published the zip, `check_contract.py` and the schema; `marvinctl pull` moved the tenant checkout `694938f`→`e2124d3` and `restart weewx.service` ran at 2026-11-12 22:42:25 ET. Verified: writer sha `8c2365d6…` = `dev`, log `LoopJsonWriter 1.2.0 (contract 1.2)`, both feed files pass the checker (17 keys incl. `windGust10_mph`), archive records continue, no traceback. Rides along inert: baked files (next image) and the monitor's message-only edit (next monitor restart).
- Opus 5.5 children on the owner's ask: S201b built DEC-0234 (PR #577, squash `5da8171`); S201a found the image's librtlsdr already drives a Blog V4 and that the Go decoder ignored `-d`, and built DEC-0235's devsel patch, `RTLSDR_DEVICE` and `doctor` listing (PR #578, squash `e2124d3`; baked, next image). Both ops#440 answers posted on the owner's go; #579 filed (dongle loss never exits the container). Both PRs merged on the owner's go after all checks passed.
- Gate read 11-11 22:35 to 11-12 19:43 ET: no `gate` line, no archive gap (1,269 records). Green gate on `dev`: 1017 passed, 27 skipped. Session start on Sonnet 5.5; a bare `/model` to Opus, restored at close. Rolled S198 and S198b to the archive.

## [S200] — 2026-11-12 — PR #575 (DEC-0233) landed; gate read to 11-11 22:35 ET; branches cleaned

- No prod change. Sonnet 5.5 throughout, no bare `/model`. PR #575's image and tests jobs had failed on a runner DNS error (`ports.ubuntu.com` unresolvable); `gh run rerun --failed` turned all seven checks green, and the owner's go merged it (squash `960107d`, 2026-11-12 08:51 ET). `s199-interfaces-spec` (remote, local, worktree) deleted after a clean-tree check: only `dev` and `main` remain. Rolled S197 to the archive; `BOOT.md` rewritten to 9,488 chars (ops#452 measured it at 2,649 tokens over the 2,500 cap).
- Gate read 11-10 19:45 to 11-11 22:35 ET: no `gate` line, no `rejecting implausible` or `unknown message type`, no archive gap (1,611 records, none over 90 s); the `Added` grep returned records, so the empty `gate` grep is a real zero.

## [S199] — 2026-11-11 — INTERFACES.md becomes a specification (DEC-0233, PR #575); #551 closed; branch cleanup

- No prod change. Sonnet 5.5 for the start and chores, then Opus 5.5 (owner's switch) for the decision. On the owner's go, DEC-0233 adopts the S197 audit's eight parts; parts 1 to 4 and 8 are written: `docs/INTERFACES.md` now specifies three surfaces (loop JSON, InfluxDB, and the SQLite archive as §3), a §0 table of rules and meanings, a row per field (only `dateTime` required; InfluxDB's 36 live fields as 17 contract, 12 written-optional, 7 diagnostics outside the contract), contract version 1.1 and one owner. The station history moved verbatim to Appendix A (checked by script); the old §1/§2 headings stay for the README anchors. Two audit claims corrected: `ET` is a per-record increment, and the loop file serves a cached `windDir` through calm until its TTL. ROADMAP P3 updated, with a `loopjson` 1.2.0 line for parts 5 to 7. PR #575 carries the change and this closeout; not merged.
- #551 closed with a comment on the owner's word (local `main` already equals `origin/main`). Deleted, all with merged PRs: nine `origin/` branches, four local branches and the S198b worktree; only `dev` and `main` remain.
- Gate read 11-10 19:45 to 11-11 08:55 ET: no time-gate drop and no archive gap (1440 of 1440 records on 11-10); the `Added` grep was the positive control. Rolled S196 to the archive. `BOOT.md` was over its 10,000-char cap (10,597); trimmed to 9,966, with job 6's carry-forward list moved verbatim to `BACKLOG.md`.
