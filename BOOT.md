# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S184 → S185)

### What's settled (do not re-derive)

**v2.2.0 runs in prod since 2026-10-31 10:51:42 ET** (image `0a790696…`, driver banner
`0.20+ws.9`): P0.8 phase 6's install path (DEC-0225, built as DEC-0227) plus S180's baked changes
(#507 `rest_site.py`, #509 the concise QC block, #506), so there was no v2.1.1. First record after
the restart: 10:54:00 ET, no errors. Rollback: `:v2.1.0-prod-pre-v2.2.0` (`6e10c71b…`) then
`:v2.1.0-predeploy`. **loopjson 1.1.0** runs since 2026-10-27 09:16 ET. ROADMAP full
reconciliation done S183 (next check S192). **P0.8 phase 5 is done**; audit 28 closed by DEC-0226 (S181: `influx.py` and `ogoxeUploader.py` are `GPL-3.0-only`, `wcloud.py` is `NOASSERTION`). **Phase 4 is done (posted 2026-10-29)**:
weewx-contrib#2, weewx-packages#6, the DEC-0223 mechanism on lheijst/rtldavis#2, and the
weewx-influx2#1 reply after commit `0c5d394` on the fork branch (`docs/UPSTREAM-THREADS.md`). The four-fixes offer to lheijst was dropped: weewx-packages already
carries all but the string version compare.

Standing facts: images are multi-arch (DEC-0214/0215); versions follow DEC-0222's SemVer rule; the
loop writer and `influx.py` ship as extensions, prod mounts both; `t-weewx` (996:986) runs under
`--cap-drop ALL`. **#475 is parked on purpose.** The prod log is `/srv/docker/weewx/logs/weewx.log`.
The bundled Go decoder is byte-identical to `lheijst/rtldavis` master (S178). Tests are pytest-only
(#502). Branches: `dev`, `main`, plus the merged `claude/s180*` and `s179-*` remotes to prune.

### ▶▶ S185 JOB LIST


1. **11-02 morning, cheap:** count archive rows for 2026-11-01 05:00–07:00 UTC (expect 120, no gap,
   no duplicate) and post the number on eaglehunt-ops#435.
2. **Watch the five upstream posts for replies** (weewx-contrib#2, weewx-packages#6, the
   lheijst/rtldavis#2 comment, weewx-influx2#1, and matthewwall/weewx-wcloud#6, the license
   request, posted 10-29 after DEC-0226; if he adds a license, retag `wcloud.py` to match) and keep `docs/UPSTREAM-THREADS.md` current.
3. **Later releases of DEC-0225:** `doctor` and the informational `HEALTHCHECK` (E), the
   `WEEWX_DRIVER=simulator` profile (F), then phase 6's acceptance test (a stock 64-bit Pi OS plus
   the quick start, timed, by someone who has not read the repo).
4. **Needs the owner:** the GitHub About text and topics; `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the shell
   profile (never CI); **the hot-swap code** (~230 driver lines, no in-repo producer; #509's PR body
   has the analysis) — keep for the gain campaign `BACKLOG.md` carries, or a DEC to remove it with
   `ops/rx_experiment.sh` converted (DEC-0014).
5. **ops#439** (a guest with a virtual USB device for `docs/DEPLOY.md`'s three systemd checks,
   phase 1's last line): filed 10-29, marvin rung; nothing to do until it answers. First arm64 run
   against a live radio still open.
6. **Watch, no action unless it fires:** `no bar_absolute` WARNING (DISC-0002) · WU gold star ·
   OWM/Windy rain in millimeters (needs rain; ERR-0010) · the next freeze (blocker 1) · any
   `Go burst gate dropped a frame` line (keep its bytes).
7. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, the reset-from-112-or-above phantom, whether to tell the
   `weewx-packages` maintainer about DEC-0218 option B (they now know of the fork: #6), `git worktree
   prune` in heartofgold (stale S161 entry), CI mypy pinned `2.3.0` while the pre-commit rev lags.
8. **Second dongle, early December (reminder set for Sat 2026-12-05 09:00 ET):** the #514 A/B of
   hilman2's Python port beside our Go decoder, and a v3-vs-V4 A/B. Our holding reply is posted
   (10-30); hilman2 answered: option names stable through 0.22.x, Pi 4 demodulator 9.7% of one
   core (31% in frequency search), no x86 numbers yet. **The V4 needs librtlsdr newer than Debian
   bookworm's 0.6.0, so build the test container on trixie**; check which base our image uses.
   The maintainer question waits on the test; any decoder swap needs a DEC (DEC-0014).

## Current state (S184)

| Thing | State |
|---|---|
| Prod | marvin, `v2.2.0` as `:marvin-live` since 2026-10-31 10:51:42 ET, weewx 5.5.2, gain 372. Writer mounted at 1.1.0 since 2026-10-27 09:16 ET |
| InfluxDB / monitor | marvin, `weewx-influxdb.service`; weewx-monitor sha `5cd09917…`, `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| `main`/`dev` | `main` = the v2.2.0 promotion (`prod-baseline-20261031`, `8ed61a0`); `dev` = main plus the host-setup asset-name fix |
| Docker Hub | `:v2.2.0` and `:latest` are the multi-arch index `3f580af7…` (published S184); `:v2.1.0` multi-arch |
| Trackers | repo: #475 parked, #380 info · ops: #435 (11-02 count), #439 (virtual-USB guest), #433 (this file), #357, #344 · upstream: weewx-contrib#2, weewx-packages#6, lheijst/rtldavis#2 comment (all 10-29), weewx-influx2#1 (reply posted 10-29), matthewwall/weewx-wcloud#6 (license request, 10-29) |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

S180 ran on Fable 5.1 by the owner's call, as a coordinator: audit 23 and 24 on Opus 5.5 `medium`,
39 and 30 on Sonnet (`high`, `low`), each in its own worktree. S181 is Sonnet work; the
hot-swap DEC is the only judgment item (Opus 5.5 `medium` if taken). The desktop app's
model picker still shows Fable: switch it back by hand (settings.json's floor was never touched).

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4).
S180 adds to §2: this repo requires PR branches current with `dev`, so after one merge every other
open PR needs `gh pr update-branch` and a CI rerun before its own merge — sequence them.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else (CLAUDE.md's Documentation map, DEC-0063).
Git workflow, secrets handling and the exact gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-10-30 (S183: ROADMAP full reconciliation). Phases 4 and 5 done._
