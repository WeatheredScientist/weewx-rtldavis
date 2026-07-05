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

**Fix status (S24):** ✅ **H1** (`0929952`), ✅ **H2** (`970c47e`), ✅ **M3 + U3** (`8872947`) — each
with a proven regression test; branch-only, driver fixes await a rebuild + hot-swap.

**Fix status (S25):** ✅ **U1/U2** (`owm.py` RESTThread rebase + `tests/test_owm_post_body.py`),
✅ **U4** (`influx.py` `verify_ssl` opt-out, default verifying), ✅ **M4** (deleted `_fmt` +
`parse_readings`), ✅ **L6** (per-element `pct_good` guard, `_stderr_sample_count` hoist, unreachable-`elif`
note), ✅ **L5** (convention documented at `parse_raw`), ✅ **L-C/L-D/U5** nit sweep, ✅ per-file **SPDX**
headers. ⏳ Still deferred to **S26**: **M-A** (monitor incremental read) + its coupled **L-B**
(double-read race) — both wait for the DEC-0024 Layer A monitor deploy to avoid stepping on the queued
`weewx_monitor.py`.

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

## The uploaders + loop writer (Part 2)

Scanned: `owm.py`, `windy.py`, `ogoxeUploader.py`, `wcloud.py`, `influx.py`, `loop_json_writer.py`.
The three upstream-derived sinks (`wcloud.py`, `influx.py`, `ogoxeUploader.py`) and the two locally
written helpers (`windy.py`, `loop_json_writer.py`) are broadly sound; the one home-grown REST
uploader (`owm.py`) is where the real finding is. **`windy.py` is the reference for the correct
pattern** — it overrides `format_url` + `check_response` and lets `RESTThread` own the retry loop,
which is exactly what `owm.py` throws away.

### U1 · `owm.py` · `run_loop` override discards all RESTThread resilience — **confirmed**
`owm.py:66-107` reimplements the whole thread loop. It accepts `post_interval`, `max_backlog`,
`stale`, `max_tries`, `retry_wait`, `skip_upload` (lines 40-53) and passes them to `super().__init__`
— then **ignores every one of them** because the custom loop does its own `queue.get`/`urlopen`. Net
effect: a single transient network failure **drops the record with no retry** (line 106-107 just logs
and moves on), no post-interval throttling, no stale-record skipping, `skip_upload` inert. **Fix:**
delete `run_loop`/`post_request`/`format_url` and drive the OWM JSON POST through the standard
`RESTThread` overrides (as `windy.py` does), so retries/backoff come for free. Meaningful for an
uploader whose whole job is reliable delivery.

### U2 · `owm.py` · dead code / cruft — **confirmed**
`format_url` (line 58) and `post_request` (61-64) are never exercised once `run_loop` is overridden;
`post_request` computes `record_m` then discards it and carries a garbled comment; `import time`
(line 68) is unused. Remove with U1.

### U3 · `influx.py` · per-record INFO logging in the hot POST path
`influx.py:484, 486, 490` — `get_post_body` runs for **every** record and unconditionally
`loginf`s `Add Bindding Tag = ...` / `Adding Binding Tag` / `tags = ...`. Same log-bloat family as
driver M3 and monitor M-A (see theme below); also `Bindding` is misspelled. **Fix:** drop to
`logdbg` or delete.

### U4 · `influx.py` · TLS verification disabled for https (security, low live impact)
`influx.py:469-476` — `post_request` uses `ssl._create_unverified_context()` for any `https://`
server URL (the `# FIXME: ... instead of this hack` is self-aware). Moot for the current local
`http://` Influx, but if the endpoint is ever pointed at TLS it silently accepts any cert (MITM).
**Fix:** default to a verifying context with an opt-out flag.

### U5 · Minor / cosmetic
- `influx.py:565-573` — `__main__` uses `os.environ['INFLUX_HOST']` as an option *default*, so a
  missing env var `KeyError`s even `--version`/`--help`. Test hook only. Also typos `InluxDfB`.
- `windy.py:25-26` — `__import__('queue').Queue()` inline fallback is an ugly wart; import `queue`
  normally.
- `ogoxeUploader.py:67 vs 79` — contradictory comments about whether `server_url` comes from
  `get_site_dict`; line 68 debug-logs a value the code says isn't there (logs `None`).
- `wcloud.py` — mature upstream (Matthew Wall 2014), proper pattern, **masks the API key in debug
  logs** (good). Only nits: it documents the WeatherCloud `-32768` "sensor present but broken"
  null-convention (lines 20-24) but `format_url` just omits `None` values instead; and `temp10`
  maps to the non-standard `heatingTemp4`. Low value, upstream — leave alone.
- `loop_json_writer.py` — clean; atomic tmp+rename write, well-commented sparse-field cache. No
  action. (Only theoretical: `data['dateTime']` can be `None` if a packet lacks it.)

**Out of scope this pass:** `pressure_service.py` and `dewpoint_service.py` are *services*, not
uploaders; `dewpoint_service.py`'s stale-substitution issue is already tracked as DEC-0022 (a later
session), so it is deliberately not re-reviewed here.

---

## Cross-cutting theme

**The dead metric + the log-bloat trio.** H2 + M3 (driver), M-A (monitor), and U3 (influx) are one
story. The driver's native reception metric is **dead** (H2) *and* the driver — plus the influx sink
— spam the log at INFO on every packet/record (M3, U3). That forced a log-scraping reception
workaround (`weewx_monitor.py`) which must then re-read the whole bloated log every 30 s (M-A).
Fixing the INFO-spam and H2 together shrinks the log, cheapens the monitor, and could eventually let
the monitor read `rxCheckPercent` from the archive directly instead of tailing text.

Also pending from the handoff: per-file SPDX `GPL-3.0-or-later` headers (fold in with the agreed
fixes).

---

## Suggested fix ordering (for discussion — nothing applied yet)

1. **H1** (`raw`→`pkt`) — trivial, self-evidently correct; add a regression test exercising the
   unknown-channel branch.
2. **H2** (`pct_good_all` guard) — fix + a unit test on `_update_summaries`/`_reset_stats` across two
   periods; then live-confirm `rxCheckPercent` starts populating.
3. **M3 / U3 / M-A together** — gate the driver's RAW logs behind `debug_rtld` and drop influx's
   per-record `loginf`s (the log-bloat sources), then switch the monitor to incremental reads (its
   most expensive consumer). Fix the cause and effect as one unit.
4. **U1 / U2** — re-base `owm.py` on the standard `RESTThread` overrides (model it on `windy.py`) so
   it regains retry/backoff; delete the dead `format_url`/`post_request`/`import time`.
5. **U4** — restore TLS verification in `influx.py` with an opt-out flag.
6. **M4** dead-code deletion + **L5/L6/L-B/L-C/L-D/U5** cleanups as a low-risk sweep, with per-file
   SPDX `GPL-3.0-or-later` headers.
