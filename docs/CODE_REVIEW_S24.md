# Code-quality review — S24

**Session:** S24 (2026-07-05), building on S23. **Scope (ROADMAP P0.5 / STATUS "Next session
actions" #2):** a thorough read of the driver and its satellites for sloppy, confusing, or
under-commented code — deliver *ranked findings first*, then agree fixes on a branch. **No-Rewrite
(DEC-0014) applies:** every finding below is fixable surgically (a one-liner, a log-level gate, or a
dead-code deletion); none justifies a subsystem rewrite.

This file is the **deliverable-of-record** for the review. It is analysis only — no production code
was changed in producing it. Fixes, once agreed, land as separate commits that reference the finding
IDs here.

**Method:** full read of each file; Python-version-sensitive claims were verified against the actual
Python **3.14.5** interpreter (the container runtime), and "dead code" / "never fires" claims were
verified with repo-wide `grep` and static control-flow tracing. Where a claim needs live runtime
confirmation that isn't reachable from a dev checkout, it is marked **[needs live confirm]**.

Severity: **H** = correctness bug (wrong output, crash, or silently-dead feature) · **M** =
maintainability/efficiency with real impact · **L** = minor/readability.

---

## `rtldavis.py` (1506 lines) — the driver

### H1 · `raw` NameError on the unknown-channel path — **confirmed**
`rtldavis.py:1430-1431`
```python
logerr("unknown station with channel: %s, raw message: %s" % (data['channel'], raw))
```
`raw` is undefined in `parse_raw` (the parameter is `pkt`; `raw` is the only bare, undefined name in
the file). A packet arriving on a channel that matches none of the configured sensors would raise
`NameError` *inside* `genLoopPackets` instead of logging the intended diagnostic — converting a
benign "unknown station" into a driver `WeeWxIOError`/crash. Latent because the path is rare, but
real. **Fix:** `raw` → `pkt`.

### H2 · `pct_good_all` bootstrap deadlock → driver's `rxCheckPercent` is never populated — **confirmed (static); [needs live confirm]**
`rtldavis.py:1006-1007`
```python
if total_max_count > 0 and self.stats['pct_good_all'] is not None:
    self.stats['pct_good_all'] = 100.0 * total_count / total_max_count
```
The only statement that assigns a numeric `pct_good_all` is itself guarded by
`pct_good_all is not None`. But `_init_stats` (line 959) and `_reset_stats` (line 966) both set it to
`None`, and `_reset_stats` runs at the end of **every** archive period (`new_archive_record`). So the
guard is always False → `pct_good_all` is permanently `None` → `new_archive_record` never writes
`event.record['rxCheckPercent']` (line 1025). The driver's native reception metric has been silently
dead. The guard is almost certainly inverted (intended `is None`) or the `pct_good_all` clause should
be dropped so the condition is just `if total_max_count > 0:`.

**Significance:** this plausibly explains *why* the log-scraping reception subsystem in
`weewx_monitor.py` exists at all — the in-driver metric it would otherwise rely on doesn't work.
**Live confirm:** `SELECT rxCheckPercent FROM archive ORDER BY dateTime DESC LIMIT 200;` — expect all
`NULL`. Not reachable from a dev checkout.

### M3 · Debug scaffolding left at INFO in production (the `weewx.log` bloat, DEC-0024 Layer B)
`rtldavis.py:693-694, 880, 1067-1073` — unconditional `loginf(...)` of `RAW_CHANNEL_PAYLOAD`,
`RTLDAVIS_DRIVER_MARKER`, `RAW_RTL_STDERR_SAMPLE`, and *every* line containing `Hop:`/`ChannelIdx:`
(`RAW_RTL_HOP`). This is the ~15 MB log growth flagged in DEC-0024. **Fix:** gate behind the existing
`debug_rtld` flag (via `dbg_rtld`) instead of hard INFO; drop the one-shot marker. Compounds M-A in
the monitor (below), which re-reads the whole log every poll.

### M4 · Dead code — **confirmed (zero callers repo-wide)**
`_fmt` (line 228; also uses py2-only `ord()`, would fail on `bytes` under py3) and `parse_readings`
(line 1094) are never called anywhere in the repo. **Fix:** delete both.

### L5 · Systemic confusing pattern: `@staticmethod` that takes `self`
`DATAPacket.parse_text`, `CHANNELPacket.parse_text`, `ch_to_xmit`, `parse_raw` are declared
`@staticmethod` yet take `self` as the first parameter and are invoked `X.parse_raw(self, pkt)`. It
works (the driver instance is passed explicitly) but is consistently misleading. **No-Rewrite:**
document the convention with a short comment at each site rather than restructuring the call graph.

### L6 · Minor
- `rtldavis.py:1012` — guard `self.stats['pct_good'] is not None` tests the *list* (always truthy),
  not the element `['pct_good'][i]`; the guard is a no-op as written.
- `rtldavis.py:1067` — `_stderr_sample_count` is lazily created with `hasattr` *inside* the hot
  read loop; initialize it once in `__init__`.
- `rtldavis.py:1088` — the `elif lines:` "missed (unparsed)" branch is effectively unreachable
  because `PacketFactory.create` drains `lines` to empty before the loop exits.

---

## `weewx_monitor.py` (409 lines) — USB watchdog + downtime alerts + reception tracking

Overall notably cleaner than the driver: well-commented, secrets sourced from env (DEC-0012
compliant), and the DEC-0024 epoch-dedup logic (`wu_record_key`) is sound and unit-tested.

### M-A · Full-file re-read every 30 s poll
`weewx_monitor.py:82-83, 89-91` — `get_linecount` (`sum(1 for _ in f)`) and `get_new_lines`
(`f.readlines()` then slice) each read the **entire** `weewx.log` on every `POLL` (30 s). Two full
passes over a multi-MB file per poll, and it compounds directly with driver finding M3 (log bloat).
**Fix:** track a byte offset and `seek()` to read only what was appended.

### L-B · Double-read race (minor)
`cur = get_linecount()` is computed, then `get_new_lines` re-reads to EOF (possibly past `cur`), but
`last_line = cur` is stored. Lines appended between the two reads are processed now *and* again next
poll. Mostly masked for reception by the epoch-dedup, but it can double-count service `Published`
hits. Resolved for free by the M-A offset fix.

### L-C · Bare `except:`
`weewx_monitor.py:84, 92, 148` swallow everything, including `KeyboardInterrupt`/`SystemExit`.
Narrow to `except OSError:` (file reads) / `except Exception:` (subprocess).

### L-D · Hardcoded paths
`weewx_monitor.py:9, 10, 78` hardcode `/volume1/docker/...`, unlike the credentials which come from
env. Minor portability nit; make them env-overridable for parity.

---

## Cross-cutting theme

H2 + M3 (driver) and M-A (monitor) are one story: the driver's native reception metric is **dead**
*and* the driver spams the log, which forced a log-scraping reception workaround that must then chew
through the bloated log every 30 s. Fixing H2 could eventually let the monitor read `rxCheckPercent`
from the archive directly instead of tailing text.

---

## Not yet reviewed — Part 2 (pending)

The handoff folds "the uploaders" into scope. Still to read: `owm.py`, `wcloud.py`, `windy.py`,
`ogoxeUploader.py`, `influx.py`, and `loop_json_writer.py`. This section will be filled in before the
review is considered complete.

Also pending from the handoff: per-file SPDX `GPL-3.0-or-later` headers (fold in with the agreed
fixes).

---

## Suggested fix ordering (for discussion — nothing applied yet)

1. **H1** (`raw`→`pkt`) — trivial, self-evidently correct; add a regression test exercising the
   unknown-channel branch.
2. **H2** (`pct_good_all` guard) — fix + a unit test on `_update_summaries`/`_reset_stats` across two
   periods; then live-confirm `rxCheckPercent` starts populating.
3. **M3 / M-A together** — gate the driver's RAW logs behind `debug_rtld`, then switch the monitor to
   incremental reads (the log-bloat cause and its most expensive consumer, fixed as a pair).
4. **M4** dead-code deletion + **L5/L6/L-B/L-C/L-D** cleanups as a low-risk sweep, with SPDX headers.
