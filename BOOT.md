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

## ▶ Resume here (S121 → S122)

### What's settled (do not re-derive)

**The ~25% "loss" was the demodulator's duplicate filter — solved, fixed, deployed, confirmed
(DEC-0134 → 0135 → 0136).** `v2.0.15` since 2026-09-03 07:17:53 EDT; `missed` 81 → 0. 27.2% of
transmissions are the ISS's verbatim re-sends — S119 added an independent check: wind bytes changed
in 33 of 213 different-type consecutive pairs and **0 of 80** same-type pairs, a copy, not a
coincidence. It unbiased a statistic; the data was always correct. Gain 372 holds. Campaigns A–D
are *untested* and not re-run.

**#317's fix is built, deployed, and running — `v2.0.16` since 2026-09-03 20:29:06 EDT (DEC-0137 →
DEC-0138).** `rxCheckPercent` now denominates by `round((last − prev) / loop_time)` — the ISS's own
inter-arrival clock per transmitter — instead of `floor(wall-clock period / loop period)`, so
`count <= max_count` holds by construction and PR #315's clamp (S119) should stop firing rather than
just hide the over-count. Pre-fix scale measured directly: 197/360 records (55%) over 100% in the
12:00–18:00 window. Cutover outage **31 s** (same-host recreate); artifact verified directly
(`grep -n last_pkt_ts` in the built image) before the unit-file flip, not from the build pipeline's
exit. Driver banner unchanged `0.20+ws.5`; no CRITICAL since restart. **#317 stays open** — deploy-
verified, not yet metric-verified; close it once the 18:00/00:00 ET monitor email shows the 55%
baseline reading ~0%, then write `DISC-0001`'s second boundary in `docs/DATA_ERRATA.md`.

**Two Class C gates per marvin release, not one** (`docs/GOTCHAS.md` §3, S121) — the tarball `scp`
and the `sudo tar` extraction into the `t-weewx`-owned tenant root are separately guarded; the
extraction needs the owner's own hands (interactive sudo password, no passwordless path since
MARVIN-DEC-0105), not a mint. Budget for two owner confirmations per build until `ops#257` closes.

**S120 shipped #317's code but never ran its own closeout** (ops#218) — repaired at S121's start:
BOOT pointer, CHANGELOG `[S120]` entry, DEC-0137 (PR #321). S120 does not get a done-marker.

**The per-transmitter-ID loop period is verified, not inherited (S119, #313).** `(41 + id) / 16` s
for packet id 0..7 = DIP ID 1..8 = 2.5625..3.0 s. Davis's own VP2 spec sheet (DS6152: every sensor
update interval is N × 2.5–3.0 s), DeKay's RF-Protocol notes, `lheijst/rtldavis` `idLoopPeriods`,
and our S115 capture (292 single-slot gaps, mean **2.8124 s, sd 1.0 ms**; span / 2.8125 = 294.00 =
transmissions seen) agree. This ISS is packet id 4 = **DIP ID 5** (`-tr 16` is "tr5"); the
monitor's "Transmitter 4" is the zero-based id. A period difference, not a phase offset. The
Vantage Vue sheet is a sibling product's document, not a source here (owner correction).

**`rxCheckPercent` > 100% is the driver's denominator, not the radio (#313 → #317).**
`max_count = period // 2.8125` floors 21.33 to 21, and a 59 s `int(time.time())` period to 20, so a
fully received minute reads 101–105% (~103% mean). Reporting fix **live** since 16:11 ET: the
monitor clamps each record at 100, labels `dropped` a lower bound, and counts clamped records
(PR #315). Root-cause fix is **#317** (job 1): denominate by ISS slots between received packets,
`round(Δt / loop_time)` — a full minute reads exactly 100 and > 100 becomes impossible.

**Three denominators measure three things (DEC-0136):** `hops = accepted + missed + init`; slot
arithmetic (~100% steady-state); the monitor's `WINDOW` (`len(set(epochs))`, saturating,
insensitive — `WU_RF_MIN_PCT = 60` stays valid).

**The monitor deploy path is known (S119) — see `CONSTANTS.md` deploy layers.** File transport is
**owner-run** (the tenant key is forced-command); restart is self-service `marvinctl --tenant weewx
restart weewx-monitor.service`; unit edits are owner-run. Verify by sha, start-after-mtime, and the
`Remedy armed:` startup line. **S118's monitor change (#312) had never been transported** — closed
on merge, not on deploy — until S119's deploy carried it.

**#316 fixed live.** The unit's unquoted `REMEDY_SYSTEMCTL=sudo systemctl` had made the armed
remedy `sudo restart weewx.service` since Aug 30 (systemd drops the second token, journal-only
warning). Quoted in-repo and on marvin; the startup line reads `sudo systemctl restart
weewx.service` since 16:20 ET. Still untested end-to-end (no stall since).

**Also settled:** ops#256 closed empty — the dashboard has no reception consumer, HLF only
inventories the field. `ops/soak_check.sh` still targets `NAS_HOST` (unverified since DEC-0118).
Repo #253 and #216 were fixed in S118; close them once the owner confirms.

### ▶▶ S122 JOB LIST

1. **Close #317.** `v2.0.16` is built, deployed, and running (DEC-0138, 31 s cutover, 2026-09-03
   20:29:06 EDT) — code and deploy are done. Only remaining: confirm the 18:00/00:00 ET monitor
   email shows the pre-fix 55%-over-100% baseline reading ~0% (`marvinctl --tenant weewx tail
   /srv/docker/weewx/logs/weewx_monitor.log N`) → close #317 with that number → `DISC-0001`'s second
   boundary in `docs/DATA_ERRATA.md` (a metric-definition step change, same treatment DEC-0135's
   ~73%→~99% got).
