# Changes from upstream

**Status:** Source of truth for what this project changed in code it did not write.
**Last updated:** 2026-09-04 (S123)

This project is a Docker distribution of a **modified** Davis/rtldavis receiver stack. It is not
stock upstream, and several of the files it ships are other people's work with our patches on top.
This file records every one of those divergences: what we changed, when, why, and whether it belongs
upstream.

It exists for three reasons:

1. **GPLv3 section 5(a)** requires a modified work to "carry prominent notices stating that you
   modified it, and giving a relevant date." Each patched file now carries that notice in its header;
   this file is the long-form version.
2. **Honesty.** Until S37 the driver logged `driver version is 0.20` — the stock upstream version —
   while carrying a rain filter, a sensor plausibility filter and five bug fixes that do not exist
   upstream. Anyone debugging from our logs (including us, and including anyone we try to help on an
   upstream issue) was being misled. It now logs `0.20+ws.5`.
3. **It is the checklist for shrinking the fork.** Every row below is either something to upstream or
   something to justify keeping. A fork with no inventory only grows.

## Provenance

We build from Vince Skahan's repackage, not from Luc Heijst's repository directly. The chain is
verified from `Dockerfile` (which fetches `weewx-contrib/weewx-rtldavis/src.tgz` and installs
`david-lutz/weewx-influx2`):

