# Roadmap — weewx-rtldavis

**Status:** Prioritized plan
**Last updated:** 2026-07-04 (S17)

STATUS.md holds what's *in motion right now*; this holds the ordered plan. BACKLOG.md holds
unordered ideas not yet scheduled.

## P0 — Governance bootstrap (S16–S17, in progress)
- [x] Reconcile repo with production truth; `prod-baseline-20260704` (S16).
- [~] Docs bootstrap: nine-file governance, backfilled DECs, INTERFACES (S17, this).
- [ ] Pre-commit + CI: ruff / ruff-format / mypy + secret-scan hook (S17, DEC-0015).
- [ ] Fix remote URL casing (lowercase → canonical `WeatheredScientist/`).
- [ ] Review + clean the stale public `origin/feature/influxdb-grafana` branch: cherry-pick any
      driver-relevant commit (e.g. `3f5470f` wind-warmup fix), move dashboard JSON out (belongs to
      the dashboard repo per DEC-0010), delete the branch from the remote.

## P1 — The false-rain fix (first change through the new workflow) → v2.0.3
The proving run. Feature branch off `dev`. Defense in depth (DEC-0006 null-on-rejection philosophy):
1. [ ] **Confirm first** — pull driver/WeeWX logs around the two known events (recent ~03:00 spike +
       the late-May occurrence); look for the lone +128 rain-counter step-and-return (0x80 bit-flip).
       Correlate CRC-failure logging and pre-dawn ISS battery/reception.
2. [ ] **StdQC tightening (cheap, immediate)** — `[StdQC]` `rain = 0, 10, inch` → a physically
       plausible per-interval cap (~0.5"); blocks 128-count spikes, never clips real convective rain.
       `weewx.conf` edit + restart (no rebuild).
3. [ ] **Driver spike filter (the real fix)** — reject a single-packet rain-counter delta ≥ threshold
       (flag exactly-128 / bit-7-dominated) as missing, in `rtldavis.py` (volume-mounted, hot-swap).
4. [ ] **Verify** across several pre-dawn windows against the WeatherLink Live gold standard.
5. [ ] Fold in the pending dewpoint cold-start rewrite (the honest-null Jun-16 version — needs a
       rebuild since dewpoint is baked). Release **v2.0.3** on GitHub + Docker Hub, superseding
       rw250-test with a properly tagged image.

**Blocker to resolve first:** a dev-WeeWX test strategy (there's no drop-in dev receiver). Propose
Simulator-backed dev container for logic (2) + reversible live hot-swap for RF-dependent (3)/(4)
before touching prod (DEC-0011). Bug timing is calendar-bound (pre-dawn) — verification spans days.

**S18 status:** driver fix + StdQC backstop built and unit-tested on `feature/rain-spike-filter`;
pending deploy + v2.0.3 release (see STATUS). Confirmed root cause = DEC-0021.

## P1.5 — Sensor-QC hardening (S19, DEC-0022) — after v2.0.3
- [ ] Fix the stale-substitution DEC-0006 violation in `dewpoint_service.py`: null
      temp/humidity/radiation/UV after a sensor-failure timeout instead of holding the last value
      forever — while still caching across the VP2+'s normal sparse-packet field rotation. Likely
      folds into the pending dewpoint rewrite.
- [ ] Add minor `[StdQC]` bounds: high-side `windGust`, `radiation`, `UV`.

## P2 — RF optimization, done honestly
- [ ] 24 h+ **averaged gain sweep, no inline preamp**, to settle gain 372-vs-207 (DEC-0017). ~1–2 wk.
- [ ] 24 h **receiveWindow sweep** to settle rw250-vs-rw350 and reconcile image tag ↔ Dockerfile.
- [ ] Rebuild image from clean source; confirm the running binary's receiveWindow (ARCHITECTURE §6).
- [ ] Investigate rebuilding `rtldavis` from newer Go source to emit `FreqError`/`ChannelIdx`
      telemetry, enabling data-driven `-ppm`/`-fc` tuning (BACKLOG RF history).

## P3 — Modularity toward multi-source (PRINCIPLES §1)
- [ ] Harden INTERFACES.md as the stable contract; document it well enough for a non-Davis WeeWX or
      CumulusMX producer to satisfy it.
- [ ] Remove the vestigial `loopdata.py` mount + `[LoopData]` section (DEC-0005).

## P4 — Housekeeping / community
- [ ] Rotate the exposed WU API key; move it to `monitor.env` env-var (DEC-0012, BACKLOG).
- [ ] README refresh (Docker Desktop USB findings, current install flow).
- [ ] Reconcile compromised May monthly rain totals against the WLC gold standard (don't compound).
