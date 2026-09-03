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

**RF TUNING IS OVER — every axis is measured flat (DEC-0128, DEC-0129). Do not re-sweep.** Gain
holds at 372; flat axes are **gain · receive window (`-ex`) · physical siting · frequency offset**.
The ~25% loss is deterministic, structural, ours (the owner's Davis console at comparable distance
drops single digits). Chain of evidence: DEC-0128 → 0129 → 0130 → 0131 → 0132 → **0133 (S115)**.

**The channels-46–48 cluster is EXPLAINED and DEMOTED (DEC-0133).** With the demodulator's
±134 kHz passband applied, S114's capture picks out exactly 46/47/48 — an FHSS neighbour on a
~400 kHz channel comb — but the whole cluster is ~2 pts of the ceiling. **The ceiling is
frequency-independent**: the other 48 channels sit flat at 69.7 ± 10 misses.

**History was rewritten and force-pushed 2026-09-01 (DEC-0127) — old clones must re-clone.**
Support purge ticket still pending (job 3). `SCHEDULE=` stood down (DEC-0096), marvin's copy inert.
ops#253 CLOSED (S114). No Class C write owed.

### S115 — DEC-0133: the bulk of the loss is a fixed ~7.75 s wall-clock modulation

The 3,047 miss timestamps from the S113/S114 debug window are periodic in **wall-clock time**, not
hop count: Rayleigh peak at **7.7495 s (z = 97)** vs z = 4 for the hop-locked 11/4-hop alternative;
fold mod 11 hops flat; miss-to-miss gaps peak at 3 hops; autocorrelation undecayed to 60 hops;
consecutive misses anticorrelated. Smooth modulation (miss probability ~0.17 → 0.5 across the
cycle), phase stable to ~0.05% with slow wander (mechanical/RC-grade, not crystal). Aliases
(~4.41 s, ~2.06 s) indistinguishable on the hop grid. Isolated single misses carry **21.9 of the
window's 32.2 pts**; pairs 5.3; runs ≥10 (re-inits, blocker 2's class) 4.3. **Ruled out** (read-only,
this session): host stalls — cgroup cpu/mem/io pressure zero on container and slice, no throttling,
and **72.83% on Foundation vs 72.82% on marvin**; in-band RF in 924.5–927.5; every hop-locked
mechanism; static offset. **Survivors:** what moved intact between hosts — dongle + its 1 KB
single-buffer USB geometry (`main.go:262`), Go pipeline, antenna/feedline, the ISS, the outdoor
path — and the owner confirmed the console receives this ISS at this property, so **ISS and
outdoor path are exonerated: the periodic loss is in our receiver chain.**

**Data loss:** the Sep 1 debug window's received-packet lines rotated away unharvested; only the
`missed` grep survives in S114's session scratch (`misslines.txt`, 3,047 lines). GOTCHAS §3.

### ▶▶ S116 JOB LIST

**Live, in order:**
1. ~~Ask the owner whether the single-digit console receives this ISS~~ — **ANSWERED (S115): yes,
   same ISS, same property.** ISS and outdoor path exonerated; the periodic loss is in OUR chain
   (antenna/feedline, dongle, USB geometry, Go pipeline).
