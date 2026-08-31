# CONSTANTS — weewx-rtldavis

**Always-load, tier 1.** Durable facts that almost never change. If something here changes more than
about once a quarter, it belongs in `BOOT.md` instead.

> **This file is self-sufficient by design (DEC-0063).** This repo is **public**; the shared
> `eaglehunt-ops/CONSTANTS.md` is in a **private** repo. A tier file that told its reader to go load
> a private repo would be a dead end for every external contributor — the population this repo has
> and the sibling repos do not. So the constants below are stated here outright. The ops file is an
> **owner-only supplement, never a prerequisite**, and its values are never quoted into this file.

## Secret hygiene — this governs everything below (DEC-0012)

**The repo is PUBLIC and permanent.** Real hostnames, IPs, ports, usernames, coordinates, the WU PWS
id, and every credential live **only** in the gitignored local-infra doc. Committed docs and source
carry the placeholders below and `YOUR_*` values. Never paste a live secret into an LLM prompt —
treat anything that reaches one as compromised and rotate it server-side.

## Infra

**The container moved hosts 2026-08-28/29 (DEC-0118) — it now runs on `marvin`, not the NAS.** The
NAS still matters (InfluxDB stays there, and its old weewx path still resolves — see below) but
`docker`/`nasctl` against the NAS no longer touches the live weewx container. This section got its
first pass at S105; **verify rows against live infra before trusting them for anything operational**
(`BOOT.md` job 8) rather than assuming a one-session update caught everything.

| Thing | Value |
|-------|-------|
| **marvin (prod host, since DEC-0118)** | Debian hypervisor · `<MARVIN_HOST>` · `<MARVIN_IP>` — access today is the guarded `marvin-admin` alias; self-service `marvinctl` for this repo isn't live yet (`t-weewx`'s key unminted, `BOOT.md` job 6) |
| Tenant root (marvin) | `/srv/docker/weewx/` (owned `t-weewx`, mode `0750`) |
| Container | `weewx-rtldavis-v2` (now on marvin) |
| NAS | Synology DS918+ · `<NAS_HOST>` · `<NAS_IP>` · SSH port `<SSH_PORT>` · user `<NAS_USER>` — still hosts InfluxDB; no longer hosts the weewx container |
| SSH / SCP (NAS) | `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` · `scp -P <SSH_PORT> -O` (capital `-P`; `-O` for the legacy protocol) |
| Real values | gitignored local-infra doc — never committed. **Needs a marvin entry added; not done as of S105** |
| Read-only NAS access | `nasctl` (`ps`, `logs <c> [N]`, `inspect`, `cat/ls/head/tail/sha/grep/conf`). Rides a read-only key; mutations refused by the box. **No marvin-side equivalent for this repo yet** — that's what the unminted `t-weewx` key blocks |
| Docker binary (NAS) | `/usr/local/bin/docker` (no sudo; not on default PATH) — relevant to InfluxDB and other NAS-resident containers now, not weewx |
| Project root, real (marvin) | `/srv/docker/weewx/` |
| Project root, NAS-side compat path | `/volume1/docker/weewx-rtldavis/` — **now an NFS overlay mount of marvin's export**, not local NAS storage. Dashboard and HLF still read this exact path unchanged; only what's behind it changed |
| Live config | `<project root>/weewx-data/weewx.conf` (bind-mounted; gain/ppm edits need only a restart) — path convention unchanged, host behind it did not |
| Container venv user files | `/opt/weewx-venv/lib/python3.14/site-packages/user/` |
| Loop-JSON output | `/opt/weewx-data/loop-data.txt` (in container), plus `current.json` |
| Missing tools | NAS: no `bc`, `tmux`, `screen` — use bash integer arithmetic and `nohup`. **Marvin is untested for this** — it's a full Debian box, likely has all three, but not verified this session |

## Deploy layers — the single most expensive thing to get wrong

**The driver is BAKED into the image; the config is MOUNTED. They are exact inverses (DEC-0031 /
DEC-0046).**

