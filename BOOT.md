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

**S63 found that "prod went deaf" was wrong for the recurring case (DEC-0067).** The receiver was
fine; the **weewx process freezes** for ~3.5 min about once a day, and the monitor's metric — which
counts *published output* — cannot tell that apart from deafness. The driver's own 150 s watchdog is
the discriminator, and it had been reporting correctly all along: **21 firings during ERR-0005, zero
on every other day.** So ERR-0005 is a genuine RF outage and a **single incident**; the recurring
"dropouts" are software freezes that **pre-date the LNA removal** (one on 07-30, LNA in).

**Campaign B stays HELD (DEC-0066)** — but its launch condition is now mechanical (detect and
exclude freeze windows) rather than "wait until the instrument is trusted". Prod is healthy; the
LNA is out and the schedule is shifted in-repo.

### Current state — every row re-verified at S63 open, not carried over

*(S62's handoff was stale — its branch merged and its watchdog deployed between sessions. Fixed.)*

| Thing | State |
|---|---|
| `s62-incident-followups` | **merged** (PR #118, `bdc4f9f`). Stale branch still exists, harmless |
| `:v2.0.12` image | S62's local build is **gone**. Rebuild from the merged tip when B launches |
| Campaign B apparatus | schedule shifted in-repo; **NOT on the NAS** (its `rx_experiment.sh` is still campaign A's, mtime Jul 29) |
| Watchdog (DEC-0065) | **deployed and live** — NAS copy matches repo tip byte-for-byte, zero resets since |
| Prod right now | **v2.0.11**, LNA **out**, gain 372, ~70–80%, up since 08-02 05:48 |
| Campaign A | **STOPped, sentinel in place.** Do not clear it |
| Campaign B | **HELD (DEC-0066).** Schedule dates are a placeholder (08-10 → 08-19) |

**The schedule dates are a placeholder** — arbitrary, existing only so nothing sits in the past.
Re-shift the whole `SCHEDULE=` block by a constant offset when a launch is agreed (S62's method: 39
substitutions; the structure tests confirm the square survives). You do not have to remember this:
`install` **refuses** a schedule whose first row has passed (`schedule_started()`, DEC-0066), because
`due_arm()` picks the *latest* row already passed — so a stale schedule fails silently, joining
mid-square with no pilot or recording the campaign complete without running it. Both look like
success, and prose would not have caught it (DEC-0040).

### Before B can launch (DEC-0066)

1. ~~Explain the two unexplained outages~~ — **substantially done (DEC-0067).** The recurring class
   is explained in kind (process freeze, RF unaffected), bounded (~1/day, ~3.5 min, ~0.4 % of
   wall-clock) and pre-dates the LNA. ERR-0005 is unexplained but is a **single incident**.
2. **Make the campaign metric freeze-aware** — *this is now the real gate.* A ~3.5 min freeze inside
   a 6 h arm block moves that block's mean ~0.8 pts against a **2 pt** adoption threshold, and a
   freeze also *inflates* the record that follows it (parse-time stamping). Detect freeze windows
   via the DEC-0067 log rule and exclude them. Not yet designed — discuss before coding.
3. **Fix the DB-lock defect** — independent of the freezes. Try **WAL mode** on the archive DB
   first; bound the uploader-thread joins second.
4. ~~Deploy the watchdog~~ — **done**, verified live at S63 open.
5. Then: promote + tag → rebuild `:v2.0.12` from the **merged tip** (`bdc4f9f`) → push `:v2.0.12`
   (`:latest` only after our own station proves it) → regenerate the schedule → the Class C deploy
   steps → `install`.

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

**Model note (closeout step 6):** S62 ran on **Opus 5**. S63 opened on Sonnet, then the owner
escalated to **Opus 5** for the outage diagnosis — correct call, it was unfamiliar debugging. That
was a bare `/model`, so it **persists as the new-session default**: restore the Sonnet floor before
the next execution-shaped session.

## Blockers

1. **The weewx process freezes ~3.5 min, roughly once a day. Cause unknown (DEC-0067).** Replaces
   the old "two unexplained outages" blocker, which conflated two things. Freezes seen 07-30 08:04,
   08-02 13:46, 08-03 02:59 — **07-30 was LNA-in, so they pre-date the LNA removal.** All threads
   stop at once and nothing is logged; leading hypothesis is a thread blocking on the bind-mounted
   log volume while holding the logging lock (box runs at 18.6 % cumulative iowait). **Unproven** —
   the discriminating capture is thread state `D` vs `S` during a freeze.
2. **ERR-0005 is still unexplained** — but is demonstrably a **single incident**, not the head of a
   pattern (21 driver detections that day, 0 on every other). Do not let it block B on its own.
3. **`database is locked` is recurrent and pre-dates the LNA removal** (08-01 15:08, 08-02 19:45;
   earlier S59). Independent of the freezes. The 10-min outage decomposes as ~106 s hung threads +
   **120 s of weewx's own hardcoded wait** + ~5 min restart — the hang is only ~18 % of it, and the
   identical lock on 08-01 cost 4 min because threads exited in 0.26 s. **The archive DB is not in
   WAL mode** — the standard cause of this contention, and the first thing to try.
- **`ppm`/`fc` still unmeasured** and deliberately unchanged for B (would confound the LNA contrast).

## Ordered backlog

1. **Find out why the process freezes (DEC-0067).** Capture thread state during one: `D` =
   blocked on I/O (leading hypothesis), `S` = lock or socket. A read-only watcher polling
   `weewx.log`'s size and dumping `/proc/<tid>/stat` is enough and needs no NAS deploy — S63 built
   one at `scratchpad/stallwatch.sh` but the session ended before it caught a freeze; it is **not**
   in the repo, rebuild or re-run it. Container thread PIDs come from
   `/sys/fs/cgroup/cpuacct/docker/<CID>/tasks`. Then: make the metric freeze-aware, fix the DB lock,
   launch B.
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

✅ **"Unexplained reception dropouts" CLOSED (S63/DEC-0067)** — answered, not just observed longer:
  process freezes, not reception loss, and pre-dating the LNA removal. Replaced by Blocker 1. Do not
  re-open it on a `WINDOW: 0/21` reading — that metric cannot tell a freeze from deafness, which was
  the whole problem. Use the DEC-0067 rule: a >150 s output gap **with** `rtldavis process stalled`
  is RF; a silent one is a freeze.
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

_Last updated: 2026-08-03 (S63) — corrected S62's stale handoff, then rewrote Blockers and the
standing watches around DEC-0067 (the recurring dropouts are process freezes, not RF loss). Session
numbering: this repo's own counter; governed era runs S16 → …_
