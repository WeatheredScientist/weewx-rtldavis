# Status — weewx-rtldavis

**In-flight working state (what's on the bench right now).** Read first at the start of a session,
update last before finishing. ROADMAP.md holds the full prioritized plan; this file holds only what
is actively in motion, parked, or needs a check.

- DECISIONS.md records *settled* decisions. **This file records open ones.**
- CHANGELOG.md records *shipped* work. **This file records work not yet shipped.**
- **This file is the single source of truth for the current session number and the next-session
  handoff** (DEC-0023). Every other doc — and Claude memory — points *at* this; none carries its own
  copy. Handoff state lives here (in the repo, visible on GitHub), never only in private memory.

When something here becomes permanent (a decision is made, a feature ships), move it to
DECISIONS.md / CHANGELOG.md and delete it here. Keep this file short.

> **Current session: S32** (2026-07-08) — **v2.0.3 RELEASED.** Soak day 4 clean (rx 75.4% 24 h avg,
> 0 rain rejections, survived an unplanned NAS reboot with clean dongle handoff) → gate passed. PR #15
> reconciled `main`'s S26 secret-gate commits into `dev` (kept `dev`'s DEC-0027 `ci.yml`); PR #11 merged
> `dev`→`main` (`f64f8d8`); tags **`v2.0.3`** + **`prod-baseline-20260705`**; GitHub release published;
> Docker Hub push **`:v2.0.3` + `:latest`** (digest `9dfd9b57…`) — the first public image that actually
> contains the driver fixes. **Also: S31 monitor deployed + live** (dropped-packets email, 6 h cadence;
> the NAS reboot had broken the boot task — ran as non-root, monitor down 06:56→17:28 until the owner
> reset the task user to root). **Security: Gmail app password found in public repo history — rotated**
> (DEC-0028; revoked + reissued, verified live; no history rewrite). This file was cleaned out
> post-release per its own rules; pre-S32 session narratives live in CHANGELOG.md.

_Last updated: 2026-07-08 (S32 — release cut + monitor live + credential rotation)._

---

## Active thread

> **▶ Resume here (S32 → S33).** v2.0.3 is released and the release thread is **closed**. The next
> big item is the **owner-priority bad-packet root-cause session** (below). First, the quick checks
> in "Next session actions".

## Open threads (not yet shipped)

- **Owner priority — root-cause temp/humidity/radiation/UV spikes as bad RF packets** (same class as
  the rain glitch), replacing StdQC/carry-forward bandaids with a decode-layer plausibility filter.
  Dedicated session, deep-debug model recommended (BACKLOG §Data integrity; DEC-0022). Ties into:
- **Sensor-QC hardening (DEC-0022):** the stale-substitution DEC-0006 violation in
  `dewpoint_service.py` for temp/humidity/radiation/UV (wind was fixed honest-null in v2.0.3) +
  minor windGust/radiation/UV StdQC bounds.
- **Watch for the first real rain glitch in the wild** — the filter is now live *and* released;
  expect log "rejecting implausible counter delta" + clean archive + the alert email
  (~1 glitch/2–3 wk; 0 to date as of 2026-07-08).
- **Reception Layer B (driver, DEC-0024):** persist raw `count`/`missed`; stop publishing dataless
  freqError packets; fix the ~1–2 pt floor-division optimism; disable `RAW_*` debug logging (also
  fixes ~15 MB/day `weewx.log` bloat). No-Rewrite applies; needs an image rebuild.
- **ERR-0001 InfluxDB honest-null** — the dashboard's InfluxDB copy still carries the July-4 phantom
  rain; cross-repo (DEC-0010), handle dashboard-side or via the Influx API (no `influx` CLI on NAS).
- **Gain 372, interim** (DEC-0017) — awaiting a 24 h averaged no-preamp sweep to settle vs 207.
- **Vestigial `loopdata.py`** — mounted + `[LoopData]` present but in no active service list; safe to
  remove, not urgent.

## Needs a check / housekeeping

- **Confirm the first 6 h dropped-packets email** (due at the first 00/06/12/18 local boundary after
  2026-07-08 17:28) reads sanely: ~75% mean, ~1,900 dropped per 6 h window — not ~100%.
- **NAS boot task fragility (new, S32):** the 2026-07-08 reboot left the `weewx_monitor` scheduler
  task running as a non-root user → monitor down ~10.5 h (sudo loop-fail). Owner reset it to root.
  **After the next DSM update/reboot, verify the task still runs as root** (symptom: `sudo: a
  terminal is required` spam in `logs/weewx_monitor.log`, no pidfile).
- **Rotate the exposed WU API key** (NAS `wxcheck.sh`; scrubbed from repo S16, real key still live).
  Owner-acknowledged; still owed. (The Gmail app password from the same era is **done** — DEC-0028.)
- **Docker Hub README auto-sync:** add repo secrets `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` to
  activate `.github/workflows/dockerhub-description.yml` (green no-op until then). Owner action.
- **Branch/tag cleanup:** delete merged `feature/rain-spike-filter` + `s32-reconcile-main`; the old
  `rw250-test` image tag is a misnomer (receiveWindow ships at upstream default) — retire when
  rollback confidence allows.
- **Snow / freezing / no heating tape** (parked, owner's future thread) — cold-weather failure modes
  we haven't designed for. 2026 = learning year.

## Next session actions (S32 done → S33)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S32 (2026-07-08):** v2.0.3 released end-to-end (PR #15 reconcile → PR #11 promote → tags →
GitHub release → Docker Hub `:v2.0.3`+`:latest`); S31 monitor deployed and verified live (root task
restored after reboot breakage; startup email OK; `STATION_NAME` now set — "Eagle Hunt PWS");
Gmail app password rotated after being found in public history (DEC-0028); legacy NAS
`weewx_monitor.sh` password neutered. See CHANGELOG [S32].

**▶ ON RETURN (S33), do this first:**
1. **Quick post-release health check** (read-only): container still on `:v2.0.3`, `RestartCount`,
   `rxCheckPercent` flowing ~70–90%, 0 rain rejections, monitor polling + the 6 h emails arriving.
2. Confirm the housekeeping items above haven't bitten (boot-task user, first 6 h email).
3. Then start the **bad-packet root-cause thread** (owner priority, top of Open threads) — design
   discussion first per PRINCIPLES §8; No-Rewrite applies to the driver.

**Live access:** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in gitignored
`docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use `env -u GH_TOKEN` for
any `git push` (keyring token, not the PAT).
