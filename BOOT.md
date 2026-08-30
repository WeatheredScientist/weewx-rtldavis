# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3 — the "escape the WeatherLink lock" tool. A public, published
WeeWX extension (Docker Hub + GitHub releases), GPLv3. Its real contract is the **data it emits**
(loop-JSON + InfluxDB line-protocol schema), not any one consumer. The dashboard that consumes it
is a **separate repo** — don't make dashboard changes here.

---

## ▶ Resume here (S107 → S108)

### What's settled (do not re-derive)

**The marvin alerting rebuild is BUILT and MERGED-READY, but deliberately NOT DEPLOYED (DEC-0120,
answers ops#233).** Read the DEC before touching it; the short version is that the 08-29 false-alert
episode was **not** a wrong path. Every threshold in `weewx_monitor.py` is "nothing seen for N
seconds", and a frozen input satisfies all of them at once — so it structurally could not tell *the
station is down* from *I am blind*. Repointing the path would have fixed the instance and left the
mechanism. Now: staleness is checked **before** any threshold (worse of log mtime and newest parsed
line timestamp), raised as its own alert class, and it suspends uploader/reception judgement while it
holds. `REMEDY_MODE` replaces the assumed USB reset (`usb_reset` default for Synology,
`restart_unit` for marvin, `none` = detect-only). Campaign inhibit added. New
`ops/weewx-monitor.service` ships at `REMEDY_MODE=none`.

**ops#233's premise was wrong in a way that made the job easier: marvin's
`/srv/docker/weewx/logs/weewx.log` is alive, local and healthy** — growing continuously, rotating
daily, bind-mounted. The "no path to the log" problem exists only when looking *from Foundation*.

**Today's 4-hour gain campaign was refused on this repo's own power math, and the owner agreed.**
DEC-0059 measured 24 h/arm resolving 1.1 pts; 4 h splits to ~2 h/arm → MDE **~3.8 pts against a
2.0-pt effect** (~3.6× too short; confirmed two independent ways). It would have returned "no
difference" nearly regardless of truth. A properly-powered 2-arm run needs **~15 h**. Do not let this
be re-proposed as a short run.

**Prod is running gain 372 while DEC-0115 adopted 496.** The 08-29 migration incident set 372 without
a controlled comparison and the aborted campaign's exit trap codified it as the restore value.
**Owner's decision: hold 372 until measured** — this is deliberate, not drift-in-waiting.

**marvin is clear for RF work.** Its GPU passthrough bind completed and is final since 08-29; no
hardware work scheduled. Caveat that matters for any measurement: the 2070 now lives in the win11
guest **full-time, driver-active even at idle**, and owner gaming is ad-hoc — an uncontrolled EMI
variable unless hands-off is declared for the window.

### ▶▶ S108 JOB LIST

**Live, in order:**
1. **Run the overnight 2-arm gain campaign (372 vs 496, ~15 h).** **Fully pre-registered in
   `BACKLOG.md` (S107) — read it there, don't re-derive.** Arms/order/blocks/exit-trap/abort floor
   are locked, and the power was re-checked against marvin's *own* measured noise (block sd 0.936
   pts at 90 min, 0.84× Foundation's): **the 15 h design gives MDE ~1.66 pts against the 2.0 bar —
   it clears, with margin.** Still needs: a marvin-side session to deploy the transient unit (we
   have no arbitrary file write), and **an owner hands-off-the-guest declaration** for the window
   (the 2070 is attached to win11 full-time; ad-hoc gaming is the one uncontrolled EMI variable).
   ⚠ Prior worth knowing before reading results: **marvin @372 already measures 73.88%**, within
   ~0.95 pts of Foundation @496 — so 496 repeating its 2.00-pt win here is not the safe assumption.
2. **Deploy the S107 alerting** — *after* the campaign, never before (it would fight the per-arm
   restarts). Deploy `weewx_monitor.py` from the **merged `dev` tip**: marvin's copy is already
   **stale vs `dev`** (sha mismatch, 50026 vs 50538 bytes — the ops#214 family).
3. **Verify the archive DB is readable unprivileged before enabling the reception-summary path.**
   `weewx.sdb` is mode `0500 t-weewx`, written by root in-container. If it is WAL, a `?mode=ro` open
   may fail needing `-shm` write — DEC-0119's bug class. **Unverified; do not assume either way.**
4. **Then** flip `REMEDY_MODE=none` → `restart_unit`, but only once `t-weewx` actually holds a
   restart grant (sudoers or a marvinctl tier-2 verb). Setting it without one yields a remedy that
   fails every time while looking correct (DEC-0061).
5. **`usb_watchdog.sh`'s fate** — still simply OFF, still undecided. ops#233's sibling finding.

**Carried forward, untouched:**
6. **`main` promotion for v2.0.14** — deliberately deferred (DEC-0114).
7. **Convert `ops/rx_experiment.sh` to the DEC-0117 control file** — gated on job 8.
8. **DEC-0117 hot swap needs an image rebuild to reach prod** (off by default). Still unverified
   whether marvin can build natively vs. repeating the `docker save`/`load` dance.
9. **Foundation decommission timing** — owner's call, after a week-plus soak.
10. **NAS-LEASE cross-host wiring** — low priority; marvin's `/nas-lease` is a deliberate no-op.
11. **`CONSTANTS.md`'s infra section second pass** — still not re-verified row by row. S107 captured
    the authoritative `docker run` line from `marvinctl unit weewx` if that helps the next pass.
12. **Sanity-check ops' `CONSTANTS.md` §5 register row** for weewx's token (`ef8e9af8`).

**Retired this session:** ~~merge PR #282~~ (was already merged before S107 began);
~~revert `debug_rtld` 3→2~~ — **stale job, live config is already at 1**.

### Current state (S107 close)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` (a restart IS a full recreate) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, **gain 372** (owner-held pending measurement; adopted value is 496) |
| Alerting | **Built, not deployed.** Foundation's `weewx_monitor.py` + `usb_watchdog.sh` still OFF — marvin has zero alerting from this repo until job 2 |
| marvin GPU bind | Complete + final since 08-29; 2070 attached to win11 full-time, driver-active at idle |
| `marvinctl` | Tier-1 reads proven (needs `--tenant weewx`). No SQL verb — an archive-DB readout needs a marvin-side session |
| Campaign | Refused today on power grounds; ~15 h overnight run agreed, not yet scheduled |
| Trackers | ops#233 answered by DEC-0120 (not closed — deploy outstanding) · #216/#214/#110 open · repo #274/#253 open |


## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven on
   the NAS specifically. S105 added a data point (independent confirmation on different hardware,
   firing only under a bad USB controller); untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). Untouched this session.
3. **ERR-0005** — unchanged.
4. `ppm`/`fc` — still unmeasured; deliberately unchanged for Campaign B, no sweep data to fall back on.

## Model tier

No `/model` switch this session. Nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-29 (S106 close). Green gate: ruff clean, 428 passed / 8 skipped, mypy clean
(65 files), secret gate clean. Shipped: ops#183's Influx outage fully remediated and backfilled
(DEC-0119), `ops/backfill_influx.py` hardened (PR #282), `weewx_monitor.py`'s stale-watch-path blind
spot found and disabled — full narrative in `CHANGELOG.md`._