| Layer | Wins in prod | The silent no-op |
|---|---|---|
| Driver (`rtldavis.py`), `pressure_service.py`, **`dewpoint_service.py`** (verified S94) | the **image** | an `scp` to `weewx-data/bin/user/` does nothing — needs a rebuild |
| `weewx.conf` and other mounted config | the **mount** | an image rebuild does nothing — needs a live edit **on marvin** (since DEC-0118; was the NAS through S104). **The NAS-side path is now read-only** (marvin exports it `ro`) — an edit attempted via the old NAS path will fail or silently not persist, not just be the wrong layer |
| `influx.py` | mounted → `scp` **is** correct | — |
| **`loop_json_writer.py`** (verified S85) | the **mount** — `<project root>/loop_json_writer.py`, bind-mounted `ro` over the venv copy | **an image rebuild does nothing** — the Dockerfile never `COPY`s this file. Deploy = `scp` to the **project root** + restart. **The copy in `weewx-data/bin/user/` is a DECOY**: it is not the mount source and editing it changes nothing |
| **`ogoxeUploader.py`** (verified S104) | the **mount** — but its source is **`weewx-data/bin/user/ogoxeUploader.py`**, the very directory that is a decoy for `loop_json_writer.py`. Two adjacent rows, opposite truths: check the source path per file, never carry one file's answer to another | an image rebuild does nothing — the Dockerfile never `COPY`s this file either. Deploy = `scp` to **`weewx-data/bin/user/`** + recreate |
| `sortedcontainers` (verified S104) | the **mount** — a whole-**directory** `ro` bind, not a per-file one | **no repo copy exists**: this is a vendored third-party package pinned by the mount, so there is no `dev` version to diff it against. "In sync with `dev`" is undefined here — don't report it as either |

