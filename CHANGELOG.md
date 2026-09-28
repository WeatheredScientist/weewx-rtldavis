# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S143] — 2026-09-27 — The loop feed moves into `weewx-data/feed/`, and `eh-proxy` now mounts only that (`eaglehunt-ops#348` complete, DEC-0202); PR #396 merged

- **PR #396 merged** (S142's DEC-0201 and handoff) as squash `0d79daf` at 22:30 ET. S142's worktree
  and branches were removed, along with the stale `claude/pensive-borg-1958f0` (its one commit
  landed as PR #338 on 2026-09-05).
- **`eaglehunt-ops#348` step 1 applied, owner-approved.** The dashboard (S316) and marvin (S54)
  agreed on a symlink transition that needs no synchronized window.
  - `[LoopJsonWriter]` `path`/`current_path` now point at `/opt/weewx-data/feed/` in the live conf
    and in the tenant-root `weewx.conf.rx-baseline`. The baseline went through the owner root route
    as t-weewx at 22:54:57 ET. The live conf went as 996 via `marvinctl exec` at 22:56:28, after a
    dry run. Both stay 0600, and the pre-edit copies are in `conf-archive/`.
  - `feed/` was created at 0755. weewx restarted at 22:56:50, and the writer's startup line names
    the feed paths. The first packet landed about 106 s later.
  - At 22:58:37 the top-level `loop-data.txt` and `current.json` were swapped atomically for
    relative symlinks into `feed/`.
  - Right after, eh-proxy served `/loopdata` 200 at 1.4 s old. There were 0 ERROR, CRITICAL or
    tracebacks since the restart, against 101 INFO lines.
- **`eaglehunt-ops#348` finished the same night.** marvin flipped `eh-proxy`'s mount to `feed/` at
  23:20:56 ET (MARVIN-DEC-0183), and the dashboard's check passed at 23:22. weewx removed the two
  symlinks at 23:26:57 as t-weewx, leaving `feed/` untouched. Afterwards eh-proxy served `/loopdata`
  200 at 0.2 s old, with 0 errors against 27 INFO lines. Each step was posted on #348 and rung to
  the other two repos. The #396 merge was also posted on `eaglehunt-ops#347`, so heartofgold can
  tick weewx's row.
- **Docs:**
  - DEC-0202.
  - `CONSTANTS.md`: the Loop-JSON and compat-path rows, plus a new live-config deviation row
    carrying marvin's two `feed/` rules.
  - `docs/INTERFACES.md`: the paths are configurable, and a consumer must bind the directory, not
    the files.
  - `docs/CONVENTIONS.md`: its S55-era infra table, a stale second copy that still named the NAS as
    prod, is now a pointer to `CONSTANTS.md` (BOOT job 8's CONVENTIONS item).
  - `docs/GOTCHAS.md` §1: `weewx.log` timestamps are ISO, so a syslog-shaped window filter reads as
    a false zero.
  - `docs/GOTCHAS.md` §3: `ssh -G` trips the marvin guard, and ConfigObj needs
    `interpolation=False`. The second was re-hit because §3 went unread before the marvin task.
- Gate: ruff clean · 516 passed / 17 skipped · mypy clean, 72 files (fresh cache) · secret gate 0 on the
  staged files, positive-controlled (identifier, private-IP and credential plants each exit 1).

## [S142] — 2026-09-27 — Config backups moved out of the shared `weewx-data` top level into a 0700 `conf-archive/` (DEC-0201); `CONSTANTS.md` NAS rows corrected

- **Premises re-checked read-only first.**
  - The NAS overlay that `CONSTANTS.md` described was retired on 2026-09-05 (MARVIN-DEC-0134).
    `nfs-server` is disabled on marvin, the NAS path is gone, and there are no NFS client mounts.
    `/volume1/docker` holds only DSM system folders, and its `#recycle` is empty.
  - On marvin, a sweep of every container's mounts found the dashboard's `eh-proxy` (994:984)
    mounting all of `weewx-data`. File mode is the only boundary there.
- **Applied 2026-09-27 19:13:58 EDT, owner-approved.** One `marvinctl exec` as t-weewx moved 27
  `weewx.conf.*` backups and a pre-S13 zip into `weewx-data/conf-archive/` (dir 0700, files 0600).
  The script pinned the file list and aborted on any drift; it was dry-run in five cases first. The
  live conf was untouched and there was no restart. A names-only sweep afterwards found nothing else
  credential-shaped in reach.
- **Found a recurrence path in weewx 5.5.** `weecfg.save()`, which every conf-rewriting `weectl`
  command uses, parks `weewx.conf.<timestamp>` beside the live conf and rewrites the live conf at
  umask 0644. The re-chmod-and-archive rule is now in `CONSTANTS.md` and `GOTCHAS.md` §3.
- **Filed `eaglehunt-ops#348`** for the dashboard and marvin: narrow `eh-proxy`'s mount to a feed
  subdir. Single-file binds won't work, because atomic renames pin a stale inode. The specifics are
  in the gitignored local-infra doc, and rotation is the owner's separate call.
- **DEC-0200 confirmed on the InfluxDB side** (HLF S349): the `weewx` bucket reads UV exactly 0
  from 18:30 ET. `eaglehunt-ops#343` closed with a comment (S141's job 2).
- **`eaglehunt-ops#347` answered (owner-approved in chat).** `CLAUDE.md`'s Estate context block
  was re-adopted verbatim from heartofgold's 2026-09-27 app block (MARVIN-DEC-0180), with
  `<service>` = `weewx`. The deployment record is now `heartofgold/host/` (the units plus
  `tenants.d/weewx.conf`), not the deleted `compose/weewx/`. The image pin stays on the box.
- **The secret gate's identifier check was silently skipped in this worktree** (its gitignored
  pattern file doesn't follow a worktree). The file was copied in, and the check was then run live
  and positive-controlled (`GOTCHAS.md` §1).
- Docs: DEC-0201; `CONSTANTS.md` (NAS rows re-verified against live state, plus a new live-config
  row); `GOTCHAS.md` §1 and §3; `BOOT.md`. S138's entry rolled to `CHANGELOG-ARCHIVE.md`.
- Gate: ruff clean · 516 passed / 17 skipped · mypy clean, 72 files · secret gate 0, with the IP
  and identifier checks each positive-controlled.

## [S141] — 2026-09-27 — UV diode-floor correction: DEC-0080's exact-code zero extended to UV's two dark codes (DEC-0200, `eaglehunt-ops#343`)

- **Checked in with ops on `#343`.** The thread had closed 23 s after the owner put the UV fix on
  weewx. Posted the measurement and asked ops to confirm there was no later stand-down call
  ([comment](https://github.com/WeatheredScientist/eaglehunt-ops/issues/343#issuecomment-5860016912)),
  then rang the ops session.
- **Measured before designing (prod archive, 08-12 → 09-27).** UV's dark floor is two codes, not
  one: `uv_raw 2` (0.04) in 96.9% of rows, `uv_raw 1` (0.02) in 2.5%, in runs of minutes, and never
  0 or 3. The same pass re-verified DEC-0080's solar floor as clean: one code, with `sr_raw 2` only at
  twilight.
- **The owner chose the two-code exact window**
  `UV = UV if UV is None else (0 if 0.01 < UV < 0.05 else UV)` over the thread's one-code line.
  `weewx.conf.example` carries it. The new `tests/test_diode_floor_corrections.py` pins both
  diode-floor lines under weewx 5.5's own `StdCalibrate` eval semantics (10 tests,
  positive-controlled).
- **Applied live 2026-09-27 17:39:57 ET.** A container dry-run came first. The owner approved the
  Class C root-route `sed` over the live conf and the tenant-root `.rx-baseline`; the mint was refused
  once and succeeded on the ladder's retry. `weewx.service` restarted at 17:40:18 and booted clean.
  First dusk verified the same evening: UV read 0.0 from 18:29 with solar ~16 W/m², where it
  read 0.04 before the fix. The full-overnight check is `BOOT.md` job 1.
- Docs: DEC-0200; a `CONSTANTS.md` live-config deviations row; `docs/INTERFACES.md` now says the
  radiation/UV dark floors are zeroed by config, with this station's apply dates.
- Gate: ruff clean · 516 passed / 17 skipped · mypy clean, 72 files · secret gate 0
  (positive-controlled).
