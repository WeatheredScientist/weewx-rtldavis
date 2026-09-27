# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

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

## [S139] — 2026-09-19 — `docs/ARCHITECTURE.md` re-verified against live marvin state (BOOT job 5)

- Doc hadn't been touched since S17 (2026-07-04) and had drifted across the DEC-0118 marvin move:
  stale weewx version (5.3.1 → 5.5.0, verified live), stale LNA/bias-tee claim (LNA is out,
  `BIAS_TEE=0`), a NAS-pathed mount table duplicating (and out of sync with) `CONSTANTS.md`'s own
  table, and a NAS-side monitor section describing a DSM-Task user that no longer exists. Section
  3's mount table is now a pointer to `CONSTANTS.md` instead of a second copy (STANDARD rule 5).
  Section 7 rewritten for `weewx_monitor.py`'s current shape: `weewx-monitor.service`,
  `User=t-weewx`, `REMEDY_MODE=none`, and why `usb_reset.sh` doesn't apply on marvin's topology.
  `CONSTANTS.md` itself checked out accurate on everything verifiable — no changes needed there.
  Two rows stay flagged unverified (marvin host tool availability, `LOCAL_INFRA.md`'s marvin
  entry) — both need either an interactive host shell or reading a secret-bearing file the
  read-guard rightly blocks. PR #392.
- Closeout ran late (this entry + the `BOOT.md` pointer rewrite land at S140's session start,
  per `ops#218`'s "closeout debt" recovery path — the session that did the work ended without
  running its own closeout).
