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

## ▶ Resume here (S128 → S129)

### What's settled (do not re-derive)

**S127's own history (PR #360, campaign_analyze.py port) is prior history — see CHANGELOG/
DECISIONS, not repeated here. S128 did not touch prod: it decided, but did not execute, ops#257
limb 1's reconciliation shape.**

- **ops#257 limb 1 — reconciliation shape decided (DEC-0149), not yet executed.** marvin S29
  landed `git_branch=dev` + the deploy key (`MARVIN-DEC-0144`, owner-confirmed on GitHub) and
  researched HLF/dashboard/CoffeeRadar's onboarding precedent at weewx's request. Owner picked the
  **CoffeeRadar swap shape** over weewx's own originally-floated file-by-file diff-and-categorize
  plan: fresh `dev` clone in a `.git-recon/` scratch subdir inside our own tenant tree, live tree
  renamed aside intact (kept, not deleted), fresh clone dropped into place, documented landmine
  paths restored. No marvin gesture needed — all inside `/srv/docker/weewx`, `t-weewx`-owned.
  Marvin's own review then caught a hazard neither plan draft stated: `weewx.service` runs
  continuously through this (unlike HLF/dashboard's clean-tree onboardings), so the host loses path
  access mid-rename — **the service must be stopped for the whole swap window**, folded into
  DEC-0149 before anything ran. Landed as PR [#362](https://github.com/WeatheredScientist/weewx-rtldavis/pull/362),
  merged to `dev`. **The swap itself is next session's work — see job 1.**
- **Model tier: this session ran entirely on Sonnet, no escalation** — S126's "floor not yet
  restored" note is stale; the floor reads correctly restored (this session started and stayed on
  Sonnet). Nothing to restore.

### ▶▶ S129 JOB LIST

1. **ops#257 limb 1 — execute the swap (DEC-0149).** Plan is agreed, nothing executed yet. Steps,
   in order: **stop `weewx.service`**; build the fresh `dev` clone in
   `/srv/docker/weewx/.git-recon/`; rename the live tree aside intact (do not delete); drop the
   fresh clone into place; restore the documented landmine paths from the renamed-aside tree
   (`weewx.conf`, `weewx.conf.rx-baseline`, `archive/weewx.sdb`, `logs/`, the
   `loop_json_writer.py`/`ogoxeUploader.py` decoys in `weewx-data/bin/user/`, the
   `sortedcontainers/` vendor directory); restart `weewx.service`; verify `git status` clean; then
   **run a live `marvinctl --tenant weewx pull` test** (required, not optional — DEC-0149:
   CoffeeRadar's own `pull` was never confirmed end-to-end, only dashboard's is a proven
   precedent). Once `pull` is confirmed, update `docs/CONVENTIONS.md`'s release-mechanics section —
   it still documents the owner-run git-archive/scp/tar flow as current, which becomes wrong the
   moment this lands.
2. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix and install both unit changes in
   their next units gesture (queued, owner check-in pending on marvin's side as of S126 close).
3. Carry forward job 8's remaining untouched items (EnvironmentFile, `marvin-release.sh`)
   exactly as S126 left them — none are due, none are blocked on anything weewx can do alone.
4. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) for a maintainer reply** —
   repo's been dormant since 2023-12-22, don't chase it, just notice if it moves.
5. `CONSTANTS.md` infra re-verify (S105-era, still stale) · `docs/ARCHITECTURE.md` mount table still
   NAS-pathed (S30) · `CHANGELOG.md` archive rollup overdue — S122 and earlier still inline, past the
   ~3-session guideline (pre-existing debt, carried again).
6. **Container not actually in `weather.slice` yet (marvin S29, MARVIN-DEC-0141).** `Slice=` only
   placed systemd's docker-run launcher there; dockerd creates the real cgroup under
   `system.slice/docker-<id>.scope` without `--cgroup-parent`. Marvin added
   `--cgroup-parent=weather.slice` to `weewx.service`/`weewx-influxdb.service` and reloaded, but the
   currently-running container (S126's `--user` cutover) predates that and hasn't picked it up. No
   urgency — fold into the next natural restart of `weewx.service` (**job 1's swap restart is that
   trigger** — verify cgroup placement as part of the same restart, don't do it twice). Verify:
   `docker inspect --format '{{.State.Pid}}' weewx-rtldavis-v2` then `cat /proc/<pid>/cgroup` should
   show `weather.slice`, not `system.slice/docker-….scope`.
7. **`ops/soak_check.sh` still NAS-hardwired**, same root cause ops#250/ops#286 were — not yet filed
   as its own tracker item (do that, or fold into ops#286, before picking it up). `ops/freeze_baseline.py`
   is now tracked at ops#286. `campaign_analyze.py`'s port (S127, PR #360, merged) is the template: two
   clean `marvinctl` calls replaced a whole ssh round-trip; `soak_check.sh` is shaped differently (a
   dozen live checks, remote awk log-windowing) and will need its own design pass, not a copy.

### Current state (S128 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` unit in `/weather.slice`, but the **container's actual cgroup is not** — needs one more restart to pick up `--cgroup-parent` (job 6, MARVIN-DEC-0141; job 1's swap restart is the natural trigger); `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, `ExecStop=docker kill` (MARVIN-DEC-0137) — runs as `t-weewx` (996:986) via unit `--user` since 13:12:05 EDT 09-06 (DEC-0147). **Untouched this session** — DEC-0149 is a plan, not an execution |
| Reception | **100% mean, every post-v2.0.16 6h window since 09-03 18:00** (S126 job 6) — RF question reads closed; blocker 2 (RF-dead) unfired, watch continues |
| InfluxDB | marvin, `weewx-influxdb.service` since 09-04 22:35:02 ET, v2.7.12; backup timer armed |
| Foundation | fully decommissioned — project directory deleted, NFS export retired, DSM tasks disabled (ops#278 closed) |
| `main`/`dev` | `dev` carries all of S127 + PR #362 (S128, DEC-0149); `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · self-service `push` LIVE (ops#265, unchanged, still closes on first real push) |
| GitHub Releases | **v2.0.12–v2.0.16 backfilled, live** (#331 closed, DEC-0145) |
| Git | S128: PR #362 merged → `dev` (`s128-ops257-limb1-recon-plan`, deleted both sides). No other local branches or worktrees left over |
| Trackers | repo: none open · ops: **#257 limb 1 recon shape decided (DEC-0149), execution pending — job 1** (limbs 2/3 already closed); #250 closed S127 (DEC-0148), #286 filed S127 (freeze_baseline.py); #272 weewx-half unchanged since S127 · #110/#265/#274 (EnvironmentFile + marvin-release.sh only) open, correctly gated/deferred · #278/#275/#273/#264/#218 closed prior sessions |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

**Floor confirmed restored, no action needed.** S128 ran entirely on Sonnet, no `/model` switch —
S126's Fable escalation (desktop, persists — OPS-DEC-0036/0062) has been reverted by the time this
session started.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). No new traps found
this session.

_Last updated: 2026-09-07 (S128, ~09:40 ET). Session summary: opened checking in with the live ops
session on ops#257, per the ops-loop SOP. marvin S29 came back with precedent research on the tenant
git-checkout conversion (limb 1) — HLF/dashboard were clean fresh clones, no precedent value;
CoffeeRadar's comparable mess was fixed with a clean rename-aside-and-swap, not a file-by-file diff.
Owner picked the swap shape (DEC-0149), which also resolved the scratch-dir access question for
free (inside our own tenant tree, no marvin gesture) and carries forward a required live `pull`
verification (CoffeeRadar's own was never confirmed working). Marvin's own review then caught a
hazard neither draft had stated — `weewx.service` must be stopped for the swap window since it runs
continuously, unlike the clean-tree onboardings — folded into the decision before anything touched
prod. Landed as PR #362 (green gate, squash-merged, `dev` fast-forwarded). No code or prod-tree
change this session — planning only; the swap itself is S129's job 1._
