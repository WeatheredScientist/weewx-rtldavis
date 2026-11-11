# windGust10 archive column — prod migration plan (DEC-0232)

Status: **plan, not run.** Owner-run: every step that writes goes through `marvin-sudo` or a
restart. Written S198b, 2026-11-10. Run the commands from the repo root on the Mac, one per line.

## What changes, and what does not

- The prod archive (`weewx.sdb`, wview-extended, US units) gains one `REAL` column, `windGust10`,
  and its daily summary table `archive_day_windGust10`. That is all `weectl database add-column`
  does (checked in WeeWX 5.5.2's `manager.py`).
- **No image and no config change.** The running v2.4.0 driver already puts `windGust10` (m/s,
  unit group registered, DEC-0224) on every loop packet that carries message 9; `StdConvert` makes
  it mph; the record already reaches InfluxDB as `windGust10_mph`. Only the column is missing.
- **A restart is required.** A running `weewxd` reads the column list once, when it opens the
  database, and writes only those columns. Until it restarts, the new column stays NULL.
- New installs get the column from the next image (`user.rtldavis.schema`); that path never
  touches an existing archive.
- Rows written before the restart read NULL. A minute without a message-9 packet also reads NULL
  (about a third of minutes), never 0.

## Steps

### 0. Read before writing

- `marvinctl --tenant weewx stat /srv/docker/weewx/weewx-data/archive/weewx.sdb` — note the size;
  step 1 needs that much free space twice (the nightly dump plus the kept copy).
- `marvinctl --tenant weewx ls /srv/docker/weewx/weewx-data` — note the files, to compare after
  step 3 (no new `weewx.conf.<timestamp>` should appear: `add-column` does not rewrite the config).

### 1. Back up

The `weewx-db-dump.service` unit makes the nightly consistent copy with SQLite's online backup API,
as `t-weewx`, safe while `weewxd` writes. Run it now, then keep a named copy, since the 03:15 timer
overwrites `weewx.sdb.bak` every night:

- `ssh marvin-sudo systemctl start weewx-db-dump.service`
- `ssh marvin-sudo runuser -u t-weewx -- cp -p /srv/docker/weewx/weewx-data/archive/weewx.sdb.bak /srv/docker/weewx/weewx-data/archive/weewx.sdb.pre-dec0232`
- `marvinctl --tenant weewx stat /srv/docker/weewx/weewx-data/archive/weewx.sdb.pre-dec0232` —
  size close to step 0's, owner `t-weewx`, modified a moment ago.

### 2. Dry run

- `ssh marvin-sudo docker exec -u 996:986 weewx-rtldavis-v2 /opt/weewx-venv/bin/weectl database add-column windGust10 --config=/opt/weewx-data/weewx.conf --dry-run`

A `--- Logging error ---` / `/dev/log` traceback from `weectl` inside `docker exec` is harmless;
read the last lines.

### 3. Add the column

- `ssh marvin-sudo docker exec -u 996:986 weewx-rtldavis-v2 /opt/weewx-venv/bin/weectl database add-column windGust10 --config=/opt/weewx-data/weewx.conf -y`

Expect `New column windGust10 of type REAL added to database.` `-u 996:986` keeps any journal file
owned by `t-weewx` (a root-owned hot journal blocks the next open, DEC-0147). The `ALTER TABLE`
and the empty day table take well under a second; `weewxd`'s 30 s lock timeout covers it.

### 4. Restart

- `marvinctl --tenant weewx restart weewx.service`

Expect a short gap while the decoder resyncs, as at any restart. Check it the usual way (`grep
Added`, steps over 90 s).

### 5. Verify

- `ssh marvin-sudo runuser -u t-weewx -- sqlite3 -readonly /srv/docker/weewx/weewx-data/archive/weewx.sdb < ops/windgust10_check.sql`

Pass: `column` and `day table` both 1; the newest records after the restart carry `windGust10` in
about two minutes of three, in mph, equal to InfluxDB's `windGust10_mph` at the same timestamps;
today's day row exists. A value that never appears after several minutes means the restart did
not happen or the column went to another database: stop and look before going on.

### 6. Backfill from InfluxDB (optional; the owner approved shipping it)

InfluxDB has held the same value since 2026-10-28 12:30 ET (DEC-0224). Run after step 4, so the
backfill reaches up to the minutes the running `weewxd` already fills. The script only reads
InfluxDB (through the dashboard's read-only Flux proxy, no token) and writes a SQL file:

- `python3 ops/backfill_windgust10.py --query-url <proxy_origin>/query --out "$TMPDIR/gust10.sql"`

It prints the point count and the local dates covered. The SQL sets only NULL cells at existing
rows, requires `usUnits = 1`, and runs in one transaction under `.bail on` (no column = nothing
committed). Apply it as `t-weewx`:

- `ssh marvin-sudo runuser -u t-weewx -- sqlite3 /srv/docker/weewx/weewx-data/archive/weewx.sdb < "$TMPDIR/gust10.sql"`

Expect `cells set:` close to the printed point count, minus the minutes the restarted `weewxd`
already wrote. A smaller number is fine when archive rows are missing (an outage); a zero means
the column or units check failed.

### 7. Daily summaries for the backfilled days

The backfill fills archive cells; the day table still holds only what `weewxd` wrote after step
4. Rebuild past days now and the migration day tomorrow. `rebuild-daily` takes **local** dates and
is safe while `weewxd` runs on a day it is no longer writing:

- `ssh marvin-sudo docker exec -u 996:986 weewx-rtldavis-v2 /opt/weewx-venv/bin/weectl database rebuild-daily --config=/opt/weewx-data/weewx.conf --from=2026-10-28 --to=<the day before the migration> -y`
- next day: the same command with `--date=<the migration day>` in place of `--from`/`--to`.

Then step 5's check again: one day row per date since 2026-10-28, with a `max_windGust10`.

### 8. After a week

Delete `weewx.sdb.pre-dec0232` once nothing has gone wrong (it sits in the directory HLF mounts
read-only; HLF opens `weewx.sdb` by name, so the copy is only disk).

## Rollback

- **Default: none needed.** The column is additive. No consumer reads it unless it asks for it by
  name (the dashboard's adapter lists columns with `PRAGMA table_info`; HLF names its 16 columns),
  and `weewxd` writes one more `REAL` per record. Leaving it in place is the rollback for anything
  short of corruption.
- **Remove the column:** `weectl database drop-columns windGust10 -y` through the same `docker
  exec`, then a restart. In SQLite this copies the whole archive table under one write lock, and a
  `weewxd` write that waits more than 30 s fails that record. Time it first on the step 1 copy.
- **Restore the backup** (corruption only): stop `weewx.service`, `cp -p` the `.pre-dec0232` copy
  over `weewx.sdb` as `t-weewx`, start it. Every record since step 1 is lost from the archive;
  InfluxDB keeps them.
