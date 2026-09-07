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

## ▶ Resume here (S129 → S130)

### What's settled (do not re-derive)

**ops#257 is CLOSED. Limb 1 (the tenant-root git conversion) executed and verified live this
session — DEC-0150. Limbs 2/3 were already closed. ops#272's weewx row is now postable — see job 1.**

- **ops#257 limb 1 executed (DEC-0150).** `/srv/docker/weewx` is a real `dev` checkout, `origin` on
  the SSH deploy-key URL, `marvinctl --tenant weewx pull` verified working end-to-end (fast-forward
  succeeded, confirmed over the deploy-key path after fixing an origin that briefly landed on
  anonymous HTTPS). Mechanism was plain SFTP (`mkdir`/`rename`/`rmdir`/`get`/`put`) — the tenant's
  forced command has no shell/clone verb, discovered mid-session and confirmed against marvin's own
  `marvinctl-remote` source. `weewx-data/` turned out to be entirely untracked by git so it moved
  wholesale; `weewx_monitor.py` is tracked but its live SHA didn't match `dev`'s tip (a real,
  previously-invisible deploy gap) — restored the live copy rather than silently deploying
  unreviewed monitor code, kept `dev`'s copy as `weewx_monitor.py.dev-tip-not-deployed`. Outage ~9
  min (14:15:36–14:24:48 EDT 09-07). Container's cgroup placement corrected as a free side effect of
  the restart — **job 6 closed too.** Full account: `DECISIONS-FULL.md` DEC-0150.
- **`weewx_monitor.py`'s dev-tip-vs-deployed gap reconciled same session** (right after the swap,
  same S129 sitting). Diffed the two copies: the entire gap was comment/docstring text plus one
  email-summary string, correcting stale explanatory text to match issue #317's driver fix (already
  shipped in v2.0.16) — zero functional code change, safe to adopt. `weewx_monitor.py` now matches
  `dev`'s tip exactly (sha-verified), old deployed copy kept as
  `weewx_monitor.py.pre-reconcile-20260907` (not deleted), `weewx-monitor.service` restarted clean,
  `Remedy armed:` line confirmed post-restart.
- **Model tier: this session ran entirely on Sonnet, no escalation.** Nothing to restore.

### ▶▶ S130 JOB LIST

1. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix (issue #337) and install both unit
   changes in their next units gesture (queued, owner check-in pending on marvin's side as of S126
   close) — note this is the **unit file**, a separate artifact from `weewx_monitor.py` above.
4. Carry forward job 8's remaining untouched items (EnvironmentFile, `marvin-release.sh`)
   exactly as S126 left them — none are due, none are blocked on anything weewx can do alone.
5. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) for a maintainer reply** —
   repo's been dormant since 2023-12-22, don't chase it, just notice if it moves.
6. `CONSTANTS.md` infra re-verify (S105-era, still stale outside what S129 touched) ·
   `docs/ARCHITECTURE.md` mount table still NAS-pathed (S30) · `CHANGELOG.md` archive rollup
   overdue — S122 and earlier still inline, past the ~3-session guideline (pre-existing debt,
   carried again, one session closer).
7. **`ops/soak_check.sh` still NAS-hardwired**, same root cause ops#250/ops#286 were — not yet filed
   as its own tracker item (do that, or fold into ops#286, before picking it up). `campaign_analyze.py`'s
   port (S127, PR #360) is the template: two clean `marvinctl` calls replaced a whole ssh round-trip;
   `soak_check.sh` is shaped differently (a dozen live checks, remote awk log-windowing) and will
   need its own design pass, not a copy.
8. **Now that a real `dev` checkout exists on marvin, revisit whether `ops/soak_check.sh` and other
   still-NAS/ssh-hardwired tooling could instead run via `marvinctl exec-ro`** the way
   `campaign_analyze.py` (DEC-0148) does — worth a look before designing job 7's fix from scratch.

### Current state (S129 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` unit AND container both in `/weather.slice` now (job 6 closed this session); `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, `ExecStop=docker kill` (MARVIN-DEC-0137) — runs as `t-weewx` (996:986) via unit `--user` since 13:12:05 EDT 09-06 (DEC-0147). Restarted 14:24:48 EDT 09-07 as part of the ops#257 swap (DEC-0150) — same image, tree layout changed underneath it, not the image |
| Reception | unchanged this session — 100% mean through S126's last read (09-03 18:00 baseline); watch continues |
| InfluxDB | marvin, `weewx-influxdb.service` since 09-04 22:35:02 ET, v2.7.12; backup timer armed; untouched this session |
| Foundation | fully decommissioned — project directory deleted, NFS export retired, DSM tasks disabled (ops#278 closed) |
| `main`/`dev` | `dev` unchanged in content this session (docs-only commit pending, no feature branch code) — `/srv/docker/weewx` now tracks it directly; `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · self-service `push` LIVE (ops#265, unchanged, still closes on first real push) |
| GitHub Releases | v2.0.12–v2.0.16 backfilled, live (#331 closed, DEC-0145) |
| Git | S129: docs-only changes (PR #364 merged; the `weewx_monitor.py` reconciliation is a prod-tree action, no repo code) |
| Tenant tree | **Real `git` checkout as of S129** — `/srv/docker/weewx` on `dev`, `origin` = SSH deploy-key URL, `marvinctl --tenant weewx pull` self-service and verified. Pre-swap tree preserved intact at `/srv/docker/weewx/live-aside-20260907/` (not deleted) |
| Trackers | repo: none open · ops: **#257 CLOSED S129 (DEC-0150)**; #272 weewx row posted S129 (staleness gate → yes); #250/#278/#275/#273/#264/#218 closed prior sessions; #286 (freeze_baseline.py) open · #110/#265/#274 (EnvironmentFile + marvin-release.sh only) open, correctly gated/deferred |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

**Floor confirmed restored, no action needed.** S129 ran entirely on Sonnet, no `/model` switch.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3, now covers `marvin-<tenant>` SSH's missing shell/clone verb — S129) ·
judging a component live, dead, or shipped (§4). No new traps found beyond that one this session.

_Last updated: 2026-09-07 (S129, ~15:15 ET). Session summary: executed and verified ops#257 limb 1
live (DEC-0150) — the tenant-root git-conversion plan DEC-0149 agreed but hadn't run. Coordinated
with live ops and marvin sessions before touching prod; marvin confirmed clear (no marvin-side write
queued into the tenant tree) and answered the bootstrap-clone mechanics question with real code, not
a guess. Discovered mid-session that the planned ssh-shell-script mechanism doesn't exist on this
alias and switched to plain SFTP, generated from a live directory listing rather than hand-typed.
Found and handled one landmine DEC-0149 hadn't named (`weewx_monitor.py`'s live/dev-tip SHA
mismatch) after systematically SHA-checking every git-tracked root file against live, not just the
ones already suspected. Verified `pull` end-to-end after fixing an origin that briefly landed on
plain HTTPS. Outage ran longer than estimated (~9 min) — verification happened with the service
already down rather than staged first; worth doing more dry-run prep before the next live-service
cutover. `docs/GOTCHAS.md` §3 got the new ssh-forced-command entry. **After PR #364 merged, the
owner asked directly for the `weewx_monitor.py` reconciliation this same session** — diffed the two
copies (comment/docstring text + one email-summary string correcting stale #317 wording, zero
functional change), adopted `dev`'s tip, restarted `weewx-monitor.service`, sha- and
`Remedy armed:`-verified. Old deployed copy kept as `weewx_monitor.py.pre-reconcile-20260907`._
