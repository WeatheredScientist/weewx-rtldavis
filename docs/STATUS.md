# Status — weewx-rtldavis

**In-flight working state (what's on the bench right now).** Read first at the start of a session,
update last before finishing. ROADMAP.md holds the full prioritized plan; this file holds only what
is actively in motion, parked, or needs a check.

- DECISIONS.md records *settled* decisions. **This file records open ones.**
- CHANGELOG.md records *shipped* work. **This file records work not yet shipped.**

When something here becomes permanent (a decision is made, a feature ships), move it to
DECISIONS.md / CHANGELOG.md and delete it here. Keep this file short.

_Last updated: 2026-07-04 (S17 — docs bootstrap on `dev`)_

---

## Active thread

> **▶ Resume here.** S17 in progress: nine-file governance authored on `dev`. Next up in S17:
> add pre-commit + CI (ruff/mypy + secret-scan), then review + commit on `dev` (pause for approval),
> then decide whether to push `dev` and merge to `main`.
>
> After S17 lands, the natural clean session boundary is **before the P1 rain fix** — a fresh session
> will then auto-load this CLAUDE.md the proper way.

## Open threads (not yet shipped)

- **`dev` branch is local-only** — created off `prod-baseline-20260704` in S16, never pushed. Decide
  at end of S17 whether to publish it.
- **Rain fix (P1)** not started. Blocker: agree a dev-WeeWX test strategy (no drop-in dev receiver) —
  Simulator-backed container for logic + reversible live hot-swap for RF checks — *before* touching
  prod. Targets confirmed: `[StdQC] rain = 0, 10, inch` (weewx.conf) + spike filter in the
  volume-mounted `rtldavis.py`. Release target v2.0.3.
- **Pending v2.0.3 dewpoint rewrite** — the honest-null Jun-16 host version is written but undeployed
  (dewpoint is baked → needs a rebuild). Fold into the v2.0.3 release, not before.
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
