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
| Driver (`rtldavis.py`), `pressure_service.py` | the **image** | an `scp` to `weewx-data/bin/user/` does nothing — needs a rebuild |
| `weewx.conf` and other mounted config | the **mount** | an image rebuild does nothing — needs a live edit on the NAS |
| `influx.py` | mounted → `scp` **is** correct | — |

**Ask "which layer actually wins in prod?" for every file, every time.** A previous session's answer
about a *different* file proves nothing about this one.

## Release / rollback

| Thing | Value |
|-------|-------|
| Published image | `:v2.0.11` + `:latest` — matches prod, no drift |
| Rollback | `:v2.0.10`, still on the NAS and Docker Hub |
| Prod baseline tag | `prod-baseline-20260728b` (`main` == this) |
| Driver banner | `0.20+ws.4` |
| Release mechanics | no git on the NAS; the `docker-compose.yml` there is stale/decorative — always `docker inspect` the live container. `kill` → `rm` → `sleep 3` → `run`, never `compose up` |

## Hardware / site

Davis 6263 VP2+ ISS · 6410 hall anemometer (replaced ~16–17 Jun 2026) · RTL-SDR Blog v3 + inline LNA
(bias-tee) · 915 MHz vertical · ~150 ft through walls. Reception is **noise-floor limited**:
measured baseline **73.3%, sd 4.67** (DEC-0059 — this supersedes the older "~67–70%" figure).
A reproducible ~2-pt dip at **hours 07 and 19** belongs to the site, not to any experiment arm.

Station coordinates: gitignored local-infra doc. Attribution: **WeatheredScientist**.

## Git

`main` = production truth (tagged `prod-baseline-YYYYMMDD`) · `dev` = work · feature branches off
`dev` (DEC-0011). Steady state is exactly `dev` + `main`. Finish a change with **`land`** — it
pushes, opens/updates the PR, reports checks, and **stops at the merge**; the merge is the owner's.
Commit subjects are imperative with a session tag.
