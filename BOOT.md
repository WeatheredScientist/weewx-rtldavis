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

## ▶ Resume here (S162 → S163)

### What's settled (do not re-derive)

**v2.0.20 has run in prod since 2026-10-06 22:15:14 ET (DEC-0209): WeatherLink's `bar_absolute`
is weewx's `pressure`, `altimeter` derives from it, nothing else changed** (of the seven baked
modules only `pressure_service.py` differs from v2.0.19; engine 5.5.2, banner `0.20+ws.6`). The
archive's `pressure` is measured from **22:18:00 ET** (DISC-0002: +0.008 inHg step, `barometer`
unchanged). Zero WARNING/ERROR lines, soak 19/0/0 at the release. Tagged `v2.0.20` on `9a86c97`
with a GitHub release; `:v2.0.20` on Docker Hub (digest = prod's). `eaglehunt-ops#357` closed on
weewx's side with the boundary timestamp; HLF gates its mapping on it. Rollback: retag `:v2.0.19` +
restart — that puts the columns back on the derived path. **The same night: `dev` promoted to
`main` (`prod-baseline-20261006`, #436; `main` had been v2.0.16, not v2.0.13) and Docker Hub
`:latest` moved to v2.0.20.** `main` lags `dev` by the closeout docs, S151's secret-gate fix (#439),
S152's docs fix (#441) and S153's design records: nothing that changes the image or prod.

**#423's swap path is proved end to end as `t-weewx` (S148).** Schedule stood down, arm `T` kept in
`arm_cmd`, timer not installed. **`eaglehunt-ops#360` is done on weewx's side** (both units under
`--cap-drop ALL` + `no-new-privileges`). The S145 audit's ten high items shipped; 29 medium/low
stay in `docs/CODE_REVIEW_S145.md`. **The secret gate's four detector holes (#421) are closed
(S151, DEC-0210, merged as #439).** `LoopJsonWriter` runs last in `process_services`, with
`data_services` empty, since 2026-07-12 (S152, #441). **`weewx#440` is closed (S155, DEC-0211):
the writer ships as a WeeWX extension, release `loopjson-v1.0.0` of this repo; prod runs the new writer (a mount, no image change).**
ROADMAP next check: S166 (S156 ran the full pass). **The public face is rewritten for a new user
(S156, DEC-0213):** README 634 → 211 lines with an unprivileged quickstart that seeds the baked
config (the old one could not start), `docs/DEPLOY.md` (systemd recommended, Synology kept),
`examples/systemd/`, a hardened compose file. User-facing text follows the dashboard's
public-release scrub rules; the internal records keep their machine names (owner call). **Images
are multi-arch from v2.0.20 (DEC-0214, DEC-0215):** both downloads pinned with sha256s, CI builds
and smoke-tests amd64 and arm64, CI pushes arm64 to GHCR and `scripts/join_multiarch.sh` joins it
with marvin's `:vX.Y.Z-amd64`; the v2.0.20 backfill ran 2026-10-17 18:41 ET (`:latest` multi-arch,
`:v2.0.20-amd64` = prod's digest). **The plan is ROADMAP P0.8 (public readiness: five phases,
issues #451–#456) and P1.9 (decoder fixes in Go: #458 measure CRC failures, #459 burst gate)**,
on #457. **#458 is merged (S157, DEC-0216, PR #461, log-only, not deployed). S158 did P0.8 phase 1's cheap items (#451, #452, #454, #455); #451 edits the baked `pressure_service.py`, so it ships with v2.0.21.** **S159's #463 (#453, DEC-0217) and #464 (#456) are merged to `dev`, issues closed with comments; #464 carries the 240 s init grace (baked, v2.0.21) and `influx.py`'s lease-JSON fix (mounted, not yet deployed).** **S160 (#465, DEC-0218, merged as #466): a rain reading after a rejected one is judged first against the last accepted count, removing the up-to-16-tip phantom when a counter dips and comes back; baked, rides v2.0.21. S161 deployed #464's mounted `influx.py` (and the writer's docstring) with a `weewx.service` restart at 2026-10-21 23:14:42 ET; sha matches `dev`, soak 19/0/0.** It was prompted by four replies on 2026-10-21 from `weewx-packages`, a day-old continuation org that folded our upstream PRs (lheijst#22, #23, #15, lheijst/rtldavis#7) into its own fork with accurate credit and no endorsement from the original maintainers. No reply is owed; our upstream PRs stay open. Non-Davis platform research is `eaglehunt-weather-dashboard#936`, dash's to run; weewx
files issues from its section A.

### ▶▶ S163 JOB LIST

1. **Watch, no action unless it fires** (last checked S161: soak 19 passed / 0 failures, no
   `bar_absolute` fallback since v2.0.20): the measured `pressure` keeps arriving (a `no
   bar_absolute` WARNING means the column went derived again, and DISC-0002 needs a second
   boundary) · WU gold star (≥ 5 uninterrupted days; the run restarted at the 2026-10-14 21:22 ET
   restart, so the earliest is 10-19 21:22 ET; the owner reads it off WU) · OWM and Windy rain in
   millimeters (needs rain; ERR-0010) · freeze lead (blocker 1), measure at the next freeze; none
   since at least 10-11. The message-type proof fired (3 times, `BACKLOG.md`); no longer a watch.
2. **P0.8 phase 1, what is left:** the quickstart's container half is proven on arm64 (S162: seed,
   non-root writes, banner). The host steps (blacklist, udev rule, systemd unit) wait on marvin's
   answer to **ops#427** (a disposable Debian VM); then the GitHub About text and topics (owner's
   go). **#468** (two stray `weewx.conf.<timestamp>` files in the seed) rides v2.0.21. The Hub overview syncs from README on the next push to `main`, if the Hub
   secrets are set.
3. **First arm64 run against a live radio** (any Pi with a dongle); until then README says
   smoke-tested only. Then P0.8 phase 2's v2.0.21 (audit 15), which carries #451, #458, #456's
   init grace and #465 (bump `ws.7`); after it deploys, collect a day of `crc failures this period`
   lines and DEC-0218's `rain: counter recovered` lines, and design #459 from them (frontier tier,
   DEC first).
