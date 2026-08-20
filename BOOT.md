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

## ▶ Resume here (S95 → S96)

### What's settled (do not re-derive)

**The crash-loop report is refuted and #245 is closed — `DEC-0106` holds the whole derivation.**
It was **4 scheduled arm swaps a day** (HH:05, 6 h apart) read through an 8-day-old container's
**undated, accumulating stdout**; `docker restart` never increments `RestartCount`, so that `0` was
truthful and uninformative. The owner's *"more crashes lately"* is **correct and benign**: 0/day
between campaigns, 4/day during them. **HLF's staleness is NOT ours** — weewx archived and published
to InfluxDB every minute through their window. **ops#184 left OPEN on purpose**: that redirect is
HLF's action item, and closing it would bury it. Do not re-measure any of this.

**`soak_check.sh` gained a restart-loop detector** — fixed 6 h window, fails when consecutive starts
are **<1800 s apart** (swaps 21,600 s, real loops 43–90 s). Reads **yesterday's rotated log too**,
without which its first live run returns a false zero at exactly DEC-0097's overnight hour.
Positive-controlled over 7 cases. **Laptop-side diagnostic — nothing deployed.**

**Model tier — read from the files, not inferred** (the S89/S94 mistake): `~/.claude/settings.json`
= `sonnet`, every other scope absent, so **nothing to restore in the files**. But S95 ran in the
**desktop app**, where OPS-DEC-0036/0062 makes the floor inert and switches persist in app state
`settings.json` does not reflect — and the persisting form (`/model claude-opus-5`) was used. **The
next session may still start on Opus: state the running model in your first reply.**

### ▶▶ S96 JOB LIST

1. **Daily square watch** (~5 min): `ops/soak_check.sh` + a direct `rx_experiment.state` read.
   **Know which WARNs are artifacts before chasing them:** after midnight the soak's *pre-existing*
   window computation collapses to the new day's log, so *no startup banner* · *driver banner not in
   window* · *sensor_qc not seen* · *log_humidity_raw not seen* are **rotation artifacts, not
   findings** (job 7a). The `stdout is chatty` WARN is likewise explained — see 7b.
