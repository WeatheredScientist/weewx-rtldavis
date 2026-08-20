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

## ▶ Resume here (S94 → S95)

### What's settled (do not re-derive)

**#223 shipped — #227's sequence is 5 of 8.** Its four defects were one design gap; **DEC-0103**
records the fix and both open calls (the bounds-vs-delta split; ported locally rather than importing
`SensorQC`, to keep `dewpoint_service.py`'s zero coupling to the driver). One consumer-visible change:
`windDir` is now co-nulled with a rejected `windSpeed`. PR #241 merged (`592064b`); #223 closed on
GitHub with a comment. **Not deployed** — the file is BAKED, so it ships on the v2.0.14 image rebuild.

**ops#169 is UNBLOCKED — `DEC-0104` records why.** Reading `eaglehunt-ops/NAS-LEASE.md` overturned
this repo's own DEC-0099: adoption is **not** gated on the v2.0.14 recreate, because §9 had already
placed weewx's client host-side precisely to avoid one. DEC-0099's index row carries a correction
pointer. Position posted to the thread. Actionable detail in **job 2**.

**Model tier: nothing to restore — verified, not inferred.** S94 escalated to Opus via a bare
`/model`; all five scopes read `sonnet`/absent at close, so that switch touched no floor file.
**Answer closeout step 6 from the files, never from OPS-DEC-0010's rule** — asserting it from the rule
was wrong at S89 and again at S94, both times shipped into this file before being caught. Read with a
**leading** `command jq -r '.model' <file>`.

### ▶▶ S95 JOB LIST

1. Daily square watch (~5 min): `ops/soak_check.sh` + a direct `rx_experiment.state` read.
2. **[ops#169] — OWNER-RAISED PRIORITY: act within the next few sessions.** **Read `DEC-0104` first,
   then `eaglehunt-ops/NAS-LEASE.md`** — between them the research is done; do not re-derive it.
   The shape: adoption is **host-side and needs no container change** (holder = wrap the NAS image
   build; observer = `weewx_monitor.py`, already resident). Only the InfluxDB `post_interval` yield
   lever needs the mount, and that is all v2.0.14 buys. §8 designates our **~08-23 image build as the
   protocol's first cross-tenant exercise** — that is the real date.
   - **★ Deliberate act, not a side effect: weewx's adoption LOCKS §5's constants for every tenant**
     (HLF's DEC-0177 was the first adopter). Raise any amendment on ops#169 *before* our client DEC.
   - **Owed before a client ships:** runtime-user create/rename in `LEASE_DIR`, `O_CREAT|O_EXCL`
     atomicity on btrfs, a cross-tenant-visible log append, and a **declared renewal floor** (§5 lists
     weewx as "none declared"). `LEASE_DIR` itself exists (mode 1777) and HLF is renewing live.
   - **Red lines:** SQLite archive commit **never** deferred; `loop-data.txt` has a hard 30 s ceiling.
     Lease writes are in-place, **never** tmp+`os.replace` (§3, DEC-0051).
3. Continue #227's sequence: **#224 next** (tier:mid, same file as #223 — `dewpoint_service.py` — so
   it pairs naturally and DEC-0103's context is fresh). **#223 widened its surface:** #224 already
   flagged `MAX_WIND_DELTA = 75.0` as documented-mph and therefore miscalibrated under
   `target_unit=METRIC`, and S94 added `MAX_PLAUSIBLE_WIND_SPEED = 200.0` in the same units — fix
   both constants in the same pass as the `dewpointF`/`heatindexF` unit branch. #225/#226 are lower
   priority (confirmed dormant / cheap-tier) and can ride v2.0.15+.
4. **v2.0.14 prep is DONE for code**, now also carrying #223's fix. One optional addition to decide
   before the cut (not a blocker on job 2, see there): whether to mount `LEASE_DIR` read-only into
   the container while it is being recreated anyway. That mount buys **only** the InfluxDB
   `post_interval` yield lever; skipping it costs that one lever until the next recreate, and costs
   adoption nothing.
5. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Revisit once the square closes **and** the gated queue clears.
6. **[ops#173] — DIET DONE at S94: `BOOT.md` 4,866 → 2,346 tok, under the 2,500 cap.** Issue left
   **open on purpose** for the automated sweep to close, not asserted green: `MANIFEST.md` sits at
   1,226 vs its 1,000 cap (the documented OPS-DEC-0101 carry, +130 for the `GOTCHAS.md` row). Result
   posted to the thread. **Nothing to do here unless the sweep re-flags** — do not re-derive the diet.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173
[weewx#227]: https://github.com/WeatheredScientist/weewx-rtldavis/issues/227

### Current state (S94 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` + `weewx_monitor.py` unchanged since S82/S82b |
| Campaign B | **Live and on schedule — arm D since 08-19T18:08:23 EDT** (scheduled mid-session swap from C; confirmed against the state file *and* 19-min container uptime, not inferred from fresh soak counters). Square through `08-23T00:05`. STOP/PAUSE/lock absent. Soak (S94 close): 16 pass / 2 expected-WARN, reception 72%/86% |
| Swap settle time | n=10 (unchanged since S90): 82/139/198/137/197/79/136/196/144/84 s — not a trend |
| Retention | **BOTH halves SETTLED** (DEC-0095/DEC-0100), unchanged since S90 |
| `dev` beyond prod | Everything for v2.0.14 **plus** DEC-0102, #219–#222, and **DEC-0103 / #223** |
| Freeze rate | DEC-0088-corrected (1.31/day); DEC-0102 adds the overnight-window confound number |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | **Steady state restored: exactly `dev` + `main`.** S94's feature branch merged and deleted, remote + local, same session |
| Trackers | **#227: 5/8 done, merged and closed on GitHub.** #233 open (follow-up from #219, tier:mid) · #172/#144 open until v2.0.14 · #204 open (current.json cadence). Recently-closed issues audited at close: all carry an explanatory comment, no silent closes. Remember `Closes #N` does NOT auto-fire here (PRs land on `dev`, not the default branch) — S93 found #219/#220/#221 silently unclosed for exactly that reason |
| Cross-repo (S94) | Swept. **[ops#169] — owner-raised priority; now job 2, researched, and answered (DEC-0104).** Position posted to the thread: our DEC-0099 correction, the not-blocked-on-v2.0.14 conclusion, the constants-lock heads-up, and verified pre-flight status. No questions asked of other repos — the one we had was already answered in `coffeeradar/BACKLOG.md`. Everything else unchanged |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected), separate phenomenon**
   from DEC-0081's RF-dead episodes. Still hard-aborts. Root cause unproven (thread blocking on the
   bind-mounted log volume is the leading hypothesis, DEC-0067/0068). Evening 18:00–21:00 carries
   the signal (DEC-0094). Untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0097 adds a timing
   signature (clusters 00:00–04:00); DEC-0102 adds the first kernel-level number on the leading
   confound (11.80x iowait) but does NOT close it. Next real step is multi-night minute-level
   correlation, not a re-run. Untouched this session.
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-stall episode remains the
   largest on record. Unchanged.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B. Unchanged.

## Gotchas — moved to `docs/GOTCHAS.md` (S94)

**~1,700 tokens of durable traps moved out of the always-load tier** under STANDARD rule 1 (ops#173).
None of it was session state, so none of it belonged here. **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign task
(§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps are
appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-19 (S94 close). Green gate: ruff clean, **339/339**, mypy clean (57 files),
secret gate positive-controlled. Shipped #223 (DEC-0103) and, after the owner raised ops#169,
DEC-0104 — which corrects this repo's own DEC-0099. Campaign B checked twice (arm C → arm D on a
scheduled swap), healthy both times. ROADMAP checked for both DECs: nothing to reconcile, tripwire
S96. **Seven PRs, three of them corrections of this session's own errors** (#242 stale handoff, #243
a false tier claim repeating S89's mistake, #246 the DEC-0099 premise) — each caught by re-reading,
not by getting it right first. **`BOOT.md` diet done (DEC-0105, ops#173): 4,866 → 2,406 tok, under
cap for the first time since before S83** — ~1,700 tok of durable gotchas to `docs/GOTCHAS.md`, the
rest compressed to conclusions now that DEC-0103/DEC-0104 hold the detail. **That only holds if new
traps go to `GOTCHAS.md`, never here.** Full session narrative in `CHANGELOG.md`._
