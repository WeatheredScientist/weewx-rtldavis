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

## ▶ Resume here (S84 → S85)

### What's settled (do not re-derive)

**Campaign B: v2.0.13/ws.5 in prod, `prod-baseline-20260811` tagged.** Square runs
**08-15 → 08-23T00:05** (third shift, DEC-0089). **Started on time and is running** — live state
in the table below, night-one detail in the S84b block.

**S82/S82b (DEC-0090, DEC-0091): apparatus fixes + the monitor trio are deployed and verified; the
pressure package (#183) is merged to `dev` for v2.0.14.** The whole square runs one monitor
version. Detail in CHANGELOG / the DEC rows; what is still live sits in the state table and the
v2.0.14 queue below.

**S84b: the square is live and DEC-0087/0089 earned their keep on night one.** `H -> A`
`00:05:01` (healthy `00:06:23`), `A -> B` `06:05:01` (healthy `06:07:20`). **One ~20-min
blackout at 02:00–02:22 produced THREE pause/resume cycles** as the 30-min mean lagged the
recovery — exactly DEC-0087's scenario, and **pre-DEC-0087 the first trip would have been a
sticky STOP killing the block unattended.** Resumes 2 and 3 came from `recovered_since()`'s
**second** path (`RECEPTION: [OK]` lines newer than the pause), i.e. **DEC-0089's fix carried
them** — only one `RECEPTION RECOVERY` edge line exists, so edge-only logic would have stranded
both. The blackout was **RF-dead, not a freeze** (three `rtldavis process stalled` lines inside
it, DEC-0094). Full account in CHANGELOG S84. *(The `.STOP.campaignA` file at the project root
is campaign **A**'s — a different name, not a live sentinel.)*

**S84 (DEC-0093): `current.json` is written ~22,500×/day and nothing reads it.** DEC-0092's
"skip dataless loop-JSON writes" queue item **was already done in S43** (Layer B) and is retired;
measured **~45,000 renames/day**, not 50–85k. Direction: **decouple `current.json`'s cadence to
30–60 s (~47% of renames), gated on the dashboard** (job 4). **Do not "optimize" `loop-data.txt`**
— the eh-proxy 503s at `now - dateTime > 30` and the dashboard reads that as proof the station is
down, so content-based suppression would report a healthy station offline on a calm night. Full
argument, and the freeze link that does *not* hold, in DEC-0093.

**S83: the box has a nightly heavy window, and the midnight block sits in it (ops#169, DEC-0092).**
A sibling project's nightly maintenance (DSM id=15) runs **00:10 → ~03:00–05:10 every night**
(6 nights verified), so **~72% of every 00:05 campaign block runs under it**; id=2 (our own
logrotate, same minute as the swap's `harvest()`) and id=9 (a tenant capture job) fire at 00:05
itself. **Comparability is safe** — the square runs twice, so each arm takes the midnight slot
exactly twice and the confound is absorbed by construction; what it threatens is *swap
reliability* and *variance*. Workup, the btrfs-not-ext4 correction and the task-id method:
DEC-0092. **Post-square queue from it:** `noatime` on `/volume1` (owner-level DSM change) ·
`chattr +C` on the archive DB (own DEC, rides the v2.0.14 recreate, does **not** reopen DEC-0071) ·
move our logrotate off 00:05.

**The v2.0.14 queue (post-campaign, ~08-23):** weewx 5.5.0 (PR #158) + #172's field + #144's
honest nulls + move `:latest` to v2.0.13 once the square proves it + **copy the new
`loop_json_writer.py` to the NAS *project root* — NOT into the image, NOT into
`weewx-data/bin/user/` (DEC-0093: it is bind-mounted, the bake does not carry it, and that second
path is a decoy). Verify with `nasctl inspect` before, and after the restart confirm the startup
line reads `every 60 s`; a file check alone proves the FILE, never the PROCESS (DEC-0074).** NAS-native build (DEC-0078),
recreate re-verifies the three CONSTANTS live-config deviations. **5.5.0 is pre-reviewed GREEN**
(S82b source-diff pass over 11 runtime-chain files; verdict + cut checklist on PR #158) — **the cut
is execution-only, Sonnet-fit.**

**#144's offset is settled: station-side, ~+0.04 inHg high, knob is the WeatherLink console's
configured station elevation.** Owner check filed as **ops#168**; no repo work pending. Workup in
DEC-0091 / hlf#302 / #144.

### ▶▶ S85 JOB LIST

1. Daily square watch (~5 min): `ops/soak_check.sh`; STOP **and PAUSE** both absent; state
   matches schedule. **Verified good through block 4 (08-15 18:18 EDT)** — next unobserved
   window is the `08-16T00:05` swap to `B`, which is also the first repeat of an arm.
2. **Watch the revised resume machinery on a real pause** — **no longer n=0: it fired three times
   on 08-15 and worked** (see below). Remaining unexercised: the 120-min ceiling escalation, the
   swap-deferral path, and rotated-log reads across a `.1` boundary.
3. **This file is over cap and it is TRACKED as [ops#173]** (~3,670 vs 2,500; acknowledged there
   S84 at ~3,550, plus the swap-settle row added after — a deliberate ~50 tok spend to stop a
   future session re-investigating a non-trend. **Do not re-derive this or open a second issue.**)
   Repeated trimming passes applied rule 1 and still landed above cap: **a repo running a live
   time-boxed experiment exceeds a static cap for the duration, structurally.** The diet lands at
   the **square's close ~08-23**, when most of this section becomes deletable in one stroke;
   remainder to `ARCHIVE/` or a `MANIFEST.md` row (DEC-0063). ops#173 closes when the sweep is green.

4. **[dash#430] ANSWERED and IMPLEMENTED — this now needs DEPLOYING, not deciding** (DEC-0093).
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
[dash#430]: https://github.com/WeatheredScientist/eaglehunt-weather-dashboard/issues/430

### Current state (S84 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` (S82) + `weewx_monitor.py` (S82b, pid 7625) both redeployed today, sha+process verified |
| Campaign B | **Live and on schedule — day 1 complete, all four arms exercised once (4 of 32 blocks).** `A` `00:05:01` · `B` `06:05:01` · `C` `12:05:01` · **`D` `18:05:01`, healthy `18:07:18`** — every swap on time, none deferred. Next `08-16T00:05` → `B`. Square through `08-23T00:05`. STOP/PAUSE/lock all absent; the only pauses were night one's three (all auto-resumed); reception 69–77% [OK]. Verified 08-15 18:18 EDT |
| Swap settle time | 82/139/198/137 s — **not a trend, do not re-flag.** All fit `~20 s + k×60 s` (stable restart, k = archive boundaries missed: 1,2,3,2). Budget ~383 s, wide margin — but an unhealthy swap is `trip_abort()`, a sticky STOP DEC-0087 does **not** soften |
| `dev` beyond prod | #183's pressure package (baked files) + S84's docs — rides until the v2.0.14 image cut |
| Freeze rate | DEC-0088-corrected (1.31/day), untouched. **Hour-of-day split done (DEC-0094): nightly window refuted, evening 18:00–21:00 carries the signal** |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | `dev` = `origin/dev` (`26ea196` + S84's docs PR). Only `dependabot/pip/weewx-5.5.0` (#158) beyond, queued for v2.0.14 — deliberately held for the post-campaign cut, pre-reviewed GREEN, not stalled |
| Trackers | #180 closed · #172/#144 open until v2.0.14 · #158 held for v2.0.14 (pre-reviewed GREEN, **not stalled**) · ops#163 closed / ops#165 filed |
| Cross-repo (S84) | **[ops#169] updated** — footprint corrected to ~45k, ~47% removable unilaterally, `loop-data.txt` declared a **hard 30 s floor** for the lease spec, the nightly-window freeze lead **retracted**, and coffee-radar's ~19:00 job reported as correlating with 30% of our freezes (limits stated). **[dash#430] filed, awaiting their answer** — `current.json` cadence. **[ops#173] acknowledged** (BOOT cap, job 3). **[ops#157] acknowledged** — the VPN heads-up explained this session's NAS gap. ops#168 still owner-side (WL elevation) |

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
freeze lead **refuted**, evening cluster real). The square started on time. Cross-repo: ops#169
updated with both, ops#173 + ops#157 acknowledged, dash#430 filed and awaiting._

_Blocker 1 is narrower but NOT closed: the freeze mechanism is still unproven — DEC-0068 measured
the main thread `S`, never `D`, so "correlates with" is not "is blocked by". Next step there is a
mechanism probe during an evening window, not more timestamp counting._
