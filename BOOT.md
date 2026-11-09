# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S195 → S196)

### What's settled (do not re-derive)

**v2.4.0 runs in prod since 2026-11-04 18:36:38 ET** (image `82220200…`, banner `0.20+ws.10`):
DEC-0229's arrival-time gate in Go, `-tolerance` default 100 ms; `-tolerance 0` in the live `cmd` is
the no-rebuild off switch. Rollback: `:v2.3.0-prod-pre-v2.4.0` (`71c201b6…`), then
`:v2.2.0-prod-pre-v2.3.0`. **P0.8 phase 6 is built out**; only its acceptance test is left.
**loopjson 1.1.0** runs since 2026-10-27 09:16 ET. **ROADMAP fully reconciled S192 (PR #549), next
check due S202.**

**DEC-0229 in one line:** upstream re-anchors the hop clock to any CRC-valid frame, so a noise decode
cost a 2 to 5 min loss (13 of 16 garbage frames to date, last 11-04 12:53 ET); the gate drops a frame
over 100 ms off its transmitter's schedule. On-schedule bit-error frames (ERR-0012) are out of its
reach. **At `debug_rtld = 1` neither `tolerance=` nor `crc_stats` reaches the log, and `off-schedule
frames this period: 0` proves the driver only;** a `Go time gate dropped a frame` line is the proof
of a drop. **Two so far, neither with an archive gap: 11-05 05:06:39 ET, +725.6 ms, and 11-07
09:04:56 ET, +1036.2 ms (#536). Clear from 11-07 12:01 to 11-08 21:14 ET: no drop, no gap (1275
of 1275 records on 11-08).** `ops/garbage_gap_corr.py` reproduces the correlation from `marvinctl
grep ERROR` and `grep database` extracts. **The crcstats line is lowercase (`crc failures this
period`), so `grep CRC` is a false zero.** A day's gap check: `grep Added`, keep the `record
2026-…` stamps, flag steps over 90 s (each minute logs twice: archive + daily summary). Read-only
Flux works through the dashboard's public proxy, no token.

**S192 cruft audit (PR #565): `docs/CODE_REVIEW_S192.md`, #550 to #564**; its "Deliberately kept"
list is settled. Done: #551, #563's local half, S193's job 0(a), S194's #550 (DEC-0231) and #552
(DEC-0230), and **S195's #554 + #559 (PR #570, open):** `MANIFEST.md` at 3,258 chars (~815 tok),
under the 1,000 cap; the wxcheck pair has headers and pipes the repo copy through `marvinctl exec`
over stdin (**unexercised: the auto-mode classifier declined the live read**). The audit was wrong
twice (`docs/handoffs/` is cited by path; the Go tests did run in CI). **CI's tests job fails, not
skips, the Go gate tests (`REQUIRE_GO_TESTS=1`) and prints skips with `-rs`: expect 21.**

Standing facts: images are multi-arch (DEC-0214/0215); versions follow DEC-0222's SemVer rule; the
loop writer and `influx.py` ship as extensions, prod mounts both; `t-weewx` (996:986) runs under
`--cap-drop ALL`. **#475 is parked on purpose.** The prod log is `/srv/docker/weewx/logs/weewx.log`,
rotated daily, 30 days kept. The bundled Go decoder is byte-identical to `lheijst/rtldavis` master
(S178). Tests are pytest-only (#502). `marvinctl inspect` takes containers only (S185). On marvin,
`doctor` exits 13 (the dongle is held by prod); that is the correct verdict. **Running code inside
the prod container is a classifier-gated "production read"** (S195): plan for the owner to run it.

### ▶▶ S196 JOB LIST

0. **Audit triage, what is left.** (a) When #570 merges, close #550, #552, #554 and #559 with a
   comment each (merges to `dev` do not auto-close; the owner names closures), and ask ops to drop
   tier-sweep's `weewx-rtldavis:MANIFEST.md:OPS-DEC-0102:1094` exemption (stale once merged). (b)
   Design first: #561 (the dead `else` branches at `rtldavis.py` ~:1294/:1320, a baked-file
   behavior change), #553 (campaign apparatus: truthful headers now, retirement needs a DEC under
   DEC-0014; Opus 5.5). (c) **Owner decision before anything:** #558 (NAS-LEASE no-op in the
   public `influx` extension and the mounted prod file; a DEC and an `influx-v*` release). (d)
   Owner-authorized pushes: #563's 30 merged `origin/` branches and the `backfill-v2.0.20` tag;
   locally, the merged `claude/s192a-…` and `claude/s192b-…` branches remain.
1. **Read the gate's results since 11-08 21:14 ET:** any `Go time gate dropped a frame` line (keep
   its bytes and offset; expect under one a day; `marvinctl grep` takes one token, so grep `gate`)
   and any gap with no such line. Around 2026-12-04, re-run `ops/garbage_gap_corr.py` over the 30
   days after the deploy: expect no garbage-then-gap events. #536 stays open until then.
2. **Watch the three upstream threads still open** (the lheijst/rtldavis#2 comment, weewx-influx2#1,
   matthewwall/weewx-wcloud#6; if he adds a license, retag `wcloud.py`) and #514: **cdavis289's
   72-hour Go v0.21.2 vs Python v0.22.2 results were due about 11-09; read them before designing
   our A/B, no reply owed.** Keep `docs/UPSTREAM-THREADS.md` current.
3. **Needs the owner:** the GitHub About text and topics; `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in
   the shell profile (never CI); **the hot-swap code** — keep for the gain campaign `BACKLOG.md`
   carries, or a DEC to remove it with `ops/rx_experiment.sh` converted (#553 and DEC-0014 together).
4. **Phase 6's acceptance test:** a stock 64-bit Pi OS plus `docs/QUICKSTART.md`, timed, by someone
   who has not read the repo. Needs a person, not a session. First arm64 run against a live radio
   also still open (ops#439 proved the amd64 systemd path only).
5. **Watch, no action unless it fires:** `no bar_absolute` WARNING (DISC-0002) · WU gold star ·
   OWM/Windy rain in millimeters (needs rain; ERR-0010) · `Go burst gate dropped a frame` (fired
   11-08 19:50:07 ET, bytes in CHANGELOG [S195]; keep each one's bytes) · the first `unhealthy` on
   prod · any `rejecting implausible` or `unknown message type` line: run the correlation on that
   day's extracts; a gap behind one means a noise decode inside the 100 ms window, so add it to
   #536. Clear through 2026-11-08 21:14 ET except the 11-04 12:53 row.
6. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, the reset-from-112-or-above phantom, whether to tell the
   `weewx-packages` maintainer about DEC-0218 option B, `git worktree prune` in heartofgold, CI
   mypy pinned `2.3.0` while the pre-commit rev lags, the 10-27 double CRC-failure period (noted),
   `WEEWX_CONTAINER` unset for the monitor since S159 (a one-line heartofgold unit edit if the
   escalation email ever matters), the stale `weewx-data/wxcheck.py` on marvin (unused since #570).
7. **Second dongle, early December (reminder set for Sat 2026-12-05 09:00 ET):** the #514 A/B of
   hilman2's Python port (weewx-packages 0.22.0) beside our Go decoder, and a v3-vs-V4 A/B;
   hilman2's answers are on #514. **The V4 needs librtlsdr newer than bookworm's 0.6.0, so build
   the test container on trixie**; check which base our image uses. Any decoder swap needs a DEC.

## Current state (S195)

| Thing | State |
|---|---|
| Prod | marvin, `v2.4.0` as `:marvin-live` since 2026-11-04 18:36:38 ET, weewx 5.5.2, gain 372. Writer mounted at 1.1.0 since 2026-10-27 09:16 ET |
| InfluxDB / monitor | marvin, `weewx-influxdb.service`; weewx-monitor sha `2f8a1eda…` = `dev`, restarted 2026-11-07 13:43:18 ET, `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` (archive metric); 240 to 260 CRC failures a minute; 0 archive gaps 11-05 00:00 to 11-08 21:14 ET |
| `main`/`dev` | `main` = the v2.4.0 promotion (`c376037`, PR #545, `prod-baseline-20261104`); `dev` = main plus doc, test, CI and ops-script changes only; nothing baked differs |
| Docker Hub | `:v2.4.0` is the multi-arch index `2b146586…` (amd64 `82220200…` = prod, arm64 `e986aae1…`); `:latest` = `:v2.4.0` since 2026-11-06 01:52 ET, moved by the owner |
| Trackers | repo: #550/#552 (merged, to close), #554/#559 (PR #570), #553, #558, #561, #563 (half done), #536 (open until the 30-day re-run), #475 parked, #380 info, #514 (December A/B) · ops: #440 (second dongle), #110 (gated, Jan-Feb), #344 · upstream open: lheijst/rtldavis#2 comment, weewx-influx2#1, matthewwall/weewx-wcloud#6 |

## Blockers

Unchanged from S145 except blocker 1: 1 freeze mechanism (DEC-0068/0094) **now has a measured
mechanism for the short gaps (DEC-0229); the 10-22 62 min outage and DEC-0083's long tail are not
it**, 2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

S195 ran Opus 5.5 throughout (the picker was still raised from S193's bare `/model`, which
persists). **Switch the picker back to Sonnet by hand.** S196: Sonnet for the watches, closures
and pushes; Opus 5.5 only for #553/#561 design.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4).

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else (CLAUDE.md's Documentation map, DEC-0063).
Git workflow, secrets handling and the exact gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-11-08 (S195: #554 MANIFEST diet, #559 wxcheck headers, PR #570; gate clean)._