2. **Post-fix baseline watch** — RF-dead episodes (blocker 2) are measurable now; observation only.
3. **`v2.0.16` promotion to `main` + Docker Hub** (DEC-0078; Hub is at `:v2.0.13`, now two releases
   behind). Tag a new `prod-baseline-YYYYMMDD` once #317 closes and the metric is confirmed.
4. **ops#257 limb 2 — `EnvironmentFile` with `IMAGE=`.** MARVIN-DEC-0109 approved the property;
   read ops#257 for what marvin now allows before building.
5. **Retire the campaign residue** — `weewx-rx-experiment.timer` (self-service `marvinctl disable
   --now`) and the `campaign.inhibit` lifecycle at `ops/weewx-monitor.service:88` that no code
   implements. Fix the comment or implement it; not both.
6. **Fix `ExecStop=docker stop` in `weewx.service`** (DEC-0008) — owner root-edit path, same
   sitting as any other unit change.
7. **Upstream issue/PR to `lheijst/rtldavis`** — draft in `docs/upstream/`, owner tone review,
   never posted without a go.
8. **#314** — `campaign_analyze.py`'s `rx > 100` backstop excludes good minutes (low; moot once
   #317 ships).
9. **#320 (new, filed 2026-09-03 22:51 ET)** — `CHANGES-FROM-UPSTREAM.md`'s Go-decoder row says
   "unmodified" but the Dockerfile has carried the dupgate patch to `main.go` since DEC-0135; the
   GPLv3 §5(a) divergence inventory is stale. Cheap, mechanical doc fix.
10. **Audit Phase 2** sessions A (Sonnet, mechanical), B (judgment), C (design, owner) — unchanged.
11. `campaign_analyze.py` port to marvin (ops#250) · durable logrotate for marvin `logs/`.

**Carried forward, untouched:** NAS-LEASE cross-host wiring (low) · `CONSTANTS.md` infra re-verify
(S119 corrected the prod-image row and added the monitor row; the rest is unverified) · ops
CONSTANTS §5 register row check (`ef8e9af8`) · GitHub Support purge ticket.

### Current state (S121 close)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` — two-tenant box |
| Prod | **`v2.0.16`**, driver ws.5 + dupgate + slot-count denominator, weewx 5.5.0, gain 372. Since 09-03 20:29:06 ET (DEC-0138), 31 s cutover |
| Docker Hub | `:v2.0.13` — job 3, now two releases behind |
| Monitor | dev tip `bd499d3`'s file (sha `147f3eff…`), running since 16:20:49 ET; `REMEDY_MODE=restart_unit` armed and executable |
| Git | PR #319 (S120 code) + PR #321 (closeout repair + DEC-0137/0138) merged to `dev`@`73acc3d` |
| Open risks | the 6-hourly email was thought broken (Gmail 535) and arrived 09-03; cause of the recovery unknown, not ours to chase |
| Trackers | repo **#317** (mid, deploy-verified/metric-verification pending), **#314** (cheap), **#320** (cheap) open · ops#257 (limb 2), #250, #110, #260 open · repo #313, #316 closed; ops#256, #233 closed |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open) — measurable post-DEC-0136.
   Job 2.
3. **ERR-0005** — unchanged.
4. ~~6-hourly reception-summary email~~ — arriving again as of 09-03; watch, don't chase.

## Model tier

S119 ran on **Fable** (owner's desktop session; the interval question was judgment work). S120 and
S121 both ran on **Sonnet** — implementation, closeout repair, and the v2.0.16 build/deploy were all
execution of an already-settled design, no judgment call needed. S122's job 1 (confirm the monitor
email, close #317) is equally mechanical — **Sonnet or Opus, not frontier**. Desktop switches
persist (OPS-DEC-0036/0062): state the running model in the first reply.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). **New traps are appended THERE.**

_Last updated: 2026-09-03 (S121 close). Session summary: opened on a closeout-debt hook (ops#218) —
S120 had shipped #317's fix (PR #319 → `e158741`) without running BOOT/CHANGELOG/DEC or a session
title. Repaired that first (DEC-0137, PR #321), then continued straight into the job list's
remainder: built `v2.0.16` self-service (`marvinctl build`), transported via the same one-off
owner-authorized path DEC-0136 used (two separate Class C gates found this time, not one —
`docs/GOTCHAS.md` §3), verified the artifact directly before touching prod, and cut prod over in
31 s (DEC-0138). #317 stays open pending the 18:00/00:00 ET monitor email's metric confirmation —
first job for S122. Gate clean throughout: ruff clean, 475 passed / 17 skipped, mypy clean (68
files), secret gate clean on every commit._
