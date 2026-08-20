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

## ▶ Resume here (S97 → S98)

### What's settled (do not re-derive)

**The S91 audit's whole 8-issue sequence (#219–226) is CLOSED — tracking issue #227 closed with
it.** #225 and #226 (this session) were the last two. Nothing left to pick up from that audit.

**`ops/nas_build.py` — weewx's NAS-LEASE holder client — is built, tested, and verified live
against the real NAS (DEC-0108).** Generic lease-wrapper (`--job <name> -- <command>`); 14 local
tests against a real `flock()`, plus one real dry-run against the actual shared `LEASE_DIR` this
session — clean `acquired`/`released` pair, no stray lease file left behind. **Not built on
purpose:** the observer/downshift side — no live lever to act on a "held" verdict yet. **Still
waits for the ~08-23 event itself:** the real build's measured duration (floor/TTL ship
provisional at 600s/3600s, re-pin same day) and the adopting DEC (locks §5 for every tenant, takes
the next free number that day — DEC-0109+, since DEC-0108 is used).

**`INTERFACES.md` now actually documents DEC-0053's two open findings — ROADMAP had been
overclaiming this since S48.** §2 carries the missing-station-identity gap (Finding 2, the
series-fork trap) and a pointer to Finding 3 (SQLite's own missing correction flag, which stays in
`DATA_ERRATA.md` on purpose). Do not re-open either without new reason — DEC-0053 already declined
Finding 3's schema change deliberately.

### ▶▶ S98 JOB LIST

1. Confirm steady state is exactly `dev` + `main`, no stray `s97-*` branch (checked clean at S97
   close). Nothing else carries over from S97 — all five PRs merged, both trackers touched (#225,
   #227) closed with explanatory comments.
2. **Daily square watch** (~5 min): `ops/soak_check.sh` + a direct `rx_experiment.state` read.
   **Campaign B ENDS 08-23T00:05 — very imminent now.** Interim readout at S97 (22/32 blocks, via
   `ops/campaign_analyze.py --since <live attempt's epoch>` — the raw log still pools 6 aborted
   attempts back to 08-11, the tool's own warning catches it): gain 496 leads 372 by a margin past
   DEC-0059's 2.0-pt adoption bar at **both** ex levels tested; the ex axis itself is a wash. **Not
   a verdict** — square isn't done, don't read partial results, DEC-0102's overnight-iowait confound
   is still open. Rotation-artifact WARNs after midnight are #252; `stdout is chatty` is #253,
   permanent until the next container recreate.
3. **★ The ~08-23 v2.0.14 build is still a THREE-purpose event.** The holder wrapper is now ready
   (job above) — this reduces to: run `ops/nas_build.py --job nas-image-build -- docker build ...`
   for the actual build, measure its real duration, re-pin `RENEWAL_FLOOR_S`/`TTL_S` in that file
   against it, and write the adopting DEC same day. Carries **#224** into prod (baked in the image).
   Optional call unchanged: mounting `LEASE_DIR` read-only only buys the InfluxDB `post_interval`
   yield lever; skipping costs adoption nothing.
4. **P0.5 — Keep-a-Changelog headings + DECISIONS entry-skeleton convergence, owner-requested next
   round.** Proposed S25 (~72 sessions ago), never picked up. Needs a discovery pass first — check
   what S25 actually proposed (session transcript / `DECISIONS-FULL.md` context) before scoping any
   change; nothing concrete queued yet.
5. **Watch for HLF's ~08-23 floor re-measure.** Their blend-refresh ran 88 min → 155m31s → 275m33s
   (ratios 1.767, 1.772 — read as compounding steps across their DEC-0173/0178 landings, not
   settling). **Their 8h TTL goes out of spec the moment they declare an honest floor** (3×275min =
   13.8h) — unresolved, their thread to close.
6. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Revisit once the square closes **and** the gated queue clears.
7. **[ops#173]** — left open on purpose for the automated sweep to close. Nothing to do unless it
   re-flags.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173

### Current state (S97 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; unchanged this session |
| Campaign B | **Live.** Square through **08-23T00:05**, imminent. Interim S97 readout: see job 2. Soak at S97: **17 pass / 2 warn / 0 fail** — both warns known (#253 chatty stdout; USB hedge 6/7, expected during RF-dead per S73) |
| Restart rate | DEC-0106 baseline unchanged: 4/day during a campaign, 0/day between |
| `dev` beyond prod | Everything for v2.0.14 **plus S97's 5 merged PRs** (#258–262: #226, DEC-0108, #225, INTERFACES.md ×2) |
| S91 audit | **CLOSED** — #219–227 all closed, nothing left |
| NAS-LEASE | Holder client built + verified live (DEC-0108); adopting DEC still waits for ~08-23 |
| Trackers | #233 open · #172/#144 open until v2.0.14 · #204 open · **#227 CLOSED** (was open) · ops#184 open on purpose (HLF redirect) |
| Cross-repo (S97) | coffee-radar (`coffeeradar-28`) confirmed the ~08-23 timeline mid-session; told them the holder client is verified, not just designed. A secret-read-guard false-positive gotcha flagged to ops via `spawn_task` |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven
   (thread blocking on the bind-mounted log volume leads, DEC-0067/0068); evening 18:00–21:00 carries
   the signal (DEC-0094). Untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0097 adds 00:00–04:00
   clustering; DEC-0102 the 11.80x iowait confound, which does **not** close it. Next real step is
   multi-night minute-level correlation, not a re-run. Untouched this session.
3. **ERR-0005** — largely explained by DEC-0081; its 21-stall episode remains the largest on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Model tier

Ran on Sonnet 5 throughout S97, confirmed directly (not inferred) — nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-20 (S97 close). Green gate: ruff clean, **386/386**, mypy clean (62 files),
secret gate clean **and positive-controlled** (planted a fake key mid-session, confirmed the catch,
restored from a pre-mutation backup rather than `git checkout` since the index held the payload).
Shipped: **S91 audit fully closed** (#225/#226, PRs #258/#260) · **DEC-0108** NAS-LEASE holder
client, built and verified live on the real NAS · **INTERFACES.md hardened** — both DEC-0053
findings actually documented (PRs #261/#262), correcting ROADMAP's own overclaim. **Five PRs merged
(#258–262)**, steady state verified after each. Full narrative in `CHANGELOG.md`._
