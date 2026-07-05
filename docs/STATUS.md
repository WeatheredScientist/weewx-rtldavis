# Status — weewx-rtldavis

**In-flight working state (what's on the bench right now).** Read first at the start of a session,
update last before finishing. ROADMAP.md holds the full prioritized plan; this file holds only what
is actively in motion, parked, or needs a check.

- DECISIONS.md records *settled* decisions. **This file records open ones.**
- CHANGELOG.md records *shipped* work. **This file records work not yet shipped.**

When something here becomes permanent (a decision is made, a feature ships), move it to
DECISIONS.md / CHANGELOG.md and delete it here. Keep this file short.

_Last updated: 2026-07-04 (S21 — reception-metric ~150% root cause confirmed, documented; DEC-0024)_

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
> 2. After it's ridden a few days clean: **merge `feature/rain-spike-filter` → `dev` → `main` + tag
>    v2.0.3**, folding in the pending baked dewpoint rewrite (needs an image rebuild — bigger deploy
>    than the hot-swap; plan it).
> 3. Then **S19 proper** — DEC-0022 sensor-QC hardening (below).

## Open threads (not yet shipped)

- **Reception metric reads ~150% (DEC-0024, S21) — root cause confirmed, fix deferred.** The daily
  RF-Reception email over-counts: `weewx_monitor.py` counts `Wunderground-RF: Published` log lines,
  but the driver publishes freqError freq-hop channel packets as extra dataless loop packets (~1.66×;
  live: 1605 publishes / 968 unique records, single transmitter). Cosmetic (metric only — real
  weather data & rain fix unaffected). Next move likely **Layer A** (monitor counts unique record
  epochs — safe, monitor-restart-only). **Layer B** (driver stops publishing dataless freqError
  packets + disable `RAW_*` debug logging; also fixes 15 MB `weewx.log` bloat) is deeper, No-Rewrite
  applies. Also flagged a doc-vs-reality contradiction: the running binary **does** emit
  `ChannelIdx`/`FreqError` (BACKLOG said it didn't). See DEC-0024 + BACKLOG.
- **Draft PR #2** (`s20-governance-hardening` → `feature/rain-spike-filter`) awaits review/merge — the
  S20 governance-hardening session: DEC-0023 independent numbering + two `check_secrets.sh` gate fixes.
  On merge, **STATUS.md + CHANGELOG.md will conflict** (this rain-branch S21 commit + PR #2 both touch
  them) — resolve keeping both the reception thread/entry and the numbering entry. Then rides to v2.0.3.
- **Rain fix** deployed live but **not merged** — still only on `feature/rain-spike-filter` (`dev`
  and `main` untouched). Promote to v2.0.3 once it's proven in the wild (see Active thread).
- **S19 — sensor-QC hardening (DEC-0022):** the stale-substitution DEC-0006 violation in
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
