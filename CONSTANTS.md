# CONSTANTS — weewx-rtldavis

**Always-load, tier 1.** Durable facts; what changes more than quarterly belongs in `BOOT.md`. A row
holds the current value and at most one "before it"; a release replaces the value, never prepends
(DEC-0231). History: the DEC bodies, and `CHANGELOG-ARCHIVE.md` [S194b] for the pre-diet rows.

> **Self-sufficient by design (DEC-0063).** This repo is public, `eaglehunt-ops` private: the ops
> `CONSTANTS.md` is an owner-only supplement, never a prerequisite, never quoted here.

## Secret hygiene — this governs everything below (DEC-0012)

**The repo is PUBLIC and permanent.** Real hostnames, IPs, ports, usernames, coordinates, the WU PWS
id, and every credential live **only** in the gitignored local-infra doc. Committed docs and source
carry the placeholders below and `YOUR_*` values. Never paste a live secret into an LLM prompt —
treat anything that reaches one as compromised and rotate it server-side.

## Infra

Prod on `marvin` since 2026-08-28/29 (DEC-0118), InfluxDB since 2026-09-04 (DEC-0141); the NAS
holds nothing weewx uses (verified S142). Verify a row against live state before relying on it.

| Thing | Value |
|-------|-------|
| marvin | Debian · `<MARVIN_HOST>` · `<MARVIN_IP>`. Self-service: `marvinctl --tenant weewx` (`marvin-weewx` alias, adds `exec-ro`, DEC-0125); the tenant key has no host shell. The guarded `marvin-admin` alias covers the rest |
| Tenant root | `/srv/docker/weewx/` (`t-weewx`, `0750`), a `dev` checkout since S129 (DEC-0150) |
| Container | `weewx-rtldavis-v2`, run as `t-weewx` (996:986) by the unit's `--user` (DEC-0147); the image defaults to root |
| InfluxDB | `weewx-influxdb.service` in `/weather.slice`: `influxdb:2.7.12` `--pull=never`, `--user 996:986`, `-p 8086:8086`, data under `/srv/docker/weewx/influxdb/`. Consumers use `http://<MARVIN_IP>:8086` (`docs/INFLUXDB-MIGRATION.md`) |
| Live config | `<tenant root>/weewx-data/weewx.conf`, bind-mounted (gain/ppm edits need only a restart) |
| Venv user files | `/opt/weewx-venv/lib/python3.14/site-packages/user/` (in the container) |
| Loop-JSON output | `/opt/weewx-data/feed/loop-data.txt` + `feed/current.json`, a live-config deviation (DEC-0202). The dashboard's `eh-proxy` mounts only `weewx-data/feed`, HLF only `weewx-data/archive` |
| Real values | the gitignored local-infra doc |

## Deploy layers — the single most expensive thing to get wrong

**The driver is BAKED into the image; the config is MOUNTED. They are exact inverses (DEC-0031 /
DEC-0046).** Ask "which layer wins in prod?" for every file, every time. The authority is
`marvinctl --tenant weewx inspect weewx-rtldavis-v2`'s mount list.

