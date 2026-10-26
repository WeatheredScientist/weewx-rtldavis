# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3 — the "escape the WeatherLink lock" tool. A public, published
WeeWX extension (Docker Hub + GitHub releases), GPLv3. Its real contract is the **data it emits**
(loop-JSON + InfluxDB line-protocol schema), not any one consumer. The dashboard that consumes it
is a **separate repo** — don't make dashboard changes here.

---

## ▶ Resume here (S169 → S170)

### What's settled (do not re-derive)

**v2.0.21 runs in prod since 2026-10-26 18:16:14 ET** (image `5ca44ede…`, built on marvin from
`dev`@`c9c5934`, driver banner `0.20+ws.7`). It carries: #451 (`pressure_service.py`), #458 (the Go
decoder counts CRC failures, log-only), #456's 240 s init grace, #465/DEC-0218 (rain recovery judged
against the last accepted count), #468 (seed backups removed), audit 15, and #474's Dockerfile
change. **The build gate caught a DEC-0219 gap (S169, PR #484):** the extension install alone left
`user.influx` unimportable, because the venv's `user` package shadows `weewx-data/bin/user`; the
Dockerfile copies the root `influx.py` into the venv again, and `smoke_image.sh` now imports it. The
baked config sha moved `ee62b7a2…` to `f67762d9…` (only the Influx placeholders, now
`YOUR_INFLUX_*`). Rollback: retag `:v2.0.20` as `:marvin-live` + restart (CONSTANTS).

**v2.0.20 (2026-10-06, DEC-0209):** WeatherLink's `bar_absolute` is `pressure`, `altimeter` derives
from it; archive `pressure` is measured from 22:18:00 ET (DISC-0002). `main` = `prod-baseline-20261006`
(v2.0.20); `dev` is ahead by v2.0.21 and design records, so **v2.0.21 is not promoted to `main`
yet**. Images are multi-arch (DEC-0214/0215, `scripts/join_multiarch.sh`). `LoopJsonWriter` and
`influx.py` ship as extensions (`loopjson-v1.0.0`, `influx-v0.20+ws.2`); prod still mounts both.
`t-weewx` (996:986) under `--cap-drop ALL` (ops#360 done); swap path proved (#423). The S145 audit's
ten high items shipped; 29 medium/low stay in `docs/CODE_REVIEW_S145.md`. The public face was
rewritten in S156 (DEC-0213); a continuation org, `weewx-packages`, folded our upstream PRs on
2026-10-21 (no reply owed). The 2026-10-22 marvin outage is ERR-0011. Designs accepted, not built:
**#473 / DEC-0220 + DEC-0221** (`extra_fields`, `loop_interval_s`, contract
`loop_json_writer/1.1.0`). **#475 (portable SensorQC) is parked on purpose.** #481: the driver
drops message 9's 10-minute gust.

### ▶▶ S170 JOB LIST

1. **Finish the v2.0.21 release if S169 did not:** `:v2.0.21-amd64` on Hub, the multi-arch join
   (dry run, then `--apply` on the owner's go), `:latest` (owner's gesture), `v2.0.21` tag and
   GitHub release, promotion `dev` to `main` with `prod-baseline-20261026` (owner's go). Close
   **#474** with a comment once the owner calls it done.
2. **Watch, no action unless it fires:** measured `pressure` keeps arriving (a `no bar_absolute`
   WARNING means DISC-0002 needs a second boundary) · WU gold star (owner reads it off WU) · OWM and
   Windy rain in millimeters (needs rain; ERR-0010) · freeze lead (blocker 1) at the next freeze.
3. **Collect a day of v2.0.21 evidence, then design #459** (frontier tier, DEC first): the `crc
   failures this period` lines and DEC-0218's `rain: counter recovered` lines.
4. **Build #473 from DEC-0220/0221** (tier:mid, Sonnet): small steps, tests that cannot pass
   vacuously (GOTCHAS §1), INTERFACES §1 rows per sensor class, tell dash when the contract ships.
   **#481** (`windGust10`) is its own mid-tier issue; design the key name first.
5. **ROADMAP tripwire is overdue** (next check was S166; S166 to S169 skipped it): run the full
   reconciliation pass (`docs/ROADMAP.md`, "Keeping this current").
6. **P0.8 phase 1:** the host steps wait on marvin's answer to **ops#427** (disposable Debian VM);
   then the GitHub About text and topics (owner's go). First arm64 run against a live radio (any
   Pi with a dongle); until then README says smoke-tested only.
7. **Owner-only:** `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the shell profile, never CI. Whether to
   tell the `weewx-packages` maintainer about DEC-0218 option B.
8. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, audit 37 and 39 (phase 5), the reset-from-112-or-above phantom.

## Current state (S169)

| Thing | State |
|---|---|
| Prod | marvin, **`v2.0.21`** as `:marvin-live` (image `5ca44ede…`) since 2026-10-26 18:16:14 ET, weewx 5.5.2, gain 372, `t-weewx`. `:v2.0.20` (`f617c9ca…`) is local for rollback |
| InfluxDB / monitor | marvin, `weewx-influxdb.service`; weewx-monitor sha `5cd09917…` since 2026-09-29, `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| `main`/`dev` | `main` = v2.0.20's promotion (`prod-baseline-20261006`); `dev` ahead (above) |
| Docker Hub | `:v2.0.20` = `:latest`, multi-arch. `:v2.0.21` not pushed until job 1 is done |
| Trackers | repo: #458/#459 decoder, #473/#481 live feed, #474 (close), #475 parked, #380 info · ops: #427 VM, #357 done on our side, #344 macOS LAN, #433 (this file's size) |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

S169 ran on Sonnet 5.5 (release execution of a locked design). S166 (#473 design) ran on Opus 5.5 at
medium. A bare `/model` switch persists in the desktop app: restore the Sonnet floor if one is used.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after.** S169 adds one to §4: an image build is not proof of an import
path (the smoke test now imports `user.influx`).

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-10-26 (S169). v2.0.21 in prod; Hub push, tag and `main` promotion pending._