**Verify, don't recall** — an `inspect` of the live `weewx-rtldavis-v2` container lists the per-file
bind mounts explicitly and is the authoritative answer for any file. **`nasctl inspect
weewx-rtldavis-v2` no longer reaches it** (DEC-0118 — the container isn't on the NAS anymore); no
marvin-side self-service equivalent exists yet for this repo (`t-weewx`'s `marvinctl` key is
unminted, `BOOT.md` job 6). Until that lands, verifying this table means asking a marvin-side session
directly, not running a command from here. S85 found `loop_json_writer.py` missing from this table
entirely while being mounted, which would have made a change "ship" with an image cut and silently
do nothing — DEC-0046's exact failure; don't let the lost self-service path regress that discipline.

**Ask "which layer actually wins in prod?" for every file, every time.** A previous session's answer
about a *different* file proves nothing about this one.

### Live-config deviations from stock — host-only, no repo artifact (DEC-0070)

`weewx.conf` is mounted and **never committed** (DEC-0012), so anything set in it exists only on the
live host (marvin, since DEC-0118 — was the NAS through S104), with no CI and no diff to notice. **A
container recreate from a stock config silently reverts these.** Re-apply and re-verify after any
recreate. **All six rode the direct file copy at cutover** (unverified this session whether a
`weewx.conf.rx-baseline`-equivalent snapshot exists on marvin — the NAS's `restore_baseline`
mechanism is `ops/rx_experiment.sh` tooling that has not itself moved yet, `BOOT.md` job 2).

| Setting | Value | Why |
|---|---|---|
| `[DatabaseTypes][[SQLite]]` → `timeout` | **30** | weedb defaults to **5 s** (`weedb/sqlite.py:136`). At 5 s a reader holding the lock six seconds cost a CRITICAL + weewx's hardcoded 120 s wait + restart ≈ **5–10 min outage**. 30 s stays under the 60 s archive interval so records can't pile up. **Permanent** — WAL was tried and abandoned (DEC-0071), so this is the fix, not an interim |
| `[DatabaseTypes][[SQLite]]` → `[[[pragmas]]] journal_mode = DELETE` | **subsection, not a scalar** | Re-pins `delete` on every connection so an accidental WAL flip can never again silently strand a reader on a stale snapshot (DEC-0071). **weedb iterates `pragmas` as a MAPPING** — the scalar spelling `pragmas = journal_mode = DELETE` parses as a string, and iterating it raises `TypeError: string indices must be integers`, which crash-loops weewxd. It cost ~6 min of prod on 2026-08-06 |
| `[StdCalibrate][[Corrections]]` → `radiation` exact-code zero | DEC-0080 line, verbatim from `weewx.conf.example` | Zeros the VP2+ diode floor (`sr_raw=1` ≈ 1.758 W/m²) every dark minute. Applied 2026-08-11 (S73), **also written into `weewx.conf.rx-baseline`** — `restore_baseline` copies that snapshot over the live conf at every campaign abort/end, so a live-conf-only apply would be silently wiped (hazard found at apply; BOOT's original steps missed it). Verify after any recreate from stock **and** confirm dark hours read 0 (if 3.516 shows, extend per-code) |
| `[DavisPressure]` → `fetch_interval` | **300** (applied S101/DEC-0113 at the v2.0.14 build event, verified live) | WeatherLink v2's documented ceiling is 1,000 calls/hour + 10/s; 300s uses ~1.2% of quota. Cuts the archived barometer from a 60-min sample-and-hold staircase to a 5-min one (#144 item 3) |
| `[Rtldavis]` → `cmd` gain | **372**, re-tested and holding as of DEC-0125 (S111). DEC-0118's cutover incident originally left it at 372 by accident (an unrelated USB controller, not gain); Campaign C then re-tested 372 vs DEC-0115's Foundation-adopted 496 at marvin's own RF position under a properly-powered design, and **496 did not clear the 2.0-pt adoption bar** (+1.16 pts, DEC-0059/DEC-0069). DEC-0115 stands for Foundation's own siting — this is a separate finding that the answer doesn't transfer to marvin, not a correction of it. 372 is no longer "provisional-by-accident"; it is measured-and-unbeaten at this site pending a longer multi-day campaign (`BACKLOG.md`) |
| `[[Influx]]` → `lease_dir` | **`/nas-lease`** (in-container path, added S101/DEC-0111 — unchanged by the host move) | Points `influx.py`'s NAS-LEASE courtesy-yield at a mount. **On marvin this is a deliberately empty local directory (`MARVIN-DEC-0063`), not a live share of the NAS's real lease file** — the courtesy-yield is a permanent no-op until cross-host lease sharing is built (`BOOT.md` job 7). On the NAS through S104 it was `-v /volume1/docker/nas-lease:/nas-lease:ro`, a live bind. Either way, absent/broken silently disables the yield — the mechanism fails open by design, never errors |

## Release / rollback

| Thing | Value |
|-------|-------|
| Prod image | **`:v2.0.14`**, unchanged since 2026-08-23 (S101) through tonight's host move (DEC-0118) — same bits, `docker save`/`load` (608 MB) onto marvin, no rebuild. Originally NAS-built from `origin/dev`@`efeeebd` under `ops/nas_build.py`'s NAS-LEASE wrapper (DEC-0114) — carries DEC-0110/DEC-0111/#233/#224/DEC-0113 and the weewx 5.4.0→5.5.0 bump. Driver banner unchanged at `0.20+ws.5` |
| Docker Hub | Still `:v2.0.13` as of this writing — v2.0.14's Hub push follows prod proof, per DEC-0078. Hold at `:v2.0.13` until v2.0.14 proves out |
| Rollback (image) | `:v2.0.13` (the prior prod image) on Docker Hub; `:v2.0.12` one step further back. **Untested whether either copy still exists on the NAS itself** post-migration |
| Rollback (host) | **New since DEC-0118**: Foundation (the NAS container) is stopped, not decommissioned, specifically as a host-level rollback net — move the dongle back, start it, revert the consumer mounts. Kept through a soak period (`BOOT.md` job 6), separate from and faster than any image-tag rollback |
| Prod baseline tag | **`prod-baseline-20260811`** (`main` = `1cc9605`, the v2.0.13 promotion via PR #161) — still current; v2.0.14's `main` promotion is separate and later, once it proves out (DEC-0114). Untouched by the host move |
| Driver banner | **prod runs `0.20+ws.5`** (shipped in `:v2.0.13`, unchanged in `:v2.0.14`) |
| Build host | **Historically the NAS, natively** (DEC-0078) — the arm64 laptop's linux/amd64 cross-build fails (tar ENOSYS under emulation). **Untested since DEC-0118 whether marvin (Ryzen 9700X, amd64) can now build natively** — `BOOT.md` job 3 flags this as worth checking before assuming the NAS-build-then-transfer dance repeats for the next image cut. Verify any NAS build by the explicit `BUILD-EXIT` marker in `build.log`, never a pipeline exit |
| Release mechanics | No git on the NAS; the `docker-compose.yml` there was stale/decorative even before the move. `kill` → `rm` → `sleep 3` → `run`, never `compose up` — this convention travels with the container to marvin, but **the actual commands to run it there aren't self-service from this repo yet** (`t-weewx`'s `marvinctl` key is unminted) |

## Hardware / site

Davis 6263 VP2+ ISS · RTL-SDR Blog v3 · 915 MHz vertical · ~150 ft through walls. **LNA (bias-tee)
currently OUT** — see timeline below, do not assume it's inline. Reception is **noise-floor
limited on Foundation's own siting** (~150 ft through walls, above) — **this changed 2026-08-28/29
when the receiver moved to marvin**, a measurably closer position with fewer walls (DEC-0118); the
figures below are Foundation's own measured history and should not be assumed to transfer.

**Gain running now: 372, re-tested and holding at marvin's position (DEC-0125, S111).** DEC-0115
adopted **496** on Foundation's siting: measured **74.83%, sd 8.47** at gain 496 on the clean
32/32-block Campaign B square (superseding the older "73.3%, sd 4.67" figure, which was gain 372's
on the same siting — DEC-0059). 372 ended up running post-migration by accident — a same-night
incident (the actual cause was unrelated — a USB controller, not gain) — but Campaign C then ran the
proper same-position re-sweep `BACKLOG.md` had queued, and **496 did not beat 372 by DEC-0059's
2.0-pt bar** (+1.16 pts, per-minute freeze-aware metric). DEC-0115 is still the right call for
Foundation's own data; it simply doesn't transfer to marvin's closer, fewer-walls position.
Foundation's reproducible ~2-pt dip at **hours 07 and 19** was a property of that site — marvin's own
morning notch instead runs **hours 07–09, 2–3.5 pts** (found pre-registering Campaign C), so treat
either site's dip shape as local, not universal.

### Hardware timeline

| Date | Change |
|---|---|
| 2026-05-01 | Station operational |
| 2026-05-16 | Dedicated 915 MHz antenna installed |
| 2026-05-27 | LNA ordered |
| ~2026-06-01 | LNA activated (bias-tee voltage) |
| 2026-06-16/17 | 6410 hall anemometer replaced |
| 2026-08-02 | LNA removed (mid-ERR-0005; DEC-0081/DEC-0083) |
| 2026-08-23 | RF gain 372 → 496 adopted, Campaign B's result (DEC-0115) |
| 2026-08-28/29 | **Receiver relocated: NAS ("Foundation") → marvin (DEC-0118).** Closer, fewer walls — a new siting, not a tuning change. Gain reverted to 372 mid-incident |
| 2026-08-30/31 | Campaign C: same-position re-sweep of 372 vs 496 — 496 does not clear the adoption bar at marvin (DEC-0125). Gain holds at 372 |

Station coordinates: gitignored local-infra doc. Attribution: **WeatheredScientist**.

## Git

`main` = production truth (tagged `prod-baseline-YYYYMMDD`) · `dev` = work · feature branches off
`dev` (DEC-0011). Steady state is exactly `dev` + `main`. Finish a change with **`land`** — it
pushes, opens/updates the PR, reports checks, and **stops at the merge**; the merge is the owner's.
Commit subjects are imperative with a session tag.