| Layer | Wins in prod | The silent no-op |
|---|---|---|
| `rtldavis.py`, `pressure_service.py`, `dewpoint_service.py`, `owm.py`, `windy.py`, `rest_site.py` | the **image** | an `scp` to `weewx-data/bin/user/` does nothing — rebuild |
| `weewx.conf` and other mounted config | the **mount** (marvin's tree is the only copy) | a rebuild does nothing — edit live |
| `influx.py` | the **mount** → `scp` **is** correct | — |
| `loop_json_writer.py` | the **mount**: `<tenant root>/loop_json_writer.py`, `ro` over the venv copy | a rebuild does nothing. Deploy = `scp` to the tenant root + restart. **The copy in `weewx-data/bin/user/` is a DECOY** |
| `ogoxeUploader.py` | the **mount**, sourced from **`weewx-data/bin/user/`** (the row above's decoy dir: check per file) | a rebuild does nothing. Deploy = `scp` there + recreate |
| `sortedcontainers` | a whole-directory `ro` mount, vendored | no repo copy: "in sync with `dev`" is undefined |
| `weewx_monitor.py`, a host daemon | `<tenant root>/weewx_monitor.py`, run by `weewx-monitor.service` | `pull` updates the bytes, but the daemon reads them only at start: deploy = `pull`, then a deliberate `restart weewx-monitor.service` (unit edits stay owner-run). Verify sha = `dev`, start after mtime, `Remedy armed:` |

### Live-config deviations from stock — host-only, no repo artifact (DEC-0070)

`weewx.conf` is mounted and **never committed** (DEC-0012), so these exist only on marvin. **A
recreate from a stock config silently reverts them:** re-apply and re-verify after any recreate.
"+ baseline": also set in the tenant-root `weewx.conf.rx-baseline`, which a campaign
`restore_baseline` copies over the live conf (DEC-0080's two-copies hazard).

| Setting | Value | Why |
|---|---|---|
| `[DatabaseTypes][[SQLite]]` → `timeout` | **30** | weedb's 5 s default made a 6 s lock a 5–10 min outage; 30 s is under the 60 s archive interval |
| `[[SQLite]]` → `[[[pragmas]]] journal_mode = DELETE` | **a subsection, never a scalar** | Re-pins `delete` (DEC-0071, WAL abandoned). A scalar crash-loops weewxd (`TypeError: string indices must be integers`) |
| `[StdCalibrate][[Corrections]]` → `radiation` | DEC-0080's exact-code zero, verbatim from `weewx.conf.example`; + baseline | Zeros the diode floor (`sr_raw=1`). After a recreate, dark hours must read 0 (3.516: extend per code) |
| `[StdCalibrate][[Corrections]]` → `UV` | DEC-0200's two-code zero, verbatim from `weewx.conf.example`; + baseline | Zeros `uv_raw` 2 and 1 in the dark. Extend per code, never a threshold |
| `[DavisPressure]` → `fetch_interval` | **300** (DEC-0113) | ~1.2% of WeatherLink's quota; a 5-min barometer step, not 60 |
| `[Rtldavis]` → `cmd` gain | **372** (DEC-0125) | 496 (DEC-0115, Foundation's siting) gained +1.16 pts at marvin, under DEC-0059's 2.0-pt bar |
| `[[Influx]]` → `server_url` | **`http://<MARVIN_IP>:8086`** (DEC-0141); + baseline | Else `restore_baseline` points the writer at the dead Foundation port |
| `[[Influx]]` → `lease_dir` | **`/nas-lease`** (DEC-0111) | An empty local dir on marvin (MARVIN-DEC-0063): the NAS-LEASE yield is a no-op, moot since DEC-0141; fails open |
| file modes for the 996 container | `archive/weewx.sdb` owner-writable, `logs/weewx.log` 996:986 | Root-written files are unwritable as 996; a root-owned hot `weewx.sdb-journal` blocks the DB open (DEC-0147) |
| live conf mode + backups | live `weewx.conf` **0600**; backups only in **`weewx-data/conf-archive/`** (0700, files 0600) (DEC-0201) | **A conf-rewriting `weectl` run** leaves `weewx.conf.<timestamp>` beside it and a 0644 conf: `chmod 0600`, move the copy |
| `[LoopJsonWriter]` → `path`, `current_path` | **`/opt/weewx-data/feed/loop-data.txt`**, **`…/feed/current.json`** (DEC-0202); + baseline | `feed/` is all `eh-proxy` (994:984) mounts: dir 0755, files `o+r`, present before it starts; while it runs, only rename files in, never recreate the dir (the bind pins the inode) |
| `[LoopJsonWriter]` → `extra_fields` | **`windGust10`** (DEC-0224); + baseline | Puts `windGust10_mph` in the feed |

## Release / rollback

| Thing | Value |
|-------|-------|
| Prod image | **`:v2.4.0`** as `:marvin-live` since 2026-11-04 18:36:38 ET (S190, DEC-0229): index `82220200…`, from `dev`@`694938f`, banner `0.20+ws.10`, baked driver sha `7b6fb60a…`. Before it `:v2.3.0` (`71c201b6…`, `ws.9`, DEC-0228). The banner doesn't identify a build; the image ID and the driver's sha do (`marvinctl exec weewx-rtldavis-v2 -- sha256sum <venv user dir>/rtldavis.py`) |
| Docker Hub | **`:v2.4.0`** = multi-arch index `2b146586…` (amd64 `82220200…` = prod, arm64 `e986aae1…`); **`:latest` = `:v2.4.0`**. Before it `:v2.3.0` (`03f3c891…`). Multi-arch from v2.0.20 (DEC-0215). marvin's image IDs are index digests: compare index to index; on a multi-arch tag, its amd64 manifest to prod's. `:latest` moves are the owner's, after prod proof (DEC-0078). Check Hub's tag list, not this row |
| Rollback (image) | **`:v2.3.0-prod-pre-v2.4.0`** (`71c201b6…`), then **`:v2.2.0-prod-pre-v2.3.0`** (`0a790696…`): `marvinctl tag <it> …:marvin-live`, `restart weewx.service`. `-tolerance 0` in the live `cmd` + a restart turns the time gate off. Also local: `:v2.1.0-prod-pre-v2.2.0`, `:v2.0.21`, `:v2.0.20`, `:v2.0.19` … `:v2.0.16` (v2.0.19 or older puts `pressure` back on the derived path, DISC-0002). DEC-0147's user change is a unit-flag revert |
| Rollback (host) | None: Foundation was decommissioned 2026-09-02 |
| Prod baseline tag | **`prod-baseline-20261104`** (v2.4.0, `main` = `c376037`); before it `-20261101`. Check `git tag -l 'prod-baseline-*'` |
| Build host | **marvin** (amd64), `marvinctl build`, context the tenant root behind `.dockerignore`. BuildKit caches layers, so a cached log proves nothing about the Go patches. A NAS-era build was verified by the `BUILD-EXIT` marker in `build.log` |
| Release mechanics | `marvinctl pull` → `build /srv/docker/weewx -t …:vX.Y.Z` → verify with `exec-ro` → `tag …:vX.Y.Z …:marvin-live` → `restart weewx.service` (DEC-0204). The unit runs `:marvin-live` under `--pull=never` (not `set-image`); never `compose up`. Hub tags and the GitHub release: `docs/CONVENTIONS.md` |

## Hardware / site

Davis 6263 VP2+ ISS · RTL-SDR Blog v3 at USB `5-1` · 915 MHz vertical · **LNA (bias-tee) OUT**.
marvin sits closer than Foundation's ~150 ft through walls, so Foundation's figures don't transfer.
Coordinates: the local-infra doc. Attribution: **WeatheredScientist**.

| Date | Change |
|---|---|
| 2026-05-01 | Station operational; 05-16 dedicated antenna |
| ~2026-06-01 | LNA activated; removed 2026-08-02 (DEC-0081/0083) |
| 2026-06-16/17 | 6410 hall anemometer replaced |
| 2026-08-28/29 | Receiver moved to marvin (DEC-0118); gain 372, not Foundation's 496 (DEC-0115/0125) |
| 2026-09-07 | USB `7-1.2` → `5-1` (DEC-0154); reception unchanged |

## Git

`main` = production truth (tagged `prod-baseline-YYYYMMDD`) · `dev` = work · feature branches off
`dev` (DEC-0011). Steady state is exactly `dev` + `main`. Finish a change with **`land`** — it
pushes, opens/updates the PR, reports checks, and **stops at the merge**; the merge is the owner's.
Commit subjects are imperative with a session tag.
