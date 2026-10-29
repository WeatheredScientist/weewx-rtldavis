# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S178] — 2026-10-29 — P0.8 phase 5, first slice: comments, SPDX, test boilerplate; the Go decoder diff

- **Bundled Go decoder == upstream.** The `src.tgz` pinned in the Dockerfile (commit `bfa9e3d9`, sha256 verified) was diffed against `lheijst/rtldavis` master (`b95d5d7`, "Version 0.15", 2020-06-05): every Go source file is byte-identical. The bundle only adds `go.mod`/`go.sum` and vendored dependencies. Closes P1.9's "which upstream version" question.
- PR #501: SPDX `GPL-3.0-or-later` on 40 files that lacked it, modification notice on `weewx.conf.example`, reference-copy banners on the lagging `ops/*.service` copies, `campaign.inhibit` and `sortedcontainers` wording fixed, three misleading `rtldavis.py` comments corrected, its encoding line now `utf-8`, CI pins `mypy==2.3.0` (audit 13, 14, 18, 25, 26, 27, 31). Comments only: the baked driver's bytes differ from prod's until the next image.
- PR #502: tests are pytest-only (audit 37). Per-file `sys.path` shims and `__main__` runners gone, redundant `weewx` stubs gone from 22 rtldavis/dewpoint_service tests (1,604 lines deleted). 757 passed, 21 skipped before and after; passes reversed and with each file alone.
- v2.1.0 watch, 15:40 ET restart to 17:22 ET: largest duplicate gap 8 samples, 0 burst copies, no `dropped` line, no WARNING or ERROR. `rxCheckPercent` not checked.
- Branch cleanup: 13 + 48 local and 71 origin branches deleted after each was checked against its merged PR; five stale worktrees removed. Only `dev` and `main` remain.

## [S177] — 2026-10-28 — #481 follow-through: `windGust10` in the live feed; shipped issues closed

- `extra_fields = windGust10` was already in the mounted config (edited 12:20 ET, live with the 15:40 restart); `current.json` carries `windGust10_mph`. Added the same line to the tenant-root `weewx.conf.rx-baseline` (a restore would have dropped it). Told dash#936. Closed #481, #459 and #468 with comments. First 14 minutes of v2.1.0: duplicate gaps single-digit or none, no gate drops, no warnings.

## [S176] — 2026-10-28 — v2.1.0 deployed, on Hub, baseline tagged

- Prod had run an earlier v2.1.0-era build (`a1e6e94c…`) since 12:24 ET with no matching tag; retagged it `:v2.1.0-predeploy`, moved `:marvin-live` to `:v2.1.0` (`6e10c71b…`) and restarted at 15:40:40 ET (first records clean). Pushed `:v2.1.0-amd64` and joined `:v2.1.0` multi-arch (`881e6c43…`). Tagged `prod-baseline-20261028` on `main`. `:latest` untouched.