2. **[ops#169] — OWNER-RAISED PRIORITY, unchanged from S95; act within the next few sessions.**
   **Read `DEC-0104` first, then `eaglehunt-ops/NAS-LEASE.md`** — between them the research is done.
   Adoption is **host-side and needs no container change** (holder = wrap the NAS image build;
   observer = `weewx_monitor.py`, already resident). Only the InfluxDB `post_interval` yield lever
   needs the mount, which is all v2.0.14 buys. §8 designates our **~08-23 image build** as the
   protocol's first cross-tenant exercise — that is the real date.
   - **★ Deliberate act: weewx's adoption LOCKS §5's constants for every tenant.** Raise any
     amendment on ops#169 *before* our client DEC.
   - **Owed before a client ships:** runtime-user create/rename in `LEASE_DIR`, `O_CREAT|O_EXCL`
     atomicity on btrfs, a cross-tenant-visible log append, a **declared renewal floor**.
   - **Red lines:** SQLite archive commit **never** deferred; `loop-data.txt` hard 30 s ceiling;
     lease writes in-place, **never** tmp+`os.replace` (§3, DEC-0051).
3. **Continue #227's sequence: #224 next** (tier:mid, `dewpoint_service.py`). #223 widened its
   surface — `MAX_WIND_DELTA = 75.0` and `MAX_PLAUSIBLE_WIND_SPEED = 200.0` are both
   documented-mph and miscalibrated under `target_unit=METRIC`; fix both in the same pass as the
   `dewpointF`/`heatindexF` unit branch. #225/#226 are lower priority and can ride v2.0.15+.
4. **v2.0.14 prep is DONE for code.** One optional call before the cut: whether to mount `LEASE_DIR`
   read-only while the container is being recreated anyway. Buys **only** the `post_interval` lever;
   skipping costs that lever until the next recreate and costs adoption nothing.
5. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Revisit once the square closes **and** the gated queue clears.
6. **[ops#173]** — diet done at S94, `BOOT.md` under cap. Left **open on purpose** for the automated
   sweep to close (`MANIFEST.md` carries its documented OPS-DEC-0101 overage). **Nothing to do
   unless the sweep re-flags.**
7. **NEW from S95 — two follow-ups, NOT yet filed as issues** (both in DEC-0106's closing paragraph):
   **(a)** the soak's pre-existing window computation has the same daily-rotation blindness the new
   detector had to fix, producing job 1's artifact WARNs; **(b)** `stdout is chatty — 162 lines` is
   accumulated restart output on a long-lived container, **permanent until the next recreate**, not
   "freeze fuel" — it has been dismissed as expected noise for weeks and should be re-tuned or
   scoped. File both, or fix (a) with the same rotation pattern already used twice.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173

### Current state (S95 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` + `weewx_monitor.py` unchanged since S82/S82b |
| Campaign B | **Live and on schedule — arm B since `08-20T00:07:30` EDT** (read from the state file; 134 s settle after the 00:05:16 container start, mid-range). Square through `08-23T00:05`. No active STOP/PAUSE/lock — the only `.STOP` present is campaignA's inert Aug-2 file. Soak at S95 close: **13 pass / 6 warn / 0 fail**, 4 of those warns rotation artifacts (job 1) |
| Restart rate | **NEW BASELINE (DEC-0106):** 4/day during a campaign, every one at HH:05; **0/day between campaigns**. A real loop looks like 2026-08-06: 7 starts in 7 min |
| Swap settle time | n=11: 82/139/198/137/197/79/136/196/144/84/**134** s — still not a trend |
| Retention | **BOTH halves SETTLED** (DEC-0095/DEC-0100), unchanged since S90 |
| `dev` beyond prod | Everything for v2.0.14 **plus** DEC-0102, #219–#223, DEC-0103/0104, and **DEC-0106 + the soak detector** |
| Freeze rate | DEC-0088-corrected (1.31/day); DEC-0102 adds the overnight-window confound number. **Unrelated to DEC-0106** — that was scheduled restarts, this is the silent wedge |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | S95 worked on `s95-restart-loop-detector-245`; **confirm it merged and was deleted, then steady state is exactly `dev` + `main`** |
| Trackers | **#245 CLOSED** with an explanatory comment. **ops#184 OPEN on purpose** (HLF redirect). #233 open (from #219, tier:mid) · #172/#144 open until v2.0.14 · #204 open · #227 at 5/8. Remember `Closes #N` does **not** auto-fire here — PRs land on `dev` |
| Cross-repo (S95) | ops#184 answered in full and left open for HLF. ops#169 unchanged and still job 2. ops#173 unchanged. Nothing new owed |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Still hard-aborts, root
   cause unproven (thread blocking on the bind-mounted log volume leads, DEC-0067/0068). Evening
   18:00–21:00 carries the signal (DEC-0094). **DEC-0106 did not touch this** — it refuted a
   *restart* claim; the freeze is the silent wedge, a different phenomenon. Untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0097 adds the
   00:00–04:00 clustering; DEC-0102 the 11.80x iowait confound, which does NOT close it. Next real
   step is multi-night minute-level correlation, not a re-run. Untouched this session.
3. **ERR-0005** — largely explained by DEC-0081; its 21-stall episode remains the largest on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap. S95 added two to §1: an
undated log tail reads history as *now*, and a daily-rotating log makes any window past midnight
span two files.

_Last updated: 2026-08-20 (S95 close). Green gate: ruff clean, **339/339**, mypy clean (57 files),
secret gate clean **and positive-controlled** (three planted payload shapes caught, exit 1).
Shipped **DEC-0106** — the tier:frontier crash-loop report refuted on measurement, #245 closed,
ops#184 answered and left open for HLF — plus a restart-loop detector for `soak_check.sh` that the
old presence-only banner check could never have caught. **The detector's own rotation bug was caught
by verifying it against production rather than trusting the positive control alone**; unfixed, it
would have returned a false green on its first run. ROADMAP: nothing to reconcile (DEC-0106 is
tooling), **tripwire still S96 — due next session**. Full narrative in `CHANGELOG.md`._
