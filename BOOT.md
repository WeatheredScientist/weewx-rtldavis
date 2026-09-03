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

## ▶ Resume here (S115 → S116)

### What's settled (do not re-derive)

**THE ~25% "LOSS" IS SOLVED (DEC-0134, S115): there is no RF ceiling.** The Go demodulator's
byte-only duplicate filter discards the ISS's genuine repeat packets (byte-identical, re-sent one
hop later, ~27% of transmissions on a cadence of the ISS's own) and, because the hop handler is
skipped, the pending timer books each one as `packet missed`. Standalone 15-min run of the deployed
binary: 295 hops, 81 misses, **80 preceded by a `duplicate packet` line 0.363 s earlier; real loss
1/295 = 0.3%.** `rtl_test` at the Go geometry: zero lost samples. **`rxCheckPercent` has
under-reported a ~99% link as ~73% since the receiver was built.** Every flat axis (gain 328–496,
`-ex`, siting, offset, frequency, host — 72.83 vs 72.82 is the ISS's repeat fraction measured
twice) and the console's single-digit loss are explained. **RF tuning stays closed** (DEC-0128/0129);
gain holds at 372. Chain: DEC-0128 → 0129 → 0130 → 0131 → 0132 → 0133 → **0134**.

**Real loss that remains, both small:** the ~400 kHz-comb FHSS neighbour on channels 46–48 (~2 pts,
DEC-0133) and the RF-dead runs ≥10 (blocker 2). Raw captures: local `ARCHIVE/s115-capture/`.

**History was rewritten and force-pushed 2026-09-01 (DEC-0127) — old clones must re-clone.**
Support purge ticket pending (job 4). `SCHEDULE=` stood down (DEC-0096). ops#253 CLOSED. **PR #307
open** (this session's closeout, dev-bound) — merge is the owner's / the in-chat token path.

### ▶▶ S116 JOB LIST

**Live, in order:**
1. **[Judgment — Opus/Fable] THE FIX (DEC-0134).** Time-gate the duplicate check in the Go
   demodulator (`main.go` ~393–398, `lastRecMsg`): identical bytes **< 500 ms** after the last
   decode = within-burst double-decode (DEC-0035), drop; **≥ 1 s** = a new transmission, emit and
   hop. Design first (PRINCIPLES §8), DEC row, then: (a) make `rtldavis.py` tolerate byte-identical
   consecutive packets — rain wraparound (DEC-0022) and `log_humidity_raw`'s on-change logic; (b) the
   image must be rebuilt: **DEC-0117's "can marvin build natively?" question is now on the critical
   path** (NAS build + `docker save/load` is the fallback, DEC-0078); (c) deploy to prod = a real
   deploy — pair it with job 8 (`REMEDY_MODE`) and the v2.0.14 `main` promotion; (d) expect
   `rxCheckPercent` to jump to ~99% — every ~73% baseline is stale (`BACKLOG.md`, `docs/ROADMAP.md`,
   monitor thresholds in `weewx_monitor.py`, the dashboard's — dashboard via eaglehunt-ops, DEC-0010).
2. **Upstream issue/PR to `lheijst/rtldavis`** — draft in `docs/upstream/` (gitignored), owner
   tone review, **never posted without a go** (`docs/UPSTREAM-THREADS.md`).
3. **ROADMAP tripwire fires at S116 — full reconciliation**, and it is overdue in substance: P2's
   RF section, every campaign baseline, and `BACKLOG.md`'s "durable RF findings" are now
   "measured the ISS's repeat fraction". Reconcile, don't delete — the negative results stay valid
   as don't-re-sweep evidence.
4. **Check the GitHub Support purge ticket** — if purged, verify an old SHA 404s, update
   `LOCAL_INFRA.md`'s PENDING line and drop this job.
5. **Port `campaign_analyze.py` to marvin** (ops#250) — lower priority now that campaigns are over.
6. **Audit Phase 2, session A (mechanical, Sonnet):** version/doc sync per the BACKLOG item.
7. **Audit Phase 2, session B (judgment, Opus):** runtime-emitted internal IDs, driver docstrings,
   stale test refs, the unfailable assertion (`test_input_staleness.py:195`), `ops/` banners.
8. **Flip `REMEDY_MODE=none` → `restart_unit`** at the job-1 deploy.
9. **Audit Phase 2, session C (design, owner + Opus/Fable):** public-surface reorg. Needs DECs.
10. **Durable logrotate fix for marvin** — `logs/` keeps only two rotated days.

**Carried forward, untouched:** `main` promotion for v2.0.14 (DEC-0114) · NAS-LEASE cross-host
wiring (low) · `CONSTANTS.md` infra re-verify · ops CONSTANTS §5 register row check (`ef8e9af8`) ·
ops#241 BOOT-over-cap (re-measure with ops' `checks/tier-sweep.sh`).

### Current state (S115 close)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` — two-tenant box (`t-hlf`, ops#234) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, gain 372. **Restarted 21:09 ET after the 26.5-min capture outage; verified up** |
| Campaigns | **None, and none needed.** The RF question is closed by DEC-0134 |
| Git | History rewritten 2026-09-01 (DEC-0127). Support purge pending (job 4). **PR #307 open** |
| Alerting | `weewx_monitor.py` (`REMEDY_MODE=none`) live; its reception thresholds assume ~73% — stale after the fix |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, unchanged) |
| Trackers | ops#250 · ops#241 · ops#233 · #216/#110 open · repo #274, #253 open |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). ~4 pts on Sep 1 (runs ≥10,
   incl. four `maxmissed` re-inits) — now the largest *real* loss mechanism.
3. **ERR-0005** — unchanged.
4. ~~`ppm`/`fc` unmeasured~~ — **CLOSED (DEC-0129).**
5. **6-hourly reception-summary email broken** — Gmail 535, needs the owner's Google account.
6. ~~The ~25% reception ceiling is unexplained~~ — **RESOLVED (DEC-0134).** Duplicate filter
   discarding the ISS's repeat packets; real loss 0.3%. **Fix pending: S116 job 1.**
7. ~~`max_count` is not the constant it should be~~ — **CLOSED (DEC-0130):** transmitter ID 4.

## Model tier

S115 ran on **Fable** (owner's call, session-only via the desktop picker). S116 job 1 is design +
a Go change + a deploy plan — Opus or Fable; jobs 4–6 are Sonnet-able. Desktop switches persist
(OPS-DEC-0036/0062): check the running model in the first reply.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1 — now includes "a `packet missed` line is a claim") · any PR/merge
sequence or handoff write (§2) · any NAS or campaign task (§3) · judging a component live, dead,
or shipped (§4). **New traps are appended THERE.**

_Last updated: 2026-09-02 (S115). Session summary: the "free" cross-reference DEC-0132 left on the
table inverted its reading (the RFI explains channels 46–48 once the passband is applied, worth
~2 pts), and the miss timestamps turned out to be periodic in wall-clock time — so a designed
capture ran the same evening: transport clean, the deployed binary standalone reproduced prod's
27.5% "loss" with nothing else in the loop, and its own log said why: 89 duplicate-packet lines,
each the ISS re-sending a byte-identical packet one hop later, each dropped without hopping, each
booked as a miss when the old timer fired. Real loss 1 in 295. Seven DECs of RF work were measuring
the ISS's repeat fraction; the receiver was never the problem, the accounting was. Gate: ruff clean,
457 passed / 17 skipped, mypy clean (66 files), secret gate exit 0 + 54/54 positive control._
