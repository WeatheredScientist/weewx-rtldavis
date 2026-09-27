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

## ▶ Resume here (S141 → S142)

### What's settled (do not re-derive)

**S141 shipped DEC-0200: UV's diode dark floor is zeroed at the source. It is live on marvin
(2026-09-27 17:39:57 ET).** `eaglehunt-ops#343` asked whether DEC-0080's exact-code solar zero
should extend to UV. Measurement showed UV's dark floor is **two** codes, not one: `uv_raw 2`
(0.04) in ~97% of dark minutes and `uv_raw 1` (0.02) in ~3%, in runs; never 0 or 3. The owner chose
the two-code exact window `UV = UV if UV is None else (0 if 0.01 < UV < 0.05 else UV)`. It is in the
live conf, the tenant-root `.rx-baseline`, and `weewx.conf.example`, and is pinned by
`tests/test_diode_floor_corrections.py`. History is not rewritten. **First dusk verified:** UV read
0.0 from 18:29 with solar ~16 W/m² (0.04 before the fix). **DEC-0080 was re-verified clean
in the same pass:** the solar floor is one code, and `sr_raw 2` appears only at twilight.

**ops#343 check-in.** Ops closed the thread and withdrew its weewx ask 23 s after the owner put the
fix on weewx. S141 posted the measurement there. Ops answered at 5:34 PM ET: there was no later owner
call, and its close was its own inference, now retracted. Ops **reopened #343 with `repo:weewx` so
weewx closes it after HLF's InfluxDB confirm** (job 2), and corrected its §1 row to `uv_raw` 1–2.

**The S140 list's job 1 was already done at S139:** `#337` closed 2026-09-19, and marvin's
`weewx_monitor.py` sha equals `dev`'s tip (restarted 2026-09-18 23:13 ET). DEC-0199's alert class is
live.

### ▶▶ S142 JOB LIST

1. **DEC-0200 full-overnight verification.** First dusk was already verified at S141: UV read 0.0
   from 18:29 at ~16 W/m². Query archive rows with `radiation = 0` after 2026-09-27 17:41 ET for any
   `0 < UV < 0.05`; expect none. **A twilight fraction such as 18:28's 0.0141 is expected**: it's a
   transition minute averaging zeroed readings with readings ≥ 0.06. A dark fraction, or any exact
   0.02/0.04, needs its minute examined. Find the code before touching the window; never widen it.
   Windy/WOW's one post-restart 429 each already recovered by 18:36. HLF will separately confirm the
   `weewx` bucket (ops#343, rung).
2. **Close ops#343 once HLF confirms** that dark UV reaches the `weewx` bucket as 0. Ops reopened the
   issue with `repo:weewx` for exactly this (5:34 PM ET). Close it with a comment, never bare.
   Ops has already confirmed there was no later owner stand-down call. Its §1 row now says
   `uv_raw` 1–2, and ops will name DEC-0200 in it (rung 2026-09-27).
3. **`#394` (surface the ISS low-battery flag `bat_iss`).** Owner-filed 2026-09-20, `tier:mid`,
   untriaged. Starts with the issue's own question: is `bat_iss` archived or surfaced anywhere yet?
4. **Reception at the dongle's new position (`5-1`) vs the old `7-1.2` cluster is unmeasured.**
   DEC-0154 fixed the crash loop, not this. Needs a longer `rxCheckPercent` read.
5. Carry forward job 8's remaining items (EnvironmentFile, `marvin-release.sh`) exactly as S126 left
   them. None are due.
6. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7)** for a maintainer reply
   (repo dormant since 2023-12-22). Don't chase it.
7. `eaglehunt-ops#306`'s residual `MANIFEST.md` cap overage: coverage beats the cap, so no action
   unless a real instance-collapse turns up.
8. `CONSTANTS.md` infra re-verify, the S105-era remainder that S129/S130/S139 didn't touch.

## Current state (S141 close)

| Thing | State |
|---|---|
| Prod | marvin, `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986). **`weewx.service` restarted 2026-09-27 17:40:18 ET to load DEC-0200** (config only, image unchanged). Clean boot |
| InfluxDB | marvin, `weewx-influxdb.service`, unchanged. From 17:40 ET on, dark UV arrives as 0 |
| weewx-monitor | sha = `dev` tip, running since 2026-09-18 23:13 ET; carries the `REMEDY_SYSTEMCTL` fix + DEC-0199 |
| Reception | unchanged since DEC-0154's recovery; new-position comparison unmeasured (job 4) |
| `main`/`dev` | S141: DEC-0200 PR to `dev`. `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged |
| Trackers | repo: #394 open (job 3) · #380 open (marvin's pager, informational) · ops: #343 reopened `repo:weewx`, weewx closes it after HLF's confirm (job 2) · #265/#110 deferred-trigger, unfired · #306 residual (job 7) · #344 macOS LAN heads-up (worked around, MARVIN-DEC-0179) |

## Blockers

1. **weewx process freezes — rate confirmed 1.31/day median 240s (DEC-0088, reconfirmed DEC-0198
   S138); root cause/mechanism still unproven** (DEC-0068/DEC-0094). No active watch on the rate;
   re-derive only if a fresh elevated reading appears.
2. **RF-dead episode root cause unknown** (DEC-0081). First clean post-fix baseline read was taken
   at S126 (100% mean, no episodes yet); the watch continues.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

**The whole session ran on Opus 5.5, flagged at the start as fitting:** a design call (DEC-0200) plus
an attended prod config change. No `/model` switch was made in-session. **Desktop app:** the
model persists for later sessions, so the next *execution* session (e.g. job 1's verification
query) should switch back to Sonnet by hand.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). No new entries
this session.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-09-27 (S141). DEC-0200 (UV diode-floor two-code zero) designed from a
prod-archive measurement, owner-approved, and applied live at 17:39:57 ET with a clean restart.
DEC-0080 re-verified clean. `eaglehunt-ops#343` check-in posted and ops rung. The dark-hours
verification is job 1._
