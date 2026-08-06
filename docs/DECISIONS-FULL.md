# Decision Log (FULL) — weewx-rtldavis

**Status:** Source of truth (full bodies) · **Read on demand** (DEC-0030)
**Last updated:** 2026-07-09 (S35 — DEC-0030 docs diet: full bodies moved here verbatim from DECISIONS.md)

This file holds the **complete, append-only bodies** of every decision. The session-start read is
`docs/DECISIONS.md` — a one-row-per-DEC index; grep the DEC id **here** whenever a task touches a
settled decision's actual text (the anti-loophole rule: *"working near it" means read it*).
A decision is never edited in place — it is **superseded** by a later entry that references it.
New decision = append the full body here + add an index row there (DEC-0030).

> **Provenance note:** entries DEC-0001…DEC-0009 are *reconstructed* from project history (the
> pre-governance chat sessions, roughly Apr–Jun 2026); their dates are approximate. DEC-0010 and
> up were made live under governance (S16 onward) and are exact. This log covers the
> **weewx-rtldavis driver/Docker** only; dashboard decisions belong to `eaglehunt-weather-dashboard`'s
> own log (the split itself is DEC-0010 there / DEC-0011 here).

ADR format: ID · Title · Status · Date · (Amended/Supersedes) · body · Rationale.

---

## DEC-0001 — Passive 915 MHz interception via RTL-SDR

**Status:** Accepted · **Date:** ~S1 (2026-04)

Receive the Davis 6263 VP2+ ISS broadcast passively with an RTL-SDR Blog v3 dongle driving the
`rtldavis` decoder, feeding WeeWX — rather than reading through the WeatherLink Console/cloud.

*Rationale:* liberates the data from Davis's ecosystem; the readings become locally owned and
real-time. This is the founding act of the whole project (PRINCIPLES §1).

## DEC-0002 — Ubuntu 26.04 / Python 3.14 multistage Docker build

**Status:** Accepted · **Date:** ~S-early (2026-05, v2.0-ubuntu26)

Build the image as a multistage Ubuntu 26.04 / Python 3.14 build (979 MB → 278 MB), superseding the
original Ubuntu 22 base (v1.0-ubuntu22).

*Rationale:* smaller image, current Python, cleaner build. The multistage builder compiles the
`rtldavis` Go binary and discards build deps from the runtime layer.

## DEC-0003 — Same-repo tags for versioning (Option 2)

**Status:** Accepted · **Date:** ~2026-05-26

Version releases as git tags on this single repo (`v1.0-ubuntu22`, `v2.0-ubuntu26`, `v2.0.1`, …),
paired with Docker Hub image tags — not separate release branches or repos.

*Rationale:* solo project, linear history; tags are the simplest durable version markers.
*Consequence / known gap:* discipline is required to actually push tags — `v2.0.2` was built and
described as a release but **never git-tagged** (caught in the S16 drift audit; see CHANGELOG [S16]).

## DEC-0004 — Volume-mount extensions for hot iteration; bake stable code

**Status:** Accepted · **Date:** ~S-mid (2026-06)

Volume-mount the files under active iteration into the container `:ro` (the driver `rtldavis.py`,
`influx.py`, `loop_json_writer.py`, `ogoxeUploader.py`, `loopdata.py`, `sortedcontainers/`) so a
change is edit + clear-pyc + restart — no image rebuild. Everything else (`dewpoint_service.py`,
`owm.py`, `pressure_service.py`, `wcloud.py`, `windy.py`, `entrypoint.sh`) is baked into the image.

*Rationale:* fast, reversible iteration on the parts that change; stable parts stay immutable in the
image. This is what makes trialing a driver change on prod low-risk (PRINCIPLES §4). *Consequence:*
changing a baked file requires a rebuild; the pyc cache must be cleared after editing a mounted file
(ARCHITECTURE §pyc-gotcha).

## DEC-0005 — Custom loop_json_writer.py; weewx-loopdata rejected

**Status:** Accepted · **Date:** ~S-mid (2026-06)

Feed the dashboard's real-time LOOP data with a custom `loop_json_writer.py` WeeWX `data_service`
that writes fields atomically to a JSON file, rather than adopting the third-party weewx-loopdata
extension.

*Rationale:* weewx-loopdata is heavier than the need; the custom writer is ~80 lines and emits
exactly the loop-JSON contract the dashboard expects (PRINCIPLES §6, INTERFACES). *Known state
(S16):* a `loopdata.py` copy is still volume-mounted and a stale `[LoopData]` config section remains,
but `user.loopdata.LoopData` is in **no** active service list — vestigial; cleanup backlogged
(BACKLOG, ROADMAP). **Cleanup done (S47):** live `weewx.conf`'s `[LoopData]` section removed, the
`loopdata.py` mount dropped from the recreated `weewx-rtldavis-v2` container (verified: 6 mounts,
clean restart, records publishing), and the file renamed aside on the NAS
(`loopdata.py.removed-S47`) rather than deleted outright.

## DEC-0006 — Null-on-rejection filter philosophy

**Status:** Accepted · **Date:** ~S-mid (2026-06)

When a reading is rejected by a QC/consistency filter, set the field to `None` — do not substitute
the last-known value. Implemented in `dewpoint_service.py` (wind delta filter `MAX_WIND_DELTA=75`,
cold-start warmup buffer, calm-air gate).

*Rationale:* an honest null is diagnosable; a stale substitute silently corrupts (PRINCIPLES §2).
This is the template for the pending rain-spike filter (DEC-0021).

## DEC-0007 — Upload services use the WeeWX RESTThread pattern

**Status:** Accepted · **Date:** ~2026-05

Custom uploaders (`owm.py`, `windy.py`, `wcloud.py`, `ogoxeUploader.py`, `influx.py`) subclass the
WeeWX `StdRESTbase` / `RESTThread` pattern for reliable, non-blocking, queue-backed posting.

*Rationale:* RESTThread handles ret/backoff and keeps posting off the main loop thread.
*Consequence (S16):* the GitHub copies of `owm.py`/`windy.py` had **stale duplicate class
definitions** appended (crude `StdService` + raw `threading` versions) that shadowed the clean
RESTThread classes — a latent regression fixed by reconciling to the running versions (CHANGELOG [S16]).

## DEC-0008 — `docker kill`, never `docker stop`

**Status:** Accepted · **Date:** ~S-early (2026-05)

Always restart the container with `docker kill` + `docker start`, never `docker stop`. `docker logs`
always with `--tail N`.

*Rationale:* clean USB device handoff for the SDR dongle; `docker stop`'s graceful path was observed
to leave the dongle in a bad state. `set_gain.sh` codifies this.

## DEC-0009 — Dedicated limited user for the NAS-side monitor

**Status:** Accepted · **Date:** ~2026-06

`weewx_monitor.py` runs NAS-side as a limited user (`weewx-monitor`), with sudo scoped to
`usb_reset.sh` only; the sudoers rule is recreated at boot via Task Scheduler; credentials live in
the gitignored `monitor.env`.

*Rationale:* least privilege for the always-on monitor; it needs only USB reset, not root.

---

## DEC-0010 — Adopt Eagle Hunt nine-file governance model

**Status:** Accepted · **Date:** 2026-07-04 (S16/S17)

Adopt the nine-file documentation governance proven in `eaglehunt-weather-dashboard` (CLAUDE.md +
docs/{CONVENTIONS, PRINCIPLES, DECISIONS, ARCHITECTURE, INTERFACES, ROADMAP, STATUS} + CHANGELOG +
BACKLOG), append-only ADRs with explicit supersession, and the No-Rewrite Rule.

*Rationale:* the tool was published without this rigor; retrofitting now is "never too late." Two
sibling repos under one workflow stay legible. INTERFACES.md replaces the dashboard's DATA-MODEL.md
role — this repo's contract is the loop-JSON + InfluxDB schema.

## DEC-0011 — Branch model: main = production truth, dev = work

**Status:** Accepted · **Date:** 2026-07-04 (S16)

`main` = what is actually running in production, tagged `prod-baseline-YYYYMMDD`; `dev` = working
branch; promotion = merge + deploy + tag. Mirrors the dashboard's DEC-0011.

*Rationale / caveat:* unlike the dashboard (a web app deployable twice), there is **no drop-in dev
WeeWX** — one dongle, one receiver. Runtime testing therefore needs a deliberate strategy
(Simulator-backed dev container for logic; reversible live hot-swap for RF-dependent checks) agreed
before touching prod (PRINCIPLES §5, ROADMAP). The S16 reconciliation is the first `prod-baseline`.

## DEC-0012 — Public repo: structural secret hygiene

**Status:** Accepted · **Date:** 2026-07-04 (S16)

Real credentials live only in gitignored files (`weewx.conf`, `monitor.env`); committed source uses
`YOUR_*` placeholders. Scrub per-file before every commit; token-pattern grep before every commit;
`weewx.conf.example` regenerated from live with **maximum scrub** (creds + station IDs + station_url
+ coordinates + org name). Never paste a live secret into an LLM prompt.

*Rationale:* the repo is public, indexed, and permanent — a pushed secret is exposed even if later
deleted. S16 caught and scrubbed three real leaks (WU API key + PWS id in `wxcheck.sh`, a place-name
chart title, the InfluxDB org name). *Follow-up:* credential hygiene, tracked in the gitignored local-infra doc (DEC-0047).

## DEC-0013 — Session numbering continues the shared lineage at S16

**Status:** Accepted · **Date:** 2026-07-04 (S16)

The governed era begins at **S16**, continuing the session lineage shared with the dashboard (which
formalized the repo split at its S15). Pre-S16 history is reconstructed/approximate; S16 is the first
live/exact session. Not reset to S1.

*Rationale:* the driver and dashboard shared chat sessions until the split; aligning the counts keeps
the two repos' histories coherent. The tool's long pre-history is real maturity — reconstruct it,
don't flatten it.

## DEC-0014 — No-Rewrite Rule

**Status:** Accepted · **Date:** 2026-07-04 (S16)

No subsystem rewrite without a documented cause, a considered alternative, a migration plan, a DEC
entry, and explicit approval. Favor incremental change.

*Rationale:* LLM-assisted work drifts toward needless rewrites and churn; this is the guard
(PRINCIPLES §7). Carried from the dashboard's DEC-0014.

## DEC-0015 — Graft Python tooling from hyperlocal-forecast

**Status:** Accepted · **Date:** 2026-07-04 (S17)

On top of the governance spine, adopt three Python practices from the `hyperlocal-forecast` repo
(which the JS dashboard has no analog for): (1) `.pre-commit-config.yaml` + a CI gate running
`ruff check` / `ruff format` / `mypy`, plus a "pytest+ruff+mypy before done" validation rule;
(2) a committed secret-scan pre-commit hook; (3) an explicit `INTERFACES.md` contract doc (modeled
on hyperlocal's API_CONTRACT/TRAINING_DATA_CONTRACT pattern).

*Rationale:* this is a Python extension the WeeWX venv imports and that feeds prod — a lint/type/test
gate and structural secret scan are direct insurance against shipping a broken or credential-leaking
`.py`. Rejected from hyperlocal: its per-session file sprawl (superseded by STATUS + CHANGELOG).

**Gap closed (S48, issue #55):** the original "pytest+ruff+mypy before done" intent only ever got
ruff and mypy wired into `.pre-commit-config.yaml` — pytest was documented as a manual pre-close
step (DEC-0052 step 1) and CI-enforced at PR time, but not gated at commit time. Added a `local`
pytest hook (`language: python`, `additional_dependencies: [pytest]`, `always_run: true`) — the
suite is all-stdlib, so pre-commit's isolated env needs nothing from this repo's own `.venv`.
Verified live: fires on every commit regardless of which files changed, passes in isolation.

## DEC-0016 — Claude Opus 4.8 at high/xhigh as the Claude Code driver

**Status:** Accepted · **Date:** 2026-07-04 (S16)

Drive Claude Code sessions with `claude-opus-4-8`: `xhigh` effort for drift-audit judgment and
bug diagnosis, `high` for general agentic work, `medium` for mechanical tasks. `claude-fable-5`
reserved for a single stalled reasoning step, not the default (cost).

*Rationale:* the work is correctness-critical, long-horizon agentic, and RF/decode-reasoning-heavy —
Opus 4.8's strengths — and its 1M context holds the consolidation doc + drift report + logs at once
at standard pricing. Effort setting matters as much as model choice; give the full task spec up front.

## DEC-0017 — Gain held at 372 pending an averaged re-test (OPEN/revisit)

**Status:** Accepted (interim) · **Date:** 2026-07-04 (S16) · **Amends:** the earlier gain=207 lock

The live `[Rtldavis] cmd` runs `-gain 372` and stays there for now. This **amends** the earlier
empirical `gain=207` lock: 207 was optimal *with* the inline preamp over short windows; the owner is
now evaluating operation **without** the inline preamp and left 372 in place deliberately during that
evaluation.

*Rationale / open thread:* neither value is settled without a proper test. A 24 h+ averaged gain
sweep (no inline preamp) is needed to pick the real optimum — it takes a 1–2 week window to run
honestly (BACKLOG, ROADMAP). Until then, 372 is the interim production value, not a final decision.

## DEC-0021 — Rain-counter glitch filter (the false-rain fix)

**Status:** Accepted · **Date:** 2026-07-04 (S18) · **Release:** v2.0.3

Reject implausible rain-counter deltas in the driver instead of accumulating phantom rain. Root
cause (confirmed S18 from code + archive + logs): the Davis rain counter is 7-bit (0–127, wraps at
128), and the original driver treated **any** negative delta as a 127→0 wraparound and added 128 —
turning an RF-decode glitch into phantom rain. Two confirmed events: 2026-05-25 (+128 → 1.28",
exceeds the world 1-min record) and 2026-07-04 (−64 → +64 → 0.64", verified false against the
WeatherLink Live console). Defense in depth:
1. **Driver** (`rtldavis.py`, `rain_delta_tips`): only deltas near −128 are treated as wraparounds
   (real ones observed were exactly −127); small-negative and >`MAX_PLAUSIBLE_TIPS` (60 tips =
   0.60") deltas are rejected → `packet['rain'] = None` (null-on-rejection, DEC-0006). Pure,
   unit-tested (`tests/test_rain_filter.py`).
2. **Backstop** (`weewx.conf [StdQC]`): `rain 0,10 → 0,1.0 inch`; add `rainRate 0,16 inch_per_hour`.

*Rationale:* honest null > fabricated rain (DEC-0006). The cap thresholds are physically grounded
(world 1-min rainfall record ~1.23"; local worst ~1.8"/hr sustained) with generous leeway, so they
catch the characteristic 64/128 glitches without ever clipping real Chester-County rain. CRC is
enforced, so these are multi-bit/mis-decode glitches that pass CRC — the filter is defensive against
the *class* of implausible value, not a specific bit. The rainRate bound is minor insurance: the
driver fix already closes the main rainRate-pollution path (StdRainRater computing from phantom rain).

## DEC-0022 — Sensor-QC hardening deferred to S19 (RESOLVED by DEC-0029, S33)

**Status:** Resolved (S33 — see DEC-0029; wind was already fixed honest-null in v2.0.3) · **Date:** 2026-07-04 (S18)

Two similar-vein issues found during the S18 rain audit, deferred to a dedicated S19 pass so the
rain fix stays tightly scoped:
1. **Stale-substitution (DEC-0006 violation):** `dewpoint_service.py` (lines ~90–97) substitutes the
   **last known** outTemp/outHumidity/radiation/UV when a field is missing, instead of nulling —
   the same anti-pattern fixed for wind. If a real sensor fails, its reading sticks indefinitely.
   Fix needs care: some caching is legitimate (the VP2+ rotates fields across LOOP packets, so
   "absent this packet" ≠ "sensor failed") and the substitution partly feeds the dewpoint/heatindex
   calc — so the fix is "cache for sparse-packet gaps, null after a sensor-failure timeout," and it
   likely folds into the pending v2.0.3 dewpoint rewrite.
2. **Minor StdQC gaps:** high-side `windGust` glitch (that still exceeds a valid windSpeed slips past
   `_filter_wind`), and no `radiation`/`UV` bounds. Low severity (transient, non-accumulating).

*Rationale:* these share the rain bug's theme (RF glitch → bad sensor data) but have real design
nuance and behavioral risk; bundling them into the rain deploy would widen the blast radius. See
ROADMAP P1.5 / STATUS.

## DEC-0023 — Independent per-repo session counter (supersedes the shared-lineage idea)

**Status:** Accepted · **Date:** 2026-07-04 (S20) · **Supersedes:** DEC-0013

**This repo counts its own sessions. There is no shared cross-repo counter.** DEC-0013 asserted that
numbering "continues a single lineage shared with `eaglehunt-weather-dashboard`." A forensic audit
(weewx S20) showed that premise never held:

- The dashboard runs its **own** continuous counter **S1 → S40** (S1–S14 reconstructed; its repo
  split + governance bootstrap at **S15**, 2026-06-23; S15 → S40 thereafter). It contains **no
  reference to a shared counter** with this repo — the "shared lineage" existed only here.
- weewx-rtldavis got its own governance on 2026-07-04 and, per DEC-0013, labeled its first governed
  session **S16** — but the dashboard was already near S38 by then. So "S16" started a **parallel**
  counter re-using numbers the dashboard had long passed. It ran S16 → S17 → S18 → S19.
- A single monotonic counter cannot be shared by two repos developed in parallel without making at
  least one repo's history non-contiguous. The two repos are *deliberately split* (DEC-0010/0011);
  their sessions are independent workstreams.

**Rule going forward:**
1. Each repo has its **own** independent session counter. A session number means something only
   **within its repo**. Coherence across repos comes from **dates**, not numbers.
2. To number a session, take **this repo's own** latest `CHANGELOG.md` / `docs/STATUS.md` + 1. **Do
   not** consult the sibling repo.
3. When referring to a session **across** repos (docs, memory, commit bodies), **prefix the repo**:
   `weewx S21`, `dash S40`. A bare `S21` always means *this* repo.
4. Published labels are **not** rewritten: S16–S19 stand (on `main`/`dev` + in commit messages). The
   one still-unmerged governance-hardening session that a since-reverted draft briefly mislabeled
   "S40" is **this session, S20** — corrected before merge, so `main` never sees the shared-counter
   detour. This repo's line is therefore contiguous: **S16 → S17 → S18 → S19 → S20 → …**

*Rationale:* a shared counter is only useful if it is actually shared — and the sibling never shared
it. Independent counters keep each repo's STATUS/CHANGELOG/DECISIONS legible on their own terms (their
whole purpose), at the cost of a bare number not being globally unique — resolved by the repo prefix
in cross-references. DEC-0013's "don't flatten the real pre-history" instinct still holds; only its
shared-counter mechanism is wrong. (An earlier draft of this DEC tried to *reunify* into the shared
counter and renumber this session to S40; that made per-repo history permanently gappy and was
reversed before reaching `main`.)

## DEC-0024 — RF-reception metric reads ~150%: freqError channel packets published as loop packets (OPEN)

**Status:** epoch-dedup deployed (S27); **daily-email source re-based to `rxCheckPercent` (S31,
committed on `feature/s31-reception-metric` — pending a monitor-restart deploy)**; driver Layer B
deferred · **Date:** 2026-07-04 (S21), updated 2026-07-05 (S22), 2026-07-08 (S31)

> DEC-0023 (independent per-repo session numbering) landed via the S20 governance-hardening branch,
> merged into this rain branch as **PR #2** (S22); this entry took the next number, DEC-0024. The two
> composed without collision.

The daily "RF Reception" summary emails (and 5-min `RECEPTION:` log lines) read ~150% — well above the
100% ceiling a reception percentage should have. **Confirmed by live read-only diagnosis (S21), not a
code regression in the metric itself** (`weewx_monitor.py` reception code is unchanged since it was
added). Root cause, traced end to end:

1. `weewx_monitor.py` computes reception as *(count of `Wunderground-RF: Published record` log lines
   per 60 s) / `WU_RF_EXPECTED` (=24)*. `24` assumes **one publish per ~2.5 s sensor transmission**
   (one Davis ISS).
2. `rtldavis.py` `CHANNELPacket.parse_text` (~L615-642) turns each RF **frequency-hop** telemetry
   message (`ChannelIdx:… FreqError:… Transmitter:N`) into a **WeeWX loop packet** carrying only
   `dateTime`+`freqError` — no weather data — and `PacketFactory.create` (~L682) yields it alongside
   the real sensor `DATAPacket`.
3. WU RapidFire publishes **every** loop packet, so each real reading is shadowed by freq-hop
   "phantom" publishes. Live evidence (4000-line sample, single active Transmitter:4): **1605**
   `Published` lines vs **968** unique record epochs (~**1.66×**); **939** `RAW_CHANNEL_PAYLOAD`
   freq-hop messages over the same span. True reception was ~90% that night; the metric showed ~150%.

**Doc-vs-reality contradiction flagged:** BACKLOG's "FreqError / ppm-fc telemetry gap" finding states
the compiled Go binary emits *neither* `ChannelIdx` nor `FreqError`. The **running binary now emits
both** — which is exactly what activates the `CHANNELPacket → loop-packet` path. This is the most
likely "as of late" trigger (a binary that started emitting the telemetry, or an always-stale
finding); BACKLOG updated accordingly.

Two fix layers, **decision deferred** (S21 was diagnosis + documentation only, no code touched):
- **Layer A (monitor, safe/reversible, not the sacred driver):** count **unique record epochs** per
  window instead of raw publish lines. Directly fixes the reading regardless of driver behavior.
  Slight known trade-off: two real records sharing one integer `dateTime` second collapse to one
  (conservative under-count, acceptable). Deploy = monitor restart only.
- **Layer B (driver, deeper — No-Rewrite DEC-0014 applies):** stop publishing dataless freqError
  channel packets as loop packets, and/or disable the `RAW_*` `loginf` debug instrumentation (also
  the cause of `weewx.log` bloat: 15 MB / 122 k lines). Side benefit: stops posting ~1.6× redundant
  dataless updates to Weather Underground. Needs its own migration plan + prod strategy + approval.

*Rationale for deferring:* the symptom is cosmetic (metric only; real weather data + rain fix
unaffected), so it can wait behind the v2.0.3 promotion. Layer A is the likely first move. See
BACKLOG "Reception-metric over-count" and STATUS.

**Update (S22, 2026-07-05):** **Layer A implemented** on `feature/reception-dedup` (commit `20bf7c0`).
A pure `wu_record_key()` helper dedups on the trailing `(<unix_epoch>)`; the reception window now
counts unique record epochs instead of raw publish lines. `close_reception_window` and the driver are
untouched; 6 offline tests (`tests/test_reception_dedup.py`) against a live-recorded 2× over-read.
Deploy is a monitor restart only (respawn loop reloads on-disk code). **Layer B remains deferred.**

**Update (S31, 2026-07-08) — the epoch-dedup treated a symptom; the *source* was wrong.** A skeptical
audit of the daily emails (owner: "the numbers are all over the place, I have no confidence") found the
`Wunderground-RF: Published` scrape measures publish **liveness**, not RF reception, and *cannot* show
packet loss in the normal regime: WeeWX publishes on its loop/upload cadence (still padded by freqError
freq-hop packets even post-dedup), so the count runs ~21+/min and the % pins at 100 regardless of how
many packets were actually received. **Live proof:** over 21:10–21:23 the email read **100% every
minute** while the driver's own `rxCheckPercent` ran **59–95% (median 75%)** for the same minutes; the
scrape's *only* excursion off 100% was a crash to 0/0/5% during a ~90 s publish stall (an archive gap,
not necessarily RF loss). Bimodal 100↔0 + the denominator churn (24→dedup→21→the old ~150%) explains
the erratic emails end to end. **Fix (Layer A, monitor-only, commit `8dc98ae` on
`feature/s31-reception-metric`):** stop scraping publish lines for the daily summary; read
`rxCheckPercent` straight from the archive DB (`summarize_reception_rows` / `db_reception_summary` /
`format_db_daily_summary`) and report packets **transmitted / received / dropped** + hourly mean & min.
Verified against the live DB (2026-07-06: mean 75%, 30,720 tx, ~7,701 dropped). Read-only, safe
fallback to the legacy summary; real-time `WINDOW` logging + outage alerting untouched (No-Rewrite);
+7 tests (suite 61/61). Deploy = monitor restart (owner-run). **Caveats, both minor & documented:**
(1) the driver floor-divides the period (`max_count = period // loop_time`, `rtldavis.py:995`) so
`rxCheckPercent` — and thus this estimate — runs ~1–2 pts optimistic; (2) the driver computes raw
`count`/`max_count`/`missed` but persists only the percentage, so absolute drops are back-computed from
`% × physical TX rate` rather than read exactly. Both fold into a future **driver Layer B** (persist raw
counts / enable `ARCHIVE_STATS` logging + stop the dataless freqError publishes), still deferred under
No-Rewrite.

**Update (S43, 2026-07-15) — Layer B shipped.** Three options were weighed: (A) drop the channel-hop
packet outright — rejected, because `freqError0-4` are repurposed onto real archive schema columns
(`consBatteryVoltage`/`hail`/`hailRate`/`heatingTemp`/`heatingVoltage`, `rtldavis.py:951-955`) and
`ops/reception_service.py` logs non-zero freqErrors, so dropping it silently breaks both; (C) tag the
packet dataless and filter in every consumer — rejected as unnecessarily broad (touches multiple
files for no benefit over B). **(B), chosen:** cache a channel-hop packet's `freqError{n}` fields
(`_cache_pending_freq_fields`) and merge them onto the *next* real DATA packet
(`_merge_pending_freq_fields`) instead of ever yielding the channel-hop packet as its own loop packet.
Each cached value rides exactly once (cleared on merge). Confined to `genLoopPackets`'s packet-yield
loop plus two small extracted helpers (~25 lines total) — no consumer files touched, no schema
change, no config change.

**`weewx_monitor.py`'s live `WINDOW:` metric is fixed as a side effect, verified live post-deploy.**
This is a *different* file from `ops/reception_service.py` (a WeeWX-internal `ReceptionMonitor`
service that turned out to be unwired from `weewx.conf`'s `[Engine][Services]` entirely, and — per
`git log --follow` — has sat untouched since S16; almost certainly vestigial, like the already-known
`loopdata.py`). `weewx_monitor.py` is the actual NAS-side script behind the reception emails: its
5-minute `WINDOW:` log counts unique record epochs from `Wunderground-RF ... Published` lines
(`wu_record_key`, the Layer A dedup from S22). Channel-hop packets stamp a *fresh* `dateTime` at parse
time (not tied to any real reading), so Layer A's epoch-dedup never fully caught them — S31 confirmed
this metric still ran inflated, pinned near 100% almost always. Post-Layer-B-deploy,
`weewx_monitor.log` reads **`WINDOW: 14-17/21 (67-81%)`, `RECEPTION: 73-77% avg`** — matching the
driver's own trusted `rxCheckPercent` range (`59-95%, median 75%`, S31) for the first time, instead of
pinning near 100%. The daily *email* summary itself was never affected either way — S31 already moved
it to reading `rxCheckPercent` straight from the archive DB, bypassing publish-line counting entirely.
5 offline unit tests
(`tests/test_reception_layer_b.py`), suite 85/85. Driver is baked (DEC-0031) — ships in the next
image rebuild. **DEC-0024 is now fully resolved; both layers shipped.**

## DEC-0025 — Known-bad data: preserve-and-flag, never delete

**Status:** Accepted · **Date:** S29 (2026-07-05)

When we discover an observation we know is wrong (RF/sensor glitch, decode fault), we **never delete
it**. We preserve the raw value and attach a quality flag + a correction, following how observational
networks (WMO, NOAA MADIS) handle suspect data. The policy has four parts:

1. **A public, append-only errata log** — `docs/DATA_ERRATA.md` — is the source of truth for every
   known-bad observation: the bad value, root cause, corrected value, and how far the bad value
   propagated (local archive / InfluxDB / immutable external networks).
2. **The local best-estimate is corrected to NULL, not deleted and not to a made-up number.** We set the
   bad field to NULL (consistent with DEC-0006 honest-null and DEC-0021) and rebuild any derived
   summaries. Nulling one field is **not** removing the record — the row's other valid sensors stay.
3. **Immutable downstream copies are reconciled by the errata, not chased.** Values already sent to
   Weather Underground / CWOP → MADIS cannot be retracted; the errata log is the bridge that maps "what
   we broadcast" to "what we now believe." We do not pretend the external record is clean.
4. **One observation legitimately has several truths** (what the receiver decoded, what we broadcast,
   what physically happened, our best estimate). Correctness depends on the question; the errata log
   preserves the mapping between them rather than collapsing them.

*Rationale:* deleting bad data destroys provenance and diverges silently from the immutable copies we
already published; keeping it silently corrupts our own totals. Preserve-and-flag is the only approach
that keeps our best-estimate honest **and** stays reconcilable with what the world already holds — and
for a public "escape the WeatherLink lock" tool, an open errata log is the honest posture. First entry:
ERR-0001, the 2026-07-04 phantom +1.28" rain (the glitch that inspired the DEC-0021 filter; confirmed to
have reached Weather Underground and, almost certainly, MADIS — precipitation is barely QC'd downstream).
Supersedes nothing; extends DEC-0006 (honest-null) and DEC-0021 (rain filter) to *historical* correction.

## DEC-0026 — v2.0.3 confidence gate waived: cut on tests + live evidence

**Status:** Accepted · **Date:** S29 (2026-07-05)

Cut v2.0.3 with the rain fix baked in **without** first watching a brand-new rain glitch get rejected
live. The original gate (wait for the S18/DEC-0021 filter to reject a real glitch in the wild) was always
a **confidence** gate, not a safety one — the fix has been live in prod for weeks, is unit-tested
(`tests/test_rain_filter.py`), and in S29 we characterized the July-4 glitch end-to-end and validated the
whole rain pipeline (glitch → filter behavior → archive → correction). Real glitches are rare (~1 per
2–3 weeks), so waiting could park the release a month or more for no material gain.

*Rationale:* the fix is already protecting prod; a formal release does not need a live catch to be safe.
If a fresh glitch does appear post-release and reveals a gap, we fix forward (the DEC-0021 filter + the
DEC-0021 email alert + the DEC-0025 errata process all still apply). Supersedes the "watch for the first
real glitch" release gate noted in prior STATUS/ROADMAP; does not change DEC-0021 itself.

## DEC-0027 — Lint scope: enforce `ruff check`, not `ruff format`; exclude vendored uploaders (S31)

**Status:** Decided · **Date:** 2026-07-08 (S31)

CI's `lint` job had been red on every branch (incl. `dev`) — a broken check erodes the "`main` =
production truth" signal and trains everyone to ignore CI. Audited the actual debt: **27 `ruff check`
findings** (17 in vendored third-party code, 10 in ours) **and `ruff format --check` wanting to reformat
25 files** — nearly the whole tree, including the baked driver and the vendored uploaders.

**Decision — lint what we maintain; don't police style or vendored code:**

1. **Drop the `ruff format --check` CI gate** (keep `ruff check`). Two reasons: (a) the codebase uses
   **deliberate column alignment** for readability (e.g. `weewx_monitor.py`'s aligned `=`, the
   `THRESHOLDS` dict) that the formatter would flatten; (b) the driver `rtldavis.py` is **baked into the
   shipped image** (ARCHITECTURE §3) — auto-reformatting a prod-sacred file to satisfy a style checker is
   exactly the churn No-Rewrite (DEC-0014) guards against. `ruff check` still catches the real bug classes
   (unused imports, bare excepts, ambiguous names).
2. **Exclude vendored third-party uploaders** (`influx.py`, `wcloud.py` — Matthew Wall; `ogoxeUploader.py`)
   via `ruff.toml` `extend-exclude`. They are copied verbatim from upstream and carry intentional
   Python 2/3 `try/except import` shims that ruff misreads as `F401`/`E402`. We do not modify vendored code.
3. **Fix the 10 findings in our own code:** `rtldavis.py` (removed unused `calendar.timegm`/`fnmatch`/
   `string`; bare `except:` → `except Exception:`), `weewx_monitor.py` (split the one multi-import line),
   `tests/test_reception_dedup.py` (ambiguous `l` → `ln`), `ops/*` (removed unused `json`, `datetime`).

**Result:** `ruff check .` passes cleanly; CI `lint` is honestly green; the driver's runtime logic and the
codebase's formatting are untouched. *Alternatives rejected:* full `ruff format` adoption (huge diff,
reformats the baked driver — No-Rewrite) and relaxing lint to non-blocking (defeats the point — we want
real green, and `ruff check` catches genuine issues). If a formatter is ever wanted, adopt it deliberately
per-file with the alignment trade-off understood, not as a blanket gate.

