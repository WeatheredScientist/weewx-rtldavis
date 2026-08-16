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

## ▶ Resume here (S85 → S86)

### What's settled (do not re-derive)

**Campaign B: v2.0.13/ws.5 in prod, `prod-baseline-20260811` tagged.** Square runs
**08-15 → 08-23T00:05** (third shift, DEC-0089). **Started on time and is running** — live state
in the table below, night-one detail in the S84b block.

**S82/S82b (DEC-0090, DEC-0091): apparatus fixes + the monitor trio are deployed and verified; the
pressure package (#183) is merged to `dev` for v2.0.14.** The whole square runs one monitor
version. Detail in CHANGELOG / the DEC rows; what is still live sits in the state table and the
v2.0.14 queue below.

**S84b: DEC-0087/0089 earned their keep.** Night one's blackout was **RF-dead, not a freeze**
(three `rtldavis process stalled` lines, DEC-0094). Pause/resume detail and the running count
are in job 2; full account in CHANGELOG S84. *(`.STOP.campaignA` at the project root is
campaign **A**'s — not a live sentinel.)*

**S84/S85 (DEC-0093): `current.json` had no reader and was rewritten ~22,500×/day.** Now
throttled to 60 s (dash#430 confirmed), **47.9%** of renames removed, merged to `dev` and
queued for deploy — job 5. **Do not "optimize" `loop-data.txt`**: the eh-proxy 503s at
`now - dateTime > 30` and the dashboard reads that as proof the station is down, so
content-based suppression reports a healthy station offline on a calm night.

**S83: the box has a nightly heavy window, and the midnight block sits in it (ops#169, DEC-0092).**
A sibling project's nightly maintenance (DSM id=15) runs **00:10 → ~03:00–05:10 every night**
(6 nights verified), so **~72% of every 00:05 campaign block runs under it**; id=2 (our own
logrotate, same minute as the swap's `harvest()`) and id=9 (a tenant capture job) fire at 00:05
itself. **Comparability is safe** — each arm takes the midnight slot exactly twice, so the confound
is absorbed by construction; what it threatens is *swap reliability* and *variance*. Workup, the
btrfs correction and the task-id method: DEC-0092.
**Post-square queue from it:** `noatime` on `/volume1` (owner-level DSM change) ·
`chattr +C` on the archive DB (own DEC, rides the v2.0.14 recreate, does **not** reopen DEC-0071) ·
move our logrotate off 00:05.

**The v2.0.14 queue (post-campaign, ~08-23):** weewx 5.5.0 (PR #158) + #172's field + #144's
honest nulls + move `:latest` to v2.0.13 once the square proves it + **copy the new
`loop_json_writer.py` to the NAS *project root* — NOT into the image, NOT into
`weewx-data/bin/user/` (DEC-0093: it is bind-mounted, the bake does not carry it, and that second
path is a decoy). Verify with `nasctl inspect` before, and after the restart confirm the startup
line reads `every 60 s`; a file check alone proves the FILE, never the PROCESS (DEC-0074).**
NAS-native build (DEC-0078); the recreate re-verifies the three CONSTANTS live-config
deviations. **5.5.0 is pre-reviewed GREEN**
(S82b source-diff pass over 11 runtime-chain files; verdict + cut checklist on PR #158) — **the cut
is execution-only, Sonnet-fit.**

**#144's offset is settled: station-side, ~+0.04 inHg high, knob is the WeatherLink console's
configured station elevation.** Owner check filed as **ops#168**; no repo work pending. Workup in
DEC-0091 / hlf#302 / #144.

### ▶▶ S86 JOB LIST

**Tier call, say it before starting (owner's `CLAUDE.md`; he asked to be reminded).** Jobs 1/3
and the v2.0.14 cut are **execution — Sonnet-fits**. **Job 2's actual test and ops#175's
retention DEC are judgment work** (ops#175 is already labelled `tier:frontier`) — name it in
your first reply and let him escalate with a **session-only** switch; a bare `/model <m>`
persists and re-prices later sessions (OPS-DEC-0010).

1. Daily square watch (~5 min): `ops/soak_check.sh`; STOP absent, state matches schedule.
   **Verified good through block 6 (08-16 08:10 EDT)** — next unobserved window is the
   `08-16T12:05` swap to `D`.
2. ⚠️ **NEW WATCH — the ~02:15–02:45 reception dip has now happened on BOTH nights of the square.**
   08-15: PAUSE 02:15 (45%), 02:30 (20%), 02:40 (39%). 08-16: PAUSE 02:15 (36%), 02:30 (37%).
   Different arms (A then B), same clock window, all five auto-resumed. **n=2 nights — a pattern
   worth testing, not yet a finding.** It sits inside HLF's published nightly maintenance
   (00:10–04:46) and near `blend-refresh`'s end (02:23). **This is a THIRD metric**: DEC-0094 tested
   *freezes* by hour (negative, P=0.29) and S85 tested *stall episodes* (negative, P=0.32) — nobody
   has tested **reception-floor dips**, which is what these are. Caveat before anyone gets excited:
   `02:15` is partly a tick artifact (the guard runs on a 5-min grid, so it fires at the first tick
   past the floor), and two nights is two nights. **Collect a few more nights, then test properly.**
   If it holds it is the first weewx evidence of cross-tenant harm — and DEC-0093's caveat applies:
   we cannot distinguish real RF loss from a starved demodulator.
3. **Resume machinery** — no longer n=0: **five pause/resume cycles over two nights, all recovered**
   (DEC-0087 + DEC-0089's second path). Still unexercised: the 120-min ceiling escalation, the
   swap-deferral path, and rotated-log reads across a `.1` boundary.
4. **Over cap, TRACKED as [ops#173] — do not re-derive or open a second issue.** Measure exactly as
   the sweep does or your number won't match: `git show origin/dev:BOOT.md | LC_ALL=en_US.UTF-8
   wc -m` ÷ 4 (**pushed** tip; plain-C `wc -m` degrades to bytes). *Not `boot-cap-check.sh` — that
   is ops's own gate and fails weewx on section names `tier-sweep.sh` deliberately ignores.*
   Repeated rule-1 passes were outpaced anyway: **a repo running a live time-boxed experiment
   exceeds a static cap for the duration, structurally.** Diet at the **square's close ~08-23**,
   when most of this section becomes deletable at once; remainder to `ARCHIVE/` or a `MANIFEST.md`
   row (DEC-0063). *(`MANIFEST.md` is over too, but that is the deliberate OPS-DEC-0101 carry, not
   drift — named on ops#173 so the dedupe doesn't re-file it.)*

5. **[dash#430] ANSWERED and IMPLEMENTED — this now needs DEPLOYING, not deciding** (DEC-0093).
   The dashboard confirmed **60 s** ("please make the change"), so `current_interval` shipped to
   `dev`: `current.json` throttled, `loop-data.txt` deliberately untouched, **47.9%** of renames
   removed (simulated a full day, not estimated). **The deploy is a file copy to the NAS project
   root, NOT the image bake** — this file is bind-mounted and the Dockerfile never `COPY`s it, so a
   rebuild alone is a silent no-op (DEC-0046's failure mode; the `weewx-data/bin/user/` copy is a
   **decoy**, not the mount source). Rides the v2.0.14 window ~08-23 because that is the next
   container recreate anyway. Steps + verification are in the v2.0.14 queue above.


[ops#157]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/157
[ops#169]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/169
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173
[ops#175]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/175
[ops#176]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/176
[dash#430]: https://github.com/WeatheredScientist/eaglehunt-weather-dashboard/issues/430

### Current state (S85 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` (S82) + `weewx_monitor.py` (S82b, pid 7625) both redeployed today, sha+process verified |
| Campaign B | **Live and on schedule — 6 of 32 blocks, every swap on time, none deferred.** 08-15: `A` 00:05 · `B` 06:05 · `C` 12:05 · `D` 18:05. 08-16: `D→B` 00:05:01 (healthy 00:08:18) · `B→C` 06:05:01 (healthy 06:06:20). **Now on arm `C`, next swap `08-16T12:05` → `D`.** Square through `08-23T00:05`. STOP/lock absent; all pauses auto-resumed. Verified 08-16 08:10 EDT |
| Swap settle time | n=6: 82/139/198/137/197/79 s — **not a trend, do not re-flag** (now well supported). All fit `~20 s + k×60 s`, k = archive boundaries missed: 1,2,3,2,3,1. Budget ~383 s, wide margin — but an unhealthy swap is `trip_abort()`, a sticky STOP DEC-0087 does **not** soften |
| `dev` beyond prod | **Two different deploy layers, don't conflate them.** #183's pressure package = **baked**, rides the v2.0.14 image cut. S85's `loop_json_writer.py` = **mounted**, needs a file copy to the project root (the bake will NOT carry it, DEC-0093). Plus S84/S85 docs |
| Freeze rate | DEC-0088-corrected (1.31/day), untouched. **Hour-of-day split done (DEC-0094): nightly window refuted, evening 18:00–21:00 carries the signal** |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | `dev` = `origin/dev` (`26ea196` + S84's docs PR). Only `dependabot/pip/weewx-5.5.0` (#158) beyond, queued for v2.0.14 — deliberately held for the post-campaign cut, pre-reviewed GREEN, not stalled |
| Trackers | #180 closed · #172/#144 open until v2.0.14 · #158 held for v2.0.14 (pre-reviewed GREEN, **not stalled**) · ops#163 closed / ops#165 filed |
| Cross-repo (S84–S85) | **NOTHING IS OWED BY WEEWX** — `ops#169` stays open and carries `repo:weewx`, so session-start will surface it; do **not** re-engage. Our input is banked (footprint, the hard 30 s floor, the freeze-lead retraction, the evening correlation with its limits, two negatives on HLF's window) and the **NAS-LEASE spec review round is DONE** — findings accepted into v1.3, landing is coffee-radar's and gates on HLF's floor. What weewx already knows about adopting it is in `BACKLOG.md`; adoption needs our own DEC. **[dash#430] ANSWERED** → job 5. **[ops#173]** BOOT cap → job 4. **[ops#157]** VPN heads-up, ack'd. **[ops#176]** guard misfire, filed, awaiting triage. **[ops#175]** archive/InfluxDB retention — acknowledged with measured growth (~0.41 MB/day, ~6.4 yr to 1 GB); **design deferred to `BACKLOG.md` Open ideas, nothing owed on the thread**. ops#168 owner-side (WL elevation) |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (S80 measurement via
   `ops/freeze_baseline.py`, DEC-0088-corrected), separate phenomenon** from DEC-0081's episodes.
   **Still hard-aborts — DEC-0087 deliberately does not cover freezes** ("RF re-established" isn't
   a meaningful resume condition for a process-wedge event). Root cause still unproven (thread
   blocking on the bind-mounted log volume is the leading hypothesis, DEC-0067/0068).
   **The S83 hour-of-day lead is ANSWERED and NEGATIVE (S84d, DEC-0094) — do not re-run it.** The
   nightly window holds **9 of 40 freezes vs 7.2 expected, P=0.29**; durations inside match outside.
   **The evening carries the signal instead: 18:00–21:00 = 12 vs 5.0 (P=0.0027)**, coffee-radar's
   ~19:00 window 7 vs 2.5 (P=0.011), over 10 distinct dates — DEC-0068's n=1 is now a base rate
   (30% of freezes in 12.5% of the day). **Mechanism still unproven**, which is why this blocker
   stays open: DEC-0068 measured the main thread `S`, never `D`, so neither coffee-radar's load nor
   our own write volume is established as *blocking* us (DEC-0093 declines the write-volume link).
   Next real step is a mechanism probe during an evening window, not more timestamp counting.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open): interference vs no-LNA
   front-end margin vs site vs condensation. **DEC-0083 adds a dated onset (08-10 23:56) the
   characterization should start from** — it coincides with the campaign-B pilot night and the
   v2.0.12 promotion, neither of which is established as cause.
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-stall episode remains
   the largest on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Gotchas that survive here because they are NOT in the canonical docs

- **Campaign clocks are LOCAL (EDT); most tool output is UTC — convert before comparing.** The
  `SCHEDULE` rows (`2026-08-15T00:05|A`), the swap slots, the log timestamps and DSM's crontab are
  all **local**; `git`/`gh` output (`mergedAt: …Z`), and most API responses are **UTC**. S83 read a
  `Z` timestamp as local and put the swap four hours nearer than it was. DEC-0068 hit the identical
  trap from the other side — coffee-radar's 19:00 run only matched the freeze once corrected to
  EDT, not UTC. Two hits now, so treat any bare timestamp as UTC until proven local.
- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone.
- **`secret-read-guard.sh` trips every NAS `scp` deploy** (S81 rx_experiment, S82 again, S82b
  monitor — likely the `. nas.env` sourcing; the `command`-prefix escape does NOT clear it). The
  settled fallback: hand the owner the single command, **saying explicitly it runs on the Mac**.
  Ran cleanly that way three times now.
- **A guard block can be a MISFIRE — check before you go near the mint path (S85, ops#176).**
  `push-nas-guard.sh` hard-blocked a `python3` heredoc that only edited a **local** `.md` file,
  because the *prose being written* quoted the transfer verb; the guard's own message named a
  **backtick** as the NAS host. **Do not ask for a mint on a misfire** — that authorizes a "NAS
  write" that never leaves the laptop and burns a classifier draw. **Rung 0: re-spell it.** Use
  `Write`/`Edit` for file content instead of a shell heredoc and the guard is not involved at all,
  correctly. A genuine NAS write just blocks again, so the check costs nothing.
- **A second same-session PR branched before the first merged sits BLOCKED by branch protection**
  ("requirements not met", state stays OPEN — and `gh pr merge`'s quiet refusal is another face
  of its never-trustworthy output). Fix server-side: `gh api -X PUT repos/<r>/pulls/<n>/update-branch`,
  wait for the CI rerun, then merge. Found S82b on #183.
- **`rx_experiment.lock` exists only during a pass's critical section** — absence at rest is
  correct; a holder older than 1800s is broken automatically and loudly ("breaking stale lock").
  Don't read a missing lock as "the cron is dead".
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **`nasctl` is read-only** — NAS mutations need the Class C mint path (confirm in chat, mint,
  re-run identical — mint and re-run as TWO separate calls). The scp shape falls through to the
  read-guard fallback above instead.
- **`due_arm()` never returns `NONE` once the pilot block has run** — its last pilot row (`H`)
  is the implicit hold value until the square's first row, so `tick`'s silent no-op
  (`want == have`) can run for hours with zero log output. Check `current_arm()`/state +
  STOP/PAUSE directly, not log silence.
- **`rx_experiment.sh` the SCRIPT lives flat at the NAS project root** — but its LOG output does
  not: `.state`/`.STOP`/`.PAUSE`/`.lock` flat at the project root next to the script; `.log` and
  `_data.log` under `logs/`, alongside `weewx.log`/`weewx_monitor.log`/`monitor_episode.state`.
  `nasctl ls` the actual directory before assuming either layout.
- **`nasctl grep` takes `<pattern> <file>`, pattern first, single-word patterns only** — reversed
  arguments are rejected with a confusing "not metacharacter-free" error (S80); multi-word
  patterns silently return a FALSE ZERO through the ssh quoting layer (S53). Positive-control any
  zero count.
- **Merging several same-session PRs in sequence: re-`git fetch` before every merge-into, not just
  the first** (S79 silently dropped a merged PR's doc changes off a stale ref). And **never
  `git checkout -- <file>` to unplant a staged positive-control payload** — it restores the
  planted version from the index (S55's gotcha, re-bitten S82b); edit the lines out instead.

_Last updated: 2026-08-15 (S84 close, four amendments same day). **DEC-0093** (`current.json` has
no reader; direction set, gated on dash#430, nothing shipped) and **DEC-0094** (nightly-window
freeze lead **refuted**, evening cluster real). The square started on time. Cross-repo: dash#430
answered and its change merged (deploy queued), the NAS-LEASE spec reviewed and our findings taken,
ops#173/#157 acknowledged, ops#176 filed. **Nothing owed by weewx — see the cross-repo row.**_

_Blocker 1 is narrower but NOT closed: the freeze mechanism is still unproven — DEC-0068 measured
the main thread `S`, never `D`, so "correlates with" is not "is blocked by". Next step there is a
mechanism probe during an evening window, not more timestamp counting._
