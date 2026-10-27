# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S170 → S171)

### What's settled (do not re-derive)

**v2.0.21 runs in prod since 2026-10-26 18:16:14 ET** (image `5ca44ede…`, driver banner
`0.20+ws.7`; rollback in CONSTANTS). `main` = `prod-baseline-20261026`.

**#473 is built and on `dev` (S170, PR #490, merge `12340a4`): loopjson 1.1.0** (DEC-0220/0221).
`extra_fields` + `[[ttl]]` (weewx-influx2 key names), `sum`-extractor deltas refused, extras on the
shared cache, `loop_interval_s` (median gap, omitted outside [1, 3600]). Tests run against real
WeeWX in `loopjson.yml`; `prove_loopjson.sh` proves it on the Simulator. **Not released, not in
prod:** prod's mounted writer is still 1.0.0. #471 closed (PR #489, docs only).

Standing facts: images are multi-arch (DEC-0214/0215); versions follow DEC-0222's SemVer rule;
the loop writer and `influx.py` ship as extensions (`loopjson-v1.0.0`, `influx-v0.20+ws.2`), prod
mounts both; `t-weewx` (996:986) runs under `--cap-drop ALL`. **#475 is parked on purpose.**

### ▶▶ S171 JOB LIST

1. **Release #473.** `git tag -l 'loopjson-v*'`: if `loopjson-v1.1.0` is missing, tag it on
   `12340a4` (annotated; the push publishes the zip; owner's go). Then: a note on dash#936 and a
   one-line ring (the contract shipped, dash DEC-0404's four asks answered); prod deploy of the
   mounted writer (owner-run `scp` to the project root, then `marvinctl` restart, one feed read
   showing `loop_interval_s`); close #473 with a comment.
2. **v2.1.0 image** (DEC-0222 names #473 as its release). The writer is mounted, not baked, so
   first check what the image carries that changed; tell dash when the contract ships.
3. **Owner-only:** move `:latest` to `:v2.0.21`; close #474 once satisfied; `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1`
   in the shell profile (never CI).
4. **Watch, no action unless it fires:** `no bar_absolute` WARNING (DISC-0002 needs a second
   boundary) · WU gold star · OWM/Windy rain in millimeters (needs rain; ERR-0010) · the next
   freeze (blocker 1).
5. **Collect a day of v2.0.21 evidence, then design #459** (frontier tier, DEC first): the
   `crc failures this period` lines and DEC-0218's `rain: counter recovered` lines.
6. **#481** (`windGust10`): its own mid-tier issue; design the key name first.
7. **ROADMAP tripwire is overdue** (next check was S166; S170 updated only the #473 line): run the
   full reconciliation pass (`docs/ROADMAP.md`, "Keeping this current").
8. **P0.8 phase 1:** ops#427 is down to one item, re-running DEPLOY.md's three unit checks in a
   guest with a virtual USB device (the host steps otherwise proved). Then the GitHub About text and
   topics (owner's go). First arm64 run against a live radio; until then README says smoke-tested.
9. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, audit 37 and 39, the reset-from-112-or-above phantom, whether to
   tell the `weewx-packages` maintainer about DEC-0218 option B.

## Current state (S170)

| Thing | State |
|---|---|
| Prod | marvin, `v2.0.21` as `:marvin-live` since 2026-10-26 18:16:14 ET, weewx 5.5.2, gain 372. Writer mounted at 1.0.0 |
| InfluxDB / monitor | marvin, `weewx-influxdb.service`; weewx-monitor sha `5cd09917…`, `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| `main`/`dev` | `main` = v2.0.21's promotion; `dev` = main + #473's build (`12340a4`) + docs |
| Docker Hub | `:v2.0.21` multi-arch; `:latest` still `:v2.0.20` until the owner moves it |
| Trackers | repo: #473 (release left), #481, #474 (close), #475 parked, #458/#459 decoder, #468 (shipped, close), #380 info · ops: #427 VM, #433 (this file), #357, #344 |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

S170 ran on Sonnet 5.5 (building a locked design). Judgment work (#459's design) wants Opus 5.5.
A bare `/model` switch persists in the desktop app: restore the Sonnet floor if one is used.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4).
S170 adds three to §1: zsh does not word-split `$VAR` (a failed stage, then a "clean" scan);
a commit piped through `grep` hides a failed hook; the secret-read guard's false trips.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else (CLAUDE.md's Documentation map, DEC-0063).
Git workflow, secrets handling and the exact gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-10-27 (S170). #473 built on `dev`; release, prod deploy and v2.1.0 are S171's._
