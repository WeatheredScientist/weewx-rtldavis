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

> **Current session: S23** (2026-07-05) — governance-alignment initiative (docs-only, zero prod
> risk). Governed lineage: S16→S17→S18→S19→S20→S21→S22→**S23**. Next session = S24.

_Last updated: 2026-07-05 (S23 — cross-project governance-alignment audit (ASSESSMENT.md) + the safe
docs deliverables: LICENSE=GPLv3, AGENTS.md, ROADMAP restructured to shared P-tiers, STATUS made the
session-# source of truth with the handoff moved in from memory, doc-map reorder. No prod code, no
deploy. Prior: S22 — merged PR #2 (S20 governance) into the rain branch; built + tested the
reception-metric Layer A fix (DEC-0024) pending a monitor restart; no rain glitch in the wild yet;
rain fix still live + unmerged.)_

---

## Active thread

> **▶ Resume here.** S18's false-rain fix is **committed, deployed live, and its email alert is
> active** — but **NOT yet merged** off `feature/rain-spike-filter`. Root cause confirmed (DEC-0021).
> Done so far: commits `be72832` (fix + 13/13 tests) and `3aabee8` (monitor alert); reversible live
> hot-swap of `rtldavis.py` + `weewx.conf [StdQC]` (`rain 0,10→0,1.0`, added `rainRate 0,16`) to
> `weewx-rtldavis-v2`; monitor restarted 2026-07-04 (PID 584) so the rain-glitch email alert is now
> live. A live storm right after deploy (0.44", peak ~1.5 in/hr) flowed through with zero false
> rejections. Remaining, in order:
> 1. **Watch for the first real glitch in the wild** — confirms fix + alert together (log
>    "rejecting implausible counter delta" + clean archive + the email). Calendar-bound (~1 glitch/2–3 wk).
>    Checked 2026-07-05 (S22, read-only): **none fired yet.**
> 2. After it's ridden a few days clean: **merge `feature/rain-spike-filter` → `dev` → `main` + tag
>    v2.0.3**, folding in the pending baked dewpoint rewrite (needs an image rebuild — bigger deploy
>    than the hot-swap; plan it). The rain branch now also carries the merged S20 governance work and
>    the reception Layer A fix.
> 3. Then, in a later session, **DEC-0022 sensor-QC hardening** (below).
>
> _Numbering note (DEC-0023): the "shared lineage with the dashboard" (DEC-0013) never held — the
> sibling runs its own S1→S40 counter and never shared one. This repo now counts **independently**:
> its line is contiguous S16→…→**S20**→**S21**→**S22** (this session). Cross-repo refs are prefixed
> (`weewx S22` vs `dash S40`)._

## Open threads (not yet shipped)

- **Reception metric ~150% — Layer A built + tested (DEC-0024, S22), PENDING DEPLOY.** Root cause: the
  daily RF-Reception email over-counts because `weewx_monitor.py` counted raw `Wunderground-RF:
  Published` log lines, but the driver publishes freqError freq-hop packets as duplicate publishes of
  the SAME record epoch (~1.66×; live 2026-07-05 sample showed a clean 2× — same epoch posted twice).
  **Layer A fix** (`feature/reception-dedup`, commit `20bf7c0`): a pure `wu_record_key()` helper dedups
  on the trailing `(<epoch>)`; the window counts unique epochs. 6 offline tests, driver + alert logic
  untouched. **Deploy = monitor restart only** (`sudo kill <pid>`, pidfile `logs/weewx_monitor.pid`;
  the respawn loop reloads on-disk code ≤5 min). Reversible. **Layer B** (driver stops publishing
  dataless freqError packets + disable `RAW_*` debug logging; also fixes 15 MB `weewx.log` bloat) is
  deeper, No-Rewrite applies — still deferred. Doc-vs-reality flag stands: the running binary **does**
  emit `ChannelIdx`/`FreqError` (BACKLOG said it didn't). See DEC-0024 + BACKLOG.
- **Rain fix** deployed live but **not merged** — still only on `feature/rain-spike-filter` (`dev`
  and `main` untouched). Promote to v2.0.3 once it's proven in the wild (see Active thread).
- **Sensor-QC hardening (DEC-0022, a later session):** the stale-substitution DEC-0006 violation in
  `dewpoint_service.py` (temp/humidity/radiation/UV — real 6263 sensors get stuck if they fail) +
  minor windGust/radiation/UV StdQC bounds. Ties into the pending dewpoint rewrite. Do after v2.0.3.
- **Pending v2.0.3 dewpoint rewrite** — the honest-null Jun-16 host version is written but undeployed
  (dewpoint is baked → needs a rebuild). Fold into the v2.0.3 release; may also address DEC-0022 #1.
- **Gain 372, interim** (DEC-0017) — awaiting a 24 h averaged no-preamp sweep to settle vs 207.
- **rw250 vs rw350** (ARCHITECTURE §6) — running binary likely rw250, committed Dockerfile patches
  rw350; needs a rebuild + receiveWindow sweep to reconcile.
- **Vestigial `loopdata.py`** — mounted + `[LoopData]` section present but not in any active service
  list; safe to remove, not urgent (don't touch prod casually).

## Needs a check / housekeeping

- **Rotate the exposed WU API key** (was hardcoded in NAS `wxcheck.sh`; scrubbed from the repo in S16,
  real key still live on the NAS). Non-urgent, owner-acknowledged 2026-07-04.
- **Remote URL casing** — origin is lowercase; GitHub redirects to canonical `WeatheredScientist/`.
- **Stale public branch** `origin/feature/influxdb-grafana` (11 commits) — may carry dashboard JSON +
  a driver-relevant wind-warmup fix; review, cherry-pick driver bits, delete from remote.

## Next session actions (→ S24)

**This section is the repo-visible handoff** (replaces the old Claude-private `next-session-actions`
memory, which now only points here). Read it first when resuming.

1. **Finish the S23 governance-alignment tail** (the `feature/s23-governance-alignment` branch): after
   review, merge it; then the small stragglers — archive/fold the root `cleanup_backlog.md` into
   BACKLOG, and resolve `logging.additions` + the bare `additions` artifact (document or remove). Then
   converge the changelog format (Keep-a-Changelog headings) + DECISIONS entry-skeleton (planned S25).
2. **S24 = thorough code-quality review** — `rtldavis.py` (1506 ll) + `weewx_monitor.py` + the
   uploaders, for sloppy/confusing/under-commented code; deliver ranked findings, then agreed fixes on
   a branch (No-Rewrite applies). Fold in per-file SPDX `GPL-3.0-or-later` headers.
3. **Deploy the reception Layer A fix** (owner action; monitor-restart-only, DEC-0024): scp the new
   `weewx_monitor.py` to the NAS, then `sudo kill <pid>` (pidfile `logs/weewx_monitor.pid`) — the
   respawn loop reloads on-disk code ≤5 min. Confirm the next RF-Reception email reads ≤100% (was
   ~150%). Review + merge draft PR #3. Reversible.
4. **Watch for the first real rain glitch in the wild** — still not fired (checked S22). Grep
   `weewx.log` for "rejecting implausible counter delta" + the monitor email. Gates v2.0.3.
5. **Then v2.0.3** — merge `feature/rain-spike-filter` → `dev` → `main`, tag, release on GitHub +
   Docker Hub; fold in the baked honest-null dewpoint rewrite (needs an image rebuild). See ROADMAP P1.
6. **Housekeeping (P0/P4):** remote URL casing (lowercase → `WeatheredScientist/`); clean stale
   `origin/feature/influxdb-grafana`; rotate the exposed WU API key.

**Live access (read-only used in S21/S22):** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in
gitignored `docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use
`env -u GH_TOKEN` for any `git push` (keyring token, not the PAT).
