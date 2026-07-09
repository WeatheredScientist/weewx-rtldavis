# Roadmap — weewx-rtldavis

**Status:** Direction (what next, in what order). For *why* see DECISIONS.md; for *how* see
ARCHITECTURE.md; for *what's on the bench right now* see STATUS.md (the single source of truth for
the current session + active thread).
**Last updated:** 2026-07-09 (S35 — docs diet DEC-0030: collapsed DONE sections to pointer
summaries; reconciled P0.6/P1/P1.5 to reality — v2.0.3 shipped S32, sensor-QC resolved S33.)

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
Prod-truth reconcile + `prod-baseline-20260704`, nine-file governance, CI/pre-commit + secret gate,
independent session numbering. See CHANGELOG-ARCHIVE `[S16]`–`[S20]`, DEC-0010…0017, DEC-0023.

## P0.5 — Governance alignment across the family (S23, this initiative) — IN PROGRESS
Bring this repo's *form* into line with the sibling repos and external best practice, keeping content
isolated (ASSESSMENT.md §2). Docs-only; zero prod risk.
- [x] `docs/ASSESSMENT.md` — cross-repo audit + draft Governance Standard v1 (S23).
- [x] `LICENSE` = GPLv3 (WeeWX-ecosystem standard; matches the free/open mission) — S23.
- [x] `AGENTS.md` — cross-agent entrypoint pointing at CLAUDE.md + STATUS.md (S23).
- [x] ROADMAP restructured to shared P-tiers / short-med-long, folded to current reality (S23, this).
- [x] STATUS.md is now the **single source of truth** for the session number; handoff/next-actions
      moved **into the repo** (out of Claude-private memory, now a pointer); STATUS promoted to
      doc-map slot #2; `CLAUDE.md` numbering rule updated (S23).
- [ ] Archive/fold the pre-governance root `cleanup_backlog.md` into BACKLOG; give `logging.additions`
      + the bare `additions` artifact a documented home or remove them (S23).
- [x] **Code-quality review of rtldavis.py + monitor + uploaders** — done S24; promoted to its own
      workstream (see **P0.6** below). Per-file SPDX headers folded into P0.6.
- [x] **Docs diet (DEC-0030)** — tiered session read, DECISIONS index+FULL split, CHANGELOG roll,
      STATUS prune ritual; the family-wide pattern (dash DEC-0081 → hyperlocal DEC-0095 → here) — S35.
- [ ] **Follow-on (own session):** Keep-a-Changelog headings + DECISIONS entry-skeleton convergence (S25).
- Two remaining P0 housekeeping stragglers, tracked here: fix remote URL casing (lowercase →
  canonical `WeatheredScientist/`); review + clean the stale public `origin/feature/influxdb-grafana`
  branch (cherry-pick the driver-relevant `3f5470f` wind-warmup fix, move dashboard JSON out per
  DEC-0010, delete the branch from the remote).

## P0.6 — Code-quality review + fixes (S24–S25, M-A S28) — ✅ DONE
Ranked findings in `docs/CODE_REVIEW_S24.md`; all fixes landed with regression tests — H1/H2/M3/U3
(S24), U1/U2 owm rebase, U4 TLS, M4 dead code, nits + SPDX headers (S25), M-A/L-B monitor
incremental read (S28). See CHANGELOG-ARCHIVE `[S24]`, `[S25]`, `[S28]`. Driver fixes shipped in
v2.0.3 (S30/S32).

## P1 — The false-rain fix → v2.0.3 (the proving run) — ✅ DONE
Root cause DEC-0021, StdQC tightening + driver spike filter + email alert (S18), reception-metric
Layer A (S22/S27) then re-based on `rxCheckPercent` (S31, DEC-0024), honest-null dewpoint + clobber
fix baked (S30). **v2.0.3 released S32** (`v2.0.3` + `prod-baseline-20260705`, GitHub + Docker Hub)
— the wild-glitch gate was consciously waived on live evidence (DEC-0026); still 0 rejections to
date (watch continues, STATUS). See CHANGELOG-ARCHIVE `[S18]`–`[S32]`.

**Blocker discipline (DEC-0011):** no drop-in dev receiver — RF-dependent verification is calendar-
bound and done via reversible live hot-swap with an instant rollback path.

---

# MEDIUM TERM (P2–P3) — after v2.0.3

## P1.5 — Sensor-QC hardening (DEC-0022) — ✅ RESOLVED (DEC-0029, S33) · deploy pending
Both items superseded by the decode-layer `SensorQC` filter + DewpointCacher timeout-null
(DEC-0029, merged to `dev` S34). **Ships with the owner-run v2.0.4 rebuild** — the live-verify plan
is STATUS's active thread.

## P2 — RF optimization, done honestly (PRINCIPLES §3)
- [ ] 24 h+ **averaged gain sweep, no inline preamp**, to settle gain 372-vs-207 (DEC-0017). ~1–2 wk.
- [ ] 24 h **receiveWindow sweep** to settle rw250-vs-rw350 and reconcile image tag ↔ Dockerfile.
- [ ] Rebuild image from clean source; confirm the running binary's receiveWindow (ARCHITECTURE §6).
- [ ] Investigate rebuilding `rtldavis` from newer Go source to emit `FreqError`/`ChannelIdx`
      telemetry, enabling data-driven `-ppm`/`-fc` tuning (BACKLOG RF history). Also the DEC-0024
      Layer B path: driver stops publishing dataless freqError packets. (The INFO-logging half of the
      `weewx.log` bloat was already fixed in S24 — see P0.6 M3.)

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
