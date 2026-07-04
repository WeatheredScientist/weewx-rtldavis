# Status — weewx-rtldavis

**In-flight working state (what's on the bench right now).** Read first at the start of a session,
update last before finishing. ROADMAP.md holds the full prioritized plan; this file holds only what
is actively in motion, parked, or needs a check.

- DECISIONS.md records *settled* decisions. **This file records open ones.**
- CHANGELOG.md records *shipped* work. **This file records work not yet shipped.**

When something here becomes permanent (a decision is made, a feature ships), move it to
DECISIONS.md / CHANGELOG.md and delete it here. Keep this file short.

_Last updated: 2026-07-04 (S18 — rain fix built + tested on `feature/rain-spike-filter`)_

---

## Active thread

> **▶ Resume here.** S18: the false-rain fix is **built, tested (13/13 offline), and documented** on
> `feature/rain-spike-filter` (off `dev`) — NOT yet committed, deployed, or merged. Root cause
> confirmed (DEC-0021). Next actions, in order:
> 1. Commit the feature branch (fix + tests + example + docs).
> 2. **Reversible live hot-swap deploy** in a dry, low-traffic window — backup + checksum →
>    in-container import pre-flight check → swap + clear pyc → `docker kill`+`start` → verify data
>    flows within 60s → instant rollback if not. Plus the live `weewx.conf [StdQC]` edits
>    (`rain 0,10→0,1.0`, add `rainRate 0,16`) with a config backup.
> 3. Verify across pre-dawn windows vs the WeatherLink Live console (calendar-bound — ~1 glitch/2–3 wk).
> 4. Merge to `dev`, then promote to `main` + tag **v2.0.3**, folding in the pending dewpoint rewrite.

## Open threads (not yet shipped)

- **Rain fix** built, not deployed/merged (see Active thread). `dev` is published; the feature
  branch and `main` are not touched yet.
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
