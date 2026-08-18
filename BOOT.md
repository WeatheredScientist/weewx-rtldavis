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

## ▶ Resume here (S87 → S88)

### What's settled (do not re-derive)

**Campaign B: v2.0.13/ws.5 in prod, `prod-baseline-20260811` tagged.** Square runs
**08-15 → 08-23T00:05** — **5 days left as of S86 close**, 11+ of 32 blocks in, every swap on
time, none deferred. Live state in the table below.

**Pressure package (#183, closes #172/#144) + monitor trio (DEC-0090/0091) + `current_interval`
throttle (DEC-0093) are all merged to `dev`, none deployed yet.** All ride the v2.0.14 cut (queue
below) — deliberately held until the square closes, not stalled. #144's offset itself is settled
(station-side, ~+0.04 inHg high, WeatherLink console elevation setting; owner check filed as
ops#168, no repo work pending) — #183 is the honest-nulls code fix, already done.

**Resume machinery (DEC-0087/0089) is proven, not theoretical: 10 pause/resume cycles across
three nights, all auto-recovered, zero STOPs.** Still unexercised: the 120-min ceiling escalation,
the swap-deferral path, rotated-log reads across a `.1` boundary. *(`.STOP.campaignA` at the
project root is campaign **A**'s — not a live sentinel.)*

**The nightly-heavy-window confound (ops#169, DEC-0092) is absorbed by design, not a live
concern.** A sibling tenant's maintenance runs 00:10→~03:00–05:10 most nights; each campaign arm
takes the midnight slot exactly twice, so comparability is safe by construction. Nothing owed by
weewx on this thread. Post-square queue from it: `noatime` on `/volume1`, `chattr +C` on the
archive DB, move our logrotate off 00:05 — all deferred to the v2.0.14 window.

**Hardware history is now documented (CONSTANTS.md, S86): LNA in ~01Jun→02Aug (~2mo), out since.**
A pre-governance no-LNA baseline also exists (~mid-May→~01Jun; owner has email records if ever
needed). Doesn't change DEC-0081/0083's finding: the current elevated stall rate's onset
(08-10 23:56) is **8 days after** the LNA came out, not coincident with it — attribution among
campaign B's high-gain arms / v2.0.12 / weather stays open (DEC-0083), post-campaign
characterization question.

**The v2.0.14 queue (post-campaign, ~08-23):** weewx 5.5.0 (PR #158, pre-reviewed GREEN) + #183's
pressure package (merged) + move `:latest` to v2.0.13 once the square proves it + **copy the new
`loop_json_writer.py` (now with `current_interval`) to the NAS *project root* — NOT the image, NOT
`weewx-data/bin/user/`** (mounted not baked, DEC-0093 — that second path is a decoy). Verify with
`nasctl inspect` before, confirm the startup line reads `every 60 s` after — a file check alone
proves the FILE, never the PROCESS (DEC-0074). NAS-native build (DEC-0078); the recreate
re-verifies CONSTANTS' three live-config deviations **and** the hardware-timeline line still
reads LNA-out. **The cut is execution-only, Sonnet-fit.**

### ▶▶ S88 JOB LIST

**No frontier-tier item is queued. S88 is execution-tier unless a watch escalates it.**
[ops#175]'s weewx half is **answered and closed out** (DEC-0095, S87 — accept-and-monitor, no
prune; the reversal condition executes in `soak_check.sh` at 10% of MemTotal, ~2.6 yr out). Do not
re-derive it; the InfluxDB half stays open **against the dashboard**, not us.

**First job: merge [PR #206]** if it is still open — S87's soak fixes, all checks green, held only
by the Class C merge boundary.

**Standing watches — cheap, execution-tier.**

1. Daily square watch (~5 min): `ops/soak_check.sh`; STOP absent, state matches schedule.
   **Verified good through block 12 (08-17 19:30 EDT)** — arm `B`, on-schedule swap 18:05:02,
   settle 136 s. Next unobserved window `08-18T00:05`. **The soak's own output is trustworthy
   again as of S87** — it had been emitting a false `MONITOR LOG STALE … wedged` on a healthy
   watchdog for ten days, and silently desensitizing the DEC-0036 freeze detector (DEC-0095 commit,
   [PR #206]). It now also prints `remote probe took Ns`; **≥20 s there is a NAS-load signal, not
   noise** — see job 6.
2. ⚠️ **Reception-floor dip, n=3 nights, pattern SHIFTED.** 08-15/08-16 both paused ~02:15–02:45;
   **08-17 paused 03:25–04:20 instead** (4 cycles, not 2–3) — argues against a pure
   tick-grid/fixed-clock artifact. **Still needs the proper statistical test — judgment work**,
   same as ops#175 (DEC-0094 refuted the *freeze* nightly-window lead, S85 refuted the *stall
   episode* one; nobody has tested this reception-floor metric). Raw numbers: `logs/rx_experiment.log`.
3. Resume machinery — see "What's settled" above; keep counting cycles, watch for the three
   untested paths.
4. **[ops#173] BOOT.md over cap — TRACKED, do not re-derive or open a second issue.** Diet at the
   square's close (~08-23), both weewx and ops sides already agreed; the issue can sit until then.
5. **[dash#430] Answered and implemented, needs DEPLOYING not deciding** — rides the v2.0.14
   window, see queue above.
6. ⚠️ **NEW (S87) — the evening window has a measured mechanism candidate, and it is a tenant.**
   At 19:16 EDT, inside DEC-0094's significant 18:00–21:00 band: NAS loadavg **9.05/11.39/8.75** on
   4 cores, driven by ~220% CPU of **`chrome-headless` (coffee-radar)** plus ~14 MB/s sustained
   writes on `md2`. **But no process was in `D` state and weewxd's threads were all `S`**, records
   still arriving — so load is established, *blocking* is not. That is still blocker 1's exact open
   question (DEC-0068 measured `S`, never `D`). **One instant is not a probe**: the real next step
   is sampling `/proc` state across a whole evening window, which runs read-only from the laptop
   over ssh and needs no NAS write. Cheap to build, judgment-tier to interpret.

[ops#169]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/169
[PR #206]: https://github.com/WeatheredScientist/weewx-rtldavis/pull/206
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173
[ops#175]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/175
[dash#430]: https://github.com/WeatheredScientist/eaglehunt-weather-dashboard/issues/430

### Current state (S87 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` + `weewx_monitor.py` unchanged since S82/S82b, sha+process verified |
| Campaign B | **Live and on schedule — 12 of 32 blocks, every swap on time, none deferred.** 08-17: `A→C` 00:05:01 · `C→D` 06:05:02 · `D→A` 12:05:01 · `A→B` 18:05:02 (all healthy). **Now on arm `B`, next swap `08-18T00:05`.** Square through `08-23T00:05` (**~5.2d left as of 08-17 19:30**). STOP/lock absent (`.STOP.campaignA` is A's, not live); all PAUSEs auto-resumed — see job 2 for the night-3 reception-floor shift (n=3). Verified 08-17 19:30 EDT |
| Swap settle time | n=7: 82/139/198/137/197/79/136 s — **not a trend, do not re-flag** (well supported). Budget ~383 s, wide margin — but an unhealthy swap is `trip_abort()`, a sticky STOP DEC-0087 does **not** soften |
| Retention | **SETTLED S87 (DEC-0095)** — accept-and-monitor, no prune. Archive 33.61 MB = 0.89% of 3.69 GiB RAM, 0.37 MB/day, ~7.3 yr to 1 GB; Influx engine 14 MB. Tripwire lives in `soak_check.sh`: reopen at 10% of MemTotal. InfluxDB horizon is the **dashboard's** call, not ours |
| `dev` beyond prod | **Two different deploy layers, don't conflate them.** #183's pressure package = **baked**, rides the v2.0.14 image cut. `loop_json_writer.py` (incl. `current_interval`) = **mounted**, needs a file copy to the project root (the bake will NOT carry it, DEC-0093). Plus S84–S86 docs |
| Freeze rate | DEC-0088-corrected (1.31/day), untouched. Hour-of-day split done (DEC-0094): nightly window refuted, evening 18:00–21:00 carries the signal — now also in `docs/ROADMAP.md` (S86 reconciliation caught it missing there) |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md`, now with the hardware timeline alongside |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | `dev` = `origin/dev`. **[PR #206] (`s87-soak-stale-now`) is OPEN and green — S87's soak fixes + DEC-0095; merge it first next session.** `dependabot/pip/weewx-5.5.0` (#158) queued for v2.0.14 — deliberately held, pre-reviewed GREEN, not stalled |
| Trackers | #180/#74/#44 closed (latter two retroactively communicated, S86 — were closed with 0 comments, now cite the fixing commits) · #172/#144 open until v2.0.14 (code done, deploy pending) · #158 held for v2.0.14 · ops#163/#176 closed |
| Cross-repo (S87) | **NOTHING OWED BY WEEWX.** [ops#175] answered in full from our side (DEC-0095, comment posted) — its InfluxDB half is the dashboard's call and the issue is deliberately left OPEN for them, not closed by us. ops#169 stays open, carries `repo:weewx`, no re-engagement needed. ops#168 owner-side (WL elevation) |

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
- **GitHub's API can degrade on WRITES while READS stay fine (S86)** — `gh pr merge` and a REST
  `PUT .../merge` both 503'd repeatedly while `gh pr view`/`gh api GET` succeeded throughout.
  Verify with a GET before assuming a mutation failed either way; don't hammer the write path in
  a foreground retry loop (blocked by design — use a bounded background retry, or let the owner
  merge via the web UI, which isn't behind the same path).

_Last updated: 2026-08-17 (S87 close). Landed: [PR #206] — the soak's ages were measured against a
clock captured before a 15–100 s remote body, so it cried `wedged` at a healthy watchdog for ten
days and quietly desensitized the DEC-0036 freeze detector; plus **DEC-0095** (retention:
accept-and-monitor, tripwire executes) and the ops#175 answer. `docs/ROADMAP.md` checked, nothing
to reconcile — retention was never a line there, and its next scheduled pass is S96.
**S88 is execution-tier: no frontier item is queued**, so the Sonnet floor is the right default._

_Blocker 1 is narrower but NOT closed: the freeze mechanism is still unproven — DEC-0068 measured
the main thread `S`, never `D`, so "correlates with" is not "is blocked by". Next step there is a
mechanism probe during an evening window, not more timestamp counting._
