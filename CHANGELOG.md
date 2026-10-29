# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S181] — 2026-10-29 — P0.8 phase 4 closed: the weewx-influx2#1 reply

- Two edits on the fork branch (commit `0c5d394`: `influx.py:501` `loginf` → `logdbg`; a `verify_ssl` line in the readme's option list), pushed on the owner's go, then the held reply posted on david-lutz/weewx-influx2#1. ROADMAP phase 4 checked, `docs/UPSTREAM-THREADS.md` and `BOOT.md` updated. A parallel session (S182) is researching an install path; its two untracked drafts are not part of this change.

## [S180] — 2026-10-29 — P0.8 phase 5 done but audit 28 (four parallel sessions); phase 4 posted; S179's closeout

- Coordinator session (Fable 5.1, owner's call) ran four child sessions in their own worktrees: PR #507 (S180a, Opus): `owm.py`/`windy.py` share a new baked `rest_site.py` base, payloads pinned byte-identical, Dockerfile/`.dockerignore`/smoke-step plumbing (audit 23). PR #509 (S180b, Opus): driver QC block out to `_apply_sensor_qc`, `genLoopPackets` 183 → 135 lines, dead `windBatteryStatus` line removed, a 600-pass characterization test with an unchanged digest (audit 24); hot-swap code flagged, kept. PR #508 (S180c, Sonnet): 673 lines of tests for `wcloud.py` and `ogoxeUploader.py` (audit 39). PR #506 (S180d, Sonnet): dupgate patch hunk headers fixed, all three patches apply at offset 0 / fuzz 0 with Apple patch (audit 30). Merged in that order after `gh pr update-branch` each (the repo requires current branches). Gates on the result: ruff clean, 808 passed / 21 skipped, mypy clean (98 files).
- Phase 4, posted on the owner's go after a re-evaluation: weewx-contrib#2 (the bundled 2023 sources have open fixes; the continuation exists), weewx-packages#6 (the string version compare; the other three fixes are already there, so the lheijst four-fixes issue was dropped), and the DEC-0223 mechanism as a comment on lheijst/rtldavis#2. The weewx-influx2#1 reply is held until its two-edit commit. Filed eaglehunt-ops#439 (virtual-USB guest for phase 1's last line).
- S179 (PRs #504/#505: audit 21, 22 and 37's helpers) ended without a closeout; its pointer is repaired here. ROADMAP: P1.9's #459 line said "not deployed" though v2.1.0 shipped it 10-28; fixed, and the "Offer upstream" step is done.

## [S178] — 2026-10-29 — P0.8 phase 5, first slice: comments, SPDX, test boilerplate; the Go decoder diff

- **Bundled Go decoder == upstream.** The `src.tgz` pinned in the Dockerfile (commit `bfa9e3d9`, sha256 verified) was diffed against `lheijst/rtldavis` master (`b95d5d7`, "Version 0.15", 2020-06-05): every Go source file is byte-identical. The bundle only adds `go.mod`/`go.sum` and vendored dependencies. Closes P1.9's "which upstream version" question.
- PR #501: SPDX `GPL-3.0-or-later` on 40 files that lacked it, modification notice on `weewx.conf.example`, reference-copy banners on the lagging `ops/*.service` copies, `campaign.inhibit` and `sortedcontainers` wording fixed, three misleading `rtldavis.py` comments corrected, its encoding line now `utf-8`, CI pins `mypy==2.3.0` (audit 13, 14, 18, 25, 26, 27, 31). Comments only: the baked driver's bytes differ from prod's until the next image.
- PR #502: tests are pytest-only (audit 37). Per-file `sys.path` shims and `__main__` runners gone, redundant `weewx` stubs gone from 22 rtldavis/dewpoint_service tests (1,604 lines deleted). 757 passed, 21 skipped before and after; passes reversed and with each file alone.
- v2.1.0 watch, 15:40 ET restart to 17:22 ET: largest duplicate gap 8 samples, 0 burst copies, no `dropped` line, no WARNING or ERROR. `rxCheckPercent` not checked.
- Branch cleanup: 13 + 48 local and 71 origin branches deleted after each was checked against its merged PR; five stale worktrees removed. Only `dev` and `main` remain.

## [S177] — 2026-10-28 — #481 follow-through: `windGust10` in the live feed; shipped issues closed

- `extra_fields = windGust10` was already in the mounted config (edited 12:20 ET, live with the 15:40 restart); `current.json` carries `windGust10_mph`. Added the same line to the tenant-root `weewx.conf.rx-baseline` (a restore would have dropped it). Told dash#936. Closed #481, #459 and #468 with comments. First 14 minutes of v2.1.0: duplicate gaps single-digit or none, no gate drops, no warnings.
