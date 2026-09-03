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

## ▶ Resume here (S117 → S118)

### What's settled (do not re-derive)

**The ~25% "loss" is solved, fixed, AND deployed (DEC-0134 → DEC-0135 → DEC-0136).** The Go
demodulator discarded the ISS's byte-identical re-sends without hopping, so the pending timer booked
each as `packet missed`. `v2.0.15` shipped 2026-09-03 07:17:53 EDT (16m09s outage). Validation met
every pre-registered number: `missed` **81 → 0**, `repeat` 0 → 79, `duplicate` 89 → 6.
**Confirmed on production data**, not just a capture: duplicate frames/period **6.23 → 0.57** with
repeat frames at **5.81**, population conserved — 91% of what was called a duplicate was a real
re-send, and 5.81/21.33 slots = **27.2% of transmissions**, matching DEC-0134's ~27%.
**It unbiased a statistic; it improved nothing.** The data was always correct. Gain holds at 372
(owner-ratified 09-02). Campaigns A–D stay *untested* and are **not** re-run.

**Three denominators measure three different things (DEC-0136) — don't conflate them.**
`hops = accepted + missed + init` (read from the Go source), so `rxCheckPercent` asks "of slots the
receiver tracked, how many decoded". Slot arithmetic asks "of transmissions the ISS made, how many
did we take" — and over the steady-state window (excluding **128 s** of cold-start acquisition)
that is **~100%**. The monitor's `WINDOW` asks a third question entirely.

**The monitor's thresholds do NOT go stale — measured, reversing the old assumption.** 73.2% before
vs 75.5% after; a real jump would read ~19.7/21. `len(set(epochs))` already counts hop packets and
saturates, so the metric is **insensitive** to this fix. `WU_RF_MIN_PCT = 60` stays valid. Only
`rxCheckPercent` consumers need re-keying (dashboard, via ops#256). `DISC-0001` carries the boundary
timestamp and the corrected consumer list.

**Also settled:** a `repeat` falls through to the normal path and emits a `msg.ID=` line, so
"decoded" **includes** repeats — 274 accepted, 195 unique. `REMEDY_MODE=restart_unit` is armed
(07:58:59) and the stale `campaign.inhibit` that would have made it a silent no-op is gone.

**PR #310 merged (S117's closeout, incl. the ops#216 job filing).** ops#233 (PWS alerting rebuild)
**closed** — ops demonstrated both asks live during today's outage (`ALERT: … down 16min`,
`INPUT RECOVERED`); the one remaining piece (log `remedy_action()` at startup) is job 3 below.
ops#257 narrowed: limb 3 is now just "no ad-hoc read, scheduled read only goes to email" (job 3
closes it); limb 2 (`EnvironmentFile` with `IMAGE=`) is blocked on marvin recording its own
OPS-DEC-0159-class reading first — don't improvise past that.

**Real loss that remains:** ~2 pts of channels-46–48 RFI (DEC-0133) and RF-dead runs ≥10
(blocker 2) — now measurable for the first time against a flat baseline. Raw captures: local
`ARCHIVE/s115-capture/`.

### ▶▶ S118 JOB LIST

**Live, in order:**
1. **Post-fix baseline watch** — the point of the whole exercise. With pseudo-loss gone, blocker 2
   (RF-dead episodes) stands out for the first time. Let it accumulate, then characterize. No
   apparatus needed; observation only.
2. **`v2.0.15` promotion to `main` + Docker Hub** — prod has proven out; per DEC-0078 the Hub push
   follows prod proof. Tag a new `prod-baseline-YYYYMMDD`. Hub is still at `:v2.0.13`.
3. **Make the monitor say what it will actually do (DEC-0074's own lesson, small repo change):**
   (a) log `remedy_action()` at startup — today the armed state cannot be confirmed short of a real
   fault; (b) `log()` the reception summary it already computes and only emails, which closes
   ops#257's observability limb cheaply.
4. **ops#257 limb 2 — `EnvironmentFile` with `IMAGE=`** so a cutover stops needing an owner-run
   `sed` on a root-owned unit. Blocked on marvin recording an OPS-DEC-0159-class reading first: it
   hands a tenant control over what root launches. Don't improvise it.
5. **Retire the stale campaign residue** — `weewx-rx-experiment.timer` is still armed against a
   campaign that ended 09-01 (self-service: `marvinctl disable --now`), and
   `ops/weewx-monitor.service:84` documents a `campaign.inhibit` lifecycle **that no code
   implements**. Fix the comment or implement the lifecycle; don't leave both.
6. **Fix `ExecStop=docker stop` in `weewx.service`** — contradicts DEC-0008 (`docker kill`, never
   `docker stop`), baked in at the DEC-0118 cutover. Needs the same root-edit path as job 4.
7. **Document the DVB blacklist step — a public first-run failure we still don't mention (ops#216
   Finding 1).** On vanilla Debian/Ubuntu the kernel auto-loads `dvb_usb_rtl28xxu` and claims the
   RTL2832U, after which `rtl_sdr` cannot open it. Grepped `origin/dev` at S117:
   `blacklist|dvb_usb|rtl28xxu|modprobe` → **0 hits**, positive-controlled (`RTL-SDR` → 48,
   `rtl_test` → 14). Never needed here because DSM's kernel ships no DVB modules — but this is a
   **public, published** extension, so every Debian/Ubuntu installer hits it and our docs are
   silent. README/install docs. ops#216 carries the finding; this line is why it isn't invisible.
