# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S189 → S190)

### What's settled (do not re-derive)

**v2.3.0 runs in prod since 2026-11-01 11:31:49 ET** (image `71c201b6…`, driver banner still
`0.20+ws.9`, no driver change): DEC-0228's `ENTRYPOINT` dispatch, `doctor`, the informational
`HEALTHCHECK`, plus `WEEWX_DRIVER=simulator` at seed time. Rollback: `:v2.2.0-prod-pre-v2.3.0`
(`0a790696…`), then `:v2.1.0-prod-pre-v2.2.0`. **P0.8 phase 6 is built out**; only its acceptance
test is left. **loopjson 1.1.0** runs since 2026-10-27 09:16 ET. ROADMAP full reconciliation done
S183 (next check S192).

**DEC-0229 is accepted and built (S189, PR #542), in no image yet.** Upstream `main.go` re-anchors
the hop clock to any accepted CRC-valid frame, so a noise decode costs 51 blind hops (143 s) plus a
re-init park of up to 149 s; S188 tied 12 of 15 driver-rejected garbage frames in 30 days to that
loss (40 archive records). `patch/rtldavis-timegate.patch` drops a frame over `-tolerance` ms
(default 100, 0 is off) from the nearest slot of its transmitter's schedule, after the burst gate,
once synced. On-schedule bit-error frames (ERR-0012) are out of its reach. Its Build notes carry the
fold to the nearest slot, the corrected `offsched` rate (under one a day) and the failure modes it
adds. CI's amd64 and arm64 image builds passed with the patch; no live radio has run it.
`ops/garbage_gap_corr.py` reproduces the correlation from `marvinctl grep ERROR` and `grep database`
extracts. **The crcstats line is lowercase (`crc failures this period`), so `grep CRC` is a false
zero.** Read-only Flux works through the dashboard's public proxy, no token.

Standing facts: images are multi-arch (DEC-0214/0215); versions follow DEC-0222's SemVer rule; the
loop writer and `influx.py` ship as extensions, prod mounts both; `t-weewx` (996:986) runs under
`--cap-drop ALL`. **#475 is parked on purpose.** The prod log is `/srv/docker/weewx/logs/weewx.log`,
rotated daily to `weewx.log.YYYY-MM-DD`, 30 days kept. The bundled Go decoder is byte-identical to
`lheijst/rtldavis` master (S178). Tests are pytest-only (#502). `marvinctl inspect` takes containers
only (S185). On marvin, `doctor` exits 13 (the dongle is held by prod); that is the correct verdict.

### ▶▶ S190 JOB LIST

0. **Release DEC-0229 once PR #542 merges (the owner's merge):** a minor release, v2.4.0 (DEC-0222),
   with the driver banner to `0.20+ws.10`; build on marvin per `CONSTANTS.md` Release mechanics.
   The patch and the driver are baked, so only a rebuild ships them. Verify the restart with
   `tolerance=100 ms` in the Go startup lines and `offsched=` in `crc_stats`. Tag, `gh release` and
   a heartofgold CHANGELOG line ride the promotion; `-tolerance 0` in `weewx.conf`'s `cmd` is the
   no-rebuild off switch. Then watch `Go time gate dropped a frame` and re-run
   `ops/garbage_gap_corr.py` after 30 days: expect no garbage-then-gap events. #536 stays open until
   then, and it still needs a comment saying the gate is built. An attended deploy: Opus 5.5.
1. **Watch the three upstream threads still open** (the lheijst/rtldavis#2 comment, weewx-influx2#1,
   matthewwall/weewx-wcloud#6; if he adds a license, retag `wcloud.py`) and #514. weewx-contrib#2
   and weewx-packages#6 closed 10-29 (recorded S188; a reply to vinceskahan's fork-consolidation
   note is the owner's call, none owed). Keep `docs/UPSTREAM-THREADS.md` current. Not rechecked S189.
2. **Phase 6's acceptance test:** a stock 64-bit Pi OS plus `docs/QUICKSTART.md`, timed, by someone
   who has not read the repo. Needs a person, not a session.
3. **Needs the owner:** the GitHub About text and topics; `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in
   the shell profile (never CI); **the hot-swap code** (~230 driver lines, no in-repo producer;
   #509's PR body has the analysis) — keep for the gain campaign `BACKLOG.md` carries, or a DEC to
   remove it with `ops/rx_experiment.sh` converted (DEC-0014).
4. First arm64 run against a live radio still open (ops#439 proved the amd64 systemd path only).
5. **Watch, no action unless it fires:** `no bar_absolute` WARNING (DISC-0002) · WU gold star ·
   OWM/Windy rain in millimeters (needs rain; ERR-0010) · any `Go burst gate dropped a frame` line
   (keep its bytes) · the first `unhealthy` on prod (it never restarts anything; note what the log
   was doing) · any `rejecting implausible` or `unknown message type` line: run the correlation on
   that day's extracts and add the row to #536 until DEC-0229 ships. All clear through 2026-11-03
   04:27 ET; not rechecked S189.
6. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, the reset-from-112-or-above phantom, whether to tell the
   `weewx-packages` maintainer about DEC-0218 option B, `git worktree prune` in heartofgold (stale
   S161 entry), CI mypy pinned `2.3.0` while the pre-commit rev lags, the
   `.claude/worktrees/s180c-audit39-uploader-tests-0d3322` leftover in this checkout (detached, prune
   it), the 10-27 00:00 to 09:17 period at double the CRC-failure rate (ended with the loopjson
   restart; noted, not chased).
7. **Second dongle, early December (reminder set for Sat 2026-12-05 09:00 ET):** the #514 A/B of
   hilman2's Python port (weewx-packages 0.22.0, which credits two changes from this fork) beside
   our Go decoder, and a v3-vs-V4 A/B. hilman2 answered: option names stable through 0.22.x, Pi 4
   demodulator 9.7% of one core (31% in frequency search), no x86 numbers yet. **The V4 needs
   librtlsdr newer than Debian bookworm's 0.6.0, so build the test container on trixie**; check
   which base our image uses. The maintainer question waits on the test; any decoder swap needs a
   DEC (DEC-0014).

## Current state (S189)

| Thing | State |
|---|---|
| Prod | marvin, `v2.3.0` as `:marvin-live` since 2026-11-01 11:31:49 ET, weewx 5.5.2, gain 372, `healthy`. Writer mounted at 1.1.0 since 2026-10-27 09:16 ET |
| InfluxDB / monitor | marvin, `weewx-influxdb.service`; weewx-monitor sha `5cd09917…`, `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric); about 255 CRC failures a minute |
| `main`/`dev` | `main` = the v2.3.0 promotion (`fe3761a`, PR #530, `prod-baseline-20261101`); `dev` = main plus doc-only work from S185 to S188 (PRs #531 to #541); PR #542 (the time gate and this closeout) is open against it, CI green |
| Docker Hub | `:v2.3.0` and `:latest` are the multi-arch index `03f3c891…` (amd64 `71c201b6…` = prod, arm64 `c0d54664…`), `:latest` moved by the owner 2026-11-01 12:25 ET |
| Trackers | repo: #536 (DEC-0229 built, PR #542), #475 parked, #380 info, #514 (December A/B) · ops: #440 (second dongle, December), #110 (gated, Jan-Feb), #344 · upstream open: lheijst/rtldavis#2 comment, weewx-influx2#1 (reply 10-29), matthewwall/weewx-wcloud#6 (license request); closed 10-29: weewx-contrib#2 (not interested), weewx-packages#6 (fixed in 0.22.0) |

## Blockers

Unchanged from S145 except blocker 1: 1 freeze mechanism (DEC-0068/0094) **now has a measured
mechanism for the short gaps (DEC-0229); the 10-22 62 min outage and DEC-0083's long tail are not
it**, 2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

S189 started on Sonnet 5.5 and moved to Opus 5.5 for the build with `/model claude-opus-5-5`.
settings.json's floor still reads `sonnet`, but the desktop picker persists: switch it back to
Sonnet by hand. S190: Opus 5.5 for the v2.4.0 deploy; Sonnet for the watches.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4).
S180 adds to §2: this repo requires PR branches current with `dev`, so after one merge every other
open PR needs `gh pr update-branch` and a CI rerun before its own merge — sequence them. S185 adds:
two children that append to the same file conflict anyway; resolve by keeping both blocks.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else (CLAUDE.md's Documentation map, DEC-0063).
Git workflow, secrets handling and the exact gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-11-03 (S189: DEC-0229 accepted and built, PR #542 open, release is next)._
