# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S185 → S186)

### What's settled (do not re-derive)

**v2.3.0 runs in prod since 2026-11-01 11:31:49 ET** (image `71c201b6…`, driver banner still
`0.20+ws.9`, no driver change): DEC-0225 item 5 built as DEC-0228 (`ENTRYPOINT` dispatch, `doctor`,
the informational `HEALTHCHECK` on `weewx.log`) plus `WEEWX_DRIVER=simulator` at seed time. First
record after the restart 11:34:00 ET, container `healthy`, no warnings. Rollback:
`:v2.2.0-prod-pre-v2.3.0` (`0a790696…`), then `:v2.1.0-prod-pre-v2.2.0`. **P0.8 phase 6 is built
out**; only its acceptance test is left. **loopjson 1.1.0** runs since 2026-10-27 09:16 ET. ROADMAP
full reconciliation done S183 (next check S192). Phases 3, 4 and 5 are done (S180/S181).

Standing facts: images are multi-arch (DEC-0214/0215); versions follow DEC-0222's SemVer rule; the
loop writer and `influx.py` ship as extensions, prod mounts both; `t-weewx` (996:986) runs under
`--cap-drop ALL`. **#475 is parked on purpose.** The prod log is `/srv/docker/weewx/logs/weewx.log`.
The bundled Go decoder is byte-identical to `lheijst/rtldavis` master (S178). Tests are pytest-only
(#502). `marvinctl inspect` takes containers only, not images (S185). On marvin, `doctor` exits 13
(the dongle is held by prod) — that is the correct verdict there, not a fault.

### ▶▶ S186 JOB LIST

1. **v2.3.0 is fully released** (PR #530, tags, GitHub release with three assets, Hub `:v2.3.0` and
   `:latest` = index `03f3c891…`). Nothing left on the release; this line goes next session.
2. **Watch the five upstream posts for replies** (weewx-contrib#2, weewx-packages#6, the
   lheijst/rtldavis#2 comment, weewx-influx2#1, matthewwall/weewx-wcloud#6; if he adds a license,
   retag `wcloud.py`) and keep `docs/UPSTREAM-THREADS.md` current.
3. **Phase 6's acceptance test:** a stock 64-bit Pi OS plus `docs/QUICKSTART.md`, timed, by someone
   who has not read the repo. Needs a person, not a session.
4. **Needs the owner:** the GitHub About text and topics; `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in
   the shell profile (never CI); **the hot-swap code** (~230 driver lines, no in-repo producer;
   #509's PR body has the analysis) — keep for the gain campaign `BACKLOG.md` carries, or a DEC to
   remove it with `ops/rx_experiment.sh` converted (DEC-0014).
5. **ops#439** (virtual-USB guest for `docs/DEPLOY.md`'s three systemd checks): heartofgold
   installed real USB passthrough (`marvin-vm create --usb-host`, MARVIN-DEC-0219, 11-01); the live
   attach waits on the owner's flash drive. Hold until HoG confirms on the issue. First arm64 run
   against a live radio still open.
6. **Watch, no action unless it fires:** `no bar_absolute` WARNING (DISC-0002) · WU gold star ·
   OWM/Windy rain in millimeters (needs rain; ERR-0010) · the next freeze (blocker 1) · any
   `Go burst gate dropped a frame` line (keep its bytes) · the first `unhealthy` on prod (it never
   restarts anything; note what the log was doing).
7. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, the reset-from-112-or-above phantom, whether to tell the
   `weewx-packages` maintainer about DEC-0218 option B, `git worktree prune` in heartofgold (stale
   S161 entry), CI mypy pinned `2.3.0` while the pre-commit rev lags, the `.claude/worktrees/s180b-*`
   leftover in this checkout.
8. **Second dongle, early December (reminder set for Sat 2026-12-05 09:00 ET):** the #514 A/B of
   hilman2's Python port beside our Go decoder, and a v3-vs-V4 A/B. Holding reply posted (10-30);
   hilman2 answered: option names stable through 0.22.x, Pi 4 demodulator 9.7% of one core (31% in
   frequency search), no x86 numbers yet. **The V4 needs librtlsdr newer than Debian bookworm's
   0.6.0, so build the test container on trixie**; check which base our image uses. The maintainer
   question waits on the test; any decoder swap needs a DEC (DEC-0014).

## Current state (S185)

| Thing | State |
|---|---|
| Prod | marvin, `v2.3.0` as `:marvin-live` since 2026-11-01 11:31:49 ET, weewx 5.5.2, gain 372, `healthy`. Writer mounted at 1.1.0 since 2026-10-27 09:16 ET |
| InfluxDB / monitor | marvin, `weewx-influxdb.service`; weewx-monitor sha `5cd09917…`, `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| `main`/`dev` | `main` = the v2.3.0 promotion (`fe3761a`, PR #530, `prod-baseline-20261101`); `dev` = main plus this release closeout |
| Docker Hub | `:v2.3.0` and `:latest` are the multi-arch index `03f3c891…` (amd64 `71c201b6…` = prod, arm64 `c0d54664…`), `:latest` moved by the owner 2026-11-01 12:25 ET |
| Trackers | repo: #475 parked, #380 info, #514 (December A/B) · ops: #439 (virtual-USB guest, waiting on HoG), #433 (this file), #357, #344 · upstream: weewx-contrib#2, weewx-packages#6, lheijst/rtldavis#2 comment (all 10-29), weewx-influx2#1 (reply 10-29), matthewwall/weewx-wcloud#6 (license request, 10-29). ops#435 answered (120 rows), ops#441 closed |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

S185 started on Sonnet (status), then Fable 5.1 by the owner's call as the coordinator for an
attended release; children S185a (Opus 5.5 `medium`) and S185b (Sonnet `medium`) in their own
worktrees. The desktop app's model picker shows Fable: switch it back by hand (settings.json's floor
was never touched). S186's job 1 is execution, Sonnet.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4).
S180 adds to §2: this repo requires PR branches current with `dev`, so after one merge every other
open PR needs `gh pr update-branch` and a CI rerun before its own merge — sequence them. S185 adds:
two children that append to the same file conflict anyway; resolve by keeping both blocks.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else (CLAUDE.md's Documentation map, DEC-0063).
Git workflow, secrets handling and the exact gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-11-01 (S185: v2.3.0 built and deployed; phase 6 built out)._
