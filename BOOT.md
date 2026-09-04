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

## ▶ Resume here (S122 → S123)

### What's settled (do not re-derive)

**The DEC-0134→0139 chain is complete: both `rxCheckPercent` distortions found, fixed, deployed,
confirmed.** Repeat-packet dedup (`v2.0.15`, DEC-0134→0136) and the slot-count denominator
(`v2.0.16`, DEC-0137→0139) each independently inflated the metric; both are gone. `v2.0.16` running
on marvin since 2026-09-03 20:29:06 EDT, no CRITICAL since restart, gain 372 holds, driver banner
`0.20+ws.5`. First fully-post-cutover monitor window: **0/360 records over 100%**, down from the
pre-fix 197/360 (55%) — **#317 closed** (DEC-0139). `docs/DATA_ERRATA.md`'s `DISC-0001` carries both
boundaries. Campaigns A-D remain *untested*, not re-run (no reason to — see `docs/ROADMAP.md` P2).

**`v2.0.16` promoted to `main`, tagged `prod-baseline-20260904`** (PR #324, 267 commits S75->S122).
`main`/`dev` are in sync. Docker Hub is still `:v2.0.13` (two releases behind) — no self-service
publish path since the marvin move; filed as
[ops#265](https://github.com/WeatheredScientist/eaglehunt-ops/issues/265).

**S122's own public-release audit (ahead of the promotion) found two more items, both filed:**
README had drifted three releases stale — **fixed same session** (PR #325); this file itself was
found over its 2,500-token cap — [ops#264](https://github.com/WeatheredScientist/eaglehunt-ops/issues/264),
not yet acted on (this rewrite is the first pass at trimming it).

**S122 shipped all of that but never ran its own closeout** (ops#218, third recurrence — see S120)
— repaired at S123's start: CHANGELOG `[S122]` entry, this pointer, `docs/ROADMAP.md`'s P2
reconciliation line. S122 does not get a done-marker.

**The per-transmitter-ID loop period is verified:** `(41 + id)/16` s, id 4 = DIP ID 5, mean
2.8124 s/slot (S115/S119, #313) — background fact, not an open question.

**The monitor deploy path (S119):** file transport is owner-run (tenant key is forced-command);
restart is self-service `marvinctl --tenant weewx restart weewx-monitor.service`; unit edits are
owner-run. Verify by sha, start-after-mtime, `Remedy armed:` line. **#316** (unquoted
`REMEDY_SYSTEMCTL`) fixed live since Aug 30 16:20 ET — still untested end-to-end (no stall since).

**Also settled:** ops#256 closed empty (dashboard has no reception consumer). Repo #253/#216 fixed
S118. Marvin releases need **two** separate Class C confirmations, not one — `docs/GOTCHAS.md` §3.

### ▶▶ S123 JOB LIST

1. **Trim `BOOT.md` under its 2,500-token cap** (ops#264) — this rewrite; verify the count after.
2. **ops#265 — Docker Hub self-service publish from marvin.** No `git_branch`/`.git` in the tenant
   root (ops#257, same root cause); read both before designing a path. Hub push is otherwise the
   only thing left on the `v2.0.16` release.
3. **ops#257 limb 2 — `EnvironmentFile` with `IMAGE=`.** MARVIN-DEC-0109 approved the property;
   read ops#257 for what marvin now allows before building.
4. **Retire the campaign residue** — `weewx-rx-experiment.timer` (self-service `marvinctl disable
   --now`) and the `campaign.inhibit` lifecycle at `ops/weewx-monitor.service:88` that no code
   implements. Fix the comment or implement it; not both.
5. **Fix `ExecStop=docker stop` in `weewx.service`** (DEC-0008) — owner root-edit path.
6. **Upstream issue/PR to `lheijst/rtldavis`** — draft in `docs/upstream/`, owner tone review,
   never posted without a go.
7. **#314** — `campaign_analyze.py`'s `rx > 100` backstop excludes good minutes (cheap, low).
8. **#320** — `CHANGES-FROM-UPSTREAM.md`'s Go-decoder row says "unmodified"; stale since the
   dupgate patch (DEC-0135). Cheap, mechanical doc fix.
9. **Post-fix baseline watch** — RF-dead episodes (blocker 2) are measurable now; observation only.
10. **Audit Phase 2** sessions A (Sonnet, mechanical), B (judgment), C (design, owner) — unchanged.
11. `campaign_analyze.py` port to marvin (ops#250) · durable logrotate for marvin `logs/` ·
    ops#260 (Foundation decoupling umbrella, frontier) · ops#110 (frontier, 2027 build).

**Carried forward, untouched:** NAS-LEASE cross-host wiring (low) · `CONSTANTS.md` infra re-verify.

### Current state (S122 close, repaired by S123)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` — two-tenant box |
| Prod | **`v2.0.16`**, driver ws.5 + dupgate + slot-count denominator, weewx 5.5.0, gain 372. Since 09-03 20:29:06 ET (DEC-0138) |
| `main` | promoted, tag `prod-baseline-20260904` (PR #324) — in sync with `dev` |
| Docker Hub | `:v2.0.13` — job 2 (ops#265), two releases behind |
| Monitor | dev tip `bd499d3`'s file (sha `147f3eff...`); `REMEDY_MODE=restart_unit` armed and executable |
| Git | PRs #322 (build/deploy), #323 (#317 close, DEC-0139), #324 (main promotion), #325 (README) merged to `dev` |
| Open risks | the 6-hourly email was thought broken (Gmail 535) and arrived 09-03; cause of recovery unknown, not ours to chase |
| Trackers | repo **#314**, **#320** (both cheap) open · ops **#264**, **#265** (new), #257 (limb 2), #250, #110, #260 open · repo #317, #313, #316, #253, #216 closed; ops#256, #233 closed |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open) — measurable post-DEC-0136.
   Job 9.
3. **ERR-0005** — unchanged.
4. ~~6-hourly reception-summary email~~ — arriving again as of 09-03; watch, don't chase.

## Model tier

S119 ran on **Fable** (judgment work). S120-S122 ran on **Sonnet** — execution of an already-settled
design throughout, no judgment call needed. S123's job list (BOOT trim, doc fixes, self-service
tooling design for ops#265/#257) is likewise mechanical-to-mid — **Sonnet**, escalate only if
ops#265's design turns out to need a real architectural call. Desktop switches persist
(OPS-DEC-0036/0062): state the running model in the first reply.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). **New traps are appended THERE.**

_Last updated: 2026-09-04 (S123, repairing S122's undone closeout). Session summary: opened on a
closeout-debt hook (ops#218, third recurrence) — S122 had closed #317 with metric confirmation
(PR #323, DEC-0139), promoted `v2.0.16` to `main` and tagged `prod-baseline-20260904` (PR #324),
and refreshed the stale README (PR #325), but never ran BOOT/CHANGELOG/DEC or a session title.
Repaired that first: CHANGELOG `[S122]` entry, `docs/ROADMAP.md`'s P2 reconciliation line, this
pointer trimmed toward ops#264's cap. Then continues into the S123 job list above._
