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

## ▶ Resume here (S109 → S110)

### What's settled (do not re-derive)

**Campaign C is DONE — ran clean, no aborts, self-terminated to `BASELINE` exactly on schedule
(2026-08-31T11:00:00 ET).** All 10 pre-registered rows executed against the clock (`A B B A B A A B
A B`, confirmed against the actual deployed script on marvin, not assumed). Only 8 restart events
appear in the apparatus log because two row-pairs share an arm (21:30/23:00 both B, 03:30/05:00 both
A) and a `tick` finding the arm unchanged doesn't restart — not a schedule deviation. Block 1 launched
by hand at 21:24:19 (84 min after the 20:00 nominal start, already logged DEC-0122). `weewx.service`
confirmed healthy on gain 372 since the restore.

**The 372-vs-496 verdict is NOT decided (DEC-0124) — do not treat either number as the answer.** A
coarse proxy (monitor's 5-min `RECEPTION:` aggregate, NOT the sanctioned metric): A (372) 70.76%
(n=76) vs B (496) 72.63% (n=70), B +1.87 pts — under DEC-0059's 2.0-pt adoption bar. DEC-0069 exists
specifically because this coarse metric absorbs freeze-contamination bias (~0.6–0.8 pts); several
blocks in this run flagged 1–5 "bad windows." The sanctioned per-minute readout needs marvin-side
archive-DB access that does not exist today.

**⚠ ops#235 is a PRIORITY, not routine backlog — it blocks a live RF-gain decision.**
[ops#235](https://github.com/WeatheredScientist/eaglehunt-ops/issues/235) (marvinctl has no
self-service SQL read verb, filed weewx S107) is why the real readout can't be pulled: `ops/
campaign_analyze.py` is NAS-only, hardcoded to ssh `NAS_HOST`, never ported to marvin. This session
tested `marvinctl exec-ro` as a workaround (owner's explicit go-ahead — it's a `docker run` under the
hood and got Class-C-blocked once from this session) and confirmed, with a positive control, it has
**no working path**: the stdin-pipe idiom forwards nothing (a trivial `print()` produced zero output
at exit 0), and the `-c` argv path rejects any string with quotes/parens even at zero literal
whitespace (tested via base64+`exec`) — real code can't be expressed without them, so this is a dead
end, not something to keep encoding around. Findings added as a comment to ops#235 (already named
`exec-ro` "unexamined for this") rather than a duplicate issue. **Until ops#235 lands a working read
path, the only way to get the real verdict is an owner-mediated pull run directly on marvin, or
porting `campaign_analyze.py` to marvin as its own piece of work.**

**Housekeeping:** `ops/rx_experiment.sh`'s `SCHEDULE=` stood down to the empty DEC-0096 form now that
the terminator passed (`test_current_schedule_is_not_fully_stale` was correctly red until this
landed; suite green after, 457 passed / 14 skipped). Unrotated `weewx.log` and the `t-hlf` tenant
were checked clear at S109 for the campaign's duration only — not re-checked this session; the
logrotate gap itself is still owed as its own job. `weewx-rx-experiment.timer`'s hands-off-guest
window (MARVIN-DEC-0088) has lapsed with the campaign's close — a fresh declaration is needed for any
future RF-position-sensitive work.

**⚠ Unchanged, still open: the 6-hourly reception-summary email is broken, needs the owner** —
`--test-alert` fails SMTP auth (535 "Bad Credentials") from Gmail, ruled out on the config/file side
on marvin. Needs the owner's own Google account access. Full trail: marvin's `DECISIONS.md`,
MARVIN-DEC-0093/-0095/-0097.

### ▶▶ S110 JOB LIST

**Live, in order:**
1. ✅ **Campaign C completed clean** — see "What's settled" above. No action needed on the campaign
   itself.
2. **⚠ PRIORITY — get ops#235 resolved, or the 372-vs-496 verdict stays stuck.** This blocks a real
   production decision (which gain to run at marvin's actual RF position), not a convenience. Next
   session: check whether ops#235 has moved; if not, that itself is the escalation point — this has
   now sat open since S107 across an entire completed campaign with no readout to show for it.
3. **Once ops#235 (or an owner-mediated pull) unblocks the read: run the actual DEC-0069 per-minute
   analysis and log the real adoption verdict as its own DEC.** Campaign C's raw data already exists
   on marvin and isn't going anywhere — this is purely a tooling gap, not a data-loss risk.
4. **Verify the archive DB is readable unprivileged before enabling the reception-summary path.**
   `weewx.sdb` is mode `0500 t-weewx`, written by root in-container. If it is WAL, a `?mode=ro` open
   may fail needing `-shm` write — DEC-0119's bug class. **Unverified; do not assume either way.**
   (Effectively the same underlying access gap as ops#235 — likely resolved by the same fix.)
5. **Then** flip `REMEDY_MODE=none` → `restart_unit` — but **not yet, and not via `marvinctl`.**
   Confirmed by a marvin-side session at S107: **no local grant exists today.** The only sudoers
   lines on the box serve the **ssh forced-command** path, and `marvinctl` is the *remote* client —
   a `t-weewx`-uid daemon already on the box has no ssh hop to make and cannot invoke it to escalate
   itself. **The only path is a narrow marvin-side grant** — one sudoers line (`t-weewx` →
   `/usr/bin/systemctl restart weewx.service`) or a scoped polkit rule — a marvin-repo change needing
   owner ratification and its own DEC row. Setting `restart_unit` without the grant yields a remedy
   that fails every time while looking correct (DEC-0061). **`REMEDY_MODE=none` permanently is a
   defensible end state**, not an unfinished job: the remedy's entire evidence record is a USB reset
   aimed at hardware that has since changed boxes.
6. **`usb_watchdog.sh`'s fate** — still simply OFF, still undecided. ops#233's sibling finding.
7. **File a durable logrotate fix for marvin** — the gap itself is still unaddressed; not numbered
   as its own job yet, fold into the next ROADMAP/job-list pass.

**Carried forward, untouched:**
8. **`main` promotion for v2.0.14** — deliberately deferred (DEC-0114).
9. **Convert `ops/rx_experiment.sh` to the DEC-0117 control file** — gated on job 10.
10. **DEC-0117 hot swap needs an image rebuild to reach prod** (off by default). Still unverified
    whether marvin can build natively vs. repeating the `docker save`/`load` dance.
11. **Foundation decommission timing** — owner's call, after a week-plus soak.
12. **NAS-LEASE cross-host wiring** — low priority; marvin's `/nas-lease` is a deliberate no-op.
13. **`CONSTANTS.md`'s infra section second pass** — still not re-verified row by row.
14. **Sanity-check ops' `CONSTANTS.md` §5 register row** for weewx's token (`ef8e9af8`).

**Retired this session (S110):** ~~campaign C in flight~~ — completed clean, see above; ~~get the
interim/final readout~~ — replaced by "verdict blocked on ops#235" (job 2) since the sanctioned tool
turned out to be unreachable from this session.

### Current state (S110 open)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` (a restart IS a full recreate) — two-tenant box (`t-hlf` / `weather-hlf.slice`, ops#234, checked no-impact at S109, not re-checked this session) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, **gain 372 live — campaign C closed, verdict on 372-vs-496 blocked on ops#235 (DEC-0124)** |
| Alerting | `weewx_monitor.py` (`REMEDY_MODE=none`) live. `weewx-rx-experiment.timer` fired cleanly all night (no gaps, no failed runs) — now a documented no-op against the stood-down empty `SCHEDULE=`. `usb_watchdog.sh` still OFF (job 6, undecided) |
| `marvinctl` | Tier-1 reads proven (needs `--tenant weewx`). **`exec-ro` confirmed non-functional for ad-hoc code** (S110, this session — see ops#235 comment). No working self-service DB read path exists |
| Campaign C | **CLOSED** — ran 2026-08-30T21:24 → 2026-08-31T11:00 ET clean, no aborts, self-terminated on schedule. Real adoption verdict pending ops#235 |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, unchanged) — unrotated-log and `t-hlf`-tenant risks checked clear at S109, not re-verified this session |
| Trackers | **ops#235 (PRIORITY — see above)** · ops#233 answered by DEC-0120 (not closed — deploy landed, verify-and-close still owed) · #216/#214/#110 open · repo #274/#253 open |


## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven on
   the NAS specifically. S105 added a data point (independent confirmation on different hardware,
   firing only under a bad USB controller); untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). Untouched this session.
3. **ERR-0005** — unchanged.
4. `ppm`/`fc` — still unmeasured; deliberately unchanged for Campaign B, no sweep data to fall back on.
5. **6-hourly reception-summary email broken (S108 find)** — Gmail SMTP rejects with 535 "Bad
   Credentials"; ruled out on the config/file side on marvin (sha-identical `GMAIL_PASS`, no embedded
   spaces). Needs the owner's own Google account access to diagnose — not actionable from either box.
6. **⚠ ops#235 — marvinctl has no self-service archive-DB read (S110, priority).** Blocks the real
   372-vs-496 adoption verdict from campaign C, which otherwise ran clean and is sitting on real data
   with no way to read it. `exec-ro` confirmed this session to have no working path as a stopgap. Owner
   directive: prioritize resolving this over routine backlog.

## Model tier

No `/model` switch this session. Nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-31 (S110). Green gate re-run clean after this session's one code change (the
`SCHEDULE=` stand-down): ruff clean, 457 passed / 14 skipped, mypy clean (66 files), secret gate
clean. Session summary: campaign C closed clean, the real adoption verdict is blocked on ops#235
(now flagged priority — see "What's settled" and DEC-0124 for the full findings), and BOOT/DECISIONS/
CHANGELOG/ROADMAP are all reconciled to that state._
