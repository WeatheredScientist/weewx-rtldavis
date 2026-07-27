# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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

---

## [S49] — 2026-07-26 — Issue #67 closed: mypy is now a real CI gate

Triaged and fixed the 19 pre-existing mypy errors S48 flagged (`--all-files` run while adding the
pytest hook) but didn't diagnose. Reproduced locally via `pre-commit run mypy --all-files`.

**Two genuine bugs, both in `ops/recover_sweep_results.py`:** the `results` list's `NO_DATA` row
appended an `int 0` for the pct column where every real-data row appends a `float`
(`round(mean_pct, 1)`) — now `0.0`. Separately, the summary loop reused the module-level names `ts`
(a `datetime` from the log-parsing loop) and `pct` (an `int` from the same) for unrelated `str`/
`float` values unpacked from `results` tuples — silent shadowing, not a crash, but genuinely
confusing and exactly the kind of thing mypy is right to flag. Renamed to `_ts` (unused) and
`row_pct`. `results` also gained an explicit type annotation
(`list[tuple[int, int, str, int, int, float, int | str]]`) documenting that its last column is
intentionally either a window count or the `"NO_DATA"` sentinel string — a deliberate design choice,
not something to unify.

**One missing stub, not a bug:** `pressure_service.py` needs `types-requests`. Added to
`.pre-commit-config.yaml`'s mypy hook `additional_dependencies` and to CI's `pip install` step.

**13 py2/py3-compat false positives (`influx.py` 9, `wcloud.py` 4), plus one real
shadowing bug in `influx.py` (3 cascading errors):** the `try: import X / except ImportError: import Y as X` compat shims
mypy statically flags on the branch that never executes under Python 3.14 — suppressed per-line with
`# type: ignore[no-redef]` / `[attr-defined]`, never a blanket per-file ignore, per the issue's own
suggested triage. Separately, `influx.py`'s manual test harness (`if __name__ == "__main__":`) had
`queue = queue.Queue()`, shadowing the `queue` module import with a same-named local — the two
`Module has no attribute "put"` errors were downstream of this one root cause, not independent bugs.
Renamed to `q: queue.Queue = queue.Queue()`.

Verified clean: `pre-commit run mypy --all-files` 19 → 0 errors, ruff clean, pytest 91/91. Removed
`.github/workflows/ci.yml:81`'s `|| true` — mypy failures now actually block CI, mirroring what
#55/DEC-0015 did for pytest via pre-commit at S48. No DEC entry — this closes an enforcement gap,
not a new design decision, same class as #55.

---

## [S48b] — 2026-07-25 — Provenance audit (DEC-0053): loop-JSON cache bounded; #48 and #45 closed

**Issue #48 — closed, DEC-0042 upheld.** A dashboard-side reconciliation found WeatherLink's
install-to-date total only balances if the console *excludes* the 2.56″ of phantom rain we corrected,
and asked whether that undercuts DEC-0042's ISS-side mechanism. It does not — the premise conflates
two classes this repo's data model already separates into independent flags: the 2.56″ is `rain_qc`
(3 points, the **counter**, owned by DEC-0021/0033/0035), while DEC-0042 governs `rainRate_qc`
(33 points, `rain = 0.0` in every one, contributing 0″ to any total). Both classes independently
*require* the console's absence — ERR-0001 was our own wraparound handler adding 128 to a logged
`rain_count=-64` and ERR-0002 a bit-7 flip passing CRC (both downstream of the shared broadcast), and
DEC-0042's mechanism predicts no tip at all. Per INTERFACES §4 the console is our ground truth for
"did the bucket actually tip," and it says no — confirmatory, not contradictory. The reconciliation is
real value as **independent validation that the correction was right** (residual 0.01″), now recorded
in `DATA_ERRATA.md`. DEC-0042 gained a "Challenged and upheld" note so it isn't re-derived.

**Issue #45 — closed as DEC-0053.** Audited every artifact a consumer reads for whether the
assumptions it was produced under travel with it. One real bug, two documented gaps:

- **Fixed:** `loop_json_writer.py`'s cache was **unbounded** — it updated only on non-None values,
  never expired them, and stamped every write with the *current* packet's `dateTime`. A dead or
  SensorQC-rejected sensor emitted its last value forever, indistinguishable from a live reading, on
  the surface the dashboard reads. Same failure `dewpoint_service.py` fixed for the archive path at
  S33/DEC-0022 — learned in one artifact, never propagated to its sibling. Now bounded per-field:
  300 s default (matching DewpointCacher), **2 × `[DavisPressure] fetch_interval`** for
  `barometer_inHg`, since a flat 300 s would have blanked the hourly-fetched barometer for 55 min of
  every hour and regressed Cold-load Fix B. Expired fields are omitted, not frozen, and logged at
  WARNING. 6 new tests + a mutation check confirming they go red against the old cache (91 total).
