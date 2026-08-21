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
| `ogoxeUploader.py`, `sortedcontainers` | the **mount** (same pattern, per-file `ro` binds) | as above |

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

## Release / rollback

| Thing | Value |
|-------|-------|
| Prod image | **`:v2.0.13`**, deployed 2026-08-11 (S73, mid-H-hold), NAS-built from `1530971` (ws.5: child reaping + stall self-classification, DEC-0081) |
| Docker Hub | `:v2.0.13` pushed at deploy. **`:latest` moved to `:v2.0.13`** 2026-08-21 (S99) — 9 clean prod days, pure retag (no rebuild), verified via Docker Hub's public API matching digest `sha256:4cfc7fb9…` on both tags. Same rule applies to v2.0.14: hold at `:v2.0.13` until it proves out |
| Rollback | `:v2.0.12` (config digest `9db5c1…`), on the NAS and Docker Hub |
| Prod baseline tag | **`prod-baseline-20260811`** (`main` = `1cc9605`, the v2.0.13 promotion via PR #161) — landed after S73 close, verified S88 |
| Driver banner | **prod runs `0.20+ws.5`** (shipped in `:v2.0.13`) |
| Build host | **the NAS, natively** (DEC-0078) — the arm64 laptop's linux/amd64 cross-build fails (tar ENOSYS under emulation). Verify builds by the explicit `BUILD-EXIT` marker in `build.log`, never a pipeline exit |
| Release mechanics | no git on the NAS; the `docker-compose.yml` there is stale/decorative — always `docker inspect` the live container. `kill` → `rm` → `sleep 3` → `run`, never `compose up` |

## Hardware / site

Davis 6263 VP2+ ISS · RTL-SDR Blog v3 · 915 MHz vertical · ~150 ft through walls. **LNA (bias-tee)
currently OUT** — see timeline below, do not assume it's inline. Reception is **noise-floor
limited**: measured baseline **73.3%, sd 4.67** (DEC-0059 — this supersedes the older "~67–70%"
figure). A reproducible ~2-pt dip at **hours 07 and 19** belongs to the site, not to any
experiment arm.

### Hardware timeline

| Date | Change |
|---|---|
| 2026-05-01 | Station operational |
| 2026-05-16 | Dedicated 915 MHz antenna installed |
| 2026-05-27 | LNA ordered |
| ~2026-06-01 | LNA activated (bias-tee voltage) |
| 2026-06-16/17 | 6410 hall anemometer replaced |
| 2026-08-02 | LNA removed (mid-ERR-0005; DEC-0081/DEC-0083) |

Station coordinates: gitignored local-infra doc. Attribution: **WeatheredScientist**.

## Git

`main` = production truth (tagged `prod-baseline-YYYYMMDD`) · `dev` = work · feature branches off
`dev` (DEC-0011). Steady state is exactly `dev` + `main`. Finish a change with **`land`** — it
pushes, opens/updates the PR, reports checks, and **stops at the merge**; the merge is the owner's.
Commit subjects are imperative with a session tag.
