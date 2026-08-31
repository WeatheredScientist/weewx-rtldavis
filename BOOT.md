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

## ▶ Resume here (S108 → S109)

### What's settled (do not re-derive)

**Campaign C is LIVE, launched tonight (2026-08-30 20:00 ET), not tomorrow.** Owner call, S108
(PR #291): the original reason to wait — letting the freshly-deployed monitor prove itself across a
log-rotation boundary before trusting it as the abort tripwire — turned out to be moot, because
**marvin has no logrotate configured for `weewx.log` at all** (confirmed directly on the box; see the
new open item below). `SCHEDULE=` shifted by a pure −1 calendar day; same 10 blocks, same clock times
(20:00/21:30/23:00/00:30/02:00/03:30/05:00/06:30/08:00/09:30/11:00), same `A B B A B A A B A B` order,
so DEC-0121's notch-balance is unchanged. As of S109 session start (2026-08-30 ~22:33 ET), confirmed
live and healthy via the marvin session: arm **B**, `weewx.service` running clean since 22:18:46 with
no restarts since, self-advancing correctly.

**The scheduler gap that would have stalled the campaign is fixed and deployed (S108, PR #292).**
DEC-0118's move to marvin never carried over the DSM cron that drove `ops/rx_experiment.sh tick`/
`guard` every 5 min — block 1 was launched by hand and then sat un-advanced, with `guard` (the
campaign's only abort-on-bad-reception check) never running at all. Discovered live, mid-campaign.
New `ops/weewx-rx-experiment.service` + `.timer` (root-owned, mirrors what the Foundation cron did)
shipped from this repo and — confirmed via marvin session — **installed and firing on marvin since
22:18:16 ET**, every 5 min; its first fire self-healed the overdue block 1→2 swap. `guard` has run
every cycle since 22:18, so abort coverage was live well before the campaign's midpoint.

**Unrotated `weewx.log` risk — checked and cleared, not a live danger tonight.** Flagged by ops
(eaglehunt-ops#209 thread): the file has grown unrotated since the 08-29 cutover. Code-level check
(this session) plus marvin-side confirmation (22:44 ET): 3,894,420 bytes (~3.7 MiB) after ~22.75h,
~171k bytes/hr, ~2.2 MiB more expected over the campaign's remaining ~13h — against 1.1 TiB free on
`/srv` (1% used), zero disk-fill risk at any plausible multiple. `weewx_monitor.py`'s `get_new_lines()`
(byte-offset seek, no whole-file re-scan, DEC-0024) shows steady 6–19 new-lines/poll with no stalls or
catch-up spikes — behavior consistent with correct offset tracking, not drift. **Not urgent, but the
underlying gap is real:** marvin still has no logrotate stanza at all — a permanent one is owed as its
own job (still not numbered below; add at next full ROADMAP pass) so this doesn't recur on the next
long campaign or in general operation.

**⚠ New open item: the 6-hourly reception-summary email is broken, needs the owner.** `--test-alert`
fails SMTP auth (535 "Bad Credentials") from Gmail. Ruled out on every axis checked on marvin's side:
`GMAIL_PASS` is byte-identical to the NAS's copy (sha256 match), no embedded spaces. Whatever's wrong
is on Google's end (credential validity or a sign-in block) — invisible from either box, needs the
owner's own Google account access. Tonight's 00:00 summary likely won't send. Full trail: marvin's
`DECISIONS.md`, MARVIN-DEC-0093/-0095/-0097.

**marvin's new second tenant (`t-hlf`, ops#234) — checked, no impact on campaign C tonight.**
`weather-hlf.slice` is loaded but **inactive/dead**: zero cgroup accounting, HLF has no live
units/containers on marvin yet. `weather.slice` itself: ~128.5 MiB memory.current (basically just
`weewx.service`), no `memory.max` cap, zero pressure/OOM signals. HLF drawing nothing means no change
to what campaign C or `weewx.service` can use. **Re-check once HLF actually deploys something under
`weather-hlf.slice`** — not tonight's concern, but don't assume this stays true indefinitely.

**Today's 4-hour gain campaign was refused on this repo's own power math, and the owner agreed.**
DEC-0059 measured 24 h/arm resolving 1.1 pts; 4 h splits to ~2 h/arm → MDE **~3.8 pts against a
2.0-pt effect** (~3.6× too short; confirmed two independent ways). It would have returned "no
difference" nearly regardless of truth. The live 15 h run (above) is that properly-powered run — do
not let a short run be re-proposed once this one closes.

**Prod is running gain 372 while DEC-0115 adopted 496 — campaign C is the measurement that settles
it.** The 08-29 migration incident set 372 without a controlled comparison and the aborted campaign's
exit trap codified it as the restore value. Tonight's run is the re-sweep; do not treat 372 or 496 as
the answer until the campaign's own readout says so.

**marvin is clear for RF work.** Its GPU passthrough bind completed and is final since 08-29; no
hardware work scheduled. Caveat that matters for any measurement: the 2070 now lives in the win11
guest **full-time, driver-active even at idle** — **owner's hands-off-the-guest declaration for
tonight's full campaign window is confirmed** (S108, PR #290; logged marvin-side as MARVIN-DEC-0088),
so this is controlled for the live run, not an open variable.

### ▶▶ S109 JOB LIST

**Live, in order:**
1. ✅ **Monitor deployed and running (marvin S16, MARVIN-DEC-0079).** `weewx_monitor.py` on marvin is
   sha `a6065f5f...`, 66183 bytes — byte-identical to `origin/dev`'s current tip, no drift. Installed
   and live: `weather.slice`, `REMEDY_MODE=none`, log actively growing.
2. ✅ **Campaign C launched and self-advancing (S108/S109).** Live now — see "What's settled" above
   for full status. Unrotated-log risk and the new `t-hlf` tenant are both checked and cleared
   (above) — no action needed tonight. Remaining sub-items:
   a. **Let the campaign run to its self-terminator** (2026-08-31T11:00 → BASELINE) and read the
      result with `ops/campaign_analyze.py` (DEC-0069's only sanctioned readout) once it closes.
      ⚠ Prior to know *before* reading results: **marvin @372 already measures 73.88%**, within ~0.95
      pts of Foundation @496 — 496 repeating its 2.00-pt win here is **not** the safe assumption.
   b. **The Gmail SMTP failure is a separate, owner-side item** (above) — not a campaign blocker, but
      don't let it get silently forgotten once the campaign wraps and attention moves on.
   c. **File a durable logrotate fix for marvin** — the gap itself (not tonight's growth) is still
      unaddressed; not numbered as its own job yet, fold into the next ROADMAP/job-list pass.
3. **Verify the archive DB is readable unprivileged before enabling the reception-summary path.**
   `weewx.sdb` is mode `0500 t-weewx`, written by root in-container. If it is WAL, a `?mode=ro` open
   may fail needing `-shm` write — DEC-0119's bug class. **Unverified; do not assume either way.**
4. **Then** flip `REMEDY_MODE=none` → `restart_unit` — but **not yet, and not via `marvinctl`.**
   Confirmed by a marvin-side session at S107: **no local grant exists today.** The only sudoers
   lines on the box serve the **ssh forced-command** path, and `marvinctl` is the *remote* client —
   a `t-weewx`-uid daemon already on the box has no ssh hop to make and cannot invoke it to escalate
   itself. Manifest scoping (`units=weewx*`) governs what *this session* may ask for over that
   channel; it says nothing about local systemd. **The only path is a narrow marvin-side grant** —
   one sudoers line (`t-weewx` → `/usr/bin/systemctl restart weewx.service`) or a scoped polkit
   rule — which is a marvin-repo change needing owner ratification and its own DEC row. File it when
   the monitor is ready to prove the mechanism, not before. Setting `restart_unit` without the grant
   yields a remedy that fails every time while looking correct (DEC-0061).
   ⚠ *An earlier draft of this line offered "sudoers **or a marvinctl tier-2 verb**". The second was
   wrong and is struck: eaglehunt-ops asserted it from manifest help text without exercising it. Left
   standing it would have sent the next session chasing a route already ruled out — the same
   never-exercised-therefore-never-disproven shape as the defect DEC-0120 fixes.*
   **`REMEDY_MODE=none` permanently is a defensible end state**, not an unfinished job: the remedy's
   entire evidence record is a USB reset aimed at hardware that has since changed boxes.
5. **`usb_watchdog.sh`'s fate** — still simply OFF, still undecided. ops#233's sibling finding.

**Carried forward, untouched:**
6. **`main` promotion for v2.0.14** — deliberately deferred (DEC-0114).
7. **Convert `ops/rx_experiment.sh` to the DEC-0117 control file** — gated on job 8.
8. **DEC-0117 hot swap needs an image rebuild to reach prod** (off by default). Still unverified
   whether marvin can build natively vs. repeating the `docker save`/`load` dance.
9. **Foundation decommission timing** — owner's call, after a week-plus soak.
10. **NAS-LEASE cross-host wiring** — low priority; marvin's `/nas-lease` is a deliberate no-op.
11. **`CONSTANTS.md`'s infra section second pass** — still not re-verified row by row. S107 captured
    the authoritative `docker run` line from `marvinctl unit weewx` if that helps the next pass.
12. **Sanity-check ops' `CONSTANTS.md` §5 register row** for weewx's token (`ef8e9af8`).

**Retired this session (S108/S109):** ~~manual launch + hand-driven tick/guard~~ — superseded by the
`weewx-rx-experiment.timer` systemd unit, installed and firing on marvin; ~~owner hands-off-guest
round-trip~~ — obtained and logged (MARVIN-DEC-0088); ~~"campaign launches 08-31"~~ — shifted to
tonight (08-30), owner call.

### Current state (S109 open)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` (a restart IS a full recreate) — now a **two-tenant box** as of today (`t-hlf` / `weather-hlf.slice`, ops#234, impact on weewx unassessed) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, **gain 372 live, campaign C running to settle 372 vs 496** |
| Alerting | **Deployed and live.** `weewx_monitor.py` (`REMEDY_MODE=none`) + the new `weewx-rx-experiment.timer` both running on marvin. `usb_watchdog.sh` still OFF (job 5, undecided) |
| marvin GPU bind | Complete + final since 08-29; 2070 attached to win11 full-time, driver-active at idle; hands-off declared for tonight's campaign window |
| `marvinctl` | Tier-1 reads proven (needs `--tenant weewx`). No SQL verb — an archive-DB readout needs a marvin-side session |
| Campaign C | **LIVE** — launched 2026-08-30T20:00 ET, arm B confirmed healthy as of ~22:33 ET, self-terminates 2026-08-31T11:00 → BASELINE |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, only unresolved item) — unrotated-log and `t-hlf`-tenant risks checked clear tonight |
| Trackers | ops#233 answered by DEC-0120 (not closed — deploy landed, verify-and-close still owed) · #216/#214/#110 open · repo #274/#253 open |


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

## Model tier

No `/model` switch this session. Nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-30 (S109, reconciling S108's un-closed-out work). Green gate re-run clean:
ruff clean, 468 passed / 3 skipped, mypy clean (66 files), secret gate clean, shell syntax OK — no
code changed this pass, gate re-verified as part of completing S108's deferred closeout. Shipped in
S108 (not by this session): campaign C's schedule shifted to launch tonight instead of tomorrow
(PR #291); the missing marvin tick/guard scheduler ported as a systemd timer/service (PR #292); the
owner's hands-off-guest declaration for tonight's window closed out (PR #290). This session (S109)
added no code — it re-derived state from git + trackers + the live marvin/ops sessions, confirmed the
campaign is live and healthy, checked and cleared two of three new risks (unrotated log, `t-hlf`
tenant) via the live marvin session, and wrote up S108's two real decisions as DEC-0122/DEC-0123
(`docs/DECISIONS.md` + `-FULL.md`, `CHANGELOG.md`, `docs/ROADMAP.md`'s campaign-C line). Only the
Gmail SMTP failure (blocker 5) remains open, and it needs the owner, not this session._
