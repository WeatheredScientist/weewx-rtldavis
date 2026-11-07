# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S191 → S192)

### What's settled (do not re-derive)

**v2.4.0 runs in prod since 2026-11-04 18:36:38 ET** (image `82220200…`, banner `0.20+ws.10`):
DEC-0229's arrival-time gate in Go, `-tolerance` default 100 ms; `-tolerance 0` in the live `cmd` is
the no-rebuild off switch. Rollback: `:v2.3.0-prod-pre-v2.4.0` (`71c201b6…`), then
`:v2.2.0-prod-pre-v2.3.0`. **P0.8 phase 6 is built out**; only its acceptance test is left.
**loopjson 1.1.0** runs since 2026-10-27 09:16 ET. ROADMAP full reconciliation done S183; **the next
check is due at S192, this coming session.**

**DEC-0229 in one line:** upstream re-anchors the hop clock to any CRC-valid frame, so a noise decode
cost a 2 to 5 min loss (13 of 16 garbage frames to date, last 11-04 12:53 ET); the gate drops a frame
over 100 ms off its transmitter's schedule. On-schedule bit-error frames (ERR-0012) are out of its
reach. **At `debug_rtld = 1` neither `tolerance=` nor `crc_stats` reaches the log, and `off-schedule
frames this period: 0` proves the driver only;** a `Go time gate dropped a frame` line is the proof
of a drop. **Two so far, neither with an archive gap: 11-05 05:06:39 ET, +725.6 ms (DEC-0229's
deployment notes), and 11-07 09:04:56 ET, +1036.2 ms (#536).** `ops/garbage_gap_corr.py` reproduces the
correlation from `marvinctl grep ERROR` and `grep database` extracts. **The crcstats line is
lowercase (`crc failures this period`), so `grep CRC` is a false zero.** Read-only Flux works through
the dashboard's public proxy, no token.

Standing facts: images are multi-arch (DEC-0214/0215); versions follow DEC-0222's SemVer rule; the
loop writer and `influx.py` ship as extensions, prod mounts both; `t-weewx` (996:986) runs under
`--cap-drop ALL`. **#475 is parked on purpose.** The prod log is `/srv/docker/weewx/logs/weewx.log`,
rotated daily to `weewx.log.YYYY-MM-DD`, 30 days kept. The bundled Go decoder is byte-identical to
`lheijst/rtldavis` master (S178). Tests are pytest-only (#502). `marvinctl inspect` takes containers
only (S185). On marvin, `doctor` exits 13 (the dongle is held by prod); that is the correct verdict.

### ▶▶ S192 JOB LIST

0. **ROADMAP full reconciliation** (its tripwire falls due at S192). Then **read the gate's results
   since 11-07 12:01 ET:** any `Go time gate dropped a frame` line (keep its bytes and offset; expect
   under one a day; `marvinctl grep` takes one token, so grep `gate`) and any gap with no such line.
   Around 2026-12-04, re-run `ops/garbage_gap_corr.py` over the 30 days after the deploy: expect no
   garbage-then-gap events. #536 stays open until then.
1. **Watch the three upstream threads still open** (the lheijst/rtldavis#2 comment, weewx-influx2#1,
   matthewwall/weewx-wcloud#6; if he adds a license, retag `wcloud.py`) and #514. weewx-contrib#2
   and weewx-packages#6 closed 10-29 (recorded S188; a reply to vinceskahan's fork-consolidation
   note is the owner's call, none owed). Keep `docs/UPSTREAM-THREADS.md` current. Upstream unmoved at
   S191; #514 moved, see job 7.
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
   that day's extracts; after the deploy a gap behind one means a noise decode inside the 100 ms
   window, so add it to #536. Clear through 2026-11-07 12:01 ET except the 11-04 12:53 row.
6. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, the reset-from-112-or-above phantom, whether to tell the
   `weewx-packages` maintainer about DEC-0218 option B, `git worktree prune` in heartofgold (stale
   S161 entry), CI mypy pinned `2.3.0` while the pre-commit rev lags, the
   `.claude/worktrees/s180c-audit39-uploader-tests-0d3322` leftover in this checkout (detached, prune
   it), the 10-27 00:00 to 09:17 period at double the CRC-failure rate (ended with the loopjson
   restart; noted, not chased), `rtldavis.py` line 43's stale `0.20+ws.7` in the header notice,
   weewx-monitor still running the 10-22 process while the on-disk file carries S179's refactor
   (restart it deliberately, CONSTANTS deploy layers).
7. **Second dongle, early December (reminder set for Sat 2026-12-05 09:00 ET):** the #514 A/B of
   hilman2's Python port (weewx-packages 0.22.0, which credits two changes from this fork) beside
   our Go decoder, and a v3-vs-V4 A/B. hilman2 answered: option names stable through 0.22.x, Pi 4
   demodulator 9.7% of one core (31% in frequency search), no x86 numbers yet. **The V4 needs
   librtlsdr newer than Debian bookworm's 0.6.0, so build the test container on trixie**; check
   which base our image uses. The maintainer question waits on the test; any decoder swap needs a
   DEC (DEC-0014). **cdavis289 posted on #514 (11-06): a 72-hour Go v0.21.2 vs Python v0.22.2 run on
   real hardware, two Nooelec dongles, full results expected about 11-09.** Read them before
   designing our A/B; no reply owed.

## Current state (S191)

| Thing | State |
|---|---|
| Prod | marvin, `v2.4.0` as `:marvin-live` since 2026-11-04 18:36:38 ET, weewx 5.5.2, gain 372. Writer mounted at 1.1.0 since 2026-10-27 09:16 ET |
| InfluxDB / monitor | marvin, `weewx-influxdb.service`; weewx-monitor process from 10-22 (sha `5cd09917…`; on disk `2f8a1eda…` = `dev`), `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric); about 255 CRC failures a minute; 0 archive gaps 11-05 00:00 to 11-07 12:01 ET |
| `main`/`dev` | `main` = the v2.4.0 promotion (`c376037`, PR #545, `prod-baseline-20261104`); `dev` = main plus this doc-only record of the Hub state |
| Docker Hub | `:v2.4.0` is the multi-arch index `2b146586…` (amd64 `82220200…` = prod, arm64 `e986aae1…`), joined 2026-11-06 01:48 ET. `:latest` = `:v2.4.0` since 2026-11-06 01:52 ET, moved by the owner |
| Trackers | repo: #536 (v2.4.0 in prod, open until the 30-day re-run), #475 parked, #380 info, #514 (December A/B) · ops: #440 (second dongle, December), #110 (gated, Jan-Feb), #344 · upstream open: lheijst/rtldavis#2 comment, weewx-influx2#1 (reply 10-29), matthewwall/weewx-wcloud#6 (license request); closed 10-29: weewx-contrib#2 (not interested), weewx-packages#6 (fixed in 0.22.0) |

## Blockers

Unchanged from S145 except blocker 1: 1 freeze mechanism (DEC-0068/0094) **now has a measured
mechanism for the short gaps (DEC-0229); the 10-22 62 min outage and DEC-0083's long tail are not
it**, 2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

S191 ran on Opus 5.5, the picker left raised from S190, for watch work that wanted Sonnet; no
`/model` switch this session. The desktop picker persists: switch it back to Sonnet by hand. S192:
Sonnet for the reconciliation and the watches.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4).
S180 adds to §2: this repo requires PR branches current with `dev`, so after one merge every other
open PR needs `gh pr update-branch` and a CI rerun before its own merge — sequence them. S185 adds:
two children that append to the same file conflict anyway; resolve by keeping both blocks.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else (CLAUDE.md's Documentation map, DEC-0063).
Git workflow, secrets handling and the exact gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-11-07 (S191: watch session, second live drop, no gaps, no prod change)._
