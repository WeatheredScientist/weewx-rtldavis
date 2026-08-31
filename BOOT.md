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

## ▶ Resume here (S111 → S112)

### What's settled (do not re-derive)

**Campaign C is DONE and the 372-vs-496 verdict is DECIDED (DEC-0125): 496 does NOT clear the
2.0-pt adoption bar at marvin's RF position — gain holds at 372, no config change.** Real per-minute
readout: A (372) 72.82% (n=368) vs B (496) 73.98% (n=350), **+1.16 pts** — smaller than the coarse
5-min proxy's +1.87 lean (DEC-0124), still under the bar either way. This is a standalone finding
that Foundation's DEC-0115 answer doesn't transfer to marvin's closer, fewer-walls site, not a
reversal of DEC-0115 itself. One clean overnight run stays directional (PRINCIPLES §3) — a real
multi-day campaign is `BACKLOG.md`'s open idea if the question is worth resolving further, not owed
as a follow-up.

**ops#235 is fixed and confirmed working for weewx's actual use case (S111).** An ops-side session
found and fixed the bug DEC-0124 hit dead: `marvinctl exec-ro`'s underlying `docker run` was missing
`-i`, so container stdin was always closed. Verified end-to-end this session, not just on the fix's
own positive control: piped a real read-only SQLite query through `exec-ro` against the live,
mode-`0500` archive DB and got 1333 clean rows back, exit 0. **This also verifies the old job 4
concern** — the DB's `journal_mode=DELETE` pin means `mode=ro` opens cleanly, no `-shm`
complication. `ops/campaign_analyze.py`'s own analysis functions were reused directly (imported, not
re-derived) against the fetched rows.

**Reconciled this session:** `CONSTANTS.md` (gain row, hardware/site prose, timeline),
`docs/ROADMAP.md` (Campaign B/C item closed as a marvin result too), `BACKLOG.md` (gain re-sweep item
closed), `docs/DECISIONS.md`/`DECISIONS-FULL.md` (DEC-0125 added, DEC-0124 marked superseded).

**Unchanged, still open: the 6-hourly reception-summary email is broken, needs the owner** —
`--test-alert` fails SMTP auth (535 "Bad Credentials") from Gmail, ruled out on the config/file side
on marvin. Needs the owner's own Google account access. Full trail: marvin's `DECISIONS.md`,
MARVIN-DEC-0093/-0095/-0097.

**Unchanged from S110: `weewx-rx-experiment.timer`'s hands-off-guest window (MARVIN-DEC-0088) has
lapsed with the campaign's close** — a fresh declaration is needed for any future RF-position-
sensitive work. The logrotate gap and the unrotated-`weewx.log`/`t-hlf`-tenant risk checks are also
unrefreshed this session.

### ▶▶ S112 JOB LIST

**Live, in order:**
1. **Flip `REMEDY_MODE=none` → `restart_unit` — not yet, and not via `marvinctl`.** Confirmed by a
   marvin-side session at S107: **no local grant exists today.** The only sudoers lines on the box
   serve the **ssh forced-command** path, and `marvinctl` is the *remote* client — a `t-weewx`-uid
   daemon already on the box has no ssh hop to make and cannot invoke it to escalate itself. **The
   only path is a narrow marvin-side grant** — one sudoers line (`t-weewx` →
   `/usr/bin/systemctl restart weewx.service`) or a scoped polkit rule — a marvin-repo change needing
   owner ratification and its own DEC row. Setting `restart_unit` without the grant yields a remedy
   that fails every time while looking correct (DEC-0061). **`REMEDY_MODE=none` permanently is a
   defensible end state**, not an unfinished job: the remedy's entire evidence record is a USB reset
   aimed at hardware that has since changed boxes.
2. **`usb_watchdog.sh`'s fate** — still simply OFF, still undecided. ops#233's sibling finding.
3. **File a durable logrotate fix for marvin** — the gap itself is still unaddressed; not numbered
   as its own job yet, fold into the next ROADMAP/job-list pass.

**Carried forward, untouched:**
4. **`main` promotion for v2.0.14** — deliberately deferred (DEC-0114).
5. **Convert `ops/rx_experiment.sh` to the DEC-0117 control file** — gated on job 6.
6. **DEC-0117 hot swap needs an image rebuild to reach prod** (off by default). Still unverified
   whether marvin can build natively vs. repeating the `docker save`/`load` dance.
7. **Foundation decommission timing** — owner's call, after a week-plus soak.
8. **NAS-LEASE cross-host wiring** — low priority; marvin's `/nas-lease` is a deliberate no-op.
9. **`CONSTANTS.md`'s infra section second pass** — still not re-verified row by row.
10. **Sanity-check ops' `CONSTANTS.md` §5 register row** for weewx's token (`ef8e9af8`).

**Retired this session (S111):** ~~get ops#235 resolved~~ — fixed ops-side, confirmed working;
~~run the real DEC-0069 analysis and log the adoption verdict~~ — done, DEC-0125; ~~verify the
archive DB is readable unprivileged~~ — confirmed via the same read.

### Current state (S111 open)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` (a restart IS a full recreate) — two-tenant box (`t-hlf` / `weather-hlf.slice`, ops#234, checked no-impact at S109, not re-checked this session) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, **gain 372 live — campaign C closed, verdict DECIDED (DEC-0125): 372 holds** |
| Alerting | `weewx_monitor.py` (`REMEDY_MODE=none`) live. `weewx-rx-experiment.timer` fired cleanly all night (no gaps, no failed runs) — now a documented no-op against the stood-down empty `SCHEDULE=`. `usb_watchdog.sh` still OFF (job 2, undecided) |
| `marvinctl` | Tier-1 reads proven (needs `--tenant weewx`). **`exec-ro` self-service DB read CONFIRMED WORKING (S111)** — stdin-pipe fix verified live against the real archive DB |
| Campaign C | **CLOSED** — ran 2026-08-30T21:24 → 2026-08-31T11:00 ET clean, no aborts, self-terminated on schedule. **Adoption verdict DECIDED (DEC-0125): 496 does not clear the bar, 372 holds** |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, unchanged) — unrotated-log and `t-hlf`-tenant risks checked clear at S109, not re-verified this session |
| Trackers | ops#235 fixed, confirmed working (not closed — that's the ops repo's own call) · ops#233 answered by DEC-0120 (not closed — deploy landed, verify-and-close still owed) · #216/#214/#110 open · repo #274/#253 open |


## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven on
   the NAS specifically. S105 added a data point (independent confirmation on different hardware,
   firing only under a bad USB controller); untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). Untouched this session.
3. **ERR-0005** — unchanged.
4. `ppm`/`fc` — still unmeasured; deliberately unchanged for Campaign B, no sweep data to fall back on.
5. **6-hourly reception-summary email broken (S108 find)** — Gmail SMTP rejects with 535 "Bad
   Credentials"; ruled out on the config/file side on marvin. Needs the owner's own Google account
   access to diagnose — not actionable from either box.

## Model tier

No `/model` switch this session. Nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-31 (S111). Session summary: ops#235 fixed ops-side and confirmed working with
the real blocked use case; ran the real DEC-0069 per-minute analysis on Campaign C's data — 496 does
not clear the adoption bar at marvin, gain holds at 372 (DEC-0125); BOOT/DECISIONS/CHANGELOG/ROADMAP/
BACKLOG/CONSTANTS all reconciled to that state. Green gate re-run clean (docs-only session, no code
changed): ruff clean, 457 passed / 14 skipped, mypy clean (66 files), secret gate clean over the
whole tracked tree._
