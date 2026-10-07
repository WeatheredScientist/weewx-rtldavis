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

**v2.0.20 has run in prod since 2026-10-06 22:15:14 ET (DEC-0209): WeatherLink's `bar_absolute`
is weewx's `pressure`, `altimeter` derives from it, nothing else changed** (of the seven baked
modules only `pressure_service.py` differs from v2.0.19; engine 5.5.2, banner `0.20+ws.6`). The
archive's `pressure` is measured from **22:18:00 ET** (DISC-0002: +0.008 inHg step, `barometer`
unchanged). Zero WARNING/ERROR lines, soak 19/0/0. Tagged `v2.0.20` on `9a86c97` with a GitHub
release; `:v2.0.20` on Docker Hub (digest = prod's). `eaglehunt-ops#357` closed on weewx's side
with the boundary timestamp; HLF gates its mapping on it. Rollback: retag `:v2.0.19` + restart —
that puts the columns back on the derived path.

**#423's swap path is proved end to end as `t-weewx` (S148).** Schedule stood down, arm `T` kept in
`arm_cmd`, timer not installed. **`eaglehunt-ops#360` is done on weewx's side** (both units under
`--cap-drop ALL` + `no-new-privileges`). The S145 audit's ten high items shipped; 29 medium/low
stay in `docs/CODE_REVIEW_S145.md`; the secret gate's four holes are #421. ROADMAP next check: S156.

### ▶▶ S151 JOB LIST

1. **Watch, no action unless it fires:** the measured `pressure` keeps arriving (a `no bar_absolute`
   WARNING in `weewx.log` means the fallback ran and the column went derived again — then DISC-0002
   needs a second boundary) · WU gold star (≥ 5 uninterrupted days; the clean run restarted at
   the 10-06 22:15 restart) · OWM and Windy rain in millimeters (needs rain; ERR-0010) · the first
   `frame failed message-type proof` line · freeze lead (blocker 1), measure at the next freeze.
2. **`:latest` on Docker Hub still points at v2.0.13** (owner's gesture, DEC-0078's route).
3. **`dev` → `main` promotion**, the owner's timing. `main` is v2.0.13; v2.0.14 to v2.0.20 have run
   unpromoted.
4. **Owner-only:** `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the shell profile, never CI; the
   remainder of `eaglehunt-ops#358`.
5. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry.

## Current state (S150 close)

| Thing | State |
|---|---|
| Prod | marvin, **`v2.0.20`** as `:marvin-live` (image `f617c9ca…`) since 2026-10-06 22:15:14 ET, weewx 5.5.2, gain 372, `t-weewx` (996:986), under #360's flags. `:v2.0.19` is local for rollback |
| InfluxDB | marvin, `weewx-influxdb.service`, under #360's flags since S147 |
| weewx-monitor | sha `5cd09917…`, running since 2026-09-29 09:31:16 ET; `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| Campaign harness | schedule empty (stand-down), state `BASELINE`, timer not installed |
| `main`/`dev` | `dev` = this closeout's merge (v2.0.20 records). `main` is still v2.0.13 (job 3) |
| Docker Hub | `:v2.0.20` (= prod) · `:v2.0.19` · `:v2.0.16` · `:latest` = v2.0.13 |
| Trackers | repo: #421 (gate holes), #380 informational · ops: #357 weewx side done, HLF's mapping pending on their side · #358 owner remainder · #265/#110 deferred-trigger · #306 residual · #344 macOS LAN |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

**S150 ran on Sonnet 5.5 for the check-in, then Fable 5.1 for DEC-0209's design and, on the
owner's go, the release** (a bare `/model` in the desktop app — it persists; the owner restores
Sonnet from the model menu). **Start S151 on Sonnet:** nothing frontier-shaped is queued.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after.** **New this session:**
- §3: the auto-mode classifier can deny a floor-allowed `marvinctl exec` into the live container as
  a production read (it did for the WeatherLink probe; it allowed a read-only sqlite probe an hour
  later — independent draws). The denial covers every other route to the same read; the owner ran
  the one-liner. A one-off script needs the venv interpreter (`/opt/weewx-venv/bin/python3`).
- §3: `marvinctl exec-ro` rejects `{}` and any multi-token argument; zsh needs `${=var}` to
  word-split a file list. `soak_check.sh` inside the post-restart acquisition gap (~3 min) reads
  ARCHIVE STALLED — re-run after the first record, don't act on it.
- §1: a bare `marvinctl tail` of `weewx.log`'s startup block prints every uploader's station
  identifier and the InfluxDB LAN IP into the transcript; filter with `grep` on the signal wanted.
- The secret-read guard keys on the conf's file NAME in a command string, even for the public
  `.example` copy; read that with the Read tool. `gh pr merge … -R owner/repo` trips the Class C
  guard (it can't read the repo from `-R`); the bare form in the check-gated checkout is advisory.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-10-06 (S150). v2.0.20 in prod: measured station pressure. Nothing queued but
watches and the owner's promotions._