2. **Item 8 — the designed capture (`BACKLOG.md` ceiling item; ~25–30 min dongle-exclusive outage,
   S114's self-service stop/exec-ro/start path, all tools in the prod image):** (1) `rtl_test
   -s 268800 -b 1024` ~5 min locally timestamped — periodic "lost bytes" implicates USB/dongle;
   (2) standalone `rtldavis -tr 16 -gain 372 -v` ~15 min — `lastFreqError` per packet (a 7.75 s
   oscillation = frequency wobble) plus the first received+missed sequence at µs; **harvest it
   whole**; (3) `rtl_power -f 902M:928M:10k -g 37.2 -i 1` ~5 min — periodic in-band level, and
   whether the 400 kHz comb spans the band. Judgment work: analysis on Fable/Opus. `exec-ro` takes
   one whitespace-free token per argument — three invocations, no `sh -c`.
3. **Check the GitHub Support purge ticket** — if purged, verify an old SHA 404s, update
   `LOCAL_INFRA.md`'s PENDING line and drop this job.
4. **Port `campaign_analyze.py` to marvin** (ops#250) — its `fetch()` still ssh's to the NAS.
5. **Audit Phase 2, session A (mechanical, Sonnet):** version/doc sync per the BACKLOG item —
   README + Docker Hub banner, driver/influx versions, weewx.conf.example, ARCHITECTURE stamps,
   broken commands, CONTRIBUTING CI wording, tag + release v2.0.12–14, BIAS_TEE docs.
6. **Audit Phase 2, session B (judgment, Opus):** scrub internal IDs from runtime output (monitor
   emails, log lines), driver docstring upstream defaults, stale test line refs, the unfailable
   assertion (`test_input_staleness.py:195`), internal-vs-user banners in `ops/`.
7. **Audit Phase 2, session C (design, owner + Opus/Fable):** public-surface reorg — root
   governance files, docs/ index, PR-title convention, tier-label rename, GitHub topics/templates,
   `DECISIONS-FULL.md` over GitHub's render limit, moving the governance corpus private. Needs DECs.
8. **Flip `REMEDY_MODE=none` → `restart_unit`** — grant present (MARVIN-DEC-0099); the live-restart
   exercise belongs at a real deploy.
9. **Durable logrotate fix for marvin** — still unaddressed; `logs/` holds only 08-28/08-29 rotated
   copies plus today's file, so retention is shorter than "daily rotation, working" implies.

**Carried forward, untouched:** `main` promotion for v2.0.14 (DEC-0114) · DEC-0117 control-file
conversion + can marvin build natively · NAS-LEASE cross-host wiring (low) · `CONSTANTS.md` infra
re-verify · ops CONSTANTS §5 register row check (`ef8e9af8`) · ops#241 BOOT-over-cap (re-measure
with ops' `checks/tier-sweep.sh`). **ROADMAP tripwire fires at S116** — run the full reconciliation.

### Current state (S115 close)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` — two-tenant box (`t-hlf`, ops#234) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, **gain 372 measured-and-unbeaten (DEC-0128)**. Untouched this session |
| Campaigns | **None running, none planned.** `SCHEDULE=` stood down |
| Git | History rewritten 2026-09-01 (DEC-0127). Support purge pending (job 3) |
| Alerting | `weewx_monitor.py` (`REMEDY_MODE=none`) live; `weewx-rx-experiment.timer` ticking but a confirmed no-op |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, unchanged) |
| Trackers | ops#250 (port) · ops#241 (BOOT cap) · ops#233 (alerting rebuild) · #216/#110 open · repo #274, #253 open |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0133 sized this class
   at ~4.3 pts of the debug window (runs ≥10 misses, incl. four `maxmissed` re-inits).
3. **ERR-0005** — unchanged.
4. ~~`ppm`/`fc` unmeasured~~ — **CLOSED (DEC-0129).**
5. **6-hourly reception-summary email broken** — Gmail 535, needs the owner's Google account.
6. **The ~25% reception ceiling is unexplained — REFRAMED (DEC-0133).** Not "which frequency": the
   loss is flat across all 51 channels and periodic at ~7.75 s wall-clock (or an alias). Question
   now: **what oscillates on that cycle in the chain the ISS, antenna, dongle and demodulator
   share?** Next: S116 jobs 1–2.
7. ~~`max_count` is not the constant it should be~~ — **CLOSED (DEC-0130):** transmitter ID 4.

## Model tier

S115 ran on **Fable** (owner's call, session-only via the desktop picker) — appropriate: open-ended
hypothesis-forming over an ambiguous result, and it found a structure nobody had asked about. S116
job 2's analysis is the same class; jobs 3–5 are Sonnet-able. Desktop switches persist
(OPS-DEC-0036/0062): check the running model in the first reply.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). **New traps are appended THERE.**

_Last updated: 2026-09-02 (S115). Session summary: did the "free" cross-reference DEC-0132 left on
the table and it inverted the reading — the RFI explains channels 46–48 exactly once the receiver's
passband is applied, and that explanation is worth ~2 pts, not 25. Then looked at the one thing
nobody had: the miss timestamps themselves. They are periodic in wall-clock time at ~7.75 s (or an
alias), not locked to the hop clock, smooth rather than blanking, and carry two-thirds of the loss.
Read-only host checks cleared marvin (pressure zero, and the loss matched Foundation's to 0.01 pt),
which narrows the field to what moved intact between hosts. The received-packet half of the debug
log had already rotated away, so the next capture is designed to be harvested whole. Gate: ruff
clean, 457 passed / 17 skipped, mypy clean (66 files)._
