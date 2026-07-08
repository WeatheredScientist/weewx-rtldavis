# Backlog — weewx-rtldavis

Unordered ideas and durable findings not yet scheduled. Scheduled work lives in ROADMAP.md;
in-flight work in docs/STATUS.md. Carried forward from the pre-governance NAS `BACKLOG.md`; the
open items from the retired root `cleanup_backlog.md` were folded in here (S27, S23 tail).

## Open ideas
- Reception improvement beyond ~70% (noise-floor limited at ~150 ft through walls).
- Windows/macOS FHSS investigation (Docker Desktop USB passthrough findings for the README).
- ESP32 secondary sensor node — lightning (AS3935), pressure (BMP390), air quality (SEN55);
  solar-powered (parts shopping list done).
- Blitzortung lightning integration (System Blue — the detection-network route; longer term).
- Remove vestigial `loopdata.py` mount + `[LoopData]` section (DEC-0005).
- Rotate the exposed WU API key; store it in `monitor.env` as an env var, not inline (DEC-0012).
- Set `STATION_NAME` in the NAS `monitor.env` — the monitor's alert/summary emails currently fall back
  to the default "My PWS" (env var unset), so they're unbranded. Cosmetic, one-line fix (observed S27).
- Verify OWM (OpenWeatherMap) measurements propagate into their API over time — a post-integration
  sanity check that the uploader's values actually land.
- Long-term stability watch (uptime / reception drift / memory) — no formal monitor yet.
- **Reception-metric over-count (DEC-0024, root cause confirmed S21):** the daily RF-Reception email
  reads ~150% because `weewx_monitor.py` counts `Wunderground-RF: Published` *log lines* while the
  driver publishes freqError freq-hop channel packets as extra dataless loop packets (~1.66×). Fix
  Layer A (monitor: count unique record epochs) is the likely first move — safe, monitor-only,
  reversible. Layer B (driver: stop publishing dataless freqError packets + disable `RAW_*` debug
  logging) is deeper and needs a prod plan. See DEC-0024.
- **`weewx.log` bloat / rotation:** the driver's `RAW_RTL_*`/`RAW_CHANNEL_PAYLOAD` `loginf` debug
  lines flood the log (15 MB / 122 k lines observed S21). Disable in prod and/or add log rotation;
  the monitor re-reads the whole file each poll, so an unbounded log also drags the monitor. Ties
  into DEC-0024 Layer B.

## Durable RF findings (from 2026-06-01 tuning sweeps — keep; these guide P2)

**CLI timing sweep (baseline, -ex 25/50/75/100, -maxmissed 25, combos):**
- All clustered ~63–66%; no material improvement over baseline.
- `-maxmissed 15` caused repeated 0/24 windows — **do not use**.

**receiveWindow:**
- rw400-test (300ms → 400ms): ~63%, **worse** than baseline ~65%.
- Larger receiveWindow is not supported by evidence so far; rw350 is the next candidate to test
  properly (24 h averaged), and must be reconciled against the running image tag (ARCHITECTURE §6).

**FreqError / ppm-fc telemetry gap — SUPERSEDED by live evidence (S21):**
- ~~The compiled Go binary emits neither `ChannelIdx` nor `FreqError`.~~ **Contradicted:** the
  *running* binary emits **both** — live `weewx.log` shows `ChannelIdx:37 … FreqError:2765
  Transmitter:4` (S21, DEC-0024). Either the deployed binary changed since this finding, or the
  original `strings` check was against a different/stale binary. **Re-verify** `strings
  /usr/local/bin/rtldavis` in the live container and reconcile with the running image tag
  (rw250-test) — this matters because the emitted `ChannelIdx`/`FreqError` is what drives the
  DEC-0024 reception over-count.
- Upside if confirmed genuine: `-ppm`/`-fc` tuning *can* now be data-driven (freqError telemetry is
  live). Downside: those same channel packets are being published to WU as dataless loop packets
  (DEC-0024 Layer B).
- **Next investigation (still open):** diff the bundled `src.tgz` rtldavis Go source vs upstream
  `lheijst/rtldavis` to understand which version is actually deployed.

## Data integrity
- May monthly rain totals were noted as compromised by dev restarts; reconcile against the Davis
  WeatherLink Live gold standard once the rain-spike fix lands — don't compound the error.
- **[PRIORITIZED — owner, S30] Bad-packet root cause for temp/humidity/radiation/UV spikes.** Recent
  temperature spikes were patched with *filtering bandaids* (coarse `[StdQC]` MinMax bounds, e.g.
  `outTemp = -40, 120 degF`, which pass any in-range spike + the DewpointCacher carry-forward that
  masks — not detects — bad reads). The likely **root cause is bad RF packets**, the same failure class
  as the rain 64/128 decode glitch — but rain got a proper packet-level plausibility filter
  (`rtldavis.py:211`, null-on-rejection per DEC-0006) while temp/humidity/radiation/UV never did. The
  real fix is a **decode-layer plausibility/delta filter** for those sensors (reject implausible
  per-packet jumps → honest null, don't clamp/substitute), which also unblocks converting them from
  carry-forward to honest-null (ties into **DEC-0022** sensor-QC hardening). **Make this a dedicated
  future session** and **pick a model suited to deep RF-decode root-causing** (Opus, high reasoning) —
  it's investigation-heavy (capture raw packets around a spike, characterize the corruption), not a
  quick patch. Do after v2.0.3 ships.
  - **Observed instance (2026-07-05, S30):** a **201 mph** wind spike flashed on the live dashboard
    gauge (owner screenshot). Confirmed **not persisted** — archive DB + InfluxDB stayed clean; only the
    real-time loop-JSON feed showed it. Two concrete findings for this session: (1) **the live gauge
    bypasses the wind filter** — `LoopJsonWriter` is a `data_service` and runs *before* `DewpointCacher`
    (a `process_service`), so `loop-data.txt` gets the raw packet; the fix belongs at the **driver/decode
    layer** (a wind plausibility clamp like the rain filter) so *all* consumers are covered. (2) **possible
    unit mismatch:** `MAX_WIND_DELTA = 75.0` is commented as mph but the packet `windSpeed` is likely m/s
    (driver stores `wind_speed_ec * MPH_TO_MPS`), which would make the delta filter far too lenient
    (only rejecting jumps > 75 m/s ≈ 168 mph). Verify + fix the units.
