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

## ▶ Resume here (S130 → S131)

### What's settled (do not re-derive)

**Post-hardware-install incident recovered and verified this session — DEC-0151. `weewx_monitor.py`'s
PID-guard fix is committed; merge + marvin deploy is this session's own immediate next step, not
deferred to S131 (unless this session ends first — check git log/PR state before assuming either way).**

- **Incident:** owner hardware installs required a graceful `weewx.service` stop at 17:09 EDT.
  DEC-0150's landmine list never named `influxdb/` (not git-tracked) and a bind-mount-follows-inode
  effect masked the gap until that stop — the first post-install boot of `weewx-influxdb.service`
  hit empty root-owned placeholders and crash-looped. Root-caused and the store restored by the
  marvin-side session; **verified independently here** (ownership, contents, unit state) before
  acting on the report, per this repo's own "verify infra claims externally" rule.
- **Recovery, self-service throughout, no Class C needed:** started `weewx-influxdb.service` (42/42
  shards clean, all 4 buckets confirmed); backfilled the archive→Influx gap via an ad hoc
  `marvinctl exec` into the **live** container — `exec-ro` turns out to have **no network egress at
  all** (fine for `campaign_analyze.py`'s read-only queries, useless for a POST) — reading the
  InfluxDB token straight out of the mounted `weewx.conf` so it never touched this session's
  transcript. Window bounded from `weewx.log` ground truth, not the peer's estimate: last good
  publish 17:08:00 EDT, first good-after 20:52:00 EDT — 34 records posted, verified via
  `influx query`.
- **Fixed `weewx_monitor.py`'s PID guard** (`weewx_monitor.py`, was crash-looping every ~15-30s since
  19:51, alerting/watchdog dark the whole time): `os.path.exists('/proc/<pid>')` can't tell "the old
  monitor is alive" from "some unrelated process now owns that number" — post-reboot the number
  landed on `weewx.service`'s own docker-run process. Replaced with an `flock`-based lock (kernel
  releases it on process exit/reboot, immune to PID reuse by construction). Green gate passed
  (ruff/mypy/475 pytest). **Committed, not yet merged or deployed as of this note** — see job 1.
