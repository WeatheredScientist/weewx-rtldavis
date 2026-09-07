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

## ▶ Resume here (S127 → S128)

### What's settled (do not re-derive)

**S126's eight-item job list is prior history (see CHANGELOG/DECISIONS for detail, not repeated
here). S127 opened one PR, not yet merged: #360, `ops/campaign_analyze.py` ported to marvin.**

- **ops#250 closed, PR [#360](https://github.com/WeatheredScientist/weewx-rtldavis/pull/360) open,
  awaiting merge (DEC-0148).** `campaign_analyze.py`'s `fetch()` moved off NAS-ssh onto `marvinctl
  --tenant weewx cat`/`exec-ro` (query on stdin, never `-c` argv — DEC-0124). Image tag now resolved
  at runtime, not hardcoded. **New finding, not previously documented:** `exec-ro` mounts the tenant
  root read-only at its own HOST path (`/srv/docker/weewx/...`), not the live container's
  in-container path (`/opt/weewx-data/...`, which doesn't exist inside `exec-ro` at all) — verified
  via `mount` inside it. Decoupled `ops/freeze_baseline.py` from `campaign_analyze`'s constants after
  the port silently broke it (caught by mypy, not inspection) — that script and `ops/soak_check.sh`
  both stay unported, same NAS-ssh shape, deliberately out of this PR's scope. **Verified against
  live data, not just "it ran"**: reproduces Campaign C's and Campaign D's historical arm means to
  the decimal. Green gate clean.
- **ops#265 answered, stays open on its own terms.** Its closing condition is weewx's first real
  `marvinctl push`, not the plumbing being ready. Checked our own records: still "wired but unused" —
  the only real push we've ever done was the old one-off save/scp/load/push mechanism, which predates
  `marvinctl push` entirely. Next real version cut is the natural trigger to exercise it.
- **Job 5 re-verified live, unchanged, still correctly deferred.** Confirmed via `marvinctl cgroup`/
  the host cgroupfs directly: the unit file already carries `--cgroup-parent=weather.slice`, but the
  currently-running container (PID matches `docker inspect`'s `State.Pid`) still sits under
  `system.slice/docker-<id>.scope`. No restart forced — the job's own note says don't restart solely
  for this; unchanged from S126, carried forward as-is.

### ▶▶ S128 JOB LIST

1. **Merge PR #360** (or confirm it merged) and update `CONSTANTS.md`'s deploy-layer verification if
   anything about `exec-ro`'s mount shape turns out to matter there too.
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
   urgency — fold into the next natural restart of `weewx.service`, don't restart solely for this.
   Verify after: `docker inspect --format '{{.State.Pid}}' weewx-rtldavis-v2` then
   `cat /proc/<pid>/cgroup` should show `weather.slice`, not `system.slice/docker-….scope`.
7. **`ops/soak_check.sh` and `ops/freeze_baseline.py` still NAS-hardwired**, same root cause ops#250
   was (not yet filed as their own tracker items — do that, or fold into a new issue, before picking
   either up). `campaign_analyze.py`'s port (S127, PR #360) is the template: two clean `marvinctl`
   calls replaced a whole ssh round-trip; these two are shaped differently (soak_check.sh especially —
   a dozen live checks, remote awk log-windowing) and will need their own design pass, not a copy.

### Current state (S127 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` unit in `/weather.slice`, but the **container's actual cgroup is not** — needs one more restart to pick up `--cgroup-parent` (job 6, MARVIN-DEC-0141, re-verified S127 unchanged); `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, `ExecStop=docker kill` (MARVIN-DEC-0137) — runs as `t-weewx` (996:986) via unit `--user` since 13:12:05 EDT 09-06 (DEC-0147) |
| Reception | **100% mean, every post-v2.0.16 6h window since 09-03 18:00** (S126 job 6) — RF question reads closed; blocker 2 (RF-dead) unfired, watch continues |
| InfluxDB | marvin, `weewx-influxdb.service` since 09-04 22:35:02 ET, v2.7.12; backup timer armed |
| Foundation | fully decommissioned — project directory deleted, NFS export retired, DSM tasks disabled (ops#278 closed) |
| `main`/`dev` | `dev` carries all of S126; PR #360 (S127, DEC-0148) open against `dev`, not yet merged; `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · self-service `push` LIVE (ops#265, unchanged, still closes on first real push) |
| GitHub Releases | **v2.0.12–v2.0.16 backfilled, live** (#331 closed, DEC-0145) |
| Git | S127: PR #360 open (`port-campaign-analyze-marvin` → `dev`), awaiting merge. No other local branches or worktrees left over |
| Trackers | repo: none open (#327/#331 closed) · ops: #250 closed S127 (DEC-0148) · #257 limb 1 open (limbs 2/3 closed) · #110/#265/#272/#274 (EnvironmentFile + marvin-release.sh only) open, correctly gated/deferred · #278/#275/#273/#264/#218 closed prior sessions |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

S126 ran on Sonnet through job 8, then the owner switched to Fable (desktop `/model`, which
PERSISTS — OPS-DEC-0036/0062) for the item-5 design + live cutover, the one judgment-work item
flagged. **Floor NOT yet restored at this write** — owner re-runs `/model` to `claude-sonnet-5` at
close; an agent cannot.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). S126 added three
traps to §2 (subagent checkout collisions, same-anchor DEC conflicts, `gh pr merge`'s bare-command
requirement) — nothing left to move.

_Last updated: 2026-09-06 (S126, ~13:30 ET). Session summary: worked the full 8-item job list
end to end (nine PRs, all merged) — GitHub Releases backfilled after 5 releases shipped silently
(#331), two of three marvin unit-file fixes shipped (REMEDY_SYSTEMCTL confirmed correct against the
real sudoers file, ExecStop=docker kill live), ops#278 closed with a full code trace rather than a
re-asserted "looks harmless," the first clean post-fix RF baseline read taken (100% mean, blocker 2
still unfired), and two separate stale-doc findings (BACKLOG.md missing the DEC-0134/0135 campaign
correction, a pre-#317 footnote) caught while doing other work rather than left for someone else.
Settled a live cross-session discrepancy on ops#257 by checking the actual log rather than deferring
it. One item (job 5's upstream post) is deliberately left mid-flight pending the owner's tone
review — not a gap, the correct stopping point for that specific task. Late addition: ops#274 item 5
executed and verified — weewx's container no longer runs as root._
