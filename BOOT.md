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

**`usb_watchdog.sh` is RETIRING, not porting (ops#233, MARVIN-DEC-0100)** — it targeted Foundation-only
USB paths; `MARVIN-DEC-0064` already fixed the failure mode it existed for (the dongle's permanent
home is marvin's CPU-attached xHCI, not the chipset one that lost hop-tracking). Matches
`REMEDY_MODE=none`. Stays OFF permanently by design, not by neglect — nothing further owed here.

**✅ Campaign D is pre-registered, shipped, deployed, and ARMED on marvin — launches automatically
2026-08-31T21:00 ET (DEC-0126).** Triggered by DEC-0125: Foundation's pilot-derived shortlist
{372, 496} was never actually validated for marvin, so this re-runs the shortlisting step there. Six
gain-only blocks HIGH→LOW — 496, 449, 402, 372, 328, 207 — 45 min each, finishing 01:30 ET, clear of
the site's notch hours on both ends. `SCHEDULE=` is populated (no longer the DEC-0096 stand-down
state), `arm_cmd()` has `P207`, `campaign_analyze.py`'s `LEGENDS` has `"D"`, and
`tests/test_rx_experiment.py` has full structural coverage (465 passed / 9 skipped). Arm-selection
input only, never adoption evidence (same doctrine as Foundation's own pilots).

**Pre-launch checklist done this session, live on marvin (owner-authorized, via marvin-admin token
path):** `rx_experiment.sh` deployed to `/srv/docker/weewx/` (hash-verified) · Campaign C's stale
baseline snapshot archived to `.campaignC` (was blocking `install`) · `install` succeeded — fresh
baseline snapshotted 17:44 ET, `rx_experiment.state` reads `NONE\|0\|1970-01-01 00:00:00` (armed, no
arm set — exactly the expected post-install state) · `logs/campaign.inhibit` set · monitor confirmed
healthy (75% reception, actively polling) via `marvinctl` directly, no marvin-side session needed for
that check. The already-running root timer (`weewx-rx-experiment.timer`, DEC-0123) picks up the first
arm automatically once the clock crosses 21:00 — **no further command needed for launch itself.**

**Still needed, not a command: the hands-off-guest declaration** (MARVIN-DEC-0088's own — the prior
one lapsed with Campaign C's close) for tonight's window. Owner's call, not something run from here.

### ▶▶ S112 JOB LIST

**Live, in order:**
1. **Once Campaign D closes (~01:30 ET, or on abort): pull the readout and log the arm-selection
   result.** `marvinctl exec-ro` + `campaign_analyze.py --campaign D` — no owner-mediated wait this
   time (ops#235 is fixed). Then empty `SCHEDULE=` back to the DEC-0096 stand-down state, or
   `tests/test_rx_experiment.py::test_current_schedule_is_not_fully_stale` starts failing CI once the
   terminator passes (same mechanism that caught Campaign C's own stale schedule).
2. **Flip `REMEDY_MODE=none` → `restart_unit` — the grant question is RESOLVED (`ops#233`,
   MARVIN-DEC-0099, corrected 2026-08-31, mid-Campaign-C), the switch itself is not yet exercised.**
   An earlier S107 finding on this file ("no local grant exists, needs a new marvin-repo sudoers/
   polkit change") was itself wrong and has been corrected upstream: `t-weewx` already holds
   `NOPASSWD: /usr/local/lib/marvin/marvin-own weewx *` (installed at tenant onboarding, verified
   live via `sudo -n -l -U t-weewx`), and the tenant manifest's `units = weewx*.service` glob already
   covers `weewx.service`. **No new privilege plumbing needed** — whatever runs the remedy just needs
   `User=t-weewx` in its own unit file and to call
   `sudo -n /usr/local/lib/marvin/marvin-own weewx restart weewx.service`. **Not yet exercised as a
   real restart** (verification-only so far; a live restart belongs at weewx's actual deploy time,
   not a verification session) — that live test, then flipping `REMEDY_MODE`, is the actual remaining
   work.
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
archive DB is readable unprivileged~~ — confirmed via the same read; ~~usb_watchdog.sh's fate~~ —
decided, retiring (ops#233, MARVIN-DEC-0100), see "What's settled"; ~~REMEDY_MODE grant question~~
— resolved, grant already exists (MARVIN-DEC-0099), only the live-exercise step remains (job 2);
~~Campaign D pre-launch checklist~~ — done, armed on marvin, see "What's settled."

### Current state (S111 open)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` (a restart IS a full recreate) — two-tenant box (`t-hlf` / `weather-hlf.slice`, ops#234, checked no-impact at S109, not re-checked this session) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, **gain 372 live — campaign C closed, verdict DECIDED (DEC-0125): 372 holds. Campaign D ARMED on marvin, self-launches 21:00 ET tonight (DEC-0126)** |
| Alerting | `weewx_monitor.py` (`REMEDY_MODE=none`) live. `weewx-rx-experiment.timer` fired cleanly all night (no gaps, no failed runs) — now a documented no-op against the stood-down empty `SCHEDULE=`. `usb_watchdog.sh` retiring permanently, not porting (ops#233, MARVIN-DEC-0100) |
| `marvinctl` | Tier-1 reads proven (needs `--tenant weewx`). **`exec-ro` self-service DB read CONFIRMED WORKING (S111)** — stdin-pipe fix verified live against the real archive DB. `restart_unit`'s grant CONFIRMED already present (MARVIN-DEC-0099), live restart itself not yet exercised (job 1) |
| Campaign C | **CLOSED** — ran 2026-08-30T21:24 → 2026-08-31T11:00 ET clean, no aborts, self-terminated on schedule. **Adoption verdict DECIDED (DEC-0125): 496 does not clear the bar, 372 holds** |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, unchanged) — unrotated-log and `t-hlf`-tenant risks checked clear at S109, not re-verified this session |
| Trackers | ops#235 fixed, confirmed working (not closed — that's the ops repo's own call) · ops#233 mostly resolved (grant confirmed, watchdog retiring — deploy + live-restart-exercise + verify-and-close still owed) · #216/#214/#110 open · repo #274/#253 open |


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
not clear the adoption bar at marvin, gain holds at 372 (DEC-0125). Caught and fixed this file
carrying two stale ops#233 claims (the restart grant already exists, MARVIN-DEC-0099; usb_watchdog.sh
is retiring, MARVIN-DEC-0100 — both had been corrected upstream but never landed here). Designed and
shipped Campaign D (DEC-0126): a marvin-site gain pilot re-running the arm-selection step Foundation's
pilot did, adding 207, launching tonight 21:00 ET — `SCHEDULE=` populated, `arm_cmd()`/`LEGENDS`/tests
all updated, `_require_campaign_b()`'s gate corrected in the process (was over-broad, would have
misfired against campaign D's pilot-only shape). BOOT/DECISIONS/CHANGELOG/ROADMAP/BACKLOG/CONSTANTS
all reconciled. Green gate clean: ruff clean, 465 passed / 9 skipped, mypy clean (66 files), secret
gate clean over the whole tracked tree. **Then deployed and armed Campaign D live on marvin**
(owner-authorized, via the marvin-admin token path each step): `rx_experiment.sh` shipped and
hash-verified, Campaign C's stale baseline archived to `.campaignC`, `install` succeeded
(`PREFLIGHT OK`, fresh baseline snapshotted, state armed), `logs/campaign.inhibit` set, monitor
confirmed healthy — no further action needed for tonight's 21:00 ET launch beyond the owner's own
hands-off-guest declaration. Also found and reverted a wrong turn: `marvinctl pull`-based deploy for
weewx was attempted (git_branch=dev added to marvin's tenant manifest) before finding MARVIN-DEC-0079,
which already tried and rejected that exact design for this tenant — weewx's marvin deploy is
deliberately flat/scp, not git, because the on-disk layout doesn't match this repo's directory
structure. Reverted before committing; no trace left in either repo._
