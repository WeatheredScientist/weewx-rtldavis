# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S176 → S177)

### What's settled (do not re-derive)

**v2.1.0 runs in prod since 2026-10-28 15:40:40 ET** (image `6e10c71b…`, driver banner `0.20+ws.8`:
#459's burst gate + #481's `windGust10`). Rollback: `:v2.1.0-predeploy` (`a1e6e94c…`, same driver
bytes, the S175 pre-promotion build) then `:v2.0.21`. `main` = `prod-baseline-20261028`; Hub `:v2.1.0`
is the multi-arch index `881e6c43…` (amd64 = prod's `6e10c71b…`); `:latest` is still `:v2.0.20`.
**loopjson 1.1.0** runs since 2026-10-27 09:16 ET. ROADMAP next check **S182**.

Standing facts: images are multi-arch (DEC-0214/0215); versions follow DEC-0222's SemVer rule;
the loop writer and `influx.py` ship as extensions (`loopjson-v1.1.0`, `influx-v0.20+ws.2`), prod
mounts both; `t-weewx` (996:986) runs under `--cap-drop ALL`. **#475 is parked on purpose.** The
prod log is `/srv/docker/weewx/logs/weewx.log` (tenant root, not `weewx-data`).

### ▶▶ S177 JOB LIST

1. **Watch v2.1.0 for a day:** `largest duplicate gap` lines (expect single digits, `-` when none),
   `rxCheckPercent` unchanged; any `Go burst gate dropped a frame` line is a phantom prevented, keep
   its bytes. First post-restart minutes were clean (S176); S177's look at 14 minutes was clean too.
2. **11-02 morning, cheap:** count archive rows for 2026-11-01 05:00–07:00 UTC (expect 120, no
   gap, no duplicate) and post the number on eaglehunt-ops#435.
3. **Owner-only:** move `:latest` to `:v2.1.0` (or `:v2.0.21`); `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in
   the shell profile (never CI).
4. **Watch, no action unless it fires:** `no bar_absolute` WARNING (DISC-0002 needs a second
   boundary) · WU gold star · OWM/Windy rain in millimeters (needs rain; ERR-0010) · the next
   freeze (blocker 1).
5. **P0.8:** phase 1's last item, `docs/DEPLOY.md`'s three systemd-unit checks, needs a guest with
   a virtual USB device: ops#427 is closed, so file a new ops ask when wanted. Then the GitHub
   About text and topics (owner's go). First arm64 run against a live radio; until then README
   says smoke-tested.
6. Carry forward, none due: the 13 `claude/*` and `s1xx` branches the session-end hook lists (audit for
   squash-merged work, then delete with the owner's go), offer DEC-0223's gate on lheijst/rtldavis#2 (owner's go), S126's
   job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, the reset-from-112-or-above phantom, whether to tell the
   `weewx-packages` maintainer about DEC-0218 option B, `git worktree prune` in heartofgold (a
   stale S161 entry).

## Current state (S176)

| Thing | State |
|---|---|
| Prod | marvin, `v2.1.0` as `:marvin-live` since 2026-10-28 15:40:40 ET, weewx 5.5.2, gain 372. Writer mounted at 1.1.0 since 2026-10-27 09:16 ET |
| InfluxDB / monitor | marvin, `weewx-influxdb.service`; weewx-monitor sha `5cd09917…`, `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| `main`/`dev` | `main` = v2.1.0's promotion (`prod-baseline-20261028`); `dev` = main minus the merge commit |
| Docker Hub | `:v2.1.0` multi-arch; `:latest` still `:v2.0.20` until the owner moves it |
| Trackers | repo: #475 parked, #380 info (#459, #481, #468 closed S177) · ops: #435 (11-02 count), #433 (this file), #357, #344 |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

S177 ran on Sonnet. What is left (the watch, the 11-02 count, the branch audit) is Sonnet work.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4).
S170 adds three to §1: zsh does not word-split `$VAR` (a failed stage, then a "clean" scan);
a commit piped through `grep` hides a failed hook; the secret-read guard's false trips.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else (CLAUDE.md's Documentation map, DEC-0063).
Git workflow, secrets handling and the exact gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-10-28 (S177). `windGust10` live in the feed; #459, #481, #468 closed._
