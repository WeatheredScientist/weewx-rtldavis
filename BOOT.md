# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S180 → S181)

### What's settled (do not re-derive)

**v2.1.0 runs in prod since 2026-10-28 15:40:40 ET** (image `6e10c71b…`, driver banner `0.20+ws.8`:
#459's burst gate + #481's `windGust10`). Rollback: `:v2.1.0-predeploy` (`a1e6e94c…`) then
`:v2.0.21`. `main` = `prod-baseline-20261028`; Hub `:v2.1.0` is the multi-arch index `881e6c43…`;
`:latest` is still `:v2.0.20`. **loopjson 1.1.0** runs since 2026-10-27 09:16 ET. ROADMAP next check
**S182**. S178's v2.1.0 watch (15:40–17:22 ET) was clean.

**`dev` now carries baked-layer changes prod does not have** (S180): #507 added `rest_site.py`, a new
BAKED module shared by `owm.py`/`windy.py` (Dockerfile COPY, `.dockerignore`, a smoke step asserting
the MRO), and #509 made the driver's QC block and `genLoopPackets` concise and dropped the dead
`windBatteryStatus` line. Payloads and packets are pinned identical by tests in both PRs. They ship
with the next release, **v2.1.1** (no contract change, DEC-0222), banner `ws.9` on the release
branch. **P0.8 phase 5 is done except audit 28** (owner read). **Phase 4 posted 2026-10-29**:
weewx-contrib#2, weewx-packages#6, and the DEC-0223 mechanism on lheijst/rtldavis#2
(`docs/UPSTREAM-THREADS.md`). The four-fixes offer to lheijst was dropped: weewx-packages already
carries all but the string version compare.

Standing facts: images are multi-arch (DEC-0214/0215); versions follow DEC-0222's SemVer rule; the
loop writer and `influx.py` ship as extensions, prod mounts both; `t-weewx` (996:986) runs under
`--cap-drop ALL`. **#475 is parked on purpose.** The prod log is `/srv/docker/weewx/logs/weewx.log`.
The bundled Go decoder is byte-identical to `lheijst/rtldavis` master (S178). Tests are pytest-only
(#502). Branches: `dev`, `main`, plus the merged `claude/s180*` and `s179-*` remotes to prune.

### ▶▶ S181 JOB LIST

1. **11-02 morning, cheap:** count archive rows for 2026-11-01 05:00–07:00 UTC (expect 120, no gap,
   no duplicate) and post the number on eaglehunt-ops#435.
2. **weewx-influx2#1 reply (phase 4's last item):** two edits on the fork branch
   `fix/tls-verification-and-py312-compat` (`influx.py:501` `loginf` → `logdbg`; a `verify_ssl`
   line in the config docs), push on the owner's go, then post the held text in
   `docs/upstream/phase4-influx2-reply.md`.
3. **Watch the three 10-29 posts for replies** and keep `docs/UPSTREAM-THREADS.md` current.
4. **Next release, v2.1.1, when wanted:** carries #507, #509 and #506's header-only patch fix.
   Bump the banner to `ws.9` and the version strings on the release branch (S175's list), build on
   marvin per `CONSTANTS.md` Release mechanics, join multi-arch, tag + GitHub release ride the
   promotion (closeout step 0).
5. **Needs the owner:** audit 28 (`-or-later` on the derived uploaders); move `:latest` to
   `:v2.1.0`; the GitHub About text and topics; `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the shell
   profile (never CI); **the hot-swap code** (~230 driver lines, no in-repo producer; #509's PR body
   has the analysis) — keep for the gain campaign `BACKLOG.md` carries, or a DEC to remove it with
   `ops/rx_experiment.sh` converted (DEC-0014).
6. **ops#439** (a guest with a virtual USB device for `docs/DEPLOY.md`'s three systemd checks,
   phase 1's last line): filed 10-29, marvin rung; nothing to do until it answers. First arm64 run
   against a live radio still open.
7. **Watch, no action unless it fires:** `no bar_absolute` WARNING (DISC-0002) · WU gold star ·
   OWM/Windy rain in millimeters (needs rain; ERR-0010) · the next freeze (blocker 1) · any
   `Go burst gate dropped a frame` line (keep its bytes).
8. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, the reset-from-112-or-above phantom, whether to tell the
   `weewx-packages` maintainer about DEC-0218 option B (they now know of the fork: #6), `git worktree
   prune` in heartofgold (stale S161 entry), CI mypy pinned `2.3.0` while the pre-commit rev lags.

## Current state (S180)

| Thing | State |
|---|---|
| Prod | marvin, `v2.1.0` as `:marvin-live` since 2026-10-28 15:40:40 ET, weewx 5.5.2, gain 372. Writer mounted at 1.1.0 since 2026-10-27 09:16 ET |
| InfluxDB / monitor | marvin, `weewx-influxdb.service`; weewx-monitor sha `5cd09917…`, `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| `main`/`dev` | `main` = v2.1.0's promotion (`prod-baseline-20261028`); `dev` = main plus S178's #501/#502, S179's #504/#505, S180's #506–#509 (two baked-layer changes awaiting v2.1.1) |
| Docker Hub | `:v2.1.0` multi-arch; `:latest` still `:v2.0.20` until the owner moves it |
| Trackers | repo: #475 parked, #380 info · ops: #435 (11-02 count), #439 (virtual-USB guest), #433 (this file), #357, #344 · upstream: weewx-contrib#2, weewx-packages#6, lheijst/rtldavis#2 comment (all 10-29), weewx-influx2#1 (reply held) |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

S180 ran on Fable 5.1 by the owner's call, as a coordinator: audit 23 and 24 on Opus 5.5 `medium`,
39 and 30 on Sonnet (`high`, `low`), each in its own worktree. S181 is Sonnet work; the influx2 push
and the hot-swap DEC are the only judgment items (Opus 5.5 `medium` if taken). The desktop app's
model picker still shows Fable: switch it back by hand (settings.json's floor was never touched).

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4).
S180 adds to §2: this repo requires PR branches current with `dev`, so after one merge every other
open PR needs `gh pr update-branch` and a CI rerun before its own merge — sequence them.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else (CLAUDE.md's Documentation map, DEC-0063).
Git workflow, secrets handling and the exact gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-10-29 (S180). Phase 5 done but 28; phase 4 posted; S179's closeout written here._