**Update (S43, 2026-07-15) — the decision was dropped from CI but never from local pre-commit.**
`.pre-commit-config.yaml` had carried a `ruff-format` hook the whole time, silently contradicting this
DEC. It never fired because **pre-commit itself was never installed** until S42 (DEC-0050) — so this
was a second, independent instance of "a configured control that nothing executes is prose," this time
inverted: once actually installed, its first real run **did** execute, and it mass-reformatted
`rtldavis.py` (a 3,213-line diff) attempting the S43 commit, exactly the outcome this DEC rejected.
Caught before it landed (a second hook's file modifications also blocked the same commit). Fixed:
`ruff-format` removed from `.pre-commit-config.yaml`, local config now matches this DEC and CI. Checked
both sibling repos for the same pattern: the dashboard already avoids it deliberately (no `ruff-format`,
noted in its own config header); `hyperlocal-forecast` does carry `ruff-format`, but with no equivalent
DEC and no known baked/aligned file, there is no evidence it's wrong there — not filed as a finding.

## DEC-0028 — Leaked credential in pushed public history: rotate immediately, don't rewrite (S32)

**Status:** Decided · **Date:** 2026-07-08 (S32)

S32 found the monitor's Gmail app password hardcoded in two *historical* commits of
`weewx_monitor.py` (`d2fb080` 2026-05-22, `eff3f56` 2026-05-24) — reachable from public `main` and
`dev` for ~6 weeks — plus a NAS-only copy in the legacy `weewx_monitor.sh`. The DEC-0012 secret gate
never fired because it scans working trees and diffs, **not history**; the current file had long
since moved the value to `monitor.env`.

**Decision — for any secret discovered in already-pushed history: rotate the credential immediately;
do not rewrite public history.**

1. **Rotation is the fix.** Once pushed to a public repo for weeks, the value must be assumed
   harvested (bots scrape GitHub for the app-password pattern); revoking it removes all residual
   value. Done same-day: revoked, reissued into `monitor.env`, verified live by the monitor's
   startup email.
2. **History rewrite rejected.** `git filter-repo` + force-push of `main`/`dev` on a *published*
   repo breaks every clone/fork, violates the never-force-push-main rule, and still doesn't un-leak
   anything (forks, caches, archives). The dead credential in history is accepted residue.
3. **Scope note for the gate:** DEC-0012's gate prevents *new* leaks; it cannot retro-scan. A
   one-time full-history scan (e.g. `git log -p | grep` for token patterns, or `gitleaks`) is cheap
   insurance after any gate hardening — this find came from exactly such an ad-hoc sweep.

Related: the WU API key from the same pre-governance era (S16 find) is still awaiting owner rotation
— same playbook applies.

## DEC-0029 — Decode-layer sensor plausibility filter (temp/humidity/wind/UV/radiation)

**Status:** Accepted · **Date:** 2026-07-08 (S33) · **Resolves:** DEC-0022 · **Extends:** DEC-0021/DEC-0006

**Problem.** The rain glitch's failure class — multi-bit RF corruption that passes CRC and decodes
to a wrong bit-field — hits every sensor, but only rain had a decode-layer filter (DEC-0021). S33
evidence (50 days of archive, 68,877 records):

- **outHumidity:** 18 confirmed one-minute glitch spikes (flat radiation + flat temp rules out the
  cloud/shield explanation). Deviations cluster at **25.6/3 ≈ 8.5%** and **12.8/2 ≈ 6.4%** — exactly
  single bit-7/bit-8 flips of the raw %×10 field averaged over the minute's 2–3 readings. The
  midday-only pattern is a **selection effect**: at night (RH ~90%) the same flips land >100%, StdQC
  nulls them, and the DewpointCacher carry-forward hides the null — so the archive *understates* the
  true rate.
- **UV:** one physically impossible record (16.29 under 320 W/m² overcast, 2026-05-30 15:50).
- **Wind:** the 201 mph loop-only spike (S30) — never archived because StdQC/DewpointCacher run
  *behind* `LoopJsonWriter` (a `data_service`), which is exactly why only the decode layer protects
  the live dashboard. (S30's suspected `MAX_WIND_DELTA` unit mismatch was **disproven**: DewpointCacher
  runs after StdConvert with `target_unit = US`, so 75.0 is correctly mph.)
- **outTemp/windGust:** archive clean — dashboard temp spikes were loop-path-only, same as wind.

**Decision.** A two-layer filter (`SensorQC` in `rtldavis.py`) applied in `_data_to_packet` (rain's
choke point), so all consumers — loop-JSON included — see honest nulls (DEC-0006), never corrupt values:

1. **Davis sensor-spec bounds** (site-agnostic, safe for any station of this public driver):
   temperature −40..65 °C, humidity 0..100%, wind 0..89.4 m/s (200 mph), UV 0..16, radiation
   0..1800 W/m². An impossible value never moves the delta baseline.
2. **Per-reading delta** vs the last accepted value, for temperature (4 °C), humidity (10%), wind
   (20 m/s), UV (8) — glitch magnitudes sit far above real inter-reading changes. **Radiation gets
   no delta filter**: genuine cloud edges swing ±900 W/m² in a minute (enhancement to 1579 W/m²
   observed), so bounds only. Delta rejections **resync the baseline** (the rain-filter trick): an
   isolated glitch costs 1–2 nulled readings, a genuine step is accepted on the very next reading,
   and no stale-baseline deadlock (the S24-H2 failure mode) is possible. Baselines expire after
   300 s (reception gaps reseed cleanly).

Rejections log `"rejecting implausible value"` (the rain filter's signature family) — the forward
packet-evidence capture this repo lacked (the old `RAW_CHANNEL_PAYLOAD` lines held only hop metadata,
and v2.0.3's upstream-default binary silenced even those). Config: `sensor_qc = false` master switch,
`qc_<field>_max_delta` overrides (`weewx.conf.example` §[Rtldavis]).

**Companion (closes DEC-0022 #1).** `dewpoint_service.py` carry-forward → **timeout-null**: the
temp/humidity/radiation/UV cache still bridges the ISS message-type rotation, but expires after
300 s of sensor silence (`CACHE_TIMEOUT_SECONDS`) — a failed sensor now reads null, not frozen.
dewpoint/heatindex are computed only from fresh values. DEC-0022 #2 (StdQC radiation/UV bounds) is
superseded at the decode layer; the windGust>windSpeed consistency check stays in `_filter_wind`.

**Deploy:** the driver is baked (S30) — ships with the next image rebuild (v2.0.4), not a hot-swap.
Tests: `tests/test_sensor_qc.py` (16) + `tests/test_dewpoint_timeout_null.py` (6), recorded-signature
based, suite 85/85.

## DEC-0030 — Docs diet: tiered session read, DEC index+full split, CHANGELOG roll, STATUS prune

**Status:** Accepted (owner-directed session goal) · **Date:** 2026-07-09 (S35)

**Problem.** The CLAUDE.md doc map mandated a ~130 KB (~32K-token) read at every session start —
CHANGELOG.md alone 46 KB, DECISIONS.md 35 KB — and it grew every session, because each session
appends narrative and every later session re-reads the total. Both siblings hit the same wall and
fixed it: the dashboard at its S57 (its DEC-0081, with the portable recipe at
`eaglehunt-weather-dashboard:docs/reference/docs-diet-playbook.md`), hyperlocal-forecast at its
S143 (its DEC-0095). This is the third and final port; the playbook's porting notes for this repo
(public-repo secret scan, own session counter, keep existing doc names) are honored below.

**Decision.**
1. **Two-tier session read (CLAUDE.md doc map).** Tier 1, always: STATUS.md (bench state + handoff),
   CONVENTIONS.md, PRINCIPLES.md, DECISIONS.md (index), live CHANGELOG.md. Tier 2, on demand by
   task: DECISIONS-FULL.md, ARCHITECTURE.md, INTERFACES.md, ROADMAP.md, BACKLOG.md,
   CHANGELOG-ARCHIVE.md, ASSESSMENT.md, DATA_ERRATA.md. Anti-loophole rule: **"working near it"
   means read it.** Plus the stale-checkout guard: the current docs live on `dev` — read from
   `dev`'s tip if the local checkout lags (this trap bit S35's own pickup).
2. **DECISIONS split: index + full.** `docs/DECISIONS.md` becomes a one-row-per-DEC index
   (id · title · status · date) + the open/deferred list; the complete append-only bodies move
   **verbatim** to `docs/DECISIONS-FULL.md`. New decision = append full body + add index row.
3. **CHANGELOG roll.** The live file keeps ~3 sessions; older entries move verbatim to
   `CHANGELOG-ARCHIVE.md` (append-only, same format). Rolling is part of the session-close ritual.
4. **STATUS prune ritual at every session close:** shipped → CHANGELOG pointer, settled → DEC
   pointer, superseded notes deleted. STATUS keeps: current session, active thread, genuinely open
   threads, the next-session handoff.
5. **Invariant: move text, never delete or rewrite history.** Everything stays greppable in this
   repo; only the default read shrinks. **Public-repo caveat:** every file a move rehomes goes
   through `scripts/check_secrets.sh` before commit (DEC-0012) — the archives are public history too.

**Measured (S35).** Mandated read before: ~130 KB ≈ ~32K tokens (10 docs). After: Tier 1 ≈ 33 KB
≈ ~8K tokens (CLAUDE 7 KB + STATUS 7 KB + CONVENTIONS 5 KB + PRINCIPLES 4 KB + DECISIONS index
4 KB + live CHANGELOG 8 KB).

*Rationale:* long boots burn context before work starts and force earlier compaction; the sibling
repos measured 4–8× reductions with no history loss. Consistency across the family is itself the
meta-goal (docs/ASSESSMENT.md): all three repos now share the same tiered-read + index/archive
skeleton. Extends DEC-0010 (the governance model) rather than superseding it — the nine files
remain; only the default read protocol changes.

---

## DEC-0031 — The driver is BAKED into the image, never bind-mounted

**Date:** 2026-07-12 (S36) · **Status:** Accepted · **Supersedes:** the driver half of DEC-0004

**Context.** weewx imports `user.*` from the venv — `/opt/weewx-venv/lib/python3.14/site-packages/user/`
— and **not** from `weewx-data/bin/user/`. That single fact has now caused the same silent failure
twice, by two different mechanisms, and cost roughly two sessions of debugging each time:

1. **Build time (found S30).** `Dockerfile` did `cp /opt/weewx-data/bin/user/rtldavis.py` over the
   patched driver it had just `COPY`'d in. `weectl extension install` lays the **stock** upstream
   driver down at that path, so every image ever built shipped the stock driver. This is why
   `rxCheckPercent` was NULL for weeks and why the July-4 phantom rain (ERR-0001) entered the archive
   with a rain filter supposedly deployed: the filter was never in the running code.
2. **Run time (found S36).** `docker-compose.yml` bind-mounted that same host path over the baked
   driver, `:ro`. The running prod container happened to escape it (it was hand-run without the
   mount), but the mount shipped in the **public** compose file — so downstream users of the
   published image have been running the stock driver regardless of what the image contains.

Both failures are **silent and actively misleading**: the version tag, the logs, and the file the
operator just edited all agree the fix is present, while the process runs different code. The S69
dashboard handoff independently recommended a `weewx-data` `scp` hot-fix as the cheap deploy path —
which would have been a no-op for exactly this reason. The trap is not obvious; it is *anti*-obvious.

**Decision.**
1. **The driver (`rtldavis.py`) is baked into the image. It is never bind-mounted, at build or run
   time, in any compose file, on any host.** To change the driver you rebuild the image. There is no
   hot-swap path for the driver, and one must not be reintroduced for convenience.
2. **Services and uploaders may still be mounted** (`influx.py`, `loop_json_writer.py`,
   `ogoxeUploader.py`, …). Nothing bakes over them, so DEC-0004's hot-iteration benefit is retained
   where it is actually safe. It is the *driver* that is carved out, not the whole idea.
3. **Verification is mandatory before declaring a driver deploy done** — the version tag is not
   evidence. Assert against the running process:
   `docker exec <ctr> /opt/weewx-venv/bin/python3 -c "import user.rtldavis as m; print(m.__file__, hasattr(m,'SensorQC'))"`
   and confirm `docker inspect` shows **no** mount landing on `.../site-packages/user/rtldavis.py`.
4. Both the `Dockerfile` and `docker-compose.yml` carry an explicit "do NOT re-add this" comment at
   the exact line where the clobber used to live, naming the consequence.

*Rationale:* a hot-swap that silently does nothing is far worse than no hot-swap at all — it
manufactures false confidence and sends the next session hunting a phantom bug in the wrong layer.
Baking is slower per iteration and honest; mounting was faster and lied. Given the data this driver
produces is uploaded to WU/CWOP → NOAA MADIS, where it is **immutable** (DATA_ERRATA "external"),
false confidence in a QC fix is a data-integrity hazard, not just a developer annoyance.

---

## DEC-0032 — Retrospective correction: correct to the KNOWN value, flag it in-band

**Date:** 2026-07-12 (S36) · **Status:** Accepted · **Clarifies:** DEC-0006 · **Serves:** DEC-0025

**Context.** DEC-0006 ("null on rejection, never stale substitution") was read as *"every correction
must be NULL."* Applying that to the phantom rain events produces a worse record, not a better one.
All three phantoms (ERR-0001 ×2, ERR-0002) are **bracketed by zeros for ±20 minutes**: we know, as a
matter of positive evidence, that it did not rain. Writing `NULL` there says *"we don't know"* — which
is false, and understates what we know. Writing `0.0` states the fact.

The apparent conflict dissolves once the two acts are separated:

- **Runtime rejection** (DEC-0006): the driver has just rejected a reading and has **no idea** what the
  true value was. Substituting anything — a stale cached value, an interpolation, a zero — fabricates
  data. It must emit `None`. **Unchanged.**
- **Retrospective correction** (this DEC): we are looking at the surrounding record, offline, with
  full context, and can often establish the true value with confidence. Recording that value is not
  fabrication; it is the correction.

`NULL` is not "safe by default" — it is itself a claim ("unknown"), and an incorrect one when the
value is in fact known.

**Decision.**
1. **Correct to the known value where positive evidence establishes it; correct to `NULL` only where
   the true value is genuinely unknown.** For an isolated rain bit-flip bracketed by zeros, the
   corrected value is **`0.0`** — a fact, not a guess. For, say, a corrupt temperature with no way to
   recover the real reading, `NULL` remains correct.
2. **The evidence must be stated in the errata entry.** A correction to a known value is only
   admissible if `DATA_ERRATA.md` records *why* we know it (here: "every minute for ±20 min reads
   exactly 0.0"). No evidence → `NULL`.
3. **Flag the correction in-band, sparsely.** InfluxDB corrected points carry a **`rain_qc = 1`** field
   written **only at the corrected timestamps**. InfluxDB is schemaless, so an absent field costs
   nothing: the flag's storage scales with the number of *corrections* (3 points, well under 1 KB), not
   with data volume, and it adds **zero** overhead to queries that don't ask for it. This mirrors
   WMO/NOAA-MADIS practice — keep the value, attach a quality flag — and gives the dashboard a way to
   render a "corrected" marker straight from the data instead of maintaining a parallel list.
4. **`DATA_ERRATA.md` remains the narrative source of truth.** The in-band flag is a pointer to it, not
   a replacement: the flag says *"this was corrected"*, the errata says *what, why, and how far it
   spread*. A consumer must never have to reconstruct the story from flags alone.
5. **Both stores must agree.** A correction is applied to the SQLite archive *and* InfluxDB in the same
   session, with matching values. (ERR-0001 sat as `NULL` in the archive and uncorrected in InfluxDB
   for a week — two stores disagreeing about one event is exactly the unauditable state this forbids.)

*Rationale:* DEC-0025's "preserve and flag, never delete" is honored at the layer that actually holds
raw data — the immutable `weewx.log` and the external WU/CWOP→MADIS copies, neither of which we touch.
The archive and InfluxDB are explicitly the **corrected best-estimate** layer (DATA_ERRATA "Three
layers"), so putting our best estimate in them is their purpose, not a violation of it. What must never
happen is a corrected value that is *indistinguishable* from a measured one — which is precisely what
the errata entry plus the in-band `rain_qc` flag prevent.

---

## DEC-0033 — The glitches are CRC-valid multi-bit corruption from spurious duplicate frames

**Date:** 2026-07-12 (S36) · **Status:** Accepted · **Confirms** DEC-0029's stated cause (which an
earlier S36 draft wrongly "corrected" — see the retraction note below)

**Context.** DEC-0029 attributed the sensor glitches to *"multi-bit corruption that passes CRC"* and
treated it as a given. Investigating it for an upstream bug report (S36) first produced a **wrong**
conclusion, then the right one. Both are recorded, because the wrong one is instructive.

**The retracted claim (do not resurrect it).** We verified that CRC-16-CCITT (poly `0x1021`) cannot
miss a **single-bit** error — 0 of 64 single-bit flips of a valid 8-byte message pass. From that we
concluded the corruption *must* be transmitter-side (present before the ISS computes its checksum).
**That inference was invalid.** "CRC catches all single-bit errors" does not imply "CRC catches all
errors" — a **multi-bit** error pattern can be a multiple of the generator polynomial and is then
completely undetectable. We had proved a narrow fact and over-generalized it.

**The evidence that settled it** — raw packets posted by user *LloydR* in upstream issue
[lheijst/weewx-rtldavis#15](https://github.com/lheijst/weewx-rtldavis/issues/15), verified against our
own `weewx.crc16`:

```
03:57:08.612942  E003BE730300E26A   rain byte 0x73 (115)   crc16 = 0  PASSES
03:57:08.613204  E0019E310300E26A   rain byte 0x31 ( 49)   crc16 = 0  PASSES   <- 262 us later
```

The two frames differ in **4 bits** (`0x02 0x20 0x42` across bytes 1–3) and **both pass CRC** — the
error pattern is a valid codeword. They arrived **262 microseconds apart**, while a Davis ISS transmits
every **~2.5 seconds**. So one transmission produced two decoded frames: the receiver, not the
transmitter, made the second one.

**Decision — the settled model:**
1. **Root cause (upstream, unfixed):** the `rtldavis` Go demodulator sometimes emits a **spurious
   near-duplicate frame** microseconds after a good one. Most such frames are garbage and **fail CRC,
   so they are dropped silently and invisibly**; roughly **1 in 65,536** passes by chance and delivers
   corrupt sensor values. This is consistent with the observed rarity (~1 event per 2–3 weeks) without
   requiring any exotic mechanism. *(LloydR independently patched the Go program to reject packets
   arriving <2 s apart and reports it fixed his station — supporting the model, though it was never
   upstreamed; the Go repo has issues disabled.)*
2. **The driver's dedup cannot catch it.** `if data != self._last_pkt` (~L1209) is **exact-equality**.
   A *corrupted* near-duplicate differs from the previous packet, so by construction it is not a
   duplicate and passes straight through. The guard only stops the harmless case.
3. **CRC is therefore NOT a defense**, and a decode-layer plausibility filter is the only one available
   to us. This is the standing justification for `rain_delta_tips` (DEC-0021) and `SensorQC`
   (DEC-0029). Anyone proposing "just trust the CRC" should be pointed here.
4. **Transmitter-side corruption is NOT ruled out** as an additional contributor — we simply have no
   evidence for it, and the demodulator model explains everything we have seen. Do not assert it.
5. **We have not confirmed the duplicate-frame fingerprint on OUR station**, because `DEBUG_RTLD = 0`
   and `weewx.log` rotates daily, so the raw `data:` lines were never captured. **Open follow-up:** run
   with `debug_rtld = 1` for a few days and look for sub-2-second packet pairs. Until then, the
   mechanism is upstream-confirmed but locally unverified.

*Rationale for recording the retraction:* the wrong version was confidently argued, internally
consistent, and would have produced a publicly wrong bug report asserting the maintainer's CRC handling
was fine and Davis was at fault. It survived until someone checked it against **another user's raw
bytes**. The lesson is narrow and worth keeping: *a proof about single-bit errors says nothing about
multi-bit errors* — and when a conclusion depends on an inference rather than a measurement, go find
the measurement.

---

## DEC-0034 — State the fork honestly: modification notices, `+ws` version, CHANGES-FROM-UPSTREAM

**Date:** 2026-07-12 (S37) · **Status:** Accepted

**Context.** This project ships several other people's GPLv3 files with our patches on top, and said so
nowhere. Specifically:

- `rtldavis.py` carried only *upstream's* header (`Copyright 2019 Matthew Wall, Luc Heijst`) and
  reported `DRIVER_VERSION = '0.20'` — the stock upstream version — while actually carrying a rain
  filter (DEC-0021), SensorQC (DEC-0029), the H1/H2/M3 fixes, a windDir fix and a calm-air gate.
  Measured delta from the `src.tgz` base: **+263 / −51 lines.**
- `influx.py` (from `david-lutz/weewx-influx2`) reported `VERSION = "0.20"` while carrying five
  patches, including a TLS-verification security fix.
- `ogoxeUploader.py` and `wcloud.py` were vendored with no modification notice.

**GPLv3 section 5(a)** requires a modified work to "carry prominent notices stating that you modified
it, and giving a relevant date." We were not doing that. Every other link in this chain was: Luc
documents his merge of Matthew Wall's drivers in the file header, and Vince Skahan added a dated
`# 20-12-2025 patched by vinceskahan@gmail.com` block to the very same file. We inherited the
convention and skipped it.

The practical harm is the same class as DEC-0031 (the compose clobber): **the artifact asserts one
thing and does another.** A `0.20` in the logs tells a reader — including us, and including anyone we
try to help on upstream issue #15 — that they are looking at stock upstream behavior. They are not.

**Decision.**

1. **Modification notices** in the header of every patched upstream file (`rtldavis.py`, `influx.py`,
   `ogoxeUploader.py`), following the convention Luc and Skahan already established in these files:
   who, when, what changed. `wcloud.py` gets a one-line notice recording that the *only* change is an
   SPDX tag.
2. **Version honestly** with a PEP 440 local identifier: `0.20` → **`0.20+ws.1`** in both
   `rtldavis.py` and `influx.py`. The driver logs
   `driver version is 0.20+ws.1 (fork of lheijst 0.20, patched by WeatheredScientist -- not stock
   upstream)`. This also replaces the ad-hoc `RTLDAVIS_DRIVER_MARKER` canary from the DEC-0031 hunt:
   stock upstream cannot print that line, so it proves which driver is loaded, honestly.
3. **`CHANGES-FROM-UPSTREAM.md`** — the full inventory: provenance chain, every divergence with a
   date and a reason, and an upstreaming status per item. It is both the "playing nice" document and
   the checklist for *shrinking* the fork.
4. **README opening rewritten.** It read as though we ship Luc's driver. It now says plainly:
   unofficial Docker distribution, patched driver, not affiliated, links upstream and to the
   divergence list.
5. **Upstream-first posture.** To contribute we fork `lheijst/weewx-rtldavis` **separately** and send
   one focused PR (starting with the rain fix). This repo correctly stays a normal repo, not a GitHub
   fork of the driver — it is a *distribution*, not a driver fork.
6. **Keep the repo and image name.** It is published and attribution is intact; renaming breaks every
   downstream `docker pull`. This is about honesty, not rebranding.

**Consequences.** The audit turned up more than expected: `influx.py` holds **five** upstream patches,
not the one Py-3.14 fix we thought — including `e.read.decode()` (a missing pair of parens that makes
the HTTP error handler raise `AttributeError` instead of reporting the error) and an unconditional
`ssl._create_unverified_context()` on https endpoints. Four of the five are unambiguous upstream bugs.
`rtldavis.py` holds four real upstream bugs beyond the rain filter. The fork is more valuable — and
more obligated to upstream — than we assumed.

---

## DEC-0035 — The duplicate-frame mechanism is CONFIRMED on this station (and the test that said otherwise was broken)

**Date:** 2026-07-12 (S37) · **Status:** Accepted · **Confirms** DEC-0033 locally (resolves its open item 5)

**Context.** DEC-0033 concluded that the CRC-valid corruption here is caused by the `rtldavis` Go
demodulator emitting a **spurious near-duplicate frame** microseconds after a good one — the fingerprint
LloydR posted upstream (two frames 262 µs apart, 4 bits different, both CRC-valid). Its item 5 was
explicit that this was **upstream-confirmed but locally unverified**, and set the follow-up: capture raw
frames, look for sub-2-second pairs. S36 enabled `debug_rtld = 2` in prod and wrote
`ops/find_duplicate_frames.py`.

**The first answer was wrong.** The script reported **0 suspicious pairs** in 1,863 frames over two
hours, with a beautifully clean gap distribution: minimum gap exactly 2.8000 s, every gap an exact
integer multiple of the ISS period (2.8 / 5.6 / 8.4 / 11.2 s). That looks like a decisive null. It is an
artifact. **The instrument was blind to the thing it was built to detect**, in two independent ways:

1. **It parsed only `data:` lines — which are post-dedup.** `main.go` compares each message to the
   previous one and, on a byte-for-byte match, logs `duplicate packet:` and `continue`s *before* the
   message ever reaches the driver (`main.go` ~L394). So every exact duplicate had already been stripped
   out upstream of the lines the script was reading. The gaps were perfectly quantized *because* Go had
   removed everything that wasn't.
2. **Its stated premise about CRC is false.** The docstring claims "the driver logs the raw `data:` line
   BEFORE it checks the CRC, so we see the spurious frames even when they fail CRC." That confuses the
   Python driver's CRC check with the Go decoder's. `protocol.go` ~L218 — *"If the checksum fails,
   bail"* — drops every CRC-failing packet inside the Go binary. Python only ever sees CRC-valid frames.

Both errors push the same way: they hide duplicates. The "answer in hours" reasoning was therefore also
wrong — had the script been correct-but-limited to CRC-valid corrupted frames, the expected count in a
2-hour window would have been ~0.005, and zero would have meant nothing either.

**The measurement, done correctly.** Counting `duplicate packet:` lines (Go's own dedup log, surfaced at
`debug_rtld = 1`) over the same 120-minute window, and matching each back to its original:

| Gap from duplicate to its original | Count | Interpretation |
|-----------------------------------|-------|----------------|
| 1.4 – 10 ms | **61** | **Receiver artifact — the ISS cannot transmit twice this fast** |
| 10 – 100 ms | 1 | same |
| 2.0 – 3.2 s | 712 | Transmitter cadence — genuine ISS repeats of an unchanged payload |

Representative event:

```
20:31:04.102918  E401BD56010ED10E  ACCEPTED
20:31:04.104955  E401BD56010ED10E  DUP-DROPPED   +0.002037 s later, IDENTICAL bytes
```

**Decision — the mechanism is confirmed on this station.** The demodulator re-decodes a single RF burst
twice, at a rate of **61 per 2 hours (~0.5/min, ~730/day)**, median gap **2.0 ms**. A Davis ISS transmits
every ~2.8 s; a second frame 2 ms later cannot come from the transmitter. This is LloydR's mechanism on
our hardware (his gap was 262 µs, ours ~2 ms — same class, different SDR timing).

The full glitch chain:

1. The demodulator double-decodes one transmission. **Observed: ~730/day** (lower bound — see below).
2. The second decode is a marginal re-detection and sometimes carries bit errors.
3. A **corrupted** second copy no longer matches the previous frame, so Go's **exact-equality** dedup
   (`seen == lastRecMsg`) does not catch it. This is DEC-0033's point 2, now confirmed at the Go layer
   as well as the Python one.
4. It must still pass CRC to be emitted. Most fail and are dropped **invisibly** at `protocol.go` L218 —
   which is why 730/day is a *lower bound* on double-decoding, counting only the copies that came
   through clean enough to be byte-identical.
5. The ~1-in-65536 that passes CRC by chance reaches the driver as a valid-looking packet carrying
   garbage — phantom rain (DEC-0021), humidity and UV spikes (DEC-0029).

**Consequences.**

1. **The owner's precondition for the upstream post is met.** He asked for *"our own confirmation of the
   duplicate-frame fingerprint"* before posting to issue #15. We have it, from our own hardware, with a
   frame-gap census behind it. The post still needs his voice and his explicit go — that has not changed.
2. **`ops/find_duplicate_frames.py` is fixed** to parse `duplicate packet:` lines and to state the CRC
   pipeline correctly. The old version would have told anyone who ran it that their station was clean.
   It is worth keeping precisely because it was wrong: it is the second time in two sessions that a
   confident conclusion here rested on an unchecked assumption about *where in the pipeline* a check
   happens (DEC-0031 was the same shape).
3. **A rate this high is itself the finding.** ~730 double-decodes/day means the corruption path is not
   exotic or marginal — it is running constantly, and only CRC and an exact-match dedup stand between it
   and the database. Both are known to be insufficient. This strengthens the case for the decode-layer
   filters, and it is the number to lead with upstream.
4. **Instrumentation, not debug mode.** The `duplicate packet:` line is logged via `dbg_rtld(1)` →
   `log.debug`, so surfacing it requires the `user` logger at DEBUG — too noisy to leave on. Prod is back
   at `debug_rtld = 1` / INFO. The right fix is a **permanent, cheap counter** in the driver: tally
   duplicate-packet lines off the Go stderr stream and log one summary line per archive period at INFO.
   Proposed for v2.0.5 — it turns a two-hour debug expedition into a standing measurement, and it is the
   instrument that would also catch the rainRate mechanism (STATUS).

*Lesson, stated plainly because it has now cost two sessions:* a null result from an instrument whose
sensitivity you have not verified is not evidence of absence. Before trusting a "zero", prove the tool
can see a "one".

**Update (S43, 2026-07-15) — the permanent counter shipped, exactly as proposed.** `genLoopPackets`'s
existing stderr-scan loop (already special-cased `"Hop:"`/`"ChannelIdx:"`) now also counts
`"duplicate packet:"` lines into `self.stats['dup_count']`, unconditionally — no `debug_rtld` gate.
`_update_summaries()` logs one INFO line every archive period (`"duplicate frames this period: N"`),
including `N=0` so a quiet period is distinguishable from the instrument not running; `_reset_stats()`
zeroes it for the next period, following the exact pattern already used for `pct_good_all`. 5 offline
unit tests (`tests/test_duplicate_frame_counter.py`), suite 85/85. Driver is baked (DEC-0031) — ships
in the next image rebuild, bundled with DEC-0024's Layer B (same file, same rebuild).

---

## DEC-0036 — The 7h18m freeze: trigger known, mechanism OPEN; bank the mitigations

**Date:** 2026-07-13 (S37) · **Status:** Accepted · **Mechanism deliberately left open**

**What happened.** At 2026-07-12 23:53:45 weewx stopped doing anything for **7 h 18 m** (ERR-0003). It did
not crash. Both processes stayed alive, the container reported "Up", and **no error or traceback was ever
written** — because the thing that was stuck *was the logging*. `weewx_monitor.py` emailed at 00:15; the
owner was asleep.

**What is established (measured, not inferred):**

- weewx's main thread (tid 1) was in kernel state **`pipe_wait`** — blocked on a pipe.
- The Docker daemon's path for **this container only** was wedged: `docker logs`, `docker exec` and
  `docker kill` all hung on it, while the other three containers (HLF, eh-proxy, influxdb) were
  completely healthy.
- A **bare `docker logs` with no `--tail`** (PID 15883) had been hung since Jul 12, along with two later
  `--tail` invocations. Synology's Docker log store is a SQLite `log.db`.
- Killing the hung clients did **not** free it. Only `synopkg restart ContainerManager` did.

**What is NOT established — and the first answer was wrong.** The initial diagnosis was *"weewx's INFO
console handler filled the container's stdout pipe."* **That is false for this station.** The live
bind-mounted `weewx.conf` has **no console handler at all** (`handlers = rotate,` — file only), so weewx
was not writing to stdout. `pipe_wait` is the kernel's wait state for a blocked pipe **read *or* write**;
it was read as "write to stdout" without checking. **We do not know which write blocked, and the
container has been restarted, so the evidence is gone.**

**Decision: bank the mitigations, record the mechanism as OPEN.** Do not fabricate a causal chain to
close the ticket. The mitigations below do not depend on knowing the exact blocked write:

1. **`logging.additions`: console handler `INFO` → `WARNING`.** *This is not the fix for our outage* — it
   is a fix for **the image we publish**. `logging.additions` (baked into the image by the Dockerfile)
   **does** define a console handler at INFO with `handlers = rotate, console,`. Our prod escaped it only
   because the **live config has drifted from the repo** and lost that handler. So **every downstream user
   of the published image runs with INFO-level stdout logging that we do not.** Same shape as DEC-0031:
   *the artifact we ship differs from what we run, and we did not know.* At WARNING the handler emits
   ~nothing in normal operation, so the pipe cannot fill regardless of `docker logs` or `debug_rtld`;
   errors stay visible; full detail is unaffected (it goes to the `rotate` file handler, which is what we
   and the monitor actually read).
2. **Never run `docker logs` without `--tail`.** The rule already existed in CONVENTIONS ("the log is
   large"). It now has teeth: a bare `docker logs` can hang, wedge the daemon's log path for that
   container, and take production down. It is not a style preference.
3. **Cap the log driver** (`max-size`, `max-file`) so the store cannot bloat. Belt-and-braces.
4. **The monitor is NOT the gap.** It detected the freeze in 22 minutes and emailed. An earlier draft of
   this decision proposed "add a liveness check" — it already exists and it worked. Recorded so nobody
   builds it twice.

**Cross-project.** This is **not weewx-specific.** Any container whose process writes to stdout can be
frozen by a wedged Docker log path. `hyperlocal-forecast-api` and `eh-proxy` have the same exposure.
Handoff docs go to those repos; **we do not change them from here** (owner's instruction, and the
DEC-0031 lesson: *infrastructure advice across a repo boundary must be verified in the target repo before
it is given*).

*Lesson, and it is the second time today:* reasoning past the evidence produced a confident, wrong,
internally-consistent story — first that the duplicate-frame test was a decisive null (DEC-0035), then
that the console handler froze prod. Both collapsed the moment someone checked the actual artifact. **The
correction is not "think harder", it is "go look at the thing."**

---

## DEC-0037 — A retrospective correction must propagate to every derived field

**Date:** 2026-07-13 (S37) · **Status:** Accepted · **Extends** DEC-0032

**Context.** DEC-0032 established *how* to correct a known-bad observation (correct to the known value,
flag it in-band). It did not say **how far** a correction must travel. ERR-0001 corrected the primary
rain fields for the 2026-07-04 phantom and stopped there. Eight days later the dashboard's S70 handoff
reported that `max(dayRain_in)` still read **1.84″** against a corrected `sum(rain_in)` of **0.56″** —
the phantom, intact, in an infinite-retention bucket, in the field a reader would most naturally reach
for as "the daily rain total."

Auditing the rest found it was **worse than reported**: `rain24_in` was also 1.84″, and `hourRain_in` was
1.28″ — *entirely* phantom. One report, three wrong fields.

**Why it happened.** Cumulative and rolling fields **do not self-heal**. A running total absorbs a bad
increment permanently. And these fields are invisible from inside this repo: they are not in our archive
schema and not produced by our driver — weewx derives them via XTypes and the uploader freezes the
result into InfluxDB. Correcting the source column does nothing to the snapshots already written.

**Decision.** A retrospective correction to a primary observation is **not complete** until every field
derived from it has been recomputed over every affected window.

1. **Enumerate the derived fields before declaring a correction done.** For rain that is `dayRain`,
   `rain24`, `hourRain` — and the list is schema-dependent, so *look*, do not recall.
2. **Recompute from the system of record** (the SQLite archive), not from the derived store. Verify the
   two agree on the primary field first — we confirmed `sum(rain) = 0.56` in both before touching
   anything.
3. **Rewrite over a window wide enough for the longest rolling lookback** (here: local-day + 24 h + 1 h →
   a 30-hour window), overwriting in place (same measurement, tags and timestamps) so no duplicate series
   is created. The operation must be **idempotent**: rewriting a correct value over a correct value is a
   no-op, so it can be safely re-run.
4. **A `*_qc` flag on the primary field under-reports the blast radius.** It says "this value was
   corrected"; a reader reasonably infers the whole record at that timestamp is clean. It was not. Until
   we have a better convention, the errata entry carries the full extent.

**Credit where due:** the dashboard found this and, per their DEC-0096, deliberately did **not** patch our
store — they display corrections, they never author them. That boundary is right, and it is why the bug
came back to us as a report instead of a silent divergence between two stores.

---

## DEC-0038 — An image tag denotes exactly one tree: publish v2.0.5, do not rebuild "v2.0.4"

**Date:** 2026-07-13 (S38) · **Status:** Accepted
**Extends:** DEC-0031 (the driver is baked), DEC-0034 (state the fork honestly).

**Context.** S37's handoff said: promote **v2.0.4** to `main` and push it to Docker Hub, because the
published image still ships the **stock driver** to every downstream user (DEC-0031) and the
**console-handler freeze hazard** (DEC-0036).

Both true. But the `weatheredscientist/weewx-rtldavis:v2.0.4` image sitting on the NAS — the one prod
has been running since 2026-07-12 15:49 — was **built at 15:44 that afternoon**, roughly eight hours
*before* the freeze began at 23:53 and long before DEC-0036 existed. It therefore does **not** contain
the `logging.additions` console-handler fix, and it does not contain DEC-0034's identity strings
either. **Publishing that image as-is would have shipped an artifact that fails the very acceptance
criterion the release was cut for.** A rebuild was mandatory in any case.

Given a rebuild is mandatory, the only real question is what to *call* it.

**Decision.** Publish the rebuilt image as **`v2.0.5`**, not as a second, different `v2.0.4`.

**A version tag must denote exactly one tree.** Had we rebuilt and republished `v2.0.4`, the string
"v2.0.4" would have named two different images: the one prod runs (`dff97719b629`) and the one on
Docker Hub (`939e949cbb28`). That is not a naming nit — **it is the same failure mode as DEC-0031 and
DEC-0034**, which this release exists to fix: *an artifact that asserts one thing and is another.* We
would have been fixing "the image lies about its driver" by shipping "the tag lies about its image."

`v2.0.4` was never published to Docker Hub (Hub went `v2.0.3` → `latest`, both 2026-07-08), so nothing
public breaks and no downstream `docker pull` is invalidated. The cost is internal bookkeeping only.

**Consequences — and one deliberate, documented drift.**

- Docker Hub now carries **`v2.0.5` + `latest`** (pushed 2026-07-13 12:55). Every new install gets the
  patched driver **and** the freeze fix. This is the item that had an ongoing external cost, and it is
  now closed.
- **Prod still runs `:v2.0.4`, and `prod-baseline` has NOT been moved.** This breaks DEC-0011's
  *`main` = production truth* invariant, knowingly and temporarily, and the alternative was worse:
  redeploying prod unattended, in a background session, hours after a seven-hour outage, to fix
  something that **does not affect prod**. The delta is behaviorally nil here — v2.0.5 = v2.0.4 + the
  console-handler default + identity strings, and prod's bind-mounted `weewx.conf` has **no console
  handler at all**, which is the config drift that spared us in the first place. The freeze fix
  protects *downstream users*, who have no such drift.
- **A catch-up deploy of `:v2.0.5` to prod is owed**, in an attended window, with `:v2.0.4` as the
  rollback. `prod-baseline` moves then, not before. Recorded in STATUS.
- Do not let this become a habit. "Published is ahead of prod" is acceptable for exactly as long as it
  takes to schedule one deploy.

---

## DEC-0039 — Every allow term is anchored or positioned; a gate ships with its planted-payload test

**Date:** 2026-07-13 (S38) · **Status:** Accepted
**Extends:** DEC-0012 (never commit secrets). **Adopts + strengthens:** dashboard DEC-0063, DEC-0100.

**Context.** `scripts/check_secrets.sh` guarded this **public** repo for nine sessions while catching
essentially nothing. S36 found the cause (`grep -viE` — a case-insensitive allow-list whose `[A-Z]`
terms matched lowercase code, so the ALL_CAPS rule swallowed nearly every unquoted secret) and fixed
it. The dashboard found the identical bug independently (their DEC-0063), then found five more holes
in the same class (DEC-0100), then we found more here. **Four separate discoveries of one bug class,
each re-derived from scratch.**

**The bug class, stated once:**

> **An allow term that can match ANYWHERE on the line is not an allow-list, it is an escape hatch —
> the secret sits on the left and the excuse on the right.**

```
token = REAL   # falls back to os.environ      <-- old gate: PASSED, exit 0
```

*(The value is stubbed to four characters on purpose. With a realistic 8+ character value, this very
line trips the hardened gate — as it did while this entry was being written. The realistic payloads
live in `scripts/test_check_secrets.sh`, the one file the gate exempts, by exact path.)*

**Decision.**

1. **Every allow term must be ANCHORED** (`^[[:space:]]*#`, `^[[:space:]]*//` — the line *is* a
   comment) **or POSITIONED** (it must appear as the value of, or in key position to, *the key the
   detector actually matched*). There are now **no free-floating terms**. A new term that can match
   mid-line re-opens the hole; that is the first thing to check when adding one.
2. **The `grep -n` prefix bug is fixed at the root, not compensated for.** The old gate piped `grep -n`
   output into its allow-list, so every line arrived prefixed `N:` — and a rule keyed on a colon
   matched *that* prefix instead of the code. The anchors had to compensate (`^[0-9]+:`), which is
   fragile and is exactly why the dashboard warns against porting our anchors verbatim. The line number
   is now stripped with **bash parameter expansion**, and the allow-list runs on the **raw line**.
3. **A gate ships with its planted-payload test.** `scripts/test_check_secrets.sh` plants 13 known-bad
   payloads (each MUST be caught), 14 known-good lines (each MUST pass), and re-runs the real gate over
   the whole tracked tree (MUST be clean). **It runs in CI, before the scan itself.**
4. **A green exit code is not evidence.** Two repos believed it for months. Evidence is a payload the
   gate catches and a tree it does not flag.
5. **Port the test, never the regex.** The dashboard's gate runs on raw lines; ours used to run on
   `grep -n` output; theirs needs JS comment forms, ours needs weewx config plumbing. The gates are
   legitimately different. **The test is the contract; the gate is the implementation** — which is
   PRINCIPLES §1 (*the contract is the data, not the consumer*) pointed at tooling.

**Evidence it works.** The harness caught a hole **in the S38 fix itself, while it was being written**:
the first cut of the prose rule began `[A-Za-z]:` — any letter, any colon, anywhere — so a secret with
a trailing `# Authorization: Bearer …` comment still passed, the excuse on the right rescuing the
secret on the left. That is the whole argument for rule 3 in one line. Final state: **28 passed,
0 failed**; 72 tracked files, zero false positives.

It then caught **this very ADR**, which originally quoted its payloads at full length. Docs describe
the *shape*; only `scripts/test_check_secrets.sh` carries realistic payloads, and it is exempt by
exact path. That is the system working, and it is why the exemption is a path and never a pattern.

**Reciprocal finding, sent back to the dashboard.** Applying their own DEC-0100 rule strictly, *their*
hardened gate still has free-floating escape hatches (`YOUR_`, `process.env`, `os.environ`, `getenv`,
`config_dict`, `.get(`, `argv`), so a real credential with a trailing `# falls back to process.env`
comment still leaks past it with exit 0 — payloads 8–12 of our harness. Handed over in
`docs/handoffs/S38-cross-repo-architecture.md`, with the same warning they gave us: **do not port our
regex verbatim.**

---

## DEC-0040 — The cross-repo gap is an ENFORCEMENT gap, not a documentation gap: no master repo (yet)

**Date:** 2026-07-13 (S38) · **Status:** Accepted (recommendation; owner to confirm moves 1 and 3)
**Answers:** the open architectural question recorded in `S37-to-all-projects-stdout-freeze.md`.

**Context.** Three shared assets have each now caused a cross-repo incident: the NAS Docker daemon
(DEC-0036, a 7h18m outage), the driver-vs-image mismatch (DEC-0031), and the secret gate (green-but-
blind in *both* repos, independently). None belongs to any one repo, and no repo's session-start read
covers the gap between them. The options tabled were: a shared `ops/` repo, a vendored CONVENTIONS
fragment, or status quo plus handoff docs.

**The reframe.** All three options are strategies for **distributing documentation**, and all three
would have failed to prevent all three incidents — because in the worst of them, *the rule was already
written down*. "`docker logs` always with `--tail N`" was in `CLAUDE.md` **and** `CONVENTIONS.md`
before the freeze. It was followed for thirty-odd sessions and broken once, and that once cost seven
hours.

> **Prose does not execute.** A rule in a document is enforced by whoever happened to read it and
> happened to remember it at the moment they typed the command. That is not a control; it is a hope.

What actually resolved the other two was, in both cases, **someone writing an executable check**: the
duplicate-frame question stood open four sessions and fell in an afternoon to
`ops/find_duplicate_frames.py` (DEC-0035); the secret gate was trusted for nine sessions and its holes
fell in twenty minutes to a planted-payload test (DEC-0039). The one incident still **mechanism-open**
is the one still without a mechanical guard.

**Decision. No master coordination repo. Build a shared enforcement layer instead.**

1. **Mechanical guards belong in `~/.claude/` (global, cross-project, zero session-boot cost).** It has
   no hooks today. A `PreToolUse` hook blocking bare `docker logs` (DEC-0036) and `docker stop`
   (DEC-0008) is the *only* candidate mechanism that would have prevented the freeze. Plus a `.zshrc`
   guard, because a Claude hook only guards the agent and we never established who ran the command.
2. **Share the test, not the regex** (see DEC-0039 §5).
3. **The NAS runtime contract is the one genuinely unowned thing** — and it is one page, not a repo.
   Verified this session: **all four** production containers run with `LogConfig.Config = map[]` — no
   `max-size`, no `max-file`, no caps of any kind — on Synology's **`db`** driver, which is the exact
   component that wedged.

   **And the `db` driver cannot be capped at all.** Tested: a container run with
   `--log-opt max-size=1m` emitted 200,000 lines (~10 MB) and **all 200,000 remained retrievable**; a
   cap would have left ~20,000. Confirmed against the literature — `db` is a **proprietary Synology
   driver**, not a Docker one, with no published options: *"the `max-size` option is not supported by
   this custom Synology db driver."* It is not undocumented, it is **unsupported**. This also corrects
   the S37 handoff, whose `--log-opt max-size` advice names **`json-file`** options.

   **Third instance in one session of the same meta-failure:** an interface that **accepts an
   instruction and discards it** — after the secret gate's green exit code (DEC-0039) and the compose
   file's silent driver clobber (DEC-0031). *"It was accepted"* is not evidence that it does anything.
   That pattern, not any individual bug, is what this decision exists to make expensive.

   **Bonus finding, which upgrades DEC-0036 from inference to demonstration:** retrieving that
   200k-line log **hung for over three minutes** — and that was a `--tail`-bounded read. The `db`
   driver's pathological slowness on a large `log.db` is real and reproducible. (Safely: throwaway
   container, per-container `log.db`, prod healthy throughout and verified after.)

   **Consequence:** the logging driver is a **per-container** choice. `json-file` + caps is the only
   way to bound a log here, and it costs the DSM Container Manager log tab for that container
   (confirmed, not speculative). So bound only the containers that actually generate volume — a fact
   that needs `sudo du` on each `log.db` and is **not yet known**. weewx itself is no longer a
   candidate: v2.0.5 put its console handler at `WARNING`, so it has almost nothing to write.

4. **Branch protection is part of the enforcement layer, and it has two holes, not one.**
   `enforce_admins: true` is now set on `main` and `dev` (required checks: `secret-scan`, `lint`,
   `tests`), closing the S36 bypass — for everyone, including the owner. But that does **nothing** for
   the way S37 was lost: an entire session's work sat in a **draft** PR, CI green, branch pushed, and
   simply never merged; it was found a day later by accident. A draft PR is invisible to every check
   that exists. The `SessionStart` hook (`~/.claude/hooks/eaglehunt-status.sh`) closes that one by
   reporting drafts, stranded branches and uncommitted work **across all three repos** at every session
   start. On its first run it immediately surfaced a live stranded draft in the *dashboard* (#22) that
   nobody knew about — which is precisely the "one project unaware of another's actions" the owner
   named as the real problem.

**Alternatives rejected.**
*(a) A shared `eaglehunt-ops` repo.* Its real benefit is discoverability for a **new** project, and
that benefit accrues only when there is someone to discover it, while the costs — a fourth
session-start read, a two-PR dance for any cross-cutting change — are paid every session, in three
repos that just spent three sessions deliberately **cutting** boot cost (DEC-0030 / dash DEC-0081 /
HLF DEC-0095). Two shared artifacts do not justify it for a solo operator. **Build it on a trigger:** a
fourth NAS service, a second operator, a third shared *executable*, or the second time the same fix is
hand-pasted into three repos.
*(b) A vendored CONVENTIONS fragment.* **Drift is the bug** — DEC-0031 is drift (compose vs.
Dockerfile), the secret gate is drift (two copies, one bug, four discoveries). An unchecked vendored
copy is the same failure with extra steps. Acceptable only with a mechanical drift check — at which
point you have built the enforcement layer and the fragment is redundant.
*(c) Status quo + handoffs.* **Kept, but only for lessons** — narrative, causal, one-directional —
where it demonstrably works (the S37 handoff did its job; it is why this decision exists). It is the
wrong mechanism for **rules**, because a rule delivered as prose is a rule enforced by memory, and
memory is what failed at 23:53 on 2026-07-12.

---

## DEC-0041 — StdPrint is removed: the console-handler fix was necessary but NOT sufficient

**Date:** 2026-07-13 (S38) · **Status:** Accepted
**Completes:** DEC-0036 (the 7h18m freeze). **Corrects an overclaim made in DEC-0038 / v2.0.5.**

**Context.** DEC-0036 identified the freeze mechanism: a container's stdout is a **pipe** drained by the
Docker daemon. If that consumer stalls, the 64 KB buffer fills and the next write **blocks forever** —
a `write()` to a pipe has no timeout. weewx does not crash; it freezes mid-write, silently, with a
container still reporting `Up`. v2.0.5 responded by moving `logging.additions`' console handler from
`INFO` to `WARNING`, on the theory that this made weewx's stdout nearly silent.

**It did not, and I said it did.** Chasing the *actual* `log.db` sizes on the NAS (which required root,
so it had not been checked) showed `weewx-rtldavis-v2` had accumulated **15 MB in ~14 hours**. The
writer was not the logging subsystem at all:

```
report_services = weewx.engine.StdPrint
```

**`StdPrint` `print()`s every LOOP packet straight to stdout.** It does not go through the `logging`
module, so **no log level touches it** — the console handler could be at `CRITICAL` and StdPrint would
still write a line per loop packet, ~0.6/s, roughly **25 MB/day**, directly into the pipe that froze us.
The v2.0.5 fix closed a door while the larger one stood open.

It is enabled in **weewx's own stock defaults**, so it was in the baked image config *and* in our
`weewx.conf.example` — meaning **every downstream user** had it too. And our example was the worst of
both worlds: it commented out `StdReport` while leaving `StdPrint` on, so users got no reports *and* a
stdout flood.

**Decision. Remove `StdPrint` everywhere.**

1. **Prod** — `report_services =` (empty) in the live `weewx.conf`; restarted (`kill`, not `stop` —
   DEC-0008). Verified after: **stdout growth 0 lines/60 s** (was ~36), archive/upload traffic
   unaffected, `Influx: Published record` continuing, `RestartCount: 0`.
2. **The image** — a `RUN sed` strips `StdPrint` from the baked default config, **with a `grep`
   assertion that fails the build if the substitution does not apply.** A config edit that silently
   no-ops is the exact failure this session kept finding; the build must not be able to ship it.
3. **`weewx.conf.example`** — `report_services =` with a comment explaining *why*, so a user does not
   helpfully "fix" it back.
4. Shipped as **v2.0.6**.

**It buys nothing in a container.** Nothing reads container stdout — we read the rotating log *file*,
and so does `weewx_monitor.py` (which is what actually detected the outage). StdPrint exists to watch
packets scroll by in a terminal. In a daemonized container it is pure hazard.

**The lesson, which is the session's lesson again.** The mitigation was reasoned about from the
architecture (*"the console handler writes to stdout, so lower its level"*) instead of **measured at the
source** (*"what is actually in the pipe?"*). One `sudo du` would have shown 15 MB and prompted the
question. **We fixed the writer we knew about, and shipped a release claiming the hazard was closed.**

**Consequence:** v2.0.5's release notes and DEC-0038 overstate the fix. They are **not rewritten** —
this entry supersedes them, per the append-only rule (DEC-0030). v2.0.5 is not *wrong*, it is
*incomplete*: the console handler genuinely was a hazard for users who route logging there. It simply
was not the biggest one.

**Related, found in the same sweep (not yet acted on):**
- The **largest `log.db` on the NAS (47 MB) belonged to `/weewx`, a container exited since 2026-05-04.**
  Dead containers keep their log store forever. Removed.
- **Prod's bind-mounted `influx.py` has drifted from the repo's** (md5 `8b0d05b3` vs `5f58c204`). The
  running copy still carries `VERSION = "0.20"`, the unconditional `ssl._create_unverified_context()`,
  and the per-record `loginf` calls. **Not a live exposure** — the endpoint is
  `http://influxdb:8086`, so the TLS branch is never taken — but it is the DEC-0031 class again, and
  `influx.py` *is* bind-mounted, so an `scp` is the correct deploy for it. **Owner decision pending.**

---

## DEC-0042 — The phantom rainRate is an ISS-side sensor artifact, not an RF or driver bug

**Date:** 2026-07-13 (S38) · **Status:** Accepted — *ISS-side is established; the condensation mechanism
is the best explanation and is testable*
**Closes:** the rainRate thread open since S36. **Bounds:** DEC-0033/DEC-0035 (which explain the rain
*counter*, and do **not** explain the rate).

**Context.** Two phantom rain events (ERR-0001, ERR-0002) each produced a phantom rain *rate* — peaks
4.736 / 4.216 in/hr — with `rain = 0.0` throughout. The counter glitch was explained (CRC-valid corrupted
duplicate frames, DEC-0033/0035). The rate was not: a single corrupt packet gives ONE bad reading, yet we
saw ~16 minutes of a *stable* rate. STATUS carried it as "the best lead we have."

**What settled it.** The archive was corrected in S36, so the originals were gone from the live DB — but
a **2026-05-29 backup predates the correction** and covers ERR-0002. Reconstructing the raw
`time_between_tips` from the stored `rainRate` (`t = 36 / rate_in_hr`):

| fact | value |
|---|---|
| real rain that entire UTC day | **none** — the whole 1.280″ day total *is* the phantom |
| rate window | 03:22 → 03:37 UTC, **sharp on, sharp off** — the ISS's ~15-min rain-rate timeout, exactly |
| implied tip interval across the window | tight band, **8.5 – 10.0 s** — physically coherent, not garbage |
| **tip counter during those 16 min** | **never advanced** — `rain = 0.0000` in *all sixteen* records |
| conditions | **94 % RH, 1.7 °F dewpoint spread, 0.0 mph wind**, slowly cooling. Both events overnight. |

**The decisive argument.** The "no rain" sentinel is `0x3FF`
(`time_between_tips_raw = ((pkt[4] & 0x30) << 4) + pkt[3]`). The observed raw values are ~136–160.
Getting from one to the other requires **~6 bit-flips — in every packet, for sixteen consecutive
minutes.** RF corruption cannot do that: a corrupted duplicate frame yields *one* bad packet, not a
coherent 16-minute stream. **The ISS genuinely transmitted those values.** The decode is stateless
(`data['rain_rate']` is computed fresh per packet, no caching), so it is not our driver either.

**Decision.** The phantom rainRate is an **ISS-side sensor artifact**. It is not in the RF path, not in
the demodulator, and not in the driver. **No decode-layer filter will fix it**, and we should stop
looking for one — `rain_delta_tips` guards the counter and does nothing here, by design.

**Mechanism (best explanation, testable).** The rate register and the tip counter are driven by the same
reed switch. Something fired the rate path without completing a counted tip. Given the conditions —
saturated, dead calm, radiating heat away — **condensation trips the reed switch often enough to start
the rate timer, but never enough water accumulates to actually tip the bucket.** Rate set, counter
untouched, which is precisely what the data shows. Dead-calm wind also rules out vibration.

**Consequences.**
1. **A third event is predictable:** expect it on a calm, saturated, cooling night. That is a falsifiable
   claim, and the cheapest possible test.
2. **The next step is physical, not software** — inspect the tipping bucket, the reed switch and its
   wiring (debris, webs, corrosion, a bucket that rocks without completing a tip).
3. **The confirming capture is now safe to run.** Logging raw type-5 bytes + the raw counter whenever the
   rate is non-sentinel was previously refused because leaving prod at DEBUG fed the stdout pipe. **That
   trap is gone** (DEC-0041 removed StdPrint; the console handler is at `WARNING`; debug goes to the
   rotating *file*). ~1 hour to build, negligible log volume, can run indefinitely.
4. **Told upstream.** The issue-#15 draft now says the rate is ISS-side — useful to that thread, where
   three people have been hunting it in software.

**Method note, worth keeping.** This was answered in half an hour from **data we already had**, because
a backup happened to predate our own correction. DEC-0025 (*preserve and flag, never delete*) is why the
evidence existed at all — but the live rows had been overwritten in place (DEC-0032), and only luck
supplied a pre-correction copy. **Snapshot the affected rows before a retrospective correction, not
after.**

**Challenged and upheld (S48, issue #48).** A dashboard-side reconciliation (their S76) found that
WeatherLink's install-to-date total only balances against our archive if the console **excludes** the
2.56″ of phantom rain we corrected — and asked whether that undercuts an ISS-side mechanism, since a
real physical tip is broadcast to every listener. **It does not.** The challenge conflates the two
phantom classes, which this repo's own data model already separates into two independent flags
(INTERFACES §2): the 2.56″ is **`rain_qc` (3 points)** — the *counter*, which DEC-0042 explicitly
disclaims and DEC-0021/0033/0035 own — while DEC-0042 governs **`rainRate_qc` (33 points)**, decoded
from a different ISS message (type 0x5 vs 0xE) and carrying `rain = 0.0` in every one of those 33
records. The rate events contributed **exactly 0″** to any accumulation, ours or the console's.

Both classes independently *require* the console's absence, so the reconciliation is confirmatory:
(1) the counter phantoms are receiver/driver-side — ERR-0001 is our own wraparound handler adding 128
to a logged `rain_count=-64`, and ERR-0002 is a bit-7 flip passing CRC — both strictly downstream of
the shared broadcast, so a console decoding its own copy with its own firmware could never reproduce
them; (2) DEC-0042's mechanism *predicts no tip at all* ("rate set, counter untouched"), so there was
never a tip for the console to count. Per INTERFACES §4 the WeatherLink console is our designated
ground truth for **"did the bucket actually tip"** — and it says no, which is what DEC-0042 claims.

Net: the reconciliation is **independent external validation that the 2.56″ correction was right**
(residual 0.01″ against ERA5 + measured capture gaps), not evidence against the mechanism. No revision
warranted; do not re-litigate.

---

## DEC-0043 — Override the ROOT logger, not just `weewx` and `user` (S39)

**Status:** Accepted · **completes** DEC-0036 / DEC-0041 · 2026-07-13 (S39)

**Context.** A routine post-deploy health check on `:v2.0.6` found the container emitting **15
logging-error tracebacks (~515 lines) to stderr on every start**. Steady state was clean — 0 lines
in 90 s, so DEC-0041's StdPrint removal genuinely holds — but every start dumped a wall of
`FileNotFoundError: /dev/log` at anyone running `docker logs`.

**Root cause.** weewx's own defaults (`weeutil/logger.py`, `LOGGING_STR`) set:

```
    [[root]]
      level = {log_level}
      handlers = syslog,
```

with `address = /dev/log` on Linux. **There is no syslog daemon in a container.** Our
`logging.additions` overrode the `weewx` and `user` loggers (giving them their own handlers and
`propagate = 0`), so those were always safe — but `weewxd` and `weeutil.*` are in **neither**
namespace. They fall through to root, hit the syslog handler, and `SysLogHandler.emit()` raises;
Python's logging module then prints the whole traceback to stderr.

**The quieter half, which matters more.** Those records were not merely noisy — they were **lost**.
`weewx.log` has **never** contained a single `weewxd` or `weeutil` line: not the version banner, not
the config path, not the group list. They only ever went to the handler that was failing. We had been
running without startup diagnostics and had not noticed, because the failure announced itself on a
stream nobody reads.

**Decision.** Add a `[[root]]` override to `logging.additions` (baked image: `rotate, console`) and
to `weewx.conf.example` (`rotate` — it defines no console handler). A **build-time assertion** fails
the image build if `[[root]]` is absent from the baked config, in the same spirit as DEC-0041's.

**Verified, not assumed** — A/B in the real container, as a separate process:

| Config | root handlers | Result |
|---|---|---|
| without `[[root]]` (prod today) | `SysLogHandler` | traceback reproduced exactly |
| with `[[root]]` (the fix) | `TimedRotatingFileHandler` | no traceback; `weewxd INFO Starting up weewx version 5.4.0` **lands in the file** |

**Consequences.** Not a freeze hazard: the burst is bounded (~515 lines/start) and steady state stays
at 0, so this never threatened DEC-0036's pipe. It is a *downstream* fix — every user of the
published image sees the tracebacks on first `docker run` — and an *observability* fix for us. Ships
in **v2.0.7**.

**The pattern, stated once.** Overriding a child logger does not protect you from a bad handler on
its parent. `propagate = 0` on `weewx` and `user` made those two namespaces safe and left every
*other* logger in the process still pointed at the broken handler — which is why the bug was
invisible for the entire life of the image.

---

## DEC-0044 — The nibble theory is not supported by the archive, and the archive can never settle it: instrument, don't filter (S39)

**Status:** Accepted · **bounds** DEC-0029 · **parks** the temp/humidity coupling filter · 2026-07-13 (S39)

**Context.** The S39 backlog carried a "cross-sensor consistency filter" inherited from dashboard S69:
*a humidity move >6 %/min with temperature essentially flat is physically impossible*, reported as
3-for-3 on the bad events with 0 false positives. Behind it sat an unproven mechanism — the **nibble
theory**: the ISS message-type nibble (`pkt[0] >> 4`) suffers a bit flip, so **another sensor's
payload is decoded as humidity**. S69 proposed a falsifiable arithmetic test, started a raw capture,
and never finished; the theory was recorded as "under investigation" and the statistical filter became
the plan. S39 ran the test.

**Finding 1 — the theory's own arithmetic does not fit its story.** Humidity is type `0xA` = `1010`.
Its **single-bit-flip neighbours are `0x2` (supercap), `0x8` (temperature), `0xB` (undefined) and
`0xE` (rain counter)**. Solar (`0x6`) is **two** bits away; UV (`0x4`) is **three**. S69's "why always
midday? — a misdecoded solar/UV payload" is therefore *not reachable by a single bit flip*, which was
the theory's central claim.

**Finding 2 — every testable variant fails.** Each type reads the same `pkt[3]`/`pkt[4]`, so a bogus
humidity value pins those bytes and the re-decode is exact arithmetic, not a guess:

| Candidate | Decode from the bogus RH | Verdict |
|---|---|---|
| UV (`0x4`) | `sr_raw / 50` | **Dead** — implied UV ≈ 2× actual on *every* spike |
| Temperature (`0x8`) | `((pkt3 << 4) + p4hi) / 10` | **Dead** — implied 200–400 °F |
| Solar (`0x6`) | `sr_raw * 1.757936` | **Not supported** — see below |
| Supercap (`0x2`) | `sr_raw / 300` | Fails where testable; `supplyVoltage` null at nearly every spike |

**Finding 3 — the solar "match" was fitted noise, and a control proves it.** The archive stores
1-minute *averages*, so recovering the raw bogus reading needs `raw = n·spike − (n−1)·baseline` with
`n` (readings/minute) **unknown**. Letting `n` range over {1,2,3} produced 12/28 hits within ±10 % —
but the winning `n` came out uniformly **{1:4, 2:4, 3:4}**, the signature of a meaningless parameter.
Scored against **2000 shuffled pairings** (each spike's implied solar vs some *other* spike's actual
radiation): true 12/28 (43 %) vs shuffled mean 9.9 (35 %), **p = 0.248**. The real pairing does not
beat chance.

**Finding 4 — this is structural, not a failure of effort.** The free parameter `n` *is* the thing
that manufactures false matches, and it exists only because the archive averages. **No analysis of
1-minute archive data can settle the nibble theory.** Neither can InfluxDB: it stores the same
1-minute records (verified — bucket `weewx`, retention infinite, timestamps on the minute).

**Decision.**

1. **Do not build the coupling filter.** Its premise does not survive the data twice over. "Temperature
   essentially flat" describes **90 % of all minutes** (66,743 of 74,538 samples at |ΔT| ≤ 0.1 °F), so
   the flatness test carries almost no discriminating power — the humidity rate does nearly all the
   work. And every spike large enough to see in the archive (8–12 %RH/min, implying a **raw** glitch of
   16–37 %RH) is **already rejected by DEC-0029's existing 10 %RH-per-reading cap**. The filter would
   have targeted a residual we have not shown exists, using a threshold we could not honestly derive.
   *The direction of the S69 insight is right* — mean |ΔRH| does climb with |ΔT| (0.29 → 0.44 → 0.82 →
   1.1 → 1.32 → 1.66), exactly as physics predicts, and every jump above 8 %/min occurs only in
   flat-temp bands. It is the *discriminator* that is not there.
2. **Instrument instead.** Enable **`log_humidity_raw`** — an option that **already exists upstream**
   (`rtldavis.py`, Luc Heijst's modification) and logs `(pkt[4] << 8) + pkt[3]`: **both payload bytes,
   in full**. With real `pkt[4]` there is no averaging and no free parameter, and the inversion becomes
   deterministic. It is a config flag, not a code change, and it emits at INFO to the *file* handler —
   prod's `weewx.conf` has no console handler, so it adds **nothing** to stdout and carries no DEC-0036
   risk.
3. **Correct the record.** The 2026-05-23 "gust front" cited as the filter's key
   false-positive test shows a **maximum humidity move of 1.0 %/min** in our archive (90 %RH, 50 °F,
   wind ≤ 2.5 mph — a calm, saturated day). It would be spared by *any* threshold. It was never
   evidence.

**Consequences.** The spike mechanism is **open** and stays open — honestly. DEC-0029's filter keeps
catching the large glitches at the source, which is what protects the data today. The next midday
spike, with `log_humidity_raw` armed, settles the question deterministically.

**The pattern, stated once.** *A statistical filter is what you build when you have given up on the
mechanism.* Before shipping one, check whether the decisive instrument is already sitting in the code
— here it was, an upstream option nobody had switched on. And when a remembered constant arrives from
another repo's session ("6 %/min, 3-for-3"), **re-derive it against your own data before you build on
it**: both the threshold and its headline test evaporated on contact.

---

## DEC-0045 — A comment is not an exemption: the secret gate scans comments like code (S40)

**Status:** Accepted · **amends** DEC-0039 (which certified the hole) · **extends** DEC-0012 · 2026-07-13 (S40)

**Context.** `scripts/check_secrets.sh` is the only thing standing between a credential and a **public**
repo. Since it was written it carried an `ALLOW (1)`: *if the whole line is a comment (`#`, `//`,
`/* */`, ` *`), allow it.* So this shipped clean:

    # api_key = <a real credential>

**In a public repo a commented-out credential is still a leaked credential.** `git push` does not strip
comments; neither does anyone reading the file on GitHub. Commenting a line out is precisely what a
person does with a secret they are "not using right now" — which is exactly when it gets committed.

**What makes this DEC necessary rather than a bug fix.** The rule was not an oversight that slipped past
the test. **The test asserted it.** `scripts/test_check_secrets.sh` listed, under *"must PASS"*, a
commented Python assignment of a real-looking API key and a commented JS assignment of a real-looking
token — both with literal 8+ character values, both marked *"comment-only line"*. (They are now BAD
payloads 15 and 16 in that file; per point 3 below, the literals live **there**, not here.)

Those two lines were part of DEC-0039's celebrated **"28/28 planted payloads, proven"**. The gate did not
merely have a blind spot — **its proof certified the blind spot.** DEC-0039's own thesis is *"a green exit
code is not evidence."* S40's correction: **a passing test is not evidence either, if the assertion is
wrong.** A test encodes a judgement about what *ought* to happen, and that judgement is as fallible as the
code. It is the fourth member of the family this repo keeps meeting — an interface that accepts an
instruction and silently discards it (DEC-0031's bind-mount, DEC-0036's `max-size`, DEC-0040's prose).

**Decision.**

1. **`ALLOW (1)` is deleted.** There is no comment rule. Comments are scanned exactly like code.
2. **A comment earns no exemption; only its VALUE can.** `# api_key = YOUR_API_KEY_HERE`,
   `# token = "${INFLUX_TOKEN}"` and `# token: InfluxDB 2.x Authorization Token` still pass — via the
   placeholder / interpolation / prose rules, which test the value. Commenting a line out does not change
   the verdict **in either direction**.
3. **No new exemptions were added.** The gate's own header had illustrated three past bugs with six
   real-looking credential literals, which the fix would now flag. The tempting move was
   to exempt `check_secrets.sh` by path, as `test_check_secrets.sh` already is. **Rejected** — that is a
   130-line blind spot in the one file that most needs scanning. Instead the literals **moved into
   `test_check_secrets.sh`, where they execute as planted payloads**, and the header now points at them.
   This is DEC-0040 applied to the gate itself: *prose does not execute.* The gate scans 100 % of tracked
   files, including its own source.

**Evidence (the whole point of DEC-0039 — a green run proves nothing on its own).**

| Check | Result |
|---|---|
| Blast radius of deleting `ALLOW (1)` over the whole tracked tree | **6 hits, all inside the gate's own header comments.** Every legitimate comment elsewhere (README's `YOUR_*` blocks, `influx.py`'s docstring, the handoff docs) already passed on its *value*. The exemption was doing **no legitimate work in this repo** — it was close to pure hole. |
| Planted-payload suite | **41 passed, 0 failed** (was 28). 7 new BAD payloads: every comment marker form (`#`, `//`, `/* */`, ` *`, indented, no-spaces) plus a commented `self.x = x`. 6 new GOOD payloads: the same placeholder/prose/empty values wearing a comment marker. |
| **Mutation test** — re-add `ALLOW (1)` | Suite goes **red: 7 LEAKED**. The fix is load-bearing; the test can actually fail. |
| **Full-history scan** — every blob that ever existed (333 unique, all refs) for a commented credential | **0.** Positive-controlled: the same scan with the gate's own files re-included finds the 11 known header examples, so the scanner demonstrably sees things. |
| **The ADR you are reading** | The first draft quoted the planted payloads verbatim, and **the new gate blocked this file** — 4 hits. Working as designed. The literals were removed rather than exempted, which is the same call as point 3, made a second time under real pressure. If a doc needs to *show* a credential shape, it has one correct home: the test. |

**Consequences.**

- **The hole was never exploited.** Nothing needs revoking, and no history rewrite is warranted. This is
  prophylactic. (The separately-tracked WU API key exposure is a *different* incident, still owed a
  rotation, and was never a comment.)
- A commented-out constructor line (`self.<field> = <field>` plumbing) is now **caught**. The `self.` rule
  stays anchored to line start and was deliberately **not** widened to tolerate a comment marker. The fix
  for a hit is to delete the dead comment — which is the right thing to do with it anyway.
- The `key: value` docstring style (`influx.py`) and the README's `YOUR_*` config blocks are unaffected —
  verified, not assumed.
- **Do not re-add a marker-based exemption.** It is bug class 4 in the gate's header, and the test now
  encodes it in both directions.

**The pattern, stated once.** *We proved the gate, and the proof was wrong.* A test is a claim about what
should happen; writing one does not make the claim true. When a test asserts that something dangerous is
fine, it converts a bug into a **certified** bug — and the green checkmark then actively defends it. So
when you add a case to a security test, the question is not "does it pass?" but **"which array does it
belong in, and why?"** That judgement *is* the gate. The code is just how it is enforced.

---

## DEC-0046 — The baked config is shadowed by the prod bind-mount: an image-only config fix never reaches prod (S41)

**Status:** Accepted · **mirrors** DEC-0031 · **completes the delivery half of** DEC-0043 · 2026-07-13 (S41)

**Context.** DEC-0043 fixed the root-logger defect by adding a `[[root]]` override to the two configs the
repo ships: `logging.additions` (concatenated into the image's baked `/opt/weewx-data/weewx.conf`) and
`weewx.conf.example`. A build-time assertion in the `Dockerfile` guarantees the baked config carries it,
so an image *cannot* be built without the fix. S41 released that image as `:v2.0.7`.

**Prod does not read the baked config.** The production container bind-mounts

    /volume1/docker/weewx-rtldavis/weewx-data  ->  /opt/weewx-data

The mount covers the *entire directory*, so the live `weewx.conf` **shadows the baked one completely**.
The baked config — assertion and all — is inert in prod. It exists on disk under the mount and is never
read.

**What this would have cost.** Deploying `:v2.0.7` and stopping there would have produced a release that
was, in prod, a **no-op with a green checkmark**: the image genuinely contains the fix, the build
assertion genuinely passed, the release notes genuinely describe the fix — and the station would have gone
on emitting syslog tracebacks and silently dropping every `weewxd`/`weeutil` startup line, exactly as
before. Nothing anywhere would have said "no". It was caught by a pre-flight `grep` of the live config,
which found **zero** `[[root]]` blocks.

**Decision.** A config-layer change has **two independent delivery paths**, and shipping one does not ship
the other:

1. **The baked config** (`logging.additions` → image). Reaches **downstream users** on `docker pull`.
   Delivered by an image rebuild. Cannot reach prod.
2. **The live bind-mounted `weewx.conf`** on the NAS. Reaches **prod** — and *only* prod. Delivered by
   editing that file on the NAS. Cannot reach downstream users, and is never committed (it holds live
   credentials; DEC-0012).

**Any release that changes shipped config MUST patch the live config in the same window, and verify the
behavior in prod** — not merely confirm the image contains the fix. S41 did both: the live conf gained the
`[[root]]` block (backed up first to `weewx.conf.bak-pre-v2.0.7`), and prod was verified behaviorally.

**Prod's `[[root]]` is not identical to the baked one, deliberately.** The baked config uses
`handlers = rotate, console,`; prod's uses `handlers = rotate,` — file only. Prod declares no console
handler at all, and adding one would pipe root records to stdout and re-arm the DEC-0036 freeze hazard
that DEC-0041 disarmed. **The two configs are allowed to differ; what must match is the *fix*, not the
text.**

**This is the exact mirror of DEC-0031, and that is the point.**

| | Wins in prod | The no-op trap |
|---|---|---|
| **The driver** (DEC-0031) | the **baked** venv copy | `scp`ing `rtldavis.py` to the NAS is silently ignored |
| **The config** (DEC-0046) | the **mounted** `weewx.conf` | rebuilding the image is silently ignored |

They are inverses, which is what makes the pair so easy to get backwards. Neither one errors. Both accept
the instruction and discard it. **For every file we ship, the question is not "did I change it?" but
"which layer actually wins in prod?"**

**The family this belongs to.** It is the fifth member of the pattern this repo keeps meeting: *an
interface that accepts an instruction and silently discards it.* DEC-0031's bind-mount over the driver,
DEC-0036's `max-size` on Synology's `db` log driver, DEC-0040's prose that does not execute, DEC-0045's
test that certified the hole — and now a bind-mount that shadows a config whose own build assertion had
just passed. **The assertion was not wrong. It was answering a question nobody was asking in prod.**

**Consequence for how we verify.** The verification criterion S39 wrote down — *`weewx.log` must now
contain `weewxd INFO Starting up weewx version 5.4.0`* — is behavioral, reads prod, and would have caught
this even if the pre-flight grep had not. **Post-deploy checks must observe the running system, never the
artifact.** An image check would have said PASS.

---

## DEC-0047 — The secret gate guards commits, not reads: the transcript is an egress path (S41)

**Status:** Accepted · **extends** DEC-0012 · **completes** DEC-0039/0045 (which hardened only the write
path) · **applies** DEC-0040 (prose does not execute) · 2026-07-13 (S41)

**The gap.** Every secret control in this repo is a **commit-time** control. DEC-0012: *the live
`weewx.conf` must never enter a commit.* `scripts/check_secrets.sh`: scans staged and tracked files. The
CI `secret-scan` job. The 41-payload proof suite (DEC-0039, DEC-0045). Four hardenings across S26 → S40.

**All of them guard the write path to GitHub. None of them has anything to say about reading.** Whatever a
tool prints is written to `~/.claude/projects/*.jsonl` in **plaintext on local disk** and **transmitted to
the model provider**. That is an egress path, and it had never been modeled as one.

The `.gitignore` entry actively feeds the blind spot: the live config is *deliberately* excluded from the
repo, which makes it feel handled. **"Not in the repo" is not "not in the transcript."**

DEC-0040 said *prose does not execute*. This is a level worse: **there was no prose.** No rule was broken,
because no rule existed.

**What surfaced it (S41).** Inspecting the live config during the v2.0.7 deploy:

    sed -n "/^\[Logging\]/,+44p" .../weewx-data/weewx.conf

A fixed **line-count window** on a file that holds credentials. `[Logging]` is ~22 lines long, so the
window ran off the end of its section and printed the *following* sections into the transcript. The
section-scoped form was tried first (`awk '/^\[Logging\]/,/^\[[A-Z]/'`), returned only the header because
the range pattern matched its own start, and `+44` was reached for as a quick fix. Nobody asked what lived
at line 45.

**A line-count window on a sectioned config is a loaded gun.** Sections move; the window does not.

**Decision — three mechanical controls, in `~/.claude/`** (global, per DEC-0040's *no master repo; guards
live in hooks*).

1. **`hooks/secret-read-guard.sh`** — a `PreToolUse` hook on `Bash`, `Read` and `Grep`. Blocks
   *(secret-bearing path)* × *(content-emitting verb)*: `cat`, `head`, `tail`, `sed` (without `-i`), `awk`,
   `grep`, `cut`, `less`, `xxd`, `diff`, `scp`, … It sees through `ssh "…"` wrapping. **Editing is
   deliberately untouched** — `cp`, `chmod`, `sed -i` and python heredocs all pass, because patching the
   live `weewx.conf` is the DEC-0046 release workflow, and **a guard that blocks the work gets switched
   off and protects nothing.** Path matching is **per-token, not per-string**: a string-level allowlist is
   a hole, since `cat weewx.conf.example && cat weewx.conf` would see `.example`, conclude "sanitized",
   and wave the live config through. `weewx.conf.bak-*` is treated as sensitive as the original, because
   it is a verbatim copy of it.

2. **`bin/readconf`** — the escape hatch that makes the guard livable. **Section-scoped: it structurally
   cannot take a line window**, so it cannot repeat the failure above. Credential values are replaced by a
   stable `<REDACTED:sha256-xxxxxxxx>` fingerprint, which still answers the two questions we actually ask
   of a config — *does prod match the repo?* and *did this drift?* — with nothing disclosed. Redaction
   keys off credential-shaped **key names** or high-entropy **values**, so `handlers = rotate,` and
   `level = INFO` stay readable: those are precisely the lines a DEC-0046 deploy must verify.

3. **`bin/scan-transcripts`** — the detection half, because prevention fails eventually. Correlates config
   values against every transcript on the machine and the full git history of all three repos. Never
   prints a value.

**Both new tools ship with a positive control, and it is not decoration.**

The guard's test asserts in **both directions** — 38 cases. The leaking command must block; and
`cat weewx.conf.example`, `sed -i`, `cp`, `readconf` must all still pass, because the MUST-ALLOW half is
what keeps the guard from being disabled. A **mutation test** (neuter the path check) turns it red — 18
failures — proving it is load-bearing. The scanner **self-tests before every run**: it plants a canary,
asserts it finds it, and asserts a placeholder is *not* reported. It refuses to report "0" if the harvest
returned nothing, because that zero would be a lie.

This is DEC-0039 and DEC-0045 compounding. *A green exit code is not evidence* (0039). *A passing test is
not evidence either, if the assertion is wrong* (0045). **And a scan that finds nothing is not evidence
unless you have proved the scanner can see.**

**A scanner that cries wolf is its own failure mode.** The first pass of this analysis reported a real
password sitting in `weewx.conf.example` in the current tree of the **public** repo — which would have
been a live exposure and a fifth gate hole. It was the example's own placeholder string. The evidence was
internally weird (the same "password" appeared as three different keys), and re-checking it is the only
reason a five-alarm claim was not filed. `is_placeholder()` is now a first-class part of both tools.
**A full scan of all refs confirms no real credential has ever been committed to any of the three repos.**

**Operational note.** Anything printed into a transcript cannot be recalled by deleting the `.jsonl` — it
has already been transmitted. That asymmetry is exactly why the *read* path deserves a guard as strong as
the write path. Credential hygiene follow-ups are tracked in the **gitignored** local-infra doc, never in
this public repo.


---

## DEC-0048 — Reception testing is a designed experiment, not a pile of image tags (S41)

**Status:** Accepted · **supersedes** the ad-hoc `rw*-test` images · **absorbs** DEC-0017's pending sweep ·
2026-07-13 (S41)

**Context.** Three images sat on the NAS for six weeks — `rw250-test`, `rw350-test`, `rw400-test` — built
during an ad-hoc `receiveWindow` sweep. They were **misnomers by the time they were a day old**:
`receiveWindow` ships at the upstream default, so the tag names described a configuration nothing was
actually running. They were never published to Docker Hub (verified: the public tag list is `latest` +
`v1.0-ubuntu22`, `v2-ubuntu26`, `v2.0.1/.3/.5/.6/.7`), so the confusion was ours alone — but a tag that
lies about what is inside it is exactly the failure DEC-0038 exists to prevent (*an image tag denotes
exactly one tree*).

**The deeper problem is that the sweep was never a controlled experiment.** It varied one parameter,
eyeballed the result over an uncontrolled window, and left artifacts behind. **DEC-0017 has been open since
S16 for the same reason** — gain is held at 372 "pending an averaged re-test" that never happened, because
there was no agreed method for running one.

**Decision.**

1. **Retire the ad-hoc tags.** `rw250-test` is deleted. (`rw350-test` and `rw400-test` are the same class
   and should follow.)
2. **A proper RX test is deferred, deliberately — it is not abandoned.** When we do it, it is a *designed*
   experiment, not a tag: a stated hypothesis, a fixed observation window long enough to average out
   propagation and weather, a control arm, and a pre-registered success metric. It settles **DEC-0017**
   (gain 372 vs 207, averaged, no preamp) and any `receiveWindow` question **in the same run**, because
   they share the same apparatus and the same confound.
3. **Until then, gain stays at 372 and `receiveWindow` stays at the upstream default.** Reception is
   noise-floor limited at ~67–70 %, which is a *known* baseline, not a mystery. **Do not tune either
   parameter by feel.**

**Why this is a DEC and not a chore.** The temptation with radio work is to twiddle a parameter, glance at
a number, and keep the tag "just in case". That produces artifacts that outlive their meaning and a
baseline nobody trusts. **An experiment we cannot describe before running it is not an experiment.** The
cleanup is trivial; the commitment is the point.


---

## DEC-0049 — The ISS hardware is new and has been inspected: the rainRate artifact is not a broken part (S41)

**Status:** Accepted · **bounds** DEC-0042 · closes DEC-0042's "next step is physical" action ·
2026-07-13 (S41)

**Owner-supplied hardware facts (2026-07-13):**

- The **ISS hardware is new**.
- It was **recently inspected**, and **no hardware problems were found** — including the tipping bucket and
  the reed switch, which DEC-0042 named as the things to look at.
- The **one** component that did fail has already been **replaced: the anemometer, circa 16–17 June 2026**.

**What this settles.** DEC-0042 concluded that the phantom `rainRate` is **ISS-side, not RF and not the
driver** — condensation trips the reed switch enough to start the rate timer but never enough to tip the
bucket — and its closing action was *"next step is physical: inspect the bucket, the reed switch and its
wiring."* **That action is now closed, and it came back clean.**

**A clean inspection does not falsify DEC-0042 — it sharpens it.** The two readings were always:

1. a **defective** bucket or reed switch (a sticky, mis-seated or corroded part), or
2. a **functioning** switch responding to an environmental condition it cannot distinguish from a tip.

**Reading 1 is now excluded.** The hardware is new and sound, so the artifact is an **interaction between
working hardware and the environment**, not a fault. That is consistent with everything DEC-0042 measured:
both events were overnight, at 94 % RH, with a 1.7 °F dewpoint spread and 0 mph wind, and the tip counter
**never advanced**. Condensation bridging a healthy reed switch produces exactly this signature. **A part
you can replace was never going to fix it.**

**Consequences.**

- **Do not "fix" the rainRate by swapping hardware.** There is nothing to swap. Anyone who reads DEC-0042's
  "next step is physical" without this entry will order a part for no reason.
- **The remaining levers are environmental or software-side** (a shield/drip path, or a rate-plausibility
  guard that requires the tip counter to advance) — but **nothing is being built yet**: the event is rare,
  benign, already corrected in the data (DEC-0032 `rain_qc`), and understood.
- **A third event remains a free test.** It is predictable on the next calm, saturated, cooling night, and
  now has a sharper prediction attached: the counter still will not advance.

**The anemometer replacement (16–17 June 2026) is also a dating anchor** — wind data before and after that
window comes from **different physical hardware**. Worth remembering before attributing any wind-series
step change to software.

## DEC-0050 — The station gets a master for its IDENTITY (and only that): eaglehunt-ops, executing DEC-0040's revisit clause (S42)

**What this settles.** DEC-0040 said *no master coordination repo — yet*, and listed the triggers that
would flip the answer: a third shared **executable** asset, or the second time the same fix is hand-pasted
into three repos. **Both fired.** By S41, `~/.claude/` held five shared executables — `docker-guard.sh`,
`eaglehunt-status.sh`, `secret-read-guard.sh`, `readconf`, `scan-transcripts` — global in blast radius and
version-controlled nowhere; and the secret-gate bug class had been re-derived four separate times (S36 here,
dash DEC-0063, dash S70, S38 here). And the failure DEC-0040 predicted arrived: the dashboard's **DEC-0106**
— the live `proxy.env` carried coordinates 6.67 km from the station (a different NWS grid cell) for a week,
poisoning every captured forecast, because the same physical fact was written six ways across three repos
and **nothing validated any of them**.

**The decision (owner-approved, cross-repo round 2026-07-14 = dash S74 / this repo's S42):**

1. **A small PRIVATE coordination repo, `eaglehunt-ops`**, scoped exactly to the S38 §Etiquette litmus
   test (*does this belong to more than one repo?*): the canonical `station-identity.env`; the drift check
   `checks/station-identity-check.sh`; the one-page NAS runtime contract; the `~/.claude/` guards **under
   version control with their tests** (the live copies become deployments, installed by an owner-run
   `hooks/install.sh`); and an issue tracker as the cross-repo inbox. It is **NOT a master repo**: no DECs
   for the three project repos, not a session-start read, and it carries a deletion clause (unused in three
   months → delete).
2. **The station identity has ONE canonical representation** — `eaglehunt-ops/station-identity.env`.
   This repo's `weewx.conf [Station]`, the gitignored `docs/LOCAL_INFRA.md`, and everything the dashboard
   and HLF hold are **copies, validated against it** by the identity check (equality predicate: same NWS
   grid cell / 250 m — HLF DEC-0078, dash DEC-0108). First run of the check: **8/9 representations agreed
   within 19 m** — and the ninth finding was real (HLF's forecast endpoint was hanging; filed in their
   tracker, not fixed from here).
3. **This repo's identifier hygiene now has a place to point:** `ops/soak_check.sh` no longer carries NAS
   connection facts as tracked defaults (they were live on public `dev` — caught by our own
   `test_check_secrets.sh` tree check, which CI structurally cannot run because `.identifiers` is
   gitignored). Facts live in `~/.claude/nas.env` / `docs/LOCAL_INFRA.md`; the tracked defaults are
   placeholders that **fail fast**. The enforcement hole underneath: **pre-commit was configured but never
   installed in any of the three clones** — the load-bearing local gate had never once run. Closed by
   actually installing it (owner-run), and the lesson is DEC-0040's own, one level down: *a configured
   control that nothing executes is prose.*

**Why not "no repo, just a file on the NAS":** an unversioned canonical file is the same failure shape as
the unversioned `proxy.env` that started this — no history, no diff, no owner. The identity file must live
where change is visible and attributable.

**Boundary rules ratified at the same round** (recorded in the owning repos): HLF's `/api/v1/` surface is
the only sanctioned cross-repo read path into HLF (their DEC-0104); the dashboard owns `proxy.env` even
though it lives under this repo's directory on the NAS (their DEC-0109); the S38 §Etiquette agent protocol
(read-only across boundaries; file, don't fix; one owner per prod; state your confidence) is now standing
doctrine, printed in eaglehunt-ops' README.

---

## DEC-0051 — Cold-load Fix B ships (`current.json`); `windchill` closes issue #44

**Status:** Accepted · **Date:** 2026-07-15 (S43)

The dashboard's S69 handoff and issue #44 (filed at the S42 cross-repo round, dash S74) asked for two
things sharing "the same file, same contract surface": a `current.json` snapshot the dashboard fetches
**first at boot** (Fix A, the dashboard's own localStorage replay via its DEC-0094, only helps *repeat*
visitors — a public link lands on a first-timer with nothing to show, hence the em-dashes), and
`windchill` as the last field the dashboard still round-trips to InfluxDB for on every 30 s tick
(`cloudbase` was already emitted).

**Shipped, both in `loop_json_writer.py`:**
1. `new_loop()` now writes the identical cached-forward dict to a second path
   (`current_path`, default `/opt/weewx-data/current.json`) on every packet, same atomic
   tmp-write + `os.replace` pattern as the existing `loop-data.txt` write. Both paths are
   independently configurable via `[LoopJsonWriter]`.
2. `windchill` added to `_FIELDS` (`windchill` → `windchill_F`), identical treatment to `heatindex`.

`docs/INTERFACES.md` §1 updated: `current.json` documented alongside `loop-data.txt` as the same
contract surface, and `windchill_F` added to the fields table. Serving `current.json` with the right
cache headers (`no-store`) is the dashboard/eh-proxy's responsibility (DEC-0010) — this repo's scope
ends at producing the file. 3 offline unit tests (`tests/test_loop_json_writer.py`), suite 85/85. No
driver involved — `loop_json_writer.py` is a `data_service` (DEC-0005), not the baked driver, so this
ships on the next ordinary config/service deploy, independent of any image rebuild.

---

## DEC-0052 — Adopt the shared closeout skeleton (adapted), from eaglehunt-ops OPS-DEC-0016

**Status:** Accepted · **Date:** 2026-07-19 (S44)

ops#22 found all three trio repos (+ coffeeradar) had independently invented their own closeout
ritual despite common tiered-read/DECISIONS-index/STATUS.md-as-source-of-truth ancestry. This repo's
was the loosest of the four: split across two separate CLAUDE.md paragraphs ("Session ritual — End"
and a separate "Docs-diet ritual at close"), no numbered list. eaglehunt-ops published a generic
6-step closeout skeleton (OPS-DEC-0016, locked OPS-DEC-0019b once three of four repos had adopted)
and filed an adoption ask in each repo's own tracker (this repo's: weewx-rtldavis#56) — adopt, adapt,
or decline is each repo's own call, per OPS-DEC-0001's charter that ops is not a master repo.

**Call: adopt, adapted — not verbatim.** Four of the template's five mechanical steps (green gate,
STATUS pointer, CHANGELOG entry, decision-log row) already matched this repo's practice; the fifth,
commit+push, already has a stricter local rule (pause for approval before every commit and every
push — Non-negotiable rules) that the template doesn't override. This repo's own docs-diet ritual
(DEC-0030) is richer than the template's step 3 for a *public* repo — CHANGELOG archival to
`CHANGELOG-ARCHIVE.md`, and `scripts/check_secrets.sh` run over anything a doc move rehomes — so it
is kept as-is and layered after step 3, per the template's own "repo-specific addenda, not replaced"
pattern.

**The one genuinely new step: step 5, the model-tier restore check.** Nothing in this repo's docs
previously prompted a check, at session close, of whether a bare `/model` switch (which persists as
the new session default — user's global CLAUDE.md, OPS-DEC-0010) needs restoring to the Sonnet
floor. Two other adopters (hyperlocal-forecast DEC-0126, coffeeradar DEC-0054) independently reported
step 5 as the only genuinely new content in the template; this repo's adoption reaches the same
conclusion a third time, from its own review rather than by import.

**What changed:** CLAUDE.md's "Session ritual" now carries one 6-step numbered "End" list in place
of the old two-paragraph split, with the docs-diet ritual folded in as step 3's addendum. No change
to session numbering, to the pause-before-commit/push rule, or to any prior DEC — step 6 points at
the existing rule instead of restating it.

Outcome reported to eaglehunt-ops#22 (cross-repo roll-up); closes weewx-rtldavis#56.

---

## DEC-0053 — Provenance audit: bound the loop-JSON cache; two identity gaps documented, not closed

**Status:** Accepted · **Date:** 2026-07-25 (S48) · **Closes:** weewx-rtldavis#45 ·
**Applies:** DEC-0006 (honest nulls, never stale substitution) to the real-time surface

**Context.** Ported from the dashboard's S73 incident (their DEC-0104/0106): their forecast archive
faithfully recorded the *wrong* coordinates in a column nothing read, and it saved nothing, because
the artifact the consumer actually reads never carried the assumption. Issue #45 asked the same
question of this repo: for each artifact a consumer reads, do the assumptions it was produced under
travel **with** it?

**The audit.**

| Artifact | Units | Station identity | Staleness / cadence | Correction state |
|---|---|---|---|---|
| loop-JSON (`current.json`, `loop-data.txt`) | ✅ in key names | ❌ absent | ❌ **was unbounded** | n/a |
| InfluxDB `record,binding=archive` | ✅ field suffixes | ❌ `tags` unset | ✅ `backfill = 1` | ✅ `*_qc` |
| SQLite `weewx.sdb` | ✅ schema | ❌ absent | ✅ honest `interval` column | ❌ none |
| `DATA_ERRATA.md` | n/a | n/a | n/a | ✅ (it *is* the record) |

**Finding 1 — FIXED. The loop-JSON cache was unbounded, on the surface the dashboard reads.**
`loop_json_writer.py` updated its cache only on non-None values, never expired them, and stamped every
write with the *current* packet's `dateTime`. A dead — or SensorQC-rejected — sensor therefore emitted
its last value forever, indistinguishable from a live reading. This is the same failure
`dewpoint_service.py` fixed for the **archive** path at S33/DEC-0022, whose comment names it exactly:
*"a stale substituted value masks that indefinitely."* The lesson was learned in one artifact and never
propagated to its sibling. Not hypothetical — the anemometer failed and was replaced ~16–17 Jun 2026,
precisely the class of event this masks.

**Decision:** bound the cache per-field. 300 s default (matching DewpointCacher, and ~5–12× the ISS
rotation), but **2 × `[DavisPressure] fetch_interval`** for `barometer_inHg` — a flat 300 s would have
blanked the barometer for 55 minutes of every hour and regressed S43's Cold-load Fix B. The barometer
TTL is *derived from that service's own config*, so the two cannot drift apart. Past its TTL a field is
omitted and a `WARNING` names it, which also turns a silently-dead sensor into an observable event.
Contract-compatible: INTERFACES §1 already required consumers to treat any field as possibly-missing.
Guarded by 6 tests, including a mutation check confirming they go red against the old unbounded cache.

**Finding 2 — DOCUMENTED, deliberately NOT fixed. InfluxDB carries no station identity.**
`influx.py` supports `tags = station=A`; the live config sets none, so the only tag is
`binding=archive` and every point in an infinite-retention bucket is anonymous. **The one-line fix is
a trap:** a point's series key *is* measurement + full tag set, so adding a tag forks a parallel
series — which INTERFACES §2 explicitly forbids for corrections/backfills, and which would split
historical continuity and require dashboard coordination. Currently harmless (one producer, one
station), and unlike the dashboard's incident we record *no* identity rather than a *wrong* one — the
gap is unauditable but not misleading. **Revisit only if a second producer appears** (PRINCIPLES §1's
multi-source future is exactly when it starts to matter), and treat it as a coordinated interface
change, never a config tweak.

**Finding 3 — DOCUMENTED, not fixed. The system of record is less provenanced than the derived store.**
InfluxDB corrected points carry `rain_qc` / `rainRate_qc` / `backfill`; the SQLite archive carries
nothing, so a corrected row is indistinguishable from a never-corrected one. Only `DATA_ERRATA.md` — a
markdown file outside the data path — records it. Backlogged; a schema change to the archive is not
justified by current need, but a reader treating SQLite as ground truth should know the flags live
downstream, not here.

**The rule this earns.** *A cached or substituted value must carry, or be bounded by, the assumption
that makes it valid.* Units already travel in key names; staleness now travels as a bound; identity
still does not, and that is recorded rather than assumed away. Corollary, from Finding 1's history:
**when a data-integrity lesson is fixed in one artifact, check its siblings in the same commit** —
DEC-0022 fixed the archive path and left the real-time path carrying the identical bug for 15 sessions.

## DEC-0054 — Frame-level co-rejection: a bounds failure condemns the whole frame

**Status:** Accepted · **Date:** 2026-07-27 (S52) · **Extends:** DEC-0029 · **Bounded by:** DEC-0044
(this is NOT the parked coupling filter) · **Motivated by:** ERR-0004 / issue #76 / ops#103

**Context — the event the old filter was structurally blind to.** 2026-07-27 14:55:50 EDT: during an
`rxCheckPercent` collapse to 13.2%, one multi-bit-corrupt-but-CRC-valid frame (the DEC-0033 class)
arrived carrying `humidity_raw = 59a9` → 144.9 %RH *and* a wind byte decoding to 39 mph, from dead
calm. SensorQC checked each field independently: humidity failed **bounds** (impossible per sensor
spec) and was rejected; wind — 17.4 m/s, inside the 6410's 0–200 mph spec, +16.5 m/s from a calm
baseline, *under* the 20 m/s delta cap — sailed through, became the archive interval's gust max, and
went out to all ten external sinks. The system had **positive proof the frame was corrupt and still
trusted every other field of that same frame.** Diagnosis credit: dashboard S149 (external evidence,
issue #76) and an eaglehunt-ops intermediary session (log forensics, ops#103); both independently
re-verified here against `weewx.log` and the driver source before this was designed.

**Why not just tighten the wind delta cap.** The 20 m/s cap was calibrated against high-bit flips
(the 201 mph spike: +128/+64 mph). This event sits in the mid-magnitude gap (+~36 mph territory) —
and so does a *genuine* first gust of a squall from calm (25–35 mph is meteorologically routine).
Field-level thresholds cannot separate those two; frame-level evidence can.

**Decision.** In `_data_to_packet`, a bounds-only pre-pass runs before per-field QC. If ANY QC-covered
field in the decoded frame fails its sensor-spec **bounds** check:

1. Every weather-observation field the frame carries (`FRAME_WEATHER_KEYS`: wind triple + direction,
   the message-type payload — temperature/humidity/UV/radiation/rain-rate, extra temp/humid channels)
   is nulled (DEC-0006 honest null). One log line names the co-rejected set.
2. The rain counter, if present, is **skipped without resyncing** `last_rain_count` — the counter is
   cumulative, so genuine tips still land in the next clean frame's delta; resyncing to a corrupt
   counter byte would swallow or invent tips.
3. **No baselines move.** The corrupt frame's in-spec values must not become delta history; the next
   genuine reading is judged against pre-glitch state and accepted immediately (tested).
4. Diagnostics (battery flags, supercap/solar power, freqError, pct_good) survive — they describe the
   link, not the weather, and nulling them would blind the very telemetry that flags these events.

**The asymmetry is the design.** Only a *bounds* failure triggers co-rejection — positive proof, a
value the sensor cannot emit. A *delta* trip never does: it may be genuine weather, and the existing
per-field resync handles it at a documented cost of 1–2 readings. This keeps the false-positive cost
of co-rejection at (probability a frame contains an impossible value) × (2–3 sibling fields nulled
for one reading) — negligible against serving a phantom to ten immutable external networks.

**Why this is not DEC-0044's coupling filter.** DEC-0044 parked a *cross-sensor delta-correlation*
filter whose fitted thresholds failed re-derivation on our own data — "instrument, don't filter."
Co-rejection has **zero free parameters**: it fires only on the bounds proof DEC-0029 already
computes, within one frame, at one choke point. Nothing is fitted, so nothing can drift.

**Precedent, generalized.** The driver already co-rejected `wind_dir` when `wind_speed` failed ("the
same-packet direction byte is equally suspect") — a two-field special case of exactly this rule. And
the old test suite *asserted the gap*: `test_packet_gets_explicit_null_and_wind_dir_nulled` required
same-frame humidity to SURVIVE a wind bounds failure. That assertion is now inverted — the S40 lesson
(a passing test is not evidence if the assertion is wrong) applied in the other direction.

**Ships in v2.0.9** (driver is baked, DEC-0031 — image rebuild, deliberate release). Guarded by 6 new
tests including a verbatim replay of the 2026-07-27 frame.

---

## DEC-0055 — The outside-temperature field is SIGNED; decode it as true two's complement, not meteostick's one's complement

**Status:** Accepted · **Date:** 2026-07-28 (S54) · **Fixes:** the R1 finding of the ops#105 audit
(weewx S53) · **Bounded by:** DEC-0054 (co-rejection is what makes this urgent) · **Deviates from:**
weewx-meteostick, deliberately, by one LSB

**Context — a latent bug that only fires in winter.** `rtldavis.py` decoded the 12-bit digital
temperature field as **unsigned**. Davis encodes it as **two's complement**. The station has never
seen a sub-0 °F reading, so the bug has never fired; the ops#105 cross-observable QC audit found it
by reading the encoding out of the source rather than observing an event.

The failure chain on the first hard freeze, with the numbers:

| Step | Value |
|---|---|
| Real reading | −5.0 °F |
| On the wire (12-bit two's complement tenths) | `0xFCE` = 4046 |
| Unsigned decode (the bug) | 4046 / 10 = **404.6 °F = 207 °C** |
| SensorQC `temperature` bounds (`rtldavis.py`) | −40…65 °C → **trip** |
| DEC-0054 co-rejection | bounds failure is *positive corruption proof* → **the whole frame is nulled** |

So genuine cold weather reads as proof of RF corruption. Pre-v2.0.9 that nulled temperature alone
(the station goes blind below 0 °F). **Post-v2.0.9 it is strictly worse:** every type-8 frame co-rejects
its wind siblings too, and the co-rejection log line — which we are actively watching as a corruption
alarm (STATUS "Active thread") — fires every ~30–60 s for the duration of the cold snap. The alarm we
built to catch corruption would have been saturated by ordinary winter.

**Why not copy weewx-meteostick verbatim.** The audit recommended adopting meteostick's handling, and
meteostick is right about the two things that matter — the field is signed, and there is a **second
no-sensor sentinel `0xFF8`** that our fork and upstream lheijst both lack. But its arithmetic is
`-(temp_raw ^ 0xFFF) / 10.0`, which is **one's** complement:

- `temp_raw ^ 0xFFF` = `4095 − temp_raw`, so it computes `temp_raw − 4095`; true two's complement is
  `temp_raw − 4096`. Every negative reading comes out **0.1 °F warm**.
- The tell: `0xFFF` should be −0.1 °F. Meteostick maps it to **0.0 °F** — the same output as `0x000`.
  One code point is duplicated and −0.1 °F is unrepresentable.
- It also breaks sign symmetry. The positive branch truncates toward zero (floor); `− 4096` floors on
  the negative side too, keeping the truncation bias uniform across zero. `− 4095` flips the bias
  direction at 0, putting a discontinuity exactly where readings cluster in winter.

We ship `(temp_raw - 0x1000) / 10.0` when bit 11 is set, and adopt the `0xFF8` sentinel. Verified
against the meteostick source (read directly, not quoted from the audit) and the DavisRFM69 protocol
notes ("the value is signed"). The `osengr.org` RF-protocol PDF surfaced by search does **not** cover
Davis and was discarded rather than cited — checked, per the verify-externally rule.

**The analog/thermistor branch is untouched.** That path reads an unsigned ADC value; sign handling
lives inside the digital branch only, matching meteostick.

**Guarded by 10 new tests** (`tests/test_temp_twos_complement.py`), including: a −40 °F frame, the
`0xFFF` case that *distinguishes this decision from meteostick's*, both sentinels, a positive-control
frame builder, a DEC-0054 **co-rejection non-fire** sweep across −0.1…−39.9 °F, and a positive control
proving the bounds gate really does fire on the old unsigned decode (the S40 lesson: a passing test is
not evidence if the assertion cannot fail). All three plausible regressions were **mutation-tested**
red: unsigned decode, dropped `0xFF8`, and meteostick's one's complement.

**Not yet shipped.** The driver is baked (DEC-0031), so this needs an image rebuild and a deliberate
release — deadline is **first frost**, not this session. A companion upstream PR belongs alongside
lheijst#22.

---

## DEC-0056 — `MAX_PLAUSIBLE_TIPS` 60 → 16 (ops#105 R2): evidence-bounded tightening, with a loud-failure tripwire instead of silent headroom

**Date:** 2026-07-28 (S55) · **Status:** Accepted · **amends** DEC-0021 · **executes** ops#105 R2 · owner-approved after evidence review

### The question, and the worry that shaped the answer

The S53 audit (ops#105) recommended tightening the rain-counter delta cap from 60 to 16 tips,
halving the residual phantom a corrupt in-bounds counter reading can book (0.30 → 0.16 in — a
phantom is never reversed in-band, DEC-0021's rejection only nulls, it cannot subtract). The owner
held the change for discussion with one specific worry: **a filter restrictive enough to reject a
genuine intense rainstorm loses real data silently and permanently** — the always-resync at the
call site (`rtldavis.py` ~1182) means a rejected delta's tips are never booked, and an undercount,
unlike a phantom, is invisible after the fact. The decision below is shaped by that asymmetry:
phantom rain is visible (rain on a dry day sticks out) and correctable (ERR process, four
precedents); missed rain during a storm is neither. So the cap change ships **as a package** whose
other parts convert "silent permanent loss" into "loud, bounded, recoverable."

### The evidence pass (2026-07-28, full pre-correction archive: 70 days, 95,901 minutes, 6.25 in of rain, 490 wet minutes)

- **Worst-ever real minute: 7 tips** (twice, 2026-06-14 storm, reception healthy at 63–71%).
  Histogram cliff: 417 of 490 wet minutes are 1 tip; 8 minutes ≥ 4 tips; nothing above 7.
- **Worst-ever real accumulation windows:** 2-min 12 tips · **3-min exactly 16** · 4-min 23 ·
  5-min 28 · 13-min 44 (all the same 06-14 storm).
- **In-service reading gaps during rain effectively do not happen:** reception has never been
  below 50% in a wet minute; station-wide rx<20% collapses total 31 minutes in 70 days with a
  longest run of **1 minute**; rain-NULL runs within ±15 min of actual rain: **two events ever,
  both 1 minute**. (The S51 "13-minute dropout" that motivated caution was humidity-message-
  specific; no sustained whole-link collapse exists in the record. Multi-hour archive gaps are
  full station outages, where the driver restarts and re-seeds its baseline — the cap never
  evaluates those.)
- **Physics closes the loop:** at the bucket's ~4 s/tip ceiling, a genuine delta can exceed
  16 tips only across a reading gap > ~64 s — and the worst observed in-service gap during rain
  is 60 s. So cap 16 is safe against **any physically possible intensity** at every gap length
  the station has ever exhibited. The audit's "zero false-positive cost" claim, previously
  resting on an assumed ~60 s worst-case gap, now rests on measurement.
- **The filter is idle at 60:** zero rain-counter rejections in the 30-day retained logs (all
  five "implausible" hits are SensorQC wind/humidity, one being ERR-0004 itself).
- **Boundary semantics preserved deliberately:** the check is `delta > max_tips`, so 16 itself
  passes — and the worst-ever real 3-minute accumulation is *exactly* 16. Even the never-observed
  freak case (a 3-min gap landing on our worst-ever burst) still books its rain.

### The reframing that shrinks the change

weewx's own `[StdQC]` layer caps rain at 0.3 in per archive minute, and a catch-up delta lands in
a single archive minute. So genuine deltas over 30 tips were **already being discarded system-wide
at cap 60** — the apparent tolerance of big catch-ups was an illusion. The band this change newly
exposes is **17–30 tips only** (gaps of ~68 s–2 min at maximum physical rate), never once occupied
in the record. "60 → 16" is really "30 → 16."

### The decision (the package, all four parts)

1. **`MAX_PLAUSIBLE_TIPS = 16`** (`rtldavis.py`; rides `dev` until the next image cut — a
   hardening, not a live bug, so it forces no deploy).
2. **The rejection email is the tripwire.** `weewx_monitor.py`'s existing DEC-0021 glitch alert
   (marker `rejecting implausible counter delta`, 300 s cooldown, live on the NAS) has its body
   reframed: a rejection is *probably* a caught glitch, but the email now explicitly prompts the
   WeatherLink cross-check in case it is real rain across a rare long gap. Base rate is zero per
   30 days — a zero-noise tripwire. A cross-module contract test now pins the monitor's marker to
   the driver's exact logerr wording, so a reworded message breaks CI instead of silently killing
   the alert.
3. **The recovery playbook** (this section is it): the co-located WeatherLink console receives the
   same ISS broadcast independently and keeps its own rain record. On any rejection that coincides
   with real rain: compare the console's window total against ours, and book the shortfall via the
   established ERR correction process (DEC-0025/0032/0037 — both stores, derived fields included).
   Worst case is therefore a bounded 0.17–0.30 in gap, reconciled same-day — never a lost storm.
4. **The revisit trigger, predefined:** any rejection alert on a genuinely wet day reopens this
   decision with that event's data in hand. The tripwire makes the revisit evidence-driven instead
   of vigilance-driven, in both directions.

### Alternatives declined, and when they would win

- **Keep 60:** keeps headroom the system already didn't have (StdQC), for a gap tail the station
  demonstrably doesn't produce, at the price of double the phantom ceiling. Declined.
- **Time-aware cap** (`allowed ≈ gap_seconds / 4 s-per-tip`): structurally elegant, no free
  parameter — but the multi-minute in-service gap it defends against does not occur here during
  rain, and its allowance grows exactly when a corrupt reading after a long quiet gap would ride
  it. Over-engineering for this station's measured conditions. Declined without prejudice — it
  remains the natural shape for upstream-grade robustness where gap behavior is unknown.
- **Confirm-on-reject** (hold the old baseline on an implausible delta; book the accumulation one
  reading later if the next independent transmission confirms the counter really moved): makes
  losing real rain structurally impossible rather than improbable, because real rain persists in
  the cumulative counter and a glitch does not. Declined **for now**: it adds a state machine to a
  deliberately pure function, and any confirmed catch-up over 30 tips still collides with StdQC,
  which needs its own design pass. **This is the designed escalation if the tripwire ever fires
  on real rain** — and the alert's data is exactly the evidence that would justify building it.

### Honest bounds on the evidence

70 days, one partial summer: no tropical remnant, no winter storm in the record. The protection's
shape is what carries the extrapolation — intensity alone *cannot* false-reject (the bucket cannot
physically out-tick ~15/min); only intensity × a >64 s reading gap can, gaps are what the station
demonstrably does not do during rain, and if that ever changes the failure is loud, bounded
(≤ 0.30 in exposure per event within the StdQC band), and same-day recoverable from an independent
record. That is the assurance: not that the tail case can't happen, but that it cannot happen
*silently*.

---

## DEC-0057 — ROADMAP.md joins the closeout ritual: same-session updates + a next-check-due tripwire

**Status:** Accepted · **Date:** 2026-07-28 (S56) · **Extends:** DEC-0052 (closeout skeleton)

**Context.** A user-asked audit this session (S56) found `docs/ROADMAP.md` had drifted 20 sessions
and 8 releases (S35 → S55c, v2.0.3 → v2.0.11) out of date: five real P1-tier releases (sensor-QC
decode filter v2.0.4, reception-metric fix v2.0.8, frame-level co-rejection v2.0.9, signed temp
decode v2.0.10, cap-16 tuning v2.0.11) had zero representation, and several already-completed
housekeeping items (remote URL casing, stale-branch cleanup, the May rain-total reconciliation
against the WeatherLink console, the README refresh) still showed as open checkboxes. Nothing in
the closeout ritual (DEC-0052) ever asked whether a shipped DEC should move a ROADMAP line — the
ritual updates STATUS.md and DECISIONS.md every session, but ROADMAP.md was only touched by the
periodic docs-diet pass or an ad-hoc audit, so "same session" discipline never applied to it.

**Decision:** two additions, not one, because they cover different failure modes.

1. **Closeout step 5 (new):** if a DEC logged this session (step 4) ships, closes, or reprioritizes
   a line item on `docs/ROADMAP.md`, update that line in the same session — not deferred to the
   next docs-diet pass or the next audit. Mirrors the discipline step 4 already applies to
   `DECISIONS.md` itself.
2. **A tripwire inside ROADMAP.md**, not just a rule in CLAUDE.md: a "Keeping this current"
   section naming the date of the last full reconciliation and a next-check-due session number
   (~10 sessions out). If the session counter reaches or passes that number, run the full
   reconciliation pass regardless of whether any DEC prompted it.

**Why both, not just one.** The same-session rule (1) catches drift *at the moment it's created* —
cheap, since the relevant context is already loaded that session. The tripwire (2) is the backstop
for drift that accumulates from elapsed time or a missed trigger rather than any single DEC — the
same failure mode that produced this session's 20-session gap in the first place: no individual
session's DEC made the whole page stale, it went stale by accretion, so a rule that only fires on a
DEC-shaped trigger would still miss it.

**What changed:** CLAUDE.md's closeout skeleton (Session ritual → End) gains step 5; the model-tier
restore check and commit+push steps renumber to 6 and 7. `docs/ROADMAP.md` gains the "Keeping this
current" section, added this session alongside the fuller restructure that prompted this DEC.

---

## DEC-0058 — ROADMAP.md trimmed to P0–P3; P4 and long-term direction move to BACKLOG.md

**Status:** Accepted · **Date:** 2026-07-28 (S56) · **Extends:** DEC-0057's same-session doc
discipline

**Context.** Same session, immediate follow-on to DEC-0057. Reviewing the just-restructured
`docs/ROADMAP.md`, the owner asked whether long-term material had a dedicated home separate from
the active plan, or whether "it's all still one roadmap" — and suggested a division would make the
active list easier to track. Looking at the page: P0–P1 were fully shipped history, P2–P3 were the
only genuinely active/sequenced tiers, and P4 + "Longer horizon" (credential hygiene, multi-source
adaptability, the governance-template harvest, and the newly-added ops#110 winter-2027 item) were
uncalendared direction with no scheduled date — sitting in the same file and same visual weight as
the work actually coming up next.

**Decision:** `docs/ROADMAP.md` now covers **P0–P3 only** — the actively-sequenced plan. P4 and
"Longer horizon" content moves to a new "## Long-term direction" section in `BACKLOG.md`, which
already existed as the unordered-ideas pool and was the natural home rather than inventing a fourth
doc. `BACKLOG.md`'s existing "Open ideas" section is left as-is (near-term-ish, ungraded); the new
section is explicitly for uncalendared/aspirational items, with a one-line rule at its top: pull an
item into ROADMAP.md's P0–P3 when it's actually about to be worked, not before.

**Why BACKLOG.md and not a new file.** STATUS.md (now) / ROADMAP.md (next, ordered) / BACKLOG.md
(someday, unordered) already covers the three horizons this repo needs. A fourth document would
duplicate that shape rather than clarify it — the actual problem wasn't a missing file, it was that
two different horizons (medium-term P2–P3 and uncalendared P4/direction) were sharing one file with
no visual separation. Splitting *within* the existing three-doc structure keeps DEC-0030's docs-diet
philosophy (tiered, not proliferating) intact.

**What changed:** `docs/ROADMAP.md` — priority-vocabulary note, intro paragraph, and the "LONG TERM"
section removed (replaced by a one-line pointer to BACKLOG.md). `BACKLOG.md` — intro updated, new
"## Long-term direction" section added. `CLAUDE.md`'s doc-map table rows for both files annotated
with the split. Same pass also pruned a second stale copy of the already-resolved (S48) May
rain-total item, found in `BACKLOG.md`'s "Data integrity" section while editing nearby content —
same fact DEC-0057's ROADMAP reconciliation had already corrected once, in the other file.

---

## DEC-0059 — The RX experiment gets an apparatus; `-ex` collapses the window axis into the cheap layer

**Status:** Accepted (design) · **Date:** 2026-07-28 (S56) · **Executes** DEC-0048 ·
**amends** DEC-0048's "same run" clause · **supersedes** DEC-0008's `set_gain.sh` exemplar ·
**absorbs** DEC-0017 · owner-approved after design review

### What prompted it

DEC-0048 committed to a designed RX experiment — hypothesis, control arm, averaged window,
pre-registered metric — and then deferred it for 15 sessions because no apparatus existed. DEC-0017
has been open since S16 for the same reason. The owner asked for the design, with two constraints:
no data may go uncollected because of poor reception, and there must be an immediate rollback if
anything egregious happens.

### The finding that reshaped the design

**`-ex N` is mathematically identical to `receiveWindow = 300 + N`.** Upstream sums them —
`int64((receiveWindow + ex) * 1000000)` — and `receiveWindow` appears in no other expression. So the
receive-window axis, which DEC-0048 treated as rebuild-only and therefore inseparable from the gain
question, is actually reachable from the **mounted** `weewx.conf` at the same cost as gain.

Consequences: the `rw250/rw350/rw400` images were **redundant**, not merely misnamed as DEC-0048
recorded; the old CLI `-ex` sweep and the old `rw400` image were the same configuration measured
twice (both ~63%, which is what equivalence predicts); and **no arm of this experiment requires an
image build**, so the owner's immediate-rollback constraint is satisfiable on every axis.

*Honest bound:* this was read from upstream master. The deployed binary comes from weewx-contrib's
bundled `src.tgz` and is demonstrably older — it lacks master's startup settings line, absent from
both `weewx.log` and container stdout. The deployed source has not been read directly. The
equivalence is load-bearing only for how arms are *labelled*, not for validity: `-ex` is a real knob
whose effect is measured directly either way.

### The measured baseline, replacing a stale one

447 five-minute reception samples (2026-07-27 full day + 07-28 to 13:29): **mean 73.3%, sd 4.67 pts**;
p5/median/p95 = 67/74/79. The docs' long-quoted "~67–70%" was pessimistic. Two properties matter more
than the mean:

- **Autocorrelation ~0 beyond 10–15 min** (lag1 0.08, lag3 0.02) — samples are effectively
  independent, so precision scales cleanly with time.
- ~~**No detectable diurnal cycle** — hourly means 70–75 with no systematic pattern.~~
  **AMENDED 2026-08-01 (S58) — the second half of that claim was wrong.** The *range* was right
  (hourly means do sit in a narrow band), but "no systematic pattern" was not: re-reading the same
  pre-campaign period from the archive's own `rxCheckPercent` at hourly resolution shows a
  **reproducible ~2-point notch at hour 07 and again at hour 19** (72.6 and 72.7, against 74.2–75.6
  for every other hour, n≈355/hour over 07-24→07-29). It is small enough to sit inside the 70–75
  band — which is exactly how it was missed — but it repeats daily and is therefore systematic by
  definition. Characterization and the falsified explanations are in BACKLOG.md §Durable RF
  findings; **it does not affect this experiment's validity** (the Latin square balances any
  time-of-day term across all four arms), but it does mean *diurnal structure exists at hourly
  resolution* and any future analysis binned finer than 6 h must account for it.

Together these say the "1–2 week averaged window" assumed by DEC-0017 and BACKLOG is roughly **7×
more than the variance requires**. 24h per arm resolves 1.1 pts; 48h resolves 0.8.

### The design

Two campaigns, blocked by hardware state, at the owner's direction: **LNA in circuit first, then the
LNA physically removed.** Within each campaign, a 2×2 factorial (gain × `ex`) run as a **Latin
square** — 6-hour blocks on the monitor's existing 00/06/12/18 summary boundaries, rotated so each
arm visits each quarter of the day exactly twice over 8 days. Campaign B's gain arms are centered
higher: with ~20 dB of front-end gain removed the optimum moves up, so reusing campaign A's values
would sweep two points that are both too low.

Adoption rule, fixed in advance: beat the incumbent by **≥2 pts on reception without materially
raising the duplicate-frame rate**. Incumbent wins ties. Two outcome metrics, not one, because a
wider window buys marginal packets by increasing preamble false-alarm opportunities — the same
mechanism as DEC-0035's ~722/day double-decodes. Both metrics are already logged; no new measurement
code.

**Declined: bracketing the LNA swap.** A blocked design confounds the LNA contrast with ~10 days of
seasonal drift, and the analytically clean answer is a tight paired swap at the moment of removal.
The owner judged that not worth the handling, which is their call to make. Mitigation instead of
argument: campaign A's own 8 days measure multi-day drift directly, and that becomes the honest error
bar on the LNA comparison rather than a confound we pretend isn't there.

### Why a new apparatus rather than extending `ops/gain_sweep.sh` (DEC-0014 cause)

It is **sequential** — every arm confounded with time-of-day, the precise flaw DEC-0048 exists to
replace. Its metric is **dead**: it counts `RAW_DATAPACKET_MATCH`, which prod no longer logs, so it
would report 0.0% for every arm and look like it worked — the green-exit-code-wrong-answer class that
has bitten the secret gate four times. Its denominator is **wrong** (2.5 s hardcoded; this ISS is
2.8125 s — the same ~13% error S29 already fixed once in the monitor). And it has no verification,
rollback, abort, or health check. Patching would touch every line.

**All seven pre-governance RF sweep scripts are deleted** (`gain_sweep.sh`, `gain_sweep_analyze.py`,
`set_gain.sh`, `fc_sweep.sh`, `gain_ppm_check.sh`, `autotest_rf_timing.sh`,
`recover_sweep_results.py`). DEC-0048's own complaint was artifacts outliving their meaning, and a
silently-broken sweep script is worse than no script. Git history preserves them; the one durable
finding that lived only in `fc_sweep.sh`'s header (gain 207 "confirmed best") was moved to BACKLOG
before deletion.

**This supersedes DEC-0008's closing sentence.** That DEC cites `set_gain.sh` as codifying
`docker kill` + `docker start`; the codification moves to `rx_experiment.sh`'s `restart_container()`,
which implements the same pattern plus S47's 3 s dongle-release sleep. DEC-0008's rule is unchanged —
only its exemplar moves.

### The safety model

The script rewrites the live, credential-bearing `weewx.conf` 32 times and restarts prod each time.
Six properties make that acceptable rather than merely convenient:

1. **Arms are complete literal strings** — never assembled. A bug can only select the wrong
   known-good arm, never synthesize a malformed one.
2. **Revert is a whole-file snapshot restore**, not line surgery. Byte-exact.
3. **Writes are atomic and verified by re-reading** before the container is ever restarted.
4. **The abort tripwire is sticky** — a STOP sentinel halts the campaign until a human clears it; a
   later scheduled tick cannot silently override it.
5. **The schedule self-terminates into the production baseline**, so a forgotten campaign ends at
   prod-normal rather than on an experimental arm.
6. **Every failure path restores the baseline and emails**, via a mailer deliberately independent of
   `weewx_monitor.py` — if the monitor is wedged, the abort must still reach a human.

Abort threshold is 55% on a 30-min rolling mean: ~9.6 SE below the measured baseline, so it cannot
fire on noise. The deeper reassurance is that reception degradation is **not** data loss — the ISS
sends ~21.3 packets/min into 1-minute archive records, so a record only nulls if a full minute
decodes zero packets. Even an arm halving reception to ~36% loses nothing. Corroborated empirically:
DEC-0056's 70-day pass found rx<20% totaled 31 minutes with a longest run of one minute.

### Tests

`tests/test_rx_experiment.py` drives the real shell functions. It asserts the write is surgical
against a fixture carrying two traps (a `-gain` in an unrelated section, another in a doc comment),
that malformed configs are refused with the file unmodified, and — per DEC-0045 — carries a
**positive control** proving the old global-regex approach corrupts that same fixture. If that
control ever passes, the fixture has lost its teeth. The Latin square is machine-checked too: a
one-row typo silently reintroduces the confound the design exists to remove, and nothing at runtime
would notice. Mutation-tested; it goes red.

### Status

**Deployed and running (S57, 2026-07-29).** Phase 0 ran first and confirmed `FreqError` telemetry
exists (see DEC-0060 for what that took). `ppm`/`fc` remain unmeasured (`0`/`0`) in all four
arms — measuring them by value instead of leaving the axis dropped is a deliberately deferred
follow-up, not a blocker (owner call: get the campaign running the same day). `rx_experiment.sh`
deployed to the NAS project root, sha-verified, `install` run (baseline snapshotted). Owner created
the two DSM Task Scheduler entries; the first automatic tick swapped to arm B (gain 207, `-ex 0`)
at 10:52:37 EDT. Campaign A runs unattended for 8 days from there, self-terminating to baseline
(expected completion ~2026-08-06). Tracked at
[ops#114](https://github.com/WeatheredScientist/eaglehunt-ops/issues/114).

---

## DEC-0060 — `debug_rtld` alone doesn't turn on driver debug logging — the `user` logger also has to be at DEBUG

**Status:** Accepted · **Date:** 2026-07-29 (S57) · **extends** DEC-0043's root-logger override ·
**explains** why DEC-0059's Phase 0 first attempt produced nothing

### The gotcha

`rtldavis.py`'s `dbg_rtld(verbosity, msg)` calls `logdbg(msg)` → `log.debug(msg)` — a plain Python
`logging` call. Python's logging module filters at the **logger's** configured level before a
handler ever sees the record. The live `weewx.conf`'s `[Logging][[loggers]][[[user]]]` carries
`level = INFO`. So every `dbg_rtld()` call — at *any* `debug_rtld` value, 1, 2, or 3 — was being
silently dropped by the logger itself, independent of the driver's own verbosity gate. `debug_rtld`
only decides whether the driver *calls* `log.debug()`; it does not decide whether that call
actually reaches the log file.

This is not a new bug — it likely explains why `ops/find_duplicate_frames.py`'s own header already
warns it "Requires `debug_rtld = 1` (or higher) **AND** the `user` logger at DEBUG in `[Logging]`."
Nobody had connected that comment to a live Phase 0 attempt before now: `debug_rtld=2` ran for ~7h
on 2026-07-28 and produced zero `chan:`/`FreqError` lines — not because the telemetry doesn't
exist, but because the logger gate was closed the whole time.

### The fix, and why it's scoped

Adding a **`[[[user.rtldavis]]]`** logger entry at `level = DEBUG` — rather than raising the
existing broader `[[[user]]]` entry — confirmed the telemetry within 13 seconds of the next
restart. Scoping it to `user.rtldavis` specifically means `pressure_service`, `wcloud`, `influx`,
`windy`, `owm`, and `loop_json_writer` (all children of the same `user` logger namespace, per
Python's dotted-logger hierarchy) stay at `INFO` throughout — raising the parent would have
changed verbosity for all of them at once, with no assessment of what each one's own debug-gated
log calls would have dumped.

### Standing rule

**Any future need for `dbg_rtld()`/`dbg_parse()` output requires BOTH**: (1) `debug_rtld`/
`debug_parse` at the right verbosity in `[Rtldavis]`, **and** (2) a scoped `[[[user.<module>]]]`
logger entry at `DEBUG` in `[Logging][[loggers]]` — never the broader `[[[user]]]`. Revert both
together when done; leaving either one in place either produces nothing (logger still at INFO) or
over-scopes the verbosity increase (broader logger raised). This is now the confirmed, tested
recipe — don't re-derive it from scratch, and don't assume `debug_rtld` alone is sufficient just
because it *was* sufficient for the always-DEBUG `chan:`/`data:` design intent (it never has been,
in this deployed config).

---

## DEC-0061 — Campaign A died of two defects the apparatus's own tests could not see; a timeout budget must be derived, not guessed

**Status:** Accepted · **Date:** 2026-07-29 (S57b) · **fixes** DEC-0059's apparatus ·
**extends** DEC-0045's positive-control rule to *runtime* budgets

### What happened

Campaign A ran for 80 minutes and aborted in its third block. The abort path did exactly what it
was designed to do — restored the baseline snapshot, halted with a sticky STOP sentinel, left prod
healthy — and then failed at the last step: it told nobody. Two independent defects, neither of
which any of the 8 shipped tests could have caught, because both live in the gap between the script
and the machine it runs on.

### Defect 1 — the health-check budget was too small BY CONSTRUCTION

`health_ok()` waited 18 × 5s (~90s) for a new archive record after a container restart. But a
restart cannot produce one faster than:

| term | value |
|---|---|
| weewx boot to "Starting main packet loop" | ~25 s |
| wait for the next archive boundary | **up to 60 s** (the archive interval) |
| write lag after that boundary | ~15–30 s |
| **worst case** | **~115 s** |

90 s could not cover 115 s. The check was a coin flip on where the restart landed relative to the
minute boundary. Arm B won it at 10:52; arm C lost it at 12:13 — measured: `weewxd` init 12:11:46,
first record 12:13:30, abort fired 12:13:27. **Three seconds.**

The number 18 appears nowhere in a specification; it was a guess that happened to be near the true
worst case, which is the most dangerous kind of wrong — it passes often enough to look correct.
`HEALTH_TRIES` is now 36 (~180 s), and the test asserts *the arithmetic* (`boot + archive_interval
+ write_lag`) rather than the literal, so lowering it fails with the reason attached.

**The generalizable rule: a timeout that waits on a periodic system must budget for a FULL period
of that system, plus the work, plus slack. Derive it from the system's own constants and write the
derivation next to the number.**

### Defect 2 — every alert the script could send was broken

`send_mail()` ran `. "$ENVFILE"`, which sets shell variables but does **not export** them. The
`python3` heredoc that actually sends the mail is a *child process*, so it saw none of them and
died on `KeyError: 'ALERT_FROM'`. This had been true since the file was written; no alert had ever
been sent, so nothing had ever disproved it.

This is the same shape as DEC-0060 one day earlier: **a configured-looking thing that was inert,
and looked fine precisely because it had never been exercised.** Extracted `load_env()` with
`set -a`/`set +a`, and tested the property that actually failed — that a *child process* can read
the value — rather than that the shell can. Verified against the real `monitor.env` on the NAS
after deploy (booleans only, never values): `ALERT_FROM/GMAIL_PASS/ALERT_TO` all `True`.

### What the tests did right, and what they could not reach

The suite's design held up where it applied: when a bad edit produced a mangled 28-row schedule
mid-session, `test_schedule_is_a_balanced_latin_square` caught it immediately, and the new
export test was mutation-verified (removed `set -a`, watched it go red, restored **from a file
copy — never `git checkout`**, per the S55 gotcha).

But both defects were *environmental* — one about wall-clock timing on this specific station, one
about process boundaries — and the tests were all offline and hermetic. **A hermetic suite cannot
falsify a claim about the machine.** That is not an argument for integration tests here (there is
one dongle and no dev receiver, DEC-0011); it is an argument for writing the environmental
assumption down as an assertion, which is what the health-budget test now does.

### Schedule regenerated, not resumed

The 07-29 run lost `A@00:05` entirely, took a partial `B@06:05`, and lost `C@12:05` — three
damaged cells of the Latin square, which is precisely the time-of-day confound the design exists
to remove. Resuming would have analyzed a broken square. The schedule was regenerated for a clean
2026-07-30 start (completing 08-07), the stale state file was reset to `NONE` — otherwise the
first tick would have "harvested" a period that ran on *baseline* config and recorded it as arm B
data — and the aborted run's 88 samples were rotated aside rather than left to contaminate the
data log. **~10 hours of delay to keep the experiment valid was the cheap side of that trade.**

Also corrected: a comment claiming a `schedule --generate <date>` mode that **has never existed**
in the code. The dev-side recipe that actually produces the table is recorded in its place.

---

## DEC-0062 — Logs are an egress path the read-guard does not cover; never log key material

**Status:** Accepted · **Date:** 2026-07-29 (S57b) · **extends** DEC-0047 from configs to logs ·
**applies** DEC-0046's layer question

### The finding

`pressure_service.py` logged `api_key[:8]` at INFO on every weewx startup. Eight characters, not
the whole key — but *where* it lands is what matters:

- It sits in `logs/weewx.log` **and its 30 daily rotations**, in plaintext.
- **DEC-0047's `secret-read-guard` covers configs** (`weewx.conf`, `*.env`) — it does **not** cover
  `weewx.log`. So the single most routine operation in this repo, *tail the log to confirm a
  restart was clean*, walks straight past the guard and into an agent transcript.
- That happened **twice on 2026-07-29** in one session, both times while verifying a restart.

DEC-0047 modeled reading a *config* as an egress path. It did not model reading a *log*, because
nothing was supposed to be in the log. Something was.

### The rule

**Never pass credential material to a log call — not the value, not a prefix, not a slice.** If the
diagnostic question is "did the credentials load?", log the *answer* (`present`/`MISSING`), never a
fragment of the input. Resolve presence flags into locals **before** the log call, so no credential
attribute appears in a log argument at all — that keeps the invariant absolute and the checker
simple. *A checker with exceptions is a weaker checker*: the first draft of the test here allowed
"safe" truthiness reads, and the exception immediately made it ambiguous whether a given use was
safe. Removing the exception from the *code* was better than adding it to the *test*.

Guarded by `tests/test_pressure_service_no_key_logging.py`, which walks the AST rather than
matching the wording — a reworded log line stays green, a reintroduced credential does not — and
carries a positive control (DEC-0045) proving it still flags the exact line that shipped, including
the `[:8]` slice form that made the original look harmless.

### The layer trap, again

The first note written about this said `pressure_service.py` was *mounted* and could be patched
live. **Wrong.** `Dockerfile:117` bakes it, and `docker inspect` confirms it is absent from the
mount list — an `scp` would have been a **silent no-op** with a green checkmark, which is exactly
DEC-0031's trap and exactly what DEC-0046's standing question exists to catch. It was caught only
by actually asking "which layer wins in prod?" instead of trusting the note. **Ask the question
every time; a previous session's answer about a *different* file proves nothing about this one.**

### Deployment: deliberately deferred

The fix needs an image rebuild, and a rebuild restarts prod. Campaign A (DEC-0059/DEC-0061) is
armed and running an 8-day factorial; swapping the image mid-campaign would change the binary
under the arms and confound the very comparison the design exists to make. **The fix rides the
next image release after the campaign completes (~2026-08-07).** The exposure it closes is a
partial-prefix re-leak, and the full-key exposure it does *not* close (S41) has rotation as its
only real remedy — so nothing is gained by rushing it into a running experiment.

---

## DEC-0063 — Adopt the eaglehunt-ops session-context tiering standard; migrate at the next session

**Status:** Accepted · **Date:** 2026-08-01 (S59) · **Supersedes:** DEC-0030's Tier-1 table (the
tiered *idea* survives; the specific six-file always-load set does not) · **Executes:**
[eaglehunt-ops#130](https://github.com/WeatheredScientist/eaglehunt-ops/issues/130) ·
**Spec:** `eaglehunt-ops/STANDARD.md` (OPS-DEC-0078)

ops#130 offered the tiering standard to this repo and — unusually for a cross-repo ask — argued
*against* it: "the case here is genuinely weak, and deferring is a defensible answer," on the
grounds that this repo is the leanest in the forum at ~21K and migration would buy "maybe 6–8K
tokens." Adoption is this repo's call under OPS-DEC-0001, so the honest thing was to check the
premise rather than accept either the offer or the disclaimer.

**Call: adopt.** The premise did not survive measurement.

### What the measurement changed

Two of ops#130's numbers are wrong in the direction that matters, both measured here on 2026-08-01:

1. **The tree is not at ~21K.** It is at **~25.5K** (91,806 B across the six Tier-1 files). ops
   measured a tree that was already two session-closes behind.
2. **The saving is not 6–8K.** `CHANGELOG.md` (~7.6K) and the `DECISIONS.md` index (~4.6K) leaving
   the always-load set is **~12.2K on its own** — already more than the quoted total — and
   `STATUS.md` → `BOOT.md` at cap is another **~5.7K**. Against ~2K of new always-load
   (`CONSTANTS.md` + `MANIFEST.md`), the realistic landing zone is **~5–6K, not ~19K**. ops#130's
   own sentence is internally inconsistent: it names those two files as "most of" a total they
   individually exceed.

**The decisive number is neither — it is the rate.** Tier-1 measured at four consecutive merge
points:

| Ref | Session | Tier-1 |
|---|---|---|
| `376285d` | S57 | 75,987 B (~21.1K) |
| `8755028` | S57 | 76,617 B (~21.3K) |
| `7fece1f` | S57b | 83,874 B (~23.3K) |
| `3b86fb6` | S58 | 87,235 B (~24.2K) |
| `HEAD` | S59 | 91,806 B (~25.5K) |

That is **~+1.1K tokens per session close**, and it is structural: STATUS.md and CHANGELOG.md both
grow at every closeout by ritual (DEC-0052 steps 2 and 3). "Leanest in the forum" is a statement
about a moment, not a trajectory — at this rate this repo passes 35K within ten sessions. **A
defensible deferral has a half-life**, and that is the argument ops#130 could not make because it
measured once.

### The other two reasons

- **Both siblings have already migrated.** The dashboard and hyperlocal-forecast each carry
  `BOOT.md` + `MANIFEST.md`; ops carries all three. This repo is the last of the trio, and
  cross-repo consistency is a standing goal, not a nicety — the drift this repo has repeatedly paid
  for (DEC-0040, DEC-0050) is what divergence costs.
- **`STATUS.md` at 29.6 KB is ~3× the `BOOT.md` cap** and wants the trim on its own merits,
  independent of any standard. This session read all of it to act on two lines of it.

### The one thing this repo must NOT inherit — an addendum to §3

STANDARD.md §3 has the trio "load `ops/CONSTANTS.md` at session start," and separately notes this
repo is public and "may point at ops but must never quote it." **Those two clauses are in tension
here and the standard does not resolve it: `eaglehunt-ops` is PRIVATE and this repo is PUBLIC.** A
`CLAUDE.md` that tells its reader to load `ops/CONSTANTS.md` is a dead end for every external
contributor — which is the population this repo has and the other three do not. It also sits badly
with §10's "any repo can be resumed cold from `BOOT.md` alone."

**Resolution adopted here:** this repo's `CONSTANTS.md` is **self-sufficient for anyone who can
clone it**. It carries the public constants outright (placeholders per DEC-0012 —
`<NAS_HOST>`/`<NAS_USER>`/`<SSH_PORT>` as today), and any pointer to `ops/CONSTANTS.md` is marked
explicitly as an owner-only supplement, never as a prerequisite. This is closer to coffeeradar's
DEC-0017 posture ("if a doc points you at another project to find out what a rule is, that is a
bug") than to the trio's, and it is deliberate: the reason coffeeradar takes the shape and not the
pointer is *self-containedness*, and a public repo needs that for the same reason a self-contained
one does. Filed back to ops as a spec gap, not resolved unilaterally in their file — this repo does
not write across the boundary.

### Why the migration is not in this session

STANDARD.md §7 says migrate at a natural session end, when full state is in context — which is
exactly now. It was still the wrong call: this session stood at **~157K absolute context** when the
decision was made, against `AGENT-ECONOMY.md` §7's ~200K close-out ceiling (OPS-DEC-0068), and the
mechanical work is ~40K more. Stranding a governance migration half-applied — `BOOT.md` written,
`CLAUDE.md` still pointing at the old tier table — is materially worse than not starting, because
the repo would then have two contradictory entrypoints and a hook (`resume_pointer_for()`) choosing
between them by fallback order.

So the **decision** is taken here, where the state is, and the **execution** is a work order in
STATUS.md's next-session actions. That split is the point: §7's real requirement is that the
*judgment* not be made cold, and it wasn't. A fresh session executing a written work order re-reads
the Tier-1 docs at start anyway — those are the migration's inputs.

**Reversal clause:** if the migration lands and a session finds itself pulling `DECISIONS.md` and
`CHANGELOG.md` by name in most sessions anyway, the saving was illusory — the read moved rather
than disappeared. Record that on the second occurrence and reopen this decision; do not quietly
re-add them to the always-load set, which is how the accretion started.

### Execution — S60, same day

Migrated. Measured outcome, always-load set: **91,806 B (~25.5K tok) across six files →
25,819 B (~7.2K) across four** (`BOOT.md` 8,975 · `CONSTANTS.md` 4,238 · `MANIFEST.md` 5,480 ·
`CLAUDE.md` 7,126). A **72% cut**, at the optimistic end of this decision's ~19K estimate. `BOOT.md`
landed at 2,493 tokens against its ~2,500 cap.

Four things the plan did not anticipate, all resolved in-session:

1. **The shared archiver matched a different set of files than ops#130 predicted.** It moves
   *date-stamped* names, so it found three pre-governance root artifacts nobody had listed
   (`DECISIONS_staging_20260704.md`, `..._Consolidation_...`, `..._ClaudeCode_Kickoff_...`) and did
   **not** match the three `docs/handoffs/S3x-*.md` files ops#130 named for `ARCHIVE/` — those are
   session-numbered. Checked before moving: the root three are unreferenced by any live doc; the
   handoffs three are cited by path from `DECISIONS-FULL.md` and `CHANGELOG-ARCHIVE.md`. So the root
   three were archived and the handoffs were left in place with `MANIFEST.md` rows. **Moving them
   would have broken three live citations to satisfy a rule about the load path they were never in.**
2. **`docs/STATUS.md` did not fit in `BOOT.md`,** and forcing it would have blown the cap (rule 1
   forbids a bigger cap). Its content distributed by kind: live bench state → `BOOT.md`; open threads
   and housekeeping → `BACKLOG.md` verbatim; the four upstream threads → a new
   `docs/UPSTREAM-THREADS.md` (Tier 2). Resolved items collapsed to one-line pointers per rule 1.
   The file is then **deleted, not archived** — git history preserves it and a copy would violate
   rule 5.
3. **The hook was verified BEFORE the delete, not after.** STANDARD §5's hazard is that a `BOOT.md`
   matching no marker shape goes *silently* quiet. `resume_pointer_for()` was run against this repo
   while `docs/STATUS.md` still existed (returned `BOOT.md` as source), and again after the delete.
   Both passed. Doing this in the other order would have produced a repo that looks fine and has no
   resume pointer — the DEC-0106 failure shape: not wrong output, no output.
4. **A third copy of the broken validation-gate list was found in `AGENTS.md`** — still naming
   `ruff-format`, which DEC-0027 rejects. S59b fixed `CLAUDE.md`'s copy, S43 fixed
   `.pre-commit-config.yaml`'s. Three copies, three independent drifts, which is rule 5's thesis
   demonstrated rather than argued. All three now point at the single list in `docs/CONVENTIONS.md`.
   `CLAUDE.md`'s duplicated infra table went the same way — it had already gone stale on the
   reception baseline and the driver-vs-config layer table.

Not done, deliberately: `docs/ASSESSMENT.md` still describes STATUS.md as the source of truth. It is
a **dated audit artifact**, not live guidance; rewriting a historical assessment to match today would
destroy the record of what was true then. Flagged in its `MANIFEST.md` row instead.

### A second public-repo divergence, found during execution — `ARCHIVE/` stays uncommitted

STANDARD rule 3 says history is "preserved, not carried": retired material moves to `ARCHIVE/` and
stays in the repo. **That does not work here, for the same reason §3's `ops/CONSTANTS.md` pointer
does not: this repo is public and the others are not.**

`ARCHIVE/` turned out to be gitignored already (`.gitignore` carries `archive/`, which matches
case-insensitively on macOS), and the three files the shared archiver moved into it had **never been
tracked**. Before treating that as a bug to fix by un-ignoring it, they were scanned: two of the
three carry **IP-shaped and credential-shaped strings**. They are pre-governance conversation dumps
from S16, written before any of this repo's secret hygiene existed. Committing them would be a
DEC-0012 violation, and STANDARD §6 requires exactly this audit before any such file is committed.

**Call: `ARCHIVE/` stays gitignored and local-only, and `MANIFEST.md` says so at the top of its
`ARCHIVE/` section** — because the failure mode otherwise is a manifest that points a fresh cloner
at three files their clone does not contain, which is the same dead-end-for-external-contributors
problem this decision already called out once.

Nothing is lost: those three were untracked working files all along, and genuinely retired *repo*
content (`docs/STATUS.md`, every superseded revision) is preserved in **git history**, reachable
with `git log --follow`. For a public repo, git history *is* the archive; a committed `ARCHIVE/`
directory is a private-repo affordance.

Both divergences share one root cause worth stating plainly: **the standard was written by and for
private repos, and its two "preserve/share by pointing at a file" mechanisms — `ops/CONSTANTS.md`
and `ARCHIVE/` — both assume every reader has access the public member's readers do not.** Reported
to ops#130 as a spec gap, not patched into their file.

---

## DEC-0064 — Campaign B: the no-LNA RX campaign, with an overnight pilot and an owner-gated swap night

**Status:** Accepted (design) · **Date:** 2026-08-01 (S61) · **Executes** the second half of
DEC-0059's two-campaign design · **applies** DEC-0046 (bias tee is image-layer) ·
**carries** DEC-0062's deferred deploy · owner-directed on timing, gating, and the pilot

### What this settles

Campaign A (LNA in circuit) self-terminates 2026-08-07T00:05. This decision pre-registers
everything that follows so the swap night is execution, not derivation: the LNA comes out, the
bias tee goes off, an overnight pilot bounds the no-LNA gain curve, and campaign B (the no-LNA
Latin square) runs 08-08T00:05 → 08-16T00:05. Checklist: `docs/CAMPAIGN-B-RUNBOOK.md`.

### The forensics that reframed the baseline

The working assumption — "the pre-LNA baseline is 67.5%" (S29's changelog) — did not survive
contact with the archive. A one-time local copy of the archive DB (cold backup, integrity-checked)
shows exactly two `rxCheckPercent` plateaus, both dead flat, with the transition hidden inside the
metric-dark gap (the pct_good deadlock, dead 06-18 → 07-05):

| Era | Config | Mean | sd (5-min bins) | n |
|---|---|---|---|---|
| 2026-06-02 → 06-18 | gain 207 | **67.45** | 3.22 | 4,321 |
| 2026-07-05 → 07-27 | gain 372, LNA in | **74.83** | 4.13 | 5,948 |

The record contradicted itself about the June plateau's LNA state: S29 calls it "the pre-LNA
baseline," but DEC-0017 says the gain-207 lock came from the 06-01 sweeps *with* the preamp, and
that the owner was evaluating *without* the preamp as of 07-04 — placing the no-LNA period inside
the dark gap, where no honest telemetry exists. The bias tee entered the image at v2.0.2
(~05-31); session transcripts carry no removal/install dates (that era predates this repo's
governance). **Resolved by owner memory (S61): the LNA was IN during June.** S29's "pre-LNA
baseline" label was wrong; DEC-0017's narrative was right. Two consequences:

1. **No honest no-LNA telemetry exists anywhere** — the pilot is the first real measurement,
   and Friday's first samples are discovery, not verification against a known band.
2. **Both plateaus are LNA-in, so their contrast is a same-hardware gain comparison:**
   207 → 372 gained **~7.4 pts** (67.45 → 74.83). Cross-era and uncontrolled (different weeks,
   the 06-16/17 anemometer swap sits inside the June window with no visible step), so it is
   corroborating directional evidence, not designed-experiment grade — but it retroactively
   answers DEC-0017's original 207-vs-372 question in 372's favor, independently of campaign
   A's forthcoming controlled answer.

### The design

**Overnight pilot (08-07 00:35–04:20), pre-registered as arm-selection input only.** Five
gain-only arms, 45 min each, strictly HIGH → LOW: 496, 449, 402, 372, 328 (all real R820T steps).
45 min = 9 five-min samples ≈ SE 1.6 pts/arm at the June-plateau sd — enough to see the curve's
shape, not enough to adopt anything. It is sequential and hour-confounded, the exact flaw
DEC-0048 exists to avoid in the campaign proper; its legitimacy is that of a pilot study: it
steers arm selection and shakes down the full apparatus (new image, bias tee off, swap → verify →
harvest cycle) on the same tick machinery the campaign uses, the night before the campaign
commits 8 days. High→low ordering makes the abort tripwire a feature: a weak low arm finding the
reception cliff halts with the high arms already harvested — an overnight abort IS a pilot
result. The window (00:35–04:20) sits inside the site's best-reception hours and clears the
hour-07 notch (BACKLOG §Durable RF findings), so pilot numbers read slightly optimistic vs 24 h
means; fine for bounding, stated so nobody mistakes them for campaign estimates.

**The H hold (08-07 04:20 → 08-08 00:05).** Arm A's exact settings under a distinct label. Two
jobs: the daylong no-LNA baseline-verification window (including how the 07/19 notch presents
without the LNA), and clean bookkeeping — the hold harvests under its own tag, and the
H→A swap at 08-08T00:05 is a real labeled swap, so the square's arm-A samples start clean
instead of inheriting a 20-hour pseudo-block (the phantom-block lesson from A's un-rotated log,
applied forward).

**The square (08-08T00:05 → 08-16T00:05).** Same Latin-square structure as A: 2×2 factorial,
6 h blocks, 32 blocks, 8/arm. Gain arms **{372, 496}**, not A's {372, 207}: with ~20 dB of
front-end gain removed the optimum moves up, and both of A's points would sit too low
(DEC-0059 said this at design time). 372 is the **cross-campaign anchor** — the same value ran
in campaign A, so the LNA contrast is measured at identical settings. 496 is the R820T maximum,
subject to Friday's pilot readout (GATE 2: a peak at/below 402 shifts the high arm; literals +
tests + redeploy is a 15-minute daytime task). The ex axis {0, 50} and `-fc 0 -ppm 0` are
**unchanged from A on purpose**: changing any other knob between campaigns would confound the
LNA contrast. Adoption bar unchanged (DEC-0059): ≥2.0 pts over the incumbent without a
duplicate-frame regression; incumbent wins ties.

**Abort floor 50% (was 55%).** The no-LNA baseline is unmeasured until the pilot; 50% sits
~5 SE below even a pessimistic 62% on a 30-min mean — forgiving on purpose, still far outside
noise. Data-loss exposure is unchanged from DEC-0059's analysis: an archive record nulls only
on a fully-dead minute.

**The swap night is owner-gated (owner's direction).** Nothing kills the container or touches
the bias tee until the owner's GO in chat, given only when physically at the dongle — the
antenna-disconnected window is the 20–40 s SMA swap, not minutes. Sequence: A terminates →
archive A's artifacts (`.campaignA` suffix) → deploy the B apparatus → **GO** → v2.0.12 with
`BIAS_TEE=0` (the night's one Class C command; kill→rm→run from `docker inspect`, never
compose) → physical swap → verify (bias-tee-off log line, DEC-0062 redaction, fresh archive
record) → `install` → pilot fires 00:35. Every failure path in the apparatus still restores
baseline and emails; the runbook adds the human-facing rollback (v2.0.11 retag) and the
"A didn't terminate" path (abort + postpone 24 h, never improvise at midnight).

**v2.0.12 carries the bias tee as configuration, not as a hardcoded flip.** `entrypoint.sh`
reads `BIAS_TEE` (default 1): the published image keeps powering LNAs for every existing user
of this public image, and our deployment turns it off with one env var. The off branch drives
`rtl_biast -b 0` explicitly rather than trusting the power-on default. The image also finally
ships DEC-0062's `pressure_service.py` redaction (deferred from S57b precisely to avoid a
mid-campaign-A rebuild) — and because the release lands *between* campaigns, campaign B runs
uniformly on one image with zero mid-campaign confound.

**Campaign A stays unread and unadopted through the gap.** Its winner is moot for prod the
moment the LNA comes out; its value is the LNA-in characterization and the honest multi-day
drift error bar on the eventual LNA-in vs LNA-out comparison (DEC-0059 declined bracketing on
exactly this plan). Analysis happens in parallel; nothing deploys from it.

### What would change this

A's completion slipping (schedule regenerates dev-side, 24 h postponement path in the runbook);
the pilot finding the gain curve peaked at/below 402 (GATE 2 shifts the high arm before the
square starts); the owner's answer on the June plateau (moves the expected-numbers table and
the acceptance band, nothing structural).

---

## DEC-0065 — The watchdog escalates and hands off; it does not acquire a bigger hammer

**Status:** Accepted · **Date:** 2026-08-02 (S62) · **Caused by** ERR-0005 · **amends** the
auto-remediation half of `weewx_monitor.py` · owner-approved, including an explicit decision
*against* the automatic container recreate the owner initially asked for

### What this settles

How the USB watchdog behaves when its remedy does not work. Before this it had exactly one
response, applied without limit and without evaluation. It now tries a bounded number of times,
checks whether each attempt worked, and escalates to a human when they don't.

### What the incident measured

ERR-0005 is the first time this loop was observed under a fault it could not fix:

| Observation | Value |
|---|---|
| USB resets fired | **9**, across 75 minutes |
| Resets that restored reception | **0** |
| Emails sent during the outage | **17** in 80 minutes |
| Emails distinguishing the 9th reset from the 1st | **0** |
| Time from outage start to correct detection | **8 minutes** (RECEPTION ALERT, 00:13) |

Reset #10 at 01:27:17 preceded, by 46 seconds, a strictly worse failure mode: the dongle still
enumerated for `rtl_biast` (device found, R820T tuner found, bias-tee command returning success)
while `rtldavis` could no longer claim it for streaming. The stall-recovery loop had separately
killed and respawned `rtldavis` ~18 times to no effect.

**Detection was never the deficiency and is not changed here.** The monitor caught the outage in
eight minutes and said so. What failed was everything downstream of that.

### The decision

**1. A remedy that is never evaluated is a ritual, not a remedy.** `watchdog_poll()` now judges
each reset by whether reception recovered within `RESET_VERIFY_S`. The old watchdog had no
concept of its own effectiveness, which is why 9 failures looked identical to 9 attempts.

**2. Bounded, then escalate.** Three ineffective resets and it stops resetting entirely and
sends one unmistakable alert. `RESET_VERIFY_S` (180 s) is deliberately **shorter** than
`RESET_CD` (300 s), so every attempt is judged before another is permitted — the counter can
never advance on an attempt whose verdict is still pending. Escalation lands ~18 minutes after
the first reset; for ERR-0005 that is an alert at ~00:29 instead of reset #10 at 01:27, and
resets #4–#10 never fire, so the worse failure mode never happens.

**3. "not running" is a different fault from "stalled".** A stall means the process runs and
yields nothing; "not running" means it dies on startup. A USB unbind/rebind does not fix the
latter and, on this evidence, plausibly caused it. `watchdog_not_running()` therefore never
resets — it escalates immediately.

**4. Alert economy is part of alerting.** Only the first reset of an outage emails. Nine
identical "RTL-SDR reset" notices is how the one alarm that mattered got buried; a channel that
cries wolf is not a channel.

### Why NOT the automatic container recreate

The owner's stated goal was to "autoinitiate proven fixes." Applying that bar honestly, the
container recreate does not qualify:

- **n = 1.** It worked once.
- **We cannot explain it.** The campaign apparatus's own `restore_baseline` did
  `kill; sleep 3; start` at 00:08:33 and reception stayed dead for 75 minutes; `kill; rm; run`
  at 01:48:41 restored it. Nobody has established why those differ. A stale device-cgroup entry,
  an orphaned USB claim, or simple coincidence with a fault that had cleared by 01:48 all remain
  live explanations.
- **`rm` is not reversible.** Automating it means reconstructing a `--privileged` container's
  full run line correctly, unattended, or production is simply gone.

Automating a remedy we cannot explain is how the nine-futile-resets pattern gets recreated at a
larger blast radius. Instead, `build_recreate_cmd()` derives the command from the **live**
container via `docker inspect` — never the NAS `docker-compose.yml`, which is stale and
decorative — and puts it in the escalation email. One paste instead of 105 minutes, without
handing an unexplained hammer to an unattended process. It returns `None` rather than a
half-right line, and redacts env values whose names look credential-shaped: this monitor ships
in a **public** repo and another user's container may carry real keys (DEC-0062).

### Deliberately unchanged

The vbus reset stays as the first-line remedy — it is bounded now, not demoted. `WU_RF_MIN_PCT`
stays at 60 even though it fired on the 03:15 dew dip in the no-LNA regime; retuning it is a
separate decision that wants campaign B's data, not this one's. Detection logic is untouched.

### What would change this

Establishing **why** the recreate works would make a phase-2 auto-recreate defensible — gated
behind a dry-run-tested run-line derivation, a hard attempt cap, and a refusal to act when
`docker inspect` fails. Evidence that the vbus reset has *never* resolved a stall would demote
it entirely rather than merely bound it. And a no-LNA regime that trips `WU_RF_MIN_PCT` routinely
would move that threshold — not this escalation logic.

### Related — checked and cleared, same session

ERR-0005 first logged what looked like a **campaign-A abort near-miss**: the apparatus declared
"did not produce records" at 00:08:21 while loop data flowed at 71% and a RapidFire record
published at 00:08:22. Since that check runs unattended for 8 days once campaign B starts, it was
resolved before B rather than after.

**It was not a near-miss — the abort was correct.** `health_ok()` waits for a new *archive* record
(`Added record` in `weewx.log`). The last one before the abort was **00:04:20**; the next was
**01:24:24**, eighty minutes later. `HEALTH_TRIES=36` (~180 s) ran its full budget against a
genuine absence. RapidFire loop publications are not archive records: the ~56 s reception island
was too short and too late to close a 60 s archive interval and clear the write lag. DEC-0061's
budget arithmetic holds and needs no change.

The lesson is about *reading* the evidence, not the apparatus: loop-level publications and archive
records are different things, and conflating them made a correct abort look like a defect.

---

## DEC-0066 — Campaign B is HELD until the instrument is trusted

**Status:** Accepted · **Date:** 2026-08-02 (S62) · **Defers** DEC-0064's execution (design
unchanged) · **caused by** ERR-0005 and two further outages the same day · owner's call, on a
recommendation that reversed twice during the evening as evidence arrived

### What this settles

Campaign B was prepared to launch the night of 08-02 — LNA already out, schedule shifted −4 days,
image built and verified, apparatus and tests green. It is **held, not cancelled.** Nothing about
DEC-0064's design changes; only the timing, and the bar that must be met first.

### The evidence

Three outages on 2026-08-02, on a station that had run clean for weeks:

| Window | Duration | Cause |
|---|---|---|
| 00:05–01:50 | 105 min | **unexplained** (ERR-0005). Driver alive, zero packets, 9 USB resets ineffective; fixed by a full container recreate |
| 13:47–13:49 | 3 min | **unexplained.** No engine shutdown, no DB error, driver never faulted. Self-recovered |
| 19:45–19:56 | 10 min | `database is locked`, aggravated by three uploader threads refusing to shut down |

### Why hold — and which argument actually carries it

Two arguments were raised. Only the second is load-bearing.

**The weaker one: abort risk.** Campaign A died on 08-02 because an outage coincided with an arm
swap — `health_ok()` waits ~180 s for an archive record, and there was none. Campaign B performs
**32 unattended swaps over 8 days**. Two unexplained outages in a day implies a real chance of
recurrence during one of them. But an abort is a *safe* failure: the apparatus restores baseline
and emails. Losing a campaign to an abort costs time, not correctness.

**The stronger one: the instrument is not trusted.** Campaign B measures reception percentage. A
receiver that intermittently loses 50–100% of its packets for reasons nobody has explained does not
produce a null result — it produces **noise that is shaped like a result**. Arms would differ, means
would compute, and a difference could be entirely an artifact of when the deafness happened to fall.
That is strictly worse than an abort, because an abort announces itself and a contaminated dataset
does not. Campaign A's data survives only because it ran clean for three days before it died.

An experiment whose instrument is behaving unpredictably should not be run on the grounds that the
apparatus around it is well built. The apparatus was never the doubt.

### The cost of holding, stated honestly

The schedule slips again (it had already moved up 4 days). The `SCHEDULE=` literals now sit in the
past, so a future launch must regenerate them — an `install` against stale dates would jump straight
into the middle of the square, which is a trap worth naming loudly in `BOOT.md`.

Against that: prod stays LNA-out either way, so the accidental **H-hold data keeps accruing** — and
per unit time it is currently worth more than a campaign that aborts on day three. As of the S62
close: n=1106 windows, mean **72.0%**, versus campaign A's pooled LNA-in 72.4%. Still not a clean
comparison (A pools the gain-207 arms and is biased low), and still not adoption evidence.

### What would change this

Any of: an established cause for the two unexplained outages; a bound on them tight enough that
their contribution to an 8-day mean is provably negligible; or several days of clean LNA-out running
that makes 08-02 look like a single bad day rather than a new regime. The DB-lock/thread-hang defect
should be fixed regardless — it is independent of the RF question and converts any future momentary
error into a multi-minute outage.

**Do not treat "the apparatus is ready" as the launch condition.** It has been ready since S61. The
condition is that the receiver's behavior is understood.

## DEC-0067 — The recurring dropouts are process freezes, not RF loss, and the driver's own watchdog proves it

**Status:** Accepted · **Date:** 2026-08-03 (S63) · **Reclassifies** the evidence behind DEC-0066 ·
**partially answers** DEC-0066's "explain the two unexplained outages" gate · **corrects** ERR-0005's
framing of the 13:47 event · does **not** change DEC-0064's design

### What this settles

The "unexplained reception dropouts" that held campaign B are **not reception dropouts**. They are
freezes of the weewx process. The receiver was working the whole time. Two different phenomena had
been filed under one name.

### The proof — the driver's 150 s watchdog is a discriminator, and it was there all along

`genLoopPackets()` (`rtldavis.py`) is a loop:

```
while self._mgr.running():
    if int(time.time()) - time_last_received > 150:
        raise weewx.WeeWxIOError("rtldavis process stalled")
    for lines in self._mgr.get_stderr():   # returns after at most 10 s
        ...
        time_last_received = int(time.time())   # only on an actual packet
```

`get_stderr()` is bounded at 10 s by construction. So a **running** main thread that hears no RF
returns to the top of the `while` within 10 s and raises at the 150 s mark. That is not a theory —
it is what happened 21 times during ERR-0005.

Therefore, for any output gap longer than 150 s:

| Gap ends with `rtldavis process stalled` | Meaning |
|---|---|
| **yes** | the main thread was executing and genuinely heard nothing → **RF loss** |
| **no** | the main thread was **not executing** → **process freeze**; RF is irrelevant |

The silent gaps of 208–218 s never raised it. The main thread was not running.

### The measurement

| Day | Driver-detected RF stalls | Silent process freezes |
|---|---|---|
| 2026-07-30 | 0 | 1 (08:04, 218 s) — **LNA still in** |
| 2026-07-31 | 0 | 0 |
| 2026-08-01 | 0 | 0 (but one `database is locked` restart, 15:08) |
| 2026-08-02 | **21** — all inside ERR-0005 | 1 (13:46, 209 s) |
| 2026-08-03 | 0 | 1 (02:59, 208 s) |

**Genuine RF loss is confined entirely to ERR-0005.** Every other day measured zero. The freezes are
independent of it, recur at roughly one per day, and last ~3.5 minutes.

### Three consequences

**1. The standing watch is answered: the freezes are not new to the no-LNA regime.** One occurred on
07-30 with the LNA still installed. Removing the LNA did not cause them. That watch can close; what
replaces it is a watch on the freeze itself.

**2. The monitor's reception metric cannot tell the two apart.** It counts published output, so a
frozen process and a deaf receiver both read `WINDOW: 0/21 (0%)`. Every "unexplained dropout" in the
standing watch was scored by an instrument that cannot make the distinction the watch was about.
The log rule above **can**, and costs nothing to apply.

**3. A freeze does not merely lose data — it misdates the data it recovers.** Packets are stamped at
*parse* time (`pkt['dateTime'] = int(time.time() + 0.5)`), not receive time, so everything buffered
during a freeze collapses onto the resume instant. On 2026-08-03 the record for 03:00 was written at
03:03:24, 03:01–03:03 have no records at all, and the following record absorbed ~3.5 minutes of
packets. **This distorts exactly the counters campaign B measures** — first downward across the
frozen windows, then upward in the one that follows.

### What this means for campaign B (DEC-0066)

DEC-0066's hold was correct, and its stated bar — *"an established cause for the two unexplained
outages, or a bound on them tight enough that their contribution is provably negligible"* — is now
partly met and partly reframed:

- The recurring class is **explained in kind** (process freeze, RF unaffected), **bounded**
  (~1/day, ~3.5 min, ~0.4 % of wall-clock), and **pre-dates the LNA removal**.
- ERR-0005 remains unexplained, but it is now demonstrably a **single incident**, not the tip of a
  recurring pattern — the 21 detections that day and zero on every other day are the evidence.
- The load-bearing risk has moved. It is no longer "the receiver is unreliable"; it is
  "**the instrument conflates a software freeze with deafness**". A ~3.5 min freeze inside a 6 h arm
  block moves that block's mean by roughly 0.8 pts against a 2 pt adoption threshold — material, and
  removable by excluding freeze-affected windows rather than by waiting for clean weather.

**Campaign B stays held** — this decision does not launch it. But the condition for launching is now
a concrete, mechanical one (detect and exclude freezes) instead of an open-ended one.

### Ruled out, with evidence rather than reasoning

| Hypothesis | Killed by |
|---|---|
| NAS-wide I/O stall | influxdb's retention timer fired at 07:01:06.576 Z **mid-freeze**, sub-ms consistent with every other check |
| The S37/DEC-0036 stdout pipe wedge | live `weewx.conf` `[Logging]` has **only** a file handler — no console handler exists |
| Container CPU-quota throttling | DSM's 4.4 kernel exposes **no `cpu.cfs_quota_us` and no `cpu.stat`** — only `cpu.shares`. CFS bandwidth control is not in play |
| `pressure_service`'s HTTP call blocking the loop | 82 completed fetches, slowest **8.99 s**, zero abandoned |
| The monitor's 6-hourly archive read holding the lock | summaries run at HH:00; the freezes do not |
| The HH:04 six-hourly gap cluster | campaign A arm swaps at HH:05:02 — deliberate restarts, benign |

### What is still open

**Why the process freezes.** All threads stop together and nothing is logged — consistent with one
thread blocking inside a write to the bind-mounted log volume while holding the shared logging lock,
which would silence every other thread at its next log call. The box is chronically I/O-bound
(**18.6 % cumulative iowait**, load average 6/13/15 on four cores), which makes a multi-second — even
multi-minute — write stall plausible. **Not proven.** The discriminating observation is the thread
state during a freeze: `D` (uninterruptible I/O) versus `S`. A read-only watcher exists to capture it.

Upstream saw this and worked around it without diagnosing it — `get_stderr()`'s own comment reads
*"When a lot rtldavis packets are read, a hangup will occur regularly, sometimes of more than a
minute."* The 10 s cap in that function is that workaround.

**Separately, the driver's stall detection is structurally blind to this failure mode** and should
not be "fixed" by shortening the 150 s threshold — the threshold is correct for what it was built to
catch. A freeze is not the driver's to detect; it needs an external observer.

### Lesson

The evidence that separated two phenomena had been in the logs since before campaign A, and the
component that distinguishes them — a 150 s watchdog whose firing and *non-firing* are both
informative — was already deployed and already working correctly. What was missing was reading its
silence as data. **A watchdog that does not fire is telling you something.** Compare DEC-0035's
structurally blind test and DEC-0045's passing test with the wrong assertion: three variants of the
same mistake, which is trusting an instrument without asking what it is physically able to observe.

## DEC-0068 — Coffee-radar is a confirmed contributor to some process freezes, not a full explanation

**Status:** Accepted · **Date:** 2026-08-05 (S65) · **Extends** DEC-0067's open "why it freezes"
question · does **not** change DEC-0064's design · Campaign B's DEC-0066 gates are unchanged

### What this settles

Direct, measured evidence — not a timestamp inference — that coffee-radar's scheduled batch job
coincided with one weewx process freeze on 2026-08-04. This NAS runs three of the owner's projects
as containers (`weewx-rtldavis-v2`, `hyperlocal-forecast-api`, `coffee-radar`), and hyperlocal-
forecast has its own well-measured incident class on this same box (its own DEC-0162: coffee-radar's
scheduled runs are a confirmed cause of severe page-cache-eviction stalls there). The question asked
this session was whether that shared-NAS mechanism also explains weewx's freezes. The answer is:
sometimes, confirmed once, not always.

### The measurement

An overnight watcher (`ops/freeze_watch.sh`, this session — polls `weewx.log`'s size, captures a
paired 12-thread `S`/`D`/`R` sample 20 s apart on a stall, plus a `nasctl ps` container snapshot)
caught two distinct freezes the night of 2026-08-04:

| | Freeze #1 | Freeze #2 |
|---|---|---|
| Time (EDT) | 17:48:59–17:52:37 (~4 min) | 19:13:43–19:15:41 (~2 min) |
| loadavg at detection | 0.67 / 0.74 / 0.66 | **12.39 / 12.18 / 8.17** |
| coffee-radar running | No | **Yes — confirmed** |
| Thread states | all `S`, three isolated single-sample `R` blips | all `S` except `pid=30506 (rtldavis)`, which read `R` in **both** 20s-apart samples |
| `weewxd` main thread | `S` throughout | `S` throughout |

Coffee-radar's presence during freeze #2 was confirmed with `nasctl inspect`, not a name match:
its scheduled command (`docker run --rm --env-file … coffee-radar node src/index.js --parallel 3`)
never passes `--name`, so the running container gets a Docker-random name (`dreamy_merkle` on the
night in question) with its real identity visible only in the `IMAGE` field. Grepping `docker ps`
output for the literal string `coffee-radar` — the check this session ran first, against freeze #1
— structurally cannot match such a container; `ops/freeze_watch.sh`'s own coffee-radar detection had
the same bug and is fixed as part of committing it (greps the whole `nasctl ps` line, not just the
`NAMES` column). `nasctl inspect` showed the container had started **19:00:16 EDT**, 13m27s before
detection, and was still running well after recovery — a start time that lines up almost exactly
with coffee-radar's own documented 19:00 daily scheduled run. That schedule is **local time (EDT)**,
not UTC — a unit mismatch in this session's own first pass at comparing freeze timestamps against
it, corrected here.

### What this does NOT settle

- **Not the sole cause.** Freeze #1, the same night, shows the identical symptom (all `S`, brief `R`
  ticks, `weewxd` never `D`) with coffee-radar not running and loadavg normal. Either freezes have
  more than one trigger, or coffee-radar's presence is a contributing-but-not-necessary condition.
- **n=1 coincidence.** One correlated instance out of three total captured freezes (S64's 08-03
  23:23 one plus these two) is suggestive, not a base rate. The 4 historical freeze timestamps
  (07-30 08:04, 08-02 13:46, 08-03 02:59, 08-03 23:23) were re-checked against coffee-radar's
  corrected local-time schedule (07:00/19:00 main, 6-hourly watchlist, Monday 14:00 prodigal) and
  show no clean match for any of them — but a documented-schedule comparison is weaker evidence than
  a direct `docker ps`/`inspect` observation, and DSM's own coffee-radar run history, if it logs
  one, has not been checked.
- **Mechanism unconfirmed.** `weewxd`'s own main thread reads `S`, never `D`, even during the
  load-12 freeze — not literal I/O-blocking in the classic sense. CPU scheduling contention, page-
  cache eviction (the mechanism behind HLF's own DEC-0162 on this box), and memory pressure are all
  still plausible and undistinguished by the current instrumentation.

### Consequences

Campaign B's gates (DEC-0066) are unchanged: make the campaign metric freeze-aware, fix the DB lock.
This finding doesn't newly block or unblock B — freezes already needed exclusion from the campaign
metric regardless of cause. `ops/freeze_watch.sh` is now a committed, reusable diagnostic instead of
a scratchpad script rebuilt from session-transcript archaeology three sessions running (S63, S64,
S65) — any future freeze investigation, or a check that this is resolved, starts from a working tool
instead of a rebuild.

### Lesson

A one-shot container launched without `--name` is invisible to any check that greps `docker ps` by
name — its real identity is in `IMAGE`, not `NAMES`. This is a general NAS-ops gotcha, not specific
to coffee-radar: any future "is container X running" check on this shared box should grep the whole
`docker ps`/`nasctl ps` line, not assume a container's own image name is also its runtime name.

## DEC-0069 — The campaign metric moves to per-minute `rxCheckPercent`, and freeze exclusion is structural

**Status:** Accepted · **Date:** 2026-08-05 (S66) · **Closes** DEC-0066's second launch gate ·
**corrects** DEC-0067's "down then up" and BOOT.md's ~0.8-point impact estimate ·
design of DEC-0064 untouched · tool `ops/campaign_analyze.py`

### What this settles

DEC-0066 held campaign B on two gates, of which the real one was: make the campaign metric
freeze-aware. This settles *how*, and — unexpectedly — *how much it was ever worth*.

The answer has two halves. The larger half is a **source change**: the campaign was reading a
5-minute aggregate, and the same measurement exists at 1-minute resolution in the archive DB. The
smaller half is an **exclusion rule**, which turns out to be worth ~0.03 points once the source is
right.

### The defect, measured

`ops/rx_experiment.sh`'s `harvest()` scrapes the monitor's 5-minute `RECEPTION: NN%` line. A freeze
lands inside one of those buckets and drags the whole bucket down — **measured 16 % and 27 %** on
2026-08-04 against a ~72 % neighbourhood — so one bad minute destroys four good ones. Across a 6 h
arm block (72 such samples) that is `(72−16)/72 ≈ 0.78` points, which is where BOOT.md's ~0.8 figure
came from. **That figure was right, but only for that metric.**

The archive DB carries the driver's own `rxCheckPercent` — good CRC-decoded packets over theoretical
max, which S31 established as the honest metric — **per archive record, i.e. per minute**. At that
resolution the same freeze damages *one* record: `(75−10.31)/360 ≈ 0.18` points on the same block,
and ~0.05 pooled across an arm. Changing the source is ~4× of the fix before any exclusion logic
runs.

### The freeze signature in the archive

Scanned 2026-07-29 → 2026-08-05: **10 988 records, 33 gaps**. Every gap falls into one of three
classes, and they do not overlap:

| Class | `rx` before the gap | `rx` after the gap | n | Identification |
|---|---|---|---|---|
| **Process freeze** | anomalously low (4.0–17.2) | normal, non-NULL | ~10 | matches every freeze in the DEC-0067/0068 record |
| **Arm swap** | normal (63–85) | **NULL** | 12 | the HH:04 cluster — campaign A's own swaps |
| **Lock / outage** | normal | **NULL** | 4 | the two `database is locked` events, and ERR-0005 |

Population baseline for scale: median **75.0**, p05 **61.9**, p01 **56.5**. The freeze records at
4–17 sit far below p01 — they are not bad RF minutes, they are artifacts.

**The contaminated record is the one ADJACENT to the gap, not the minutes inside it.** Those minutes
are simply *absent rows* and need no handling at all — this is the finding that shrank the whole
design, because BOOT.md had assumed they scored as zeros. WeeWX assembles the freeze-start record
from a truncated accumulation period but still divides by the full nominal interval; `interval`
stays `1`, so **the row cannot identify itself as contaminated** and detection must be structural.

Worked example, 2026-08-04 (`Added record` write-lag in brackets; normal lag is 15–20 s):

```
17:47  rx=72.73  [19s]        19:12  rx=70.00  [16s]
17:48  rx=10.31  [232s]  <--  19:13  rx= 4.29  [153s]  <--
17:49  ABSENT                 19:14  ABSENT
17:50  ABSENT                 19:15  ABSENT
17:51  ABSENT                 19:16  rx=73.33  [17s]
17:52  rx=87.50  [15s]        19:17  rx=80.95  [17s]
```

### The rule

Three independent exclusions, deliberately not collapsed into one so each can be argued with
separately:

1. **Gap-adjacent** — drop the record immediately before *and* after any spacing gap. Symmetric, so
   it catches truncation and absorption without having to know which occurred.
2. **NULL `rxCheckPercent`** — the restart artifact; already treated as a gap by
   `summarize_reception_rows()`.
3. **Non-physical (`rx > 100`)** — an independent backstop; see below.

Plus a settle window (default 600 s, matching `rx_experiment.sh`'s `SETTLE_SECS`) after each swap.
Total cost on campaign A: **152 records excluded of 4 285 in-block, ~3.5 %.**

### Why not a magnitude threshold

"Drop anything under 20 %" is simpler and is **wrong**. The campaign exists to *measure* reception;
a rule keyed on magnitude discards genuine deep fades and biases every arm upward — precisely the
confound the Latin square was built to remove. Structure identifies artifacts; magnitude does not.
This is asserted as a positive control in `tests/test_campaign_analyze.py`, which proves both that
the structural rule keeps a real 30 % fade and that a magnitude rule destroys it.

### The 200 % record — DEC-0067's "up" is real, and rarer than stated

2026-07-29 03:10 carries `rxCheckPercent = 200.0`: a record that absorbed a 2-minute span while
still stamped `interval=1`. This is exactly the post-freeze inflation DEC-0067 predicted. **An
initial reading of two freezes found no inflation and concluded there was none; the 8-day scan
found this one.** So DEC-0067's "down then up" stands — with the correction that the "up" is
*conditional*, not routine (weewx usually advances past the gap and starts a fresh accumulator
instead), and appears once in 8 days against roughly ten freezes.

It matters out of proportion to its rarity: `summarize_reception_rows()` applies **no cap**, so such
a record contributes twice its expected packets — an *upward* push of ~0.35 points on a 6 h block,
larger than the downward push of the freeze that caused it.

### Campaign A, recomputed

12 blocks, 2026-07-30 00:05 → 2026-08-02 00:05, balanced:

| Arm | Settings | n | Mean | sd | vs. uncleaned |
|---|---|---|---|---|---|
| A | gain 372 ex 0 | 1038 | **74.81 %** | 8.22 | −0.02 |
| C | gain 372 ex 50 | 1044 | 74.37 % | 8.10 | +0.00 |
| D | gain 207 ex 50 | 1044 | 74.17 % | 8.22 | −0.03 |
| B | gain 207 ex 0 | 1038 | 73.87 % | 8.28 | +0.03 |

**The freeze-aware correction is ±0.03 points** against a 2.0-point adoption bar — real, but ~60×
smaller than the estimate that made it a launch gate. Total arm spread is **0.94 points**; no arm
approaches adoption. Gain 372 beats 207 in both `ex` pairings but marginally; `ex` shows no
consistent effect.

**Cross-metric check:** BOOT.md records campaign A pooled at 72.4 % from the monitor scrape; this
reads ~74.3 % from `rxCheckPercent`. The ~1.9-point offset matches `weewx_monitor.py`'s own
documented "runs ~1–2 pts optimistic" note (the driver floor-divides the period, S31). Two
independent metrics agreeing on the offset is a real validation of both — **and it means A-vs-B must
be compared on the same metric**, which is now guaranteed because both are recomputed by the same
tool from the same source.

**Sealing note (honest disclosure):** DEC-0066 recorded that A's arm winner stays sealed until after
B. Validating this tool against real data necessarily computed it, and the numbers above are now
known before B runs. Pre-registration protects the *analysis plan* — DEC-0064 locked B's arms, and
DEC-0059 locked the adoption bar, both before any of this — so the design is not compromised. But
the unsealing was a side effect of tooling, not a decision anyone took deliberately, and it is
recorded here rather than left implicit.

### Two defects found while building the tool

Both would have produced confident wrong numbers rather than an error:

- **Pooled campaign attempts.** Campaign A aborted 2026-07-29 and restarted clean on 07-30. A bare
  run pooled the aborted 75-minute arm-B block with the campaign proper, giving arm B ~60 extra
  records — an unbalanced Latin square, printed as a tidy four-row table with nothing to indicate
  it. Fixed mechanically: the tool now detects multiple attempts in one apparatus log and says so
  (DEC-0040 — a docstring warning would not have executed).
- **Unbounded fetch.** Deriving the query's lower bound locally meant asking the NAS for
  `dateTime >= 0` and dragging the entire archive across ssh — measured: does not finish inside
  120 s. The bound is now resolved on the NAS from the apparatus log's first timestamp, before the
  query runs.

Also corrected: the report header named a window wider than the one actually analyzed when `--since`
excluded early blocks. Provenance a reader would have to verify by hand is provenance that lies.

### Consequences

- **DEC-0066's second gate is closed.** The remaining gate is the `database is locked` defect (try
  WAL mode first).
- `ops/rx_experiment.sh` is **unchanged** — the unattended, prod-writing apparatus was not touched
  to close this, and `harvest()` keeps producing its independent cross-check.
- Campaign B's readout runs `ops/campaign_analyze.py --campaign B`; the A-vs-B LNA contrast runs the
  same tool over both windows.

### Lesson

The instrument's *resolution* was a bigger error term than the artifact everyone was chasing. Five
sessions went into explaining why the process freezes; the metric defect it was supposed to be
corrupting was mostly an artifact of averaging the measurement into 5-minute buckets before storing
it. **Check what resolution a number was recorded at before designing a correction for it.**

## DEC-0070 — The DB lock is a 5-second timeout with a 10-minute penalty; WAL is the fix and a cross-repo mount blocks it

**Status:** Accepted · **Date:** 2026-08-05 (S66) · **Addresses** DEC-0066's last launch gate ·
**bounded, not closed** — the real fix is filed as ops#141 · **applies** DEC-0046 (mounted layer)

### What this settles

The `database is locked` defect is not mysterious and not a weewx bug. It is a **default**:
`weedb/sqlite.py:136` reads `timeout = to_int(argv.get('timeout', 5))`, the live config set none,
and the archive runs `journal_mode=delete` where a reader's SHARED lock blocks the writer. So a
reader holding the lock for **six seconds** produces `CRITICAL Database OperationalError`, weewx's
hardcoded **120 s** wait, and a restart — **5–10 minutes of outage**. The penalty is three orders of
magnitude larger than the cause.

Measured on 2026-08-02 (the CRITICAL lands *after* the teardown, because weewx shuts services down
in the exception path before logging):

```
19:47:16  ERROR Unable to shut down OWM thread
19:47:22  OWM: Published record 19:44:00      <- uploaders 3 min behind
19:47:42  rtldavis with pid 15 killed
19:47:44  CRITICAL Database OperationalError exception: database is locked
19:47:44  CRITICAL     ****  Waiting 2 minutes then retrying...
```

Live state at diagnosis: `journal_mode=delete`, `synchronous=2`, `page_size=4096`, DB **29.1 MB**,
SQLite **3.46.1**, WeeWX **5.4.0**.

### What shipped now

`timeout = 30` added to `[DatabaseTypes][[SQLite]]` in the **live** `weewx.conf`. A reader that takes
seven seconds now costs a seven-second delay instead of a ten-minute outage. 30 s, not 60 s,
deliberately: it stays under the 60 s archive interval so records cannot pile up behind a wait.

Verified in the running system, not in the artifact (DEC-0046):

```
resolved database_dict : {'database_name': 'weewx.sdb', 'driver': 'weedb.sqlite',
                          'SQLITE_ROOT': '/opt/weewx-data/archive', 'timeout': '30'}
timeout weedb will use : 30 seconds (default was 5)
```

Restart healthy: new archive record **106 s** after `kill`→`start`, inside DEC-0061's documented
~115 s worst case.

**Honest cost:** weewx now *blocks* up to 30 s instead of erroring. That trades a 5–10 min outage
for a ≤30 s stall — a good trade (a stall loses one record; a restart loses ten minutes) but it is a
new behaviour. Such a stall is indistinguishable from a DEC-0067 process freeze to
`ops/freeze_watch.sh`, and `ops/campaign_analyze.py` will exclude it via the gap-adjacent rule.
Both are correct; neither is a bug to chase.

### Why WAL is not shipped, and what actually blocks it

WAL removes the cause outright — readers stop blocking writers. It is blocked by a **cross-repo
mount contract**: `hyperlocal-forecast-api` bind-mounts the archive DB as a **single file**
(`SRC=…/archive/weewx.sdb DST=/data/weewx/weewx.sdb RW=false`). WAL needs `weewx.sdb-wal` and
`weewx.sdb-shm` beside the database; with a single-file mount those siblings can never appear in
that container.

**The initial reading of this was wrong and the correction matters.** The first assumption was that
the mount would also have to become writable, because a WAL reader needs to create the `-shm` index
— which would have meant granting a read-only consumer write access to weewx's archive directory,
a real regression. Tested instead of asserted, on the container's own SQLite 3.46.1, with a live
writer holding data in the WAL:

| Scenario | `mode=ro` reader |
|---|---|
| Directory mount, writable | OK |
| Directory mount, **read-only**, `-shm` present | OK |
| Directory mount, **read-only**, `-shm` absent | **OK** |
| **Single-file mount (today's HLF)** | **`OperationalError: no such table: archive`** |

SQLite's read-only WAL fallback handles the read-only case, so `RW=false` can stay and the fix is
*only* file → directory. HLF's in-container path stays `/data/weewx/weewx.sdb` either way, so **no
HLF code or config change is needed.** Note also that HLF's own
`observations/weewx.py::_connect_read_only` sets no busy timeout, so it takes Python's 5 s default
and is exposed to the same contention from the other side.

Filed as **ops#141** (`repo:hlf`, `tier:mid`) with the staged order: change the mount and verify HLF
under the *existing* `delete` journal first, so a failure there is unambiguously about the mount;
only then flip WAL, which is reversible via `PRAGMA journal_mode=DELETE`.

### The drift risk this creates

`weewx.conf` is the **mounted** layer (DEC-0046) and is never committed (DEC-0012). So this change
exists **only on the NAS**, in a file with no repo artifact and no CI. A future container recreate
from a stock config would silently revert it and nobody would know until the next ten-minute
outage. Recorded as a `CONSTANTS.md` row for exactly that reason — the deviation from stock has to
live somewhere a session actually reads.

### Guard finding, recorded because it is load-bearing

The NAS mutation that wrote the live production config **did not trip the Class C guard**. The
command was `ssh <nas> "python3 -" < script.py`: the guard pattern-matches the ssh command *string*,
which here says only `python3 -`, while the mutating code arrives over **stdin**. Any NAS mutation
can be laundered through this shape — and it is the shape `docs/CONVENTIONS.md` actively recommends
("batch remote work into a single `bash -s` session"). The owner had authorized this specific action
in chat, so nothing improper occurred; the point is that the mechanism did not enforce it.

The asymmetry is the sharp part: in the same session the *read* guard fired three times on `grep` or
`tail` appearing anywhere in a command string, including against files carrying no secrets, while
the high-risk mutation path had a straightforward bypass. Belongs to eaglehunt-ops (OPS-DEC-0060 —
a repo session may not edit the machine-wide floor).

### Consequences

- Campaign B's last gate is **bounded, not closed**. Outages are capped at ~30 s instead of ~10 min,
  which is enough to stop the defect contaminating a campaign; the cause is removed when ops#141
  lands and WAL is flipped.
- DEC-0067's reader list needs a correction: it named "the dashboard" as an archive-DB reader. A
  scan of every container mounting a weewx path finds only `hyperlocal-forecast-api` (the DB file),
  `eh-proxy` (the parent directory, read-only), and weewx itself. The dashboard reaches this data by
  another route.

### Lesson

Two defaults, five seconds apart, cost ten minutes each time they met. Neither was chosen — one was
weedb's fallback, the other was SQLite's journal mode — and the config that could have overridden
either was simply silent. **Before designing a fix, check what the untouched defaults actually are**;
the answer here was a one-line config change, not an architecture.

## DEC-0071 — WAL was tried and rolled back: the mount was never the only blocker, and my test that said otherwise was structurally blind

**Status:** Accepted · **Date:** 2026-08-06 (S66) · **Bounds** DEC-0070's WAL recommendation ·
**corrects** a test this session published as evidence · ops#141

### What this settles

DEC-0070 said WAL was the real fix for the `database is locked` defect, blocked only by
hyperlocal-forecast-api's single-*file* bind mount. HLF shipped the directory mount (its S235). WAL
was flipped at 06:56 EDT and **rolled back at 07:24**. It is not viable as scoped, for a reason that
was present all along and that this repo's own evidence missed.

### The test that was wrong

DEC-0070 published a four-scenario table, run on the container's own SQLite 3.46.1, concluding that
a **read-only directory mount works** with WAL and therefore `RW=false` could stay. That conclusion
was wrong because the test did not reproduce the condition it claimed to:

```python
os.chmod(tmp, stat.S_IRUSR | stat.S_IXUSR)   # the DIRECTORY only
```

It made the *directory* read-only. The files inside kept their read-write permissions, so SQLite
could still open `weewx.sdb-shm` for writing. **A Docker `:ro` bind mount makes the files read-only
too.** A WAL reader must write the `-shm` index to join the WAL; HLF cannot, so it silently falls
back to the main database alone — which in WAL mode stops advancing except at auto-checkpoints.
Result: HLF froze on a stale snapshot within minutes, exactly the failure DEC-0070 predicted for the
*single-file* mount and then declared solved.

This is DEC-0035's lesson recurring: **a passing test proves nothing if it is structurally blind to
the thing it is testing.** The scenario labels said "read-only"; the mechanism under test never was.

### The second blocker, which no mount change can fix

```
weewx.sdb       0777  root
weewx.sdb-wal   0555  root      <- read-only for everyone
weewx.sdb-shm   0777  root
```

SQLite creates the `-wal` here mode **0555**. Even a read-write mount would not let a non-root reader
write it. Any future WAL attempt must solve file permissions, not just mount granularity. This also
explains why a non-root SSH user could not checkpoint the WAL at all
(`attempt to write a readonly database`).

### Rolling back was the hard part

`PRAGMA journal_mode=DELETE` needs an **exclusive** lock; weewx holds a persistent connection, so it
failed with `database is locked`, and with the container stopped there is no `docker exec` to run it
in either. Resolved by making weewx do it: `[[[pragmas]]] journal_mode = DELETE` under `[[SQLite]]`,
which weedb applies on every connection (`weedb/sqlite.py:141-143`) as root, at startup, when it is
the only connection. **The pragma is left in place deliberately** — it re-pins `delete` on every
start, so an accidental WAL flip can never again silently strand a reader.

### Self-inflicted outage, recorded because the shape recurs

The pragma was first written as the scalar `pragmas = journal_mode = DELETE`. weedb iterates
`pragmas` as a **mapping**, so configobj requires a subsection; the scalar parses as a string,
iterating it yields characters, and weewxd crash-looped on
`TypeError: string indices must be integers`. **Prod lost ~6 minutes of collection** (CRITICALs at
07:18:58 and 07:20:22). Two process failures behind it, both this session's own:

1. The first rollback attempt opened with `SELECT COUNT(*) FROM archive` — a full scan of a 30 MB
   table under a live writer that **had already timed out once earlier the same session**. Repeating
   a known-slow query on an incident path cost a 120 s timeout at the worst moment.
2. The config shape was assumed from the field name rather than checked against the consumer, even
   though the consuming code had been read and quoted in DEC-0070 an hour earlier.

### Consequences

- **WAL is not viable as scoped.** Do not retry until both the mount *and* the `-wal` permission
  story are designed. ops#141 carries the detail.
- **The DB-lock defect stays bounded, not cured** — DEC-0070's `timeout = 30` caps outages at ~30 s
  against the old 5–10 min. That is most of the practical benefit WAL offered, at none of this risk.
- **HLF did not self-recover.** weewx and the DB were healthy and current within minutes; HLF stayed
  anchored on a `reference_time` from the crash-loop window with every core field in
  `missing_fields`. It needs a container restart, left to an HLF session (ops#141, relabelled
  `repo:hlf`). Whether a read failure can permanently poison that cached anchor is an HLF robustness
  question this incident exposed.
- **Campaign B is unaffected.** Its metric gate (DEC-0069) and its bounded lock gate (DEC-0070) both
  stand; nothing here changes the launch decision.

### Lesson

Two of the three failures in this sequence were *repeats of lessons already written down in this
repo* — a structurally blind test (DEC-0035) and a config assumed rather than verified against its
consumer (DEC-0031/0046). Having the lesson on file is not the same as applying it under time
pressure on an incident path. **When a change is going badly, stop and re-read the consuming code
before the next attempt** — every one of these was cheaper to check than to undo.
