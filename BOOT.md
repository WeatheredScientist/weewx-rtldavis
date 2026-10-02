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

## ▶ Resume here (S149 → S150)

### What's settled (do not re-derive)

**v2.0.19 has run in prod since 2026-10-02 00:18:38 ET (DEC-0208): weewx 5.5.0 → 5.5.2, nothing
else changed** (the Go binary and the five baked modules are sha-identical to v2.0.18). The
rapidfire thread's move to `rtupdate.wunderground.com` is confirmed: the station's public WU page
read CONNECTED, 2 seconds old, after the restart (that thread's failures never reach the log).
Tagged `v2.0.19` on `fee78e3` with a GitHub release, and on Docker Hub as `:v2.0.19` (the first
real `marvinctl push`, 00:31 ET, digest equal to prod's).
v2.0.18's content (DEC-0205's slot-count seed fix, banner `0.20+ws.6`, and OWM and Windy rain in
millimeters) rides underneath. The monitor's #413 has run since 2026-09-29 09:31:16 ET.

**#423's swap path is proved end to end as `t-weewx` (S148).** A test-only schedule (arm `T` =
prod's cmd plus an explicit `-ex 0`, then `BASELINE`) ran on 2026-10-01 via two hand-started passes
of `weewx-rx-experiment.service`: the `marvin-own` restart, the `systemctl is-active` health check,
the byte-exact restore, harvest and mail all worked. The schedule is stood down again; arm `T` stays
in `arm_cmd` for the next path test. The timer is still not installed (campaigns stood down).

**`eaglehunt-ops#360` is done on weewx's side.** Both units run with `--cap-drop ALL` and
`no-new-privileges` (`weewx-influxdb` S147, `weewx.service` 2026-10-01 21:04:30 ET, the swap test's
first restart). heartofgold confirmed on the box.

**The S145 audit's ten high items are fixed and shipped;** 29 medium/low stay in
`docs/CODE_REVIEW_S145.md`, the secret gate's four holes are #421. ROADMAP next check: S156.

### ▶▶ S150 JOB LIST

1. **`eaglehunt-ops#357`, `bar_absolute`: the design needs the owner's call and a Fable 5.1
   session** (a cross-repo contract change). The tracker reply gives (A) feed `bar_absolute` in as
   weewx's own `pressure`, or (B) a new field. The dashboard answered that it reads neither
   `pressure_inHg` nor `altimeter_inHg`, so (A) costs it nothing. **HLF has not answered** (which of
   the two does it read?). First step of any build: one WeatherLink fetch to confirm this station's
   response carries `bar_absolute`, credentials never printed. Fix `pressure_service.py`'s stale
   "archive columns go NULL" comment in the same change; it is baked, so it rides a release.
2. **`:latest` on Docker Hub still points at v2.0.13** (the owner's gesture, DEC-0078's route, not
   `marvinctl push`). `:v2.0.19` is on Hub since S149; the question is whether to move it.
3. **`dev` → `main` promotion**, the owner's timing. `main` is v2.0.13; v2.0.14 to v2.0.19 have run
   unpromoted.
4. **Watches, no action:** WU still showing the station over the next days (the rapidfire
   endpoint) · OWM and Windy rain in millimeters (needs rain; ERR-0010) · the first
   `frame failed message-type proof` line · freeze lead (blocker 1), measure at the next freeze.
5. **Owner-only:** `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the shell profile, never CI; the
   remainder of `eaglehunt-ops#358`.
6. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry.

## Current state (S149 close)

| Thing | State |
|---|---|
| Prod | marvin, **`v2.0.19`** as `:marvin-live` (image `e1828402…`) since 2026-10-02 00:18:38 ET, weewx 5.5.2, gain 372, `t-weewx` (996:986), under #360's flags. `:v2.0.18` is local for rollback (retag + restart) |
| InfluxDB | marvin, `weewx-influxdb.service`, under #360's flags since S147 |
| weewx-monitor | sha `5cd09917…`, running since 2026-09-29 09:31:16 ET; `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| Campaign harness | schedule empty (stand-down), state `BASELINE`, timer not installed; tenant-root snapshot = live conf (`cea58bc9…`) |
| `main`/`dev` | `dev` = this closeout's merge. `main` is still v2.0.13, unpromoted (job 3) |
| Docker Hub | `:v2.0.19` (= prod, pushed S149) · `:v2.0.16` · `:latest` = v2.0.13 · v2.0.17 and v2.0.18 never pushed. `eaglehunt-ops#265`'s trigger has fired (S149 comment) |
| Trackers | repo: #421 (gate holes), #423 closed with the S148 evidence, #380 informational · ops: #357 awaiting the owner and HLF (job 1) · #360 weewx done · #358 owner remainder · #265/#110 deferred-trigger · #306 residual · #344 macOS LAN (this desktop session reached marvin) |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

**S149 ran on Sonnet 5.5**, no switch. **Start S150 on Sonnet** unless job 1 (`#357`, Fable 5.1) is
the session's work.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after.** **New this session:**
- §3: `marvinctl grep` also refuses `/` in a pattern (same misleading whitespace message).
- A schedule PR carries dated rows: if it sits unmerged past its terminator, a merge would jump
  straight to `BASELINE`. Re-date before merging (S148 did).

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-10-02 (S149). v2.0.19 (weewx 5.5.2) in prod. Job 1 (`#357`) is the next real
design work._
