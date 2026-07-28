# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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

---

## [S50] — 2026-07-26 — STATUS resume pointer fixed (micro-session)

One docs commit (PR #73): STATUS.md's `▶ Resume here` line still read "S48 → S49" after S49 had
shipped and closed. No other work.