4. **Owner-only:** `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the shell profile, never CI. Whether to
   tell the `weewx-packages` maintainer that their equality confirmation stalls in heavy rain after
   an over-cap jump (DEC-0218 option B).
5. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, audit 37 and 39 (phase 5), the reset-from-112-or-above phantom
   (#465's footnote).

## Current state (S150 close; trackers S154)

| Thing | State |
|---|---|
| Prod | marvin, **`v2.0.20`** as `:marvin-live` (image `f617c9ca…`) since 2026-10-06 22:15:14 ET, weewx 5.5.2, gain 372, `t-weewx` (996:986), under #360's flags. `:v2.0.19` is local for rollback |
| InfluxDB | marvin, `weewx-influxdb.service`, under #360's flags since S147 |
| weewx-monitor | sha `5cd09917…`, running since 2026-09-29 09:31:16 ET; `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| Campaign harness | schedule empty (stand-down), state `BASELINE`, timer not installed |
| `main`/`dev` | `main` = `dev` at the v2.0.20 promotion (`prod-baseline-20261006`, S150); `dev` is ahead only by docs and the secret gate (see above). Before the promotion `main` was v2.0.16's (`prod-baseline-20260904`, #324, S122) plus the misrouted #338 — S149/S150's BOOT and CONSTANTS said "v2.0.13", stale since S122. The promotion merge resolved every conflict in `dev`'s favor |
| Docker Hub | `:v2.0.20` = `:latest`, multi-arch `4e9d840b…` since 2026-10-17 18:41 ET; `:v2.0.20-amd64` = prod (`f617c9ca…`) · `:v2.0.19` · `:v2.0.16` |
| Trackers | repo: #458/#459 decoder, #380 informational · ops: #395 closes with #441, #357 weewx side done (HLF accepts, ops closes), #265/#110 deferred-trigger · #306 residual · #344 macOS LAN |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

**S160 ran on Opus 5.5** (the desktop app's persisted selection): right for reading the upstream
replies and #465's design. The Sonnet floor is the owner's to restore in the app. S161 ran on Sonnet (a merge check and a mounted-file deploy). S162 is the quickstart proof: Sonnet.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after.** S151's and S152's small marvin-read traps (the live log path,
the secret-read guard on a trailing pipe, `exec-ro` argument limits, the classifier on container
reads) are in §3's last bullets.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-10-22 (S162). v2.0.20 steady in prod; arm64 container proof done; ops#427 open; v2.0.21 not yet cut._
