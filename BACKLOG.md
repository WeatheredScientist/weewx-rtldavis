# Backlog — weewx-rtldavis

Unordered ideas and durable findings not yet scheduled. Scheduled work lives in ROADMAP.md;
in-flight work in docs/STATUS.md. Carried forward from the pre-governance NAS `BACKLOG.md`.

## Open ideas
- Reception improvement beyond ~70% (noise-floor limited at ~150 ft through walls).
- Windows/macOS FHSS investigation (Docker Desktop USB passthrough findings for the README).
- ESP32 secondary sensor node.
- Blitzortung lightning integration.
- Remove vestigial `loopdata.py` mount + `[LoopData]` section (DEC-0005).
- Rotate the exposed WU API key; store it in `monitor.env` as an env var, not inline (DEC-0012).

## Durable RF findings (from 2026-06-01 tuning sweeps — keep; these guide P2)

**CLI timing sweep (baseline, -ex 25/50/75/100, -maxmissed 25, combos):**
- All clustered ~63–66%; no material improvement over baseline.
- `-maxmissed 15` caused repeated 0/24 windows — **do not use**.

**receiveWindow:**
- rw400-test (300ms → 400ms): ~63%, **worse** than baseline ~65%.
- Larger receiveWindow is not supported by evidence so far; rw350 is the next candidate to test
  properly (24 h averaged), and must be reconciled against the running image tag (ARCHITECTURE §6).

**FreqError / ppm-fc telemetry gap:**
- `rtldavis.py` parser supports `ChannelIdx`/`FreqError` fields (patched to allow EU/US/NZ), but the
  compiled Go binary emits neither (`strings /usr/local/bin/rtldavis` shows no such strings).
- Conclusion: the Python driver supports newer telemetry than the bundled stale Go binary provides;
  `-ppm`/`-fc` tuning cannot be data-driven with this binary.
- **Next investigation:** diff the bundled `src.tgz` rtldavis Go source vs upstream `lheijst/rtldavis`;
  if newer source emits `ChannelIdx`/`FreqError`, rebuild the image from it to enable frequency-error
  telemetry for future tuning.

## Data integrity
- May monthly rain totals were noted as compromised by dev restarts; reconcile against the Davis
  WeatherLink Live gold standard once the rain-spike fix lands — don't compound the error.
