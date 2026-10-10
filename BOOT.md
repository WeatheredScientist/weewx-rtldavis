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

## ▶ Resume here (S152 → S153)

### What's settled (do not re-derive)

**v2.0.20 has run in prod since 2026-10-06 22:15:14 ET (DEC-0209): WeatherLink's `bar_absolute`
is weewx's `pressure`, `altimeter` derives from it, nothing else changed** (of the seven baked
modules only `pressure_service.py` differs from v2.0.19; engine 5.5.2, banner `0.20+ws.6`). The
archive's `pressure` is measured from **22:18:00 ET** (DISC-0002: +0.008 inHg step, `barometer`
unchanged). Zero WARNING/ERROR lines, soak 19/0/0 at the release. Tagged `v2.0.20` on `9a86c97`
with a GitHub release; `:v2.0.20` on Docker Hub (digest = prod's). `eaglehunt-ops#357` closed on
weewx's side with the boundary timestamp; HLF gates its mapping on it. Rollback: retag `:v2.0.19` +
restart — that puts the columns back on the derived path. **The same night: `dev` promoted to
`main` (`prod-baseline-20261006`, #436; `main` had been v2.0.16, not v2.0.13) and Docker Hub
`:latest` moved to v2.0.20.** `main` lags `dev` by the closeout docs, S151's secret-gate fix (#439)
and S152's docs fix (#441): nothing that changes the image or prod.

**#423's swap path is proved end to end as `t-weewx` (S148).** Schedule stood down, arm `T` kept in
`arm_cmd`, timer not installed. **`eaglehunt-ops#360` is done on weewx's side** (both units under
`--cap-drop ALL` + `no-new-privileges`). The S145 audit's ten high items shipped; 29 medium/low
stay in `docs/CODE_REVIEW_S145.md`. **The secret gate's four detector holes (#421) are closed
(S151, DEC-0210, merged as #439).** **`LoopJsonWriter` runs last in `process_services`, with
`data_services` empty, since 2026-07-12 (S152 re-read the live conf); `ARCHITECTURE.md` and the
writer's deploy docstring now say so (`eaglehunt-ops#395`, #441).** ROADMAP next check: S156.

### ▶▶ S153 JOB LIST

1. **Watch, no action unless it fires** (S152 checked: soak 14 passed / 0 failures, no
   `bar_absolute` fallback warning): the measured `pressure` keeps arriving (a `no bar_absolute`
   WARNING in `weewx.log` means the fallback ran and the column went derived again — then DISC-0002
   needs a second boundary) · WU gold star (≥ 5 uninterrupted days; the clean run restarted at
   the 10-06 22:15 restart) · OWM and Windy rain in millimeters (needs rain; ERR-0010) · the first
   `frame failed message-type proof` line · freeze lead (blocker 1), measure at the next freeze.
2. **`weewx#440` — package `loop_json_writer.py` as an installable WeeWX extension** (the
   dashboard's DEC-0348 ask; no deadline, its adopter recipe cites the install command once it
   exists). **Design first** (PRINCIPLES §8): release artifact of this repo vs its own small repo;
   `install.py` plus the `[LoopJsonWriter]` stanza; a README on the fields, units and cadence; the
   field map stays byte-identical, and a version string in the output lets the dashboard detect an
   old writer. Name the model tier at its start.
3. **Owner-only:** `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the shell profile, never CI; the
   remainder of `eaglehunt-ops#358` (the owner's off-screen address check).
4. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry.

## Current state (S150 close; trackers S152)

| Thing | State |
|---|---|
| Prod | marvin, **`v2.0.20`** as `:marvin-live` (image `f617c9ca…`) since 2026-10-06 22:15:14 ET, weewx 5.5.2, gain 372, `t-weewx` (996:986), under #360's flags. `:v2.0.19` is local for rollback |
| InfluxDB | marvin, `weewx-influxdb.service`, under #360's flags since S147 |
| weewx-monitor | sha `5cd09917…`, running since 2026-09-29 09:31:16 ET; `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| Campaign harness | schedule empty (stand-down), state `BASELINE`, timer not installed |
| `main`/`dev` | `main` = `dev` at the v2.0.20 promotion (`prod-baseline-20261006`, S150); `dev` is ahead only by docs and the secret gate (see above). Before the promotion `main` was v2.0.16's (`prod-baseline-20260904`, #324, S122) plus the misrouted #338 — S149/S150's BOOT and CONSTANTS said "v2.0.13", stale since S122. The promotion merge resolved every conflict in `dev`'s favor |
| Docker Hub | `:v2.0.20` = `:latest` (= prod, `f617c9ca…`; `:latest` moved 2026-10-06 22:52 ET) · `:v2.0.19` · `:v2.0.16` |
| Trackers | repo: #440 (dashboard's extension ask, design first), #380 informational · ops: #395 closes with #441, #357 weewx side done (HLF accepts, ops closes), #358 owner remainder · #265/#110 deferred-trigger · #306 residual · #344 macOS LAN |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

**S152 ran on Sonnet 5.5 throughout** (ops check-in, #395, the closeout); no bare `/model` switch,
nothing to restore. **Start S153 on Sonnet** unless the first job is #440's design discussion, which
is the one judgment-shaped item queued: say so in the first reply and name the tier.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after.** S151's and S152's small marvin-read traps (the live log path,
the secret-read guard on a trailing pipe, `exec-ro` argument limits, the classifier on container
reads) are in §3's last bullets.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-10-10 (S152). v2.0.20 steady in prod; ops#395's docs drift fixed on #441; nothing queued but #440's design, the watches and the owner-only items._
