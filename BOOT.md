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

## ▶ Resume here (S81 → S82)

### What's settled (do not re-derive)

**Campaign B: v2.0.13/ws.5 in prod, `prod-baseline-20260811` tagged.** Square shifted a THIRD
time (DEC-0082 S75, DEC-0087 S79, **DEC-0089 S81**) — runs **08-15 → 08-23T00:05**. Holding on
**H**, confirmed live (state file, no STOP/PAUSE).

**S81: DEC-0087's first live exercise found a real bug in its own resume logic — fixed as
DEC-0089 (PR #177, merged).** Three short dips (2026-08-13 19:14–19:38) tripped `PAUSE` at
`19:40:05` (arm H). Reception then read healthy continuously from `19:43` for ~2h, but
`recovered_since()` only checked for a `RECEPTION RECOVERY` line — an ALERT→RECOVERY *edge* —
which never fired again since reception never re-alerted. The pause rode the full 120-min
ceiling into a needless `ABORT` at `21:45:01`; the resulting STOP blocked every tick for 10.5+
hours, straight through arm-A's `00:05` swap, found next session start. **Fix:** also check the
monitor's periodic `RECEPTION: NN% ... [OK]` line (a level signal) as an additive fallback to the
edge check. 4 new tests, 242/242 full suite. Deployed with a third +24h schedule shift
(sha-verified), STOP cleared after. **Post-clear silence is expected, not an incident** — see the
new `due_arm()` gotcha below before reading it as a dead cron job.

**Next session: the state-machine audit, on Fable 5.** Two sessions running (DEC-0088, DEC-0089)
each found a "signal blind spot" bug in just-shipped campaign automation — a pattern, not a
coincidence. Scope: `ops/rx_experiment.sh`'s full guard/tick/abort/pause/resume state machine +
`weewx_monitor.py`'s alerting/reset logic, hunting for other edge-vs-level signal mismatches in
the same class. Verify every finding against real log evidence before proposing a fix (both real
bugs here were only confirmed that way). **User's explicit model choice: Fable 5** — judgment/
investigative work per AGENT-ECONOMY.md, escalate off the Sonnet floor at session start.

**DEC-0088 (S80, freeze_baseline.py fix) and the DEC-0083 stall-burst plateau both hold**,
untouched this session (freeze/stall side not touched).

**Dependabot PR #158 (weewx 5.4.0→5.5.0) still deliberately deferred** — no base-platform bump
mid-campaign; revisit post-campaign (~08-23) with v2.0.14.

### ▶▶ S82 JOB LIST

1. **The state-machine audit, on Fable 5** — see above. This is the user-chosen next session;
   run it whenever convenient, doesn't depend on job 2 below.
2. **Verify arm-A's fresh block 1 — due `2026-08-15T00:05`.** Tick log should show
   `swapping H -> A` and `arm A live and healthy`.
3. **Watch for DEC-0089's fix to prove itself on a real pause**, if one occurs — first live
   exercise of the corrected `recovered_since()`. A clean pause + auto-resume via the new
   periodic-`[OK]` path needs nothing from you.
4. Daily square watch (~5 min): `ops/soak_check.sh`, STOP **and PAUSE** both absent, state matches
   schedule.

### Current state (S81 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**, untouched — only `rx_experiment.sh` (NAS-resident) was deployed |
| Campaign B | Holding on **H**, confirmed live; arm **A** now due `2026-08-15T00:05`, square through `08-23T00:05`. STOP and PAUSE both absent |
| Pause/resume (DEC-0087/0089) | Exercised once (19:40:05), revealed and triggered the DEC-0089 fix — a genuinely healthy pause+auto-resume cycle still unobserved |
| Freeze rate | DEC-0088-corrected (1.31/day), unchanged this session |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | `dev` synced with `origin/dev` (`6079053`); PR #177 merged this session. `main` unchanged. Only `dependabot/pip/weewx-5.5.0` (#158) remains beyond `dev`/`main`, deliberately deferred |

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
  `readconf`. Its documented `command`-prefix escape hatch does NOT clear it (found S75). **Recurred
  S81 on an unrelated file** — `scp`-ing `ops/rx_experiment.sh` (no secrets) tripped it too, most
  likely on the `. nas.env` sourcing in the same command, not the destination. Fallback: hand the
  owner the single command — **say explicitly it runs on the Mac, not the NAS** (S81: an unstated
  location cost a round trip when run from a NAS shell instead).
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **`nasctl` is read-only** — NAS mutations (clearing `rx_experiment.STOP`, deploying the script
  itself when the guard above doesn't intervene) need the Class C mint path: confirm in chat,
  mint, re-run identical. Worked cleanly S74/75/78/79/81.
- **`due_arm()` never returns `NONE` once the pilot block has run** — its last pilot row (`H`)
  is the implicit hold value until the square's first row, so `tick`'s silent no-op
  (`want == have`) can run for hours with zero log output — found S81, briefly read as a dead cron
  job after a schedule shift. Check `current_arm()`/state + STOP/PAUSE directly, not log silence.
- **`rx_experiment.sh` the SCRIPT lives flat at the NAS project root**
  (`/volume1/docker/weewx-rtldavis/rx_experiment.sh`), not under an `ops/` subdirectory — but its
  LOG output does not: `rx_experiment.log`/`.STOP`/`.PAUSE`/`.state` split across two different
  places (`.state`/`.STOP`/`.PAUSE` flat at the project root next to the script; `.log` and
  `_data.log` under `logs/`, alongside `weewx.log`/`weewx_monitor.log`) — confirmed S80 the hard
  way (a `nasctl tail` on the flat path 404'd). `nasctl ls` the actual directory before assuming
  either layout.
- **`nasctl grep` takes `<pattern> <file>`, pattern first** — same order as real `grep`, but easy
  to get backwards by analogy with `nasctl cat`/`tail`/`ls <path>`. Reversed, the file path gets
  treated as the pattern and rejected as "not metacharacter-free" — a confusing error that doesn't
  name the actual mistake. Found S80.
- **Merging several same-session PRs in sequence: re-`git fetch` before every merge-into, not just
  the first.** S79: fetched fresh before merging dev into PR #173's branch (correct), then reused
  that now-stale `origin/dev` ref for a third branch's merge after #173 had since merged on
  GitHub — silently dropped #173's doc changes, no conflict, no error, `git merge` just used what
  it had. `git log --oneline -3 origin/dev` right before each merge-in is the check.

_Last updated: 2026-08-14 (S81 close) — DEC-0087's first live pause/resume exercise found a real
bug in its own resume logic; fixed and shipped as DEC-0089 (PR #177, merged to `dev`), deployed
with a third +24h schedule shift, STOP cleared, live state verified healthy. Arm-A now due
2026-08-15T00:05. Next session: the state-machine audit (guard/pause/abort/resume), user's
explicit choice to run on Fable 5 — carried to S82 alongside arm-A verification and the daily
square watch._
