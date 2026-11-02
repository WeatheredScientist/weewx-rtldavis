# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S187 → S188)

### What's settled (do not re-derive)

**v2.3.0 runs in prod since 2026-11-01 11:31:49 ET** (image `71c201b6…`, driver banner still
`0.20+ws.9`, no driver change): DEC-0228's `ENTRYPOINT` dispatch, `doctor`, the informational
`HEALTHCHECK`, plus `WEEWX_DRIVER=simulator` at seed time. Rollback: `:v2.2.0-prod-pre-v2.3.0`
(`0a790696…`), then `:v2.1.0-prod-pre-v2.2.0`. **P0.8 phase 6 is built out**; only its acceptance
test is left. **loopjson 1.1.0** runs since 2026-10-27 09:16 ET. ROADMAP full reconciliation done
S183 (next check S192).

**S187 closed three asks.** ops#439: HoG ran `docs/DEPLOY.md`'s three systemd checks in a guest with
a real USB stick passed through; all pass (verdict posted, closed). DEPLOY.md's stale Quick start
references fixed and a by-hand seeding step added (the unit refuses to start without a config, so
the image never seeds under systemd; PR #534). ops#442: **`windGust10_mph` is already in InfluxDB
archive points since 2026-10-28 12:30 ET** (points carry the in-memory archive record, not the
SQLite row); no build, documented in `docs/INTERFACES.md` §2 (PR #537), dashboard confirmed, closed.
**ERR-0012** records the 10-31 10:04 ET phantom 30 mph gust, data left as is by the owner's call
(PR #535). Read-only Flux works through the dashboard's public proxy (`<origin>/query`, origin in
the dashboard's `eh-site.js`), no token needed.

Standing facts: images are multi-arch (DEC-0214/0215); versions follow DEC-0222's SemVer rule; the
loop writer and `influx.py` ship as extensions, prod mounts both; `t-weewx` (996:986) runs under
`--cap-drop ALL`. **#475 is parked on purpose.** The prod log is `/srv/docker/weewx/logs/weewx.log`.
The bundled Go decoder is byte-identical to `lheijst/rtldavis` master (S178). Tests are pytest-only
(#502). `marvinctl inspect` takes containers only, not images (S185). On marvin, `doctor` exits 13
(the dongle is held by prod) — that is the correct verdict there, not a fault.

### ▶▶ S188 JOB LIST

0. **#536 (new, tier:frontier, the owner's concern):** CRC-valid garbage frames. ~400,000 CRC
   failures a day means a few chance passes a day; ERR-0012 got through the payload checks, and on
   10-30 13:10 ET a rejected 187 mph frame was the last line before a silent 2 min 49 s gap (the P0
   freeze lead's shape, third instance; weewxd freeze vs lost station not separable from the log). The issue proposes a payload-independent timing check; **measure first** (arrival
   offset vs the expected slot), no build before a DEC. Judgment work: Opus 5.5.
1. **Watch the five upstream posts for replies** (weewx-contrib#2, weewx-packages#6, the
   lheijst/rtldavis#2 comment, weewx-influx2#1, matthewwall/weewx-wcloud#6; if he adds a license,
   retag `wcloud.py`) and keep `docs/UPSTREAM-THREADS.md` current.
2. **Phase 6's acceptance test:** a stock 64-bit Pi OS plus `docs/QUICKSTART.md`, timed, by someone
   who has not read the repo. Needs a person, not a session.
3. **Needs the owner:** the GitHub About text and topics; `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in
   the shell profile (never CI); **the hot-swap code** (~230 driver lines, no in-repo producer;
   #509's PR body has the analysis) — keep for the gain campaign `BACKLOG.md` carries, or a DEC to
   remove it with `ops/rx_experiment.sh` converted (DEC-0014).
4. First arm64 run against a live radio still open (ops#439 proved the amd64 systemd path only).
5. **Watch, no action unless it fires:** `no bar_absolute` WARNING (DISC-0002) · WU gold star ·
   OWM/Windy rain in millimeters (needs rain; ERR-0010) · the next freeze (blocker 1) · any
   `Go burst gate dropped a frame` line (keep its bytes) · the first `unhealthy` on prod (it never
   restarts anything; note what the log was doing) · any gust far above `windGust10` or a
   `rejecting implausible` wind line (add it to #536 with the minute's CRC count).
6. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, the reset-from-112-or-above phantom, whether to tell the
   `weewx-packages` maintainer about DEC-0218 option B, `git worktree prune` in heartofgold (stale
   S161 entry), CI mypy pinned `2.3.0` while the pre-commit rev lags, the `.claude/worktrees/s180b-*`
   leftover in this checkout.
7. **Second dongle, early December (reminder set for Sat 2026-12-05 09:00 ET):** the #514 A/B of
   hilman2's Python port beside our Go decoder, and a v3-vs-V4 A/B. Holding reply posted (10-30);
   hilman2 answered: option names stable through 0.22.x, Pi 4 demodulator 9.7% of one core (31% in
   frequency search), no x86 numbers yet. **The V4 needs librtlsdr newer than Debian bookworm's
   0.6.0, so build the test container on trixie**; check which base our image uses. The maintainer
   question waits on the test; any decoder swap needs a DEC (DEC-0014).

## Current state (S187)

| Thing | State |
|---|---|
| Prod | marvin, `v2.3.0` as `:marvin-live` since 2026-11-01 11:31:49 ET, weewx 5.5.2, gain 372, `healthy`. Writer mounted at 1.1.0 since 2026-10-27 09:16 ET |
| InfluxDB / monitor | marvin, `weewx-influxdb.service`; weewx-monitor sha `5cd09917…`, `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| `main`/`dev` | `main` = the v2.3.0 promotion (`fe3761a`, PR #530, `prod-baseline-20261101`); `dev` = main plus doc-only work from S185 to S187 (PRs #531 to #537) |
| Docker Hub | `:v2.3.0` and `:latest` are the multi-arch index `03f3c891…` (amd64 `71c201b6…` = prod, arm64 `c0d54664…`), `:latest` moved by the owner 2026-11-01 12:25 ET |
| Trackers | repo: #536 (CRC-valid garbage frames, new S187), #475 parked, #380 info, #514 (December A/B) · ops: #440 (second dongle, December), #110 (gated, Jan-Feb), #433 (this file), #357, #344 · upstream: weewx-contrib#2, weewx-packages#6, lheijst/rtldavis#2 comment (all 10-29), weewx-influx2#1 (reply 10-29), matthewwall/weewx-wcloud#6 (license request, 10-29). Closed S187: ops#439, ops#442; ops#435 closed by ops |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

S187 ran on Opus 5.5, again because the desktop app's model picker was left raised; no bare `/model`
switch was made and settings.json's floor was never touched. Switch the picker back to Sonnet by
hand. S188: Sonnet for the watches; #536's measurement and design are Opus 5.5 work.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4).
S180 adds to §2: this repo requires PR branches current with `dev`, so after one merge every other
open PR needs `gh pr update-branch` and a CI rerun before its own merge — sequence them. S185 adds:
two children that append to the same file conflict anyway; resolve by keeping both blocks.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else (CLAUDE.md's Documentation map, DEC-0063).
Git workflow, secrets handling and the exact gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-11-02 (S187: ops#439 verdict, ops#442 answered, ERR-0012, #536 filed)._
