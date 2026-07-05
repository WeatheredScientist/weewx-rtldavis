# Roadmap — weewx-rtldavis

**Status:** Direction (what next, in what order). For *why* see DECISIONS.md; for *how* see
ARCHITECTURE.md; for *what's on the bench right now* see STATUS.md (the single source of truth for
the current session + active thread).
**Last updated:** 2026-07-05 (S23 — governance-alignment audit; ROADMAP restructured to the shared
P0–P4 / short-med-long vocabulary and folded to post-S22 reality. See CHANGELOG `[S23]`, ASSESSMENT.md.)

STATUS.md holds what's *in motion right now*; this holds the ordered plan. BACKLOG.md holds
unordered ideas not yet scheduled.

## The vision

**Own your weather data and let others own theirs.** An RTL-SDR passively intercepts the same
915 MHz Davis broadcast the console hears, so the readings become locally owned and re-pointable —
the "escape the WeatherLink lock" tool. The durable deliverable is not "a Davis driver" but a
**stable, documented data contract** (loop-JSON + InfluxDB schema, INTERFACES.md) that non-Davis
WeeWX, other sinks, and eventually CumulusMX can satisfy (PRINCIPLES §1). Published free under GPLv3
so the community can use and extend it.

## Priority vocabulary (shared across the Eagle Hunt family)

`P0` critical path / do first · `P1` important soon · `P2` later / measured · `P3` modularity ·
`P4` housekeeping / community. Horizon mapping: **short-term = P0–P1**, **medium-term = P2–P3**,
**long-term = P4 + the "longer horizon" section**. ✅ = done; annotations mark items *found stale
during an audit* rather than deleting the history.

## Guardrails

Full operating rules live in CONVENTIONS / CLAUDE.md. The ones that bite most often: this repo is
**PUBLIC** (secret-scan gate, DEC-0012), **prod is sacred** (one dongle/receiver, deploy-to-dev-first,
DEC-0011), **hot-swap what you iterate / bake what you trust** (DEC-0004), discuss design before
coding, and the **No-Rewrite Rule** (DEC-0014).

---

# SHORT TERM (P0–P1) — the current focus

## P0 — Governance bootstrap (S16–S20) — ✅ DONE
- [x] Reconcile repo with production truth; tag `prod-baseline-20260704` (S16).
- [x] Docs bootstrap: nine-file governance model, backfilled DECs, INTERFACES (S17).
- [x] Pre-commit + CI: ruff / ruff-format / mypy + the `check_secrets.sh` gate (S17–S20, DEC-0015).
- [x] Independent per-repo session numbering (S20, DEC-0023 supersedes DEC-0013).

## P0.5 — Governance alignment across the family (S23, this initiative) — IN PROGRESS
Bring this repo's *form* into line with the sibling repos and external best practice, keeping content
isolated (ASSESSMENT.md §2). Docs-only; zero prod risk.
- [x] `docs/ASSESSMENT.md` — cross-repo audit + draft Governance Standard v1 (S23).
- [x] `LICENSE` = GPLv3 (WeeWX-ecosystem standard; matches the free/open mission) — S23.
- [x] `AGENTS.md` — cross-agent entrypoint pointing at CLAUDE.md + STATUS.md (S23).
- [x] ROADMAP restructured to shared P-tiers / short-med-long, folded to current reality (S23, this).
- [ ] STATUS.md becomes the **single source of truth** for the session number; handoff/next-actions
      move **into the repo** (out of Claude-private memory); STATUS promoted to doc-map slot #2 (S23).
- [ ] Archive/fold the pre-governance root `cleanup_backlog.md` into BACKLOG; give `logging.additions`
      + the bare `additions` artifact a documented home or remove them (S23).
- [ ] **Follow-ons (own sessions):** Keep-a-Changelog headings + DECISIONS entry-skeleton convergence
      (S25); thorough code-quality review of rtldavis.py + monitor + uploaders (S24); per-file SPDX
      `GPL-3.0-or-later` headers (fold into the S24 review).
- Two remaining P0 housekeeping stragglers, tracked here: fix remote URL casing (lowercase →
  canonical `WeatheredScientist/`); review + clean the stale public `origin/feature/influxdb-grafana`
  branch (cherry-pick the driver-relevant `3f5470f` wind-warmup fix, move dashboard JSON out per
  DEC-0010, delete the branch from the remote).

## P1 — The false-rain fix → v2.0.3 (the proving run) — IN PROGRESS
First real change through the governed workflow. Defense in depth (DEC-0006 null-on-rejection):
1. [x] **Confirm root cause** — lone +128 rain-counter step-and-return (0x80 bit-flip) at pre-dawn
       battery/reception dips (S18, DEC-0021).
