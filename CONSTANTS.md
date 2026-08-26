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

| Thing | Value |
|-------|-------|
| NAS | Synology DS918+ · `<NAS_HOST>` · `<NAS_IP>` · SSH port `<SSH_PORT>` · user `<NAS_USER>` |
| SSH / SCP | `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` · `scp -P <SSH_PORT> -O` (capital `-P`; `-O` for the legacy protocol) |
| Real values | gitignored local-infra doc — never committed |
| Read-only NAS access | `nasctl` (`ps`, `logs <c> [N]`, `inspect`, `cat/ls/head/tail/sha/grep/conf`). Rides a read-only key; mutations are refused by the box |
| Docker binary | `/usr/local/bin/docker` (no sudo; not on the default PATH) |
| Container | `weewx-rtldavis-v2` |
| Project root (NAS) | `/volume1/docker/weewx-rtldavis/` |
| Live config | `<project root>/weewx-data/weewx.conf` (bind-mounted; gain/ppm edits need only a restart) |
| Container venv user files | `/opt/weewx-venv/lib/python3.14/site-packages/user/` |
| Loop-JSON output | `/opt/weewx-data/loop-data.txt` (in container), plus `current.json` |
| Missing NAS tools | no `bc`, `tmux`, `screen` — use bash integer arithmetic and `nohup` |

## Deploy layers — the single most expensive thing to get wrong

**The driver is BAKED into the image; the config is MOUNTED. They are exact inverses (DEC-0031 /
DEC-0046).**

| Layer | Wins in prod | The silent no-op |
|---|---|---|
| Driver (`rtldavis.py`), `pressure_service.py`, **`dewpoint_service.py`** (verified S94) | the **image** | an `scp` to `weewx-data/bin/user/` does nothing — needs a rebuild |
| `weewx.conf` and other mounted config | the **mount** | an image rebuild does nothing — needs a live edit on the NAS |
| `influx.py` | mounted → `scp` **is** correct | — |
| **`loop_json_writer.py`** (verified S85) | the **mount** — `<project root>/loop_json_writer.py`, bind-mounted `ro` over the venv copy | **an image rebuild does nothing** — the Dockerfile never `COPY`s this file. Deploy = `scp` to the **project root** + restart. **The copy in `weewx-data/bin/user/` is a DECOY**: it is not the mount source and editing it changes nothing |
| **`ogoxeUploader.py`** (verified S104) | the **mount** — but its source is **`weewx-data/bin/user/ogoxeUploader.py`**, the very directory that is a decoy for `loop_json_writer.py`. Two adjacent rows, opposite truths: check the source path per file, never carry one file's answer to another | an image rebuild does nothing — the Dockerfile never `COPY`s this file either. Deploy = `scp` to **`weewx-data/bin/user/`** + recreate |
| `sortedcontainers` (verified S104) | the **mount** — a whole-**directory** `ro` bind, not a per-file one | **no repo copy exists**: this is a vendored third-party package pinned by the mount, so there is no `dev` version to diff it against. "In sync with `dev`" is undefined here — don't report it as either |

**Verify, don't recall** — `nasctl inspect weewx-rtldavis-v2` lists the per-file bind mounts
explicitly. That is the authoritative answer for any file, and it takes one command. S85 found
`loop_json_writer.py` was missing from this table entirely while being mounted, which would have
made a change "ship" with an image cut and silently do nothing — DEC-0046's exact failure.

**Ask "which layer actually wins in prod?" for every file, every time.** A previous session's answer
about a *different* file proves nothing about this one.

### Live-config deviations from stock — NAS-only, no repo artifact (DEC-0070)

`weewx.conf` is mounted and **never committed** (DEC-0012), so anything set in it exists only on the
NAS, with no CI and no diff to notice. **A container recreate from a stock config silently reverts
these.** Re-apply and re-verify after any recreate.