| Component | Chain |
|-----------|-------|
| Go decoder | [bemasher/rtldavis](https://github.com/bemasher/rtldavis) → [lheijst/rtldavis](https://github.com/lheijst/rtldavis) → bundled in `weewx-contrib` `src.tgz` → **patched by us** ([`patch/rtldavis-dupgate.patch`](patch/rtldavis-dupgate.patch), [DEC-0135](docs/DECISIONS.md)) |
| Driver | [matthewwall/weewx-sdr](https://github.com/matthewwall/weewx-sdr) + [weewx-meteostick](https://github.com/matthewwall/weewx-meteostick) → merged by **Luc Heijst** into [weewx-rtldavis](https://github.com/lheijst/weewx-rtldavis) v0.20 → repackaged by **Vince Skahan** ([weewx-contrib/weewx-rtldavis](https://github.com/weewx-contrib/weewx-rtldavis)) → **patched by us** |
| InfluxDB uploader | [matthewwall/weewx-influx](https://github.com/matthewwall/weewx-influx) → [david-lutz/weewx-influx2](https://github.com/david-lutz/weewx-influx2) (InfluxDB 2.x port) → **patched by us** |
| WeatherCloud uploader | [matthewwall/weewx-wcloud](https://github.com/matthewwall/weewx-wcloud) → us (unmodified except an SPDX tag) |
| OgoXe uploader | weewx 5.2 `restx.py` (Tom Keffer) → smeisens/weewx-wundergroundlike → OgoXe developers / Sigi Meisenbichler / Vince Skahan → **patched by us** |
| USB / SDR | [steve-m/librtlsdr](https://github.com/steve-m/librtlsdr), [jpoirier/gortlsdr](https://github.com/jpoirier/gortlsdr) → us (unmodified) |
| Wind EC table | **kobuki** (`calc_wind_speed_ec`), via Luc's driver |

Everything above is GPLv3 or compatible, and every original copyright notice is intact. We are
downstream of a lot of people's unpaid work, and this project would not exist without it.

**We are not a GitHub fork of the driver, deliberately.** This repository is a *distribution* — a
Docker image, a compose file, uploaders, services and ops tooling — that happens to carry a patched
driver. To contribute upstream we fork `lheijst/weewx-rtldavis` separately and send one focused pull
request, rather than asking anyone to swallow our whole divergence.

## Versioning

Patched upstream files carry a [PEP 440 local version](https://peps.python.org/pep-0440/#local-version-identifiers)
suffix: upstream's base version, `+ws`, our revision.

| File | Upstream version | Ours |
|------|------------------|------|
| `rtldavis.py` | `0.20` | `0.20+ws.5` |
| `influx.py` | `0.20` | `0.20+ws.1` |

The suffix sorts after the base version and is unambiguous about its parent. `rtldavis.py` also logs
`(fork of lheijst 0.20, patched by WeatheredScientist -- not stock upstream)` at startup, which
doubles as the canary for [DEC-0031](docs/DECISIONS.md) (stock upstream cannot print that line, so if
you see it, the baked driver is the one running).

---

## `rtldavis.py`

Base: `weewx-contrib/weewx-rtldavis` `src.tgz` (Luc Heijst v0.20, plus Skahan's 2025-12-20
`re.compile` deprecation patch). Delta: **+1204 / −166 lines** (1422 → 2460 lines), recounted
2026-09-04 (S123) — includes DEC-0135's driver-side repeat counters (`dedup_key`, `repeat_count`,
`duplicate`) and #317's slot-count `rxCheckPercent` denominator (PR #319), both landed since the
prior S97 count (**+815 / −149**, 1422 → 2088 lines).

The baseline is not vendored here — the Dockerfile fetches it at build time — so recount it rather
than trusting this number:

```sh
curl -sL -o /tmp/src.tgz https://github.com/weewx-contrib/weewx-rtldavis/raw/refs/heads/main/src.tgz
tar -C /tmp -zxf /tmp/src.tgz src/weewx-rtldavis/bin/user/rtldavis.py
git diff --numstat --no-index /tmp/src/weewx-rtldavis/bin/user/rtldavis.py rtldavis.py
```

Diff `bin/user/rtldavis.py`, **not** the sibling `rtldavis.py.dist` — the `.dist` is Skahan's
pre-patch copy, so it reports a delta that includes his `re.compile` fix as if it were ours. The
figure this replaces (**+263 / −51**, S37) was already one commit stale when written: it is the
count at `cd49214`, and the S37 commit that recorded it added the fork-identity header itself.

### Bug fixes (these belong upstream)

| # | Change | Date | Why |
|---|--------|------|-----|
| 1 | **Rain-counter wraparound** — `rain_delta_tips()` | 2026-07-04 | Upstream treats *any* negative counter delta as a 127→0 wraparound and adds 128. A corrupt reading that produces a small negative delta (e.g. −64) therefore becomes **+64 tips of phantom rain**. Three confirmed events on this station, one of them a phantom 1.28 in — larger than the world 1-minute rainfall record. Only a large negative delta (near −128) is a real wraparound; anything else is rejected as a glitch and returns NULL. [DEC-0021] |
| 2 | **windDir never populated in one branch** | 2026-07-04 | In `parse_raw`, `wind_dir_vue` / `wind_speed_ec` / the `data['wind_*']` assignments are indented *inside* the `else:` of the direction decode. When the other branch is taken, wind speed and direction are simply never written to the packet. De-indented so both branches populate them. |
| 3 | **`NameError` on unknown channel** | 2026-07-05 | The unknown-station handler logs `raw`, which is not defined in that scope — so the error path meant to report a bad packet crashes instead. Now logs `pkt`. |
| 4 | **`rxCheckPercent` was permanently dead** | 2026-07-05 | `pct_good_all` is only computed `if total_max_count > 0 and self.stats['pct_good_all'] is not None`, but `_init_stats()`/`_reset_stats()` set `pct_good_all = None` every archive period — so the guard can never pass and the driver's own reception metric is never populated. Separately, `self.stats['pct_good']` (a list) was compared against `None` instead of `pct_good[i]`, which is always truthy. |
| 5 | **Per-packet logging at INFO** | 2026-07-05 | `RAW_CHANNEL_PAYLOAD`, `Hop:` and `ChannelIdx:` lines were logged at INFO on every frequency hop, flooding `weewx.log`. Moved behind `debug_rtld` levels. |
| 10 | **Outside temperature decoded UNSIGNED** — `parse_raw`, message type 8 | 2026-07-28 | Davis encodes the 12-bit digital temperature as **two's complement**; upstream divides the raw value by 10 with no sign handling, so every sub-0 °F reading decodes to ~+400 °F. On this station that trips the SensorQC bounds and (since DEC-0054) co-rejects the whole frame, i.e. real winter reads as RF corruption. Upstream also lacks the second no-sensor sentinel `0xFF8` that the sibling weewx-meteostick driver checks; both are fixed here. We use `temp_raw - 0x1000`, **not** meteostick's `-(temp_raw ^ 0xFFF)` — the latter is one's complement and is 0.1 °F warm on every negative reading. [DEC-0055] |

| 12 | **Killed child processes are never reaped** — `ProcManager` | 2026-08-11 | `startup()` and `shutdown()` kill rtldavis by `pidof` + `SIGKILL` and never `wait()`; the engine builds a fresh `ProcManager` on every `WeeWxIOError` retry, so no instance holds a handle to its predecessor's corpse. Every stall-respawn cycle therefore leaks one zombie — three stacked under a single weewxd were forensically captured on 2026-08-11. Spawned children are now registered module-wide and reaped (`poll()`) on shutdown and before each startup. Any user of the stock driver whose RF drops long enough to trip the 150 s stall watchdog accumulates zombies the same way. |
| 14 | **Four public-facing CLI/config bugs** — `default_stanza`, `ProcManager.startup()`, the weewx-version gate, `--action show-packets` | 2026-08-20 | The shipped config template's `cmd =` line carried a literal, unsubstituted `[options]` token; a new user accepting it as-is ships that token into `weewx.conf`, and Go's `flag.Parse()` stops at the first non-flag argument, silently discarding the auto-appended `-tf`/`-tr` and falling back to 868MHz EU instead of 915MHz US. `startup()` split the command line on `cmd.split(' ')`, breaking on a double space or a quoted, space-containing path. The weewx-version gate compared `weewx.__version__ < "3"` as a bare string — lexicographic, not numeric; `"10.0.0" < "3"` is `True` in Python. `--action show-packets` crashed on first use: `get_stderr()`'s expected empty-list queue-timeout yield raised `IndexError`, and `get_stdout()`'s flat list of decoded strings was indexed like `get_stderr()`'s list-of-lists, raising `AttributeError`. |
| 15 | **Three more decode-path bugs** — `transm_to_store` rotation, legacy v12 `freqError`, `pct_good` storage | 2026-08-20 | `transm_to_store` (which transmitter's `freqError` gets stored, meant to rotate every 2 days) was computed once before `genLoopPackets`'s `while` loop and never recomputed inside it — the rotation only ever happened across a process restart. The legacy v12 `freqError` decode (older rtldavis binaries) has no `Transmitter` field to gate storage on, unlike v13 — with more than one active transmitter it silently mixed transmitters' data into the same fields; now refused when `tr_count > 1`. Per-transmitter `pct_good` storage tested `self.sensor_map[k] in data` where `data` had been rebound from the packet dict to a plain string (`'pct_good_%s' % tr`) — substring containment, not the intended equality; harmless with the shipped default `sensor_map` but silently wrong on a plausible user typo or an empty-string value. |
Numbers 1–4, 10, 12, 14 and 15 are real defects in upstream that any US Davis user hits — 10 bites
any cold-climate user of the stock driver. They are the intended content of an upstream
contribution (see [Upstreaming](#upstreaming) below).

### Behavior changes (ours; would need discussion upstream)

| # | Change | Date | Why |
|---|--------|------|-----|
| 6 | **SensorQC** — decode-layer plausibility filter | 2026-07-08 | Same failure class as the rain glitch, applied to temperature / humidity / wind / UV / radiation: sensor-spec bounds plus a per-reading delta check, at the single choke point (`_data_to_packet`) so every consumer sees vetted data. Rejected values become NULL and log `rejecting implausible value`. Configurable (`sensor_qc`, `qc_<field>_max_delta`). [DEC-0029] |
| 7 | **Calm-air wind gate** | 2026-07-04 | Raw wind speed ≤ 2 with direction 0 is the 6410 hall-sensor floor, not wind. Record 0 speed and a **null** direction instead of a false "2 mph from due north" that pollutes wind roses. |
| 8 | **freqError stored for US and NZ** | 2026-07-04 | Upstream stores frequency-error statistics only when `frequency == 'EU'`. We store for `EU`, `US` and `NZ` — the data is just as useful on 915 MHz, and this is a 915 MHz station. |
| 9 | Lint / dead code | 2026-07-08 | Dropped unused imports (`timegm`, `fnmatch`, `string`), the dead `_fmt()`, and the unused `parse_readings()`. Bare `except:` → `except Exception:`. [DEC-0027] |
| 11 | **Frame-level co-rejection** — a bounds failure condemns the whole frame | 2026-07-27 | Extends 6, which vetted each field independently — so a frame carrying *positive proof* of corruption could still have its other fields trusted. On 2026-07-27 one CRC-valid frame decoded humidity to 144.9 %RH (out of spec, rejected) and a wind byte to 39 mph from dead calm (in spec, under the delta cap, accepted) — the phantom became the archive interval's gust max and went out to ten external networks (ERR-0004). Every weather field rides the same 8-byte frame, so a **bounds** failure on any one of them now nulls all of them (`FRAME_WEATHER_KEYS`), skips the rain counter *without* resyncing `last_rain_count`, and moves no delta baselines. Diagnostics (battery flags, supercap, freqError, `pct_good`) deliberately survive: they describe the link, not the weather. A **delta** trip never co-rejects — a large step can be genuine weather; an impossible value cannot. Zero fitted parameters, so nothing can drift. Shipped in v2.0.9 (S52). [DEC-0054] |

| 13 | **Stall/drought self-classification** — `STALL DIAGNOSIS` + `DATA DROUGHT` log lines | 2026-08-11 | Seven sessions (S67–S73) could not tell outage classes apart after the fact: a mute child (process/USB fault), a child emitting but decoding nothing (RF-quiet), and genuine reception collapse all looked identical in the logs, and USB resets were fired blind at all three. The driver now counts raw stderr lines and hop-only packets since the last real data packet: the 150 s stall raise is preceded by a `STALL DIAGNOSIS` line (raw count 0 = mute; >0 = emitting), and a paced `DATA DROUGHT` line covers the RF-quiet case, which never trips the stall watchdog because hop packets reset it. Plus a 10-line stderr tail via `drain_stderr()` at every stall. |
| 17 | **Hot swap of `-gain` / `-ex` via a watched control file** — no weewx or container restart | 2026-08-26 | Both are startup-only CLI flags on the Go binary, so upstream's only way to change them is a full restart; campaign work paid a 600 s settle window and a restart transient per swap. Opt-in via `hotswap_control_file` (unset = off, so stock behavior is unchanged). The driver polls that path about every 10 s at the top of `genLoopPackets`, and on an mtime change respawns the child with the new flags via the `shutdown()`/`startup(cmd, …)` path that already existed. **The control file accepts only bounds-checked `gain` (0–496) and `ex` (0–1000) integers, never a command string** — `cmd` reaches `shlex.split()` → `Popen`, so a raw-command channel would be arbitrary code execution for anything able to write that path. A swap resets the stall-watchdog counters and widens the threshold to 240 s until the first packet, because a respawned child restarts its radio init period (US: 133 s) and the normal 150 s watchdog — whose timer a respawn does *not* reset — would otherwise tear the driver down mid-init. Plus rollback to the last known-good command on a failed startup, an atomic ack file recording the measured respawn gap, and the control file honored at init so a restart cannot silently revert a swapped value. [DEC-0117] |
| 16 | **SensorQC bounds extended to the extra-sensor fields and `rain_rate`** | 2026-08-20 | `temp_1`/`temp_2`/`humid_1`/`humid_2` and `rain_rate` were listed in `FRAME_WEATHER_KEYS` (co-rejected when a frame is corrupt) but absent from `SENSOR_QC_DEFAULTS` — a corrupted reading on any of them could never trigger its own bounds rejection, only ride along on some other field's. Extended to match `temperature`/`humidity`'s bounds (`temp_1`/`temp_2`/`humid_1`/`humid_2` share the identical decode expression as those fields) and `weewx.conf.example`'s existing `StdQC` `rainRate` backstop (0–16 in/h) for `rain_rate`. Dormant on this station (single ISS, no `temp_hum` channel), but a real gap for other users' multi-transmitter or temp/humidity-extension configs. |
### Why these filters exist: the corruption mechanism

Items 1 and 6 both exist because **corrupt sensor readings arrive with a valid CRC**. The cause is now
confirmed on this station (S37, [DEC-0035]) and it is a receiver artifact, not weather and not the
transmitter:

**The Go demodulator sometimes decodes a single RF burst twice.** A 2-hour census found **61 frames
that arrived 1.4–10 ms (median 2.0 ms) after a byte-identical frame** — roughly **722 per day**. A Davis
ISS transmits every ~2.8 s and physically cannot transmit twice 2 ms apart, so the receiver
manufactured the second copy. This reproduces the fingerprint LloydR reported in upstream issue
[#15](https://github.com/lheijst/weewx-rtldavis/issues/15) (his gap was 262 µs; ours is ~2 ms — same
class, different SDR timing).

The path from there to a bad reading:

1. The demodulator double-decodes. Observed ~722/day, and that is a **lower bound**.
2. The second decode is a marginal re-detection, and sometimes carries bit errors.
3. A **corrupted** copy is no longer byte-identical, so Go's exact-equality dedup
   (`seen == lastRecMsg`, `main.go` ~L394) does not catch it.
4. It must pass CRC to be emitted. Most fail and are dropped **silently and invisibly** inside the Go
   binary (`protocol.go` ~L218, *"If the checksum fails, bail"*) — which is why the observed count only
   includes copies clean enough to be byte-identical.
5. The ~1-in-65536 that passes CRC by chance reaches the driver as a **valid-looking packet full of
   garbage**. That is the phantom rain, the 25.6 %RH humidity steps, the UV 16.29 under overcast.

So CRC is not a defense, the dedup is not a defense, and a decode-layer plausibility check is the only
one available at this layer. That is the standing justification for both filters. Anyone proposing
"just trust the CRC" should be pointed here.

Run the census yourself: `ops/find_duplicate_frames.py` (needs `debug_rtld >= 1` and the `user` logger
at DEBUG). Note the warning in its docstring — an earlier version of that script reported a confident
**zero** because it read the driver's post-dedup `data:` lines, from which Go had already removed every
duplicate. Do not trust a null from an instrument you have not proven can see a positive.

---

## `rtldavis` (the Go demodulator) — `patch/rtldavis-dupgate.patch`

**A new kind of divergence for this repo: a fork of the Go binary's source, not of a Python file.**
The demodulator is not vendored here — `Dockerfile` fetches `src.tgz` from
`weewx-contrib/weewx-rtldavis` at an **unpinned `refs/heads/main`** and builds it. Our change ships
as a tracked patch applied during the build, so the divergence stays one reviewable file.

**What it changes (DEC-0135):** the duplicate-packet filter compared payload bytes with no time
bound, so a payload the transmitter **re-sent one loop period later** was dropped without hopping,
and the pending timer booked the received packet as `packet missed`. Measured live: ~27% of all
transmissions, holding `rxCheckPercent` at ~73% on a ~99% link. The patch gates the drop on
`-dupwindow` (default 500 ms — above the same-burst re-decode cluster at ~2 ms, below the shortest
loop period of 2.5625 s) and logs the survivors as `repeat packet:`.

**Belongs upstream** — it is not station-specific: any Davis station whose transmitter re-sends
unchanged payloads has been mis-reporting reception the same way. Draft lives in `docs/upstream/`
(gitignored); see `docs/UPSTREAM-THREADS.md`.

**Maintenance note:** because the tarball is unpinned, the patch is also a tripwire. It is applied
with `--batch --forward` and followed by a `grep -c dupwindow` assertion, so a build **fails loud**
rather than silently producing an unpatched binary if upstream's source moves.

**GPLv3 §5(a) notice: not yet added to `main.go` itself.** The patch's `From:`/`Subject:` header
identifies the fork, and the added code comments explain the change, but unlike `rtldavis.py`
(which logs a fork-identity line at startup) nothing in the patched binary states outright that it
carries a modification. `main.go`'s existing `log.Printf` startup line does now print `dupWindow=%d`
alongside the other flags, which at least surfaces the new flag — but that is not the same as a
"you modified this, on this date" notice. Tracked as
[#327](https://github.com/WeatheredScientist/weewx-rtldavis/issues/327) rather than patched here:
it is a Go source change to a file that is not vendored in this repo, and belongs with a
build/deploy verification pass, not a docs-only session.

## `influx.py`

Base: `david-lutz/weewx-influx2` (itself a fork of `matthewwall/weewx-influx` for InfluxDB 2.x).
Delta through item 5: **+33 / −14 lines**; item 6 (2026-08-21) adds roughly 64 more, not
re-measured against true upstream here — the number above predates it and is left as historical
rather than guessed at. The Dockerfile installs the upstream extension and then copies our patched
file over it.

| # | Change | Date | Why |
|---|--------|------|-----|
| 1 | **`e.read.decode()` → `e.read().decode()`** | 2026-07-04 | Missing parentheses. `handle_exception` raises `AttributeError` on the bound method instead of reporting the HTTP error body — so the code that exists to explain an upload failure fails itself. Real bug, one character class. |
| 2 | **TLS verification on by default** | 2026-07-04 | `post_request` unconditionally used `ssl._create_unverified_context()` for any `https` server_url — certificate verification silently off, upstream's own comment calling it a hack. Now verifies by default; `verify_ssl = false` restores the old behavior for self-signed or internal endpoints. |
| 3 | **CLI `KeyError` when env vars unset** | 2026-07-04 | `os.environ['INFLUX_HOST']` (and `_ORG`, `_TOKEN`) are read at option-parse time, so `--help` crashes with `KeyError` unless all three are exported. Now `os.environ.get()`. Also fixed the `InluxDfB` help-text typos. |
| 4 | **Per-record logging at INFO** | 2026-07-05 | `loginf("Add Bindding Tag = ...")` and `loginf("tags = ...")` fire on every record. Demoted to `logdbg`. |
| 5 | **`distutils.StrictVersion` removed** | 2026-07-04 | `distutils` is gone in Python 3.12+; this image runs 3.14. Replaced with a tuple compare. |
| 6 | **NAS-LEASE courtesy yield (opt-in)** | 2026-08-21 | `InfluxThread` gains a `lease_dir` param (default `None`, off unless `weewx.conf` sets it) and a thin `skip_this_post` override: while another tenant's `NAS-LEASE.md` lease is held and unexpired, `post_interval` rises from its configured value to 1800s (safe per DEC-0092's own data-integrity analysis: prod runs `stale=None`/`max_backlog=1,000,000`, so a 30-minute deferral queues ~30 records against a million-record cap and loses none). Any lease-file read/parse failure, or weewx's own held lease, is treated as "not held" — fails toward normal operation, never toward silently slowing our own uploads. Design: DEC-0099/DEC-0104; build: DEC-0111. |

Items 1, 2, 3 and 5 are unambiguous upstream bugs. Item 2 is a security fix. Item 6 is original functionality, not an upstream-divergence fix.

---

## `ogoxeUploader.py`

Base: OgoXe uploader v1.0.1 (OgoXe developers / Sigi Meisenbichler / Vince Skahan, derived from
weewx 5.2 `restx.py`).

| # | Change | Date | Why |
|---|--------|------|-----|
| 1 | Misleading debug log | 2026-07-05 | `log.debug` reported `_ambient_dict.get('server_url')`, a key that is never set — the URL is the hardcoded `OGOXE_API_URL` constant — so it always logged `None`. Now logs the URL actually used. |
| 2 | SPDX tag | 2026-07-05 | Added `SPDX-License-Identifier`. |

## `wcloud.py`

Base: `matthewwall/weewx-wcloud`. **Unmodified** apart from adding an `SPDX-License-Identifier` line.
Recorded here for completeness, since even that is technically a modification.

---

## Not forks — our own work

These are original to this project (GPLv3, same as the stack they plug into) and are not derived from
an upstream file: `dewpoint_service.py`, `pressure_service.py`, `loop_json_writer.py`, `owm.py`,
`windy.py`, `weewx_monitor.py`, everything in `ops/` and `tests/`, the `Dockerfile`, `entrypoint.sh`
and the compose file. `owm.py` and `windy.py` follow the weewx `RESTThread` pattern
([DEC-0007](docs/DECISIONS.md)) but were written here.

---

## Upstreaming

The goal is for this list to get **shorter**. Standing policy:

- **Fork `lheijst/weewx-rtldavis` separately** for contributions. This repository stays a normal repo
  (a distribution), not a GitHub fork of the driver.
- **One focused pull request per fix**, not one that dumps our whole divergence on a maintainer.
- Start with the rain-counter wraparound (`rtldavis.py` #1). It is the highest-impact defect, it has
  three confirmed events and a unit test behind it, and upstream issue #15 has three users reporting
  the same symptom class since 2022.

| Candidate | Where | Status |
|-----------|-------|--------|
| Rain-counter wraparound | `lheijst/weewx-rtldavis` | **[PR #22](https://github.com/lheijst/weewx-rtldavis/pull/22) OPEN** since 2026-07-13 (S38); the [issue #15 comment](https://github.com/lheijst/weewx-rtldavis/issues/15#issuecomment-4960224128) went up the same day, owner-approved |
| windDir branch bug | `lheijst/weewx-rtldavis` | Not yet offered |
| `NameError` on unknown channel | `lheijst/weewx-rtldavis` | Not yet offered |
| `rxCheckPercent` dead metric | `lheijst/weewx-rtldavis` | Not yet offered |
| Outside-temperature sign + `0xFF8` sentinel | `lheijst/weewx-rtldavis` | Not yet offered — belongs alongside [#22](https://github.com/lheijst/weewx-rtldavis/pull/22); bites every cold-climate user, so it is the strongest remaining candidate |
| `e.read()` / TLS / `KeyError` fixes | `david-lutz/weewx-influx2` | **[PR #1](https://github.com/david-lutz/weewx-influx2/pull/1) OPEN** since 2026-07-13 (S38) — that repo's first-ever PR, and it has been quiet since 2023 |

Whatever is not upstreamed stays here, with a reason. That is the point of the inventory.
