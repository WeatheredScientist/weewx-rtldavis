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

## ▶ Resume here (S150 → S151)

### What's settled (do not re-derive)

**v2.0.19 has run in prod since 2026-10-02 00:18:38 ET (DEC-0208): weewx 5.5.2, nothing
else changed.** The rapidfire thread's move to `rtupdate.wunderground.com` is confirmed on the
station's public WU page. Tagged `v2.0.19` with a GitHub release; `:v2.0.19` on Docker Hub (the
first real `marvinctl push`, digest equal to prod's). The monitor's #413 has run since 2026-09-29
09:31:16 ET.

**`eaglehunt-ops#357` is designed and coded on `dev` (DEC-0209, S150): option (A).**
`pressure_service.py` reads WeatherLink's `bar_absolute` from the barometer record and injects it
as weewx's `pressure`; `prefer_hardware` keeps it, `altimeter` derives from it. The owner's probe
confirmed the key on this station (29.534 beside 30.127 sea-level, inHg, one record). Both
consumers read neither field today. **Baked, so it is NOT live until v2.0.20 is built.**
`DISC-0002` has its boundary timestamp and level shift left blank for the deploy.

**#423's swap path is proved end to end as `t-weewx` (S148).** Schedule stood down, arm `T` kept in
`arm_cmd`, timer not installed. **`eaglehunt-ops#360` is done on weewx's side** (both units under
`--cap-drop ALL` + `no-new-privileges`). The S145 audit's ten high items shipped; 29 medium/low
stay in `docs/CODE_REVIEW_S145.md`; the secret gate's four holes are #421. ROADMAP next check: S156.

### ▶▶ S151 JOB LIST

1. **Release v2.0.20 (DEC-0209's deploy), DEC-0204's shape, the owner's go at each step.** Stamp
   PR first (Dockerfile + `soak_check.sh` fallback; `EXPECT_DRIVER` stays `0.20+ws.6`, no driver
   change), then `marvinctl pull` → `build` → `exec-ro` sha check (`pressure_service.py` is the
   one baked file that should differ from v2.0.19) → `tag :marvin-live` → `restart weewx.service`.
   Verify: the first fetch logs `got pressure X, station pressure Y` (the `no bar_absolute`
   warning means the fallback ran); the first archive row after it carries `pressure` ≈ 29.5 and
   `altimeter` moved. **Then fill `DISC-0002`**: boundary timestamp, the measured shift in
   `pressure`/`altimeter` across it (compare the derived rows just before to the measured rows
   just after). Records PR: DEC-0209 status → deployed, CHANGELOG, this file. Push `:v2.0.20` to
   Hub (`marvinctl push`). Reply on `eaglehunt-ops#357` with the timestamp so HLF adds its mapping.
2. **`:latest` on Docker Hub still points at v2.0.13** (owner's gesture, DEC-0078's route).
3. **`dev` → `main` promotion**, the owner's timing. `main` is v2.0.13.
4. **Watches, no action:** WU gold star (needs ≥ 5 uninterrupted days; the clean run started at
   the 10-02 restart) · OWM and Windy rain in millimeters (needs rain; ERR-0010) · the first
   `frame failed message-type proof` line · freeze lead (blocker 1), measure at the next freeze.
5. **Owner-only:** `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the shell profile, never CI; the
   remainder of `eaglehunt-ops#358`.
6. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry.

## Current state (S150 close)

| Thing | State |
|---|---|
| Prod | marvin, **`v2.0.19`** as `:marvin-live` (image `e1828402…`) since 2026-10-02 00:18:38 ET, weewx 5.5.2, gain 372, `t-weewx` (996:986), under #360's flags. `:v2.0.18` is local for rollback |
| InfluxDB | marvin, `weewx-influxdb.service`, under #360's flags since S147 |
| weewx-monitor | sha `5cd09917…`, running since 2026-09-29 09:31:16 ET; `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| Campaign harness | schedule empty (stand-down), state `BASELINE`, timer not installed |
| `main`/`dev` | `dev` = DEC-0209's code, unreleased. `main` is still v2.0.13 (job 3) |
| Docker Hub | `:v2.0.19` (= prod) · `:v2.0.16` · `:latest` = v2.0.13 |
| Trackers | repo: #421 (gate holes), #380 informational · ops: #357 weewx side built, deploy pending (job 1) · #358 owner remainder · #265/#110 deferred-trigger · #306 residual · #344 macOS LAN |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

**S150 ran on Sonnet 5.5 for the check-in, then Fable 5.1 for DEC-0209's design** (a bare `/model`
in the desktop app — it persists; restore Sonnet at close). **Start S151 on Sonnet:** job 1 is a
locked release routine.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after.** **New this session:**
- §3: the auto-mode classifier can deny a floor-allowed `marvinctl exec` into the live container as
  a production read, and the denial covers every other route to the same read. The owner ran the
  one-liner instead. A one-off script needs the venv interpreter
  (`/opt/weewx-venv/bin/python3`), not the container's `python3`.
- The secret-read guard keys on the conf's file NAME in a command string, even for the public
  `.example` copy; read that with the Read tool, not grep.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-10-06 (S150). DEC-0209 coded, unreleased. Job 1 is the v2.0.20 release._