2. [x] **StdQC tightening** — `[StdQC]` `rain 0,10 → 0,1.0`, added `rainRate 0,16` (S18, live).
3. [x] **Driver spike filter** — reject implausible single-packet rain-counter deltas in `rtldavis.py`
       (S18, `be72832`, 13/13 tests); email alert on rejection (`3aabee8`). Deployed live 2026-07-04
       via reversible hot-swap; monitor restarted (PID 584).
4. [~] **Verify in the wild** — a live storm right after deploy (0.44", peak ~1.5 in/hr) flowed through
       with zero false rejections. **Still awaiting the first real glitch** to confirm fix + alert
       together (calendar-bound, ~1 glitch / 2–3 wk; none as of S22). **This gates promotion.**
5. [ ] **Reception-metric Layer A fix** (DEC-0024, S22, draft PR #3 `feature/reception-dedup`) — dedup
       WU publishes on record epoch so the daily RF summary reads ≤100% (was ~150%). Built + 6 tests;
       **deploy = monitor restart only**; not yet deployed. Review + merge.
6. [ ] **Release v2.0.3** — once the rain fix has ridden clean a few days: merge
       `feature/rain-spike-filter` → `dev` → `main`, tag, release on GitHub + Docker Hub. **Fold in the
       pending honest-null dewpoint rewrite** (Jun-16 host version — dewpoint is baked, so this needs an
       **image rebuild**, a bigger deploy than the hot-swap; plan it). May also address DEC-0022 #1.

**Blocker discipline (DEC-0011):** no drop-in dev receiver — RF-dependent verification is calendar-
bound and done via reversible live hot-swap with an instant rollback path.

---

# MEDIUM TERM (P2–P3) — after v2.0.3

## P1.5 — Sensor-QC hardening (DEC-0022) — after v2.0.3
- [ ] Fix the stale-substitution DEC-0006 violation in `dewpoint_service.py`: null
      temp/humidity/radiation/UV after a sensor-failure timeout instead of holding the last value
      forever — while still caching across the VP2+'s normal sparse-packet field rotation. Likely folds
      into the pending dewpoint rewrite.
- [ ] Add minor `[StdQC]` bounds: high-side `windGust`, `radiation`, `UV`.

## P2 — RF optimization, done honestly (PRINCIPLES §3)
- [ ] 24 h+ **averaged gain sweep, no inline preamp**, to settle gain 372-vs-207 (DEC-0017). ~1–2 wk.
- [ ] 24 h **receiveWindow sweep** to settle rw250-vs-rw350 and reconcile image tag ↔ Dockerfile.
- [ ] Rebuild image from clean source; confirm the running binary's receiveWindow (ARCHITECTURE §6).
- [ ] Investigate rebuilding `rtldavis` from newer Go source to emit `FreqError`/`ChannelIdx`
      telemetry, enabling data-driven `-ppm`/`-fc` tuning (BACKLOG RF history). Also the DEC-0024
      Layer B path (driver stops publishing dataless freqError packets; fixes `weewx.log` bloat).

## P3 — Modularity toward multi-source (PRINCIPLES §1)
- [ ] Harden INTERFACES.md as the stable contract; document it well enough for a non-Davis WeeWX or
      CumulusMX producer to satisfy it.
- [ ] Remove the vestigial `loopdata.py` mount + `[LoopData]` section (DEC-0005).

---

# LONG TERM (P4 + horizon) — housekeeping, community, direction

## P4 — Housekeeping / community
- [ ] Rotate the exposed WU API key; move it to `monitor.env` env-var (DEC-0012, BACKLOG).
- [ ] README refresh for public users: Docker Desktop USB findings, current install flow, and a
      shortest-painless-path "run your own" onboarding section (mirrors the dashboard's public-release
      readiness workstream — this repo is already public, so this is polish, not a gate).
- [ ] Reconcile compromised May monthly rain totals against the WLC gold standard (don't compound).

## Longer horizon — direction, not scheduled work
- **Multi-source adaptability** (PRINCIPLES §1): keep the driver re-pointable so non-Davis WeeWX and
  eventually CumulusMX can rely on the same data contract. Record a DEC before any code depends on it.
- **Generic project-template harvest** (separate buildout): once the Governance Standard is proven here
  and propagated once, harvest it into a versioned GitHub *template repository* for all future projects
  (ASSESSMENT.md §5). Copy-not-link; tracked as its own effort, not part of this repo's release path.
