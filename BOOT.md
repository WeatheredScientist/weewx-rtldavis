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

## ▶ Resume here (S125 → S126)

### What's settled (do not re-derive)

**InfluxDB stage 3 (ops#270) essentially closed.** Backfill: 28 records posted, not 29 —
22:40–22:42 don't exist in SQLite either ([ERR-0007](docs/DATA_ERRATA.md)), verified via `influx
query`. `SuccessExitStatus=2` confirmed live. `weewx-influxdb-backup.service`/`.timer` installed by
marvin and armed self-service — first fire **2026-09-06 03:15:00 EDT**. NAS-LEASE `BACKLOG.md` item
closed. Only two pieces remain, neither weewx's action: (c) owner deletes the two token-bearing tars
from the marvin-data share; (e) ops/dashboard's own doc rows.

**Foundation-dark drill (ops#260 item E) run and closed clean, weewx's slice.** First attempt
(11:26–11:31) voided — marvin could still reach Foundation through a partial UniFi block; true T0
11:52, cable physically out, restored 12:24. Three rounds of §5.6 probes, all green: Influx health
200, `weewx-influxdb.service` active with **no restart** across the whole outage, archive cadence
unbroken at 1-minute records straight through, zero NAS reference in `weewx.conf` at any point.

**DEC-0143 (closeout ritual step 0, OPS-DEC-0195) and DEC-0144 (secret gate gains a general
private-IP/subnet detector) both shipped** (PR #339, #340 → `dev`). Two process slips found and
repaired the same session: PR #338 landed on `main` instead of `dev` (repaired via #339); DEC-0143's
own insertion split DEC-0142's body in `DECISIONS-FULL.md` (repaired same session). `SECURITY.md`
carries a second history-rewrite notice.

**Closed this session:** ops#275 (owner accepts the DEC-0144 residual) · ops#273 (CWOP verification
never reads back through APRS-IS) · ops#257 limb 2 (`:marvin-live` self-service tag confirmed live —
limbs 1/3 stay open, not weewx's to close) · ops#278 part 1 (marvin's `weewx-rx-experiment.timer`
was still firing every 10 min, stale campaign residue — disabled) · ops#218 (closed on ops's side,
OPS-DEC-0195).

**ops#274 (marvin self-service prompt audit)** independently converged with ops's own S39 sweep on
"the seven relaxations are already shipped." One live finding folds into job 3 below. Its proposed
weewx-specific relaxations (items 8–12) are backlog, not actioned — carried forward.

**Also settled:** ops#265 wired (next release self-service via `marvinctl push`, closes on first
real push) · monitor deploy path (S119) · loop period `(41 + id)/16` s (#313) · #320/#314 closed
S123 (DEC-0140) · #327 filed.

### ▶▶ S126 JOB LIST

1. **ROADMAP tripwire fires this session** — `docs/ROADMAP.md`'s own trigger (S126). Run the full
   reconciliation pass regardless of what else lands.
2. **#331 — GitHub Releases backfill** v2.0.12–16 + write the step into CONVENTIONS/closeout. Owner
   go per step (public).
3. **Bundle into one owner root-edit gesture (ops#274's own suggestion — Sonnet, mechanical):**
   `ExecStop=docker stop` → `docker kill` in `weewx.service` (DEC-0008) **+** `weewx-monitor.service:82`'s
   `REMEDY_SYSTEMCTL=sudo systemctl` → `sudo -n /usr/local/lib/marvin/marvin-own weewx restart`
   (ops#274: the armed remedy currently cannot run — `t-weewx`'s sudoers grants `marvin-own weewx
   <verb> <target>` only, not bare `sudo systemctl`; untested end-to-end, verify with a deliberate
   test after the fix). **#327 — GPLv3 §5(a) notice** in the dupgate `main.go` rides the same image
   cut if one happens to land here.
4. **ops#278 parts 2/3 — Sonnet, mechanical.** Foundation is reachable again: compare NAS-side vs
   marvin-side `rx_experiment.state`/log mtimes since the 09-02 decommission (did the duplicate DSM
   runner touch campaign state before the owner disabled it?), then retire the DSM path from
   `CAMPAIGN-B-RUNBOOK` and any other doc still describing it.
5. **Upstream issue/PR to `lheijst/rtldavis`** — draft in `docs/upstream/`, owner tone review first.
6. **Post-fix baseline watch** — RF-dead episodes (blocker 2), observation only.
7. Audit Phase 2 A/B/C · `campaign_analyze.py` port (ops#250, owner decided S125: port not retire,
   no date) · logrotate for marvin `logs/` · ops#110.
8. **Backlog, lower priority — ops#274 items 8–12, not yet actioned:** tenant-owned
   `EnvironmentFile` for the monitor's non-root knobs; `weewx.service` running as `t-weewx` instead
   of root (needs a `weewx.sdb` permission fix first, **~30s live hot-swap outage — agree the
   approach before touching prod, DEC-0011; judgment work, escalate**); a tracked
   `marvin-release.sh`; `docs/GOTCHAS.md` §3's "two Class C gates per release" line is now partly
   superseded by OPS-DEC-0193 (rsync advisory-allow) — needs a pass.

**Carried forward:** `CONSTANTS.md` infra re-verify (S105-era, still stale) · `docs/ARCHITECTURE.md`
mount table still NAS-pathed (S30) · `CHANGELOG.md` archive rollup overdue — S122 and earlier still
inline, past the ~3-session guideline (pre-existing debt, not new this session).

### Current state (S125 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` in `/weather.slice`; **`v2.0.16`** as `:marvin-live`, weewx 5.5.0, gain 372, unbroken since 09-04 22:40:42 ET — survived the Foundation-dark drill with zero restart |
| InfluxDB | **marvin**, `weewx-influxdb.service` since 09-04 22:35:02 ET, v2.7.12; backfilled (28 records, ERR-0007 — 22:40–22:42 permanently absent, not a hole to fill); `weewx-influxdb-backup.timer` armed, first fire 09-06 03:15 EDT |
| Foundation | dark 11:26 AM–12:24 PM ET for the drill, restored; no weather workload; stopped `influxdb` retained as rollback until ops#260 step 4 |
| `main`/`dev` | in sync — both carry DEC-0143 + DEC-0144 |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · self-service `push` LIVE (ops#265, closes on first real push) |
| GitHub Releases | dead since v2.0.11 — #331 |
| Git | S125: PR #336 (backfill+backup timer), #339 (dev/main parity), #340 (DEC-0144) → `dev` |
| Trackers | repo #327, #331 open · ops #270 ((c)/(e) only) · #257 (limbs 1/3 open, limb 2 closed) · #250, #110, #278 (parts 2/3) open · #273/#274/#275/#264/#218 closed S125 · #279 filed |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081) — measurable post-DEC-0136; job 6.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email arriving again since 09-03; watch, don't chase.

## Model tier

S125 ran entirely on Sonnet, no bare `/model` switch — nothing to restore. S126's queue is mostly
Sonnet-mechanical (release backfill, doc edits, NAS-state comparison, owner-gated unit edits). One
exception: job 8's `weewx.service`-as-`t-weewx` change carries a live-hot-swap outage risk on the
single receiver — treat that specific decision as judgment work (escalate, DEC-0011) even though
the rest of the queue is routine.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). S124's four traps
landed in GOTCHAS this session (§1 ×2, §4 ×2) — nothing left to move.

_Last updated: 2026-09-05 (S125 close, ~12:35 ET). Session summary: closed out InfluxDB stage 3
(backfill, unit fix, backup timer); adopted and shipped two process/security decisions (DEC-0143
closeout-ritual step 0, DEC-0144 secret-gate hardening) — both triggered by, and this session found
a live instance of, "how does this keep happening" (a raw marvin IP posted to a GitHub comment
mid-session); ran and closed weewx's slice of the Foundation-dark drill clean; closed five ops
issues; caught and repaired two of its own process mistakes (a misrouted PR base branch, a
DECISIONS-FULL.md structural slip) rather than leaving them for the next session to find._