| Setting | Value | Why |
|---|---|---|
| `[DatabaseTypes][[SQLite]]` → `timeout` | **30** | weedb defaults to **5 s** (`weedb/sqlite.py:136`). At 5 s a reader holding the lock six seconds cost a CRITICAL + weewx's hardcoded 120 s wait + restart ≈ **5–10 min outage**. 30 s stays under the 60 s archive interval so records can't pile up. **Permanent** — WAL was tried and abandoned (DEC-0071), so this is the fix, not an interim |
| `[DatabaseTypes][[SQLite]]` → `[[[pragmas]]] journal_mode = DELETE` | **subsection, not a scalar** | Re-pins `delete` on every connection so an accidental WAL flip can never again silently strand a reader on a stale snapshot (DEC-0071). **weedb iterates `pragmas` as a MAPPING** — the scalar spelling `pragmas = journal_mode = DELETE` parses as a string, and iterating it raises `TypeError: string indices must be integers`, which crash-loops weewxd. It cost ~6 min of prod on 2026-08-06 |
| `[StdCalibrate][[Corrections]]` → `radiation` exact-code zero | DEC-0080 line, verbatim from `weewx.conf.example` | Zeros the VP2+ diode floor (`sr_raw=1` ≈ 1.758 W/m²) every dark minute. Applied 2026-08-11 (S73), **also written into `weewx.conf.rx-baseline`** — `restore_baseline` copies that snapshot over the live conf at every campaign abort/end, so a live-conf-only apply would be silently wiped (hazard found at apply; BOOT's original steps missed it). Verify after any recreate from stock **and** confirm dark hours read 0 (if 3.516 shows, extend per-code) |
| `[DavisPressure]` → `fetch_interval` | **300** (applied S101/DEC-0113 at the v2.0.14 build event, verified live) | WeatherLink v2's documented ceiling is 1,000 calls/hour + 10/s; 300s uses ~1.2% of quota. Cuts the archived barometer from a 60-min sample-and-hold staircase to a 5-min one (#144 item 3) |
| `[Rtldavis]` → `cmd` gain | **496** (adopted S101/DEC-0115, superseding the stock example's 372) | Campaign B's clean 32/32-block square: gain 496 beats 372 by +2.00 reception points, exactly clearing DEC-0059's adoption bar. **Also written into `weewx.conf.rx-baseline`** (same DEC-0080 lesson as the radiation row below — `restore_baseline` would otherwise silently revert it at the next campaign's own abort/end path). A fully-stock recreate (from `weewx.conf.example`, not the live/baseline files) would still reset to 372 |
| `[[Influx]]` → `lease_dir` | **`/nas-lease`** (added S101/DEC-0111) | Points `influx.py`'s NAS-LEASE courtesy-yield at the container's `-v /volume1/docker/nas-lease:/nas-lease:ro` bind (also new S101). Absent entirely from stock — a recreate without this mount+setting silently disables the yield, no error |

## Release / rollback

| Thing | Value |
|-------|-------|
| Prod image | **`:v2.0.14`**, deployed 2026-08-23 (S101), NAS-built from `origin/dev`@`efeeebd` under `ops/nas_build.py`'s NAS-LEASE wrapper (DEC-0114) — carries DEC-0110/DEC-0111/#233/#224/DEC-0113 and the weewx 5.4.0→5.5.0 bump (pinned since S88, first release to ship it). Driver banner unchanged at `0.20+ws.5` |
| Docker Hub | Still `:v2.0.13` as of this writing — v2.0.14's Hub push follows prod proof, per DEC-0078. Hold at `:v2.0.13` until v2.0.14 proves out |
| Rollback | `:v2.0.13` (the prior prod image, 12 clean days) on the NAS and Docker Hub; `:v2.0.12` one step further back |
| Prod baseline tag | **`prod-baseline-20260811`** (`main` = `1cc9605`, the v2.0.13 promotion via PR #161) — still current; v2.0.14's `main` promotion is separate and later, once it proves out (DEC-0114) |
| Driver banner | **prod runs `0.20+ws.5`** (shipped in `:v2.0.13`, unchanged in `:v2.0.14`) |
| Build host | **the NAS, natively** (DEC-0078) — the arm64 laptop's linux/amd64 cross-build fails (tar ENOSYS under emulation). Verify builds by the explicit `BUILD-EXIT` marker in `build.log`, never a pipeline exit |
| Release mechanics | no git on the NAS; the `docker-compose.yml` there is stale/decorative — always `docker inspect` the live container. `kill` → `rm` → `sleep 3` → `run`, never `compose up` |

## Hardware / site

Davis 6263 VP2+ ISS · RTL-SDR Blog v3 · 915 MHz vertical · ~150 ft through walls. **LNA (bias-tee)
currently OUT** — see timeline below, do not assume it's inline. Reception is **noise-floor
limited**. **Gain adopted at 496 (S101/DEC-0115)**, superseding the prior 372: measured **74.83%, sd
8.47** at gain 496 on the clean 32/32-block Campaign B square (this supersedes the older "73.3%, sd
4.67" figure, which was gain 372's — DEC-0059). A reproducible ~2-pt dip at **hours 07 and 19**
belongs to the site, not to any experiment arm.

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

Station coordinates: gitignored local-infra doc. Attribution: **WeatheredScientist**.

## Git

`main` = production truth (tagged `prod-baseline-YYYYMMDD`) · `dev` = work · feature branches off
`dev` (DEC-0011). Steady state is exactly `dev` + `main`. Finish a change with **`land`** — it
pushes, opens/updates the PR, reports checks, and **stops at the merge**; the merge is the owner's.
Commit subjects are imperative with a session tag.
