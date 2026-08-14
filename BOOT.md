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

## ▶ Resume here (S82 → S83)

### What's settled (do not re-derive)

**Campaign B: v2.0.13/ws.5 in prod, `prod-baseline-20260811` tagged.** Square runs
**08-15 → 08-23T00:05** (third shift, DEC-0089). Holding on **H**; arm **A** due
`2026-08-15T00:05`.

**S82: the state-machine audit ran (DEC-0090) and shipped five `rx_experiment.sh` fixes —
PR #179 merged, deployed 10:38, sha `4438a2a3…` verified.** (1) A pause now resumes at the
`ABORT_PCT` floor, not the monitor's `[OK]` tag — the occupied [50,60) band could enter a pause
it could never exit; (2) `recovered_since()` + the guard's floor mean read the rotated `.1`
monitor log (rotation is 00:05 — the exact swap minute); (3) a due swap **defers** while paused
instead of swapping into the episode (BASELINE exempt); (4) the guard stands down once
arm=BASELINE (was armed forever between campaigns); (5) tick/guard/abort serialize behind a
mkdir lock (dead-holder break, 1800s hung-holder ceiling — the 08-11 02:05:03 interleave was
live evidence). Plus: `soak_check.sh`'s reset counter had grepped a message retired at S67 and
read 0 ever since ("1 of 0" was the tell) — fixed. 39/39 file, 251/251 suite.

**Monitor-side findings went to #180 (tier:mid, spec in the issue, Sonnet-fit):** episode state
is memory-only (a restart mid-episode silently loses the ledger row + RECOVERY edge), midnight
weewx.log rotation zeroes `wu_bad_windows` and falsifies a pending reset verdict, and
`do_reset`'s exception path never emails (timed out live 08-14 01:56:30).

**Dependabot PR #158 (weewx 5.4.0→5.5.0) stays deliberately deferred** — no base-platform bump
mid-campaign; revisit post-campaign (~08-23) with v2.0.14.

### ▶▶ S83 JOB LIST

1. **Verify arm-A's block 1 swapped in at `2026-08-15T00:05`** — tick log `swapping H -> A` +
   `arm A live and healthy`. This is also the S82 code's first live working tick (lock +
   deferral active): if the swap did NOT happen, check for a PAUSE first — a deferred swap is
   now legitimate behavior, not a fault — then for STOP.
2. Daily square watch (~5 min): `ops/soak_check.sh`; STOP **and PAUSE** both absent; state
   matches schedule.
3. **Watch the revised resume machinery on a real pause** — floor-resume + rotated-log reads
   have no live exercise yet (n=0 on the S82 mechanism; BACKLOG watch updated).
4. **#180 (monitor package)** when a session has room — mechanical once designed, deploy needs
   the owner-run kill dance (memory + issue both carry it).

### Current state (S82 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**, untouched — only NAS-resident `rx_experiment.sh` redeployed |
| Campaign B | Holding on **H**; arm **A** due `2026-08-15T00:05`, square through `08-23T00:05`. STOP and PAUSE both absent |
| rx_experiment.sh | S82 five-fix version live (sha `4438a2a3…`), owner-run scp fallback (read-guard, as S81) |
| Freeze rate | DEC-0088-corrected (1.31/day), untouched this session |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | `dev` = `origin/dev` (#179 + S82 close merged). Only `dependabot/pip/weewx-5.5.0` (#158) beyond, deferred |
| Cross-repo | ops#163 closed (OPS-DEC-0101 carry) · ops#165 filed (sweep exemption) · weewx#180 filed (monitor trio) |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (S80 measurement via
   `ops/freeze_baseline.py`, DEC-0088-corrected), separate phenomenon** from DEC-0081's episodes.
   **Still hard-aborts — DEC-0087 deliberately does not cover freezes** ("RF re-established" isn't
   a meaningful resume condition for a process-wedge event). Root cause still unproven (thread
   blocking on the bind-mounted log volume is the leading hypothesis, DEC-0067/0068).
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open): interference vs no-LNA
   front-end margin vs site vs condensation. **DEC-0083 adds a dated onset (08-10 23:56) the
   characterization should start from** — it coincides with the campaign-B pilot night and the
   v2.0.12 promotion, neither of which is established as cause.
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-stall episode remains
   the largest on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Gotchas that survive here because they are NOT in the canonical docs

- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone.
- **`secret-read-guard.sh` matches by basename** — read `ops/wxcheck.sh` / any `weewx.conf` with
  `readconf`. Its documented `command`-prefix escape hatch does NOT clear it (found S75). **Trips
  the rx_experiment.sh `scp` deploy every time** (S81, S82 — likely the `. nas.env` sourcing):
  the settled fallback is handing the owner the single command — **say explicitly it runs on the
  Mac, not the NAS**. Ran cleanly that way S82.
- **`rx_experiment.lock` exists only during a pass's critical section** — absence at rest is
  correct; a holder older than 1800s is broken automatically and loudly ("breaking stale lock").
  Don't read a missing lock as "the cron is dead".
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **`nasctl` is read-only** — NAS mutations need the Class C mint path (confirm in chat, mint,
  re-run identical — mint and re-run as TWO separate calls). Worked S74/75/78/79/81; S82's scp
  fell through to the read-guard fallback above instead.
- **`due_arm()` never returns `NONE` once the pilot block has run** — its last pilot row (`H`)
  is the implicit hold value until the square's first row, so `tick`'s silent no-op
  (`want == have`) can run for hours with zero log output — found S81, briefly read as a dead cron
  job after a schedule shift. Check `current_arm()`/state + STOP/PAUSE directly, not log silence.
- **`rx_experiment.sh` the SCRIPT lives flat at the NAS project root**
  (`/volume1/docker/weewx-rtldavis/rx_experiment.sh`), not under an `ops/` subdirectory — but its
  LOG output does not: `.state`/`.STOP`/`.PAUSE`/`.lock` flat at the project root next to the
  script; `.log` and `_data.log` under `logs/`, alongside `weewx.log`/`weewx_monitor.log` —
  confirmed S80 the hard way. `nasctl ls` the actual directory before assuming either layout.
- **`nasctl grep` takes `<pattern> <file>`, pattern first, single-word patterns only** — reversed
  arguments are rejected with a confusing "not metacharacter-free" error (S80); multi-word
  patterns silently return a FALSE ZERO through the ssh quoting layer (S53). Positive-control any
  zero count.
- **Merging several same-session PRs in sequence: re-`git fetch` before every merge-into, not just
  the first.** S79 silently dropped a merged PR's doc changes by reusing a stale `origin/dev` ref.
  `git log --oneline -3 origin/dev` right before each merge-in is the check.

_Last updated: 2026-08-14 (S82 close) — the state-machine audit (DEC-0090) shipped five
rx_experiment.sh fixes + the soak reset counter, merged (PR #179) and deployed sha-verified the
same morning, before the square's first block; monitor-side trio specced to #180; ops#163
closed / ops#165 filed. Arm A due 2026-08-15T00:05 — the new code's first live exercise._
