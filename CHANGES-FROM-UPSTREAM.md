# Changes from upstream

**Status:** Source of truth for what this project changed in code it did not write.
**Last updated:** 2026-07-12 (S37)

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
   upstream issue) was being misled. It now logs `0.20+ws.1`.
3. **It is the checklist for shrinking the fork.** Every row below is either something to upstream or
   something to justify keeping. A fork with no inventory only grows.

## Provenance

We build from Vince Skahan's repackage, not from Luc Heijst's repository directly. The chain is
verified from `Dockerfile` (which fetches `weewx-contrib/weewx-rtldavis/src.tgz` and installs
`david-lutz/weewx-influx2`):

| Component | Chain |
|-----------|-------|
| Go decoder | [bemasher/rtldavis](https://github.com/bemasher/rtldavis) → [lheijst/rtldavis](https://github.com/lheijst/rtldavis) → bundled in `weewx-contrib` `src.tgz` → us (unmodified) |
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
| `rtldavis.py` | `0.20` | `0.20+ws.1` |
| `influx.py` | `0.20` | `0.20+ws.1` |

The suffix sorts after the base version and is unambiguous about its parent. `rtldavis.py` also logs
`(fork of lheijst 0.20, patched by WeatheredScientist -- not stock upstream)` at startup, which
doubles as the canary for [DEC-0031](docs/DECISIONS.md) (stock upstream cannot print that line, so if
you see it, the baked driver is the one running).

---

## `rtldavis.py`

Base: `weewx-contrib/weewx-rtldavis` `src.tgz` (Luc Heijst v0.20, plus Skahan's 2025-12-20
`re.compile` deprecation patch). Delta: **+263 / −51 lines.**

### Bug fixes (these belong upstream)

| # | Change | Date | Why |
|---|--------|------|-----|
| 1 | **Rain-counter wraparound** — `rain_delta_tips()` | 2026-07-04 | Upstream treats *any* negative counter delta as a 127→0 wraparound and adds 128. A corrupt reading that produces a small negative delta (e.g. −64) therefore becomes **+64 tips of phantom rain**. Three confirmed events on this station, one of them a phantom 1.28 in — larger than the world 1-minute rainfall record. Only a large negative delta (near −128) is a real wraparound; anything else is rejected as a glitch and returns NULL. [DEC-0021] |
| 2 | **windDir never populated in one branch** | 2026-07-04 | In `parse_raw`, `wind_dir_vue` / `wind_speed_ec` / the `data['wind_*']` assignments are indented *inside* the `else:` of the direction decode. When the other branch is taken, wind speed and direction are simply never written to the packet. De-indented so both branches populate them. |
| 3 | **`NameError` on unknown channel** | 2026-07-05 | The unknown-station handler logs `raw`, which is not defined in that scope — so the error path meant to report a bad packet crashes instead. Now logs `pkt`. |
| 4 | **`rxCheckPercent` was permanently dead** | 2026-07-05 | `pct_good_all` is only computed `if total_max_count > 0 and self.stats['pct_good_all'] is not None`, but `_init_stats()`/`_reset_stats()` set `pct_good_all = None` every archive period — so the guard can never pass and the driver's own reception metric is never populated. Separately, `self.stats['pct_good']` (a list) was compared against `None` instead of `pct_good[i]`, which is always truthy. |
| 5 | **Per-packet logging at INFO** | 2026-07-05 | `RAW_CHANNEL_PAYLOAD`, `Hop:` and `ChannelIdx:` lines were logged at INFO on every frequency hop, flooding `weewx.log`. Moved behind `debug_rtld` levels. |

Numbers 1–4 are real defects in upstream that any US Davis user hits. They are the intended content
of an upstream contribution (see [Upstreaming](#upstreaming) below).

### Behavior changes (ours; would need discussion upstream)

| # | Change | Date | Why |
|---|--------|------|-----|
| 6 | **SensorQC** — decode-layer plausibility filter | 2026-07-08 | Same failure class as the rain glitch, applied to temperature / humidity / wind / UV / radiation: sensor-spec bounds plus a per-reading delta check, at the single choke point (`_data_to_packet`) so every consumer sees vetted data. Rejected values become NULL and log `rejecting implausible value`. Configurable (`sensor_qc`, `qc_<field>_max_delta`). [DEC-0029] |
| 7 | **Calm-air wind gate** | 2026-07-04 | Raw wind speed ≤ 2 with direction 0 is the 6410 hall-sensor floor, not wind. Record 0 speed and a **null** direction instead of a false "2 mph from due north" that pollutes wind roses. |
| 8 | **freqError stored for US and NZ** | 2026-07-04 | Upstream stores frequency-error statistics only when `frequency == 'EU'`. We store for `EU`, `US` and `NZ` — the data is just as useful on 915 MHz, and this is a 915 MHz station. |
| 9 | Lint / dead code | 2026-07-08 | Dropped unused imports (`timegm`, `fnmatch`, `string`), the dead `_fmt()`, and the unused `parse_readings()`. Bare `except:` → `except Exception:`. [DEC-0027] |

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

## `influx.py`

Base: `david-lutz/weewx-influx2` (itself a fork of `matthewwall/weewx-influx` for InfluxDB 2.x).
Delta: **+33 / −14 lines.** The Dockerfile installs the upstream extension and then copies our
patched file over it.

| # | Change | Date | Why |
|---|--------|------|-----|
| 1 | **`e.read.decode()` → `e.read().decode()`** | 2026-07-04 | Missing parentheses. `handle_exception` raises `AttributeError` on the bound method instead of reporting the HTTP error body — so the code that exists to explain an upload failure fails itself. Real bug, one character class. |
| 2 | **TLS verification on by default** | 2026-07-04 | `post_request` unconditionally used `ssl._create_unverified_context()` for any `https` server_url — certificate verification silently off, upstream's own comment calling it a hack. Now verifies by default; `verify_ssl = false` restores the old behavior for self-signed or internal endpoints. |
| 3 | **CLI `KeyError` when env vars unset** | 2026-07-04 | `os.environ['INFLUX_HOST']` (and `_ORG`, `_TOKEN`) are read at option-parse time, so `--help` crashes with `KeyError` unless all three are exported. Now `os.environ.get()`. Also fixed the `InluxDfB` help-text typos. |
| 4 | **Per-record logging at INFO** | 2026-07-05 | `loginf("Add Bindding Tag = ...")` and `loginf("tags = ...")` fire on every record. Demoted to `logdbg`. |
| 5 | **`distutils.StrictVersion` removed** | 2026-07-04 | `distutils` is gone in Python 3.12+; this image runs 3.14. Replaced with a tuple compare. |

Items 1, 2, 3 and 5 are unambiguous upstream bugs. Item 2 is a security fix.

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
| Rain-counter wraparound | `lheijst/weewx-rtldavis` | Draft comment written for issue #15, **not posted** — pending owner review |
| windDir branch bug | `lheijst/weewx-rtldavis` | Not yet offered |
| `NameError` on unknown channel | `lheijst/weewx-rtldavis` | Not yet offered |
| `rxCheckPercent` dead metric | `lheijst/weewx-rtldavis` | Not yet offered |
| `e.read()` / TLS / `KeyError` fixes | `david-lutz/weewx-influx2` | Not yet offered |

Whatever is not upstreamed stays here, with a reason. That is the point of the inventory.
