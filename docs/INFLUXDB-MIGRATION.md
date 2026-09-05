# InfluxDB migration — Foundation → marvin (ops#260 step 3)

**Status:** runbook, S124 (2026-09-04) — *nothing executed yet.* Decision record: DEC-0141. Ledger:
[ops#270](https://github.com/WeatheredScientist/eaglehunt-ops/issues/270) (the drill stays on ops#260).
**Owner of the move:** weewx-rtldavis (compose owner of the `influxdb` container, as ops#260
arbitrated). **Host:** marvin. **Consumers repoint once:** weewx's own `influx.py`, eh-proxy
`/query`, dashboard `event-detect` — all three already run on marvin. **Brokered by:** eaglehunt-ops.
**Why now:** HLF (09-04 12:26 ET) and EHWD (09-04 ~19:35 ET) both cut over; InfluxDB is the **only
weather workload left on Foundation** and the last continuous Foundation write in the whole
decoupling (OPS-DEC-0188). After it, Container Manager can come off Foundation and the
Foundation-dark drill can be scheduled.

Real hostnames/IPs are `<NAS_IP>` / `<MARVIN_IP>` here (public repo, DEC-0012); the values are in
the gitignored local-infra doc and in the sibling repos' private constants.

---

## 0. Measured state, 2026-09-04 ~21:30 ET (not recalled — re-measure before executing)

| Thing | Foundation (source) | How measured |
|---|---|---|
| Container | `influxdb`, image `influxdb:2.7` → **engine v2.7.12** (`/health`), up since 2026-06-19, `restart: unless-stopped`, log driver DSM `db`, compose project `weewx-rtldavis` (`/volume1/docker/weewx-rtldavis/docker-compose.yml`) | `nasctl inspect influxdb` (env values stripped), `curl /health` |
| Data | bind `/volume1/docker/influxdb/data` → `/var/lib/influxdb2` (`drwx------ 1000:root`) | inspect + `nasctl ls` (**the listing is EMPTY for the read-only key — a permission false-zero, not an empty dir**, GOTCHAS §1) |
| Config | bind `/volume1/docker/influxdb/config` → `/etc/influxdb2`; holds `influx-configs` (643 B, 2026-08-19 — the CLI operator config dashboard S237 repaired) | `nasctl ls` |
| Size | **16.4 MB on disk across 64 shards** (`weewx` bucket 16.1 MB · `eh_rollup` 0.2 MB · `_monitoring`/`_tasks` ~0.1 MB); plus the bolt/sqlite metadata files — whole tree well under 50 MB | `curl /metrics` → `storage_shard_disk_size` summed per bucket (unauthenticated endpoint) |
| Port | `8086/tcp` published on the host (0.0.0.0) — the compose comment claiming "no host port" is stale | inspect `PortBindings` |
| Env | `DOCKER_INFLUXDB_INIT_*` (setup-mode vars, ignored once initialised) — **values never read; they are the admin password + operator token** | inspect, keys only |
| Org / buckets | `eaglehunt` · `weewx` (retention 0) · `eh_rollup` (retention 0, dashboard DEC-0266) · system `_monitoring`, `_tasks` | dashboard `influx/README.md`, metrics bucket ids |
| Task | `eh-daily-rollup` (dashboard-owned, nightly 05:15 UTC = 01:15 EDT, inside the task store) | dashboard `influx/README.md` |
| Tokens (fingerprints only) | weewx write `sha256-ef8e9af8` · eh-proxy read · event-detect read `weewx` + rw `eh_rollup` `sha256-15442ba6` · CLI operator config in `influx-configs` | ops `CONSTANTS.md` §5, `marvinctl conf … Influx` |

| Consumer (all on marvin) | Where the URL lives | Repoint = |
|---|---|---|
| weewx `influx.py` (writer, `[[Influx]] server_url = http://<NAS_IP>:8086`, `lease_dir = /nas-lease`) | `/srv/docker/weewx/weewx-data/weewx.conf` (`t-weewx` 0600) **and** `weewx.conf.rx-baseline` (a campaign `restore_baseline` copies it over the live conf — CONSTANTS.md's DEC-0080 hazard shape) | owner edit of both files + `marvinctl --tenant weewx restart weewx.service` (~31 s recreate, DEC-0138) |
| eh-proxy `/query` (`INFLUX_URL`) | `/srv/docker/dashboard/secrets/proxy.env` (`--env-file`, host-side) | dashboard: edit + `marvinctl --tenant dashboard restart eh-proxy.service`; boot-time URL validation (their #614) fails loudly on a typo |
| dashboard `event-detect` (`EVENT_INFLUX_URL`), hourly timer | `/srv/docker/dashboard/secrets/event-detect.env` (`EnvironmentFile=`) | dashboard: edit; next timer fire picks it up, no unit change |
| HLF | **none** — `grep -ri influx` over the HLF repo finds one docstring, no runtime use (inventory answer for ops BOOT item D) | — |
| Foundation's idle `eh-proxy` (rollback instance, `INFLUX_URL=http://influxdb:8086` over the dead compose network) | Foundation | dies with the move; dashboard's own retirement step (ops#260 step 4) |

**Nothing else reads or writes this store.** Grafana was removed 2026-06-18; coffeeradar has no Influx
path (their ops#260 inventory answer).

## 1. Design (DEC-0141 — the reasoning lives there; this is the shape)

- **Raw tree copy, not `influx backup`/`restore`.** Same engine version, so `data/` + `config/`
  copied byte-for-byte carry org, buckets, **every token**, the `eh-daily-rollup` Task and the CLI
  operator config unchanged — the like-for-like cutover ops#260's hygiene rule asks for. Consumers
  change exactly one thing each: the URL. A restore path would be a second mechanism to verify.
- **Copy from a STOPPED server for the real cutover.** 16 MB copies in seconds; the outage is the
  owner's gesture time, not the transfer. The live pre-copy the generic §3 recipe describes buys
  nothing on size here — its value is the **dark-parallel test** (stage 1), so we do that.
- **Container `weewx-influxdb`, unit `weewx-influxdb.service`** ([`ops/weewx-influxdb.service`](../ops/weewx-influxdb.service))
  — inside the weewx manifest's existing globs → self-service lifecycle, no manifest edit.
- **`influxdb:2.7.12` pinned, `--pull=never`, `--user 996:986` (`t-weewx`), `-p 8086:8086`,
  `weather.slice`.** Header of the unit file says why, item by item.
- **Foundation instance retained, stopped, `--restart=no`** for at least two weeks (rollback; retires
  with Container Manager at ops#260 step 4). Never deleted in this runbook.
- **Stop by `docker kill -s TERM`, never `docker stop`** on the NAS (DEC-0008 — `stop`'s wait hangs
  this box); TERM gives influxd its clean WAL flush, then poll for exit.
- **Rides along: nothing.** No bind tightening, no memory cap, no retention change, no `lease_dir`
  removal, no backup timer *inside* the cutover — each is its own later change (§5).

## 2. Stage 0 — prep (no prod touch)

| Who | Step |
|---|---|
| weewx | this runbook + `ops/weewx-influxdb.service` merged to `dev`; DEC-0141; ops#270 filed; both sibling sessions told |
| marvin | vendor the unit verbatim into `host/etc/systemd/system/`, then one root gesture: `install-tenant-units.sh weewx` (installs + `daemon-reload`, never starts — tenant's verb) · `docker pull influxdb:2.7.12` · `mkdir -p /srv/docker/weewx/influxdb` (`t-weewx:t-weewx` 0750). Confirm `systemctl show weewx-influxdb.service -p LoadState` = `loaded` |
| dashboard | know the two edits (`proxy.env` `INFLUX_URL`, `event-detect.env` `EVENT_INFLUX_URL` → `http://<MARVIN_IP>:8086`), have `verify_archive_fresh.py --since <epoch>` ready; confirm the event-detect timer can be paused/resumed by the tenant (`marvinctl --tenant dashboard disable --now` / `enable --now dashboard-event-detect.timer`) |
| ops | broker the window; the ledger is the ops issue |

## 3. Stage 1 — dark-parallel from a snapshot (proves the unit, the uid, the bolt store; zero prod risk)

Transport is the marvin-data share (NAS `/volume1/marvin-data` ⇄ marvin `/srv/nas/marvin-data`,
IP-locked NFS, MARVIN-DEC-0020) — the route the weewx cutover's 39.5 MB archive copy took
(MARVIN-DEC-0064). **The tarball contains the token store** — it is deleted from the share in the
same stage. Each line is one owner step; NAS-side lines are Class C (agent-run on an in-chat yes via
the mint path), marvin-side root lines are the owner's own hands (GOTCHAS §3 — interactive sudo).

1. [NAS root] `sudo tar -C /volume1/docker/influxdb -czf /volume1/marvin-data/influxdb-snap-$(date +%Y%m%d-%H%M).tgz data config` — a **live** copy; the bolt file may be torn (writes are rare: 1,154 lifetime), and if it is, influxd refuses to start, which is the test doing its job. Redo from step 1, or accept and rely on stage 2's stopped copy.
2. [marvin root] `sudo tar -C /srv/docker/weewx/influxdb -xzf /srv/nas/marvin-data/influxdb-snap-<stamp>.tgz && sudo chown -R 996:986 /srv/docker/weewx/influxdb && sudo chmod 750 /srv/docker/weewx/influxdb`
3. [weewx] `marvinctl --tenant weewx start weewx-influxdb.service` (**start, not enable** — nothing survives a reboot until stage 2)
4. [Mac, read-only] `curl -s http://<MARVIN_IP>:8086/health` → `"status":"pass"`, `"version":"v2.7.12"` · `curl -s http://<MARVIN_IP>:8086/metrics | grep -c '^storage_shard_disk_size'` → 64 (the shard count at copy time) · `marvinctl --tenant weewx logs weewx-influxdb 50` → no permission errors, `Listening` line · `marvinctl --tenant weewx unit weewx-influxdb.service` → `weather.slice`.
5. [owner, optional, read-only against the dark instance] `docker exec weewx-influxdb influx bucket list --org eaglehunt` and `influx task list --org eaglehunt` — proves the CLI operator config travelled (the S237 orphaning trap: "verify CLI auth still works" after anything touches it).
6. [weewx] `marvinctl --tenant weewx stop weewx-influxdb.service`. The dark instance must not run across 01:15 EDT (the Task fires inside it — harmless, its writes land in a copy stage 2 replaces, but keep the test bounded).
7. [NAS root] `sudo rm /volume1/marvin-data/influxdb-snap-<stamp>.tgz` · [marvin root] `sudo rm -rf /srv/docker/weewx/influxdb/data /srv/docker/weewx/influxdb/config` (stage 2 lays down the real tree; an old copy underneath is exactly the kind of "which layer wins" trap CONSTANTS.md exists for).

## 4. Stage 2 — cutover (one attended window, ~20–30 min of gestures, Influx write gap ≈ the window)

**Window:** not 01:00–01:30 EDT (Task), not 03:10–03:40 EDT (dumps + restic), and start just after
an event-detect fire (`:00`) so the paused timer costs at most one hourly scan. The archive gap is
backfilled in step 9; loop-packet posts in the gap are lost by design (the archive is the deliverable).

| # | Who | Step | Proves |
|---|---|---|---|
| 1 | dashboard | `marvinctl --tenant dashboard disable --now dashboard-event-detect.timer` | no `eh_rollup` write can land on Foundation after the copy |
| 2 | Mac | `curl -s http://<NAS_IP>:8086/metrics \| grep -c '^storage_shard_disk_size'` and the per-bucket size sum — record both | the numbers step 6 must reproduce |
| 3 | NAS root (Class C) | `/usr/local/bin/docker kill -s TERM influxdb` then poll `/usr/local/bin/docker ps -a --filter name=influxdb --format '{{.Status}}'` until `Exited (0)`; then `/usr/local/bin/docker update --restart=no influxdb` | clean WAL flush; a NAS reboot can never resurrect a stale second store |
| 4 | NAS root (Class C) | `sudo tar -C /volume1/docker/influxdb -czf /volume1/marvin-data/influxdb-final-$(date +%Y%m%d-%H%M).tgz data config` (+ `sha256sum` of it) | consistent copy of a stopped server |
| 5 | marvin root (owner) | `sudo mkdir -p /srv/docker/weewx/influxdb && sudo tar -C /srv/docker/weewx/influxdb -xzf /srv/nas/marvin-data/influxdb-final-<stamp>.tgz && sudo chown -R 996:986 /srv/docker/weewx/influxdb && sudo chmod 750 /srv/docker/weewx/influxdb` (sha256 compared first) | bytes on NVMe, tenant-owned |
| 6 | weewx | `marvinctl --tenant weewx enable --now weewx-influxdb.service` · then `curl -s http://<MARVIN_IP>:8086/health` · shard count + per-bucket sums **equal step 2's** | the store is live on marvin and complete |
| 7 | weewx (owner edit) | `sudo -u t-weewx sed -i 's#http://<NAS_IP>:8086#http://<MARVIN_IP>:8086#' /srv/docker/weewx/weewx-data/weewx.conf /srv/docker/weewx/weewx-data/weewx.conf.rx-baseline` · `marvinctl --tenant weewx restart weewx.service` · `marvinctl --tenant weewx logs weewx-rtldavis-v2 100` shows `Data will be uploaded to http://<MARVIN_IP>:8086` and no `Influx` errors after it | writer repointed; the campaign baseline can't revert it |
| 8 | dashboard | edit `secrets/proxy.env` `INFLUX_URL` and `secrets/event-detect.env` `EVENT_INFLUX_URL` → `http://<MARVIN_IP>:8086`; `marvinctl --tenant dashboard restart eh-proxy.service`; `enable --now dashboard-event-detect.timer`; `verify_archive_fresh.py --since <step-6 epoch>` green once weewx's first archive record posts | both readers repointed; the dashboard's live surface is off Foundation |
| 9 | owner, marvin | backfill the gap from SQLite (source of truth): transport the **fixed** `ops/backfill_influx.py` from `dev` (the copy on marvin is the 2026-06-19 pre-DEC-0119 version — two known bugs) and run `INFLUX_TOKEN=<weewx write token> python3 backfill_influx.py --server-url http://127.0.0.1:8086 --org eaglehunt --db-path /srv/docker/weewx/weewx-data/archive/weewx.sdb --start <step-3 time> --end <step-7 time>` (`--dry-run` first). Expect ≈ one record per minute of the window, 0 errors | `weewx` bucket has no hole |
| 10 | Mac | `curl -s -m 5 http://<NAS_IP>:8086/health` → connection refused; `nasctl ps` shows no `influxdb` running | Foundation is no longer serving anything weather |

**Expected alerts during the window:** `weewx_monitor.py`'s uploader alerter will report `Influx`
failures between steps 3 and 7 — that is the instrument working, not a second incident. Tell the
owner before step 3.

## 5. Stage 3 — after the move (each its own change, none inside the cutover)

1. **Docs, same session as the cutover:** `CONSTANTS.md` (Infra "NAS still hosts InfluxDB" rows,
   deploy layers, the `lease_dir` row), `docs/ARCHITECTURE.md`, `docs/INTERFACES.md` §2's
   "reachable over the Docker `weather-net` network" wording, ops `NAS-RUNTIME.md` / `CONSTANTS.md`
   §5 "presented by", dashboard `MARVIN-MIGRATION.md`. `BOOT.md` current-state table.
2. **Consistent pre-backup dump:** `weewx-influxdb-backup.service`/`.timer` at 03:15 (the
   `weewx-db-dump` slot) — `docker exec weewx-influxdb influx backup /var/lib/influxdb2/backup/latest`
   into a path restic's 03:30 `/srv` run picks up; a file-level copy of a live TSM/bolt tree is not a
   backup (COMPUTE-NODE.md §3). Needs the CLI operator config to be valid — check it, don't assume
   (dashboard `influx/README.md` §9's orphaning trap). Foundation's store had **no backup at all**;
   this is the first time the weather history is versioned.
3. **`influx.py`'s NAS-LEASE courtesy yield is moot**, not broken: weewx now has zero NAS I/O to
   yield. Leave `lease_dir` set (harmless no-op against the empty dir, MARVIN-DEC-0063); close the
   `BACKLOG.md` cross-host-wiring item as overtaken; a later config-only cleanup may drop the key.
4. **Retire the Foundation instance** at ops#260 step 4 with Container Manager: `docker rm influxdb`
   + archive `/volume1/docker/influxdb/` (owner). Not before the drill has run.
5. **Bind tightening** (`-p <MARVIN_IP>:8086:8086` or a docker network for eh-proxy) — optional,
   later, its own DEC.
6. **Drill section (ops#260 acceptance), weewx's part:** with Foundation dark, `curl
   http://<MARVIN_IP>:8086/health` passes, weewx's log shows Influx posts succeeding with in-window
   timestamps, `verify_archive_fresh.py` green, `marvinctl unit weewx-influxdb.service` active — and
   nothing on marvin references `<NAS_IP>:8086` any more (`grep` over the three env/conf files, owner-run).

## 6. Rollback (any time before stage 3 item 4)

Consumers repoint back (the same three edits, reversed) and `/usr/local/bin/docker update
--restart=unless-stopped influxdb && /usr/local/bin/docker start influxdb` on Foundation. Data written
to marvin in between: the `weewx` bucket is regenerable from SQLite with `backfill_influx.py`; `eh_rollup`
by dashboard's Task backfill procedure (`influx/README.md` §5). Nothing needs a reverse copy.

## 7. What does NOT change

The data contract (`docs/INTERFACES.md` §2: measurement `record`, series key `binding=archive`,
unit-suffixed field names, `*_qc` flags), every token, the org, both buckets, the Task, the engine
version, weewx's write cadence, the dashboard's queries. A consumer that only knows the schema
notices nothing but a URL.
