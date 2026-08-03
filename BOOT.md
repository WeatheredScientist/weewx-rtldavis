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

## ▶ Resume here (S63)

**S62 was an incident session. Campaign B was prepared, then deliberately HELD (DEC-0066).**
Prod went deaf three times on 08-02 — 105 min (**ERR-0005**), 3 min, and 10 min. Two of the three
are still **unexplained**. Diagnosis removed the LNA, so the swap night's physical step is done and
the schedule is shifted in-repo, but **do not launch until the instrument is trusted.**

### ⚠️ Read this before touching anything: S62 ended with work IN FLIGHT

| Thing | State |
|---|---|
| `s62-incident-followups` | **+8 commits, NOT landed.** All gates green. Land → merge → promote |
| `:v2.0.12` image | built locally as `weewx-rtldavis:verify-only` only — **NOT pushed**, and the release build must come from the **merged tip**, not the branch |
| Campaign B apparatus | schedule shifted in-repo; **NOT deployed to the NAS** (still campaign A's script there) |
| Watchdog (DEC-0065) | committed; **NOT deployed** — `weewx_monitor.py` is mounted, needs `scp` + owner restart |
| Prod right now | **v2.0.11**, LNA **out**, gain 372, recovered to ~69–73%, container up since 01:48 |
| Campaign A | **STOPped, sentinel in place, not resuming.** Do not clear it |
| Campaign B | **HELD (DEC-0066).** Schedule dates are a placeholder (08-10 → 08-19); `install` refuses a stale one |

### The schedule dates are a PLACEHOLDER — and a guard now enforces it

Dates currently read **08-10 → 08-19**. That is arbitrary: it exists only so nothing sits in the
past. **Re-shift the whole `SCHEDULE=` block to real dates when a launch is actually agreed** — a
pure constant offset, same method as S62 (39 substitutions; the structure tests confirm the square
survives).

You do not have to remember this. `install` now **refuses** a schedule whose first row has passed
and prints how to fix it (`schedule_started()`, S62/DEC-0066). That guard exists because
`due_arm()` picks the *latest* row already passed, so a stale schedule fails silently: it joins
mid-square with no pilot, or past the last row records the campaign complete without running it.
Both look like success. A `BOOT.md` warning would not have caught it — prose does not execute
(DEC-0040).

### Before B can launch (DEC-0066)

1. **Explain the two unexplained outages**, or bound them. A reception experiment run across
   intermittent unexplained deafness produces *data that looks like results*.
2. **Fix the DB-lock / uploader-thread defect** — see Blockers. It is what turned a momentary lock
   into a 10-minute outage.
3. **Deploy the watchdog** (`scp weewx_monitor.py` + owner-run restart).
4. Then: `land` → merge → promote + tag → rebuild `:v2.0.12` from the **merged tip** → push
   `:v2.0.12` (`:latest` only after our own station proves it) → regenerate the schedule → the
   Class C deploy steps → `install`.

`docs/CAMPAIGN-B-RUNBOOK.md` still governs the mechanics; only the timing is open.

### What we learned about the LNA — hold it loosely

~14 h at gain 372 with the LNA out: mean **72.6%**, **no hour-07 notch** (S58 measured a ~2 pt notch
LNA-in). Campaign A pooled: 72.4%, n=922. Looks like parity — **but A's figure pools all four arms
including gain 207, so it is biased LOW.** The clean comparison is B's 372 anchor against A's 372,
which is exactly why 372 is in both campaigns. **Do not conclude futility from this.** A's arm
winner stays sealed until after B.

**Root cause of ERR-0005 is still unestablished.** A container recreate fixed it; a `kill`+`start`
20 minutes earlier had not. Nobody knows why. That gap is why DEC-0065 declined to automate the
recreate.

**Model note (closeout step 6):** S62 ran on **Opus 5** — appropriate for a live prod incident, and
the owner was told at session start. Desktop switches **persist** (OPS-DEC-0062), so S63 inherits it
unless changed. Steps 1–4 above are execution, not judgment: **drop to Sonnet before doing them.**

## Blockers

1. **Two unexplained reception outages (08-02).** ERR-0005 (105 min) and a 3-min dropout at 13:47.
   Both: driver alive and healthy, zero packets, self-recovered or fixed by a container recreate.
   No established cause. **This blocks campaign B** (DEC-0066).
2. **`database is locked` is now a THREAD, not a one-off.** It caused a standalone 10-minute outage
   at 19:45 with no restart churn preceding it — S62 initially misread it as downstream noise and
   was wrong. Worse than the lock itself: **three uploader threads (OgoxeUploader, Influx, OWM)
   refused to shut down**, holding the teardown open ~100 s while the driver sat killed. That
   converts any momentary DB error into a multi-minute outage. Prior sightings: S59, twice during
   ERR-0005, then 19:45 standalone. The archive DB is read by the monitor (read-only, 6-hourly),
   the dashboard, and `weectl` — contention is tractable to investigate.
- **`ppm`/`fc` still unmeasured** and deliberately unchanged for B (would confound the LNA contrast).

## Ordered backlog

1. **Investigate the two unexplained outages** — the gate on campaign B (DEC-0066). Then the
   DB-lock/thread-hang defect. Then launch B.
2. **WeatherLink Live backfill for ERR-0005** — approved, not applied. ~7 records at
   `interval = 15` + `backfill = 1` flag, ERR-0003's path. Back up the DB first.
3. Post-campaign: LNA-in vs LNA-out grand comparison (A × B), final prod config decision, whether
   the LNA goes back in — and whether it was ever worth anything.
4. **`ppm`/`fc` measurement-by-value** — deferred, not forgotten (DEC-0060 recipe is minutes-long).
5. **`WU_RF_MIN_PCT = 60` may need retuning for the no-LNA regime** — it fired on a dew dip at
   03:15. Wants B's data, not a guess.
6. **Consider `.claude/transient-state`** (ops#113). Opt-in is this repo's call.
7. Keep-a-Changelog headings + DECISIONS entry-skeleton convergence (proposed S25, never picked up).

## Standing watches — read-only, none block the above

- **Unexplained reception dropouts** — promoted to Blocker 1, but keep watching the shape. 08-02
  gave 14 zero windows in 1106 (1.3%). On the same 5-window metric campaign A shows no zeros and a
  min of 26, so it is **not yet proven** these are new to the no-LNA regime — the metrics differ in
  resolution. Do not conclude the LNA's removal caused them.
- **Co-rejection grep** (DEC-0054): **0 hits through 08-01 18:30**. Single-token pattern
  `co-rejecting` — *multi-word `nasctl grep` patterns silently match nothing*; positive-control any
  zero.
- **Humidity-spike watch** — unfired. **Method and arithmetic are in DEC-0044 — do not re-derive.**
- **DEC-0049 phantom-rainRate** — unfired. Next calm, saturated, cooling night is a free test.
- **First frost** — the signed decode's negative branch gets its first live air test.
- **DEC-0056 revisit trigger** — a rain-rejection email on a genuinely *wet* day.
- **Upstream replies** — four open threads (lheijst #22/#23, issue #15, david-lutz#1). See MANIFEST.
- **Dependabot** may open a deps PR — review, don't auto-merge.

✅ **#74 calm-windDir is CLOSED (S59)** — do not re-run.
✅ **Campaign-A abort near-miss is CLOSED (S62)** — the abort was correct; DEC-0061's budget holds.

## Standing rules that bite most often

- **Ask "which layer actually wins in prod?" for any file we ship (DEC-0046).** Driver +
  `pressure_service.py` + `entrypoint.sh` are **baked** (image); `weewx.conf` is **mounted**
  (live edit); `influx.py` is mounted (scp correct). Exact inverses; a release changing shipped
  config must patch the live NAS copy in the same window and verify in the **running system**.
- **The transcript is an egress path (DEC-0047).** `readconf` for configs, `scan-transcripts` to
  audit; never a line-count window on a sectioned config. **Logs are not covered (DEC-0062)** —
  never log key material.
- **`docker kill`, never `docker stop`** (DEC-0008). **`docker logs` always with `--tail N`**
  (DEC-0036; hook-blocked).
- **Prod is sacred.** One dongle, one receiver (DEC-0011). `main` = production truth; `dev` = work.
- **Pause for approval before every commit and before any push.** Discuss design before coding.
- **No-Rewrite Rule (DEC-0014).**
- **After patching any `.py` the WeeWX venv imports, clear the pyc cache.**
- A shipped/closed/reprioritized DEC gets its `docs/ROADMAP.md` line updated the **same session**
  (DEC-0057). ROADMAP is **P0–P3 only** (DEC-0058); long-horizon items live in `BACKLOG.md`.

## Style notes & contribution conventions

**This repo is PUBLIC and has external contributors** — the only one in the family that does.

- **No credential, live `weewx.conf`, `monitor.env`, or `proxy.env` ever enters any commit on any
  branch** (DEC-0012). Committed source carries `YOUR_*` placeholders; infra facts use
  `<NAS_HOST>` / `<NAS_USER>` / `<SSH_PORT>` placeholders with real values in the gitignored
  local-infra doc. Show every secret found *before* scrubbing so it can be rotated.
- **Run the secret gate with a planted-payload positive control.** It prints nothing and exits 0 on
  a clean pass — *and also exits 0 with `nothing to scan` when no files are staged*. `git add`
  first (DEC-0039/DEC-0045).
- **Validation gates and the exact interpreter are in `docs/CONVENTIONS.md`** — use them verbatim;
  **`ruff format` is not a gate and must not be run** (DEC-0027).
- Prose: **US spelling, concise over thorough, friendly and non-shaming** in anything public-facing.
  Community posts and upstream comments are drafted, owner-reviewed, never posted without a go.
- Sessions use **this repo's own independent counter** (DEC-0023); prefix cross-repo references
  (`weewx S61` vs `dash S151`). **This file is the single source of truth for the current session
  number and the handoff.**

_Last updated: 2026-08-02 (S62). Session numbering: this repo's own counter; governed era runs S16 → …_