8. **Upstream issue/PR to `lheijst/rtldavis`** — the patch header is already most of the text, and
   the deploy now gives it production evidence. Draft in `docs/upstream/` (gitignored), owner tone
   review, **never posted without a go**.
9. **Audit Phase 2, session A (mechanical, Sonnet):** version/doc sync per the BACKLOG item.
10. **Audit Phase 2, session B (judgment, Opus):** runtime-emitted internal IDs, driver docstrings,
    stale test refs, the unfailable assertion (`test_input_staleness.py:195`), `ops/` banners.
11. **Audit Phase 2, session C (design, owner + Opus):** public-surface reorg. Needs DECs.
12. **Port `campaign_analyze.py` to marvin** (ops#250) — low priority; campaigns are over.
13. **Durable logrotate fix for marvin** — `logs/` keeps only two rotated days.

**Carried forward, untouched:** NAS-LEASE cross-host wiring (low) · `CONSTANTS.md` infra re-verify ·
ops CONSTANTS §5 register row check (`ef8e9af8`) · GitHub Support purge ticket (verify an old SHA
404s, then update the gitignored local-infra doc's PENDING line).

### Current state (S117 close)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` — two-tenant box |
| Prod | **`v2.0.15`** (was v2.0.14), driver ws.5 + dupgate, weewx 5.5.0, gain 372. Deployed 09-03 |
| Docker Hub | still `:v2.0.13` — v2.0.15's push is job 2 |
| Alerting | monitor live, **`REMEDY_MODE=restart_unit` armed**; its thresholds are correct as-is |
| Campaigns | none, and none needed. A–D untested, not re-run |
| Git | PR #308, #309, #310 merged (S117 closeout landed) |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, unchanged) |
| Trackers | ops#256 · #257 (2 limbs left, #3 narrowed) · #250 · #216 · #110 open · repo #274, #253 open. ops#233 closed |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open) — now the largest *real*
   loss mechanism, and **measurable for the first time** post-DEC-0136. Job 1.
3. **ERR-0005** — unchanged.
4. **6-hourly reception-summary email broken** — Gmail 535, needs the owner's Google account.
5. ~~The ~25% ceiling~~ — **RESOLVED, FIXED, and DEPLOYED (DEC-0134/0135/0136).**

## Model tier

S117 ran on **Opus** (owner's call) — a prod deploy with an outage window. **S118's job 1 is
observation and job 2 is a mechanical release: Sonnet is the right floor**; escalate only if job 3
or 4's design questions are taken up. Desktop switches persist (OPS-DEC-0036/0062): state the
running model in the first reply.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). **New traps are appended THERE.**

_Last updated: 2026-09-03 (S117 close, pointer synced post-merge). Session summary: deployed
DEC-0135 and confirmed it on production data. The build path had no `BUILD-EXIT` marker (that
belongs to `ops/nas_build.py`), so the artifact was proven directly instead — `exec-ro rtldavis -h`
printing `-dupwindow`, at zero outage, before prod went down. Four self-service gaps surfaced by
doing the deploy: no tree transport, no image-tag control, no config write, no ad-hoc archive read;
the first two each cost an owner-run step. Three positions were reversed during the session, each
time on measurement rather than argument — that the monitor's thresholds go stale (they don't),
that the fix was unconfirmed in production (our own INFO counters confirm it), and that the slot
arithmetic showed 85.6% loss (it was cold-start acquisition). Cross-repo dialog with ops caught
three stale claims in both directions before any of them was acted on. Gate: ruff clean, 466
passed / 17 skipped, mypy clean (67 files). Docs-only in this repo — no production code changed.
Pointer-sync addendum: PR #310 merged (S117's own closeout commit) and ops#233 closed on ops's
recommendation, both confirmed via `--json state,mergedAt` rather than command exit text._
