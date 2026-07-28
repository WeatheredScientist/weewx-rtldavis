# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S54] — 2026-07-28 — R1 landed: outside-temperature decode is now signed two's complement (DEC-0055); not yet released

Owner approved **R1** from the S53 ops#105 audit; **R2** (`MAX_PLAUSIBLE_TIPS` 60 → 16) held for
further discussion and is untouched.

- **`rtldavis.py`** — the 12-bit digital temperature field is decoded as **two's complement**
  (`(temp_raw - 0x1000) / 10.0` when bit 11 is set), and `0xFF8` joins `0xFFC` as a no-sensor
  sentinel. Unsigned, a −5 °F reading decoded to 404.6 °F (207 °C), tripped the −40…65 °C SensorQC
  bounds, and — since v2.0.9 — **co-rejected the entire frame** (DEC-0054), so an ordinary cold
  snap would have nulled wind + payload every ~30–60 s and saturated the corruption alarm we are
  currently watching. Analog/thermistor branch untouched.
- **Deliberate one-LSB deviation from weewx-meteostick** (DEC-0055): its
  `-(temp_raw ^ 0xFFF)` is *one's* complement — 0.1 °F warm on every negative, maps `0xFFF` and
  `0x000` both to 0.0 °F, and flips the truncation bias at zero. Its two real contributions (the
  field is signed; the `0xFF8` sentinel) are adopted.
- **`tests/test_temp_twos_complement.py`** — 10 new tests: −40 °F frame, the `0xFFF` case that
  distinguishes this from meteostick, both sentinels, a DEC-0054 **co-rejection non-fire** sweep
  (−0.1…−39.9 °F), plus two positive controls (frame-builder round-trip; proof the bounds gate
  really fires on the old unsigned decode). All three plausible regressions **mutation-tested red**.
  Also fixed a real cross-module test-isolation trap: these suites share `sys.modules` and replace
  `weewx.wxformulas` wholesale, so the stub is now additive and resolved through `rtldavis.weewx`
  (the object the driver actually dereferences) rather than `sys.modules['weewx']`.
- **`CHANGES-FROM-UPSTREAM.md`** — two DEC-0034 fork-inventory gaps closed. DEC-0054 (frame-level
  co-rejection, shipped in v2.0.9 at S52) had never been recorded there and is now behavior
  change **11**. The `rtldavis.py` delta was **recounted against the real upstream baseline** —
  fetched from the same `weewx-contrib` `src.tgz` the Dockerfile builds from, which this repo does
  not vendor: **+477 / −88** (1422 → 1811 lines), replacing S37's **+263 / −51**. That figure was
  one commit stale the day it was written (it is the exact count at `cd49214`, and the S37 commit
  recording it also added the fork-identity header). The reproduce recipe now ships next to the
  number, so the next recount is a paste rather than an archaeology session.