- **Documented, not fixed:** InfluxDB carries no station identity — and the "one-line" `tags =` fix is
  a trap, since it forks the series key (interface break, needs dashboard coordination). The SQLite
  archive carries no correction flag, so the system of record is less provenanced than the derived
  store. Both in BACKLOG with the reasoning.

`INTERFACES.md` §1 updated — the staleness bound is part of the contract, and a missing field now
explicitly means "no current value," never "value unchanged."

**Deployed and verified in prod** (PR #69 merged, then hot-swapped — `loop_json_writer.py` is MOUNTED
per DEC-0046, so the merge alone would have been inert). Pre-flight drift check confirmed the live
file was byte-identical to the repo's pre-change version; scp'd with md5 matched both ways, pyc
cleared, container restarted (`kill` → `start`, DEC-0008). Live log: `cache TTL 300 s,
barometer_inHg 7200 s` — the barometer TTL correctly derived from the live `fetch_interval = 3600`.
Watched 453 s, past the default TTL: zero expiry warnings, all fields still served, values updating.
Rollback is `loop_json_writer.py.bak-pre-ttl-S48` + restart. No image rebuild; `:v2.0.8` unaffected.

---

## [S48] — 2026-07-25 — pytest hard-gated at commit time; closes issue #55

Investigated [#55](https://github.com/WeatheredScientist/weewx-rtldavis/issues/55) ("closeout
doesn't hard-gate on a green test suite"), filed 2026-07-16 before this repo's closeout skeleton
existed. Found the practical exposure already narrow: `dev` is a protected branch requiring the
`tests`/`lint`/`secret-scan` CI checks before any merge (verified directly this session via PR #65),
so a broken-test commit has no path onto `dev` regardless of whether an agent remembers to run
pytest locally. The one real remaining gap: pytest wasn't part of `.pre-commit-config.yaml` — only
ruff/mypy/secret-scan ran at commit time, which is what DEC-0015 originally intended but never fully
wired up. Added a `local` pytest hook (isolated pre-commit env, `additional_dependencies: [pytest]`,
`always_run: true`) — the suite is all-stdlib so it needs nothing from this repo's `.venv`. Verified
it fires on every commit and passes in isolation. Commented on and closed #55, citing the branch-
protection/CI structure as the actual hard gate, with this as the immediate-local-signal bonus.

(Caught, not fixed, as out of scope: running `pre-commit run --all-files` surfaced 19 pre-existing
mypy errors and trailing-whitespace fixes across `influx.py`/`ogoxeUploader.py`/`weewx.conf.example`
that normal per-commit runs never touch, since pre-commit only checks each commit's own diff.
Reverted those incidental changes — not this session's task.)

---

## [S47] — 2026-07-25 — Backlog + branch cleanup: loopdata.py / reception_service.py removed, rw350/400-test images deleted, stale worktree removed

Cleared four long-parked, "not urgent" backlog items in one session.

**`loopdata.py` (DEC-0005, open since S16).** `user.loopdata.LoopData` was confirmed still absent
from every active `[Engine][Services]` list. Removed the `[LoopData]` config section from the live
`weewx.conf` (backed up first as `weewx.conf.bak-pre-loopdata-cleanup-S47`; a small Python script
found the section by its top-level header and asserted on expected content before writing, rather
than a line-count sed). Recreated `weewx-rtldavis-v2` (`kill` → `rm` → 3 s settle → `run`,
reconstructed from `docker inspect`) without the `loopdata.py` bind mount. Verified live: container
`running`, 6 mounts (down from 7), `weewx.log` publishing archive records and RESTful uploads within
seconds, no `CRITICAL`/stall. `loopdata.py` renamed aside on the NAS to `loopdata.py.removed-S47`
rather than deleted, for rollback.

**`ops/reception_service.py` (found S43).** Confirmed unimported anywhere in the test suite (one
stale comment reference in `tests/test_reception_layer_b.py`, fixed), never `COPY`'d into the
Dockerfile, and its `ReceptionMonitor` service never listed in `weewx.conf`. Deleted from the repo;
the NAS copy renamed aside to `reception_service.py.removed-S47`.

**`rw350-test` / `rw400-test` Docker images (DEC-0048's last piece).** `rw250-test` was retired at
DEC-0048 (S41); the other two ad-hoc `receiveWindow`-sweep tags were left. Confirmed neither backs
any running container (`docker ps -a` showed only `weewx-rtldavis-v2` on `:v2.0.8`) and deleted both
from the NAS. DEC-0048 is now fully closed.

**Stale worktree.** `.claude/worktrees/s46-closeout-amendment` (branch
`worktree-s46-closeout-amendment`, merged via PR #64) removed — same pattern as the 8 worktrees
cleaned up at S41.

No driver/source code changed, no image rebuild, `:v2.0.8` unchanged. Docs updated: BACKLOG.md,
ROADMAP.md, docs/ARCHITECTURE.md, docs/DECISIONS-FULL.md (DEC-0005), docs/STATUS.md.
