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

## ▶ Resume here (S116 → S117)

### What's settled (do not re-derive)

**The ~25% "loss" is solved AND fixed (DEC-0134 → DEC-0135).** The Go demodulator discarded the
ISS's re-sent packets (byte-identical, one loop period later, ~27% of transmissions) without
hopping, so the pending timer booked each as `packet missed`. `rxCheckPercent` under-reported a
~99% link as ~73% since the receiver was built. **S116 built the fix** — a time-gated duplicate
check (`patch/rtldavis-dupgate.patch`, `-dupwindow` 500 ms) plus the driver's `_last_pkt` guard,
which had been **dead code since it was written**, made real so the redundant repeat is suppressed
rather than forwarded. **It unbiases the statistic; it does not improve reception** — the data was
always correct, and `maxmissed` re-inits are unaffected (`chAlarmCnts` max 2 vs a threshold of 51).
**RF tuning stays closed.** Gain holds at 372. **Campaigns A–D are demoted to *untested*** (a flat
result from an insensitive instrument is not evidence of flatness) but are **not re-run**: ~6 pts
of headroom vs a 2.0-pt bar. Chain: DEC-0128 → … → 0134 → **0135**.

**Real loss that remains:** ~2 pts of channels-46–48 RFI (DEC-0133) and RF-dead runs ≥10
(blocker 2). Raw captures: local `ARCHIVE/s115-capture/`.

**PR #308 open** (both S116 commits, CI green, dev-bound) — merge is the owner's / the token path.
History was rewritten 2026-09-01 (DEC-0127); support purge pending (job 3). ops#253 CLOSED.

### ▶▶ S117 JOB LIST

**Live, in order:**
1. **[Opus] DEPLOY DEC-0135 — the whole point of S116.** Merge #308 first. Then: (a) **build on
   marvin** — `marvinctl build <path> -t <tag>` is a tier-2 own-resource verb, **self-service, no
   NAS, no `docker save`/`load`** (answered S116); verify by the explicit `BUILD-EXIT` marker,
   never a pipeline exit (DEC-0078). (b) **Validate standalone BEFORE prod** — 15 min of
   `rtldavis -v`, pre-registered against S115's 295 hops / 214 decoded / 81 missed / 89 duplicate:
   expect `duplicate` **89 → ~9**, `repeat` **~80** appears, `missed` **81 → ~1**, decoded
   **214 → ~294**. (c) Deploy = a real release: **the driver AND the Go binary are both BAKED**
   (DEC-0031), so one image cut carries both; pair with job 2 and the v2.0.14 `main` promotion.
   (d) Post-deploy, re-key every ~73% baseline — the monitor's thresholds, the dashboard's
   (ops#256, already open), and start the **post-fix baseline watch** (`BACKLOG.md`).
2. **Flip `REMEDY_MODE=none` → `restart_unit`** at the job-1 deploy.
3. **Check the GitHub Support purge ticket** — if purged, verify an old SHA 404s and update the
   gitignored local-infra doc's PENDING line.
4. **Upstream issue/PR to `lheijst/rtldavis`** — the patch header is already most of the text;
   draft in `docs/upstream/` (gitignored), owner tone review, **never posted without a go**.
5. **Port `campaign_analyze.py` to marvin** (ops#250) — low priority; campaigns are over.
6. **Audit Phase 2, session A (mechanical, Sonnet):** version/doc sync per the BACKLOG item.
7. **Audit Phase 2, session B (judgment, Opus):** runtime-emitted internal IDs, driver docstrings,
   stale test refs, the unfailable assertion (`test_input_staleness.py:195`), `ops/` banners.
8. **Audit Phase 2, session C (design, owner + Opus):** public-surface reorg. Needs DECs.
9. **Durable logrotate fix for marvin** — `logs/` keeps only two rotated days.

**Carried forward, untouched:** NAS-LEASE cross-host wiring (low) · `CONSTANTS.md` infra re-verify ·
ops CONSTANTS §5 register row check (`ef8e9af8`) · ops#241 BOOT-over-cap.

### Current state (S116 close)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` — two-tenant box (ops#234) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, gain 372. **Unchanged this session — S116 shipped no deploy** |
| Campaigns | **None, and none needed.** A–D demoted to untested; re-baseline by observation instead |
| Git | **PR #308 open, CI green.** History rewritten 2026-09-01 (DEC-0127) |
| Alerting | the monitor (`REMEDY_MODE=none`) live; its ~73% thresholds go stale **at the job-1 deploy**, not before |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, unchanged) |
| Trackers | ops#256 · #250 · #241 · #233 · #216 · #110 open · repo #274, #253 open |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open) — now the largest *real*
   loss mechanism, and **it becomes measurable for the first time** once job 1 lands: today it hides
   inside ~27% of background pseudo-loss; against a flat ~99% baseline it stands out.
3. **ERR-0005** — unchanged.
4. **6-hourly reception-summary email broken** — Gmail 535, needs the owner's Google account.
5. ~~The ~25% ceiling~~ — **RESOLVED (DEC-0134) and FIXED (DEC-0135); deploy pending, job 1.**

## Model tier

S116 ran on **Opus** (owner's call). **S117 is job 1 — recommend Opus:** the design is locked, but
the session opens a prod outage and its expensive branch is unfamiliar debugging with the receiver
down. Desktop switches persist (OPS-DEC-0036/0062): state the running model in the first reply.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1 — now includes "a `packet missed` line is a claim") · any PR/merge
sequence or handoff write (§2) · any NAS or campaign task (§3) · judging a component live, dead,
or shipped (§4). **New traps are appended THERE.**

_Last updated: 2026-09-02 (S116). Session summary: designed and built DEC-0134's fix. First tested
the one alternative DEC-0134 had not ruled out — a stale buffer replaying a decode would have made
the miss booking honest — and 80 of 80 long-gap duplicates carry their own correlation magnitude and
symbol vector, so they are fresh receptions, not replays. The Go side is a tracked patch applied in
the build (not a fork); the driver side turned out to be a no-op as scoped, because its duplicate
guard has been dead code since it was written, which made the real question emit-vs-suppress. The
honest headline is that this unbiases a statistic and improves nothing: the data was always correct.
The tripwire pass then demoted campaigns A–D from settled-negative to untested — a flat result from
an insensitive instrument is not evidence of flatness — and closed a ROADMAP item open since S56 on
a false premise. Two repo lessons bit again in the act of applying them: the first test draft
asserted against a copy of the code rather than the code, and a piped secret-gate run reported exit
0 while the script exited 1. Gate: ruff clean, 466 passed / 17 skipped, mypy clean (67 files),
secret gate exit 0 + 54/54 positive control; the Go patch compiles and the new tests are
mutation-tested 5/5._