- **Upstreaming table** — gained the temp-sign candidate (the prose already claimed 10 was part of
  the intended contribution), and two **stale statuses corrected**: it still read *"draft comment …
  not posted"* and *"not yet offered"* for work that has been live upstream since S38 —
  [lheijst#22](https://github.com/lheijst/weewx-rtldavis/pull/22) and
  [david-lutz#1](https://github.com/david-lutz/weewx-influx2/pull/1) are both OPEN, and the issue #15
  comment was posted 2026-07-13. The table was written at S37 and never re-read after the PRs landed.
- Gates: pytest **111 passed**, `ruff check` clean (0.5.7, DEC-0027), `mypy --ignore-missing-imports
  --no-strict-optional .` clean on 33 files.
- **Not released.** The driver is baked (DEC-0031) → needs an image rebuild + deliberate release,
  deadline **before first frost**. A companion upstream PR belongs alongside lheijst#22.

---

## [S53] — 2026-07-27/28 — ops#105 cross-observable QC audit delivered; archive swept CLEAN; temp sign bug found (no code)

The owner-directed audit ([ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105),
carry-forward of ops#103's "where else could this slip through") delivered as an
[issue comment](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105#issuecomment-5099627052).
Every encoding verified against `rtldavis.py` source (ops#103's *inferred* entries confirmed; its
"rain closed since 07-12" claim corrected — counter deltas ≤ 30 tips = 0.30 in still clear both
`MAX_PLAUSIBLE_TIPS = 60` and the 0.3 in StdQC cap, and a phantom is never reversed).

- **Historical-signature sweep (full archive 2026-05-19 → 07-27, 95,901 rows, pre-correction
  backup): CLEAN.** 13 gust-spike candidates all adjudicated genuine (storm outflow / breeze
  context) except ERR-0004 itself; temp spike-and-return zero ever; humidity spikes all
  pre-SensorQC (known DEC-0029 class); night radiation/UV zero; isolated rain zero. All 5
  rejection events in 31 days of logs cross-checked — sibling fields clean in the archive. **No
  new ERR entries.** Corroboration: ~722 dup frames/day × 1/65536 CRC-pass ≈ 1 in-bounds escape
  per ~90 days — matches the 1 observed in ~4 months.
- **NEW finding (R1, needs-design, pre-winter):** the temp decode is **unsigned**; Davis is two's
  complement (verified vs weewx-meteostick, which also handles a second `0xFF8` sentinel both our
  fork and upstream lack). First sub-0 °F morning → every temp frame decodes ~+400 °F →
  bounds-trips → **DEC-0054 co-rejects the whole frame** (wind + payload nulled, ERROR-pair log
  spam) for the duration of real cold weather. Inherited upstream bug, never fired only because
  the station hasn't seen winter.
- **Recommendations R1–R5** (temp sign fix; `MAX_PLAUSIBLE_TIPS` 60 → 16; wind residual
  accepted driver-side / spike guard is dashboard's; radiation night-ceiling noted-not-built;
  extra-station zero-QC docs note) — all awaiting design agreement, no code this session.
- **v2.0.9 first-days watch:** co-rejection 0 hits (first post-deploy hour); #74 WARNINGs present
  up to the 22:18 recreate, silent after (needs a full-day re-check); soak 15/0/0, reception 81 %;
  no stalls; humidity watch through 07-27 23:14 still unfired; no Dependabot PRs yet.

---

## [S52] — 2026-07-27 — ERR-0004 phantom 39 mph gust: corrected in both stores, frame-level co-rejection shipped as v2.0.9 (DEC-0054)

**The incident (ERR-0004):** at 14:55:50 EDT, during an rxCheckPercent collapse to 13.2%, one
multi-bit-corrupt-but-CRC-valid frame (DEC-0033 class) carried humidity decoding to 144.9% — rejected
by SensorQC bounds — *and* a wind byte decoding to 39 mph from dead calm, which passed (in-spec, and
+16.5 m/s sat under the 20 m/s delta cap). It became the archive interval's gust max and went out to
all ten external sinks. Owner spotted it on the dashboard hours later; dashboard S149 and an
eaglehunt-ops session had already filed [#76](https://github.com/WeatheredScientist/weewx-rtldavis/issues/76)
+ ops#103 with the diagnosis — independently re-verified here (log + code) before acting; every
claim held. Coordinated in real time on #76 (3 comments: pickup → correction landed → release).

- **Correction applied live, both stores, same session (DEC-0025/0032/0037):** archive row
  1785178560 → windSpeed/windDir/windGust/windGustDir/ET/appTemp/windrun all NULL (wview-extended
  schema carries the derived fields in-row), guarded UPDATE + `rebuild-daily`; InfluxDB point
  rewritten minus 7 wind-affected fields with sparse `windGust_qc=1`/`windSpeed_qc=1` (DEC-0099
  contract). Verified via the public /query proxy: day-max gust now a genuine 12 mph. Dashboard's
  ops#104 verification unblocked the same hour. Backup: `weewx.sdb.bak-err0004-20260727`.
- **DEC-0054 — frame-level co-rejection (v2.0.9):** a bounds failure on ANY field now nulls every
  weather field of that frame and skips the rain counter *without* resyncing its baseline; delta
  trips never co-reject. Zero free parameters — explicitly not the parked DEC-0044 coupling filter.
  6 new tests incl. a verbatim replay of the corrupt frame; the old test asserting same-frame
  humidity *survives* a wind bounds failure was inverted (it encoded exactly this gap).
- **Issue #74 closed (bundled):** calm-windDir TTL expiry logs DEBUG when windSpeed is 0.0 (calm is
  Davis semantics, not a fault); WARNING kept for expiry with wind, and an expired windSpeed counts
  as a dropout. Recovery line downgraded symmetrically. 4 tests.
- **BACKLOG pruned:** DEC-0024 bullet (shipped v2.0.8) and RAW_* log bloat (resolved; live log has
  zero RAW_ lines) marked done.
- **v2.0.9 released:** PR #77 → dev (CI green), image built on the NAS from a fresh checkout, pushed
  to Docker Hub `:v2.0.9` + `:latest` (digest `sha256:5eb38850`), prod container recreated from the
  live inspect config (kill→rm→3s→run), `loop_json_writer.py` hot-swapped (`.bak-pre-v2.0.9`),
  live-verified: driver banner `0.20+ws.1`, `sensor_qc True`, records publishing, `current.json`
  writing (calm windDir correctly omitted), soak 14 PASS / 1 WARN (restart-empty reception window) /
  0 FAIL, no startup stall. Rollback: `:v2.0.8` remains on the NAS and Docker Hub.
- **Found in passing: the Dockerfile installed weewx UNPINNED** — this rebuild silently moved prod
  weewx 5.3.1 → 5.4.0 (came up clean, daily summaries fine; 5.4.0's changelog is reporting/tooling
  only — `weectl rest`, skin fixes — nothing touching the driver API, restx, schema, or QC paths).
  Same silent-drift class as S46's unpinned-ruff CI break. **Closed same session (#78):**
  `requirements.txt` pins `weewx==5.4.0` (matching what is verified-live), the Dockerfile installs
  from it, and `.github/dependabot.yml` turns future weewx releases into review PRs — notification
  and deliberate bump, never a blind update. No rebuild needed: the pin equals the running version.

---

## [S51] — 2026-07-26 — Watch items all run: DEC-0053 TTL watch resolved benign, humidity spike still unfired; issue #74 filed

No code changed. All four S50-handoff watch items executed against prod:

**DEC-0053 TTL-expiry watch — fired 10× in its first full day, both patterns benign, watch RESOLVED.**
(a) One real event: `dewpoint_F`/`outHumidity`/`heatindex_F` all expired at 20:09:44 after a genuine
~13-min humidity-packet reception dropout (19:59–20:12 EDT) — the bound doing exactly its job (the
~611 s of tolerated absence is the two caches stacking: DewpointCacher carries the value ≤300 s, then
the writer's own 300 s TTL runs). (b) Seven `windDir` expiries at ~301 s during calm stretches — the
driver *deliberately* sets `wind_dir = None` on calm readings (`rtldavis.py` ~1356), so any ≥5-min
calm expires the cache. Healthy sensor, semantically correct omission, misleading "sensor may be
failing" text. Filed [#74](https://github.com/WeatheredScientist/weewx-rtldavis/issues/74)
(tier:mid): proposed calm-aware downgrade to DEBUG, needs design agreement first (PRINCIPLES §8).
Explicitly NOT a bump-the-TTL case — a longer TTL would serve a stale direction during calm.

**Humidity-spike watch — still unfired.** 2,755 raw samples decoded covering 2026-07-24 00:04 →
2026-07-26 20:42; largest single step −8.7 RH pts, and that across a 4-min reception gap. Nothing
near the 16–37 pt DEC-0044 single-step signature. No SensorQC rejections in today's log at all.

**Soak check: 14 PASS / 1 WARN / 0 FAIL** (WARN = the known 67% reception baseline). Phantom-rainRate
prediction (DEC-0049): 0 qualifying rows in 1,214. No driver stalls in today's log — the S41
startup-race class is now clean across three consecutive restarts (S43, S47, S48).