- **`ops/soak_check.sh`'s NAS-hardwiring filed as its own item**,
  [ops#287](https://github.com/WeatheredScientist/eaglehunt-ops/issues/287), cross-linked from
  ops#286, PR #366 merged.
- Full account: `docs/DECISIONS-FULL.md` DEC-0151.
- **Model tier: this session ran entirely on Sonnet, no escalation.** Nothing to restore.

### ▶▶ S131 JOB LIST (S130's own unfinished step comes first)

1. **If not already done this session: merge the pidfile-fix PR, then deploy** —
   `marvinctl --tenant weewx pull` + `restart weewx-monitor.service`, verify the crash loop stopped
   (`marvinctl unit weewx-monitor.service` shows `active (running)`, not `activating (auto-restart)`)
   and `Remedy armed:` appears post-restart. Check git log / `gh pr view` for the actual PR number
   before assuming this is still open — don't re-do it if S130 finished it.
2. **Fix DEC-0150's own runbook** per the marvin session's correction: derive a landmine list from
   every unit's bind-mount sources (`grep -- '-v /srv/docker/weewx' /etc/systemd/system/weewx*.service`,
   plus hlf-api's read-only mount of `weewx.sdb`) rather than from memory/git-tracked-file diffing
   alone — `influxdb/` being untracked is exactly what the old method missed. Update
   `CONSTANTS.md`'s release-mechanics section and/or `docs/CONVENTIONS.md` with this, not just BOOT.
3. Consider porting `ops/backfill_influx.py` to run natively against marvin (NAS-path and
   `localhost:8086` defaults, no `--dry-run`-through-marvinctl path) — this session solved one
   incident's window with an ad hoc inline script rather than fixing the tool itself.
4. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix (issue #337) and install both unit
   changes in their next units gesture — note this is the **unit file**, a separate artifact from
   `weewx_monitor.py` above.
5. Carry forward job 8's remaining untouched items (EnvironmentFile, `marvin-release.sh`)
   exactly as S126 left them — none are due, none are blocked on anything weewx can do alone.
6. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) for a maintainer reply** —
   repo's been dormant since 2023-12-22, don't chase it, just notice if it moves.
7. `CONSTANTS.md` infra re-verify (S105-era, still stale outside what S129/S130 touched) ·
   `docs/ARCHITECTURE.md` mount table still NAS-pathed (S30) · `CHANGELOG.md` archive rollup
   overdue — S122 and earlier still inline, past the ~3-session guideline (pre-existing debt,
   carried again, one session closer).
8. **Now that a real `dev` checkout exists on marvin, revisit whether `ops/soak_check.sh` and other
   still-NAS/ssh-hardwired tooling could instead run via `marvinctl exec-ro`** — with the caveat
   this session found: `exec-ro` has no network egress, so anything needing to reach Influx (like
   `soak_check.sh`'s own checks might) needs the `marvinctl exec`-into-live-container path instead.

### Current state (S130, mid-close — deploy step pending)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` running unaffected throughout this incident (the incident was `weewx-influxdb.service` and `weewx-monitor.service`, not the main container). `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986) since DEC-0147 |
| InfluxDB | marvin, `weewx-influxdb.service` — **down 20:09:20→20:53:19 EDT 09-07 (this incident), restarted and verified clean**; gap 17:09→20:52 backfilled (34 records, DEC-0151) |
| weewx-monitor | **crash-looping since 19:51 EDT 09-07 as of this note** — fix committed (flock-based lock), merge + deploy is job 1, not yet done as this note is written |
| Reception | unchanged this session — 100% mean through S126's last read; watch continues |
| Foundation | fully decommissioned (unchanged) |
| `main`/`dev` | pidfile-fix branch pushed, PR open or merged (check job 1) — `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged this session |
| GitHub Releases | unchanged this session |
| Tenant tree | unchanged this session — real `git` checkout since S129, `marvinctl pull` self-service |
| Trackers | repo: #337 open (unchanged) · ops: #287 filed S130 (soak_check.sh), cross-linked to #286 · #286/#265/#110 open, correctly gated/deferred |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.
5. **weewx-monitor.service crash-loop** — fix committed this session, deploy pending (job 1). Until
   deployed, no uploader alerting or RF watchdog is running.

## Model tier

**Floor confirmed restored, no action needed.** S130 ran entirely on Sonnet, no `/model` switch.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). **New this session:**
a bind mount follows the inode, not the path — a directory move after a container starts is
invisible to it until the next restart, and an untracked (non-git) directory won't show up in a
SHA-diff landmine sweep. Also: `marvinctl exec-ro` has no network egress at all; `marvinctl exec`
into the live container does.

_Last updated: 2026-09-07 (S130, ~21:00 ET). Session summary: filed ops#287 (soak_check.sh
NAS-hardwiring), then a live incident arrived via cross-session message from the marvin-side
session — DEC-0150's landmine list had missed `influxdb/`, causing a crash loop discovered during
owner hardware installs. Verified every claim independently via read-only `marvinctl` checks before
acting (ownership, unit status, log evidence) rather than trusting the peer report outright.
Started `weewx-influxdb.service`, backfilled the 17:09-20:52 EDT gap (34 records) via an ad hoc
script run inside the live container after discovering `exec-ro` has no network path. Found and
fixed `weewx_monitor.py`'s PID-reuse pidfile bug independently (crash-looping since 19:51,
watchdog/alerting dark) — replaced with an flock-based lock. Coordinated throughout via
`send_message` to the marvin session per this repo's cross-repo SOP. Deploy of the pidfile fix
(merge + `marvinctl pull` + restart) is this session's own remaining step._
