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

**Update (S84d, 2026-08-15) — "n=1, not a base rate" now HAS its base rate; see DEC-0094.** An
hour-of-day split of the 40 DEC-0088-corrected freezes (2026-07-14 → 08-13) puts **12 in 18:00–21:00
against 5.0 expected (P=0.0027)** and **7 in this job's own ~18:30–20:00 window against 2.5
(P=0.011)**, spread over **10 distinct dates** — so the correlation this DEC could only observe once
holds across a month: **30% of all freezes in 12.5% of the day.** Two limits carried forward: the
cluster was identified post hoc and the omnibus X² does not reject uniformity (so this is
corroboration of this DEC's hypothesis, not independent proof), and **the mechanism is still the
open part** — this DEC's own finding that `weewxd` stays `S` and never `D` even at loadavg 12.39
means "correlates with" is still not "is blocked by".

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

---

## DEC-0072 — The MANIFEST indexes classes, and that makes each script's header a load-bearing artifact

**Status:** Accepted · **Date:** 2026-08-06 (S67) · **Amends** DEC-0063's tier-file structure ·
**applies** eaglehunt-ops STANDARD rule 9 (OPS-DEC-0098) · ops#145

### What this settles

`MANIFEST.md` had one row per artifact. That shape cannot hold a fixed cap: the row count tracks a
population that only grows — one row per ops script, per runbook, per handoff — so the file crosses
any cap by construction rather than by neglect. Measured at S67: 1948 tokens against a 1000 cap,
197% — the worst of the four member repos in the ops sweep.

The fix is not a bigger cap and not fewer artifacts. **Where every member of a set shares a
load-time convention, the index carries one row naming the set and the convention, and the instances
self-describe at their source.** `ops/*` + `scripts/*` collapsed from five per-artifact rows to one:
*the script's header comment is its manual — read it before using or extending one.*

### Why this was safe here, and how that was checked

Rule 9 is only sound if the convention actually holds. It was verified before being relied on, not
assumed: the headers of `soak_check.sh`, `rx_experiment.sh`, `campaign_analyze.py`,
`find_duplicate_frames.py`, `freeze_watch.sh` and `check_secrets.sh` already state why each exists
and which lying symptom it was built to catch — **richer than the MANIFEST rows that duplicated
them.** That is STANDARD rule 5 applied to the index itself: the row was the second copy.

Coverage went **up**, not down. The old index carried rows for 5 of the 11 harness scripts; six
(`backfill_container.py`, `backfill_influx.py`, `find_duplicate_frames.py`, `usb_watchdog.sh`,
`wxcheck.py`, `wxcheck.sh`) had no row at all. One class row covers all eleven.

### The obligation this creates — the reason this is a DEC and not a chore

A class row is a **promise about every present and future member of the set.** From now on:

- **A new script in `ops/` or `scripts/` must ship with a header that answers "why does this exist,
  and when would I load it?"** A script with a bare shebang silently falsifies the index. The index
  will not notice; nothing will fail; a future session simply will not find what it needs.
- **A fact that is true of one script belongs in that script, not in the MANIFEST.** Four such facts
  were moved back at S67: campaign A needs `--since` (`campaign_analyze.py`); campaign B is the
  loaded schedule and `install` refuses a stale one (`rx_experiment.sh`); `EXPECT_IMAGE` must track
  the deployed tag (`soak_check.sh`). Each had drifted into the index because the index was the
  thing being read.

This is the trade: the index gets cheap and stays cheap, and the cost moves to a discipline that has
to be maintained at the source. It is the right trade only while the headers stay honest.

### What was NOT done

The `docs/` rows were left per-artifact. Their "when to load" genuinely cannot be inferred from name
or location — `ASSESSMENT.md` needs its "read as a dated audit of S23" caveat, `ROADMAP.md` needs
its same-session DEC-0057 rule — which is exactly the exception rule 9 reserves.

### Result

`BOOT.md` 3734 → 2161 tokens (cap 2500); `MANIFEST.md` 1948 → 970 (cap 1000). Verified by running
`checks/tier-sweep.sh` itself against fixtures rather than by hand arithmetic — the tool that files
the issue is the tool that confirms the fix. MANIFEST landed at 3% headroom, deliberately not at
100% of cap: the dashboard's S193 diet hit exactly the cap with zero headroom and was over again
within a session, which is the failure this leaves room against.

---

## DEC-0073 — Supervise the USB watchdog, make its absence loud, and model its resets before campaign B

**Status:** Accepted (design; implementation follows) · **Date:** 2026-08-06 (S67) ·
**gates** campaign B · **extends** DEC-0069's gap taxonomy · **re-proves** DEC-0035

### What this settles

`ops/usb_watchdog.sh` was deployed 2026-05-22, hand-started once, and never ran again. Nothing
supervised it: no crontab entry, no pidfile, no boot task. It died no later than the 2026-07-08 NAS
reboot and was absent for three qualifying stalls on 2026-08-06. For ~2.5 months `BOOT.md` recorded
it as "deployed and live." Evidence: `BACKLOG.md` §USB watchdog.

Two defects, and fixing only the first would leave the more important one:

1. **It is not supervised.** A hand-started `tail -F | while read` loop cannot survive a reboot.
2. **Its absence is invisible.** A watchdog that is not running writes exactly the same log as one
   running with nothing to do: nothing. No observation distinguishes them, so the failure could only
   ever be found by accident — which is how it was found.

Defect 2 is the one worth deciding about. Supervision without observability just moves the silence.

### Decision

**(a) Supervise it the way the monitor is supervised.** `weewx_monitor.py:102-115` has run reliably
for months on a PID guard — read pidfile, exit 0 if `/proc/<pid>` exists, else claim it and release
via `atexit` — plus a scheduled task that re-launches every 5 minutes. The guard makes re-launch
idempotent, so the scheduler carries no state. Give `usb_watchdog.sh` the same guard and cadence.
Proven in this exact environment, no new dependency, survives reboots because the scheduler does.

**(b) Give it a heartbeat.** Touch a liveness file on each loop tick, so liveness is an mtime
comparison rather than an inference. Deliberately not a periodic "still alive" log line: that grows
the log without bound and buries the real events.

**(c) Make `ops/soak_check.sh` assert it — the structural half.** That script exists to answer "is
the station actually healthy, or does it just look Up?", and a dead watchdog is exactly that
question, which it did not ask. Add a criterion: heartbeat mtime within 2× the tick interval, else
red. Without this we fix one instance and leave the class, and the next unsupervised helper dies the
same silent way.

**(d) Treat a rising reset rate as a signal.** The watchdog treats a symptom. A watchdog that
silently papers over a degrading dongle is worse than none, so resets stay logged with reasons and a
rising rate should reach the monitor's alert path.

### The campaign-B interaction, and the call made

`ops/campaign_analyze.py` sorts every archive gap into three non-overlapping classes — **freeze**
(rx before 4–17 %, rx after normal and non-NULL), **arm swap** (rx before normal, rx after NULL) and
**lock/outage** (same shape as a swap) — validated over 2026-07-29 → 08-05, 10 988 records, 33 gaps.

**The watchdog was dead for the whole of that window.** A USB-reset gap is therefore a fourth class
the taxonomy has never observed. By shape — reception degrades into the stall, the dongle
power-cycles, reception returns — a reset would most likely be absorbed into **freeze** and silently
excluded. That may even be the right treatment, but it would be right *by accident*, and this repo
has been burned twice by precisely that (DEC-0035, DEC-0071): a test blind to the condition it tests
proves nothing about it. Enabling the watchdog also changes the apparatus of a pre-registered
experiment (DEC-0048), which must not happen implicitly.

**Chosen (owner call, S67): watchdog ON for campaign B, and `campaign_analyze.py` taught a fourth
gap class** that reads the watchdog log and excludes reset-adjacent minutes explicitly. Rejected:
leaving resets unmodelled (reintroduces the DEC-0035 shape, and B's headline number could be quietly
shaped by an intervention nobody accounted for), and disabling the watchdog for the campaign (an
unattended multi-night run with no USB recovery is the exact scenario it exists for). The change is
small because the apparatus already excludes gaps — this adds a source of truth, not a mechanism.

### Verified before deciding

- **The dongle has not moved:** `/sys/bus/usb/devices/1-3/` still reads `idVendor 0bda`,
  `idProduct 2838` (Realtek RTL2838), and `syno_vbus_reset` is present. Worth checking, because a
  silently wrong path would make every future reset a no-op that logs success.
- **The script is sound.** On 2026-05-22 it detected 3 stalls, fired 2 resets and correctly skipped
  the middle one for its 300 s cooldown. NAS copy byte-identical to repo (sha256 `fc65a0d7…`).
- **The monitor's guard was read, not remembered** — `weewx_monitor.py:102-115`.

### What this does NOT do

- It does not explain **why** the stalls happen. This is mitigation. The 08-06 burst — three in 40
  minutes, then ten hours of nothing — stays unexplained and is not closed here.
- It does not change the reset mechanism or the 300 s cooldown; both worked as designed.
- It does not touch the driver or the deployed image.

### Consequences

- Campaign B gains a pre-launch gate: the watchdog verified **running**, by heartbeat, not by a sha.
- `soak_check.sh` gains a criterion, so this class of silent death is caught by the tool whose job
  that already was.
- Installing the scheduled task is a NAS mutation: **Class C, owner-run.**
- **Lesson, and the reason this is a DEC rather than a chore: a sha match proves the FILE, never the
  PROCESS.** "Deployed and live — NAS copy matches repo byte-for-byte, zero resets since" was true in
  both its sub-claims and wrong in its conclusion. For anything long-running, liveness needs its own
  evidence.

---

## DEC-0074 — Retire `ops/usb_watchdog.sh`: the monitor IS the watchdog, and DEC-0073 solved a problem that did not exist

**Status:** Accepted · **Date:** 2026-08-07 (S67) · **Supersedes DEC-0073** ·
**corrects** the S67 blocker-4 finding · **re-proves** DEC-0031 against its own author

### What this settles

DEC-0073 concluded that the USB watchdog was dead and that three stalls on 2026-08-06 "went
unhandled". **The second half was false.** `weewx_monitor.py` — pid 5015, alive, log seconds old —
carries `reset_dongle()` (line 342) and `watchdog_stall()` with escalation (line 354), wired to
`'rtldavis process stalled'` at line 692. It handled all three stalls within seconds:

```
09:53:40 STALL detected → RESET: triggering syno_vbus_reset → done, idVendor=0bda
10:11:13 STALL detected → RESET → done
10:32:52 STALL detected → RESET → done
```

`ops/usb_watchdog.sh` is a **superseded standalone predecessor**. Its function was absorbed first
into `weewx_monitor.sh` (which still carries a `reset_dongle()` and is itself dead — it references
the pre-v2 container name) and then into `weewx_monitor.py`, which does strictly more: it verifies
whether a reset actually *worked* (`RESET_VERIFY_S`), escalates after `RESET_MAX_TRIES`
consecutive ineffective resets, distinguishes 'stalled' from 'not running', and records that a USB
reset does not fix the latter and may have caused ERR-0005.

**So the script is retired, not deployed.** Deploying it would have put a second, uncoordinated
resetter on the same dongle with an unshared cooldown, next to a monitor whose own source records
the 2026-08-02 incident of **nine resets in 75 minutes**. That is a regression, not a fix.

### How the wrong conclusion was reached, since the shape recurs

The evidence for "not running" was sound and is unchanged: the script logs `Watchdog started`
unconditionally, its whole 845-byte log holds one such line from 2026-05-22, nothing supervises it,
and NAS uptime bounded it anyway. What was never checked was **whether anything else was doing the
job.** Three sources were consulted — the watchdog's log, `weewx.log`, and the process table — and
all three are silent about the monitor. `weewx_monitor.log` was never read, and it holds the answer
in plain text.

This is DEC-0031's lesson turned on its author: *the artifact in front of you being wrong does not
establish that the system is broken.* "This component is dead" and "this capability is missing" are
different claims requiring different evidence, and DEC-0073 conflated them.

### What survives from DEC-0073

- **"A sha match proves the FILE, never the PROCESS."** Still exactly right, and it is what found the
  dead script in the first place. Now generalized: liveness needs its own evidence, and so does
  *absence of function* — check the whole system, not the one component you are looking at.

  ⚠️ **AMENDED 2026-08-09 (S68b, #147) — the lesson stands; the INSTRUMENT this DEC reached for does
  not.** The check written down here and in the deploy notes was *"process start time after the file
  mtime, via `nasctl ls /proc/<newpid>`"*. Measured on the NAS: `stat -c %y /proc/<pid>` reported an
  `rtldavis` as **17 seconds old** when `/proc/<pid>/stat` field 22 against `/proc/uptime` put it at
  **2.88 days**, corroborated by a container up 3 days with unbroken output. That directory's mtime
  tracks **access**, so anything that reads `status`/`cmdline`/`fd` underneath it first — as a
  liveness check naturally does — sees "just now".

  There is an irony worth keeping rather than smoothing away: this DEC exists because months of logs
  named an operation that never ran, and the probe it adopted in response would have reported a
  restart that never happened. *Replacing a bad signal with an unverified one repeats the error at
  one remove.*

  **What actually holds** — and what carried both the S67 and S68 verifications in practice, though
  neither said so at the time:
  1. a **startup line in the log** (`Monitor started`) timestamped after the file mtime;
  2. `/proc/<pid>/stat` **field 22** against `/proc/uptime` (HZ confirmed, not assumed);
  3. a **new pid** with the **old pid gone** (`/proc/<oldpid>` absent).

  Best used together. `ops/usb_forensics.sh` uses (2) and records the proc-dir mtime only under an
  explicit "ACCESS time, NOT start" label.
- **The `soak_check.sh` criterion**, repointed. It now asserts the **monitor's** liveness (live pid
  plus a log younger than 300 s — its poll is 30 s, and a live pid with a stale log means *wedged*,
  which is not the same as dead), because that is the process whose death would leave stalls
  unhandled and unalerted.
- **What DEC-0073 got right about the class:** this script had no criterion in `soak_check.sh`, and
  neither did the monitor. Now the monitor does.

### The real defect, which DEC-0073 walked past

All three resets on 08-06 **failed**:

```
09:56:45  RESET ineffective (1/3); bad windows still 8
10:14:16  RESET ineffective (1/3); bad windows still 10
10:36:23  RESET ineffective (1/3); bad windows still 15
```

Three stalls, three resets, zero recoveries, and the bad-window count climbing 8 → 10 → 15. The
monitor is working correctly and reporting that **the remedy does not work**. `soak_check.sh` now
carries a criterion for exactly this (`USB RESETS INEFFECTIVE`), because a watchdog that fires is
not the same as a watchdog that helps. This is open and unexplained.

### Consequence for campaign B, which is larger than DEC-0073 thought

DEC-0073 framed USB-reset gaps as a *new* class that enabling the watchdog would introduce. Wrong
again, and in the more expensive direction: the monitor has been firing resets all along — **nine on
2026-08-02, inside the 2026-07-29 → 08-05 window that `campaign_analyze.py`'s three-class taxonomy
was validated against.** So reset-adjacent gaps are already in campaign A's recomputed numbers,
classified as freeze or swap or lock. The fourth-class question is therefore not a pre-launch
nicety for B; it is a question about a result already published in DEC-0069. Still open.

### Consequences

- `ops/usb_watchdog.sh` and `tests/test_usb_watchdog.sh` deleted. Recoverable from git history if
  the standalone form is ever wanted; it should not be.
- **No NAS change was made, and none was needed.** Blocker 4's "deploy" gate on campaign B is void.
- `soak_check.sh` asserts monitor liveness and reset effectiveness.
- Two things stay open: why the resets do not work, and whether reset gaps have already skewed the
  campaign-A figures.

## DEC-0075 — Photograph the reset instead of reasoning about it: capture from inside the sudo grant, host-side through `/proc`

**Status:** Accepted · **Date:** 2026-08-08 (S68) · **advances** DEC-0074's open blocker 4 ·
**applies** DEC-0040 (prose does not execute) · **leaves DEC-0065 untouched**

### What this settles

The USB resets fire and do not work — 3/3 on 2026-08-06, 9/9 on 2026-08-02 — and the standing
hypothesis is explicitly *not* established: the reset may be treating the **device** while the fault
is the **consumer's grip** on it. `usb_reset.sh` is a driver unbind/rebind, not a power cycle, so the
dongle stays enumerated and nothing makes the stalled `rtldavis` inside the container drop its open
libusb handle.

That predicts two observable things, and `ops/usb_forensics.sh` is built to see either:

- **stale container view** — the host's `/dev/bus/usb/001/` gains a new `devnum` after the rebind
  while the container still shows the old node; or
- **surviving grip** — `rtldavis` still holds an fd on the pre-reset device node afterwards.

If both look clean across a real stall, **the stall is not a USB fault at all** and the reset is
treating the wrong thing entirely. That is a real answer too, and the capture is designed to be able
to return it.

### Why it had to be built before the evidence existed

The decisive capture needs a live stall: ~1/day, unpredictable, and gone by the time anyone looks.
There has been **no stall since the corrected reset code went live at 2026-08-07 19:28** (checked at
S68 open: zero `RESET` and zero `stalled` lines in the 08-07 and 08-08 monitor logs, both greps
positive-controlled against 1440/521-hit `WINDOW` counts). So there was nothing to read
retroactively and no way to harvest this after the fact — the apparatus has to exist first.

### The three design calls

**1. Host-side `/proc`, not `docker exec`.** The container's view is reachable as
`/proc/<pid>/root/dev/bus/usb/001/` and its handles as `/proc/<pid>/fd`. This fires *during a stall*,
and a wedged container can block an exec indefinitely — the capture would hang on exactly the event
it exists to record. `/proc` reads cannot. One pid, discovered by `comm`, yields every piece of
evidence, and `rtldavis` being **absent** is itself a finding (the 'not running' mode, a different
fault).

**2. Pre/post fire from inside `usb_reset.sh`, not from the monitor.** Both decisive reads are
root-only, and `weewx_monitor.py` runs as the unprivileged `weewx-monitor` user — which is *why* it
shells the reset out through sudo. The sudoers grant is scoped to `usb_reset.sh` alone (README Setup
step 4). Capturing from there therefore needs **no new sudoers grant** and lands the evidence at the
only two moments that matter. The monitor fires only the `+RESET_VERIFY_S` capture, host-side and
**self-labelled DEGRADED** — an unreadable fd section must never be mistaken for a released handle,
which is the same absence-is-not-evidence trap DEC-0074 cost 2.5 months to.

**3. Capture-only. The escalation ladder is unchanged.** DEC-0065 declined to automate the container
recreate while ERR-0005's cause was unknown; that reasoning is untouched. Mixing a remedy change into
the measurement meant to justify it would confound both. Three failed resets still produce an alert
and no further action — deliberately, and still open.

### The escalation this introduced, and closed

Having `usb_reset.sh` execute a helper means **the helper runs as root under the NOPASSWD grant**. On
this NAS mode 777 is common, so a helper writable by `weewx-monitor` would have converted that narrow
grant into arbitrary root execution — precisely what the dedicated-user design exists to prevent.

`usb_reset.sh` now verifies the helper is root-owned and root-only-writable before running it, and
**refuses loudly** otherwise while still performing the reset; `do_reset()` logs the script's output
on a zero exit so that refusal cannot become a silent no-op. Checked rather than documented, because
prose does not execute (DEC-0040). Positive-controlled by neutering the check and watching the
helper execute.

**Evidence is never load-bearing over the watchdog it observes:** a missing, broken or refused
capture always leaves the reset intact, proven by running the real script against a helper that exits
non-zero and asserting the unbind/rebind still happened.

### Status

**Deployed and verified 2026-08-09**, from merged tip `ad7e5a4`. `usb_forensics.sh` and
`usb_reset.sh` installed `root:root 755` (the ownership the guard depends on), `weewx_monitor.py` as
the service account; monitor restarted 3870 → 8810, proven by its own startup log line rather than a
sha. Smoke-tested live: pid discovery by `comm` works, the dongle is `1-3` / `0bda:2838` /
`devnum=5`, and the root-only sections self-labelled `DEGRADED` when run unprivileged.

**The smoke test immediately earned itself back**, which is the argument for running a capture script
on the real box rather than only where every `/proc` read fails by design. It reported `rtldavis` as
17 seconds old when the process had been up **2.88 days** — `/proc/<pid>` directory mtime is
**access** time, and the script reads files under that directory moments earlier. In a stall capture
that field would have asserted a restart that never happened: a fabricated event, in the one artifact
built to settle a question whose hypothesis is deliberately unsettled. Fixed in PR #146 (field 22 vs
`/proc/uptime`, HZ=100 confirmed not assumed).

⚠️ **This flaw is not confined to this script.** DEC-0074's own replacement for "a sha match proves
the FILE, never the PROCESS" is `nasctl ls /proc/<newpid>` against the file mtime — the same unsound
probe. The **lesson** stands untouched; only the instrument was wrong. What actually carried both the
S67 and the S68 verification was a **startup line in the log** timestamped after the file mtime.
Tracked as **#147**; also usable: `/proc/<pid>/stat` field 22 vs `/proc/uptime`, and new-pid-with-old-
pid-gone. Best used together.

---

## DEC-0076 — The secret gate missed `GMAIL_PASS`-shaped keys: the fifth hole, and the first found by routine control rather than by audit

**Status:** Accepted · **Date:** 2026-08-08 (S68) · **extends** DEC-0039/DEC-0045 ·
**closes** a future hole, not a live one

### What this settles

The gate's key list held `password` and `passcode` but nothing for the `_PASS` abbreviation, so
`GMAIL_PASS = "..."` was **undetected in every spelling** — spaced, unspaced, colon-separated.
`GMAIL_PASS` is the exact variable name `weewx_monitor.py` uses for its Gmail credential, so the hole
sat squarely under this repo's own secret.

**Nothing was ever leaked through it.** The tracked tree carries no `_PASS` literal (the sole match is
README's documented `NOPASSWD:` sudoers line) and no `GMAIL_PASS = "<literal>"` was ever added on any
ref in the full history. This closed a future hole.

### How it was found — the part worth keeping

Not by an audit. By the **routine positive control before an unrelated commit** (DEC-0045's standing
rule): a planted payload carried both an `api_key` line and a `GMAIL_PASS` line, the gate reported
only the first, and the asymmetry was visible for free. The rule that costs one command per commit is
what found the fifth instance of this gate being wrong.

### The fix, and why it is two detectors

- **bare `pass` in the key list.** Deliberately *not* `passwd`, which matches README's
  `NOPASSWD: /volume1/...` and reports the binary path as a credential. Bare `pass` cannot: the
  detector requires `[:=]` immediately after the key and `NOPASSWD` has `WD` there — the same reason
  Python's `pass` statement and `passed = True` do not trip it.
- **a literal matcher for the four-group app-password form.** It slips past the assignment detector
  *even with* `pass` in the key list, because that detector needs 8+ **consecutive** value characters
  and the four-group form breaks every 4. That is the shape Google displays and people paste.

Each was proven necessary by removing it and watching its own payloads leak.

### The false-positive half, which nearly shipped

`PASS` is listed separately from `pass` because **detection is case-insensitive and the allow-list
deliberately is not** — that asymmetry is what distinguishes a constant reference from a literal
(bug class 1). Without the uppercase spelling, widening the key list made the gate report
`weewx_monitor.py`'s own `os.environ` lookup and README's placeholder as credentials, and the
tracked-tree check failed.

**The harness caught that before it shipped.** A gate that cries wolf on a repo's own source gets
switched off, so the false-positive direction is not a nicety — it is half the fix. Harness: 41 → 51
cases, tracked tree still clean.

## DEC-0077 — Reset gaps do NOT contaminate campaign A's figures: the exclusion is class-independent, and the outage left no rows to mis-average

**Status:** Accepted · **Date:** 2026-08-09 (S68d) · **closes** blocker 5 ·
**bounds** DEC-0074's concern · **amends** DEC-0069's taxonomy completeness claim ·
**corrects** ERR-0005 / DEC-0065's reset count

### What this settles

DEC-0074 raised blocker 5: the monitor fired resets on 2026-08-02, **inside** the 07-29 → 08-05
window `campaign_analyze.py`'s three-class gap taxonomy was validated against, so reset-adjacent gaps
were sorted into freeze / arm-swap / lock-outage in the figures DEC-0069 published. It called this "a
question about an existing result, not a pre-launch nicety." Correct to raise. The answer is **no
contamination**, and the reasoning matters more than the verdict.

### The measurement

Every rotated monitor log spanning campaign A (`.11` = 07-29 through `.4` = 08-05) grepped for
resets. **11 resets, all on 08-02**, 00:11:23 → 01:27:20. Seven of the eight days are empty, which
independently corroborates DEC-0067's "0 detections on every other day measured".

Archive rows across the incident (`rxCheckPercent`, `interval`, 08-01 23:00 → 08-02 03:30):

| Time (EDT) | Row |
|---|---|
| 00:04 | **72.73%** — normal, and the last row before the outage |
| 00:05 → 01:23 | **80 rows absent** |
| 01:24 | **NULL** |
| 01:25 → 01:50 | **25 rows absent** |
| 01:51 | **NULL** |
| 01:52 | 57.14% — back inside the population |

### Why the figures are unaffected

That shape is precisely the **lock/outage** signature the tool already documents: *rx BEFORE normal,
rx AFTER NULL*. So the taxonomy classified it, and — the load-bearing point — **classification is
descriptive; exclusion is structural.** DEC-0069's rule drops the record on either side of **any**
gap, plus every NULL, plus `rx > 100`, without consulting the class. 00:04, 01:24 and 01:51 were all
excluded. The 105 absent minutes contribute nothing: absent rows are not zeros, which the tool's own
header already established and which is why the design shrank at DEC-0069.

**The feared mode did not occur.** The real exposure was never mislabeling — it was a reset outage
producing *present but low* rows, which nothing would exclude, because the tool refuses magnitude
thresholds on purpose (a threshold discards genuine deep fades and biases every arm upward). No such
rows exist here. The transition is normal → absent → NULL → normal with nothing low-but-present at
either edge.

### What IS wrong, narrowly

DEC-0069's taxonomy says "every gap falls into one of three classes, and they do not overlap". That
still holds as a statement about *shapes*. It is wrong as a statement about *causes*: a USB reset
outage is a fourth cause producing the lock/outage shape. Since treatment keys on shape, **no
analyzer change is warranted** — recorded so campaign B's reading does not re-open it.

### Residuals, both bounded, neither gating

- **01:52 (57.14%) survives the rule**, because it neighbours a NULL *row*, not a gap. It sits just
  above the population p01 of 56.5, so it is plausible as real. Worst case it is one truncated
  record: ≈ (72−57)/360 ≈ **0.04 pts** on a 6 h block, against a 0.94-pt observed spread and a 2.0-pt
  adoption bar.
- **105 minutes vanished from one arm's block** — ~2.4% of the campaign's 12 × 6 h. This costs
  **precision, not bias**: during a receiver outage the arm's true RF performance is unmeasurable, and
  a USB failure is not a property of the arm, so excluding it is the correct treatment rather than a
  concession. Which arm is identifiable from the apparatus log if it is ever worth knowing; it does
  not change the verdict.

### A correction to the record

The monitor log shows **11 resets**, not nine. ERR-0005 and DEC-0065 both state "nine resets in 75
minutes" and refer to "reset #10 at 01:27:17"; that event is the **11th**, and the span is 76 min.
Nothing downstream depended on the count — DEC-0065's argument is about unbounded retry, which 11
makes marginally stronger — but the figure appears in two decision entries and should be right.


## DEC-0078 — Image builds move to the NAS: the arm64 laptop can no longer cross-build linux/amd64

**Status:** Accepted · **Date:** 2026-08-10 (S70) · **amends** release mechanics
(`docs/CAMPAIGN-B-RUNBOOK.md` §Release mechanics, `CONSTANTS.md` §Release) · **applies** the
v2.0.3 NAS-build precedent

### Context

Every prior release was built on the dev laptop. For v2.0.12, `docker build --platform
linux/amd64` on the Apple-Silicon machine fails deterministically inside the first `tar zxf` of
the upstream `src.tgz`: every entry errors `Cannot open: Function not implemented` (ENOSYS from
the emulation layer) and the RUN step exits 2. Not flaky — reproduced identically. The failure
initially hid behind a `| tail` pipeline whose exit 0 was read as the build's own — the repo's
green-checkmark trap, caught because the tar noise was distrusted and the log read back.

### Decision

1. **Release images build natively on the NAS** (amd64 — the deploy target): `git archive` the
   merged tip → scp the tarball → extract to `build-vX.Y.Z/` → `nohup docker build` writing
   `build.log` ending in an explicit `BUILD-EXIT=$?` marker. Success is that marker plus the
   `Successfully tagged` line — never a pipeline exit.
2. **The deploy consumes the NAS-local image directly** — no Hub round-trip on the deploy path.
3. **Docker Hub publication is decoupled and follows prod proof**: `docker save` on the NAS →
   scp to the laptop → `docker load` → `docker push :vX.Y.Z`; `:latest` moves only after the
   station proves the release. Until the push lands, **Hub lags prod** — the reverse of the
   historical drift direction; `CONSTANTS.md` documents the window so nobody reads Hub as prod.

### Alternatives rejected

- **Toggle Docker Desktop's Rosetta/QEMU emulation** — the setting key is not even present in
  this version's settings store, the experiment is a global Docker Desktop behavior change for
  one repo's need, and the NAS path removes emulation instead of switching its flavor.
- **Build in CI (native amd64 GitHub runner)** — the structural fix, but it needs Hub
  credentials as repo secrets and a workflow design; deliberately not improvised the night it
  was discovered. Backlogged.

### Consequences

- NAS CPU absorbs builds (~10 min for v2.0.12); campaign-adjacent builds are pre-launch by
  construction, so the load never lands mid-square.
- v2.0.12 deployed 2026-08-10 from NAS build `9db5c1ddaac3` (tip `7b6fd42`), verified in the
  running system (ws.4 banner, bias-tee-off line, soak identity canaries green). Hub push
  landed the same day (S70 close): config digest on Hub verified identical to the NAS build; layers rode the transfer path near-uncompressed (283 MB vs ~120 MB typical) — content-identical, tightening belongs to the CI-build follow-up.

---

## DEC-0079 — Opt into the ops-wide `.claude/transient-state` convention (ops#113)

**Status:** Accepted · **Date:** 2026-08-10 (S71) · **adopts** ops#113 (commit `e5094a4`,
OPS-DEC-0067)

### Context

ops#113 proposed, and a later ops session built, a generic repo-opt-in mechanism for tracking
intentionally non-default, reversible prod/shared state — a debug flag flipped for a few hours, a
verbose log level, a temporary monitoring hook — so the revert doesn't depend entirely on a
session or the owner remembering to come back to it. Motivating case: this repo's own
`debug_rtld=2` prod flip (ops#112), tracked only by a STATUS.md note and a manually-filed ops
issue at the time. This repo's `BOOT.md` ordered backlog carried "Consider
`.claude/transient-state` (ops#113). Opt-in is this repo's call" since around S69 — this closes
that.

### Decision

Opt in. A repo registers a state with one line in a tracked `.claude/transient-state`:
`<revert-by-epoch> <tracking-ref> <description>`. The epoch is computed **once**, by whoever
files the entry (`date -v+3H +%s` / `date -d '+3 hours' +%s`), so the SessionStart hook does only
integer arithmetic against `date +%s` — never date-string parsing. Anything past its epoch is
flagged OVERDUE at the next session start. A line that doesn't parse (non-integer epoch, missing
ref) is silently skipped rather than guessed — a false "is this overdue" read would be worse than
an invisible malformed line. **Deleting the line is the whole close mechanism.**

`.claude/` is locally excluded via `.git/info/exclude` (not a committed `.gitignore`), so the file
needed `git add -f` to become tracked — the same precedent already set for `.claude/settings.json`.

**Left empty at creation.** No state active right now meets the motivating shape (a short,
easily-forgotten flip) that isn't already carried prominently in `BOOT.md`/`CONSTANTS.md` — for
example the `:latest` tag deliberately still pointing at v2.0.11 pending GATE 2 is a real
deliberate-non-default state, but it's already the lead item in `BOOT.md`'s active thread, so a
second copy here would be redundant rather than a safety net. The first real entry waits for the
next genuine short-lived, revert-planned flip — the ops#112 shape, not a multi-day campaign (which
already has its own dedicated tracking apparatus).

### Alternatives rejected

- **Decline to opt in** — rejected on cost: the mechanism is built, proven (ops's own test suite),
  warn-only (mirrors the draft-PR hygiene hook from #107, not a gate), and this repo's own
  governance history (stale ROADMAP/BOOT entries going unnoticed between sessions) is the same
  "nobody came back to it" failure shape, just applied to a different kind of artifact.
- **Backfill entries for existing non-default state** (the `:latest` pin, `BIAS_TEE=0`) —
  rejected: both are already tracked, prominently, in the tier-1 docs this session reads every
  time. Duplicating them here trades one drift risk (forgetting to revert) for another (two copies
  disagreeing).

### Consequences

- The next short-lived prod/shared-state flip in this repo gets a cheap, mechanical tripwire
  instead of relying on session memory or prose alone.
- `.claude/` stays locally gitignored for everything else; this file and `settings.json` remain
  the two tracked exceptions.

---

## DEC-0080 — Solar diode-floor correction: exact-code `StdCalibrate` zero at the config layer

**Status:** Accepted · **Date:** 2026-08-10 (S72) · **resolves** the S71 radiation-floor handoff ·
**relates to** DEC-0029 · **applies** DEC-0070 at apply time

### Context

At true zero irradiance the VP2+ solar sensor's diode dark current decodes to **exactly**
`sr_raw=1 × 1.757936 ≈ 1.758 W/m²` (`rtldavis.py` message type 6): near zero, only 0, 1.758 and
3.516 are representable at all. The floor flows into the archive, InfluxDB and all nine RESTful
uploads every dark minute — ~76 kJ/m²/day of phantom energy (12 h × 1.758). The June 2026 fix was
dashboard-only and presentation-layer; it regressed at the chart layer during the July supercard
refactor — the second time a per-path filter was dropped on refactor. The owner decided at S71 to
fix at the source; the full diagnosis and both drafted designs are in
`docs/handoffs/S71-radiation-floor-design.md` (verified there: radiation passes SensorQC's bounds
unrejected per DEC-0029, and `StdCalibrate` runs ahead of `LoopJsonWriter` and every RESTful
service in the live config, so one correction reaches every consumer).

### Decision

Option A — one `StdCalibrate` correction, exact-window and None-guarded:

    radiation = radiation if radiation is None else (0 if 1.75 < radiation < 1.77 else radiation)

- **Exact-code matching, not a tolerance.** The window brackets `1.757936` alone; 0 and 3.516 pass
  untouched. Range form because only `math.*` is confirmed in `StdCalibrate`'s eval namespace;
  None-guard because radiation is absent from most packets (ISS message rotation) and nullable
  after QC rejection.
- **Where it lives is the actual fix.** (1) The live NAS `weewx.conf` — the layer that wins in
  prod (DEC-0046). (2) `weewx.conf.example` — the **versioned, public artifact**; the June fix
  regressed precisely because it existed nowhere versioned. A reprovision from the example now
  carries the correction, and downstream users of the published extension get it documented in the
  WeeWX-idiomatic place for per-station sensor calibration. (3) A `CONSTANTS.md` live-config
  deviations row (DEC-0070) — **added at apply time, not before**: CONSTANTS records what IS live,
  and until the NAS edit lands the deviation does not exist.
- **Apply deferred to post-GATE 2.** Campaign B's pilot runs tonight unattended with no working
  dongle recovery; a config typo is a crash-loop-into-the-pilot risk (the `pragmas` scalar spelling
  cost ~6 min of prod, attended). The artifact is months old; one more night is free.

### Alternatives rejected

- **Option B — almanac elevation-gated service** (drafted in the handoff): the only design that
  distinguishes a genuine `sr_raw=1` twilight reading from the artifact. Rejected on three counts:
  it **also** needs a live-config edit (`process_services`), so it escapes none of the config
  fragility while adding image surface; it bakes one station's sensor calibration into the public
  image's default service set (dark current varies unit-to-unit — wrong layer for a published
  tool); and the edge it buys is a few minutes/day at one quantization step (~1.76 W/m², ~0.4
  kJ/m²/day) — **below the instrument's own resolution** — for a new service, tests and a NAS
  rebuild. Design preserved in the handoff; it could ride the #144 pressure rebuild if the edge is
  ever wanted.
- **Driver-layer zero** (`rtldavis.py` maps `sr_raw=1 → 0`): same collision as A but baked (a
  rebuild to change), and it ships one station's floor as decode truth to every user of the
  published driver.
- **Patch the dashboard chart a second time:** rejected at S71 (owner) — a third per-consumer
  filter is the exact shape that has now regressed twice.

### Consequences

- ~99%+ of the artifact removed at every consumer at once. Residual: a genuine twilight reading
  that quantizes to `sr_raw=1` reads 0 for a few minutes/day — accepted, below sensor resolution.
- Step-change in the historical series at cutover (night 1.758 → 0), accepted at S71; no
  retroactive rewrite. Dark rows before cutover keep the floor — any future retro-correction is an
  ERR entry (DEC-0025), currently not requested.
- **Verify at apply:** the first corrected night must read 0 through the dark hours. If 3.516
  (`sr_raw=2`) appears at night, the floor wanders one code — extend **per-code** (a second exact
  band), never a loose threshold.
- The dashboard's surviving `eh-ui.js` narrow-window filter becomes vestigial after cutover;
  retiring it is dashboard-repo work (DEC-0010) — ops-tracker note to be filed at apply. The
  regressed chart path needs no dashboard fix at all: post-cutover data arrives clean.

### Applied — 2026-08-11 (S73), post-GATE 2 as planned

- **Both files, not one:** the apply step surfaced that `restore_baseline` (in
  `ops/rx_experiment.sh`) copies `weewx.conf.rx-baseline` over the live conf at every campaign
  abort and at self-termination — a live-conf-only apply would be silently reverted by the next
  restore. The line went into **the live `weewx.conf` AND the rx-baseline snapshot**, identical
  and verbatim from `weewx.conf.example`. The durable statement lives in the `CONSTANTS.md`
  live-config deviations table (the DEC-0070 mechanism, as this entry required).
- **Runtime-verified the same morning:** weewx 5.4.0 booted clean with the line twice (08:55:17
  and 08:58:23 restarts) and published normally — the config-typo crash-loop this entry deferred
  around did not occur. Activated by the campaign's own restart path; zero added downtime.
- **Ops note filed:** eaglehunt-ops#154 (dashboard `eh-ui.js` filter vestigial).
- Dark-hours-read-0 verification due S74 (first corrected night 2026-08-11 → 12); the
  `sr_raw=2` / 3.516 extend-per-code rule above stands.

## DEC-0081 — The stall class is RF-dead episodes: resets demoted, events self-classify, episodes ledgered

**Status:** Accepted · **Date:** 2026-08-11 (S73) · **supersedes** DEC-0074's open question and
DEC-0075's hypothesis set · **vindicates** DEC-0065 · **amends** DEC-0073 · **relates to**
DEC-0067/0068, ERR-0005

### Context

DEC-0074 (S67) established that USB resets fire but never work — 11/11 failed on 08-02, 3/3 on
08-06 — and DEC-0075 built a forensics apparatus around two hypotheses: (a) a stale container
view of a re-enumerated device, or (b) a surviving file-descriptor grip. The 08-10/11 night
delivered three full capture sets (one effective-looking reset at 23:56, two ineffective at
01:52/01:59) and aborted the campaign-B pilot. The S73 differential — Sub-A collating all 11
capture files, Sub-B extracting the night timeline from three logs, Sub-C correlating HLF and
coffee-radar activity, main thread synthesizing against the driver source — answered the
question with a mechanism nobody had on the board.

### What the evidence established

1. **Neither DEC-0075 hypothesis occurred.** The device never re-enumerates (devnum 5 and node
   mtime unchanged since Aug 2 across every reset — driver unbind/rebind does not re-enumerate,
   so the stale-devnum prediction was a measurement-design error, not a finding), and the dead
   children hold zero fds.
2. **The driver's watchdog and respawn machinery work.** All three stalls show the identical
   healthy sequence: 150 s silence → `Caught WeeWxIOError: rtldavis process stalled` → pidof
   SIGKILL → ~60 s weewx retry wait → fresh child with the correct arm cmdline. The earlier
   "frozen parent / no respawn" reading was log-blindness: driver re-inits log `startup
   process`, not `Starting up weewx`.
3. **The stall class is RF-dead episodes.** Two that night: 23:52→00:01 (~9 min) and
   01:49→02:14 (~25 min). During the second, four fresh children across three gain configs
   (449, 449, 402) all produced nothing; recovery came gradually at ~02:14, minutes after the
   baseline revert — time-correlated, not action-correlated. The 23:56 "effective" reset was
   the same event shape whose episode happened to end while the monitor was watching.
4. **Resets are theater for this class.** ~17 attempts, zero demonstrable fixes; ERR-0005
   suspects reset #10 caused the strictly-worse dies-on-startup mode. ERR-0005's
   recreate-fixed-it (105-min episode, 21 driver detections = the same serial-respawn
   signature) now reads as coincidence with episode end — DEC-0065's refusal to automate the
   recreate was correct for the right reason before the reason was known.
5. **One real process bug: kill-without-wait.** ProcManager kills via pidof + `os.kill` and
   never reaps; the engine builds a fresh ProcManager per retry, so no instance holds its
   predecessor's handle. Three zombies stacked under one weewxd, forensically captured.
6. **External load is a contributor to at most one episode.** The 23:52 onset sits inside a
   real congestion window (coffee-radar ad-hoc ~23:58, HLF maintenance chain 00:10, measured
   15-min loadavg ~25 — extends DEC-0068's n). The campaign-killing 01:49 episode has no
   confirmed external correlate.

### Decision

- **Demote the resets:** `RESET_MAX_TRIES` 3 → 1. One hedge per episode for the genuine dongle
  wedge that has never yet been captured; the second stall escalates to the human (email still
  carries the built recreate command). The `not running` path stays no-reset (S62).
- **Make every event self-classify at the source (ws.5):** `STALL DIAGNOSIS` at the 150 s
  raise — `raw_stderr_lines=0` is a mute child (process/USB class, the only signature that
  would ever again justify USB-level remedies); `>0` is an emitting child (RF class) — plus a
  10-line `drain_stderr` tail. The RF-quiet mode (hops flowing, nothing decoding) never trips
  the 150 s watchdog because hop packets reset it, so a paced `DATA DROUGHT` line covers it.
- **Reap children (ws.5):** every spawn registers module-wide; shutdown waits on its kill;
  startup reaps predecessors. Upstreamable with the diagnosis lines (CHANGES rows 12–13).
- **Ledger episodes (monitor):** one row per ALERT→RECOVERY in `logs/episodes.log`
  (`onset|recovery|duration_s|stalls|resets|respawns|droughts|worst_avg|last_cmd`). This is
  the pre-registered LNA-verdict datum: does episode susceptibility differ LNA-in vs LNA-out —
  the owner's reportable result for similar sites (~50–70 m, trees, walls, non-ideal siting).
- **Accept guard aborts during episodes as designed protection.** No auto-restart rung:
  restarts show the same evidence pattern as resets (every "recovery after restart" is equally
  explained by episode end). An episode night costs a block; morning STOP-clear resumes;
  structural exclusion keeps the data honest.
- **Leave the episode root cause open, deliberately** — interference vs no-LNA front-end
  margin vs site is a post-campaign characterization question, to be answered with A×B data
  plus the ledger. ⚠️ **AMENDED S76 (DEC-0083): the LNA dates in this clause were wrong.**
  It read *"episodes predate the LNA removal: 08-02 and 08-06 were LNA-in"*. The LNA came out
  **mid-ERR-0005, early on 08-02** (S61: no no-LNA telemetry existed yet; S62: "first honest
  no-LNA telemetry accruing, n=1106 windows" and "the LNA was already physically out" at the
  01:48 recreate; S70: "out since 08-02"). So **08-06 was LNA-OUT**, and 08-02 only *straddles*
  the removal. The point this clause was making survives on 08-02 alone — that episode did begin
  LNA-in — but do not carry the 08-06 claim into the LNA characterization.
- `soak_check.sh` ineffective-reset criterion FAIL → WARN with the class-aware message — a
  criterion that fails on expected behavior trains people to skip the check (ops#147 item 6).

### Deployed (same day, before the 08-12T00:05 square start)

v2.0.13 NAS-built from merged tip `1530971` (`BUILD-EXIT=0`), swapped mid-H-hold with
identical mounts/devices/env + `BIAS_TEE=0`, ws.5 banner + DEC-0031 canary verified in the
running log, records within 35 s, soak 15/2/0. `:v2.0.13` on Hub; `:latest` stays v2.0.12
until proven. Monitor scp'd + sha-verified; its respawn needs the owner's path-scoped-sudo
kill (uid-1031 process). PR #159; tests 185 → 203.

## DEC-0082 — Campaign B square recovery: shift the whole schedule +24h rather than accept a lost block

**Status:** Accepted · **Date:** 2026-08-12 (S75) · **relates to** DEC-0064 (campaign B design),
DEC-0081 (RF-dead episodes)

### Context

A third same-day RF-dead-episode abort (18:05, 2026-08-11 — `30-min mean reception 47% < 50%
floor (arm H)`) tripped six minutes after S74 had verified the day's second episode "without
re-tripping" and written "square proceeds on schedule" into BOOT.md. Nobody was in the loop to
clear it overnight: the STOP sentinel blocked every 5-minute tick continuously from 18:10:01
through the S75 session-start tick (09:20:01, 08-12) — spanning the entire scheduled 00:05
A-arm swap. `due_arm()` reads the latest schedule row whose time has passed, with no memory of
why a tick was refused, so clearing the STOP at any point without editing the schedule would
silently join the square wherever the fixed 6-hour grid says it should be *now* — skipping arm
A's block 1 (and, depending on exactly when cleared, truncating whichever block was already in
progress) with no error and no visible sign anything was lost.

Root cause: confirmed the same DEC-0081 RF-dead-episode signature via `weewx_monitor.log` WINDOW
samples (an ~11-minute near-total reception collapse, 17:48–17:59, matching the 410s episode
already in `episodes.log`) — not a new failure mode, and not litigated further.

### The choice

`tests/test_rx_experiment.py::test_schedule_is_a_balanced_latin_square` pins every arm to land on
exactly `00:05/06:05/12:05/18:05` twice each — the diurnal-drift control the whole campaign
design depends on. That rules out a same-day off-grid restart (e.g. resuming at 10:05): it would
put arm A on an unbalanced slot and pass silently until the analysis stage, exactly the kind of
green-signal-resting-on-wrong-evidence failure DEC-0067/0074/ops#147 already catalog for this
repo. Three options were on the table:

1. **Clear now, accept the gap.** `due_arm()` swaps H→B immediately; arm A permanently loses
   block 1 (7/8 reps instead of 8), block B runs truncated. Fastest, but breaks the balanced
   design.
2. **Clear at the next slot boundary (12:05).** Same permanent loss for arm A, but avoids also
   truncating B. Marginal improvement, same core defect.
3. **Shift every square row (A → BASELINE) by a whole number of days**, preserving each row's
   exact time-of-day slot and the day-to-day cadence. The earliest valid slot for arm A is the
   *next* occurrence of its own slot — one day out, `2026-08-13T00:05` — not "now" as first
   floated to the owner; the balanced-Latin-square test itself is what proves this (a same-day,
   off-grid restart fails it).

**Chose (3), owner-confirmed after the tradeoff was corrected in chat** (the first framing
undersold the cost — "starts fresh from now" — before the grid constraint was checked against
the pinned test). All 33 rows from `2026-08-12T00:05|A` through `2026-08-20T00:05|BASELINE`
shifted to `2026-08-13T00:05` through `2026-08-21T00:05`, verbatim arm sequence, +24h uniformly.
17/17 `test_rx_experiment.py` tests pass unmodified, including the balanced-Latin-square and
chronological/self-terminating/not-fully-stale assertions — no test was loosened to make the
recovery fit.

### What shipped

- `ops/rx_experiment.sh` `SCHEDULE=` edited, pytest-verified, deployed to the NAS (sha-matched),
  `rx_experiment.STOP` cleared same session. `due_arm()` now returns `H` (unchanged) until
  2026-08-13T00:05, then swaps cleanly to `A` — full 8/8 per-arm balance preserved, at the cost
  of the entire remainder of 2026-08-12 (H continues to hold, which is what was already
  happening).
- **Deploy mechanics hit three independent guard/classifier layers** on the same `scp` action
  before landing: the Class C owner-confirm hook (expected), `secret-read-guard.sh` (blocked
  even *with* its own documented `command`-prefix escape hatch already applied — looks like a
  bug in that guard's own matching, filed nowhere yet), and a bare classifier denial on an
  `rsync` substitution with no mint path offered at all. Owner ran the final `scp` by hand after
  three automated attempts; the STOP clear itself minted cleanly on the second attempt (first
  refused, per the documented ~50/50 rate).

### Why this belongs in DECISIONS, not just BOOT

Not a one-off — it is the concrete instance the family's ops#147/#159 governance thread is about:
a "square proceeds on schedule" claim in BOOT.md was true when written and silently wrong six
minutes later, and the recovery path that preserves the pre-registered design (DEC-0064) is not
obvious from the schedule format alone. Future campaign recoveries should default to the
whole-day-shift pattern, not a partial-day one, and check the balanced-square test *before*
picking a target time, not after.

## DEC-0083 — The stall rate is measured, not eyeballed: the alarm was right, its evidence was not, and the onset is 08-10

**Status:** Accepted · **Date:** 2026-08-12 (S76) · **amends** DEC-0081 (LNA dates; ws.5
attribution) · **executes** ops#160 · **answers** ops#159's weewx bullet · **relates to**
DEC-0067/0068, ERR-0005

### Context

S75 read `logs/episodes.log` growing 2 → 4 rows in ~18 h and wrote "trending hot, not settling"
into `BOOT.md`. ops#160 filed that as the exact shape ops#159 warns about — a signal escalated
on eyeball rather than checked against its own distribution — and scoped S76 to measure it.

The expected outcome was deflation. **The measurement confirmed the alarm and invalidated the
evidence offered for it.** Both halves matter, and the second is the transferable one.

### Method — and the two traps in it

`ops/stall_baseline.py` (new, this session) is the executable form, because a prose rule saying
"measure it" does not execute (DEC-0040). It pulls every `rtldavis process stalled` line from all
31 daily rotations in one ssh round trip and clusters them.

- **The unit is an EPISODE, not a stall line.** When RF goes dead the 150 s watchdog raises,
  weewx waits ~60 s, respawns, and the fresh child hears nothing either — so one episode emits a
  stall line every ~3 m 40 s for its whole duration. **2026-08-02 is 21 lines and one event.**
  Counting lines would have scored a single incident as 21 and swamped every comparison.
  Threshold sensitivity is reported on every run: 15 episodes at 30, 45 and 60 min. The
  clustering was **validated against DEC-0081's independently-derived boundaries** for the
  08-10/11 night (23:52→00:01 and 01:49→02:14) — both recovered exactly.
- **`rtldavis process is not running` is a different class and is excluded** — the driver gone
  entirely, DEC-0081/S62's no-reset path, the strictly-worse mode ERR-0005 hit after reset #10.
  20 lines, **all on 08-02, none on any burst day**. Folding it in would merge the two failure
  modes the DEC-0081 diagnosis exists to separate.

### What the record says

Window 2026-07-13 → 2026-08-12 12:42 (30.5 d, 31 files), **left-censored** — the left edge is the
30-day retention policy, not the onset of the phenomenon. 41 stall lines → **15 episodes**.

| Window ending now | Episodes | Rank among all such windows |
|---|---|---|
| 24 h | 3 | 96.1st pct (peak 5, off it) |
| 36 h | 5 | 97.1st pct |
| **48 h** | **6** | **record maximum**, 98.3rd pct |
| **72 h** | **6** | **record maximum**, 98.2nd pct |

**"Trending hot" survives measurement.** No 48 h or 72 h window anywhere in 30.5 days matches the
current one. The 24 h figure is off its own peak, so the burst may be easing — but it is real,
and S75 understated rather than overstated it.

### Three corrections to how that conclusion was reached

1. **The onset is 2026-08-10 23:56, not the ws.5 deploy.** The v2.0.13 container's `StartedAt` is
   2026-08-11T22:05:22Z = **18:05 local** (NAS is UTC−4). **Five of the six burst episodes
   predate it**; only 08-12 01:36 runs on ws.5. ws.5 is exonerated, and the ledger's field of
   view — which opens at 16:34 on 08-11, mid-burst — was mistaken for the phenomenon's onset.
2. **It is not a simple LNA effect either.** Rates: LNA-in **0.40/day** (8 ep / 20.07 d) →
   LNA-out 08-02→08-10 **0.13/day** (1 ep / 7.92 d, the *quietest* stretch in the whole record,
   quieter than LNA-in) → 08-10→now **2.43/day** (6 ep / 2.47 d). Whatever changed, changed eight
   days after the LNA came out. That night is the campaign-B pilot; attribution stays open.
3. **The stated evidence was never commensurable.** Of the 4 ledger rows, row 3 (00:49,
   `stalls=0 droughts=10`) is drought-only, and `DATA DROUGHT` appears **zero times in every
   pre-ws.5 rotated log** (verified). RF-quiet episodes never trip the 150 s watchdog at all —
   hop packets keep resetting it — so they were **structurally invisible** before ws.5. Only 3 of
   the 4 rows can be compared to anything historical. "2 → 4 rows" compared two instruments.

### DEC-0081 amended on the LNA dates

DEC-0081 states *"episodes predate the LNA removal: 08-02 and 08-06 were LNA-in."* Measured
against the record: **S61 (08-01) says no honest no-LNA telemetry existed anywhere**; **S62
(08-02) reports "first honest no-LNA telemetry accruing, n=1106 windows" and "the LNA was already
physically out"** at the 01:48 ERR-0005 recreate; **S70 says "the LNA has been out since 08-02."**
The LNA came out **mid-ERR-0005, in the early hours of 08-02**. So **08-06 was LNA-out**, and
08-02 only *straddles* the removal. DEC-0081's argument survives on 08-02 alone — that episode did
begin LNA-in — but the sentence as written is wrong and would mislead the post-campaign LNA
characterization it was written to feed. Corrected in place, same pattern as DEC-0074's S68b
amendment.

### Why this belongs in DECISIONS

**A red signal resting on the wrong evidence, which happened to be true.** Every case in the
ops#147 catalog is a *green* signal on bad evidence, plus the dashboard's *false* red. This is the
third variant and the most dangerous, because being right rewards the method: the same 19-hour
look would have produced the same alarm on a station that had been perfectly healthy for a month,
and nothing in the reading could tell those apart. **A correct conclusion is not evidence that the
method was sound** — the sibling of DEC-0045's "a passing test is not evidence if the assertion is
wrong". Worth stating as its own item because the failure is self-concealing: a confirmed alarm
retires the question that would have exposed it.

Follow-on, deliberately not decided here: what changed on 08-10. Candidates are the campaign-B
pilot's high-gain arms (496/449/402 vs the 372 hold), the v2.0.12 image promoted that morning, and
ordinary weather. The ledger plus the A×B square are the instruments; this is post-campaign
characterization, as DEC-0081 already scoped it.

### Secondary sweep — which standing watches rest on a computed baseline (ops#160 job 3)

- **Freeze rate: measured 1.49/day, median 240 s** (45 freezes / 30.3 d). BOOT and DEC-0067/0068
  carried *"~once/day, ~3.5 min"*, inherited rather than computed. It is the right order of
  magnitude and **understates both terms by roughly 40 %**. Method: archive gaps > 150 s
  classified by BACKLOG's own rule — gap **with** a stall within ±5 min = RF-dead (21), gap at a
  campaign swap slot = arm swap (12), silent off-slot gap = freeze (45). *This refines the
  characterization; unlike the stall claim it overturns nothing.*
  **One confounder had to be removed first, and it would have inflated the answer by 60 %:** the
  S37 backfill (2026-07-13, ERR-0003's path) wrote records at `interval=15`, which read as an
  unbroken run of 900 s "freezes" — 28 phantom events, and the first cut of this measurement
  counted every one. Only rows at `interval=1` are comparable; a gap is meaningful only *between
  two genuine per-minute records*. The tell was that the run stopped dead at 07:12 next to a
  `weewx.sdb.bak-S37-preBackfill-20260713-072441` snapshot — visible only because the individual
  events were printed rather than just the summary rate.
- **Co-rejection grep (DEC-0054): still 0, now verified through 2026-08-12** and
  **positive-controlled** (the identical pipeline returns 2308 for a token known to be present).
  BACKLOG carried *"0 hits through 08-01 18:30"* — true, and 11 days stale. A zero from this
  pipeline is not believable without the control (single-token rule, memory of the false-zero).
- **Phantom-rainRate (DEC-0049): already has a live instrument** — `soak_check.sh` computes it
  every run (0 rows of `rainRate>0 while rain=0` in 998 archive rows this session). No gut-feel
  here; nothing to fix.
- **Humidity-spike (DEC-0044): unfired, method pinned.** Left alone deliberately — its arithmetic
  is settled and re-deriving it is what DEC-0044 forbids.

So of the four, one was gut-feel (freeze rate, now measured), one was measured-but-stale
(co-rejection, now refreshed), one was already instrumented, and one is correctly left pinned.

## DEC-0084 — Secret gate hole class 6: the app-password detector required quotes

**Status:** Accepted · **Date:** 2026-08-12 (S76) · **extends** DEC-0012 · **continues**
DEC-0039/DEC-0045/DEC-0076 · **found by** the routine pre-commit positive control

### The hole

`check_secrets.sh` carried two detectors that between them could not see an **unquoted** Google
app password:

- `_assign` requires **8+ consecutive** value characters. Google issues an app password as four
  4-character groups, so the run breaks at 4 and the rule never fires.
- `_apppw` (added S68 for exactly this shape) requires the value to sit **inside quotes**.

So a `GMAIL_PASS` assigned the bare four-group form was missed in **every** spelling — spaced `=`,
env-style `=`, and ConfigObj-style indented `gmail_pass = …` — all verified MISSED before the fix.
(The literal is described rather than written here for the same reason `check_secrets.sh`'s own
comment describes it: writing the example would make this entry a finding, and **a decision log
earns no exemption** — DEC-0045. The gate proved that live, going red on the first draft of this
paragraph.)

**Unquoted is not an exotic variant; it is the native form of the two files this repo must never
commit.** `weewx.conf` is ConfigObj, where bare values are the norm, and `monitor.env` is an env
file. The gate would have missed this project's own credential in the format its own configuration
writes it. `monitor.env` is gitignored (`.gitignore:5`), so the gate is the second line of defence
and nothing was ever leaked through it — this closes a future hole, as DEC-0076 did.

### Why it survived DEC-0076's fix

S68 planted the **quoted** literal as holes 25/26, the harness went green, and the neighbouring
spelling was never asked about. That is DEC-0045's lesson recurring one level down: a passing test
is not evidence if the assertion is incomplete. **The fix certified its own blind spot** — the
same shape as this session's DEC-0083, and the sixth time this gate has been wrong.

### The fix, and why it is anchored rather than loosened

    _apppw_assign="${_key}"'[[:space:]]*[:=][[:space:]]*["']?[a-z]{4}([[:space:]][a-z]{4}){3}'

Quotes become optional, but the rule is **anchored on `_key` + `[:=]`**. That anchor is
load-bearing, not decoration: four consecutive lowercase four-letter words occur in ordinary
English, so simply dropping the quote requirement would flag prose and comments across the repo —
a criterion that fails on healthy content trains people to skip the gate (ops#147 item 6).
Requiring the credential key immediately before the shape cannot fire on prose.

**Verified by the harness, not by inspection:** 3 new payloads (holes 27–29), 54 passed / 0
failed, all previously-good lines still pass, real tracked tree clean.

### One allow-list widening refused

The new rule flagged `monitor.env.example`'s own placeholder — a `GMAIL_PASS` assigned four
repeated-character groups in the app-password shape (again described, not written: see above).
The tempting fix was an allow term for those groups. **Rejected:** five of this gate's six historical
holes were allow-list defects, so widening the allow-list to accommodate a placeholder trades a
known-good detector for a new excuse path. The placeholder moved to `YOUR_GMAIL_APP_PASSWORD`
instead — the convention `CONSTANTS.md` already mandates — with the four-group shape documented in
a neighbouring comment, so no information is lost and no excuse path is created.

## DEC-0085 — The freeze-rate one-off becomes a tool: `ops/freeze_baseline.py`

**Status:** Accepted · **Date:** 2026-08-12 (S77) · **completes** DEC-0083's flagged follow-up ·
**executes** BOOT S77 job 3 / BACKLOG's "folding it in is an open follow-up" · **relates to**
DEC-0067/0068

### Context

DEC-0083 (S76) measured the freeze rate at 1.49/day, median 240 s — but as a one-off derivation
in scratch work, not a committed script. Both BOOT.md and BACKLOG.md flagged the same risk in the
same words: "this number decays unless someone re-derives it." The stall side already had
`ops/stall_baseline.py`; the freeze side did not.

### Method — reuse, not re-derivation

`ops/freeze_baseline.py` classifies archive gaps > 150 s using BACKLOG's own rule (gap **with** a
`rtldavis process stalled` line within ±5 min = RF-dead, checked *first*; gap at a scheduled
campaign swap slot (:05 past 00/06/12/18, confirmed against `ops/rx_experiment.sh`'s own
`SCHEDULE`) = arm swap; silent off-slot gap = freeze). Two reuse decisions, both to avoid a second
copy of something already correct (STANDARD rule 5):

- Stall timestamps come from `stall_baseline.fetch()` / `.stamps()` directly (imported), not a
  hand-prepared file — the prototype this replaces (found abandoned in the S76 session's own
  scratchpad, never shipped) had loaded them from a static `all_stalls.txt`, which would go stale
  the moment it aged past the next `weewx.log` rotation.
- DB connection constants (`DOCKER`, `CONTAINER`, `VENV_PY`, `ARCHIVE_DB`) come from
  `campaign_analyze.py`, the existing sanctioned archive reader, rather than a duplicate literal.
- `window_start()` — "left-censored at the oldest surviving log rotation" — was extracted out of
  `stall_baseline.py` into a shared function (+2 tests) so both tools agree on the same boundary
  instead of each computing it independently and risking drift between them.

Both of DEC-0083's traps carry forward unchanged: rows at `interval != 1` are dropped before gaps
are computed (the S37 backfill trap), and every individual freeze event is printed, never just the
summary rate.

### New: rolling-window placement for the freeze side

DEC-0083 placed the *stall* rate in its own history (24 h/36 h/48 h/72 h percentile ranking) but
the freeze measurement was a flat rate + duration stats only — never placed against its own
distribution. `ops/freeze_baseline.py` adds that section, the same technique applied to freeze
onsets. First read, this session: 24 h = 1 (36.6th pct), 36 h = 3 (62.9th pct), 48 h = 5 (78.3rd
pct), 72 h = 6 (66.9th pct) — **unremarkable across every window**, unlike the stall side's
record-max reading the same day. The two phenomena are moving independently.

### Validation against DEC-0083's own numbers

A live run reproduces the S76 figures closely: **21 RF-dead / 12 arm-swap / 45 freeze** (exact
match on the classification breakdown) and **median 240 s** (exact). The rate reads 1.48/day
against the recorded 1.49/day — the small drift is the ~14 additional hours of window between the
two runs, not a methodology difference. This is the positive control DEC-0045 asks for: the new
tool was checked against a known answer before being trusted for the next one.

### Why this belongs in DECISIONS

Closes a named, cross-referenced follow-up (BOOT S77 job 3, BACKLOG's own words, ops#160's
"secondary sweep, time permitting" scope) rather than leaving it as an implicit code change — and
records the first-ever placement of the freeze rate in its own history, which is new information
DEC-0083 didn't produce.

## DEC-0086 — `barometer_inHg` is an unflagged, already-corrected WeatherLink passthrough

**Status:** Accepted · **Date:** 2026-08-12 (S77) · **documents** `docs/INTERFACES.md` §1 ·
**relates to** DEC-0032 (`_qc` flag mechanism), DEC-0053 (InfluxDB provenance findings)

### Context

Owner question: does the barometer reading carry a correction we apply and flag for the dashboard,
or is it raw? Neither — the actual answer is a third thing, previously undocumented.

### What the code does

The VP2+ ISS **never transmits barometric pressure over 915 MHz** — there is no RF path for this
field at all. `pressure_service.py`'s `DavisPressureFetcher` polls WeatherLink's own cloud API
(`api.weatherlink.com/v2/current/<station_id>`, hourly) directly and prefers `bar_sea_level`,
falling back to raw `bar` if absent. `bar_sea_level` is **already sea-level-corrected by
WeatherLink's own cloud side** — this repo applies no elevation/temperature correction of its own
to this field; it relays whatever the API returns.

Two things worth recording precisely:

1. **No `_qc` flag marks it.** DEC-0032's mechanism (`docs/INTERFACES.md` §2) covers only
   `rain`/`rainRate` today. So `barometer_inHg` is indistinguishable on the wire from every
   RF-derived field beside it in the same loop packet, even though its correction (if any)
   happened entirely upstream and invisibly, on infrastructure this repo doesn't control.
2. **One fetched value backfills three internal keys.** `pressure_service.py:92-97` sets
   `barometer`, `pressure`, and `altimeter` to the *same* `self.last_pressure` when each is
   otherwise null. Normally these are three distinct quantities (raw station pressure vs. two
   different sea-level-correction formulas); here they collapse to one borrowed number. Only
   `barometer_inHg` is in the published contract (`docs/INTERFACES.md` §1's fields table), so this
   doesn't leak externally — but a future reader of the driver internals should not assume
   `pressure`/`altimeter` mean their usual distinct things in this codebase.

### Action taken

Documented in `docs/INTERFACES.md` §1 (this session). Cross-posted as a heads-up, not a change
request, to `eaglehunt-weather-dashboard#377` (that repo's own direct-heads-up channel) and
`eaglehunt-ops#162` (cross-repo record, `repo:weewx`/`repo:dashboard`). Nothing was changed in
`pressure_service.py` — this decision is documentation of existing, previously-unrecorded
behavior, not a design change.

### Open, deliberately not decided here

Whether `barometer_inHg` ever warrants its own `_qc`-style flag, or a provenance marker
distinguishing cloud-API-sourced fields from RF-decoded ones, is left to whoever picks up the two
filed issues — dashboard-side UI value and flag-mechanism scope are both judgment calls this
finding doesn't resolve on its own.

### Why this belongs in DECISIONS

A data-provenance fact about the published contract that was true for the life of this repo and
had never been written down anywhere — the same class of gap DEC-0053 closed for InfluxDB station
identity and archive correction flags. Future sessions and cross-repo consumers now have a citable
answer instead of needing to re-read `pressure_service.py` to rediscover it.

## DEC-0087 — RF-dead reception dips PAUSE the campaign instead of hard-aborting

**Status:** Accepted · **Date:** 2026-08-13 (S79) · **relates to** DEC-0081 (RF-dead episodes
"gate nothing"), DEC-0082 (schedule-shift recovery, same underlying failure shape), DEC-0083/0085
(freeze/stall measurement tooling), DEC-0014 (No-Rewrite Rule — this is a subsystem change to
`ops/rx_experiment.sh`'s abort tripwire, the "most dangerous thing in this repo's ops/ directory"
per that file's own test docstring)

### Context

The guard's 30-min-mean reception floor has, twice now, produced the exact failure DEC-0082 was
supposed to have made rare: an ordinary, self-resolving RF-dead episode trips `trip_abort()`,
which is STICKY by design (safety property #4) — sentinel, revert to baseline, halt until a human
looks. When nobody is in the loop at that moment, the halt just sits.

**S79's instance, fully reconstructed from `weewx_monitor.log`/`weewx.log`/`rx_experiment.log`:**
arm A swapped in cleanly at `00:05:02` (`arm A live and healthy` at `00:08:24`), ran clean for
1h20m at 66–79% reception, then a genuine RF-dead episode hit: `01:40:39` reception falling,
`01:42:23` **RECEPTION ALERT** (5 consecutive windows below 60%, avg 0%), `01:48:28`
`rtldavis process stalled` (the driver's own 150s watchdog), `01:51:33` **RECEPTION RECOVERY: 62%
avg after 9min** — fully back to normal. The 30-min mean, still dragged down by the dead window,
crossed the floor four minutes later anyway: `01:55:02` **ABORT: 30-min mean reception 43% < 50%
floor (arm A)**. STOP then sat uncleared for 7.5+ hours (spanning the 06:05 swap slot too) —
nobody was watching between the abort firing and this session's daily check picking it up. This is
structurally the same shape as DEC-0082's S75 incident (STOP present, unattended, spanning a
scheduled swap), just with a shorter unattended window that time (18:10 through the next
session's 09:20 start tick) than this time (01:55 through 09:23).

Two distinct phenomena currently funnel through the same `trip_abort()`: the guard's own
reception-floor check (a pure "is RF currently bad" signal), and `tick`'s own abort calls on a
failed config write or an unhealthy post-swap check (genuine operational failures, where "keep
going" would be dangerous — a bug in a new arm's command string should not be silently tolerated).
DEC-0081 already established that RF-dead episodes specifically are expected, noise-floor-driven,
and "gate nothing" as a *rate* — the abort mechanism treating every instance as urgent-enough-for-
sticky-halt was never matched to that finding.

### The choice

Three forks, each with a chosen answer (owner-confirmed in chat, S79):

1. **Scope: RF-dead only, not freezes.** "Reception re-established" is not a meaningful resume
   condition for a freeze — that is a process-wedge event with unproven root cause (BOOT.md
   blocker 1), not a signal-loss event. `tick`'s own abort paths (write failure, unhealthy swap)
   are untouched too, for the same reason: they are not RF-weather.
2. **Timing model: fixed slots, reduced exposure — not extended blocks.** The Latin square is
   pinned to `00:05/06:05/12:05/18:05` specifically to control diurnal RF drift
   (`test_schedule_is_a_balanced_latin_square`); that is the actual experimental control DEC-0082
   already protected once. Letting a paused block's end time slide by the paused duration would
   re-drift the whole remaining schedule off that grid — the exact confound the fixed-slot design
   exists to prevent. Instead, a paused arm simply accumulates fewer live minutes that rep,
   captured automatically in `harvest()`'s existing reception-sample accounting (no code change
   needed there) rather than compensated by moving clock boundaries. Whole-day shifts (DEC-0082's
   mechanism) stay reserved for the rarer case of a block getting wiped out entirely, as happened
   here (companion change, PR #171 / this session's schedule shift to 2026-08-14T00:05).
3. **Resume trigger: reuse `weewx_monitor.py`'s own RECEPTION RECOVERY line.** It already exists,
   is already proven (it fired at `01:51:33` today, four minutes before the mean-based abort even
   tripped), and needs no new detector. The alternative (wait for the same 30-min mean to climb
   back over the floor) was rejected as unnecessarily slow — stale bad samples keep dragging the
   mean down well after the episode itself has ended, which is the exact lagging-indicator
   behavior that let today's abort fire four minutes into an already-recovered station.

Two supporting parameter choices, not put to a separate question but stated with reasoning and
open to revision: a **120-minute escalation ceiling** (`PAUSE_CEILING_SECS`) — the longest RF-dead
episode on record is the 75.8-minute ERR-0005 outlier (`ops/stall_baseline.py`), so 120 minutes
clears every known case with ~60% margin while still escalating something genuinely novel (a
dongle fault, a disconnected antenna) to a human rather than pausing silently forever; and **no
email on an ordinary pause/resume** — DEC-0081 already called these "gates nothing," and paging
the owner for something routine and self-resolving is alert fatigue with no offsetting benefit.
The escalation path keeps its email, unchanged.

### What shipped

`ops/rx_experiment.sh`: a new non-sticky `rx_experiment.PAUSE` marker (`epoch|human` on one line),
parallel to `STOP` but self-clearing. `guard`'s existing 30-min-mean check is unchanged as the
*trigger* — the change is only in the *response*: a floor trip now writes `PAUSE` and logs `PAUSE:
...` instead of calling `trip_abort()`. No config or container write happens on pause (nothing is
being received during a true RF-dead episode regardless of which arm's gain is active, so there is
nothing useful to revert). Every subsequent `guard` tick while paused checks, in order: has
`recovered_since()` (new helper) found a `RECEPTION RECOVERY` line in `weewx_monitor.log` newer
than the pause's start (→ log `RESUME`, delete the marker, done) — or has the pause run past
`PAUSE_CEILING_SECS` with no recovery (→ delete the marker, call the unchanged `trip_abort()`,
full sticky halt exactly as before). `tick`'s swap path clears any stale `PAUSE` marker when a
scheduled swap fires regardless of pause state (a real swap supersedes it — the new arm gets its
own clean settle window). `trip_abort()` itself also clears `PAUSE` defensively, so a stray marker
can never linger past a real halt. `status` gained a `paused:` line.

Documented as new safety property #7 in the script's own header (properties #1–#6 renumbered not
at all — #7 is additive, referencing back to #4). 9 new tests in `tests/test_rx_experiment.py`:
pause-not-abort on a fresh floor trip (and that the live config is provably untouched), a no-op
regression on healthy reception, resume on a fresh recovery line, non-resume on a stale recovery
line predating the pause (guards against a previous episode's recovery line clearing an unrelated
later pause), escalation past the ceiling with the baseline actually verified restored, STOP still
short-circuiting before any pause logic runs even with a stale PAUSE also present, and
`recovered_since()` tested in isolation for all three cases (after/before/absent). 26/26
`test_rx_experiment.py`, 233/233 full suite. `tick`'s stale-pause-clear line is deliberately left
without a dedicated end-to-end test — exercising `tick`'s full swap path needs a real
`health_ok()` timing loop and `docker`, infrastructure the existing suite has never built for any
of `tick`'s other lines either (write failure, unhealthy swap) — consistent scope, not a new gap.

Shipped as PR #173, on its own branch off `dev` (independent of PR #171's schedule shift — the two
touch disjoint regions of the same file and are reviewable/mergeable in either order).

### Why this belongs in DECISIONS

Same class as DEC-0082: not a one-off, but the second occurrence of a named failure mode (STOP
sitting unattended across a scheduled boundary) that the ops#147/#159 governance thread already
tracks as a family-wide pattern. Also a subsystem behavior change to the abort tripwire DEC-0014
singles out by name as needing "a documented cause, an alternative, a migration plan, a DEC entry,
and explicit approval" before touching — this entry is that record, including the two rejected
alternatives (extend-block timing; keep the 30-min mean as the resume trigger) so a future session
does not have to re-litigate why they were not chosen.

## DEC-0088 — freeze_baseline.py's swap detection was schedule-only; ad hoc restarts were inflating the freeze rate

**Status:** Accepted · **Date:** 2026-08-13 (S80) · **relates to** DEC-0085 (built the tool),
DEC-0083 (the sibling stall-side measurement correction, same shape), DEC-0087 (ships the pause/
resume mechanism that will keep producing exactly this class of restart going forward), DEC-0082
(the earlier schedule-shift recovery, another ad hoc restart source)

### Context

S80 re-ran `ops/freeze_baseline.py` for its scheduled corroboration (BOOT S80 job 3, following
S79's "one elevated window — re-run for a second reading" watch item). The 48h window S79 flagged
(92.5th pct) had dropped back to unremarkable — but 24h and 36h had newly become elevated (95.9th/
94.0th pct), a *different* window than the one being watched. Before reading that as a real
short-window signal, the freshest event in the list was checked against other evidence: a 180s gap
at 2026-08-13 10:24-10:27, which lines up almost exactly with this same session's own tick log
(`10:25:01 tick: swapping A -> H`, `10:27:19 tick: arm H live and healthy`) — the S79 abort's own
self-heal restart, not a process wedge.

### What was wrong

`classify()`'s swap detection (`is_swap_slot`, added DEC-0085) only recognized the four *scheduled*
hours (`SWAP_HOURS = (0, 6, 12, 18)`, `:05` past each). It had no way to see a restart landing off
that schedule — and `rx_experiment.sh` triggers restarts off-schedule routinely: every abort's
baseline restore (`trip_abort()` → `restore_baseline()`), every DEC-0087 pause escalating past its
120-minute ceiling, and every tick's own self-heal after a STOP clears (today's case). Each
produces a real, expected archive gap while the container reboots and re-syncs — and the tool was
silently counting every one of them as a freeze.

**Verified against the log, not just inferred:** BACKLOG.md's own S79 entry noted the 2026-08-12
"21:04 freeze traced separately: it landed while STOP was still present from the 19:55:35 abort" —
without questioning whether the *other* freeze in that cluster, "19:55→20:02 (420s)", was itself
that abort's footprint. Checking `logs/rx_experiment.log` directly confirms it was:
`19:55:35 ABORT: 30-min mean reception 47% < 50% floor (arm H)` immediately followed by
`19:55:36 RESTORING baseline snapshot` — the container restart this triggers is what produced the
420s gap the old tool then miscounted as a second, independent freeze.

### The fix

`classify()` now also cross-references ground truth: every `tick: swapping` / `RESTORING baseline
snapshot` line `rx_experiment.sh` itself logged (`logs/rx_experiment.log` +
`logs/rx_experiment.log.campaignA`, the two files that between them cover the apparatus's full
history). A gap counts as swap if it lands in the fixed schedule window **or** within a padded
window of a logged restart (3 min before / 12 min after — `SWAP_SLACK_MIN`'s already-proven-
generous forward pad, reused, not re-derived). RF-dead is still checked first, so a genuine outage
overlapping a restart's health-check window still correctly reads as RF-dead, not swap — same
precedence rule DEC-0085 established, now proven against the new path too (new test).

### Effect on the live reading

Re-run against the same 30.5-day window: **7 of 47 previously-counted "freezes" were actually ad
hoc restarts** — freeze count 47 → 40, rate 1.54/day → 1.31/day. All four rolling windows flip to
unremarkable: 24h 95.9th→65.0th pct, 36h 94.0th→67.3rd pct, 48h 85.4th→55.9th pct, 72h 89.0th→
49.3rd pct. **This was not a one-off correction — it was live and about to get worse**: DEC-0087
shipped this same session and guarantees more ad hoc restarts going forward (every pause/resume
cycle, once the mechanism exercises for real), so S79's "elevated window" read a bug whose main
contribution was still ahead of it, not behind it.

5 new tests in `tests/test_freeze_baseline.py` (ad hoc restart detection, its pad boundaries, RF-
dead precedence over the new path, and a positive control encoding the exact 10:24 event that
found this — asserting it reads as freeze *without* the fix, matching the tool's actual prior
behavior). 17/17 `test_freeze_baseline.py`, 238/238 full suite.

### Why this belongs in DECISIONS

Same shape as DEC-0083: a measurement claim ("elevated window") that rested on an instrument with
an undocumented blind spot, this doc's own recurring lesson that a passing check proves nothing if
the assertion — here, the classification — is wrong (DEC-0045). Also corrects a live BACKLOG.md
watch item (S79's freeze-rate entry) that would otherwise have been read as a possible trend at
the next check.

## DEC-0089 — `recovered_since()`'s RECOVERY-edge check had the same lagging-signal blind spot DEC-0087 was built to fix

**Status:** Accepted · **Date:** 2026-08-14 (S81) · **relates to** DEC-0087 (the mechanism this
corrects), DEC-0082 (schedule-shift recovery, applied a third time), DEC-0045 (a passing test
proves nothing if the assertion is wrong), DEC-0088 (same session's sibling finding, same lesson)

### Context

DEC-0087's own first live exercise, ~14 hours after S80 closed. Three short reception dips
(2026-08-13 19:14, 19:22, 19:37 — each under a minute, each self-recovering) dragged the 30-min
mean below the floor and correctly tripped `PAUSE: 30-min mean reception 48% < 50% floor (arm H)`
at `19:40:05`. Reception then read healthy continuously from `19:43` onward — every periodic
`RECEPTION: NN% ... [OK]` line for almost two hours straight, verified directly against
`weewx_monitor.log.1` — yet the pause never auto-resumed. It rode the full 120-minute ceiling into
`ABORT: RF-dead pause exceeded 120min without recovery (arm H)` at `21:45:01`, which restored
baseline and set STOP. STOP then blocked every tick for the next 10.5+ hours, straight through
arm-A's scheduled `00:05` swap, which never happened — discovered at session start the next
morning (~08:15 EDT) when the campaign hadn't advanced.

### What was wrong

`recovered_since()` (DEC-0087) checks for a `RECEPTION RECOVERY` log line newer than the pause
start. That line is written **only on an ALERT→RECOVERY transition edge** — the monitor logs it
when reception climbs back over threshold *after* having been in a 5-consecutive-window ALERT
state. Reception recovered gradually after `19:40:05` and never dropped low enough again to
re-trigger a fresh ALERT, so no fresh RECOVERY line was ever written — confirmed by grepping the
exact window: zero matches, despite dozens of `[OK]` readings in the same span. `recovered_since()`
had no way to see a station that is *currently* healthy but never re-entered the specific
state-machine transition it was watching for.

**The irony, stated plainly:** DEC-0087 exists because the guard's original resume check (wait for
the 30-min mean itself to climb back over the floor) was "unnecessarily slow — stale bad samples
keep dragging the mean down well after the episode itself has ended." The replacement traded a
too-slow signal for one with a different failure mode: an edge detector that can go permanently
silent if the underlying condition never produces a fresh edge. Same lesson as DEC-0088, found the
same session: a corrected mechanism can carry a new blind spot of its own, and the only way to
know is to watch its first real exercise against the actual log, not assume the design reasoning
was complete.

### The fix

`recovered_since()` gains a second, independent check: the monitor's own periodic classification
line (`RECEPTION: NN% avg over last N windows [OK]`/`[LOW]`, logged roughly every 5 minutes
**regardless of ALERT state** — a level signal, not an edge signal). If the newest such line since
the pause start reads `[OK]`, that counts as recovered. This is additive, not a replacement: the
original RECOVERY-edge check still runs first and can still resolve a sharp recovery faster than
waiting for the next periodic tick; the new check only matters when the edge check would otherwise
go silent. RF-dead pause/escalation precedence and every other DEC-0087 behavior are untouched.

4 new tests: the exact incident fixture (an `[OK]` line, no RECOVERY line at all) now asserts
**recovered**, where it previously asserted the opposite — that flipped assertion *is* the
regression test, not a broken one; a fresh `[LOW]` line still does not resume; a stale `[OK]`
predating the pause still does not resume (matches the existing stale-RECOVERY-line test's logic);
a guard-level end-to-end test confirms auto-resume fires from a periodic `[OK]` line with zero
RECOVERY lines anywhere in the log. 30/30 `test_rx_experiment.py`, 242/242 full suite.

### Recovery actions taken same session

- **Schedule shifted +24h a third time** (DEC-0082's mechanism, unchanged, applied again): arm A's
  block 1 now due `2026-08-15T00:05`; square runs `08-15 → 08-23T00:05`. Dates only — arm sequence
  and full 8/8 balance preserved verbatim, confirmed by `test_schedule_is_a_balanced_latin_square`
  passing unmodified.
- Fixed script + shifted schedule deployed together (one NAS write, avoids a tick landing between
  the two and computing `due_arm()` against a schedule that's fixed but not yet shifted, or
  vice versa).
- STOP cleared only after the deploy verified live — clearing it first, against a stale schedule,
  would let `due_arm()` join the square mid-grid on the very next tick, the exact hazard DEC-0066/
  DEC-0082 already named ("do not improvise... regenerate schedule dates first").

### Why this belongs in DECISIONS

A second, independent subsystem-behavior defect in the file DEC-0087 itself calls "the most
dangerous thing in this repo's ops/ directory," found and fixed the same class of way DEC-0014
requires: documented cause, a concrete alternative considered (see above — replace vs. augment the
edge check), tests, and this record. Also the second time in two consecutive sessions (DEC-0088,
DEC-0089) that a just-shipped correction to this campaign's automation carried its own undiscovered
blind spot — worth naming as a pattern, not just two unrelated bugs, when scoping the broader
robustness review this incident also prompted (BACKLOG.md).

---

## DEC-0090 — The S82 state-machine audit: the DEC-0088/0089 blind-spot pattern was a class, and the class had more members

**Date:** 2026-08-14 (S82) · **Status:** Accepted
**Relates to:** DEC-0087/0088/0089 (the prompting pattern) · DEC-0069/0077 (records stop during
episodes — the evidence under fix 3) · DEC-0074 (the rename fix 6's counter missed) · DEC-0064
(campaign B design, unchanged) · DEC-0014 (incremental, tested, no rewrite)

**Why an audit.** Two consecutive sessions (DEC-0088, DEC-0089) each found a "signal blind spot"
in just-shipped campaign automation — a consumer watching for an edge that need not fire, blind to
the level that was there. BOOT ordered a dedicated pass (user's explicit Fable 5 pick) over
`ops/rx_experiment.sh`'s full guard/tick/abort/pause/resume machine plus `weewx_monitor.py`'s
alerting/reset logic, with one rule: every finding verified against real log/ledger evidence
before a fix is proposed. Result: five defects fixed same-session (PR #179), three monitor-side
defects specced and deferred (#180), two clean checks and one deliberate reliance recorded.

**1. Resume threshold aligned to the pause floor.** `recovered_since()`'s level check required the
monitor's `[OK]` tag, which means ≥60% (`WU_RF_MIN_PCT`) — stricter than the 50% `ABORT_PCT` that
pauses. Reception in [50,60) could never have entered a pause yet could not end one, and rode the
120-min ceiling into the same needless abort DEC-0089 had just fixed, one band lower. The band is
occupied, not theoretical: 52–58% periodic reads logged 08-13 10:26, 14:32–14:37, 19:17 and 08-14
01:50. Resume is now the newest periodic line ≥ `ABORT_PCT` (the RECOVERY-edge check stays as the
fast path; `[OK]` implies ≥50 so it is subsumed). Flap near the floor is accepted deliberately:
a flap is two log lines and no config/container touch, and a genuinely dead receiver reads ~0%
and never flaps, so the ceiling escalation the pause exists for is unaffected. Rejected
alternative: a hysteresis margin (floor+5) — shrinks the trap band instead of closing it and
invents a third threshold to keep consistent.

**2. Rotation-blind reads.** `recovered_since()` and the guard's floor mean read only the live
`weewx_monitor.log`, which rotates daily at 00:05 — the exact minute of every swap slot. A
recovery landing just before rotation was invisible to the resume path, and the floor had a
~30-min post-rotation blackout nightly (fewer than `ABORT_SAMPLES` fresh lines → the
never-abort-on-absence refusal), in the hour the episode cluster lives. `harvest()` and
`soak_check.sh` had each already learned the `.1`-pair lesson; the resume path had not. Both
greps now read `"$MONLOG.1" "$MONLOG"`.

**3. Swap deferral while paused.** tick force-cleared an active PAUSE at swap time ("arm swap
supersedes it") and swapped into the live episode: `health_ok` waits on archive records, and
records stop during RF-dead episodes (DEC-0069's absent-rows measurement; DEC-0077's outage
anatomy), so a slot-straddling episode converted DEC-0087's soft pause straight back into the
hard sticky abort it exists to avoid — at 00:05/06:05, inside the nightly episode cluster
(ledger 08-11→14: 12 episodes, 00:49–02:12 plus evening events, 5 of them ≥6 min; roughly a
1-in-4 chance across the square's 32 slots at recent rates). Swaps now defer while paused —
`due_arm()`'s existing self-heal makes the block start late instead of the campaign halting.
BASELINE is exempt: self-termination onto prod config never waits on RF (safety property #5)
and runs no health check an episode could fail. This deliberately changes pre-registered
apparatus behavior mid-campaign, before the square's first block: the alternative — keep the
supersede rule and let a collision abort — is the failure mode that had already cost three
recovery cycles in four days.

**4. Guard stand-down at BASELINE.** The guard never stood down after the self-terminator: its
early exits knew STOP/no-state/NONE but not BASELINE, and the scheduler entries deliberately
persist between campaigns (runbook: "idempotent no-ops against a completed campaign"). So the
first ≥120-min unrecovered episode after a clean campaign end would pause, ride the ceiling,
restart prod for nothing and email "campaign halted" about a campaign that no longer existed.
Campaign A never exposed it only because it ended in an abort whose STOP short-circuits first.
One-line early exit on `BASELINE`.

**5. tick/guard/abort serialize behind a lock.** No mutual exclusion existed, and a full-budget
`health_ok` outlives the 5-min scheduler period (measured 383s wall on the 2026-08-11 02:05
abort at the then-36-try budget; the budget is now 60 tries ≈ 500s+ wall). The guard/tick
interleave is on record — 02:05:03 that morning: tick logs "swapping P449 -> P402" and guard
logs "ABORT: 30-min mean 39%" the same second; double restore, double restart, two emails,
the conf written concurrently by both. The tick-vs-tick variant (unobserved, arithmetic-certain
on a slow RF acquisition) duplicates harvest rows and kills the container under the very health
check judging it. Mechanism: `mkdir` lock + pid file; liveness via `kill -0` (root-to-root on
the NAS; also the macOS test host has no /proc); empty-pid grace <60s (a winner mid-acquisition
is not debris); 1800s age ceiling breaks a HUNG holder loudly — a silently-skipped-forever tick
would be the `due_arm()` no-op trap wearing a new hat. Manual `abort` takes the lock when free
but proceeds regardless: a human's emergency stop is never skipped.

**6. soak_check's reset counter, dead since S67.** `mon_resets` grepped `RESET: triggering` — a
message DEC-0074's rename retired — and read 0 for ~6 weeks; the impossible "1 ineffective of 0
fired" on S82's morning soak was the tell. Now counts `RESET: running` (fires exactly once per
attempt). ops#147 item-6 class: a consumer grep stranded by a message rename — the very class
DEC-0074 documents, one hop downstream from where it fixed it.

**Monitor-side, specced and deferred to #180 (tier:mid).** (a) Episode/alert state is
memory-only — a monitor restart mid-episode silently loses the `episodes.log` row (the
pre-registered LNA-verdict datum), the RECOVERY edge and the ALERT's email pairing; all 6
recent ALERTs pair 1:1 with ledger rows, so nothing is lost yet, but every deploy is a
kill+respawn. (b) The weewx.log rotation-reset branch zeroes `wu_bad_windows` while an
alert survives, so a reset fired within `RESET_VERIFY_S` of midnight is judged "verified
effective" by rotation rather than by reception — mislabeling the forensics captures
DEC-0075/0081-class analysis depends on, and silently refreshing the 1-hedge budget.
(c) `do_reset()`'s exception path only logs, unlike the nonzero-exit path which emails — and
it fired live at 01:56:30 this morning (`timed out after 15 seconds`). Deferral grounds: no
deadline, the daemon deploy needs the owner-run kill dance, and the fixes are mechanical now
that the spec is written — it is the issue body.

**Checked and clean, recorded so they are not re-derived:** the guard's mean-source regex
matches only the periodic level lines (the ALERT/RECOVERY/REPEAT/SUMMARY formats cannot
contaminate it); `due_arm`/`schedule_started` string comparisons; `write_arm`'s atomic
write-and-verify; `harvest`'s rotation pair; `health_ok`'s rotation exposure at 00:05
(weewx.log rotates ~23:59, complete before the slot).

**Known reliance left in place, on purpose:** the guard's floor mean has no freshness
requirement — six stale healthy lines from a dead monitor would pin it green indefinitely.
Deliberate layering: the guard trusts the monitor; `soak_check.sh` criterion 9 watches the
monitor's liveness. Duplicating that watch inside the guard buys nothing.

9 new tests, one renamed to the new semantics (39/39 file, 251/251 suite). Deployed
same session: merged tip sha `4438a2a3…` scp'd to the NAS (owner-run fallback — the S81
read-guard gotcha recurred exactly as documented) and verified at 10:38. First live exercise
is the 08-15 00:05 arm-A swap. Cross-repo same session: ops#163 closed (the MANIFEST carry is
settled — OPS-DEC-0101, ops#158 precedent), ops#165 filed (decision-blessed carries need a
sweep exemption or they re-file forever), weewx#180 filed.

---

## DEC-0091 — The pre-square window used: the audit's remaining fixes shipped and deployed the same day, plus two deliberate contract changes for v2.0.14

**Date:** 2026-08-14 (S82b) · **Status:** Accepted
**Relates to:** DEC-0090 (the audit that specced all of this) · DEC-0006 (honest nulls, applied to
the archive's pressure columns) · DEC-0086 (the barometer passthrough this instruments) · DEC-0074
(the deploy-verification criterion used) · DEC-0064 (one-image-per-square, upheld)

**The owner's reframe, and what it changed.** S82 had scheduled the monitor trio and the pressure
work post-campaign on instrument-stability grounds. The owner pointed out the square had not
started — pilot and hold were done, block 1 was due at 00:05 that night. That flips the calculus:
changing the instrument BEFORE the measurement begins is strictly better than after it ends, since
the whole square then runs on one consistent monitor. Executed same day: PR #182 (monitor trio)
merged 16:13Z, deployed 12:24 EDT, respawned pid 7625 with `Monitor started` 12:25:21 — startup
line after file mtime, per DEC-0074. PR #183 (pressure package) merged 16:23Z onto `dev`.
**The image was still held**: cutting v2.0.14 and recreating the container hours before the
square's clean start trades a week of dashboard convenience for a NAS build, a recreate that can
silently revert the three live-config deviations (CONSTANTS), and a midnight deadline — and the
square runs on exactly one image either way. v2.0.14 is queued post-campaign (~08-23): weewx
5.5.0 (#158) + `barometer_fetch_epoch` (#172) + honest-null pressure (#144) + the `:latest` move
once the square proves v2.0.13.

**Contract change 1 (#144): `pressure`/`altimeter` become honest nulls — a consumer-visible
archive change.** `pressure_service.py` backfilled both internal keys with the fetched
`bar_sea_level`. Those are different quantities: at any nonzero elevation the archive's
station-pressure column carried sea-level numbers — not DEC-0086's "reader trap" but a wrong
value, and `hyperlocal-forecast` reads that archive (hlf#302 is the complaint). Per DEC-0006 the
keys now stay None; **from the v2.0.14 deploy onward the archive's `pressure`/`altimeter` columns
are NULL**. Rejected: computing true station pressure from altitude (adds a formula and a
dependency for columns no published contract carries); documenting-and-keeping (a wrong number
with a footnote is still wrong). Heads-up posted on #144 for HLF; INTERFACES §1 documents it.

**Contract change 2 (#172): `barometer_fetch_epoch`, a freshness stamp outside the TTL
machinery.** `last_fetch` is a throttle stamp — it advances on FAILED attempts too — so a new
`last_success` records the last fetch that actually yielded a value, and every loop packet
carries it as an integer epoch. `loop_json_writer` publishes it verbatim, deliberately bypassing
the cache/TTL: the field's entire job is to REVEAL staleness, so omitting it for being old would
recreate the gap it closes. Absent only before the first success of a run. Loop-JSON only —
InfluxDB deliberately not extended (schemaless absence is free, nothing asked for it there).
This is provenance metadata beside DEC-0086's still-open `_qc`-flag question, not a resolution
of it.

**Monitor persistence semantics (the #180 trio's design calls).** (a) The open episode mirrors to
`logs/monitor_episode.state` on every mutation; startup restores it, and `wu_in_alert` re-derives
from the restored onset (an alert IS an open episode — one fact, not two states to sync). The
repeat-email clock restarts at load so a pre-restart REPEAT cannot double-send. Close is
**row-first, then clear**: a crash between the two duplicates an adjacent ledger row at worst,
never loses one — losing rows was the defect. (b) The rotation branch **voids** a pending reset
verdict (`RESET verdict void: ...`) instead of letting the zeroed `wu_bad_windows` fake
"verified effective" — tries/escalated untouched, forensics labels stay honest. (c) `do_reset`'s
exception path emails like its nonzero-exit sibling (it fired live at 01:56:30 that morning as a
15 s sudo timeout that told nobody).

**Mechanical fact worth keeping:** a second same-session PR branched before the first merged sits
BLOCKED by branch protection ("requirements not met", state stays OPEN — and `gh pr merge`'s
quiet refusal is another face of its never-trustworthy output) until the branch is updated;
`gh api -X PUT repos/<r>/pulls/<n>/update-branch` does it server-side, CI reruns, then the merge
lands. That is how #183 went in.

12 + 8 new tests (271/271 on the merged tip). One test-infra note: per-file weewx stubs interact —
`test_parse_raw_channel`'s StdService stub has no `bind`, so the new pressure tests reuse whatever
stub is present but guarantee `bind` exists. The #144 **offset quantification** (archive vs METAR
MSLP) is the batch's one open sliver — method written into #144, read-only, campaign-safe.

## DEC-0092 — Answering the shared-NAS I/O lease proposal (ops#169): our yield is a near-no-op, the box's real schedule is a nightly heavy window, and the filesystem everyone was reasoning from was wrong

**Date:** 2026-08-14 (S83) · **Status:** Accepted
**Relates to:** DEC-0068 (coffee-radar / freeze correlation, which this extends with a second and
much larger candidate) · DEC-0067 (the freeze mechanism this hands a testable split) · DEC-0074
(process-not-file verification, applied to a neighbour's schedule change) · DEC-0071 (WAL —
**informed, deliberately NOT reopened**) · DEC-0024 (the loop-packet inflation this re-reads as a
write-amplification fact) · DEC-0059/0064 (campaign integrity, the constraint that drove the
coordination)

**The ask.** coffee-radar filed ops#169 proposing an advisory disk-I/O lease on the shared NAS: a
heavy job atomically creates a lease `{tenant, job, ttl, renew_at}`, cooperating tenants poll it
and voluntarily downshift while a foreign lease is live. weewx was asked first, as the box's
continuous writer, on the reasoning that S185's measured contention correlated with continuous
weather ingestion. The protocol is advisory because per-container I/O attribution is impossible
on this kernel; the format and constants were deliberately left unlocked pending our answer.

**The answer: yes to a client, and the honest caveat that our yield frees almost nothing.**
Measured rather than estimated before replying. `binding` defaults to `archive`, so InfluxDB
receives **1 record per 60 s**, not loop packets. Total weewx-originated write bandwidth is order
**tens of MB/day** — a single sweep moves more in a minute. Our shape is the inverse of a sweep:
high-frequency, tiny, and metadata-heavy (~50–85k tmp-write + rename cycles/day via
`loop_json_writer.py`, near-zero data). The counterpart accepted this and recorded that a
near-no-op weewx courtesy side is an acceptable answer to ops#169 — the protocol is advisory
precisely so a tenant can answer that honestly rather than ship a client that looks cooperative
and moves nothing.

**The data-integrity line, which is what ops#169 actually asked us to draw.** Deferring InfluxDB
posts is safe: the **live** config was checked (not the shipped defaults) and `[[Influx]]` sets
only connection keys, so prod runs `stale = None` and `max_backlog = 1,000,000` — a 30-minute
deferral queues ~30 records against a million-record cap, posting late and losing none. The
**SQLite archive write is the red line**: weewx's engine waits a hardcoded 120 s on a busy
database and then restarts, and our non-stock `timeout = 30` exists because a *reader* holding
the lock six seconds once cost a 5–10 minute outage. weewx will never delay an archive commit
for a lease; the failure mode there is an outage, not late data. The loop-JSON surface is
likewise undeferrable — INTERFACES §1 publishes its ~2.5 s cadence and the dashboard reads it,
so our one high-volume write is contractually fixed.

**The filesystem correction, and why it is in a DEC rather than a comment.** Both sessions had
converged on a mechanism — that our rename load costs ext4 journal commits, that `jbd2` runs in
its own kernel context outside any ioprio, and therefore that the pressure is reachable by
neither protocol lever. The conclusion is right; the mechanism was wrong. **`/proc/mounts` shows
`/volume1` and all 25 mounts beneath it are btrfs** (`cachedev_0`, `space_cache=v2`,
`metadata_ratio=50`, `auto_reclaim_space`, `ssd`, `relatime`); **only DSM's `/` on `/dev/md0` is
ext4**, and neither tenant writes application data there. There is no `jbd2` in either party's
data path. What replaces it is copy-on-write B-tree churn serialized through
`btrfs-transaction` — equally outside ioprio, so the strategic conclusion survives intact, but
write amplification is higher than the ext4 model predicts and the mount is `relatime`, not
`noatime`, so read sweeps generate real allocations. This was caught only because the claim was
verified instead of inherited, after it had already been adopted into our draft.

**Attribution is genuinely impossible, and now the reason is recorded.**
`/sys/fs/cgroup/blkio/` exists but holds only `blkio.reset_stats` plus cgroup boilerplate — no
`io_service_bytes`, no `throttle.*`, no `weight`. `CONFIG_BLK_CGROUP` is on; accounting and
throttling are not. The obvious escape hatch is also closed for a reason worth stating once so it
is not re-opened: the kernel is **4.4.302+**, and cgroup v2's `io.max`/`io.latency`/`io.cost`
landed in 4.10/4.19/5.4. The feature postdates the kernel; this is not a Synology configuration
choice that can be argued with. Verified independently by both tenants.

**The finding that outranks the protocol: the box has a nightly heavy window, and our midnight
block sits in it.** Resolving the DSM task ids in `/etc/crontab` (method:
`/volume1/docker/TaskSchedulerOutput/synoscheduler/<id>/<epoch>/`, world-readable, no root)
turned up three daily jobs firing inside the 00:05 swap window — and one of them is not small.
A sibling tenant's nightly maintenance (id=15) runs **00:10 → ~03:00–05:10 every night**, six
nights verified, median ~4h20m. Campaign blocks are 6 h, so **~72% of every 00:05 block runs
under a heavy-I/O window that no prior analysis knew about.** Two more fire at 00:05 itself:
our own `weewx-monitor` logrotate (id=2 — the same minute as the swap's `harvest()`, which reads
that very log and its rotation) and another tenant's capture job (id=9). Identities are recorded
in the gitignored local-infra doc; the repo copy is genericized because this repo is public.

**Comparability is safe; reliability and variance are the exposure.** The square is a 4×4 Latin
square run twice, so each arm occupies the midnight slot exactly twice and a slot-level confound
is absorbed by construction — this is what the design is for, and it holds without changes.
What the cluster threatens is (a) the midnight *swap* succeeding, since three jobs contend in the
same minute as `health_ok()`, and (b) variance, since freezes distort exactly the counters the
campaign measures (DEC-0067) and midnight blocks are systematically noisier. Both apply
uniformly across arms, so neither biases the result.

**The lead this hands DEC-0067/0068.** Blocker 1 (freezes, 1.31/day, root cause unproven) has a
new testable hypothesis: **split the freeze timestamps by hour-of-day against that nightly
window.** DEC-0068 found coffee-radar correlated with 1 of 3 captured freezes; this is a second
candidate with roughly eight times the nightly duration, and no prior analysis controlled for it
because nobody knew it ran. It is testable **against rotated logs we already hold** — no new
instrumentation. Deferred until after the square, because `ops/freeze_baseline.py` is itself a
heavy multi-rotation sweep and would add load to the measurement it is trying to explain.

**Coordination worked before any constant was locked, and the mechanism was disclosure.**
On being told the square's schedule, the counterpart **held its 12–20 h Stage-1 sweep until after
08-22** and banked the hold so a later session could not relaunch it by accident, then **moved its
6-hourly job off :00 to :30** before block 1. Both were verified here rather than relayed —
`30 0,6,12,18` in the live crontab, and the id=11 output directory stamped 18:31, which proves the
new schedule *executed* rather than merely being configured (DEC-0074's principle applied to a
neighbour). None of that required throttling; it required knowing each other's schedules. That is
the argument for the lease log being the load-bearing part of ops#169 rather than the yield.

**Recorded but deliberately not acted on.** SQLite on CoW btrfs is a documented pathology, and we
run `journal_mode = DELETE` — the worst mode for CoW — pinned on every connection. **This does
not reopen DEC-0071.** WAL was abandoned for a correctness failure (a reader stranded on a stale
snapshot) that is independent of performance, and the counterpart supplied the qualification that
settles it: the ~300% WAL figure comes from single-writer workloads, while ours is exactly the
multi-process shape that bit us — `weewxd` writing while the monitor, `wxcheck`, and the analysis
scripts read. The non-conflicting option is `chattr +C` on the archive DB (~25–30% class,
compatible with DELETE mode, costs btrfs checksums on that file, and only takes effect on an empty
file or directory). Queued post-square with the v2.0.14 recreate, needing its own DEC.

**Post-square queue from this work:** `noatime` on `/volume1` (owner-level DSM change, benefits
all four tenants, plausibly the cheapest single intervention identified) · `chattr +C` on the
archive DB · move our own logrotate off 00:05 · the freeze hour-of-day split · and the standing
option to stop generating dataless loop-JSON writes at all, since DEC-0024's freq-hop packets
republish byte-identical values under a refreshed timestamp (own design pass, touches INTERFACES).

**Update (S84, 2026-08-15) — the last queue item was answered and is retired; see DEC-0093.**
The dataless-write option rested on a stale reading of DEC-0024: **Layer B (S43) already stopped
freq-hop packets from being published as loop packets**, so the class this proposed to remove has
been empty for three months and the design pass would have found nothing to cut. Two figures above
are refined by the measurement that followed: the renames estimate is **~45,000/day, not 50–85k**
(the upper bound was the *pre*-Layer-B rate), and "**loop-JSON is contractually fixed by
INTERFACES §1**" is right for `loop-data.txt` — pinned by a 30 s consumer liveness gate this repo
had never written down — but wrong for `current.json`, which has no consumer at all and is where
the yield actually is.

**Update (S84d, 2026-08-15) — the testable lead this DEC handed DEC-0067/0068 is answered, and it
is NEGATIVE; see DEC-0094.** The hour-of-day split was run (at zero prod cost — the deferral had
priced a *fresh* `freeze_baseline.py` run, but the split only needed events already printed and
preserved in transcripts). The nightly maintenance window holds **9 of 40 freezes against 7.2
expected, P=0.29** — it does not explain the freeze rate. The evening cluster does carry signal
(18:00–21:00: 12 vs 5.0, P=0.0027), which corroborates DEC-0068 rather than this DEC's lead. The
schedule finding above stands on its own evidence; only its freeze-explaining *implication* is
withdrawn.

## DEC-0093 — The dataless-write proposal was answered three months ago; the real write amplification is `current.json`, which nothing reads

**Status:** Accepted (finding + direction; **no code changed this session** — PRINCIPLES §8,
DEC-0014) · implementation gated on the dashboard confirming the cadence
**Date:** S84 (2026-08-15)
**Relations:** **answers and retires** DEC-0092's last post-square queue item · **refines**
DEC-0092's renames figure and its "loop-JSON is contractually fixed" claim · **does NOT reopen**
DEC-0024 (both layers stand) · **upholds** DEC-0006/DEC-0053 · **relates to** DEC-0051, DEC-0054 ·
**declines a link to** DEC-0067/0068

### What was asked

Whether `loop_json_writer.py` should skip writing when a LOOP packet carries no sensor data —
raised out of ops#169's cooperative disk-I/O lease proposal, where weewx's footprint was
established as metadata/rename-heavy rather than bandwidth-heavy (DEC-0092). The stated premise:
`PacketFactory.create()` yields CHANNELPackets carrying `freqError` telemetry and no readings, the
writer fires on them, and ~40% of writes are therefore byte-identical to the previous write except
for a refreshed `dateTime`.

### The premise was stale

**DEC-0024 Layer B (S43) already fixed this**, one level above the writer. A channel-hop packet is
stashed by `_cache_pending_freq_fields()` and the loop `continue`s (`rtldavis.py:1507-1517`); its
`freqError{n}` fields ride in on the next real DATA packet (`_merge_pending_freq_fields()`,
`rtldavis.py:1506`). `PacketFactory.create()` does still *yield* CHANNELPackets — which is what the
reading saw — but `genLoopPackets` filters them before WeeWX ever sees one, so `new_loop()` cannot
fire on a hop packet. The `~40%` figure is `66/166`: DEC-0024's own **pre-fix** 1.66×.

**Verified live, not from source** (DEC-0074 — a file proves the file, never the process). The
monitor is logging `WINDOW: 12–18/21 (57–86%)`, `RECEPTION: 72–74% avg` — the post-Layer-B
signature DEC-0024 recorded (67–81%, matching the driver's trusted `rxCheckPercent`). The
inflation's signature is this metric pinning near 100%, because dataless publishes were what
inflated it. It is not pinned.

Also re-confirmed, because it constrains any future attempt: DEC-0024 rejected option (A), dropping
the hop packet outright, because `freqError0-4` are mapped onto real archive columns
(`consBatteryVoltage`/`hail`/`hailRate`/`heatingTemp`/`heatingVoltage`). That constraint still
holds.

### The measurement DEC-0092 estimated

From the live monitor, ~15.6 packets/min received → **~22,500 loop packets/day → ~45,000
renames/day** across the two paths. DEC-0092's `~50–85k` brackets both states: ~85k is the
pre-Layer-B rate, ~45–50k is the corrected one. The measured value landing at the low end is
independent confirmation that no inflation remains.

### The real finding: `current.json` has no consumer

The eh-proxy's only `/weewx-data` read is `loop-data.txt` (dashboard `server.js:889`); its
`serveStatic` serves the public/dev/lab directories and never that path. No runtime reference
exists in the dashboard, in hyperlocal-forecast, or in this repo outside the writer and its tests —
every other hit is documentation. The dashboard's own roadmap still carries Cold-load Fix B's
consumer half as **open at P0**.

So **half of all writes — ~22,500 renames/day — go to a file nothing reads.** That is essentially
the entire 40% the proposal was chasing, except it is real, and it is removable by inspection
rather than by reasoning about semantics.

### Direction (gated, not shipped)

`current.json`'s cadence **decouples** from `loop-data.txt`. It is a cold-load snapshot: 30–60 s is
ample, since the polling loop replaces it within one tick, and a first-time visitor's worst case is
a first paint up to a minute stale. That removes **~47% of total renames**.

Not deletion — `current.json` is a published surface (INTERFACES §1) and the dashboard intends to
build against it. **Gated on the dashboard confirming**, per INTERFACES change discipline. The
argument for doing it now rather than later: the window is open *because* Fix B's consumer half was
never built, so nothing can break; once that consumer exists against a 2.5 s assumption, the same
change becomes a genuine interface break.

### Why the write is NOT suppressed on unchanged content — recorded so it is not re-proposed

`dateTime` on `loop-data.txt` is a **liveness** signal with a numeric threshold a consumer already
depends on: the eh-proxy 503s when `Date.now()/1000 - parsed.dateTime > 30` (`server.js:896`), and
the dashboard treats that 503 as its single authoritative proof the station is down (dash
DEC-0154). `wind_speed` is set unconditionally in every parsed frame (`rtldavis.py:1579`),
including `0.0` when calm, so on a calm night consecutive payloads are genuinely identical for
minutes. Content-based suppression would therefore report a **healthy station as offline**. Any
such scheme would need a heartbeat floor well under 30 s, which reclaims most of what it saves.

The semantic argument put to us was that a hop packet republishing cached values under an advanced
`dateTime` is already "serving a stale value under a live timestamp", so suppressing would be *more*
honest. It inverts. DEC-0006/DEC-0053 deliberately keep **two independent axes**: per-field
freshness is carried by the TTL machinery (a field that stops updating is *omitted* within 300 s),
and feed liveness is carried by `dateTime`. Republishing a cached value under a new `dateTime` is
honest *because* the TTL bounds it — that is precisely what DEC-0053 closed. Suppression collapses
the two axes back into one, so a frozen `dateTime` would mean either "no packets" or "no changes"
with no way to tell — reintroducing the exact ambiguity DEC-0006 exists to remove, one level up.
S82b's own `barometer_fetch_epoch` states the governing principle: a staleness signal must never be
omitted for being old. A liveness signal must likewise not be withheld for being unchanged.

One residual dataless case does survive Layer B: DEC-0054 frame co-rejection nulls every
`FRAME_WEATHER_KEYS` field, so that packet updates no cache entry. Suppressing it would be actively
wrong — the packet's *arrival* is proof RF is alive; only its content was rejected.

### The link that does not hold

Tempting and false: that halving writer I/O bears on the freeze blocker. **DEC-0068 measured
`weewxd`'s main thread staying `S`, never `D`, even during a load-12 freeze** and concluded "this
isn't literal I/O-blocking". Less writer I/O is not evidence toward DEC-0067/0068. Recorded so the
motivation is not re-derived.

### Doc contradiction found and corrected

INTERFACES §1 and the writer's module docstring both asserted, in the present tense since S43, that
the dashboard fetches `current.json` at boot. It does not, and did not. Both corrected this
session; INTERFACES §1 additionally now records the **30 s liveness gate**, a load-bearing consumer
expectation this repo had never written down — DEC-0092 asserted loop-JSON was "contractually
fixed" without the number that makes it so. The dashboard's roadmap holds the accurate half (Fix B
open), so **cross-repo reconciliation is still owed**: weewx shipped its half and documented the
whole feature as done.

### For ops#169

weewx's honest position: its footprint is **~47% removable unilaterally, with no lease protocol at
all**, and the remaining `loop-data.txt` half is pinned to a 30 s consumer gate, so it cannot defer
those writes under a lease without a consumer-visible outage. That is a **hard floor, not a soft
one** — useful for the protocol to know about this participant.

## DEC-0094 — The nightly-window freeze lead is refuted; the evening cluster is real, and the whole test cost prod nothing

**Status:** Accepted (measurement) · **Date:** S84d (2026-08-15)
**Relations:** **answers and closes** DEC-0092's testable lead · **upgrades** DEC-0068 from n=1 to a
measured base rate · **feeds** DEC-0067's open mechanism question · **applies** DEC-0088's
correction · **does NOT close** blocker 1

### The deferral was priced wrong

DEC-0092 handed DEC-0067/0068 a lead — split the freeze timestamps by hour-of-day against the
sibling tenant's nightly maintenance window — and deferred it post-square because "the script is
itself a heavy sweep" that "would add load to the measurement it is trying to explain." That is
true of a **fresh** `ops/freeze_baseline.py` run. It is not true of the split.

The script prints **every individual freeze event**, by deliberate design — an S37 anti-confounder
("a summary rate alone hides exactly the confounder above"). Those listings survive in the session
transcripts. So the split is arithmetic over data already collected: **no archive query, no log
sweep, no ssh, zero load on the running square.** The generalisable form: *before deferring an
analysis for its collection cost, check whether collection already happened.* This repo's own
S39 lesson (an inherited item's reasoning often lives only in a transcript) applies to its **data**,
not just its reasoning.

### Dataset, and why it is the right one

The **DEC-0088-corrected** run only: **n=40, 1.31/day, window 2026-07-14 → 2026-08-13**. Three
other runs sit in the transcripts (1.48, 1.54, 1.57/day) and all pre-date DEC-0088's
ad-hoc-restart fix; analysing those would have meant analysing known-miscounted data.

Two integrity checks, both passed before any conclusion was drawn:
- **Parsed event count equals the run's own claimed count** (40 = 40), so the transcript block is
  complete, not truncated.
- **Positive control against an independently documented fact:** DEC-0088 established that
  2026-08-12 **19:55** was an abort-recovery restart, not a freeze. It is **absent** from the n=40
  set and **present** in the 1.54 and 1.57 sets — the corrected run is provably the one used.

Timestamps are `datetime.fromtimestamp()`, i.e. naive **local**, so they align with the local
maintenance window directly (assumes Mac and NAS both EDT; the 00:05/06:05 swap lines corroborate).

### Result — the lead is refuted

| window | share of day | observed | expected | P(X ≥ obs) |
|---|---|---|---|---|
| nightly maintenance 00:10–04:30 | 18.1% | 9 | 7.2 | 0.29 |
| evening 18:00–21:00 | 12.5% | **12** | 5.0 | **0.0027** |
| coffee-radar's ~19:00 run, 18:30–20:00 | 6.3% | 7 | 2.5 | 0.011 |

**The nightly window explains nothing.** It covers 18% of the day and holds 9 of 40 freezes against
7.2 expected. DEC-0092's hypothesis — that a large share of the 1.31/day would prove to sit inside
it — is **refuted on this data**, and blocker 1 should stop advertising it as a pending lead.
Median freeze duration inside the window (240 s) is identical to outside (240 s): no severity
effect either.

**The evening is where the signal is**, and it is not a new hypothesis. DEC-0068 already named
coffee-radar's documented 19:00 daily run as a *confirmed contributor* from process evidence
(loadavg 12.39, the container verified running through freeze #2) but could only say "n=1
correlated out of 3 captured freezes, **not a base rate**". This is the base rate: **30% of all
freezes in 12.5% of the day**, spread across **10 distinct dates**, so it is not one bad night
repeated.

### Stated honestly: what this is not

The evening cluster was found **post hoc**, by looking at the histogram. The omnibus test across all
24 bins is **X² = 30.8, df = 23, critical 35.2 — not significant**: the 24-hour distribution as a
whole does *not* reject uniformity. What keeps the finding from being a naked post-hoc peak is that
it is an **independent dataset agreeing with a pre-existing, mechanistically motivated hypothesis**
(DEC-0068), not a fresh claim mined from the same data that suggested it. Treated as corroboration,
not proof.

The window also **pre-dates both the campaign and the nightly-window discovery** — correct for
testing a standing schedule, but a fresh `freeze_baseline.py` run after the square should confirm,
and that run still belongs post-square at its real cost.

### Side result: the 2026-08-15 blackout was RF-dead, not a freeze

Arm A's first block took a ~20-min reception blackout at 02:00–02:22 (S84b), and its position inside
the nightly window made "process freeze" the tempting reading. It is not: `weewx.log` carries
**three `rtldavis process stalled` lines** in it (02:05:00, 02:16:16, 02:20:19). By BACKLOG's own
rule (DEC-0067) a >150 s gap **with** a stall line is RF-dead — the watchdog fired, so the main
thread was running and correctly reporting that it heard no RF. Consistent with the hour-of-day
result. One grep, and it closes the S84b open question.

### What is still open

Blocker 1 stands. The freeze **mechanism** remains unproven — DEC-0068 measured `weewxd`'s main
thread staying `S`, never `D`, even during the load-12 freeze, so "coffee-radar's run correlates"
is still not "coffee-radar's I/O blocks us". This narrows *when* to look, not *what to look for*.

**Update (S85, 2026-08-15) — the gate opened, the change is IMPLEMENTED, and the deploy mechanism
in this DEC's own "Direction" section was wrong.**

`eaglehunt-weather-dashboard#430` answered with Option 1: *"Confirmed — `current.json` is
cold-load-only... 60s is fine... Please make the change — Fix B isn't built yet, so there's nothing
to break, and we'll design its consumer against 60s from the start."* So the cadence question is
settled by the consumer, exactly as the gating required.

**Shipped:** `current_interval` (default **60 s**) throttles `current.json` only; `loop-data.txt`
stays per-packet. The first packet of a run always writes the snapshot, so a restart republishes
immediately instead of leaving the previous run's file standing for an interval. `current_interval
= 0` restores the S43–S84 behavior. A failed snapshot write does **not** advance the timestamp, so
one transient failure cannot suppress it for an extra interval; a **backwards** clock step also
forces a write, since treating negative elapsed as "not due" would freeze the snapshot until real
time caught up. 8 new tests (23 in the file, 279 suite).

**Measured, not estimated:** simulating one day at 2.5625 s/packet gives `loop-data.txt` 33,717
writes and `current.json` **1,405** — 67,434 → 35,122 renames/day, **47.9% removed**, matching the
~47% this DEC projected.

**The correction that matters for anyone shipping this: `loop_json_writer.py` is MOUNTED, not
baked.** `nasctl inspect` shows `<project root>/loop_json_writer.py` bind-mounted `ro` over
`site-packages/user/loop_json_writer.py`, and **the Dockerfile never `COPY`s the file at all.** So
"ships with the v2.0.14 image cut" — the plan this DEC and BOOT both carried — **would have been a
silent no-op with a green checkmark**, DEC-0046's exact failure mode. Deploy is `scp` to the
**project root** plus a container restart. Two further traps found the same way: the copy in
`weewx-data/bin/user/loop_json_writer.py` is a **decoy** (not the mount source, editing it does
nothing), and `CONSTANTS.md`'s deploy-layer table did not list this file at all — now fixed, with
`nasctl inspect` named as the authoritative per-file check.

**Deploy timing unchanged in substance:** it still rides the ~08-23 v2.0.14 window, because that is
when the container is next recreated anyway and mid-square restarts are avoidable churn — but it
rides as an `scp`, not as a bake, and the v2.0.14 checklist now says so.

## DEC-0095 — Retention: the archive is accepted and monitored, not pruned — and the monitor executes

**Status:** Accepted · **Date:** S87 (2026-08-17)
**Relations:** **answers** [ops#175](https://github.com/WeatheredScientist/eaglehunt-ops/issues/175)
for the weewx side · **adopts the METHOD of, and departs from the CONCLUSION of, HLF DEC-0156/0174**
· **defers to** DEC-0092 on the fragmentation lever · **applies** DEC-0040 (prose does not execute)
· **respects** DEC-0010 on the InfluxDB half · **does NOT close** ops#175's cross-repo half

### The question was never "what horizon"

ops#175 filed a real gap: neither of this repo's ongoing-write stores has a retention policy, and
that is the same shape HLF's DEC-0156 (`verification_records`) and DEC-0174 (`observations`) had to
solve. The filing was careful to caveat scale and to leave the design to us.

The backlog entry that banked it (S85) already refused the obvious framing. The question is not what
horizon to pick. It is **whether retention is the right lever at all**, and that is answerable only
by measuring what actually binds. HLF's own DEC-0174 is the model here, and its most transferable
sentence is the one about its own constraint: *disk measured NOT binding (5.5 TB free) — the working
set is the why.* Retention is a working-set policy wearing a disk-policy costume.

### Measured, read-only, 2026-08-17

| Question | Measurement | Binds? |
|---|---|---|
| Disk | 5.1 TB free on `/volume1` (14 T, 64% used) | **No** |
| Working set | archive **33.61 MB** = **0.89%** of MemTotal 3.69 GiB; page cache 1.91 GiB | **No** |
| Growth | **125,613 rows / 90.2 d = 1,392 rows/day** at 275 B/row = **0.37 MB/day** → **~7.3 yr to 1 GB** | — |
| InfluxDB | engine **14 MB** total, larger bucket 13 MB | **No** |
| Aggregation | **114** `archive_day_*` tables, 10,624 rows, ~0.1 MB | already bounds long reads |
| CoW | btrfs confirmed; `lsattr` shows **no `C`** → DEC-0092's `chattr +C` genuinely unapplied | live lever |
| `journal_mode` | `delete` | DEC-0071's pin holds |

`dbstat` puts **32.94 MB of the 33.61 MB in the single `archive` table** — there is no second
offender to find. The measured rate came in *below* the banked 0.41 MB/day estimate, not above it;
the S85 warning that HLF's DEC-0156 landed 1.75× over its design assumption is still the right
instinct, and is why the tripwire below exists rather than a horizon.

### The decision, and why it is not HLF's

**The SQLite archive is accepted and monitored. No prune, no horizon, no cold export.** Four grounds,
in descending order of how hard they are to argue with:

1. **Neither constraint binds, by two to three orders of magnitude.** HLF justified retention on the
   working set at ~8.0 M hot rows against **this same 3.69 GiB box**. We have 125,613 rows — 66×
   fewer — and the *entire* database is 0.89% of RAM. Both weewx stores together are ~47 MB. The
   prior art's method transfers exactly; its conclusion does not, because the inputs differ by a
   factor that no amount of design can make matter.
2. **The `archive` table is the deliverable, not a diagnostic.** This is the load-bearing asymmetry
   with HLF. `verification_records` and `observations` are derived, regenerable, and their loss
   costs diagnostic depth. This repo's stated contract is *the data it emits*; the archive **is** the
   weather history, and it is irreplaceable — a passively intercepted station cannot backfill. A
   prune here would destroy the product to reclaim 0.89% of RAM.
3. **Upstream already solved the working-set problem by aggregation.** WeeWX maintains 114
   `archive_day_*` summary tables (10,624 rows, ~0.1 MB) precisely so long-range queries never scan
   the 32.94 MB archive table. The mechanism HLF reached for retention to achieve, we already have,
   for free, maintained upstream.
4. **The one cost this database's history actually documents is fragmentation, and retention is the
   wrong lever for it.** DEC-0070/0071/0092 all studied this DB — lock timeouts, WAL-vs-DELETE, CoW
   fragmentation on btrfs. `chattr +C` is already queued for the v2.0.14 recreate and is confirmed
   unapplied. Pruning rows would not defragment an extent.

A fifth, weaker but real: WeeWX ships no prune, so adding one is permanent fork divergence to carry
(`CHANGES-FROM-UPSTREAM.md`).

### Rejected

- **HLF-shape archive-then-prune** (cold NDJSON, checksum-verified, bounded batches, hot-days
  horizon) — correct machinery, wrong problem here; building it now costs maintenance against a
  constraint that is 2.6+ years away at the measured rate, and it would prune the product.
- **A fixed-MB tripwire** — names a number instead of the constraint. A RAM ratio survives a memory
  upgrade and states *why* the bound exists.
- **`VACUUM`** — not proposed, and worth recording as refused: freelist is 0, so there is nothing to
  reclaim, and a VACUUM rewrites the whole file, which is the fragmentation-maximizing operation on
  CoW.
- **Deferring again** — the deferral's condition (measure first) is now met.

### The reversal condition, which executes

Accept-and-monitor is worthless as an intention. DEC-0040 is the rule, and **this very script is the
cautionary tale**: `EXPECT_IMAGE` sat wrong for five sessions because nobody ran the check, and S87
opened by finding the soak's monitor check had been emitting a false FAIL for ten days. So the
decision ships its own reversal condition as code, in the thing that actually runs:

`ops/soak_check.sh` reports `archive within retention budget — N MB = X% of RAM (reopen DEC-0095 at
10%)`. Crossing **10% of MemTotal** (~386 MB today, ~2.6 years out at 0.37 MB/day) is the point at
which this DEC is **reopened**, not quietly tolerated. An unmeasurable tripwire says so out loud
rather than reading as green. All three states are test-pinned with positive controls
(`tests/test_soak_check.py`).

### The InfluxDB half is not ours to decide

Measured at 14 MB engine total, infinite retention, also not binding. But that series is the
**dashboard's history** — its Flux queries read it and its charts render from it — so a retention
change there is a cross-repo interface decision under DEC-0010, not a weewx prune of a shared
bucket. **weewx's position, filed back to ops#175:** we do not propose a horizon, we will not set one
unilaterally, and our only requirement on any horizon the dashboard may later want is that the
loop-JSON and line-protocol contract in `docs/INTERFACES.md` is unaffected. That half of ops#175
stays open against the dashboard, not against us.

### Stated as unmeasured

`filefrag` is unavailable on this NAS, so the archive's **extent count is unknown** and this DEC
makes no claim about how fragmented the file actually is. That gap does not affect the decision —
fragmentation is DEC-0092's lever, not retention's — but it does mean DEC-0092's `chattr +C` will
ship without a before/after extent measurement unless someone builds a FIEMAP probe first.

## DEC-0096 — The campaign harness gains an explicit stand-down state: an empty SCHEDULE is the shipped between-campaigns form

**Date:** 2026-08-18 (S88) · **Status:** Accepted · **Extends** DEC-0066's guard family ·
**applies** DEC-0045's positive-control rule · **unblocks** the v2.0.14 window

### The problem: the staleness guard has no honest green state between campaigns

`test_current_schedule_is_not_fully_stale` (the S73-corrected form of DEC-0066's guard) requires
the shipped SCHEDULE's self-terminator to be in the future. That is exactly right while a campaign
is planned or in flight — a fully-elapsed table sitting in the repo is DEC-0066's trap: `due_arm()`
selects the latest row already passed, so an `install` against it silently joins mid-square or
records the campaign complete without running it.

But `tests` is a **required status check on both `dev` and `main`** (enforce_admins on). So from
the moment a campaign's terminator passes, **every pull request in the repo is red** until the
block is regenerated — and between campaigns there is nothing honest to regenerate it TO. A
placeholder future schedule is worse than a red check: it is a live landmine that `install` would
happily run against prod.

Found at S88 while staging the v2.0.14 window: campaign B's terminator (`2026-08-23T00:05`) **is**
the window's opening moment. The cut's own PRs would have landed into a red-blocked repo, with the
fix needed while several other changes were queued behind it.

### The design: empty means stand-down, and every layer knows it

An **empty SCHEDULE block** is the deliberate between-campaigns state:

- `schedule_started()` already returned "not started" on empty (the shell half predated this DEC);
- new `schedule_has_rows()` names the state, and **`install` refuses it loudly** ("REFUSING to
  install: no campaign scheduled") — installing would snapshot a baseline and then tick forever
  doing nothing;
- `due_arm()` returns `NONE` on empty (now pinned by test);
- the six structural tests (latin square, self-terminator, pilot, hold, and both
  `schedule_started` behavior tests) **skip** via `_require_campaign()` — there is no campaign
  shape to assert;
- the staleness guard **passes** — its classification is extracted to `_schedule_state()` with
  three explicit states: `stand-down` (empty), `live` (terminator ahead), `stale` (fully elapsed).

**The stale branch is positively controlled** (DEC-0045): a fully-elapsed non-empty schedule must
classify `stale`, never slip through the emptiness gate by being old. The gate keys on emptiness
alone. A stale real schedule fails exactly as before this DEC.

Five new tests, including an end-to-end `install` refusal against the real script text with its
SCHEDULE block emptied — byte-for-byte the state a post-campaign stand-down commit ships.
299/299 full suite.

### What this deliberately does not do

The dev schedule itself is **untouched** — campaign B runs to completion on its installed NAS
copy, and the repo's shipped table stays live until the square closes. The post-square PR that
empties the literal is a trivial deletion, self-consistently green under this support, and must be
the **first PR of the v2.0.14 window** so nothing else queues behind a red check.

No `schedule --generate` mode was added (the NOTE comment's dev-side recipe stands); no tick/guard
behavior changed (the installed copy always has rows — `install` refuses the empty form, so the
stand-down state can never reach the NAS through the sanctioned path).

---

## DEC-0097 — The "reception-floor dip" is not a reception measurement; it is RF-dead episodes, and they cluster post-midnight

**Date:** 2026-08-18 (S89) · **Status:** Accepted (measurement) · **Retires** BOOT job 2's watch as a
distinct phenomenon · **feeds** blocker 2 / DEC-0081 / DEC-0083 · **extends** DEC-0094's side
result · **applies** DEC-0069's exclusion rules and DEC-0083's unit lesson · **changes no code**

### The claim under test, and why it was never tested

BOOT carried a watch across four sessions: a reception-floor dip recurring nightly, "window
drifting later" (02:15 → 03:25 → 03:30), n=4, flagged as needing "the proper statistical test —
judgment work". DEC-0094 had refuted the nightly lead for *freezes* and S85 for *stall episodes*;
this reception-floor metric was recorded as the one nobody had tested.

It turns out three of the watch's four premises do not survive contact with the logs.

### Correction 1 — the record itself was wrong

`rx_experiment.log`'s PAUSE/RESUME lines pair one-to-one (the guard cannot log a fresh PAUSE while
a PAUSE sentinel exists), so cycles are countable exactly:

| Night | Arm | Onset | Cycles | End |
|---|---|---|---|---|
| 08-15 | A | 02:15 | 3 | 02:45 |
| 08-16 | B | 02:15 | 2 | 02:35 |
| 08-17 | C | 03:25 | 4 | 04:20 |
| 08-18 | D | **02:55** | **5** | 03:45 |

BOOT and the S88 CHANGELOG entry both record 08-18 as "03:30–03:45, 2 cycles" — the tail of the
episode, not the episode. Corrected onsets are **02:15, 02:15, 03:25, 02:55**: not monotonic, and
"drifting later" was the watch's stated reason for rejecting a fixed-clock artifact.

Also visible once the arms are read off: the four nights are arms **A, B, C and D** — every
gain × receive-window combination in the square. Whatever this is, it is not an arm effect.

### Correction 2 — reception does not dip

Tested on the honest instrument, the archive's per-minute `rxCheckPercent` (DEC-0069/S31), not the
monitor's 30-min mean that fires the PAUSE. The two are different instruments and the 50% floor
does not transfer between them.

The window and the notion of "a dip" were both derived from 08-15..08-18, so testing them on those
same nights is circular. The hypothesis was therefore tested on **31 pre-campaign nights
(07-15..08-14)** that played no part in generating it, contrasting the dip window against its own
flanks *within one arm block* (00:05–06:05), which holds gain, receive window and arm constant by
construction:

    d = mean(rx in [02:00,04:30)) - mean(rx in [00:35,02:00) u [04:30,06:00))

    held-out: n = 31 nights, mean d = -0.01 pts, median +0.10, 12/31 negative
              Wilcoxon signed-rank p = 0.60 · sign-flip permutation p = 0.47

There is no dip. On the four campaign nights the deepest 30-min rolling mean never fell below
**68.4%** against DEC-0059's measured 73.3% baseline (sd 4.67), and **0 of 35 nights** in the whole
34-day record put a 30-min mean under 50% — while the monitor was reporting 20%, 36%, 45%.

### What is actually happening: truncated records, not degraded RF

The raw per-minute rows across every episode have one shape — a pathologically low record, then
minutes **absent entirely**, then a NULL, then normal values:

    08-15  02:00=17  [02:01-02:07 missing]  02:08=NULL  02:09=14  [...]  02:23=68 → normal
    08-17  03:17=22  [03:18-03:24 missing]  03:25=NULL  03:26=70 → normal
    08-18  03:15=3   [03:16-03:21 missing]              03:22=76 → normal

`campaign_analyze.py` already documents this mechanism: a record assembled from a truncated
accumulation period still divides by the full nominal interval, so it reads artificially low while
`interval` stays 1 and the row cannot identify itself as contaminated. Those artifacts feed the
monitor's laggy 30-min mean, which crosses the 50% floor and trips the PAUSE. **Between episodes
reception is entirely normal (65–90%).**

This also explains why the held-out test found nothing: `partition()` correctly excludes
gap-adjacent records, so DEC-0069's cleaning removes the artifacts — the null result is
confirmation of the mechanism, not evidence against a phenomenon.

### Correction 3 — night 1 was already classified, three sessions ago

DEC-0094 recorded, as a side result: *the 08-15 02:00–02:22 blackout was RF-dead, not a freeze* —
three `rtldavis process stalled` lines inside it, and DEC-0067's rule makes a >150 s gap *with* a
stall line RF-dead. That is night 1 of this very watch. The resolution was never carried forward,
and the watch was opened and carried for four sessions as an untested question.

The episode ledger extends it to all four nights: every overnight episode carries `stalls>=1`
and/or `respawns>=1`.

### The result that does survive, on the right unit

Restated on the episode ledger (`logs/episodes.log`, one row per ALERT→RECOVERY): **do RF-dead
episodes concentrate post-midnight?** Ledger rows are re-clustered first — DEC-0083's central
lesson is that the unit dominates the answer, and the monitor opens a fresh row on every flap
exactly as stall *lines* overcounted one episode 21-fold.

    clustered 30 min → 20 events · 00:00-04:00 holds 9 vs 3.33 expected · P = 0.0028
    clustered 45 min → 19 events · 00:00-04:00 holds 8 vs 3.17 expected · P = 0.0079
    clustered 60 min → 19 events · 00:00-04:00 holds 8 vs 3.17 expected · P = 0.0079

    stall-bearing rows only (unambiguously RF-dead under DEC-0067, no reliance on
    the monitor's reception alerting at all):
        00:00-04:00 holds 7 of 9 vs 1.50 expected · P = 0.00009
        18:00-21:00 holds 0 of 9 vs 1.12 expected

Stable across clustering thresholds, as DEC-0083 requires. **The discriminator matters as much as
the p-value:** DEC-0094's evening window (18:00–21:00), where freezes cluster at P=0.0027, holds
*zero* stall-bearing RF-dead events. Freezes and RF-dead episodes keep different clocks, which is
independent support for the DEC-0081/DEC-0067 position that they are separate phenomena.

It is also not a few bad nights: **7 of 7 ledger dates** carry post-midnight events, including
08-12, 08-13 and 08-14 — which **predate the square**. Campaign B did not cause this, and the
watch's n=4 undercounted it: three of those nights simply never crossed the PAUSE floor.

### Stated against itself

* The ledger is **6.5 days and left-censored** at the ws.5 deploy — that is the age of the
  instrument, not the onset of the phenomenon (`stall_baseline.py`'s standing warning).
* The **24-hour omnibus does not reject uniformity** (X²=27.7, df=23, crit 35.2). Expected counts
  are ~0.8/hour, so the omnibus is weak by construction. This is the same honesty caveat DEC-0094
  raised against itself: corroboration of a pre-specified window, not proof of one.
* The window was **pre-registered by the watch** (BOOT job 2 named 02:15–04:20 across four nights
  before this test existed), which is what keeps the episode test out of the circularity that
  sank the reception test.
* A live alternative explanation is on the table and is **not** discriminated against here:
  DEC-0092 measured a sibling tenant's nightly maintenance running **00:10 → ~03:00–05:10 every
  night**, overlapping this window almost exactly.

### Consequences

**No code changes.** The apparatus is behaving as designed: DEC-0087 scoped the PAUSE to RF-dead
episodes, and RF-dead episodes are precisely what fires it. The flapping (five cycles in one hour
on 08-18) is the entry/exit-share-one-floor behavior S82 considered and deliberately accepted —
two log lines per flap, no config or container touch. The error was interpretive, never
operational.

1. **Retire "reception-floor dip" as a distinct phenomenon.** It is blocker 2 seen through the
   PAUSE log. BOOT job 2 closes.
2. **Blocker 2 gains a timing signature** it did not have: RF-dead episodes concentrate in
   00:00–04:00, on every ledger night, across all four arms. The post-campaign characterization
   (DEC-0081/DEC-0083, root cause deliberately open) should start from that.
3. **Job 6's mechanism probe gains a second target window.** The tenant-load hypothesis fits the
   *post-midnight* window (DEC-0092's maintenance) as naturally as it fits the evening one
   (coffee-radar, DEC-0068/0094) — and they are different windows for different phenomena. A
   host starved on I/O could plausibly starve the driver's packet path into the 150 s watchdog,
   which would read as RF-dead while the RF is fine. `ops/proc_probe.py` should be run across
   00:00–04:00 with control flanks, not only across the evening.
4. **The transferable lesson** is DEC-0094's own, re-earned: *read a DEC's resolution before
   treating its headline finding as live.* A watch was carried for four sessions over a question
   one of its four nights had already answered — and the answer was one row away in the same
   decision log the watch cited.

---

## DEC-0098 — The mechanism probe runs ON the NAS: a laptop-side overnight probe is not a limitation, it is an infeasible design

**Date:** 2026-08-18 (S89) · **Status:** Accepted · **Overrides** BOOT job 6's "read-only from the
laptop, no NAS write" scoping · **required by** DEC-0097's second window · **applies** DEC-0074's
process-evidence rule

### What was built first, and why it was wrong

BOOT job 6 scoped the probe as "sampling `/proc` state across a whole evening window — read-only
from the laptop over ssh, no NAS write." `ops/proc_probe.py` was built to that scope and hardened
inside it: per-batch ssh so a dropped connection costs one batch, a supervisor
(`proc_probe_watch.sh`) that relaunches on process death, an idempotent `--resume`, gap-guarded
deltas so a resume cannot charge hours of accumulated iowait to one hour. All of that is real and
all of it is retained.

None of it addresses the actual failure mode. The design required the owner's laptop to stay awake
for **12+ hours**, which the owner correctly rejected as infeasible. Nothing scheduled locally runs
while a laptop is asleep, and `caffeinate -i` holds off idle sleep but not a closed lid.

**It is worse than inconvenient.** DEC-0097 added a second target window at **00:00–04:00** — the
RF-dead episode cluster. A laptop-side probe can never sample that window at all. So the inherited
constraint did not make half the measurement awkward; it made it impossible. The constraint was a
previous session's scoping choice, not a rule, and it should have been challenged the moment the
overnight window appeared rather than engineered around.

### The design

`ops/proc_probe_nas.sh` runs on the NAS under `nohup`, appending the **same pipe-delimited stream**
`proc_probe.py` already parses. The laptop is then irrelevant: harvest read-only whenever, and fold
it in with `--ingest`, which reuses `parse_line()` so there is exactly **one** parser for both
paths. Merging is idempotent — `--analyze` de-duplicates on `(ts, kind, pid, tid)` — so ingesting
twice, or ingesting a file overlapping a laptop-side run, cannot double-count.

Deliberately not reinvented: the CSV column padding. The laptop version's first cut mis-aligned
system rows by two columns because it padded with literal `|` runs and the header made the result
look correct. Emitting a tagged stream and letting one parser place the fields is what stops that
bug having a second home.

**The footprint goes down, not up.** Driving the sampler remotely meant ~2,700 ssh round-trips over
the run; on the NAS it is `/proc` reads plus an append, and `/proc` reads never touch disk.

### What it costs, stated plainly

* **A Class C NAS write**, approved in chat before anything ran — the script itself, its output
  under `logs/`, and a pidfile at the project root.
* **A resident process on prod during a live campaign.** It is bounded by an end epoch
  (`2026-08-19 05:00`, epoch 1787130000) rather than running until someone remembers it, and it
  checks a `proc_probe.STOP` sentinel every cycle for a clean early stop.
* **Cleanup is owed**: the script, pidfile and its two logs should come off the NAS once the run
  is analyzed. Recorded in BOOT job 6 so it is not left behind.

### Verified, not assumed

Liveness was confirmed by **process** evidence per DEC-0074, not by the output file existing:
`/proc/28699/stat` reads `28699 (proc_probe_nas.) S` and the log grew across two reads.

A trap worth recording: `nasctl cat /proc/<pid>/cmdline` returns **empty** for a live process — the
NUL-delimited file does not survive that path. Read as "process gone" it would have been a false
negative, and it was only caught by positive-controlling the method against weewxd's own known-live
pid, which reads empty too. *A zero from a look-alike tool is a claim, not a result* — the third
instance of that pattern in this repo (`nasctl grep` multi-word, leading-dash globs, host-side `du`
on a bind mount).

## DEC-0099 — NAS-LEASE adoption deferred to the v2.0.14 window, bundled with weewx's first holder exercise

**Date:** 2026-08-18 (S90) · **Status:** Accepted · **extends** DEC-0092 · **answers** ops#169 /
OPS-DEC-0107 · **applies** DEC-0051's forbidden-idiom warning

### Where the thread actually stands

OPS-DEC-0107 (NAS-LEASE) landed 2026-08-15. HLF adopted the same window via their own DEC-0177 —
client live since 2026-08-16, first real acquire/release cycle in the shared log dated 2026-08-18.
weewx is a named participant in the spec (§6) with an already-scoped-but-unbuilt client shape; the
spec's own charter (§9) binds a tenant only when that tenant lands its own adopting DEC. This is
that DEC, and the decision is to defer, not decline.

### What's actually true today, per the spec's own tenant table

weewx has **zero live levers**. The one committed-unbuilt lever — InfluxDB `post_interval`
deferral, proven safe to ~30 min (DEC-0092: `stale=None`, `max_backlog=1e6`) — needs `influx.py`
(a `RESTThread` running inside the container) to see `LEASE_DIR`. It can't: the container's mount
set is fixed at creation and excludes it, so reaching the lever needs a mount that doesn't exist
today. `weewx_monitor.py` already runs resident host-side on a 30 s poll and sees the whole shared
volume — but building only that half would let us READ the lease and have nothing to act on.
Recorded at S85 (BACKLOG.md), true again now.

### The decision: bundle both halves into v2.0.14, don't build a partial piece now

v2.0.14 (~08-23) already recreates the container — weewx 5.5.0, #183's pressure package, DEC-0096's
stand-down support. That recreate is the first moment a `LEASE_DIR` mount costs nothing extra;
adding it today would mean a SEPARATE release-class event (kill→rm→run) for a mount that serves
only this one purpose, ahead of a recreate that's already scheduled.

Concrete plan for that window, recorded now so it isn't re-derived:

1. **Container recreate adds a read-only `LEASE_DIR` mount.** Verify with `nasctl inspect` after,
   per CONSTANTS.md's standing rule — a claimed mount is unverified until inspected.
2. **`influx.py` checks the lease at its own post cadence** (its natural checkpoint; the spec's
   floor is 60 s and explicitly never loop/packet cadence). While a foreign lease is held, raise
   `post_interval` — the only live-adjustable lever we have, and the only one we're offering.
3. **weewx's own first HOLDER exercise: the NAS-native image build (DEC-0078)** wraps `docker
   build` with acquire→flock→release using shell primitives — the spec itself names this as "the
   protocol's first concrete cross-tenant test case." The shape mirrors `rx_experiment.lock`'s own
   break-a-stale-holder-loudly behavior, which the spec's stale/steal language credits as prior art
   from our side.
4. **Any lease-file write we ever do — renewal, if we hold — is in-place** (seek-0 + write +
   truncate on the held descriptor), **never** the `tmp` + `os.replace()` idiom
   `loop_json_writer.py` uses everywhere (DEC-0051's house pattern). The spec's §3 names this exact
   mistake — a rename replaces the inode and silently strands the holder's `flock` on an unlinked
   file, degrading validity to TTL-only with no error anywhere. HLF caught it on their own v1
   review; weewx is the tenant most exposed to it because the wrong idiom is our reflex. Restated
   here, not just in BACKLOG, because a DEC is where a future session is told **not** to re-derive
   it.

### What this does NOT do

Adopt a participant role today. Between now and v2.0.14, weewx holds no lease and yields nothing —
there is nothing built to yield with. ops#169 stays open against weewx until the window actually
lands the client; this DEC is the plan, not the shipment.

### The one thing that needed no adoption at all

Reading the world-readable attribution log for our own analysis isn't gated behind participation —
it's the same posture HLF committed to (correlating `tick_step_timings` against the log). Read once
this session (S90): one real lease-held window exists so far (2026-08-18 00:10–06:10 EDT, HLF's
`daily-maintenance`), and it's far too small a sample to test anything. The result and its caveats
are in `BACKLOG.md`'s NAS-LEASE watch entry, not here — this DEC is about the adoption decision, not
the measurement.

## DEC-0100 — The InfluxDB rollup is dashboard's to build — a Task, not a weewx write-path change

**Date:** 2026-08-18 (S90) · **Status:** Accepted · **completes** DEC-0095's open InfluxDB half ·
**answers** ops#175 · **applies** DEC-0010

### Context

DEC-0095 settled weewx's own SQLite retention (accept-and-monitor) but left the InfluxDB bucket's
horizon explicitly "against the dashboard, not us" — a cross-repo interface call under DEC-0010,
not a unilateral prune of a shared bucket. ops#175 subsequently logged a mutual wait: weewx's
DEC-0095 comment framed it as the dashboard's call, dashboard's reply said they'd declare a
consumer-contract DEC "once weewx picks a shape" — each side waiting on the other. ops broke the
stall with a strawman: accept-and-monitor for Influx too (its own measured tripwire, not SQLite's
number), plus a permanent daily rollup (hi/lo/mean + running record extremes per station/field) so
dashboard's `card-records` all-time-window queries (dash DEC-0111) survive whatever eventually
happens to raw instead of silently reporting wrong answers. "Who builds the rollup" was left open on
purpose.

### Decision

weewx declines to build it. Recommend dashboard builds it, as an **InfluxDB 2.x Task** — the native
scheduled-Flux mechanism (confirmed 2.x per `docs/INTERFACES.md` §2; Tasks are 2.x's replacement for
1.x continuous queries).

### Reasoning

1. **`docs/INTERFACES.md` already draws this exact boundary, unprompted by this thread**: *"The
   dashboard reads InfluxDB only through its own `eh-proxy`... this repo never sees the dashboard's
   read path. Our responsibility ends at writing the documented schema."* A derived rollup
   measurement is a new read-side artifact computed FROM the schema, not part of what we write.
2. **The rollup protects a dashboard-specific feature** — `card-records`'s all-time windows — that
   weewx doesn't consume and has no way to validate. We'd be building blind for a consumer's own
   correctness property.
3. **dashboard "already runs arbitrary Flux against this bucket"** (ops#175's own strawman, and
   independently true — INTERFACES §2 notes the dashboard's Flux queries are written against our
   field names). A Task is Flux-native. `influx.py` has never written a line of Flux; it's a Python
   `RESTThread` speaking line protocol (DEC-0007). Building this in weewx means this repo learning a
   query language it has no other use for, to solve a problem it doesn't have.
4. **A Task changes neither write path.** It reads the existing raw bucket on its own schedule and
   writes a new measurement, entirely inside InfluxDB. No schema change on our side, nothing for
   `docs/INTERFACES.md` to record, no DEC needed on the write-contract half.

### What this is not

Not a refusal to help, and not a mandate on dashboard. If dashboard's own investigation finds the
Task needs something from weewx's write side — a tag, a field, a schema change — that reopens as a
fresh cross-repo interface conversation under DEC-0010, the same path the still-open station-identity
tag question (BACKLOG.md) would take. This DEC settles only who builds the rollup as currently
scoped, not every future ask.

## DEC-0101 — SMTP TLS went unverified at both alert-mail call sites; the WeatherLink key could leak into weewx.log via exception text

**Date:** 2026-08-18 (S91) · **Status:** Accepted · **extends** DEC-0062's log-egress rule ·
**fixes an unverified-TLS regression** against the pattern `influx.py` already uses · **applies**
DEC-0045's positive-control rule

### Context

S91 ran the full-repo security audit BOOT job 7 scoped at S90 close: four Sonnet-tier finder agents,
each DEC-primed and each covering one file (`rtldavis.py`; `pressure_service.py` +
`dewpoint_service.py`; `weewx_monitor.py`; `ops/rx_experiment.sh`), followed by one Opus-tier
verification pass over everything the finders surfaced. Two files came back clean — `rtldavis.py`,
and `weewx_monitor.py`'s own privilege boundary (the sudo-gated USB reset call DEC-0075 governs).
Two independent findings survived verification at 9/10 confidence, both fixed on the same branch
this session.

### Decision

**1. TLS certificate verification, both SMTP call sites.** `weewx_monitor.py`'s `send_email()`
(`smtplib.SMTP_SSL('smtp.gmail.com', 465)`, the continuously-running production monitor) and
`ops/rx_experiment.sh`'s `send_mail()` (`s.starttls()`, the campaign abort-notification path) both
omitted `context=`. Verified directly against the installed CPython 3.14.5 stdlib, not recalled from
memory: smtplib's fallback (`ssl._create_stdlib_context()`) is an unconditional alias for
`ssl._create_unverified_context()` — `CERT_NONE`, `check_hostname=False`. An on-path attacker
(compromised router, ARP spoofing, DNS spoofing of `smtp.gmail.com`) can complete the handshake with
any certificate and either capture `GMAIL_PASS` (a full-mailbox app password, bypasses 2FA) or
silently swallow the message — for `rx_experiment.sh`, that message is the one channel designed to
reach a human independent of the monitor itself, the same "the alert path looked configured and was
never exercised" shape DEC-0061 already found once via a different bug (env-export, not TLS).
`influx.py`'s `post_request()` already passes `ssl.create_default_context()`; this is a regression
against a pattern this codebase already established, not a novel hardening ask. Fix: `context=
ssl.create_default_context()` at both sites (`import ssl` added to each), guarded by
`tests/test_smtp_tls_verification.py` — AST-checking the `.py` site, text-checking the bash-heredoc
site (the same split this repo already uses for `rx_experiment.sh` elsewhere) — each half
positive-controlled per DEC-0045.

**2. WeatherLink API key redacted before it can reach `weewx.log`.** `pressure_service.py`'s
`fetch_pressure()` builds its request URL with `api-key`/`api-signature` in the query string, then
its broad `except Exception as e:` logged `e` directly via `%s`. `requests`/`urllib3` embed the full
request URL in the string form of any connection-level failure (`ConnectionError`, `SSLError`,
`MaxRetryError`) — reproduced empirically in an isolated venv: DNS failure, connection-refused, TLS
failure, and connect-timeout all leaked the key, 4/4. **New gap, not a DEC-0062 regression**: that
decision fixed a different log line (the startup log) and shipped an AST-based regression test
(`tests/test_pressure_service_no_key_logging.py`) that structurally cannot see this one — the
credential exists only at runtime, inside the exception's `__str__()`, never as a source-level
`self.api_key`/`self.api_secret` reference the checker greps for. `weewx.log` also sits outside
DEC-0047's read-guard (configs only), and DEC-0062's own history records this exact log being tailed
into an agent transcript twice already, for the older, now-fixed leak. **Narrower than DEC-0062's
case, though:** only `api-key` and a timestamp-bound `api-signature` are ever in the URL —
`api_secret` (the HMAC key) never is — so a captured line permits replaying that one exact request,
not minting new ones; real but bounded. Fix: `_redact_secrets()`, a module-level regex scrubbing
`api-key=`/`api-signature=` values by query-param NAME rather than by a known local value
(`get_signature()` can itself raise before `sig` is bound, so no local variable is guaranteed in
scope at the failure point), applied to the exception string before it reaches `log.error`.
`tests/test_pressure_service_no_key_logging.py` gained a second rule: a raw exception object, or a
bare `str()` of one, reaching a log call is now flagged on its own, independent of whether it
mentions `api_key`/`api_secret` by name — positive-controlled against the exact pre-fix line.

### Why this needed a DEC and not just a commit

Both fixes establish a pattern future sessions should reuse rather than re-derive: **(a)** any new
`smtplib` call site in this repo must carry `context=`, now mechanically enforced; **(b)** an
exception object is credential-shaped whenever the code that can raise it built a credential-bearing
URL/command, which an attribute-name-based secret checker cannot see on its own — redact by shape
(query-param name) when the exact secret value may not be reliably in scope, not only by known
variable.

### What was checked and not flagged

`rtldavis.py` (subprocess construction, path/device handling, credential handling, deserialization,
crypto/randomness) and `weewx_monitor.py`'s sudo-gated USB-reset invocation and Gmail-credential
handling end-to-end (DEC-0075's grant, DEC-0076/0084's gate history) both came back clean under two
independent passes each — a finder plus the Opus verification agent — against the audit's
hard-exclusion list (no DOS, no theoretical/non-concrete findings, no re-litigating a settled DEC).
Recorded here rather than as their own DEC since nothing changed; the negative result lives in the
S91 session record.

---

## DEC-0102 — The overnight probe measures DEC-0092's flagged confound directly (11.80x iowait), but a minute-level stall cross-check is mixed, not confirmatory

**Date:** 2026-08-19 (S92) · **Status:** Accepted (measurement) · **extends** DEC-0092/DEC-0097's
flagged confound with a direct measurement · **corrects** a control-bucketing bug in
`ops/proc_probe.py` · **does NOT close** blocker 2 / DEC-0081 · **applies** DEC-0074's
process-evidence rule

### What was measured

Job 6's NAS-side probe (DEC-0098) ran its full scheduled window, 2026-08-19 00:00–05:00 EDT, and
exited cleanly on schedule — verified by process evidence, not computed: `/proc/28699` gone, its
pidfile removed, and the script's own `done pid=28699` line timestamped 05:00:25 against a last
sample at 04:59:49, both in the NAS's own local clock. That resolves DEC-0098's unrecorded-timezone
gap as EDT, not UTC. Harvested read-only (`nasctl cat`, byte-exact against the NAS's own `ls`),
ingested and analyzed with `ops/proc_probe.py`.

### The tool bug this ingest exposed

`--analyze`'s "evening window vs control" comparison bucketed control as *every hour not in 18–21*.
Correct as long as only the evening window had ever been sampled. This session's ingest put
00:00–04:00 data into the CSV for the first time — hours carrying massive iowait (03:00 alone:
1169.8s, vs. 25–48s on a normal daytime hour) — and control's own average absorbed the spike it was
supposed to be a clean baseline against. Printed result: evening ratio 0.43x, readable as a negative
result. Recomputed against a control that excludes both named windows: the evening ratio is actually
**1.82x**, not negative — modest but real, consistent with (not proof of) DEC-0094's original
hypothesis. Fixed in `ops/proc_probe.py`: both windows (`evening` 18–21 DEC-0094, `overnight` 00–05
DEC-0097/DEC-0092) are now named explicitly and excluded from each other's control, not just their
own; a `D hits/sample` ratio was added alongside iowait/runq since it's part of what this DEC
reports. 305/305 tests, ruff/mypy clean.

### The overnight number

Overnight (00:00–05:00) vs. that same clean control: **11.80x iowait ms/sample, 5.82x D-state-hit
ratio, 1.52x runq-wait** — the strongest signal anywhere in the dataset, far exceeding the evening
window's 1.82x. Hour 03:00 alone carries 60 D-state hits and 1169.8s of accumulated iowait against a
normal daytime hour's 1–6 hits and 25–48s.

### What this does and does not tell us

This is the first hard kernel-level measurement of the confound DEC-0092 already named (a sibling
tenant's recurring nightly maintenance, measured at S83 as 00:10→~03:00–05:10, median ~4h20m, over 6
nights) and DEC-0097 already flagged as unresolved against the RF-dead cluster ("not discriminated
against"). The overlap between this measured window and DEC-0092's already-documented span is close
enough to read as the same phenomenon, not a new one — job 6 was built for exactly this (DEC-0097
point 3: "a host starved on I/O could plausibly starve the driver's packet path into the 150s
watchdog... read as RF-dead while the RF is fine").

A second, separate event shares the same night: ops#169 (filed 2026-08-18) documents a coffee-radar
Stage D `--full-refresh` sweep ("live... tonight") that independently drove this NAS to ~41%
iowait, and already names weewx's own continuous InfluxDB writes as a suspected, unconfirmed
contributor. Per coffee-radar's own `BACKLOG.md`, that specific trial was stopped early ("clean at
4/230") and any relaunch is now explicitly held until Campaign B closes (2026-08-23T00:05), agreed at
an S186 working-level exchange — so unlike DEC-0092's window, it is not a recurring confound for
future nights. Its exact stop time isn't pinned down precisely enough here to confirm or rule out
overlap with this specific probe window; DEC-0092's routine window, ops#169's one-off event, or both
together all remain consistent with a single night's data.

**Minute-level cross-check, done and mixed, not confirmatory.** Last night's 4 stall lines in
`weewx.log` (02:55:32, 04:46:57, 05:08:24, 05:29:09) — 2 of 4 fall inside elevated-iowait hours
(02:00, 04:00), but the single highest-iowait hour in the whole dataset (03:00, 1169.8s/60 D-hits)
has zero stalls, and 2 of the 4 stalls fall after the probe's last sample (04:59:49), where no direct
iowait data exists to check them against. This neither confirms nor refutes DEC-0097's
I/O-starvation-trips-watchdog hypothesis on this single night's data.

### Root cause stays open

Blocker 2 is not closed. What changed: DEC-0092/0097's confound now has a real number (11.80x/5.82x)
instead of a qualitative flag, and the I/O-starvation mechanism DEC-0097 proposed is plausible and
un-refuted but not confirmed at minute resolution. A single clean re-run would not settle it either —
DEC-0092's window recurs every night, so isolating it needs multi-night minute-level stall-vs-iowait
correlation, not a one-off retry. Recorded here for the next session picking up blocker 2.

### Cross-repo

ops#169 comment posted with this measurement and a pointer to this DEC — informational, no action
requested from coffee-radar or ops; the existing hold already covers the only lever on their side.

---

## DEC-0103 — The bounds/delta split is the repo's QC convention, and it is ported, not imported

**Status:** Accepted · **Date:** 2026-08-19 (S94) · **Extends:** DEC-0054, DEC-0029 ·
**Applies:** DEC-0006 (honest nulls), DEC-0045 (positive controls) · **Closes:** issue #223 ·
**Part of:** issue #227's remediation sequence (5 of 8)

**Context.** Issue #223 (tier:frontier, from the S91 full-repo audit) bundled four defects in
`dewpoint_service.py`'s `_filter_wind` and argued they were one design gap, not four patches: the
filter never adopted the resync-on-reject and co-null behavior that `rtldavis.py`'s `SensorQC` had
already established as correct in this same repo. The issue left two calls open, and this DEC makes
both.

**Decision 1 — the two reject classes are different things, and the difference is the fix.**
`SensorQC.check()` and DEC-0054 already draw a line this filter did not:

| Class | Meaning | Baseline action |
|---|---|---|
| **Bounds** | the reading is impossible per sensor spec, or internally inconsistent (a gust below its own speed) — positive proof of corruption | leave the baseline **untouched**: the value carries no information |
| **Delta** | the reading is an implausibly large *step* — may be a genuine gust front | **always resync** the baseline, even when rejecting |

That single distinction is what fixes #223's item 1 at the root rather than by whack-a-mole. A delta
reject that does not resync freezes the baseline permanently: every later reading is then measured
against a value the weather has left behind, and real wind is nulled until the weewx process
restarts. `SensorQC.check()` says so in its own comment — *"always resync, even on reject... no
stale-baseline deadlock"* — and this filter simply never inherited it. A 300 s TTL
(`WIND_BASELINE_TTL_SECONDS`, deliberately the same number as `QC_RESEED_SECONDS` and this file's own
`CACHE_TIMEOUT_SECONDS`) adds the second, independent escape: a baseline older than the reception gap
that made it stale is reseeded rather than enforced.

**Decision 2 — port the pattern locally; do NOT import `SensorQC` from `rtldavis.py`.**
The cheaper move is `from rtldavis import SensorQC`: one source of truth, less code. Rejected.
`dewpoint_service.py` today has **zero** imports from the driver, and `docs/INTERFACES.md` states the
repo's contract is the data it emits, not any one consumer or producer — the service is meant to
survive being re-pointed at non-Davis WeeWX, and eventually CumulusMX (PRINCIPLES §1). Importing
would couple a driver-agnostic LOOP-packet service to a vendored fork carrying USB and subprocess
concerns, to reuse ~20 lines of pure logic, for a single field where `SensorQC`'s multi-key
generality is not needed. **The duplication is the cheaper of the two costs, and it is deliberate.**
Recorded here because the reasoning is invisible from the code: a later reader seeing two similar
filters should know the second is a considered port, not drift.

**Consequences — one is consumer-visible.** `windDir` is now nulled in every branch that nulls
`windSpeed` (#223 item 2). Previously a rejected speed left a bare heading to reach loop-JSON,
InfluxDB and every uploader, where it reads downstream as real wind. This follows the driver's own
convention in both places it appears (`_data_to_packet`'s *"the same-packet direction byte is equally
suspect"*, and the calm-air gate's *"no direction when calm"*), and it is narrower than DEC-0054's
frame-level co-rejection — which delta rejects correctly still never trigger. Also fixed: the
cold-start warmup buffer is bounds-checked before it can seed a wrong baseline (item 3), and
`windGust` is bounds-checked independently of `windSpeed`'s presence (item 4) — confirmed unreachable
with today's driver, included anyway because the driver-agnostic goal in decision 2 is the entire
reason this file does not import from the driver.

**Evidence.** 10 tests; 6 of 8 behavioral checks confirmed to fail against the pre-fix file via
`git stash`. **The first attempt at that proof was worthless and looked fine**: all 10 tests failed
pre-fix with `TypeError: unexpected keyword argument 'now'` — the signature change, not the defects.
Re-run with a shim giving the old `_filter_wind` the new signature, so only behavior was under test:
6 fail pre-fix with the exact predicted symptom, 0 after, and the 2 convention locks pass on both
sides by design. Full suite 339/339, ruff/mypy clean (57 files, up from 56 — the count is the only
proof the new file was not silently skipped), secret gate positive-controlled.

**Deploy.** `dewpoint_service.py` is **BAKED into the image**, not mounted — established by
`nasctl inspect` and positive-controlled against a known-mounted file rather than assumed from its
sibling `pressure_service.py`. It ships on an image rebuild, gated behind v2.0.14; an `scp` would be
a silent no-op (DEC-0031). `CONSTANTS.md`'s deploy-layer table did not list this file at all — the
same omission S85 found for `loop_json_writer.py` — and gains a row in this session.

*Rationale:* the repo already had the right pattern and the right reasons; #223 was the cost of not
applying them consistently across two files that do the same kind of work. Porting rather than
importing accepts a small, documented duplication to protect a stated architectural goal — the
alternative trades an invisible coupling for twenty lines saved.

---

## DEC-0104 — DEC-0099's gating premise was wrong: weewx's NAS-LEASE client is host-side and unblocked

**Status:** Accepted (correction of record) · **Date:** 2026-08-19 (S94) ·
**Corrects:** DEC-0099's framing (not its plan's content) · **Applies:** DEC-0074 (verify, don't
recall) · **Answers:** the weewx half of ops#169 · **Does NOT adopt** — the adopting DEC is S95's

**Context.** The owner raised ops#169's priority at S94 close: act within the next few sessions.
DEC-0099 (S90) had recorded weewx's adoption as "deferred to the v2.0.14 window", on the grounds that
the one committed-unbuilt lever — InfluxDB `post_interval` deferral — needs `influx.py`, a RESTThread
*inside* the container, to see `LEASE_DIR`, which the container's fixed mount set excludes. That
reasoning is correct **for that lever** and was over-generalized into a gate on the whole client. A
first S94 attempt to act on it amplified the error into `BOOT.md` as a hard deadline ("ship the mount
in the v2.0.14 cut or lose a recreate cycle").

**What re-reading the actual spec establishes.** `eaglehunt-ops/NAS-LEASE.md` §9 had already settled
this, before either framing was written: weewx's client's **"natural home is host-side"**, chosen
precisely so adoption does not cost a release-class recreate.

| Half | Where it runs | Container change? |
|---|---|---|
| **Holder** — wrap the NAS image build (DEC-0078) | the NAS **host** (`docker build`) | **none** |
| **Observer** — read the lease, append `heavy-io.log` | `weewx_monitor.py`, already host-resident, 30 s poll, sees the volume natively | **none** |
| **Yield** — InfluxDB `post_interval` downshift | inside the container | **yes** — the only thing the v2.0.14 mount buys |

So adoption is **not** gated on v2.0.14. The mount remains worth taking opportunistically while the
container is being recreated anyway, but skipping it costs one optional lever, not the client.

**Two further findings from the same read.**

1. **The "two strands" on ops#169 are one strand.** coffee-radar's disk-contention handshake **is**
   this lease: their DEC-0181 Stage 2 landed *as* OPS-DEC-0107. Stage 1 (`--blkio-weight` caps) is
   coffee-radar-unilateral and requires nothing from weewx. There is no second protocol pending, and
   the question S94 nearly posted to ops#169 was already answered in coffee-radar's own `BACKLOG.md`.
2. **★ weewx's adoption is the event that LOCKS the protocol's constants for every tenant.** §5 holds
   them UNLOCKED "until the second adopting DEC lands"; HLF's DEC-0177 was the first. This arrives
   disguised as a merge-order side effect and should be taken deliberately — any amendment weewx
   wants raised on ops#169 *before* its own client DEC lands.

**Pre-flight, verified rather than assumed (DEC-0074).** `LEASE_DIR` exists at
`/volume1/docker/nas-lease/`, mode `drwxrwxrwt` (1777, as §5 specifies) — the one-time owner step is
already done; `heavy-io.log` is live and HLF is renewing against it in production (held ~8.7 h on
2026-08-19, 04:56Z→13:39Z on an 8 h TTL, released `outcome: step-failures`). A weewx client is Python
`fcntl.flock()`, no binary (§9). **Still unverified, and owed before any client ships:** that weewx's
runtime user can create/rename in `LEASE_DIR`; `O_CREAT|O_EXCL` atomicity on the btrfs mount; a
cross-tenant-visible log append. **weewx has no declared renewal floor** (§5: "none declared") —
wrapping the build requires declaring one. §8 already ranks that build, ~08-23, as the protocol's
first cross-tenant exercise.

**Red lines the spec already records for us, restated so they are not re-derived:** the SQLite
archive commit is **never** deferred (the engine restarts after a 120 s busy wait; this station runs
a non-stock `timeout=30` because a 6 s reader lock once cost a 5–10 min outage), and `loop-data.txt`
carries a **hard 30 s ceiling** — the eh-proxy 503s past it and the dashboard treats that as
authoritative station-down. Any lease write is in-place (seek+write+truncate), **never**
`loop_json_writer.py`'s tmp+`os.replace` idiom, which the spec names as silently stranding a flock on
an unlinked inode (DEC-0051).

*Rationale:* DEC-0099 reached the right plan through a premise that would have cost a session waiting
on a recreate it never needed, and the correction is only visible by reading the shared spec rather
than this repo's own record of it. Logged as its own entry because `BOOT.md` is rewritten every
session and a finding left only there evaporates at the next close — while DEC-0099 would have stayed
greppable and wrong.

---

## DEC-0105 — `docs/GOTCHAS.md`: traps are durable, so they leave the always-load tier

**Status:** Accepted · **Date:** 2026-08-19 (S94) · **Follows:** DEC-0072 (standing watches →
`BACKLOG.md`, S67) · **Serves:** DEC-0063's tiering · **Applies:** STANDARD rules 1 and 5 ·
**Answers:** ops#173 (weewx half)

**Context.** `BOOT.md` reached **4,866 tok against a 2,500 cap — 195%**, worse than the 4,427 ops#173
last recorded, because S94 itself added ~1,000 (two DECs and an owner-raised cross-repo item). Four
prior trimming passes (S84) had applied rule 1 as written and moved the number ~50 tok net: deleting
resolved items cannot keep pace with a file that absorbs a session's state every close.

**Decision.** The gotchas block — ~1,700 tok, **41% of the file** — moves to `docs/GOTCHAS.md`, an
on-demand artifact with a `MANIFEST.md` row. The test that justifies it: **BOOT holds what expires at
a session close; a trap in reading a signal never expires.** Nothing in that block was session state,
so none of it belonged in the always-load tier — the same reasoning DEC-0072 used for standing
watches, applied to the other large durable block BOOT had accumulated.

Organized into four sections (false signals · git/PR/handoff · NAS and campaign · liveness and
deployment) so the MANIFEST row can name a **trigger** rather than a topic. An index entry that says
"read this sometimes" is not lazily loaded, it is unread.

**The structural claim, and its one condition.** The cap holds only if **new traps are appended to
`GOTCHAS.md`, never to `BOOT.md`**. That instruction is stated in both files, but `BOOT.md` is
rewritten every session and cannot carry a durable rule — so `MANIFEST.md`'s row is the load-bearing
copy. If a future session appends traps to BOOT again, this decision has failed and the file will
re-cross the cap within a few sessions at S94's observed growth rate.

**Rejected: distributing the entries into the canonical docs** (`CONVENTIONS.md`, `ARCHITECTURE.md`,
`CAMPAIGN-B-RUNBOOK.md`) by topic. Each entry would land in a defensible home, but the *class* would
stop existing — and the class is the point: these are traps in **using a tool or reading a signal**,
not facts about how the system is built. The canonical docs say what things are; this one says how
they mislead. Splitting them also multiplies the chance one is silently lost in a move.

**A rule-5 trap found while doing this, worth recording because the remedy text does not warn about
it.** The first draft of the new file also pulled in the gate commands, the baked-vs-mounted deploy
table, and the pyc cache from `CONVENTIONS.md` / `CONSTANTS.md` / `ARCHITECTURE.md` — it read as
completeness. It is STANDARD rule 5's defect exactly: a second copy is not redundancy, it is what
drifts. Eight entries removed, and the file now states the exclusion inline so the next editor does
not re-add them. **Generalizable: moving content OUT of a tier-1 file invites duplicating the
canonical docs INTO the new one, because the new file feels like it should stand alone. It should
not.**

**Cost, taken deliberately.** `MANIFEST.md` goes **1,096 → 1,226 tok** (+130) for the row plus an
honest restatement of its own carried figure, which said "~1.1K" and would otherwise have kept saying
so — the carried-stale-figure shape DEC-0083 exists to stop. That file remains over its own 1,000 cap
under the documented OPS-DEC-0101 carry, where `docs/` rows are named as rule 9's reserved exception.
**130 tokens there bought ~1,700 out of the always-load tier**, and an unindexed artifact is a lost
one.

**Result:** `BOOT.md` **4,866 → 2,406 tok**, under cap for the first time since before S83, measured
the sweep's way (`LC_ALL=en_US.UTF-8 wc -m` / 4, OPS-DEC-0089) against the pushed `dev` tip.
**ops#173 deliberately left OPEN** — the result was posted to the thread rather than the issue closed,
because `MANIFEST.md` is still over its own cap and the automated sweep, not this repo, is the thing
that should call it green.

*Rationale:* rule 1's "delete resolved items" is necessary and, at this file's size, insufficient —
four passes proved it. The remaining bulk was not stale, it was **misfiled**: durable content sitting
in the tier reserved for what changes every session.

---

## DEC-0106 — The crash-loop that wasn't: an undated, accumulating log tail reads history as now

**Status:** Accepted (measurement + fix) · **Date:** 2026-08-20 (S95) · **Refutes:** #245 / ops#184's
crash-loop reading, **not** the owner's trend observation · **Applies:** DEC-0045 (positive control),
DEC-0074 (a file/counter proves the artifact, never the process) · **Extends:** DEC-0067's freeze
taxonomy with a fourth class · **Does NOT touch:** blockers 1 and 2

**Context.** #245, cross-tracked as ops#184 and labelled tier:frontier, reported `weewx-rtldavis-v2`
crash-looping: `RestartCount: 0` while the container's stdout showed RTL-SDR re-detection cycling
repeatedly inside a 30-line tail, with HLF observing stale rows downstream. The owner added the part
that mattered more than the snapshot: *"I have been noticing a lot more crashes of weewx lately, it
used to be super stable."* A trend claim, not a one-off.

**The measurement.** weewxd logs `Initializing weewxd version` once per start, timestamped, and
`weewx.log` rotates daily — so the restart history is directly countable, per day, for a month.
Aug 15–19 returned **exactly 4 startups a day, every one at HH:05 ±30 s**: 00:05, 06:05, 12:05,
18:05. Those are precisely the four scheduled Campaign B arm swaps, 6 h apart. **Zero off-schedule
restarts in five days.** The contrast case sits in our own history: 2026-08-06's `journal_mode`
crash-loop ran **07:18:55, 07:20:18, 07:21:39, 07:22:25, 07:23:08, 07:23:58, 07:25:48** — seven
starts in seven minutes, 43–90 s apart. **The healthy and pathological signatures differ by three
orders of magnitude**, which is why this was answerable at all.

**Why the report looked exactly like a loop — three things compounding, none of them a misreading.**
Container stdout carries **no timestamps**. **`docker restart` does not increment `RestartCount`**,
so the reported `RestartCount: 0` was truthful *and* carried no information about the process. And
the container object was **8 days old and restarted rather than recreated**, so its stdout
accumulated every restart into a single stream. Net effect: ~32 routine restarts stack up
consecutively, and a 30-line tail shows about four of them back-to-back that are in fact **six hours
apart**. Corroborated by count: in a `--tail 200` window the three restart markers (`Starting
weewx`, `Bias-tee`, tuner detection) each appear **exactly 27** times — 27 × ~7 lines ≈ 189 against a
200-line cap, so 27 is itself truncation and the true figure is ~32 = 8 days × 4/day.

**The owner's trend observation is correct, and the cause is benign.** Restarts per day, measured
across the rotated logs: **0/day Jul 20–24** (no campaign), 1–5/day Jul 25–Aug 2 (Campaign A),
**mostly 0/day Aug 3–14** (between campaigns), **4/day Aug 15–19** (Campaign B). So "it used to be
super stable" is literally accurate — between campaigns the rate is *zero*, and Campaign B introduced
four deliberate restarts a day. Every elevated non-campaign day has a known cause: Aug 6 = 7 (the WAL
loop), Aug 11 = 10 (the v2.0.13 deploy), Aug 10 = 3 (v2.0.12). **The zeros were positive-controlled,
not assumed** (DEC-0045): Aug 3's log is full of normal data through 23:59 and contains zero `weewxd`
events, so the zero is real rather than a grep artifact.

**HLF's staleness is not ours.** Through their reported window (19:45–20:07Z = 15:45–16:07 EDT) weewx
was adding archive records **every minute** and publishing to InfluxDB **every minute, successfully**
— `Influx: Published record`, no errors in-window. The day's four driver stalls sat at 02:55, 04:46,
05:08 and 05:29 EDT, DEC-0097's overnight cluster, hours away. The weewx side was healthy end to end
during that window, so the staleness originates downstream — InfluxDB ingest/query or HLF's own read
path. Redirected on the thread rather than left filed against this repo.

**The defect this exposed is structural, and the obvious fix would not have worked.**
`soak_check.sh` computed a real banner count with `grep -c` and then tested only non-zero, so one
banner and fifty read identically green — the gap the S94 session's own soak ran through twice while
#245 was live. But **raising that to a count would still have failed**, because `entrypoint.sh`
`exec`s weewxd: weewxd *is* pid 1, its death takes the container with it, and therefore **every
container lifetime contains exactly one startup banner.** A restart loop is structurally invisible
inside a "since container start" window; it exists only *across* container lifetimes. **So the
detector reads a fixed 6 h window instead**, and fails when two consecutive starts are **<1800 s
apart** — scheduled swaps are 21,600 s apart and real loops are 43–90 s, so the threshold sits in a
gap two orders of magnitude wide. Positive-controlled over 7 cases against the real Aug-6 timestamps,
including both sides of the boundary (1799 s fires, 1800 s does not) and a loop hidden beside a
legitimate swap.

**A rotation trap, caught in verification and proven in production.** The first draft grepped only
the current `weewx.log`. But that file **rotates daily**, so a 6 h window run after midnight spans
two files — the same trap the `mon_resets` check already documents for `weewx_monitor.log`, and the
worst possible place to repeat it, since DEC-0097's stalls cluster at 00:00–04:00. The fix reads
yesterday's rotated file first, and the very first live run (00:0x EDT) proved it was load-bearing:
the window's only start lived in the **rotated** file, so the unfixed version would have reported
**0 starts — a false green** at exactly the hour the real trouble happens.

**Found and filed, not fixed here.** The same rotation blindness affects the soak's *pre-existing*
window computation, which cuts from the first line matching the container-start hour and so collapses
to the new day's log after midnight; four window-scoped checks (startup banner, driver version,
`sensor_qc`, `log_humidity_raw`) currently WARN as artifacts of that, not as findings. Separately,
the long-standing `stdout is chatty — 162 lines` WARN is now **explained**: it is accumulated restart
output on an 8-day-old container, permanent until the next recreate, and not "freeze fuel". Both are
follow-ups rather than in-scope edits, per DEC-0014.

*Rationale:* the reusable lesson is not about Docker. It is that **an unbounded, undated log tail
silently reports history as though it were now**, and every instinct available at the time — the tail
looked frantic, the counter said zero, the soak said green — pointed the same wrong way. What broke
the tie was the one signal carrying *timestamps*, which turned an unfalsifiable impression into
arithmetic. DEC-0074 said a file proves the file and never the process; this extends the same shape
to counters and tails. The owner's "more crashes lately" was the most reliable instrument in the
report, and it deserved a measured answer rather than a reassurance.

---

## DEC-0107 — ops#169 pre-flight: both weewx lease roles are non-root, and the spec gets corrected before adoption locks it

**Status:** Accepted (pre-flight + negotiated positions) · **Date:** 2026-08-20 (S96) ·
**Follows:** DEC-0104 · **Answers:** ops#169's second-tenant round ·
**Deliberately NOT the adopting DEC** — see §What is still owed

### Context

DEC-0104 corrected DEC-0099's gating premise and established that weewx's `NAS-LEASE` client is
host-side and unblocked. It left four things explicitly owed before any client ships: that our
runtime user can create/rename in `LEASE_DIR`, `O_CREAT|O_EXCL` atomicity on the btrfs mount, a
cross-tenant-visible log append, and a declared renewal floor. This session ran that pre-flight
against the live box and settled the resulting spec corrections directly with coffee-radar (their
S205), at the owner's direction, with eaglehunt-ops kept informed throughout.

### The decisive finding: both weewx lease roles run non-root

coffee-radar's ops#169 comment reasoned that both uid gaps would be moot for weewx *"if your client
runs as root under DSM the way your rx_experiment tasks do."* Those tasks **are** DSM root tasks —
but neither of them is the lease client. The two halves that would carry it are **two different
non-root accounts**:

| Role | Runs as | Established by |
|---|---|---|
| **Observer** — read the lease, append `heavy-io.log` | `weewx-monitor`, uid 1031 | DEC-0009's least-privilege account; sudo scoped to `usb_reset.sh` alone |
| **Holder** — wrap the NAS image build (DEC-0078) | the owner's own NAS account, non-root — **named only in the gitignored local-infra doc** | ownership of every `build-v2.0.*` directory under the project root, read this session |

So **weewx is the first tenant these gaps actually bite.** HLF and coffee-radar are both uid 0 today,
which is precisely why three nights of production never surfaced them — every writer so far happened
to be root, so the mechanism looked proven in the one dimension nobody had tested.

**Widening the monitor's sudo grant to work around a file mode was considered and rejected outright.**
That trades a documented security decision (DEC-0009) for a `chmod` somebody else can make.

### The two gaps, and what each costs us

- **Gap A — `heavy-io.log` is `root:root 0644`.** Any non-root tenant gets `EACCES` on append. This
  blocks our holder's **mandatory** `acquired`/`released` events (§4), which is the entire artifact
  §8 designates our ~08-23 image build to produce.
- **Gap B — `LEASE_DIR` is `1777`.** The sticky bit restricts unlink to the file's owner, so §3's
  *"any tenant may break a stale lease"* is unexecutable for us: a stale root-owned lease blocks our
  `O_CREAT|O_EXCL` acquire for the whole 8 h TTL and we run permanently un-announced.

**Gap A is worse than `EACCES` makes it sound, and this is the repo's signature failure shape.**
HLF's client appends under `|| :` and reports `log append failed (non-fatal)` (`hlf_capture.sh:837`)
— correct for their nightly, but it means a non-root tenant does not *error*, it **silently writes
nothing and exits green**. Our whole cross-tenant exercise could complete "successfully" and produce
no artifact at all. A green result from a path nobody has exercised is not evidence (DEC-0045).

### Positions weewx took, and why

1. **Gap B → option (a), drop the sticky bit to `0777`.** Not hypothetical: of the three nightly
   holds in the live log (08-18/19/20), **both that had completed released `outcome: step-failures`**
   — the third was still held when we read it. A nightly that routinely ends in step failures is one
   whose launcher dying mid-hold is a real shape, not a thought experiment. Option (b) — document the asymmetry and let unprivileged tenants
   proceed un-announced — trades a *possibility* for a *certainty*, and lands that certainty on the
   least-privileged tenant.
2. **`chattr +a` on `heavy-io.log`, proposed as optional hardening.** Sticky was *incidentally* the
   only thing protecting the log from unlink — a fact nobody had priced, because sticky had only ever
   been weighed against §3's break clause. Append-only is strictly better than sticky was here: it
   blocks unlink **and** truncate, needs root to set or clear, survives `0777`, and it *enforces*
   §4's "append-only JSONL" instead of leaving it a convention. **Support on this DSM/btrfs build was
   unverified when proposed**, so (a) was deliberately chosen to stand on its own without it. It has
   since been run **and confirmed set by direct observation** — see §What is still owed.
3. **Sequencing: the spec edits and both chmods land BEFORE either client DEC.** §5's constants lock
   at the *second* adopting DEC; locking a spec both tenants already agree is wrong, purely to unlock
   and re-amend it, is churn. Fixing first also **dissolves the who-goes-second question**, which was
   otherwise about to be settled by date coincidence. weewx stated deliberately that it does not care
   whether it goes second, rather than defaulting into it.

### The cost of our own recommendation, priced in writing

Dropping sticky **widens an already-accepted §11 gap**. Under `1777`, unlink is owner-or-root only,
so a non-root tenant cannot remove a *valid* foreign lease even by accident. Under `0777` any tenant
can unlink any lease at any time, including one actively held — after which the holder keeps its
flock on the now-unlinked inode and renews into it unaware, every observer reads the slot as **free**,
and a second heavy job starts. That is exactly the state §3's in-place-renewal rule exists to prevent,
reached by a different route.

This does not change the recommendation — §11 already accepts wrong-lease deletion at these stakes,
and (a) widens it from a same-owner race to an any-tenant one, against (b)'s guaranteed silent
stranding. A low-probability failure that leaves evidence beats a certainty that leaves a hole. But
it is recorded because **naming the cost of your own preferred option is the only way it gets weighed
at all**; `chattr +a` does not cover this, since it protects the log and not the lease.

### Considered and discarded, so it stays discarded

**Break-by-takeover-in-place** — instead of unlinking a stale lease, open `O_RDWR`, take the flock,
re-verify expiry *under* the lock, and rewrite in place. It fixes Gap B without touching sticky and is
genuinely more atomic than rm-then-create. **It fails at release:** a non-root tenant that takes over
a root-owned lease can never unlink it afterward under sticky, so the file becomes permanent and every
subsequent `O_CREAT|O_EXCL` acquire fails **protocol-wide**. Checked against HLF's real acquire and
release code (`hlf_capture.sh:864-876`) before discarding, not reasoned about in the abstract.

### Our declared renewal floor — dated DATA, not a constant (§5's own rule)

`docker build` is a **single invocation with no natural mid-job checkpoint**, so our holder never
renews. This is a third holder shape the spec does not describe — §5's `TTL ≥ 3× renewal_floor_s`
reads as though renewal were mandatory. Our honest declaration is `renewal_floor_s` = the whole
expected job duration. From DEC-0078's ~10 min v2.0.12 build: **floor 600 s, TTL 3600 s** (above the
naive 1800 s, for cold-cache and slower-build margin). **To be re-pinned against the real ~08-23
wrapped build** rather than letting one release's number harden into a constant.

### A secret-hygiene near-miss, caught by another tenant

Verifying the holder's uid meant reading it off the NAS build directories, and the literal account
name then went into three peer messages. **coffee-radar flagged it unprompted**, applying their own
repo's never-commit reflex to a shared surface. Verified rather than assumed: that name appears in
**zero tracked files** here, and our commits are authored under a GitHub `users.noreply` address, so
it is not in the public history either — it is the owner's personal login *and* the local part of the
personal email.

**The hazard was ahead, not behind:** weewx's adopting DEC lands in a **public, permanent** repo, so
the literal name would have travelled from a transcript into published history. The working line,
now applied in this file: **the build account never; `weewx-monitor` and its uid whenever useful**,
since those are deliberately documented already (`docs/ARCHITECTURE.md`, DEC-0009). Nothing to rotate
— a login name is not a credential. This is DEC-0047's rule arriving from an unexpected direction:
the gate guards commits, and the exposure route was a *read* that fed a *future* commit.

### What is still owed, and why this is not the adopting DEC

**Landing an adopting DEC is the event that locks §5's constants for every tenant** (HLF's DEC-0177
was the first). It must therefore lock a *corrected* spec. Items 1 and 2 below closed during this
same session; **item 3 is the only one still open**, and it is not ours:

1. ~~Owner runs `chmod 666` on the log and `chmod 0777` on `LEASE_DIR`.~~ **DONE, same session, and
   verified independently rather than taken on report** (a peer's "it's live" is a claim, not a
   result): `nasctl ls` returns `drwxrwxrwx` on `LEASE_DIR` — sticky dropped — and `-rw-rw-rw-` on
   `heavy-io.log`. **Both gaps are closed on the box before our holder exercise ever runs.**
   **`chattr +a` is also CONFIRMED SET** — owner-run `lsattr` returns `-----a------------`. It got
   there the long way, and the detour is the point: it was run under sudo and reported no error,
   which coffee-radar read as its success signature (correct as a general rule). We declined to
   close on that, because **this box is the origin of our sharpest counter-example** — Synology's
   `db` log driver **accepts `max-size` and silently ignores it** (DEC-0036: 7 h of prod lost to a
   cap that was never real). On *this* hardware, absence of an error is weaker evidence than
   elsewhere. The cost of converting inference into observation was **one read-only command**;
   a write-based probe was explicitly rejected, since it would confirm the attribute by attacking
   the attribution record. **All three fixes now rest on direct observation, none on report.**
   The existing `heavy-io.lease` remains 0644 from its pre-change creation, which is harmless
   (world-readable is all an observer needs) and is exactly what item 3 future-proofs.
   **NAS mutations on a shared resource stayed owner-run throughout — neither tenant session
   executed them.**
2. ~~eaglehunt-ops lands the `NAS-LEASE.md` diff.~~ **DONE, same session — `NAS-LEASE.md` v1.4,
   commit `63e2afc`, `OPS-DEC-0110`**: §4 log kept 0666 · §5 dir cell `1777`→`0777` · §3 holders set
   the lease mode explicitly after create · §5 non-renewing-holder line · §5 weewx floor row · §11
   the widened-unlink sentence. Identities kept generic in the spec text, as asked.
3. ~~HLF patches `hlf_capture.sh:872`.~~ **DONE, same session — their PR #388, merged and deployed
   (`066bbf9f`).** The `set -C` create takes `0666 & ~umask`, so today's 0644 was root's umask being
   lucky, not a rule; under a stricter umask it yields 0600 and silently degrades **every** observer
   to `couldn't tell` for the whole hold. Routed to HLF directly rather than through the issue
   mirror, because a patch needs a file and a line and that does not survive a paraphrase — which
   is also what let them find **a second create we had not flagged**: the steal-then-acquire retry
   path. Had they patched exactly what we reported, the bug would have survived in the branch that
   only runs after a crash, i.e. precisely when the lease matters most. Their fix covers both and
   carries a 0077-umask regression test.

**So all three closed inside this one session, and the round is fully closed** — nothing outstanding
on the NAS-LEASE front from any tenant. weewx's adopting DEC is therefore no longer blocked on anyone
else; it waits only on our own client, and lands with the ~08-23 image build, taking **the next free
number at that time** (not reserved here, since the gap may hold other decisions).

*Rationale:* the reusable lesson is that **a mechanism can look production-proven and still be
untested in the only dimension that matters.** Three nights of `heavy-io.log` proved the protocol
worked *for root*, and every tenant reasoned from that — including, initially, about weewx.
What broke it was not cleverness but reading the actual uid off the actual box instead of inferring it
from a sibling script's behavior, which is DEC-0074's file-proves-the-file rule applied to identity.
The second lesson is procedural and worth as much: the two findings that most improved the outcome
(sticky was also protecting the log; the account name was about to be published) each came from the
*other* tenant looking at our situation, and both arrived because the round was conducted directly
between sessions rather than as alternating comments on an issue.

## DEC-0108 — weewx's NAS-LEASE holder client ships as `ops/nas_build.py`, scoped to the wrapper alone

**Status:** Accepted (design + build) · **Date:** 2026-08-20 (S97) ·
**Follows:** DEC-0107 · **Implements:** the holder half of `NAS-LEASE.md` §6/§9 ·
**Deliberately NOT the adopting DEC** — see §What this does not do

### Context

DEC-0107 closed the round of spec corrections with coffee-radar: "weewx's adoption is no longer
blocked on anyone else... waits only on our own client." This session built that client, ahead of
the ~08-23 v2.0.14 build so the mechanism is tested and boring by the time it runs for real,
rather than assembled under time pressure on the night itself.

### What shipped: `ops/nas_build.py`

A generic lease-holder wrapper: `python3 ops/nas_build.py --job <name> -- <command>`. Acquire is
`O_CREAT|O_EXCL` on `heavy-io.lease`, immediate explicit `fchmod 0644` (§3 v1.4's own rule — a
shell/language default takes `0666 & ~umask`, and a restrictive holder-side umask would silently
ship an unreadable lease, exactly the near-miss DEC-0107 found and fixed on the box), then an
exclusive `flock` held for the wrapped command's whole run. Release removes the lease file and
appends a `released` event with a truthful `outcome` (`clean` / `build-failed` / `crashed`),
wrapped in `try/finally` so a crash still releases rather than abandoning the file to sit until TTL
expiry. A stale foreign lease (flock free **and** `expires_at` passed — both, not either) is broken
and logged as `broken`, naming the stale tenant/job; anything else — a valid lease, or one that
can't be read at all — defers, never proceeds un-announced.

**Generic on purpose, not build-specific:** `NAS-LEASE.md` §6 names TWO holder cases for weewx —
the NAS image build, and manual bulk historical analysis. A wrapper that only knew about `docker
build` would need a second implementation for the other case; wrapping an arbitrary command serves
both from one script.

**Language: Python**, matching two independent signals rather than either alone: `NAS-LEASE.md` §9
already assumed "a weewx client would be Python via `fcntl`, no binary involved" during the
original design round, and this repo's own `ops/` already splits work that way — Python for
protocol/data logic (`campaign_analyze.py`, `freeze_baseline.py`), bash for process orchestration
(`rx_experiment.sh`, `soak_check.sh`).

**Preserves the existing `BUILD-EXIT` marker convention** (`CONSTANTS.md`: verify a build by that
marker, never a pipeline exit code) — but implemented correctly via `subprocess.Popen`'s own
`returncode`, which has no pipeline stage to lose the real exit code in. The manual convention
exists specifically because `docker build ... | tee build.log; echo $?` reports `tee`'s exit code,
not the build's; a Python wrapper reading `Popen.returncode` directly never has that failure mode
to guard against in the first place.

### Scope decision: holder only — the observer side is recorded, not built

`NAS-LEASE.md` §3's read protocol (checking OTHER tenants' leases and downshifting) is explicitly
optional infrastructure for weewx today, for a concrete reason rather than a deferral-by-default:
**weewx has no live downshift lever to act on a "held" verdict.** §6 lists weewx's levers as *live
today: none*; the `current.json` cadence lever is already spent (~1,150/day residual headroom,
nobody plans around it); the InfluxDB `post_interval` deferral is committed-unbuilt and needs
in-container reach this host-side client doesn't have. A courtesy read that can only ever log
`observed-held` and take no other action has a real but currently-unclear benefit — it produces a
data point for the correlation work §4/§8 describe, but nothing this session could point to as
using it. Building it now would be scope growth past "first holder exercise" for a benefit not yet
established. **Recorded here so the option isn't silently lost**, not because it's rejected — the
natural trigger to revisit is the InfluxDB deferral lever actually getting built, at which point an
observer with something to act on is a different, stronger case.

### Provisional constants, to be re-pinned

`RENEWAL_FLOOR_S = 600` / `TTL_S = 3600`, taken as-is from §5's table — DEC-0078's ~10 min v2.0.12
build, explicitly marked there as "placeholder, not measured on the wrapped build." They ship
unchanged in this commit. The ~08-23 v2.0.14 build run under this wrapper produces the first real
measured duration for weewx's holder shape; re-pinning these two literals against that number is
the one piece of this work that cannot happen before the event itself, and is what the eventual
adopting DEC's own numbers rest on.

### What this does not do

- **Does not touch the rest of the ~08-23 release sequence.** `CAMPAIGN-B-RUNBOOK.md`'s existing
  "Release mechanics" list (promote+tag, rebuild, push, regenerate `SCHEDULE=` dates, bump
  `EXPECT_IMAGE`/`EXPECT_DRIVER`) stays exactly as manual as it is today — this wraps only the
  `docker build` invocation itself, not the pipeline around it.
- **Does not build the observer/downshift side** — see above.
- **Is not the adopting DEC.** `NAS-LEASE.md` §5's constants stay UNLOCKED until that DEC lands
  with the ~08-23 build, carrying the real measured floor/TTL and taking the next free DEC number
  at that time.

### Testing

14 new tests (`tests/test_nas_build.py`), exercising a real `flock()` against a `tmp_path` lease
directory rather than mocking it — `flock` is real POSIX and behaves identically on macOS and the
NAS's Linux/btrfs. Covers: explicit `fchmod` winning against a hostile umask (the exact production
near-miss `NAS-LEASE.md` v1.4 documents and DEC-0107 found on the live box); validity as
flock-held-**OR**-unexpired, not either alone (a wedged-but-alive holder past its own TTL must not
be broken); a stale break firing only when both conditions hold; a torn/malformed lease read as
"couldn't tell," never "free" (never broken on a guess); the real subprocess exit code surviving
through to both the `BUILD-EXIT` marker and the log's `outcome` field; and the lease releasing
(outcome `crashed`) even when the wrapped command can't start at all. 373/373 full suite, ruff
clean, mypy clean (61 files, confirming both new files were checked, not skipped), secret gate
clean.

## DEC-0109 — Retire P0.5's last follow-on: Keep-a-Changelog headings + DECISIONS entry-skeleton convergence

**Status:** Accepted (retirement) · **Date:** 2026-08-20 (S98) ·
**Closes:** ROADMAP.md's P0.5 (the only remaining checkbox)

### Context

ROADMAP.md's P0.5 section ("Governance alignment across the family") has carried one unchecked
follow-on since S25 (2026-07-05, ~72 sessions ago): "Keep-a-Changelog headings + DECISIONS
entry-skeleton convergence (proposed S25, never picked up)." S98's job list flagged it for a
discovery pass before any scoping — check what S25 actually proposed before building anything.

### The original proposal is unrecoverable

No session transcript survives: local retention for this repo's Claude sessions starts
2026-07-21, sixteen days after S25. S25's own `CHANGELOG-ARCHIVE.md` entry (`[S25] — 2026-07-05 —
Finish the S24 review fixes`) is entirely about unrelated code-quality fixes (owm.py RESTThread
rebase, influx.py TLS verification, dead-code removal, SPDX headers) — the changelog-format idea
was never written up anywhere beyond ROADMAP's own one-line bullet. That bullet is the entire
surviving record of what was proposed.

### Checked: is this repo behind a family standard? No.

- weewx's own `CHANGELOG.md`: free-form narrative prose per session, no Keep-a-Changelog-style
  headings (Added/Changed/Deprecated/Removed/Fixed/Security).
- eaglehunt-weather-dashboard's `CHANGELOG.md`: same — free-form prose, no such headings.
- hyperlocal-forecast: no separate `CHANGELOG.md` at all; `docs/DECISIONS.md`/`-FULL.md` serve
  that role.

Nobody in the family adopted this. There is no existing target to converge toward, so
"convergence" cannot mean catching up to a sibling.

### The DECISIONS half is separately moot

`docs/DECISIONS-FULL.md` has, since S25, organically grown its own working skeleton — a
`**Status:**`/`**Date:**`/`**Follows:**`/`**Answers:**` metadata line plus a `### Context` section,
consistent across recent entries (DEC-0107, DEC-0108, this one). That happened entirely
independently of `CHANGELOG.md`. It converged with itself; there is nothing left to reconcile.

### The judgment call: not just absence of evidence

Beyond the missing rationale and the lack of a family precedent, retrofitting Keep-a-Changelog's
Added/Changed/Deprecated/Removed/Fixed/Security categories onto this repo's actual entries would
likely make them worse. Entries here are dense, cross-referencing narratives — a single bullet
routinely spans a shipped fix, the measurement behind it, the PR, and a cross-repo pointer (see
DEC-0108's own CHANGELOG entry, above). A rigid single-facet schema built for simpler,
one-thing-per-line projects would fragment that causal narrative rather than clarify it. 72
sessions unclaimed, zero family adoption, and an architectural reason it likely never took hold
are read together as a real signal, not a gap waiting to be filled.

### Disposition

ROADMAP.md's P0.5 line struck through as retired (not done); P0.5 as a whole is now fully closed —
nothing carries forward.

## DEC-0110 — Archive-level reception-quality wind guard, in response to ERR-0004/ERR-0006

**Status:** Accepted (design + build) · **Date:** 2026-08-20 (S98) ·
**Follows:** ERR-0004, ERR-0006 (`docs/DATA_ERRATA.md`) ·
**Implements:** the `BACKLOG.md` "Reception-quality-correlated wind guard" proposal

### Context

`ERR-0004` (2026-07-27) and `ERR-0006` (2026-08-20) are the same blind spot recurring
independently: a mid-magnitude phantom wind reading (37–39 mph from calm) that passes both
`rtldavis.py`'s bounds check (0–200 mph) and `dewpoint_service.py`'s 75 mph/packet delta cap,
because a genuine squall gust of similar size is real and routine — tightening either threshold
risks false-rejecting real weather, and `ERR-0004`'s own writeup already established that. Neither
incident had another field in the same corrupted frame also fail bounds, so DEC-0054's frame
co-rejection had nothing to trigger on.

Both incidents share a signal neither filter consults: `rxCheckPercent` for that one archive
minute collapsed to 13.2%/9.2%, against a 60–90%+ baseline every surrounding minute.

### Measurement (owner-requested before any design was fixed)

Queried the full archive (93 days, 129,607 records, 87,310 with non-null `rxCheckPercent`) to
check the one thing that would have made this design actively harmful: does genuine severe
weather also degrade reception at this station (e.g. rain/wind attenuating 915 MHz)? If so, a
reception-based guard would silently discard exactly the extreme-weather data a station exists to
capture.

- **`rxCheckPercent` distribution:** p50=72.7%, p25=66.7%, p10=62.8%, p5=60.0%, p1=55.0%.
  Records under 20% are genuinely rare: 89/129,607 (0.10%).
- **The key check — high wind vs. reception, cross-referenced both directions:**
  - Of 220 archive records with `windGust>=10 mph` (post-correction), the LOWEST
    `rxCheckPercent` among them is 54.5% — nowhere near the collapse range. (`windGust>=15 mph`,
    n=14: minimum 63.6%.)
  - Of the 89 records with `rxCheckPercent<20%`, 87 recorded `windGust` of 0–4 mph — genuinely
    calm. The only two exceptions were `ERR-0004` and `ERR-0006` themselves (both since
    corrected to NULL, which is why they show as absent wind in this same query — verified by
    hand-checking their known original values instead).
- **Conclusion:** at this station, severe reception collapse and genuine high wind have never
  co-occurred in 93 days of history. A guard combining both signals would not have touched any
  known-good gust on record, with wide margins on both sides (>2.5× on the wind threshold,
  >2.7× on the reception threshold — see thresholds below).

### Design

Two-factor guard, checked once per archive interval:
`rxCheckPercent < 20.0` **and** `windGust > 10.0 mph` → null the wind triple for that record.

- **20.0% threshold:** both known incidents (13.2%, 9.2%) sit well under half of it; only 0.10%
  of all records fall under it at all.
- **10.0 mph threshold:** >2.5× the observed benign-collapse ceiling (4 mph) and well under
  half of both known corrupt values (37/39 mph) — wide margin against false-nulling a real gust
  during a coincidental reception dip, while still catching a smaller future corruption event
  than either historical incident.
- **Why not tighten the existing bounds/delta checks instead:** already tried and explicitly
  rejected by `ERR-0004` — the wind value alone cannot distinguish the two cases at this
  magnitude. This guard uses an orthogonal signal (reception quality) instead of a tighter
  version of the same one.
- **Why archive-record time, not loop-packet time:** `rxCheckPercent` is an interval statistic,
  not final until the interval closes — a per-loop-packet filter (`_filter_wind`) structurally
  cannot know it yet. Archive-record time is also the correct choke point regardless:
  `user.dewpoint_service.DewpointCacher` sits in `weewx.conf`'s `process_services`, which runs
  before `archive_services` (`StdArchive`'s own DB write) and `restful_services` (every
  uploader — Wunderground, CWOP, PWSWeather, OWM, WOW, WOW-BE, Ogoxe, Influx), confirmed
  directly against the live `[Engine][Services]` ordering rather than assumed.
- **What this does NOT reach:** Wunderground's RapidFire feed publishes near-instantly per loop
  packet, before the interval even closes — a live ticker, constantly overwritten, not an
  archive of record, and outside what an archive-time guard can affect. Named explicitly so it
  isn't mistaken for a gap in this fix.

### Implementation

`dewpoint_service.py`: `DewpointCacher` gains a `NEW_ARCHIVE_RECORD` binding
(`new_archive_record`), nulling `windSpeed`/`windGust`/`windDir`/`windGustDir` plus the
archive-only derived fields `ET`/`appTemp`/`windrun` (DEC-0037) — the same field set the
`ERR-0004`/`ERR-0006` manual corrections used by hand. `RXCHECK_COLLAPSE_PCT`/
`COLLAPSE_WIND_GUST_MPH` module constants carry the measurement above as inline comments, so the
numbers don't decay into unexplained magic values. Threshold comparisons run on the
mph-normalized reading (`_WIND_TO_MPH`, #224), so the guard is unit-system-correct for
METRIC/METRICWX configs too, not just this station's US default.

11 new tests (`tests/test_dewpoint_archive_rxcheck_guard.py`): both incidents replayed verbatim
as positive controls (`ERR-0004`'s and `ERR-0006`'s exact recorded values, pre-correction);
genuine high gust at normal reception survives untouched (the station's actual day-max, 19 mph
@ 72.7%); a moderate gust just outside the collapse threshold survives; calm wind during a
benign collapse survives; both thresholds' exact boundary (strict `<`/`>`, matching this file's
existing bounds-check convention) is pinned in both directions; missing `rxCheckPercent`/
`windGust` is a no-op, not a crash; unit conversion is exercised in both directions (METRICWX)
so a corrupt event doesn't slip through unconverted and a calm reading isn't inflated past the
threshold by a units bug. The four existing `dewpoint_service` test files needed a
`weewx.NEW_ARCHIVE_RECORD` stub addition (their `weewx` module mock didn't carry it, and
`DewpointCacher.__init__` now binds to it unconditionally) — mechanical, no behavior change to
what they test.

**Verified:** 397/397 full suite (was 386; +11 new, 0 regressions), ruff clean, mypy clean (63
files, `.mypy_cache` cleared first per this repo's own gotcha), secret gate clean.

### Deploy gate

`dewpoint_service.py` is baked into the Docker image (same layer as the driver, DEC-0031) — this
ships with the same ~08-23 v2.0.14 build already gated for `#225`'s fixes, not before. No urgency
to force an earlier cut for this alone; the guard protects going forward once it deploys, and
does not (cannot) retroactively touch anything published before that.

### What this does not do

Does not attempt a third occurrence's root cause (the underlying RF corruption mechanism itself
remains uncharacterized, same as `ERR-0004`/`DEC-0081`'s broader RF-dead-episode work). This is a
detection/suppression guard at the archive choke point, not a decode-layer fix.

---

## DEC-0111 — `influx.py` NAS-LEASE courtesy yield: the observer/downshift half DEC-0108 deliberately left unbuilt

**Status:** Accepted (design + build) · **Date:** 2026-08-21 (S99) ·
**Follows:** DEC-0099, DEC-0104 (the original plan) · DEC-0108 (built the holder half only) ·
**Implements:** the `post_interval` yield lever named in both

### Context

DEC-0099 designed a three-part plan for weewx's NAS-LEASE adoption: mount `LEASE_DIR` read-only,
have `influx.py` poll it, and raise `post_interval` while a foreign lease is held. DEC-0104
corrected DEC-0099's gating premise (adoption isn't blocked on a v2.0.14 container recreate) but
left the plan's content standing. DEC-0108 then built the **holder** side (`ops/nas_build.py`,
wrapping weewx's own NAS image build) and explicitly scoped the **observer** side out: "weewx has
no live downshift lever yet... a courtesy check with nothing to act on has unclear benefit." This
session builds that lever, at the owner's direction, bundled into the same v2.0.14 build-prep work
that also moved Docker Hub's `:latest` tag to the now-proven `:v2.0.13` and confirmed the next DEC
number is unclaimed.

### Mechanism, verified against real weewx source, not recalled

Rather than trust recollection of how `weewx.restx.RESTThread` handles `post_interval`, the actual
weewx 5.5.0 sdist was downloaded to a scratch directory and inspected directly. Confirmed:
`self.post_interval` is a plain instance attribute (`RESTThread.__init__`, `self.post_interval =
to_int(post_interval)`), read fresh on every queued record inside `skip_this_post(self, time_ts)`
(`restx.py` lines 556–576) — no caching, no local-variable capture, no thread restart needed for a
runtime mutation to take effect on the next record.

### Design

`InfluxThread` gains an opt-in `lease_dir` constructor param, default `None` — off entirely unless
`weewx.conf`'s `[[Influx]]` stanza sets it, matching this repo's existing optional-arg convention
(`site_dict.setdefault('lease_dir', None)`, same pattern as `verify_ssl`/`augment_record`/etc.).
On construction (after `super().__init__()` has already set `self.post_interval`), the configured
value is saved as `self._base_post_interval` and the lease file path is precomputed.

A thin `skip_this_post` override re-derives `self.post_interval` on every call, before delegating
to the base class for the actual stale/interval logic:

```python
def skip_this_post(self, time_ts):
    self.post_interval = (LEASE_YIELD_POST_INTERVAL_S
                           if self._foreign_lease_active()
                           else self._base_post_interval)
    return super(InfluxThread, self).skip_this_post(time_ts)
```

No separate restore path exists or is needed — every call re-evaluates fresh, so the value tracks
lease state automatically as it changes.

**`_foreign_lease_active()`** reads `heavy-io.lease` (same file, same JSON shape `ops/nas_build.py`
already writes) and returns `True` only for a lease that is (a) present and parseable, (b) not our
own (`tenant != TENANT`, matching `nas_build.py`'s own constant — duplicated rather than imported,
since ops/ scripts and this in-container service run in different execution contexts), and (c) not
expired. **Any other outcome — unmounted `lease_dir`, missing file, corrupt JSON, a missing
`expires_at` key, a permission error — returns `False`.** This is the one load-bearing design
choice: the fail-safe direction is "post normally," never "yield defensively." An uncertain read
must never be allowed to silently slow this repo's own data path — the same asymmetry
`ops/nas_build.py`'s own `_read_lease` already applies on the holder side (`None` on any read
problem, never treated as free).

**Why not yield to weewx's own held lease:** the yield exists as a courtesy to *other* tenants
(`NAS-LEASE.md` §3's own framing, quoted in DEC-0104). If weewx's own `nas_build.py` job is
running, that's already a deliberate, self-scheduled resource use — nothing to defer to.

**1800s (30 min):** re-uses DEC-0092's own data-integrity analysis rather than re-deriving it —
live prod runs `stale=None` and `max_backlog=1,000,000`, so a 30-minute deferral queues roughly 30
records against a million-record cap and loses none.

### Implementation

`influx.py` (`VERSION` bumped `0.20+ws.1` → `0.20+ws.2`, per this file's existing per-patch
convention): the two module constants (`TENANT`, `LEASE_YIELD_POST_INTERVAL_S`), the
`lease_dir` param, `_foreign_lease_active()`, and the `skip_this_post` override. `tests/
test_influx_lease_yield.py` (new — this file had no prior dedicated tests): 10 cases, built on a
`RESTThread` stub that actually implements the real `post_interval`/`lastpost`/`skip_this_post`
shape (verified against the real source above) rather than a no-op stand-in, since the interaction
is exactly what's under test — off-by-default, missing/corrupt/incomplete lease file, own-tenant
lease, foreign unexpired lease, foreign expired lease, the raise-then-restore cycle across two
calls, and an end-to-end check that the base interval is still honored when no lease is held.
407/407 full suite (was 397; +10 new, 0 regressions), ruff clean, mypy clean (64 files,
`.mypy_cache` cleared first), secret gate clean and positive-controlled this session (a planted
fake token was caught, then correctly identified as still-present after a `git checkout` restore
attempt that only reverts to the index — the same gotcha this repo's own memory already carries —
and removed properly via a targeted edit instead).

`CHANGES-FROM-UPSTREAM.md`'s `influx.py` table gains row 6, explicitly marked as original
functionality rather than an upstream-divergence fix (unlike rows 1–5).

## DEC-0112 — Adopt closeout self-naming (`CLOSEOUT-TEMPLATE.md` step 7 / OPS-DEC-0114) as this repo's step 8

**Status:** Accepted · **Date:** 2026-08-21 (S99) ·
**Follows:** DEC-0052 (this repo's 7-step closeout skeleton) ·
**Adopts:** eaglehunt-ops OPS-DEC-0114 / `CLOSEOUT-TEMPLATE.md` step 7 ·
**Resolves:** weewx-rtldavis#264

### Context

eaglehunt-ops offered a closeout-template amendment (weewx-rtldavis#264): as the last action of a
session's closeout, call `set_session_title` on `"self"` to record that the session actually ran
its own closeout. Coffeeradar, eaglehunt-weather-dashboard, and hyperlocal-forecast had already
adopted it (DEC-0190, DEC-0276, DEC-0193 respectively) by the time it reached this repo. Per
OPS-DEC-0001, eaglehunt-ops owns the spec and never the adoption — this DEC is the owner's decision
to adopt it here, made directly (not deferred to after Campaign B, as `BACKLOG.md` had provisionally
marked it).

### Why step 8, not step 7

The generic `CLOSEOUT-TEMPLATE.md` numbers this its step 7. This repo's own closeout skeleton
(DEC-0052, `CLAUDE.md`'s Session ritual section) already has seven steps ending in commit + push —
adopted from `OPS-DEC-0016` and adapted before the generic template's step 7 existed. The spec's
actual requirement is positional ("as the **last** action of the closeout"), not numeric, so it
lands here as step 8, after commit + push.

### What the mark means, and what it deliberately does not

Three separate facts about a session, each with its own carrier (eaglehunt-ops#185's finding, that
collapsing them into one marker was itself the bug):

| Fact | Question it answers | Carrier |
|---|---|---|
| The work landed | did the PR merge? | `ccAutoArchiveOnPrClose` (app preference, already on) |
| The session finished | did it run its own closeout? | **the `✓`, step 8** — the only one this DEC defines |
| The window is open | still resumable? | `isRunning` from `list_sessions` |

The `✓` claims exactly one thing. Its failure mode is silence, not false confidence: a session that
crashes or is abandoned never writes it, rather than something else inferring a wrong answer on its
behalf (the fate of the `session-title-sweep` script OPS-DEC-0114 retired — ~620 lines of
branch-name inference, wrong in all four repos' session counters on its first version).

### Grammar

`weewx S<nums>[ ✓] · <slug>` — e.g. `weewx S99 ✓ · v2.0.14 build-prep + closeout-step8 adoption`.
Matches the existing cross-repo session-reference convention (`CONSTANTS.md`'s Git section: "weewx
S21" vs "dash S40"). No shared regex, no ops-owned matcher — this repo's own label and slug, per the
spec's explicit design (OPS-DEC-0114: "no cross-repo coupling: you write your own label, in your own
grammar").

### Implementation

`CLAUDE.md`'s closeout skeleton gains step 8 (this file, Session ritual section). `BACKLOG.md`'s
provisional "decide after Campaign B closes" line for #264 is removed — the decision is made now,
not deferred; nothing left to backlog. weewx-rtldavis#264 closed with a pointer to this DEC.

### Deploy gate

Two NAS-side, non-repo steps remain, deliberately not done here: the `docker run` invocation for
the v2.0.14 container needs `LEASE_DIR` bind-mounted read-only, and `weewx.conf`'s `[[Influx]]`
stanza needs `lease_dir` set to that in-container path. Both belong to the same ~08-23 build-night
event as `#224`, `DEC-0110`, and the NAS-LEASE holder adoption itself — `weewx.conf` is mounted,
never committed (DEC-0012), so there is no repo-side artifact for this half of the change.

### What this does not do

Does not touch the `LEASE_DIR` mount itself, `weewx.conf`, or any NAS state — code only, gated
behind an opt-in default-`None` parameter that is inert until the build-night deploy steps above
happen. Does not change behavior for any deployment that doesn't set `lease_dir` (every current
install, including this station until the ~08-23 build).

## DEC-0113 — WeatherLink pressure poll tightens from hourly to 5 min, backed by the measured API ceiling (#144 item 3); item 1 reviewed and closed with no change

**Status:** Accepted (research + queued config change) · **Date:** 2026-08-21 (S99) ·
**Resolves:** #144 ·
**Applies:** DEC-0086's documented passthrough mechanism ·
**Queued behind:** DEC-0059/DEC-0064/DEC-0092's campaign-comparability discipline

### Context

#144 (hlf#302's barometer-offset attribution) carried three station-side items, filed
file-don't-fix, every action owner-decision. Item 2 (the triple-field `pressure`/`barometer`/
`altimeter` bug) was already fixed at S82b (DEC-0086/DEC-0091) before this session started. This
DEC closes the other two.

### Item 3 — the poll interval was never actually checked against the API

`pressure_service.py`'s `DavisPressureFetcher` has polled WeatherLink's v2 current-conditions
endpoint at `fetch_interval=3600` (hourly) since early deployment. The owner's own account: it was
set to "what I thought was as fast as the free tier of weatherlink would allow" — a guess, never
verified against the published limit. Checked this session against WeatherLink's own v2 API docs
(`weatherlink.github.io/v2-api/rate-limits`): the documented ceiling is **1,000 calls/hour and 10
calls/second**, uniform across endpoints and account tiers (higher limits exist only as a
large-scale-customer exception). A 300 s interval uses 12 calls/hour — **~1.2% of quota** — leaving
enormous headroom even accounting for research error. Chosen over going tighter still (e.g. 60 s to
match the archive's own write cadence) because `new_loop_packet` only writes `barometer` into
whatever loop packet is open when a fetch completes, and the SQLite archive is built from loop
packets at the fixed 60 s archive interval regardless of poll rate — polling faster than the
consumer's own resolution buys nothing. 300 s cuts the archived barometer from a 60-min
sample-and-hold staircase to a 5-min one, matching the range #144 itself already suggested
("5–15 min").

### Item 1 — the console-vs-METAR offset, reviewed and closed with no change

hlf#302's attribution measured the station's sea-level pressure reading ~+0.03 inHg high against
two independent METAR references (KMQS, KLOM) across two calm/clear windows, equivalent to the
console believing it sits ~30 ft higher than its surveyed 550 ft. Put to the owner directly this
session: **the console does apply an elevation-based sea-level correction, for the surveyed 550 ft,
as designed** — the mechanism DEC-0086 already documented (WeatherLink's cloud side sea-level-
corrects `bar_sea_level` before this repo ever sees it). That mechanism working correctly is not in
question; the finding is a small residual on top of it, quantified and stable across both reference
stations. The owner's call: leave it as-is. This matches #144's own framing ("leaving it as-is is
also fine") — HLF's per-source additive correction absorbs a constant offset by design, and the
station remains ground truth by product definition regardless of the console's exact configured
value. No code, config, or console change follows from item 1.

### Deploy gate

`fetch_interval` lives in the **mounted** `weewx.conf`'s `[DavisPressure]` section (confirmed live
via `nasctl conf` — the file already carries an explicit `fetch_interval = 3600`, so the Python
default is not what's running). Per `CONSTANTS.md`'s deploy-layers rule the mount wins, so this is
a live-NAS edit, not a code change requiring an image rebuild. It still can't happen today: the new
value only takes effect at the next `weewxd` restart, and every restart is deliberately deferred
until Campaign B's square closes (~08-23) to protect Latin-square comparability (DEC-0059/0064/
0092) — the same discipline gating every other change queued behind the v2.0.14 build-night event.
Recorded as a new row in `CONSTANTS.md`'s live-config-deviations table (DEC-0070's class: NAS-only,
no repo artifact, silently reverted by a stock recreate) so it survives future recreates once
applied, and added to `BOOT.md`'s v2.0.14 job list so it isn't dropped on the night.

### What this does not do

Does not edit the live `weewx.conf` now — the value is queued, not applied, per the deploy gate
above. Does not change `pressure_service.py`'s code-level default (3600 stays as the fallback for
any deployment that doesn't set `fetch_interval` explicitly; this station's install already does).
Does not touch the console or WeatherLink cloud account settings — item 1 concludes with no action
by design, not by deferral.

## DEC-0114 — The ~08-23 v2.0.14 build event ships; NAS-LEASE adoption locks (the §5 event DEC-0107 deferred)

**Status:** Accepted (design + build event) · **Date:** 2026-08-23 (S101) · **Locks:** `NAS-LEASE.md`
§5's constants for weewx, the event DEC-0104/DEC-0107 deliberately deferred · **Ships:** DEC-0110,
DEC-0111, #233, #224, DEC-0113's queued config edit, weewx 5.4.0 → 5.5.0 (pinned since S88, `ca3c024`,
first release to actually carry it) · **Re-pins:** `ops/nas_build.py`'s `RENEWAL_FLOOR_S`/`TTL_S`

### What shipped

Campaign B self-terminated on schedule (`BASELINE` row, 2026-08-23T00:05 local), clearing the
precondition every queued change was gated behind. Built natively on the NAS from `origin/dev`@
`efeeebd` (`git archive` → scp → extract, per DEC-0078) under `ops/nas_build.py`'s NAS-LEASE holder
wrapper, tagged `weatheredscientist/weewx-rtldavis:v2.0.14`. Container recreated with the new
`-v /volume1/docker/nas-lease:/nas-lease:ro` bind alongside the existing per-file mounts; live
`weewx.conf` gained `[[Influx]] lease_dir = /nas-lease` (DEC-0111) and `[DavisPressure]
fetch_interval` 3600 → 300 (DEC-0113). Verified post-deploy: driver banner unchanged at `0.20+ws.5`
(confirms the correct image), no new CRITICAL/ERROR lines since restart, `weewxd` on 5.5.0.

### Two real problems found and fixed live, not glossed over

1. **`docker` wasn't on the non-interactive SSH PATH.** The first build attempt crashed immediately
   (`FileNotFoundError: docker`) — `CONSTANTS.md` already documents the binary at
   `/usr/local/bin/docker`, off the default PATH; the wrapper invocation needed the full path passed
   explicitly in `cmd`, not a change to `ops/nas_build.py` itself.
2. **A build genuinely hung for over an hour**, not just ran slow: `docker build` crashed mid-Step
   7/30 on a `weectl` syslog-handler traceback (`FileNotFoundError` connecting a unix socket — no
   syslog inside a container build) and the wrapper process sat at 0:00 accumulated CPU across all
   three PIDs (shell, `nas_build.py`, `docker build`) for 70+ minutes — verified via `ps aux`, not
   inferred from log silence alone. Killed on owner instruction, stale lease file removed (SIGKILL
   skips the `finally`-block release, same shape as HLF's own stuck job earlier this session), log
   rotated aside, retried clean — that run completed in ~360s, Step 30/30, `BUILD-EXIT:0`.
3. **`influx.py`'s DEC-0111 code never reached the running container** despite being baked into the
   fresh image: `influx.py` is a **mounted** file (`CONSTANTS.md`'s deploy-layers table), so the image
   rebuild was irrelevant to it — the NAS-side mount source (`/volume1/docker/weewx-rtldavis/influx.py`)
   still held the pre-DEC-0111 `ws.1` code. Confirmed by the running banner (`service version is
   0.20+ws.1` against source's `0.20+ws.2`) immediately after the "successful" recreate. Fixed by
   `scp`-ing the correct file to its mount source (checksum-verified) and restarting; banner now
   reads `0.20+ws.2`. This is the exact hazard the deploy-layers table exists to prevent, and it still
   required a live verification step to catch — a rebuilt-and-running image is not proof every baked
   change actually took effect.

### The NAS-LEASE adoption lock

Per DEC-0104/DEC-0107, weewx's holder client (`ops/nas_build.py`, DEC-0108) shipped pre-flight-clean
but deliberately did not lock `NAS-LEASE.md` §5's constants until it had run against a real event.
Tonight's build (the retried, successful run) is that event: **`RENEWAL_FLOOR_S` re-pinned 600 → 420
(measured ~360s clean-run duration + ~15% margin), `TTL_S` held at 3600** — deliberately generous, not
tightened to match the measured duration, because this same session also produced a genuine hour-plus
hang on a non-capacity failure (see above); a short TTL would let another tenant break a legitimately
slow-but-alive build, not just a dead one. weewx's adoption of the shared `heavy-io.lease` protocol is
now locked with these numbers — see `ops/nas_build.py`'s module docstring and constant comments for
the reasoning, not just the numbers.

### Live contention exercised the courtesy-first design for real

Before this event could run, `hyperlocal-forecast`'s `daily-maintenance` job held the shared lease
(acquired 04:10 EDT, renewing continuously) and the wrapper deferred cleanly, exactly as designed —
no break attempted. Resolved through direct session-to-session coordination (a new standing SOP this
session, see the parallel session memory) rather than passive waiting: HLF found and killed a
concurrent, lease-unaware manual job of their own that was the actual contention source, then killed
the stuck `daily-maintenance` run itself and cleared its own stale lease after an owner priority call
(`OPS-DEC-0136`). Independently verified on this side at each step (`nasctl cat` on the lease file),
not taken on report.

### What this does not do

`main` promotion is separate and later, once v2.0.14 proves out in prod — not part of this event.
Does not touch the gain-496 adoption — that is DEC-0115, a distinct decision from the same session.

## DEC-0116 — `loop_json_writer.py`'s mount was stale for four weeks despite v2.0.14 shipping; caught closing #172/#204, fixed live

**Status:** Accepted (verification + deploy fix) · **Date:** 2026-08-25 (S102) · **Corrects:** BOOT.md's
S101 claim that `dev`/prod were "in sync" · **Recurrence of:** DEC-0114's `influx.py` mounted-file miss

### What ops asked, and what turned out to be true

An `eaglehunt-ops` session asked this repo to confirm four items were live post-v2.0.14 and close
whichever were done: ops#179 (not started — matched ops's own description, no action), #144, #172,
#204. Rather than taking the ship announcement at face value, each was checked against the running
container directly. #144 held up: `fetch_interval=300` confirmed live via `readconf --nas`, the
triple-field null fix is baked into the running image, and the owner's item-1 decision was already
final. **#172 and #204 did not hold up.** Both features — `barometer_fetch_epoch` passthrough
(DEC-0091) and the `current_interval` 60s throttle (DEC-0093) — live in `loop_json_writer.py`, which
`CONSTANTS.md`'s deploy-layers table already documents as a **mounted**, not baked, file. The
deployed copy on the NAS was checked directly: `mtime` 2026-07-27, hash mismatched `dev`, and grepping
it for `current_interval` and `barometer_fetch_epoch` found neither. A live `current.json` read
confirmed the absence end-to-end (no `barometer_fetch_epoch` field), and `current.json`/`loop-data.txt`
shared an identical mtime — consistent with per-packet writes, not a 60s throttle.

### Why this slipped past DEC-0114's own catch

DEC-0114 caught the identical trap for `influx.py` during the v2.0.14 event three days earlier —
image rebuild doesn't touch a mounted file, only a separate `scp` does — and fixed it live, verified
by banner. That session's verification pass covered the files it touched (`influx.py`, gain config)
but not every mounted file in the deploy-layers table. `loop_json_writer.py` hadn't been re-deployed
since its last real edit (2026-07-27, predating both DEC-0091 and DEC-0093's features by weeks), and
nothing in the v2.0.14 event's own checklist re-verified it, because nothing in that event's scope
touched it. The image bump created no signal, positive or negative, about this file's state.

### The fix

Deployed the current `dev` copy of `loop_json_writer.py` to its NAS mount source
(`/volume1/docker/weewx-rtldavis/loop_json_writer.py`), hash-verified the match, then `docker kill` +
`docker start` (DEC-0008 — never `docker stop`) to force `weewxd` to re-import it. Confirmed live
post-restart: `current.json` picked up `barometer_fetch_epoch` on the first WeatherLink poll, and
`current.json`/`loop-data.txt` mtimes now diverge (throttle active). #172 and #204 closed with the
live evidence in the closing comments; #144 closed separately, its own verification unaffected by
this file.

### The generalizable lesson

**A "dev and prod are in sync" claim is only as true as the last verification pass's scope.** An image
bump proves the baked layer moved; it says nothing about any mounted file not specifically checked
that build. `CONSTANTS.md`'s deploy-layers table lists five mounted files (`rtldavis.py`'s baked
neighbors aside: `influx.py`, `loop_json_writer.py`, `ogoxeUploader.py`, `sortedcontainers`,
`weewx.conf`) — DEC-0114 checked one, this session checked another because two open issues happened
to depend on it. The other mounted files' live-vs-`dev` state is **not** independently verified by
either session and should not be assumed current without its own check.

## DEC-0115 — Campaign B adopts gain 496 (arm B) as the new RF baseline, at exactly DEC-0059's adoption bar

**Status:** Accepted (data + config change) · **Date:** 2026-08-23 (S101) · **Resolves:** the RX gain
experiment DEC-0048/DEC-0059 designed · **Supersedes:** the `73.3%, sd 4.67` baseline figure recorded
in `CONSTANTS.md` (DEC-0059)

### The clean readout

The apparatus log pools 6 campaign attempts (repeated aborted/restarted starts, 2026-08-11 through
2026-08-15) under one `--campaign B` invocation of `ops/campaign_analyze.py` by default — the tool
warns about this itself. Re-run scoped to the real, completed run only (`--since` the epoch of
2026-08-15T00:05 EDT, the first row of the square that actually finished): 32/32 blocks,
2026-08-15T00:05 → 2026-08-23T00:05.

| arm | settings | mean | n | vs incumbent (A) |
|---|---|---|---|---|
| A | gain 372, ex 0 (incumbent) | 72.83% | 2658 | — |
| B | gain 496, ex 0 | 74.83% | 2722 | **+2.00** |
| C | gain 372, ex 50 | 73.28% | 2678 | +0.45 |
| D | gain 496, ex 50 | 74.77% | 2746 | +1.94 |

Gain axis: 496 beats 372 clearly at both extraction levels. Extraction axis: a wash (helps slightly
at gain 372, marginally hurts at gain 496) — matches the S97 interim readout's direction on both
axes, now confirmed on the complete square.

### The margin is real, not comfortable

Arm B clears DEC-0059's ≥2.0-point adoption bar at **exactly** 2.00 points — not comfortably above
it. Arm D (496/ex50) falls just short at 1.94. Put to the owner directly rather than rounded up in
the telling; the owner's call was to adopt B anyway rather than hold for more data, given the
consistent direction across both the interim and final readouts and across both extraction levels.
DEC-0102's overnight-iowait confound (a different investigation track — freeze/RF-dead episodes, not
this gain comparison) was still open as of `BOOT.md`'s last note; recorded here as an interpretive
caveat, not treated as invalidating this result.

### Not pursuing a narrower sweep now

A follow-up sweep at gain values just above/below 496 was considered and explicitly declined for now:
each additional value needs its own multi-day campaign square for comparable statistical power, and
the existing pilot data (P449: n=15, mean 72.65%, *below* the incumbent; P496: n=33, mean 75.56%,
consistent with the full square) suggests the curve is fairly flat near 496 rather than hiding a
sharper nearby peak. Revisit only if a specific reason to suspect a local peak surfaces (e.g. a known
hardware ceiling); otherwise this is closed, not deferred.

### Deploy

Two files edited on the NAS: live `weewx.conf`'s `[Rtldavis] cmd` (`-gain 372` → `-gain 496`) and
`weewx.conf.rx-baseline` (the snapshot `restore_baseline` copies over live config at every campaign
abort/end, per the DEC-0080 lesson — a live-conf-only edit would be silently wiped by the next
campaign's own stand-down path). Verified live post-restart: `startup process '/usr/local/bin/rtldavis
-gain 496 -v -fc 0 -ppm 0 -tf US -tr 16'`. `CONSTANTS.md`'s Hardware/site section updated to record
the new adopted setting and supersede the old baseline figure.

### What this does not do

Does not change `ex` (extraction) from its current value — the extraction axis was a wash, no
adoption case either direction. Does not close `BACKLOG.md`'s gain/receive-window hot-swap item
(ops#179) — that is a mechanism question (swap without a restart), orthogonal to which gain value is
adopted.

## DEC-0117 — Gain / receive-window hot swap: a validated control file, not a command string; and the post-swap watchdog grace that makes it safe

**Status:** Accepted (design + implementation) · **Date:** 2026-08-26 (S103) · **Closes:** the
`BACKLOG.md` §Open ideas hot-swap item, [ops#179] · **Touches:** `rtldavis.py` (vendored fork —
`CHANGES-FROM-UPSTREAM.md`) · **Default:** off; no prod behavior changes until the config key is set

### The problem

Campaign B swapped arms every 6 h by rewriting the `[Rtldavis] cmd` line in the mounted config and
restarting the container. That costs a 600 s settle window per block (~2.8% of campaign data), puts
a restart transient inside every comparison, and carries an abort-on-unhealthy-swap failure class
that has already cost real blocks (DEC-0082's +24 h shift; the S79 incident behind DEC-0087).

S89's finding held up on re-inspection: nothing prevents a hot swap but the feature itself. Gain and
`-ex` are CLI flags on the Go binary, carried in the `cmd` string; `rtldavis.py` never inspects them.
`ProcManager.startup(cmd, …)` already takes the command as a parameter, `shutdown()` kills and reaps
(ws.5 / #233), and the 150 s watchdog exercises that kill→respawn cycle routinely. The whole gap was
the trigger.

### Decision 1 — the control channel carries validated integers, never a command string

A watched control file, path from a new `hotswap_control_file` setting. Absent = feature off, which
is stock/upstream behavior and keeps this upstreamable.

The file accepts **only** `gain` (0–496) and `ex` (0–1000), as integers, bounds-checked. It does not
accept a command string, and must never be extended to.

`self.cmd` flows to `shlex.split()` → `Popen`. A control file carrying raw command text would hand
arbitrary code execution inside the container to anything able to write that path — and that path is
a NAS share, on a public-repo project. Two bounded integers spliced into the existing command is a
config knob; a command string is a shell. The unit tests pin the rejection of unknown names,
non-integers, out-of-range values and a command-string payload specifically, so a later "just let it
pass the whole cmd" convenience change fails loudly rather than quietly.

### Decision 2 — a swap resets the stall watchdog and widens it to 240 s

**This is the part a naive implementation gets wrong, and it would have been expensive.**

`genLoopPackets`' stall watchdog raises `WeeWxIOError` when `_now - time_last_received > 150`.
`time_last_received` is a **local** in that generator and is not reset by a child respawn. A freshly
spawned child is legitimately silent for the radio init period — **US/AU/NZ: 133 s** (the driver's
own comment says the stall timeout must exceed it). So a bare `shutdown()` → `startup()` inherits a
possibly-already-stale timer, trips the watchdog mid-init, and tears the driver down: the feature
built to retire the abort-on-unhealthy-swap failure class would have reintroduced it in a worse
form, on every swap rather than only on an unhealthy one.

Every swap therefore resets `time_last_received`, `time_last_data`, `raw_since_data` and
`hop_since_data`. And a reset alone is not enough: 150 s against a 133 s init is **17 s of margin**,
too thin to run a campaign on. The first packet after a swap gets `HOTSWAP_GRACE_S = 240` instead
(~107 s of margin), reverting to the normal 150 s the moment anything is received — the widened
window is for the init period, not a permanent loosening of the freeze detector. 240 s was chosen
over a tunable setting deliberately: one fewer knob to get wrong, and no campaign has a reason to
tune it.

The three loop-level tests are mutation-verified — removing the grace, removing the reset, or
removing the rollback each turns a green suite red, and a positive-control test proves the same
silence *without* a swap still stalls at 150 s.

### Decision 3 — rollback, an ack file, and honoring the control file at init

**Rollback:** if `startup()` raises on the new command, the last known-good command is started back
up before the error propagates. A rejected gain value must not cost us the receiver. The swap still
reports as having happened, because the child *was* replaced and the watchdog reset is owed either
way.

**Ack file** (`<control file>.ack`, atomic via tmp+rename): records status, the applied values, and
the measured respawn gap. The harness must be able to *confirm* a swap took rather than assume it —
GOTCHAS §4, and DEC-0116 four weeks earlier. It also makes the feature self-measuring against
ops#179's constraint 4: how fast the RTL-SDR device re-opens after a deliberate SIGKILL under normal
conditions has never been measured, and now it is recorded on every swap instead of staying a
known-unknown.

**Honored at init, before the first startup:** a pre-existing control file is applied to `self.cmd`
*before* the initial spawn — no extra respawn, and more importantly a container restart cannot
silently revert a swapped gain to the configured value while the ack file still advertises the
swapped one. That silent-revert shape is exactly what DEC-0116 cost four weeks to notice; it is not
being rebuilt here.

### What this does not do

Does not touch `ops/rx_experiment.sh` — the campaign harness still swaps arms by rewriting the
mounted config and restarting. Converting it is a separate change and is the piece that must not
land mid-campaign (ops#179 constraint 1). Does not change any prod behavior: the setting is unset,
so the poll is a single `if not self._hotswap_path: return False`. Does not add a runtime control
channel to the Go binary — this remains a child respawn, not a live `rtlsdr_set_tuner_gain()` call.
Does not deploy: `rtldavis.py` is a **BAKED** file (`CONSTANTS.md` deploy-layers table), so this
reaches prod only via an image rebuild, never an scp.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179

## DEC-0118 — Production migrates from the NAS to marvin; a live incident was the USB controller, not RF

**Status:** Accepted · **Date:** 2026-08-28/29 (S105) · **Relates to** DEC-0067/0068 (corroborates,
does not close) · DEC-0064/0115 (gain history — neither confirmed nor revisited by this incident) ·
DEC-0111/0114 (NAS-LEASE) · does not change DEC-0011's prod-is-sacred discipline or the deploy-layers
model in `CONSTANTS.md` (baked vs mounted still holds — only the host changed)

### What this settles

weewx-rtldavis's production instance moved off the Synology NAS ("Foundation") onto **marvin**, a
new self-hosted Debian hypervisor (`marvin` repo, `MARVIN-DEC-0062`), the same night the owner called
it — moved up from a planned Saturday to Friday night, 2026-08-28, on the same dark/calm/zero-solar
reasoning. The cutover was coordinated live across four repos (weewx, marvin, eaglehunt-ops,
eaglehunt-weather-dashboard; hyperlocal-forecast looped in) via direct cross-session messaging per the
standing inter-repo SOP, and succeeded. A ~90-minute live incident during the cutover was root-caused
to **the host's USB controller topology**, not any RF or software hypothesis tested first — a
mechanism this repo's own troubleshooting history had never encountered, because until tonight there
was never a second host to compare against.

### Cutover mechanics

- **Transparent to consumers by design.** marvin exports its `weewx-data` tree over NFS; the NAS
  overlay-mounts that export **directly over the path consumers already use**
  (`/volume1/docker/weewx-rtldavis/weewx-data`), so eh-proxy's and HLF's `-v` source strings stayed
  byte-identical — no compose edits, no redeploys, just a container restart once the overlay landed.
- **Ordering hazard caught before it bit:** the archive (`weewx.sdb`, 39.5 MB) had to be copied off
  the NAS to marvin's tenant tree *before* the overlay mount landed, because the overlay hides the
  original directory underneath it — copy-then-overlay, not overlay-then-copy.
  Revised order: stop Foundation → copy `weewx.sdb` → move the RTL-SDR dongle → start marvin's weewx,
  confirm writing → owner overlay-mounts on the NAS → consumers restart.
  Rollback stayed clean at every step: unmount the overlay, the original NAS tree is untouched
  underneath.
- **No registry push existed for the deployed image.** `v2.0.14`'s Docker Hub push logs stop at
  `v2.0.7` (Hub proof follows prod, DEC-0078 — never actually done past that tag). Image crossed via
  `docker save`/`docker load` (608 MB, exact bits, no rebuild) rather than a registry pull.
- **`[[Influx]] server_url`** needed one edit (a docker-network-internal name that doesn't resolve
  from marvin, corrected to the NAS's real IP — InfluxDB itself stays NAS-hosted for now).
- **`[[Influx]] lease_dir`/NAS-LEASE courtesy yield is now a deliberate no-op on marvin.** `influx.py`
  never holds or writes the lease — it is a passive reader that backs its own post_interval off only
  when it can read another tenant's active `heavy-io.lease` file (§ confirmed by source read this
  session: `InfluxThread._foreign_lease_active()`, `rtldavis` `influx.py` lines ~486-507). Marvin
  pointed the mount at a guaranteed-empty directory rather than wiring live cross-host access to the
  NAS's real lease directory (`MARVIN-DEC-0063`) — reasoned as acceptable because every current
  heavy-I/O tenant is itself paused or already migrated. The failure mode is silent by construction
  (any read error → "not held" → normal cadence, no log line), so this is a standing gap, not a bug:
  tracked in `BACKLOG.md` for whenever cross-host lease sharing is actually built.

### The incident: what was tried, and what it ruled out

Once the dongle moved, `loop-data.txt` wrote two packets (22:40:08, 22:40:58) then went silent. Live
troubleshooting, in order:

1. **Gain 496 → 372 (Foundation's own prior production value).** No change. Reasoned from this repo's
   own gain-adoption history — DEC-0059/0115 found removing the LNA (~20 dB of front-end gain) pushed
   the *optimal* receiver gain up (372→496); marvin's position is measurably closer with fewer walls,
   the same physics in reverse, so overload at 496 was a plausible, historically-grounded hypothesis.
   It did not hold up in testing.
2. **`-fc`/`-ppm` frequency correction.** No historical data exists to draw a value from — DEC-0064
   held both at `0` through **every** real campaign specifically to keep other comparisons clean; `0`
   was never varied, never measured as optimal. No sweep files exist in this repo despite a
   contemporaneous belief that they did. Correctly not acted on for lack of evidence, not because the
   hypothesis was refuted.
3. **Process freeze (DEC-0067's own discriminator, applied live).** The original ~20-minute silence
   produced *zero* `"rtldavis process stalled"` raises despite being well past the 150 s watchdog
   threshold — DEC-0067's own table reads that as "main thread not executing," i.e. a freeze, not RF
   silence. This diagnosis was corrected in the same incident once restarts began: a later ~203 s gap
   landed almost exactly on the known 150 s-raise + ~60 s-respawn cycle (DEC-0067/0081's own
   arithmetic), meaning the watchdog was now actively firing and respawning — behavior a genuinely
   frozen process cannot produce. **This is itself a useful, independent corroboration of DEC-0067/0081**
   on hardware neither decision was ever measured on: across roughly an hour of subsequent *healthy*
   operation (good controller, see below) the 150 s watchdog never fired once — the stall/respawn
   cycle appeared *only* under the bad-controller condition. That supports reading DEC-0067/0081's
   original freeze episodes as environmental/hardware-triggered rather than a defect in weewx's own
   code, though it does not by itself identify what triggers them on the NAS.
4. **The actual mechanism: USB controller topology.** Every USB port routed through the B850
   chipset's own xHCI controller broke hop-tracking under sustained streaming, confirmed with
   `rtl_test` directly (not weewx) — a demodulator-agnostic RF-capture tool showing lost samples on
   chipset ports and zero lost samples on the CPU-attached controller. A research pass explained the
   *why*: AMD's AM5 chipset-to-CPU link is a shared, QoS-less PCIe uplink with ASPM power-state
   transitions the CPU-attached path doesn't have — plausible cause for the observed pattern (a
   `rtl_sdr` USB isochronous stream is real-time-sensitive; one dropped hop forces a full blind
   rescan, producing exactly the "one packet, then a `~45-200 s` gap, repeat" metronomic signature
   this incident showed). Moving the dongle to the CPU-attached controller (`11:00.0`) resolved it;
   weewx has run cleanly since.

### Consequences

- **Gain stays at 372, not readopted as a decision.** The controller was the actual defect; 372 just
  happened to be set when the real fix landed, so it never got a clean test against 496 at marvin's
  RF position. A proper re-sweep (Campaign-style measurement, not a snap call) is a `BACKLOG.md` item,
  not resolved by this incident.
- **`debug_rtld` raised to `3`** (per-packet) for the initial soak period; reverts to the driver's
  own default (`2`) once marvin's weewx is proven stable for a few days.
- **Foundation's container stays stopped-but-intact**, not decommissioned, through a real soak — this
  stack has a documented history of multi-day-cycle intermittent issues (DEC-0067 freezes ~1/day,
  DEC-0081 RF-dead episodes) that one clean night does not rule out. Same conservatism this repo
  already applies to image rollbacks.
- **`t-weewx`'s `marvinctl` access key is not yet minted** — self-service deploys to marvin from this
  repo aren't live yet; `eaglehunt-ops`'s own follow-up (§9 step 4, same process CoffeeRadar got).
  Marvin-side sessions drove tonight's deploy directly.
- **A live SQLite-safe backup gap was caught and closed same night**, not left for the next
  scheduled restic run: marvin's `/srv` backup fires at 03:30 and `weewx.sdb` is now a
  continuously-written live database there. A `weewx-db-dump.service`/`.timer` (SQLite Online Backup
  API, `.backup`, not a raw copy — safe against a concurrent writer regardless of journal mode) was
  deployed and armed for 03:15, mirroring CoffeeRadar's own existing dump-before-restic pattern on the
  same host.

### What this does not do

Does not change the data contract — `docs/INTERFACES.md`'s loop-JSON and InfluxDB surfaces are
unaffected; consumers repoint via the transparent NAS overlay mount, not a contract change. Does not
change the deploy-layers model in `CONSTANTS.md` — baked-vs-mounted still holds, only the physical
host underneath the mounted layer changed. Does not resolve DEC-0067/0068's freeze mechanism in
general (the `S`-vs-`D` thread-state question they left open is untouched) — it explains *this*
incident and adds one data point toward "environmental," not a general proof. Does not re-validate or
change the adopted gain (DEC-0115's 496 stands as the last *measured* value; 372 is what's running,
provisionally, pending a real re-sweep). Does not touch InfluxDB's own location — it stays NAS-hosted
for now; only the config pointing at it moved.

## DEC-0119 — ops#183's Influx outage: root cause was external, the backfill tool had two real bugs, and this repo's own alerter was blind the whole time

**Status:** Accepted · **Date:** 2026-08-29 (S106) · **Relates to** DEC-0118 (the migration this
outage followed within hours) · DEC-0074 (file-vs-process liveness — the alerter's failure is that
pattern one level up: a *path* proves nothing about the *service* behind it) · does not change
`CONSTANTS.md`'s deploy-layers model or `docs/INTERFACES.md`'s data contract

### What this settles

weewx's InfluxDB uploads were down 00:14 → 12:08:27 ET 2026-08-29 (~11h54m). The cause was entirely
external to this repo: `eaglehunt-ops`'s own session deleted an InfluxDB auth token (ops#183) believing
it was an unused "old" credential, not knowing it was the same value `influx.py` presents to write —
a sharing relationship that had never been recorded anywhere (weewx's write token had no row in the
secrets register at all before this incident; full record and hardening in `eaglehunt-ops`'s
`OPS-DEC-0162`). **weewx's own config was never at fault** — its token was confirmed unchanged since
at least 2026-08-23 against the genuine pre-cutover baseline, fingerprint-verified without ever
printing the raw value. Fix: a new token, scoped write-only and never shared, minted and installed in
marvin's live `weewx.conf` by a marvin-side session under direct owner authorization (this repo's own
session had no path to make that edit — `marvinctl`'s tier 2 has no arbitrary file write, by design);
`weewx.service` restarted 12:08:27 ET; first new point landed at 12:10:44.

### The backfill tool had two real bugs, now fixed

`ops/backfill_influx.py` — this repo's own sanctioned tool for exactly this situation
(`docs/INTERFACES.md` §2 names it as the repair path) — had never been run against a live outage
before and had two defects that would have made the first real run fail:

1. `INFLUX_ORG` was a committed placeholder (`"YOUR_INFLUX_ORG"`), which would have failed every POST
   with the wrong org.
2. `sqlite3.connect()` opened read-write, which fails (or attempts to create `-wal`/`-shm`) against a
   read-only export — the exact shape of access this incident needed, reading marvin's live archive
   without disturbing the process still writing it.

Both fixed, plus hardening prompted directly by this incident: `--server-url`/`--db-path` CLI
overrides (the execution venue — NAS vs marvin — was undecided when the fix was written, and the
sibling script `backfill_container.py` already carried the exact wrong-venue trap this was written to
avoid), and `$INFLUX_TOKEN`/`$INFLUX_ORG` env-var sourcing so a credential never has to be a literal
CLI argument. Landed on PR #282, tested live in production before the branch merged — the incident
could not wait for the normal order. The entire outage window backfilled clean: 712 records posted, 0
errors, plus small follow-up slices for a boundary and a later maintenance reboot. The one apparent
gap that survived a first pass (`04:00–05:00Z` short by what looked like one record) turned out to be
two correct counts disputing an unstated boundary convention (SQL's inclusive vs. Flux's
`aggregateWindow` exclusive) — not a missing record. The real, unrecoverable shortfalls in two hours
(14 and 6 records against a 60/hr cadence) are genuine source-side loss: this driver's archive
generation runs in `hardware` mode, meaning an archive row only exists if a loop packet was actually
received — the tail of the cutover night's RF reception fight, and the two gain-campaign restarts plus
the 01:12 host reboot, respectively. No import can recover data that was never generated.

### `weewx_monitor.py`'s alerter was blind for the entire outage, and made it worse

`weewx_monitor.py` (repo root — this is this repo's own artifact, not `eaglehunt-ops`'s) watches
`{BASE_DIR}/logs/weewx.log`, hardcoded to Foundation's (the NAS's) path. marvin's NFS export overlay
covers `weewx-data/` — verified live and current throughout this incident — but **not** `logs/`. That
NAS-side log path froze at 22:33:46 ET on 08-28, the moment Foundation's own weewx stopped, and has
not moved since. Every alert the monitor sent afterward — reception percentage, "STILL DOWN" — was
computing from the age and content of a dead file, not the health of anything real. For roughly 14
hours the alerter fired false alarms with exactly the *shape* of a real outage, which is what let the
actual (unrelated) Influx outage run undiscovered until a human noticed the pattern didn't add up. This
is `DEC-0074`'s lesson one level up: a *file path* surviving a host migration proves nothing about the
*process* it used to watch. **Disabled on Foundation** (owner action, DSM Task Scheduler) rather than
repointed — there is no path from Foundation to marvin's live log; the export is one-directional and
does not include it. A second, independently stale watcher (`usb_watchdog.sh`, root-scripts class per
`MANIFEST.md`) was found in the same sweep: it tails the same frozen log and would reset Foundation's
own USB bus on a stall match — inert since it stopped seeing activity, silent since 2026-05-22,
filed on `eaglehunt-ops`#233 alongside this. Neither has a marvin-side equivalent yet — open question,
`BOOT.md` job 10. `logrotate-weewx`, a third watcher pointed at the same frozen file, was caught and
disabled before it fired at 00:05 the same night this DEC was written — it would have rotated the
frozen log into an empty one, turning a detectable staleness signature into a silent one.

### Verification

All twelve publish legs (`Wunderground-RF`, `Wunderground-PWS`, `PWSWeather`, `CWOP`, `AWEKAS`,
`WOW`, `WOW-BE`, `WeatherCloud`, `OWM`, `Windy`, `Influx`, `OgoxeUploader`) confirmed independently
healthy by reading marvin's live log directly, through the newly-minted `marvin-weewx` `marvinctl`
alias — the first real use of that access from this repo's own session (tier-1 reads only; no guard
friction, no relay through a marvin session needed). `WeatherCloud`'s apparent sparseness in an
initial spot-check was a real ~10-minute publish interval, not a gap — confirmed against its own
timestamped log lines, not assumed.

### What this does not do

Does not change `docs/INTERFACES.md`'s data contract or `CONSTANTS.md`'s deploy-layers model — the
credential fix and the backfill are operational repair, not a schema or architecture change. Does not
decide a marvin-side alerter design — disabling the broken watchers on Foundation stops the false
alarms; what (if anything) replaces them on marvin is still open (`BOOT.md` job 10). Does not close
`eaglehunt-ops`#216 (the migration's own tracking issue) — its remaining items (the dashboard's
go/no-go gate re-derivation, an isolation matrix, ops' own closeout report) belong to other repos.
Does not re-litigate `OPS-DEC-0162` — the credential-sharing lesson and the secrets-register hardening
are `eaglehunt-ops`'s decision, referenced here only for the parts that touch this repo's own files.

## DEC-0120 — Rebuild weewx's alerting for marvin: input-staleness as a first-class state, and a remedy that is selected rather than assumed

**Status:** Accepted (design + implementation; deploy deferred) · **Date:** 2026-08-30 (S107) ·
**Answers:** `eaglehunt-ops`#233 · **Follows from:** DEC-0118 (the host move), DEC-0119 (which found
the alerter blind) · **Generalizes:** DEC-0074's log/action drift guard · **Acts on:** DEC-0081's
closed finding that the USB remedy does not work

### The defect is structural, not a wrong path

On 2026-08-29 `weewx_monitor.py` sent ~14 hours of confident "STILL DOWN" mail about six uploaders
that were all healthy — live `rxCheckPercent` ran 74–77% while it reported reception "below 60%".
The obvious reading is "it pointed at the old host's log". That is true and it is not the lesson.

**Every threshold in the file is of the form "nothing has been seen for N seconds", and a frozen
input satisfies all of them simultaneously and indefinitely.** The monitor had no way to distinguish
*the station is down* from *I am blind*, because both present identically to every check it runs.
Repointing the path fixes the 08-29 instance and leaves the mechanism that produced it fully intact —
the next mount change, export narrowing or host move reproduces it exactly.

So blindness became its own state, evaluated *before* any threshold, on two signals that fail
differently: the log's **mtime** (cheap; fooled by a touch, or by a writer that reopens without
writing) and the **timestamp parsed from the newest line actually consumed** (catches content going
stale behind a fresh mtime — the "right path, wrong host" shape, which is precisely what the cutover
produced). Staleness is the worse of the two; five minutes is already far outside normal for a
station publishing every ~3 s and archiving every 60 s.

It is reported as a **distinct alert class**, deliberately not resembling `<svc> DOWN`, and it
**suspends** uploader and reception judgement while it holds. Collapsing the two is the original
defect in one line: fourteen hours of mail asserted six specific things that were all false, when
the one true statement available was "I cannot see."

### What ops#233's own framing got wrong, and it matters

The issue reasons from "there is no path from Foundation to marvin's live log", which is correct, to
a rebuild scoped as if the input were the hard part. Checked directly: **marvin's
`/srv/docker/weewx/logs/weewx.log` is alive, local, and healthy** — growing continuously, rotating
daily, bind-mounted `-v /srv/docker/weewx/logs:/var/log/weewx`. The input problem exists only when
looking *from Foundation*. On marvin itself jobs 1 and 2 (service alerting, reception tracking) port
on an environment variable and nothing else.

Found in the same pass, unrelated to the rebuild but the same family as ops#214: **marvin's copy of
`weewx_monitor.py` is stale against `dev`** (sha mismatch, 50026 vs 50538 bytes). Any deploy must
come from the merged tip, never from what is already sitting on the box.

### The remedy is now chosen, not assumed — and the Foundation body is not ported

The USB unbind/rebind survives in this repo as "a hedge for a genuine (never yet observed) dongle
wedge". The evidence behind that wording: across ~17 forensically-captured events (08-02 ×11,
08-06 ×3, 08-10/11 ×3) it **never once demonstrably fixed a stall**, S73 demoted it 3 → 1 on exactly
that record, and ERR-0005 suspects reset #10 *caused* a strictly worse failure mode.

Porting it to marvin would be worse than useless. `usb_reset.sh` unbinds a driver at a hardcoded
Synology bus path (`/sys/bus/usb/devices/1-3`); marvin's topology differs — `MARVIN-DEC-0051`
reassigned two controller roles — so on a box now hosting two live tenants and a passed-through
ASM3142 the same call either no-ops or resets **someone else's device**.

`REMEDY_MODE` therefore selects the action while the escalation discipline around it (one attempt,
the verify window, one email per outage) is untouched:

| mode | action | for |
|---|---|---|
| `usb_reset` | `sudo usb_reset.sh` — driver unbind/rebind | Synology; **the default**, see below |
| `restart_unit` | `systemctl restart weewx.service` | marvin |
| `none` | detect and escalate only | any host where no remedy has been shown to work |

**`usb_reset` stays the default deliberately.** This is a published extension; silently changing what
an existing Synology install does because *our* host moved would be its own defect, and our evidence
is from our hardware. The efficacy record is documented loudly at the constant instead, so an
operator can opt out on the evidence rather than on our say-so.

On marvin `restart_unit` is not the timid option — it is the *strong* one. `weewx.service` is
`docker run --rm` with `ExecStartPre=/usr/bin/docker rm -f`, so a restart **is** a full container
recreate: the remedy that actually resolved ERR-0005, and the one the Foundation monitor could only
reconstruct via `docker inspect` and mail to a human to run by hand.

### The campaign inhibit

An RX campaign restarts weewx once per arm on purpose. Every one of those restarts looks exactly like
the fault this watchdog remedies, and a remedy landing mid-arm corrupts the block being measured —
the watchdog would fight the campaign it exists to observe. While `CAMPAIGN_INHIBIT` exists, **no
automatic remedy fires; detection and alerting continue unchanged.** The skip is logged with the
action it *would* have taken, because a bare "skipped" line reads, months later, exactly like a
remedy that fired and worked — the same unfalsifiable-record failure DEC-0074 is about.

### Deploy is deliberately deferred, and the unit ships at `REMEDY_MODE=none`

Nothing is deployed this session. The gain campaign runs tonight and restarts weewx per arm; a
monitor landing before it would either fight it or spam reception alerts on every switch. Deploy
follows the campaign.

`ops/weewx-monitor.service` ships with `REMEDY_MODE=none` — alert-only — until two things are true:
the unit has been observed through a full day including a 00:00 log rotation and a deliberate
restart, **and** `t-weewx` has actually been granted a way to restart `weewx.service` (a path-scoped
sudoers entry, or a `marvinctl` tier-2 verb). Setting `restart_unit` without that grant yields a
remedy that fails every time it is needed while looking correct — DEC-0061's "configured-looking,
never exercised, therefore never disproved", which has already bitten this repo twice. For the same
reason `NoNewPrivileges` stays `false` now rather than being flipped later in a separate change.

### Not settled here

The archive DB is mode `0500 t-weewx` and the container writes it as root. If it is in WAL mode, an
unprivileged reader opening it `?mode=ro` may fail needing `-shm` write — the same bug class as
DEC-0119's read-only-export failure. **Unverified; do not assume either way** before enabling the
reception-summary path on marvin.

Ownership stays the three-way split ops#183 needed: the tool is this repo's, the host and the unit
install are marvin's, the coordination is `eaglehunt-ops`'s. `usb_watchdog.sh`'s fate
(`eaglehunt-ops`#233's sibling finding) is not decided here — it remains simply OFF.

## DEC-0121 — Campaign C: the apparatus learns the new host, and refuses to run without its safety net

**Status:** Accepted (apparatus + pre-registration) · **Date:** 2026-08-30 (S107) ·
**Extends:** DEC-0059's apparatus to a second host · **Depends on:** DEC-0120 (the monitor IS the
safety net this now demands) · **Follows:** DEC-0118 (the host move)

### Four ways to run this into production and fail at 3am

`ops/rx_experiment.sh` autonomously rewrites the live `weewx.conf` and restarts prod, unattended,
overnight. Prod moved to marvin (DEC-0118). Checked against the new host, four things were wrong,
and **three of them fail silently**:

1. `DOCKER=/usr/local/bin/docker` — hardcoded, not overridable; marvin's is `/usr/bin/docker`.
2. **The restart mechanism is not portable, and getting it wrong takes prod DOWN.** The script does
   `docker kill` + `docker start`. On marvin `weewx.service` runs `docker run --rm` with
   `ExecStartPre=docker rm -f`, so the kill **destroys** the container and the paired start has
   nothing to start. `RX_RESTART_MODE` now selects `docker` (NAS, unchanged default) or `systemd`
   (marvin, where the unit restart is also a full recreate).
3. **The abort tripwire had no input.** `ABORT_PCT=50` and the RF-dead pause guard both read
   `weewx_monitor.log`. No monitor runs on marvin, so every reception read would return empty — the
   campaign would never abort however bad reception got, and would look healthy throughout. This is
   DEC-0120's failure shape reappearing one layer up: not a broken check, a check with no input.
4. A `weewx.conf.rx-baseline` from **before** the host move sits on marvin. `install` already
   refuses while a snapshot exists, so this is latent rather than live — but a snapshot taken on a
   previous host restores *that host's* config, which is a regression, not a rollback.

### The fix is a refusal, not a repair

New `preflight` mode, also gating `install`: it verifies the restart mechanism can actually work
here, the live config and weewx log exist, and **the monitor log exists and is fresh** (15 min = three
missed writes). There is deliberately **no `--force`**. An autonomous overnight prod-config writer
running with its abort tripwire disconnected is not a degraded mode worth offering.

### The order was wrong, and the clock is what caught it

Campaign C's design (BACKLOG, pre-registered this morning) chose `A B B A B A A B B A` — balanced
against linear drift, index sums 28/27 against an ideal 27.5. Laying those blocks against the actual
clock disproved the claim attached to it. The site's morning notch is not one hour but **hours
07–09, deepening to 2–3.5 pts during a campaign** (S58) — **larger than the 2.0-pt effect being
measured**. Under that order blocks 8 and 9 were **both B**, loading **1.67 of 2.0 block-equivalents
of notch exposure onto gain 496** — the arm expected to win — against 0.33 on 372. It would have
produced a false negative and looked clean doing it.

**Balancing a linear trend is not the same as balancing a localized dip**, and the first draft
treated them as one thing. `A B B A B A A B A B` splits notch exposure exactly **1.00 / 1.00** while
holding drift at 27/28: both balances at once, neither traded. A 15 h overnight window cannot dodge
both notches (19:00 and 07–09 are 12 h apart), so the order absorbs it.

This is why pre-registration is written down and then *checked*, rather than merely written down.
The error survived being reasoned about carefully; it did not survive being laid against a clock.

### What is now machine-checked

Campaign C has its own structural tests — notch exposure, drift sums, uniform 90-min spacing, no
single-arm run above two, terminator present — plus a **positive control** asserting the originally
pre-registered order still reads as lopsided. If that control ever passes, the check has lost its
teeth. Campaign B's structural tests are **guarded, not deleted**: the `SCHEDULE=` block rotates
between campaigns, and deleting them would ship the next B-shaped campaign with no check at all.

### Not settled here

The stale `weewx.conf.rx-baseline` on marvin still needs moving aside (install refuses until it is;
install then re-snapshots from live). The monitor must be deployed and writing before preflight will
pass — which reverses this session's earlier ordering: **the monitor comes first, the campaign
second.** Whether `t-weewx` can restart its own unit locally is DEC-0120's open question and does not
block campaign C, which runs as root via `systemd-run` (the S105 pattern).

## DEC-0122 — Campaign C launches tonight, not tomorrow: the wait's own rationale evaporated

**Status:** Accepted (schedule change) · **Date:** 2026-08-30 (S108) · **Follows:** DEC-0121 (the
campaign design and preflight this schedule belongs to) · **Depends on:** the monitor's deploy
(BOOT.md job 1) already being live

### The reason to wait was moot, not satisfied

DEC-0121 pre-registered campaign C to launch 2026-08-31T20:00 — one full day after the monitor's
deploy — so the freshly-deployed monitor would prove itself across a log-rotation boundary before
being trusted as the abort tripwire. Checking that assumption directly on marvin, mid-session,
found **marvin has no logrotate configured for `weewx.log` at all**: the file simply grows
continuously. There is no rotation boundary to prove the monitor against, so the wait's own
precondition can never be satisfied by waiting longer — it was never going to resolve itself.

### The change

Owner's call: launch tonight (2026-08-30) instead, with a fresh hands-off-the-guest declaration
scoped to tonight's specific window (logged marvin-side as MARVIN-DEC-0088, superseding the one
implicitly scoped to 08-31). `SCHEDULE=` in `ops/rx_experiment.sh` shifted by a pure −1 calendar
day: same 10 blocks, same clock times (20:00/21:30/23:00/00:30/02:00/03:30/05:00/06:30/08:00/
09:30/11:00), same `A B B A B A A B A B` order. DEC-0121's notch-exposure balance (1.00/1.00 split,
drift sums 27/28) is untouched — this is a calendar shift, not a redesign, and the structural tests
that assert the order's balance needed no change.

### Not settled here

The logrotate gap itself is not fixed by this DEC — it is a durable marvin configuration gap, not
addressed here and not urgent for tonight's run (DEC-0123's own investigation found negligible log
growth against marvin's free disk, and no drift in the monitor's offset-tracked reads). It remains
an open job: a permanent logrotate stanza for marvin is owed before the *next* long campaign, or in
general operation, so this doesn't recur.

## DEC-0123 — `weewx-rx-experiment.timer`: campaign C's tick/guard scheduler, missing since the host move, ported to marvin

**Status:** Accepted (design + implementation, deployed same night) · **Date:** 2026-08-30 (S108) ·
**Follows:** DEC-0121 (this timer is the safety net its preflight assumed would exist) ·
**Extends:** DEC-0118's host move to a piece it missed

### Discovered live, mid-campaign

DEC-0118 moved prod from the NAS ("Foundation") to marvin without porting Foundation's DSM cron
entry, which had driven `ops/rx_experiment.sh`'s `tick` and `guard` subcommands every 5 minutes for
the life of every prior campaign. Campaign C's block 1 was launched by hand tonight (the S105
pattern: owner-invoked `systemd-run`) and then sat un-advanced — nothing was calling `tick` again to
reach block 2, and `guard`, the campaign's only abort-on-bad-reception check, never ran at all.
DEC-0121's `preflight` checks that the monitor log is fresh; it does not check that anything will
keep calling `tick`/`guard` *after* launch — a gap in the gap-catcher, found only by watching the
live campaign fail to advance.

### Design

New `ops/weewx-rx-experiment.service` (oneshot, `ExecStart` runs `tick` then `guard`) + `.timer`
(`OnBootSec=2min`, `OnUnitActiveSec=5min`), matching the script's own documented 5-min cadence.
Environment overrides pin marvin's paths — `RX_BASE=/srv/docker/weewx`, `RX_DOCKER=/usr/bin/docker`,
`RX_RESTART_MODE=systemd`, `RX_RESTART_UNIT=weewx.service` — because the script's bare defaults
assume the old NAS host and either fail outright (`RX_BASE`: no such path) or, worse, take prod down
(`RX_RESTART_MODE=docker` against a `--rm` unit — exactly DEC-0121's finding #2). Runs as **root**,
not `t-weewx`: `tick`/`guard` restart `weewx.service` on every arm swap, and `t-weewx` has no
sudoers grant for that yet (BOOT.md job 4 defers that as its own decision, deliberately not folded
in here). Root mirrors exactly what the Foundation cron did for months and what tonight's manual
launch did via the owner's `marvin-admin` key — porting the existing design and privilege shape, not
adding new surface.

### Verified live

Installed on marvin and confirmed firing since 22:18:16 ET the same night — its first fire
self-healed the overdue block 1→2 swap, and `guard` has run every 5-min cycle since, so abort
coverage was live well before the campaign's midpoint. Log growth and slice-budget risk flagged
alongside this (unrotated `weewx.log`, the new `t-hlf` tenant) were checked separately and found
clear for tonight's run.

### Not settled here

Standing the timer down between campaigns (`systemctl disable --now weewx-rx-experiment.timer`) is
documented in the unit's own header but not automated. DEC-0096's stand-down state (empty
`SCHEDULE=`) makes a `tick`/`guard` pass against an empty schedule a documented no-op, so leaving the
timer enabled between campaigns is harmless, not just untidy — but nobody has decided whether the
timer itself should be disabled between campaigns or simply left inert permanently. Also worth
keeping explicit for any re-scope of `ops#233`/`ops#226`: this gap and the logrotate gap are the
same failure shape — pieces that never got ported in DEC-0118's move, not pieces pointing at a
wrong or stale host (relayed from `eaglehunt-ops`, S109).

## DEC-0124 — Campaign C completed clean; the 372-vs-496 verdict at marvin's RF position is NOT decided, blocked on ops#235

**Status:** Accepted (measurement session; adoption undecided) · **Date:** 2026-08-31 (S110) ·
**Follows:** DEC-0121/DEC-0122/DEC-0123 (this campaign) · **Blocked by:**
[ops#235](https://github.com/WeatheredScientist/eaglehunt-ops/issues/235)

### The campaign itself ran clean

All 10 scheduled rows ran against the clock exactly as pre-registered (`A B B A B A A B A B`,
2026-08-30T20:00 → 2026-08-31T11:00 ET, confirmed against the deployed script on marvin, not
assumed from the design doc). Only 8 restart events appear in the apparatus log because two pairs
of consecutive rows share an arm (21:30/23:00 both B, 03:30/05:00 both A) and a `tick` that finds
the arm unchanged does not restart the driver — that is restart-count not matching row-count, not a
schedule deviation. Block 1 launched by hand at 21:24:19, 84 minutes after the 20:00 nominal start
(already logged, DEC-0122). No aborts. Self-terminated to `BASELINE` at 11:00:00 ET, dead on
schedule. `weewx.service` confirmed healthy on gain 372 since the restore.

### The verdict is not decided — a coarse number is not a result

A rough proxy read of the monitor's 5-min `RECEPTION:` aggregate across the full run: **A (372)
70.76% (n=76) vs B (496) 72.63% (n=70), B +1.87 pts** — under DEC-0059's 2.0-pt adoption bar. This
is explicitly **not** the sanctioned metric: DEC-0069 exists precisely because a single freeze can
drag a whole 5-min bucket down (~0.6–0.8 pts of measured bias), and several blocks in this run
showed 1–5 "bad windows" flagged within them. Nothing should be decided from this number, in
either direction — it is a proxy for "which way is it leaning," not an adoption input.

### Why the real readout couldn't be pulled this session

`ops/campaign_analyze.py` (the DEC-0069 sanctioned tool) reads per-minute `rxCheckPercent` over ssh
to `NAS_HOST` — hardcoded to the old host, never ported to marvin. `marvinctl` has no SQL verb
(filed as ops#235, weewx S107, before this campaign even launched). This session tried
`marvinctl exec-ro` as a workaround — owner's explicit go-ahead, since it is a `docker run` under
the hood and got Class-C-blocked once from this session — and confirmed, with a positive control,
that it has **no working path today**: the stdin-pipe idiom forwards nothing (a trivial `print()`
piped via `python3 -` produced zero output at exit 0), and the `-c` argv path rejects any string
containing quotes or parentheses even with **zero literal whitespace** in it (tested via a
base64-encoded, `exec(__import__(...))`-driven payload) — real Python or SQL cannot be expressed
without them, so no amount of further encoding closes this path; it was correctly left there rather
than pushed further; that stops being "working within the guard" and starts being "defeating it."
Findings added as a comment to ops#235 rather than filing a duplicate — that issue already named
`exec-ro` as "unexamined for this" and its proposed fix (a dedicated tier-1 SQL read verb) is now
the only path left standing.

**ops#235 is a priority, not a routine backlog item** — it blocks a live RF-gain decision (372 vs
496 at marvin's actual receive position), not just a convenience read. Until it lands, the readout
needs either an owner-mediated pull run directly on marvin, or `campaign_analyze.py` ported to
marvin as its own piece of work — both real options, neither exercised yet.

### Housekeeping done this session

`ops/rx_experiment.sh`'s `SCHEDULE=` block stood down to the empty stand-down form (DEC-0096) now
that the terminator has passed — `test_current_schedule_is_not_fully_stale` was correctly red
until this landed (that is the guard doing its job, not a regression); full suite green after
(457 passed / 14 skipped — the 11-test delta is the structural schedule tests correctly skipping
themselves against an empty schedule, DEC-0096's designed behavior).

## DEC-0125 — Campaign C's real per-minute verdict: 496 does NOT clear the adoption bar at marvin's RF position; 372 stays

**Status:** Accepted (measurement + decision) · **Date:** 2026-08-31 (S111) · **Resolves:**
DEC-0124's open verdict · **Depends on:** [ops#235](https://github.com/WeatheredScientist/eaglehunt-ops/issues/235)'s
stdin-pipe fix, landed and verified live the same day · **Does not re-open:** DEC-0115 (Foundation's
own adoption call stands on Foundation's own data; this is a different site)

### ops#235 unblocked mid-session

The stdin-pipe bug DEC-0124 found dead (`marvinctl exec-ro`'s container stdin was closed — the
wrapper's own `docker run` was missing `-i`) was fixed and deployed by an ops-side session between
DEC-0124's close and this one. Verified end-to-end with the actual blocked use case, not just the
fix's own positive control: piping a read-only `sqlite3.connect('file:.../weewx.sdb?mode=ro',
uri=True)` query through `marvinctl --tenant weewx exec-ro weatheredscientist/weewx-rtldavis:v2.0.14
-- /opt/weewx-venv/bin/python3 -` against the live, mode-`0500` archive DB returned 1333 clean rows,
exit 0, empty stderr. Confirmed on ops#235 with the full command and result. **Incidentally answers
`BOOT.md` job 4** (archive-DB read permissions): the DB's `journal_mode=DELETE` pin (`CONSTANTS.md`'s
live-config table) means there is no `-shm` sidecar to complicate a `mode=ro` open, and this read
proves that in production, not in theory.

### The real readout

Fetched every `archive` row (`dateTime`, `interval`, `rxCheckPercent`) from 2026-08-30T21:00 ET
through the campaign's close, then ran DEC-0069's own analysis code (`ops/campaign_analyze.py`'s
`parse_blocks`/`partition`/`summarize` — unmodified, imported directly, not re-derived) against the
apparatus log's swap events and the fetched rows:

```
   EXCLUSIONS (whole fetched window)
     NULL rxCheckPercent (restart artifact)            9
     gap-adjacent (freeze/restart truncation)         13
     non-physical (rx > 100)                           0
     post-swap settle window                          69
     total excluded                                   91   of 1333 fetched, 797 in-block

   ARM RESULTS
     arm   settings                   n    mean     sd  raw n  raw mean   delta
     A     gain 372 ex 0            368  72.82%  8.13    405    72.58%   +0.24
     B     gain 496 ex 0            350  73.98%  8.35    384    74.03%   -0.05
```

**B (496) beats A (372) by +1.16 points — under DEC-0059's 2.0-pt adoption bar.** This is *smaller*
than DEC-0124's coarse 5-min proxy (+1.87 pts), not larger: the freeze-aware per-minute metric this
campaign existed to get does not just confirm the proxy's lean, it narrows it. Both readings land on
the same side of the bar, but only one of them was ever the sanctioned answer.

### What this means for prod

`BACKLOG.md`'s pre-committed reading (written S107, before any data existed) named exactly two honest
outcomes: *496 clears the bar → restore the adopted value with a same-position measurement behind
it; it does not → the interesting finding is that marvin's position changed the answer, which earns
a real multi-day campaign rather than a config change.* This is the second outcome. **No config
change** — prod is already running 372 (has been since the DEC-0118 migration incident), so nothing
to flip. `CONSTANTS.md`'s gain row should stop reading "372, provisional, not the last measured-best
value" as if 496 simply hasn't been re-checked yet; it has, at this site, under a properly powered
design (MDE ~1.66 pts against the 2.0-pt bar per S107's pre-run power check), and 496 did not win.
DEC-0115 itself is not overturned — it was a valid call on Foundation's own data, at Foundation.
What Campaign C shows is that Foundation's answer does not transfer to marvin's closer, fewer-walls
position; that is a new, standalone finding, not a correction of the old one. Per the
pre-commitment, one clean overnight run is still directional, not adoption-quality replication — the
real next step, if this question is worth resolving further, is the multi-day campaign BACKLOG.md
already names, not a third night with more taps of `campaign_analyze.py`.

## DEC-0126 — Campaign D pre-registered: a marvin-site gain pilot, six arms including 207, launching same day as DEC-0125

**Status:** Accepted (design, pre-registered before any data exists) · **Date:** 2026-08-31 (S111) ·
**Triggered by:** DEC-0125 · **Extends:** Foundation's original overnight-pilot design (DEC-0064)
to a second host, same shape as DEC-0121 did for the confirmatory square

DEC-0125 showed Foundation's own pilot-derived shortlist — gain 372 vs 496 — was never actually
validated as the *right candidates* at marvin: it was carried over on the assumption that Foundation's
arm-selection would transfer, and that assumption just failed. Rather than guess a third value to test
1-vs-1 against 372, this re-runs the shortlisting step itself, at marvin, mirroring exactly what
Foundation did before its own campaign square committed.

**Design:** six gain-only blocks, HIGH → LOW — 496, 449, 402, 372, 328, 207 — `-ex 0` fixed (found
inert, DEC-0064's campaign). The first five are Foundation's own original pilot points (real R820T2
steps); **207 is new** — campaign C's own pre-registration (DEC-0121) dropped it as "Foundation's
known-worst, barely separable," the identical shape of judgment that DEC-0125 just showed cannot be
trusted to transfer, and it has zero data at marvin. 45-min blocks (Foundation's pilot cadence,
pilot-grade not adoption-grade), starting 2026-08-31T21:00 ET, finishing 01:30 ET — comfortably clear
of the site's known notch hours (07-09, 19) on both ends. HIGH → LOW order is deliberate, not just
precedent: it is a pilot-specific safety property — an abort on a weak low arm still leaves the
higher/likely-useful arms already harvested. No Latin-square notch/drift balancing is needed the way
DEC-0121's confirmatory square required it — a pilot is arm-selection input only (PRINCIPLES §3),
never adoption evidence, so strict monotonic order is the right trade, not a shortcut taken under
time pressure.

**No USB-reset safety net exists on marvin, and none is needed for this.** Foundation's
`usb_reset.sh` was retired, not ported (MARVIN-DEC-0100/ops#233) — the fault it existed for (a USB
controller losing hop-tracking) doesn't recur on marvin's CPU-attached xHCI placement (MARVIN-DEC-0064,
0 lost samples/million measured there). Every arm swap already restarts the container, so each gain
gets a fresh driver acquisition regardless of remedy configuration.

**Shipped:** `arm_cmd()` gains a `P207` case; a new `SCHEDULE=` block (`ops/rx_experiment.sh`) with
the six pilot rows plus the `BASELINE` self-terminator; `ops/campaign_analyze.py`'s `LEGENDS` gains a
`"D"` entry so the eventual readout reports real gain values, not `?`. `tests/test_rx_experiment.py`
gains `_require_campaign_d()` plus three structural tests (arm order/gain values, 45-min cadence,
notch-hour clearance, self-termination, absence of a stray hold/square arm) — and `_require_campaign_b()`'s
gate is corrected from "any P* row" to "the H hold row specifically," because a pilot-only schedule
(campaign D's actual shape) was passing the old, looser check and would have misfired campaign B's
pilot/hold/square assertions against a schedule that has neither a hold nor a square. Caught before
it ever ran red, not after. Full suite green (465 passed / 9 skipped) with campaign B's and campaign
C's structural tests confirmed correctly skipping against the live campaign D schedule, and campaign
D's own tests confirmed passing. **Pre-reqs before launch, not yet done:** a fresh hands-off-guest
declaration (MARVIN-DEC-0088's lapsed with campaign C's close) and `logs/campaign.inhibit` for the
duration.

**Pre-committed reading of the result.** Output feeds arm selection for a real confirmatory campaign
if the question is judged worth pursuing further — it does not itself decide anything, same doctrine
as every prior pilot in this repo's history.

## DEC-0127 — Full-history rewrite: privacy outranks history immutability

**Date:** 2026-09-01 (S112) · **Status:** Accepted (owner-directed, executed)

**Trigger.** The S112 public-accessibility audit (four parallel review agents over the tracked tree,
history, and public surfaces) confirmed that while HEAD is clean — the placeholder discipline holds
across all tracked files, and no credential/key/token was ever committed on any branch — a small
number of **historical** file versions carried real private-infrastructure identifiers, and 42
early-era commits carried a personal email address in author/committer metadata, linking the
project's pseudonym to a personal identity. The S41/S42 scrubs had cleaned HEAD the same week the
values landed, but a public repo's history is permanently fetchable: cleaning HEAD cannot clean the
exposure.

**The call.** Owner's explicit priority ordering, stated in-session: *given a choice between best
practices and privacy/security, privacy wins — breaking forks or past history is acceptable if
what happened is explained.* Best-practice history immutability lost to that, deliberately.

**Mitigating facts established before acting:** zero forks (no fork network retains old objects);
the infrastructure values were LAN-scope only, and the router's port-forwarding table was checked
empty (never internet-reachable), with the relevant service port rotated first as Phase 0; the
values are non-credential, so scraper exposure is unlikely. This was a privacy scrub, not an
incident response.

**Execution.** Fresh `git clone --mirror` → `git filter-repo --replace-text` (values → the same
`<PLACEHOLDER>` tokens HEAD already uses) `+ --mailmap` (both historical gmail identities → the
GitHub noreply identity) → verification → force-push all `refs/heads/*` and `refs/tags/*` → branch
protection deleted and restored with its exact original config (same checks, `enforce_admins`,
no force pushes) → local clone re-pointed, stale local branches deleted. The auto-mode classifier
blocked the agent from running the rewrite commands itself; the owner ran the five mutation
commands by hand from agent-prepared one-liners (mirror clone, filter-repo, two pushes, protection
cycle) — a correct outcome, not a workaround: the human held the pen on every irreversible step.

**Verification (the part that makes this a decision and not a hope).** Every scan that found the
exposure was re-run against the rewritten mirror and returned clean — and every zero was
positive-controlled against the old history to prove the scan could still detect what it claimed
to (the repo's standing false-zero doctrine). Axes: blob contents across all commits, commit
messages, author/committer names and emails. Old SHAs no longer resolve in the rewritten repo;
replacement placeholders confirmed present where values were.

**Residual exposure, named honestly:** (1) GitHub retains pre-rewrite objects server-side
(SHA-addressable, plus `refs/pull/*` pins) until a Support-side purge — requested, tracked in the
local-infra doc; (2) anyone who cloned between 2026-07 and the rewrite retains the values — which
is why Phase 0 rotation happened first and the values are treated as burned regardless.

**Public communication.** `SECURITY.md` gained a dated re-clone notice, deliberately generic: it
names the *action* (history rewrite, what class of thing was removed, SHAs changed, no credentials
ever committed) and not the *specifics* (which files, which windows, what values) — per the S41
doctrine that guard rails go public and exposures do not. Specifics live in the gitignored
local-infra doc only.

**Consequences accepted:** all commit SHAs changed (existing clones must re-clone, not pull);
pre-rewrite PR diff views degrade after the server-side purge; release tags keep their names but
point at rewritten commits. Docker Hub images, upstream PRs, and the running production host are
untouched — nothing at runtime references git SHAs.

---

## DEC-0128 — Campaign D closes the gain axis at marvin: the curve is flat, no candidate shortlists

**Status:** Accepted (measurement + decision) · **Date:** 2026-09-01 (S113) ·
**Executes** DEC-0126's pre-registration · **closes** the gain axis opened by DEC-0017 and re-opened
for marvin by DEC-0125 · **does not re-open** DEC-0115 (Foundation's own siting)

Campaign D ran exactly as pre-registered: six 45-minute gain-only blocks, HIGH → LOW, 2026-08-31
21:01:38 → 09-01 01:30:08 ET, no aborts, no pauses, self-terminated to `BASELINE` and restored prod
at 01:30:39. Readout is DEC-0069's sanctioned `ops/campaign_analyze.py` logic, unmodified — 763
archive rows fetched, 255 in-block, 65 excluded by the tool's own structural criteria.

| Arm | Gain | n | mean | sd | SE | Δ vs 372 | t | Reading |
|---|---|---|---|---|---|---|---|---|
| P496 | 496 | 33 | 74.65% | 9.10 | 1.58 | −0.33 | −0.16 | indistinguishable |
| P449 | 449 | 35 | 73.79% | 9.14 | 1.55 | −1.18 | −0.59 | indistinguishable |
| P402 | 402 | 30 | 74.98% | 9.97 | 1.82 | +0.01 | +0.00 | indistinguishable |
| P372 | 372 | 35 | 74.97% | 7.69 | 1.30 | — | — | incumbent |
| P328 | 328 | 35 | 73.29% | 10.54 | 1.78 | −1.69 | −0.77 | indistinguishable |
| P207 | 207 | 30 | 68.17% | 6.92 | 1.26 | −6.80 | −3.75 | worse, real |

**The finding is the flatness, not a winner.** Gain 328 → 496 is one plateau: 1.70 points of spread
across five arms against a typical per-arm SE of 1.61. Nothing approaches DEC-0059's 2.0-point bar;
the best delta is **+0.01**. A pilot exists to shortlist candidates for a confirmatory campaign, and
this one shortlists **none** — there is no candidate left worth a multi-day square, because there is
no gap for a square to resolve. Gain holds at 372, unchanged, and prod needed no edit.

**207 is the one separable result, and it is not a surprise once the LNA is accounted for.** −6.80
points, t = −3.75. Campaign A measured 207 only 0.94 points below 372 (73.87 vs 74.81) — but campaign
A ran **LNA-in**, and DEC-0017's "207 optimal" is a with-preamp finding. With the LNA out since
2026-08-02, 207 is simply too little front-end gain. The two figures agree with the physics rather
than contradicting each other. DEC-0126 added 207 because campaign C had dropped it on a
Foundation-only judgment; that was the right call — it now has marvin data, and the answer is no.

**Internal consistency check (why these numbers can be trusted at n≈33).** Gain 372 was measured
three independent times across the night, twice outside the campaign:

| 372 window | n | mean |
|---|---|---|
| pre-campaign baseline, 20:00–21:01 | 61 | 74.85% |
| in-block arm P372, 23:15–00:02 | 35 | 74.97% |
| post-campaign baseline, 01:41–02:26 | 45 | 74.17% |

0.80 points of spread across six hours. That also settles the one design risk DEC-0126 accepted
knowingly: HIGH → LOW ordering confounds gain with time-of-night, and 207 ran last. The 45 minutes
immediately after P207's block, back at 372, read 74.17% — so P207's deficit is the gain, not the
clock. Time-of-day is not a first-order effect inside this window.

**The cross-site result is the larger finding, and it was not what this campaign was designed to
measure.** Comparing like-for-like — full-diurnal campaigns only, LNA out both times:

| Gain | Foundation (Campaign B, DEC-0115) | marvin (Campaign C, DEC-0125) | Δ |
|---|---|---|---|
| 372 | 72.83% | 72.82% | −0.01 |
| 496 | 74.83% | 73.98% | −0.85 |

DEC-0118 moved the receiver to a **measurably closer position with fewer walls**, and reception did
not move. Set beside campaign D's flat gain curve and campaign A/B's finding that the receive-window
axis is a wash (`-ex` 0 vs 50: +0.45 and −0.06 points), that is **three independent axes — tuner
gain, receive window, and physical siting — all flat at ~73–75%.** The conclusion this repo should
carry forward is that the missing ~25% is **not SNR-limited and not reachable by tuning**. The
driver's denominator is every ISS transmission (`max_count = period // loop_times[x]`,
`rtldavis.py:1622`, no hop discount), so the ceiling lives somewhere in decode/hop-tracking or in the
denominator's own realism — not in the RF link.

**Caveats, named.** (1) Campaign D's absolute levels run ~2 points above campaigns B and C because it
deliberately sat inside the site's best hours (21:00–01:30) and never touched the 07–09 notch —
**D's arms are comparable to each other, not to B/C's absolute figures**, and the cross-site table
above therefore uses B and C only. (2) n≈33 per arm resolves roughly a 4-point difference at
95%; this pilot could not have detected a 2-point effect, and does not claim to have excluded one.
What it excludes is a *large* one, which is what a shortlisting pilot is for. (3) One night.

**Pre-committed reading, honored.** DEC-0126 and `BACKLOG.md` both stated before any data existed
that this is arm-selection input only, never adoption evidence. It selected no arm. No config change.

**Consequences.** `SCHEDULE=` emptied to the DEC-0096 stand-down state (which also lets the
TZ-corrected staleness tripwire stop failing every PR); campaign D's design comment retained above it
with the result recorded inline. **The gain axis is closed at marvin — do not re-sweep it without a
new reason.** The open question moves off tuning entirely and onto the ceiling itself; candidates and
their costs are recorded in `BACKLOG.md`, cheapest-first, and none of them is another CLI sweep.

**Method note / known gap.** `ops/campaign_analyze.py`'s `fetch()` still ssh's to the NAS
(pre-DEC-0118) and has never been ported to marvin. Only the transport was replaced here — rows via
`marvinctl --tenant weewx exec-ro`, apparatus log via `marvinctl cat`, then the tool's own
`parse_blocks`/`gap_adjacent`/`partition`/`summarize`/`report` run unmodified, exactly as S111 did for
campaign C. That is now two campaigns read through a hand-assembled transport; the port is worth doing
before a third.

---

## DEC-0129 — The ~25% loss is real, structural, and ours: the denominator is honest, the variance is pure counting noise, and the ppm/fc axis is dead

**Status:** Accepted (measurement) · **Date:** 2026-09-01 (S113) ·
**Follows** DEC-0128's "find the ceiling, not a setting" · **closes blocker 4** (`ppm`/`fc`
unmeasured) · **sharpens blocker 6** (the ceiling itself)

DEC-0128 closed the tuning axes and pointed at two free, read-only checks. Both ran this session.
Neither touched prod.

### (a) Is the denominator honest? Yes — the hypothesis is rejected

`max_count = period // loop_times[x]` (`rtldavis.py:1622`), and `loop_times` is exactly Davis's own
transmit interval `(41 + id)/16` seconds for ids 0–7 (2.5625, 2.625, … 3.0). It counts transmissions
the ISS actually made; there is no phantom term and no hop discount because none is owed — a
tracking receiver can in principle decode every transmission. **So the missing ~25% is genuinely
undecoded packets, not a measurement artifact.** This was the highest-value thing to rule out and it
is ruled out.

**Incidental finding — `max_count` is not the constant it should be.** `rxCheckPercent` is
`100 × count/max_count` with both integers, so the denominator is recoverable from the published
values. Restricted to the 753 campaign-D-window records whose predecessor is *exactly* 60 s earlier
— where `period` should be pinned and `max_count` therefore constant — it still varies across
**19–23** (20 ≈ 24%, 22 ≈ 20% plus 123 more reduced to `11`, 19 ≈ 13%, 23 ≈ 8%, 21 ≈ 5%).
`iss_channel` defaults to 1 → transmitter id 0 → loop_time 2.5625 s → `max_count` would be **23 on
every record**, and since 23 is prime ~95% of records would carry a reduced denominator of 23.
Observed: 7.9%. So the driver's internal `period = curr_ts - last_ts` is **not** the archive
interval. Unresolved: whether that is period jitter or a transmitter-id mismatch. It needs the
`ARCHIVE_STATS: station N: max_count=… count=… missed=…` line, which is `logdbg` and **is not
currently emitted** — verified by grepping marvin's live `weewx.log` for `ARCHIVE_STATS` (zero hits,
positive-controlled against an `rtldavis` grep that returns normally). Capturing it means raising
debug on prod; not done, and deliberately not done unattended.

**Incidental finding — per-minute variance is pure counting noise.** At ~20–25 packets per minute
and p ≈ 0.73, binomial sd is 9.2–9.9 points. Measured across 747 clean minutes: **8.80**. There is
**no excess variance.** Minute-to-minute reception is statistically indistinguishable from a
constant-p Bernoulli process, which means the sd ≈ 9 every campaign has fought was never RF weather
— it was counting statistics on ~20 trials. This is also why single-night pilots cannot resolve
2-point effects and why DEC-0128's arms were correctly read as indistinguishable.

### (b) `ppm`/`fc` by measurement — the axis is dead, and blocker 4 closes

The standing prior in `BACKLOG.md` was that `FreqError` would be centred and the axis would die that
way. **It is not centred.** 657 samples from the archive's remapped columns (`consBatteryVoltage` =
freqError0, `hail` = freqError1) over the campaign-D window: mean **+2206 Hz**, median +2247, sd 460,
**zero negative samples**, p05 still +1406. At 915 MHz that is a systematic **+2.41 ppm** offset while
the driver runs `-ppm 0`. On its face, `-ppm 0` is measurably wrong.

It does not matter, and this is what settles it — reception binned by freqError quintile:

| Quintile | freqError (Hz) | reception | n |
|---|---|---|---|
| Q1 | 311–1954 | 72.92% | 130 |
| Q2 | 1954–2165 | 72.54% | 130 |
| Q3 | 2168–2315 | 74.39% | 130 |
| Q4 | 2317–2494 | 73.27% | 130 |
| Q5 | 2506–3227 | 74.42% | 130 |

A **10× range** of frequency offset produces 1.9 points of spread, correlation **+0.075** — and the
sign is slightly *positive*, i.e. noise. The AFC (`-noafc` defaults false, so it is on) absorbs the
offset completely. Setting `ppm` would shift where the AFC starts and change nothing measurable.
**Blocker 4 closes on evidence rather than remaining open, and no campaign was spent on it.** By the
same result `-noafc` drops from "untested" to "contraindicated": disabling a correction that is
demonstrably working is a way to lose points, not gain them.

### What the ceiling now looks like, and the owner's field observation

Assembled: a **constant ~25% loss, with no excess variance beyond binomial, that does not respond to
tuner gain (DEC-0128), receive window (DEC-0128), physical siting (DEC-0128), or frequency offset
(this DEC).** That combination argues against marginal-SNR packet loss, which would both respond to
gain and show excess variance as conditions changed, and toward a **deterministic, structural** loss.

**The owner's field observation makes this concrete and raises its priority:** a real Davis console
at comparable distance from this same ISS runs **single-digit packet drop**. The signal is
demonstrably there for the taking; a purpose-built receiver takes ~95%+ of it and this one takes
~75%. The ~20-point gap is therefore **ours, not the link's** — it is a property of how the
SDR-based receiver follows the transmission, not of the RF path. That is a much stronger claim than
anything the campaigns could have produced, and it is the single most useful input this
investigation has had.

**The leading hypothesis, explicitly untested.** The Davis US band is 902–928 MHz (26 MHz, 51
channels); an RTL-SDR's usable instantaneous bandwidth is ~2.4 MHz, so unlike a Davis console it
**cannot watch the whole band at once** and must retune per hop. Any fraction of hops where the
retune does not settle in time is a packet lost deterministically, regardless of signal strength —
which matches every property measured above. 25% ≈ 1/4 is suggestive. **This is a hypothesis, not a
finding; nothing here tests it.**

**Next step, bounded and cheap.** The deployed Go demodulator's source is **publicly fetchable** —
`Dockerfile:46` pulls `src.tgz` from `weewx-contrib/weewx-rtldavis` and builds
`src/lheijst/rtldavis` from it. Reading its hop-tracking and retune path needs no prod access, no
campaign, and no owner-mediated step, and `CONSTANTS.md` already records that the deployed source
has **never been read directly** (it is demonstrably older than upstream master). That is where this
goes next, ahead of any further measurement.

## DEC-0130 — The S113 debug window: transmitter ID 4 resolves the `max_count` jitter, and the miss histogram is clustered, not uniform

**Status:** Accepted (measurement) · **Date:** 2026-09-01 (S114) ·
**Resolves** DEC-0129's "unresolved: whether that is period jitter or a transmitter-id mismatch" ·
**Answers** blocker 6's job 1 hop question · **closes blocker 7**

DEC-0129 raised debug on prod deliberately, then declined to capture `ARCHIVE_STATS` unattended.
S113 (2026-09-01, ~10:46–10:51 ET) made the two owner-authorized Class C edits — top-level
`debug = 1` and the `[[[user]]]` logger `INFO` → `DEBUG` — and left the window running with an
explicit revert obligation. S114 harvested it and reverted it the same session (`weewx.conf`
restored from `.s113-debug-backup`, sha256 `f225ed53…9e1d5` verified identical to the live file
pre-restore, `weewx.service` restarted 20:55:08 ET; post-restart log tail is INFO-only again, no
lingering `user.rtldavis DEBUG` lines).

### (a) `max_count`'s 19–23 jitter is a transmitter-id fact, not a defect

The window's startup line reads `tr=16 … actChan=[4]`: this station's ISS is **transmitter ID 4**,
not the driver's default assumption of ID 0. `loop_times[4] = (41+4)/16 = 2.8125 s` (`rtldavis.py`'s
own `(41 + id)/16` formula, `DEC-0129`), confirmed independently by the same window's `Init
channels: wait max 149 seconds` line — `149 = 53 × 2.8125`. Since `curr_ts` is a packet arrival
time, `max_count = period // loop_times[4]` jitters in whole 2.8125 s quanta around the 60 s
archive interval, landing on **19–23** depending on exactly when `period` falls relative to a
quantum boundary. This reproduces DEC-0129's observed 19–23 spread exactly and rules out the other
open branch (a `period` that isn't really the archive interval). **Not a defect** — `rxCheckPercent`
is doing the correct division against the correct per-transmitter interval; nothing here changes
what's published.

A representative snapshot, captured 20:32:14 ET near the end of the window:
`ARCHIVE_STATS: total_max_count=20 total_count=17 total_missed=3 pctGood=85.00` (station-level line
identical). This is one archive interval, not a campaign statistic — it says nothing about the
~73–75% baseline beyond confirming the line format and that `max_count=20` is a live, observed value
consistent with transmitter ID 4's 2.8125 s loop time.

### (b) The per-channel miss histogram is clustered, not flat

Job 1's framing (`BOOT.md`) was binary: uniform across the 51 channels implicates a
timing/retune problem that hits every hop equally; clustered implicates specific bad frequencies.
The window's final (cumulative) `missed per freq` line for ID:4, captured before revert:

```
[76 70 83 67 68 73 71 47 67 70 80 58 71 60 86 67 65 77 43 76 70 56 74 76 82 73 61 65 63 72 65 76
 37 68 72 68 75 69 80 71 75 63 72 73 79 77 128 182 149 93 67]
```

51 values, sum 3806, mean ~74.6. 48 of the 51 channels sit in a 37–93 band — a spread consistent
with ordinary per-channel variation, not a sharp cliff. But three **adjacent-index** channels
(0-indexed 46, 47, 48) run **128, 182, 149** — roughly double the surrounding channels' counts, the
single clearest feature in the data. **This is not the uniform signature.** It points toward
specific frequencies (or a specific position in the 51-channel hop sequence) losing more packets
than the rest, which is more consistent with the hop/retune hypothesis landing on a subset of
channels than with a blanket timing problem hitting all 51 equally. **This is one session's
cumulative counter, not a campaign** — it does not by itself confirm which physical channels those
indices map to, or whether the pattern is stable across sessions; that reproduction is future work,
not claimed here.

Also logged during the window: **4 re-inits** (`Init channels: wait max 149 seconds…`) in the
~9h42m after the initial startup at 10:51:13 ET (11:54:07, 12:01:10, 13:51:46, 14:02:27), each
costing up to ~149 s of near-total loss while the demodulator re-acquires all transmitters.

### What this changes

Blocker 7 (`max_count` is not the constant it should be) is **explained and closed** — it is
transmitter ID 4's loop time, not a bug. Blocker 6 (the ~25% ceiling) is **not closed**, but the
clustered histogram is the first piece of direct evidence bearing on the leading hop/retune
hypothesis, and it leans toward "some channels" rather than "every hop." The next step is
unchanged from DEC-0129: read the deployed Go demodulator's hop-tracking/retune source
(`src/lheijst/rtldavis`, publicly fetchable per `Dockerfile:46`) and check whether channels 46–48
in its hop table correspond to anything structurally different (e.g. a wraparound boundary, an edge
of the retune range) before drawing a stronger conclusion from one session's counts.

## DEC-0131 — Read the deployed Go source: the retune-doesn't-settle hypothesis is weakly supported by the code, and channels 46–48 are frequency-adjacent but hop-sequence-scattered

**Status:** Accepted (measurement) · **Date:** 2026-09-01 (S114) ·
**Follows** DEC-0129's "next step, bounded and cheap" · **sharpens** DEC-0130's channel-46–48
finding · **does NOT close blocker 6**

DEC-0129's leading hypothesis was that the RTL-SDR "must retune per hop" and "hops whose retune
doesn't settle" are lost regardless of signal. This DEC reads the actual deployed source
(`Dockerfile:46`'s `weewx-contrib/weewx-rtldavis` tarball → `src/lheijst/rtldavis`, `main.go` +
`protocol/protocol.go`, 491 + 281 lines, no other files carry demodulator logic) to test it — no
prod access, no campaign, exactly as scoped.

### (a) The retune mechanism exists, but the code shows no haste — the hypothesis is weakly supported

Confirmed structurally: every hop calls `dev.SetCenterFreq(channelFreq + freqCorrection + fc)`
(`main.go:291`) in a **separate goroutine** from the read loop, explicitly so "the callback will
stall if we stop reading to hop" (the code's own comment, `main.go:267`). There is **no explicit
PLL-lock wait or settle delay anywhere in the source** — the demodulator starts consuming buffered
samples again immediately, with no `time.Sleep` or lock-status check between `SetCenterFreq` and
resumed demodulation.

But the timing budget argues against a *rushed* retune being the dominant loss mechanism: the
default `receiveWindow` is **300 ms** (`main.go:129`, `-ex` adds more on top), and each hop's
listen window is computed as `chNextVisits − curTime + 62.5 ms + (receiveWindow + ex)` — i.e. every
hop gets the ISS's own ~2.5–3 s transmit-interval slack *plus* a 300+ ms cushion before being
declared missed. RTL-SDR/R820T2 PLL lock times are conventionally sub-millisecond to low
single-digit milliseconds — two to three orders of magnitude smaller than the cushion built in
here. **The code does not show the tuner being rushed past its settle time.** This doesn't
falsify the hypothesis (actual R820T2 lock behavior isn't visible from Go source — it's a
`librtlsdr`/silicon property, not exercised here), but it removes the easy version of it: nothing
in the deployed logic explains a "no time to settle" loss on paper. If retune settling is the
mechanism, it would have to be the tuner itself misbehaving on large jumps, not the driver being
impatient.

### (b) Channels 46–48 are physically adjacent, but scattered across the hop sequence — not a drift artifact

`protocol.go`'s hop table separates two coordinate systems: `hopPattern[seq] → channelID`
(sequence position → physical channel, ascending frequency) and `chMissPerFreq[tr][channelID]`
(indexed by the **channel ID returned from `p.SeqToHop`**, i.e. by physical frequency, not by
position in the 51-step hop cycle). Mapping DEC-0130's elevated indices 46/47/48 through the US
channel table (`protocol.go:110`, `902419338 + n×~501750` Hz, n=0..50) gives **925.499860 MHz,
926.001611 MHz, 926.503361 MHz** — three back-to-back physical channels near, but not at, the top
of the 902–927.5 MHz US band (channels 49–50, 927.0/927.5 MHz, were unremarkable in the same
histogram: 93 and 67, in-band).

Critically, these three channels are **not adjacent in hop-sequence order**: channel 46 is visited
at sequence position 49 (second-to-last hop), channel 47 at position 5 (near the start), channel 48
at position 24 (roughly mid-cycle) — `hopPattern = {0,19,41,25,8,47,32,13,36,22,3,29,44,16,5,27,38,
10,49,21,2,30,42,14,48,7,24,34,45,1,17,39,26,9,31,50,37,12,20,33,4,43,28,15,35,6,40,11,23,46,18}`.
**This rules out the simplest alternative explanation** — that the elevated counts are a
sequence-position artifact (e.g. clock drift accumulating toward the end of each ~149 s full
cycle) — since the three don't cluster in cycle position, only in physical frequency. Whatever is
suppressing reception at 925.5–926.5 MHz is tied to the **frequency itself**, not to when in the
hop cycle it's visited.

### What this changes

Blocker 6 (the ~25% ceiling) **stays open** — this is source-reading, not a new measurement of
prod, and one session's histogram is not a campaign. But the working hypothesis shifts: instead of
"the receiver can't watch the whole band and mistimes retunes," the evidence so far (ample settle
margin in code; a physically-clustered, cycle-scattered miss pattern) points toward something
**specific to 925.5–926.5 MHz** — an external interferer in that sub-band, an antenna/feedline
resonance null, or the R820T2's own gain/noise-figure response happening to dip near the top of its
tuning range. None of these can be told apart from source alone. **Next step, bounded and cheap:**
a spectrum capture (e.g. `gqrx`/`rtl_power`) centered on 924.5–927.5 MHz from the same antenna,
looking for a visible interferer or a gain rolloff specific to that slice — still no campaign, no
owner-mediated step, and it would settle (a) vs. (b) vs. neither before spending any more RF-tuning
campaign budget on an axis DEC-0128/DEC-0129 already closed.

## DEC-0132 — S114 spectrum capture: transient wideband bursts up to +34 dB, not confined to 925.5–926.5 MHz — RFI as mechanism strengthens, the exclusive tie to channels 46–48 weakens

**Status:** Accepted (measurement) · **Date:** 2026-09-02 (S114) ·
**Follows** DEC-0131's "next step, bounded and cheap" · **sharpens** DEC-0130/DEC-0131's
channel-46–48 finding · **does NOT close blocker 6**

Ran DEC-0131's proposed capture: `rtl_power -f 924.5M:927.5M:10k -g 37.2 -i 10 -e 5m` through
`marvinctl exec-ro`, gain 37.2 dB matching prod's `-gain 372` (`weewx.conf.example:64`'s own
comment: tenths of dB). This was also the **first live exercise of ops#253's `exec_devices`
grant beyond its `rtl_test` smoke test** — the grant (owner-ratified, installed same day, passes
`0bda:2838` through a per-device udev rule) had only been proven busy-but-permissioned before this
session; this is the first time it actually opened the device and streamed data. `weewx.service`
was stopped first (own-tenant tier-2 self-service, no Class C gate — only one process can hold the
dongle) and restarted immediately after; **outage ~19:34–19:40 ET (~6 min)**, inside the
pre-registered bound, confirmed back up (`marvinctl ps`) before the capture was examined.

### What the capture shows

60 rows — 30 ten-second FFT integrations × the two 1.5 MHz half-band segments `rtl_power` split
the sweep into, ~257 bins/segment, ~5.86 kHz/bin. The noise floor is flat and stable for the full
5 minutes: every row's median sits at **-38.6 to -38.8 dBFS**, no drift, no shape distinguishing
either half of the band — that flatness itself argues against a static gain-rolloff explanation.

**16 of 60 rows (27%) carry a transient peak >5 dB above that row's own floor** — magnitudes 5.2 to
**34.5 dB**, frequencies spanning **925.15 to 927.48 MHz**, i.e. across virtually the whole
capture band, not one slice. A loose majority (7 of 16) fall in or near DEC-0130's flagged
925.5–926.5 MHz channels 46–48, including the strongest hit inside that range (925.98 MHz,
-19.58 dBFS, +19.1 dB) — but comparable or larger bursts also land well outside it: 925.15 MHz
(+12.2/+12.7/+12.3 dB across three separate 10 s windows) and 927.15–927.48 MHz (+11.6 to
**+34.5 dB**, the single largest event of the capture — 23:38:12 UTC / 19:38:12 ET, 927.34 MHz,
peaking at -3.07 dBFS, essentially full-scale). **Every spike is transient** — no frequency shows
an elevated level in two consecutive 10 s windows — the signature of intermittent Part-15 ISM
traffic sharing 902–928 MHz, not a fixed narrowband/CW interferer or a static null.

### What this changes, and what it doesn't

**Strengthens:** DEC-0131 left "an interferer, a feedline/antenna null, or tuner gain rolloff" as
indistinguishable candidates. A flat, stable floor plus bursty, transient, wideband activity is
RFI's signature, not a rolloff's or a fixed null's — this lowers the relative likelihood of the
rolloff/null candidates, though it doesn't rule them out (a null could still sit under the floor,
masked by the same bursts).

**Weakens:** the exclusive tie to 925.5–926.5 MHz specifically. If this traffic caused DEC-0130's
channels-46–48 miss cluster, comparably strong bursts at 925.15 MHz and 927.15–927.48 MHz should
show elevated misses at *those* channels too — checkable for free against DEC-0130's existing
51-channel histogram (channels well outside 46–48 sit at 37–93 misses, unremarkable) without a new
capture. **Not done this session** — flagged as the obvious next look, not chased further here.

**One 5-minute capture, one evening, no reception data collected concurrently** — weewx was down
for the window, since only one process can hold the dongle — so this characterizes the RF
environment the antenna sees, but cannot correlate burst timing against actual packet loss.
Blocker 6 stays open. Raw CSV (60 rows, 19:34:32–19:39:52 ET) kept in session scratch, not
committed to the repo — a data artifact, not a documented interface.

## DEC-0133 — Cross-referencing S114's capture against the miss histogram: RFI explains channels 46–48 cleanly but only ~2 pts of the ceiling; the bulk of the loss is a fixed-period (~7.75 s) modulation that is not locked to the hop clock

**Status:** Accepted (analysis) · **Date:** 2026-09-02 (S115) ·
**Follows** DEC-0132's "checkable for free" next step · **reframes** blocker 6 ·
**does NOT close blocker 6**

Job 1 of S115 was arithmetic over data already in hand: S114's `rtl_power` CSV (60 rows) and the
S113/S114 debug window's 3,047 `packet missed` lines (both in session scratch, neither committed).
No prod access beyond read-only `marvinctl` checks; no capture; no campaign.

### (a) With the receiver's passband applied, the RFI does explain channels 46–48

DEC-0132 compared spike frequencies to channel centres in bare MHz and read the result as
"weakens the tie". That comparison skipped the receiver's own selectivity: the demodulator runs at
`19200 × 14 = 268,800` samples/s (`dsp.go:210`), so a burst matters to a channel only if it lands
within roughly **±134 kHz** of that channel's centre. Re-clustering the capture at that width
(44 above-floor clusters in the same 16 rows DEC-0132 counted):

| ch | MHz | misses (DEC-0130) | clusters within ±134 kHz | strongest (dB over floor) |
|---|---|---|---|---|
| 44 | 924.496 | 79 | 2 | 11.5 |
| 45 | 924.998 | 77 | **0** | — |
| 46 | 925.500 | **128** | **8** | 14.6 |
| 47 | 926.002 | **182** | **6** | **19.1** (13 kHz off-centre) |
| 48 | 926.503 | **149** | **6** | 17.3 |
| 49 | 927.005 | 93 | **0** | — |
| 50 | 927.507 | 67 | 2 | 16.2 |

The two channels with zero in-passband exposure (45, 49) are the unremarkable ones; the three with
6–8 exposures are exactly the elevated three; the channel with the strongest, most on-centre hit
(47) has the most misses. DEC-0132's counter-examples — 925.15 MHz and 927.15–927.21 MHz — sit
+150 to +210 kHz from channels 45 and 49, *outside* the passband, which is why those channels are
fine. **The exclusive tie holds once selectivity is applied; DEC-0132's "weakens" was an artifact of
the bare-MHz comparison.**

The interferer has structure: the same frequency triplets recur across windows (924.78/.81/.83,
925.16/.19/.21, 925.56/.58/.61, 925.96/.98/.99, 926.36/.38/.41, 927.15/.18/.21 MHz), each ~25 kHz
apart internally and the groups **~400 kHz apart** — one frequency-hopping device with a fixed
channel comb, not random traffic. A 400 kHz comb against Davis's 501.75 kHz plan aligns within
±134 kHz for about three of every four channels, so if this device covered the whole 902–928 MHz
band, channels 40–43 would be elevated too. They are not (72–79 misses), so either the comb is
confined to the top of the band or the S114 3 MHz window caught only part of it. Separate from the
comb: two on-channel narrowband hits at channels 44 and 50 (source unknown, not the ISS — same
channel in consecutive 10 s windows, which a 149 s revisit cannot do) and the single 193 kHz-wide
near-full-scale event at 927.34 MHz.

### (b) Explaining channels 46–48 explains ~2 points, not 25

The other 48 channels average 69.7 misses (sd 10.0; channels 46–48 are z = 5.8 / 11.2 / 7.9). The
excess at 46–48 over that baseline is **~250 misses of 3,806 — 6.6% of all misses, ~2 pts of the
~30 pt loss in the window.** The remaining ~28 pts are flat across all 51 channels, including the
44 channels nowhere near the captured band. **The ceiling is frequency-independent.** Nothing
found in 924.5–927.5 MHz can be it, whatever it turns out to be.

### (c) The bulk of the loss is periodic in wall-clock time, and not locked to the hop clock

The 3,047 miss timestamps carry structure nobody had looked for:

- **Miss-to-miss gaps peak at 3 hops** (1,176 of 2,357 runs, 50%), then 2 (497), 5 (228), 4 (142),
  6 (104), 8 (95), 11 (27) — gaps ≡ 0 or 2 (mod 3) dominate, ≡ 1 is rare.
- **Autocorrelation by hop lag** peaks at 3, 6, 8, 11, 14, 17, 19, 22, 25, 28, 31, 33, 36, 39, 41,
  44, 47, 50, 52, 55, 58 — multiples of **2.755 hops** — with **no decay out to 60 hops** (~3 min).
- **Consecutive misses are anticorrelated:** 12% of runs are ≥2 long vs 28% expected for
  independent misses at p = 0.32.
- **A Rayleigh scan of miss times** (steady stretch after the last re-init, 14:10–18:16 ET,
  n = 1,553) peaks at **T = 7.7495 s** (R = 0.250, z = nR² = 97). The hop-locked alternative —
  11/4 of the fitted ISS interval 2.81243 s = 7.7342 s — scores R = 0.049 (z = 4), its phase
  wanders freely between 40-min chunks, and folding the misses modulo 11 hops is flat
  (123–167 per bin). **The period is a wall-clock period, not a hop count.** On a 2.81 s sampling
  grid it is indistinguishable from its aliases (~4.41 s, ~2.06 s, …); the true fundamental is one
  of that set.
- **The modulation is smooth, not a hard blank:** folded at 7.7495 s the miss density runs from
  ~0.5× to ~1.6× the mean across the cycle (miss probability roughly 0.17 → 0.5), and the phase
  holds within about ±0.2 cycle across 40-min chunks — stable to ~0.05% over hours, which is
  mechanical- or RC-timer-grade, not crystal-grade.

Loss decomposition over the whole 9,463-hop window: **32.2% missed = 21.9 pts in isolated single
misses (the periodic component lives here) + 5.3 pts in pairs + 0.7 pts in 3–9 runs + 4.3 pts in
runs ≥ 10** (the four `maxmissed` re-inits and the 25–42-long dead stretches — blocker 2's class,
not this one). The periodic component is roughly two-thirds of everything lost.

### What this rules out, and what survives

Ruled out or disfavoured for the periodic component: any hop-locked mechanism (message-type
rotation, hop-table position, per-channel AFC history — all would fold cleanly on the hop grid,
and none does); host-side stalls (cgroup cpu/memory/io pressure all zero on both the container and
`weather.slice`, no throttling, container at ~1.8% CPU, no timer near the period — and the loss was
**72.83% on Foundation vs 72.82% on marvin**, two unrelated hosts agreeing to 0.01 pt); an in-band
interferer in 924.5–927.5 MHz (a 30%-duty process there would have lit every 10 s window; the floor
was flat); a static frequency offset (DEC-0129). Still standing: the parts that moved intact between
hosts — the dongle and its USB geometry (`ReadAsync` with one 1 KB buffer into an unbuffered
`io.Pipe`, `main.go:262`), the Go pipeline, the antenna and feedline, the ISS itself, and the outdoor
path. A smooth periodic modulation with a wandering phase reads most naturally as a **frequency
wobble** (ISS transmitter or receiver LO — DEC-0129 tested static offsets only, and a 7.75 s wobble
is far too fast for a per-channel AFC with a 149 s revisit) or a **slow mechanical modulation of the
path**; either would be gain-flat, siting-flat and window-flat, which is exactly the profile
DEC-0128/0129 measured.

One fact split the field and was not in any doc until now: **the owner's "single-digit loss" Davis
console receives *this* ISS at *this* property** (owner, S115). So the ISS and the outdoor path are
exonerated — a Davis receiver in the same house decodes the same transmissions with ~5% loss — and
**the periodic component lives in our receiver chain: antenna/feedline, dongle, USB geometry, or the
Go pipeline.**

### Next step — a designed capture, not another 10 s-integration sweep

The received-packet side of the debug window is gone: `/srv/docker/weewx/logs/` now holds only
Sep 2's `weewx.log` (daily rotation; the Sep 1 file is not among the rotated copies) and S114
harvested the `missed` grep only. Only the miss lines survive, in session scratch. The next capture
should be dongle-exclusive (weewx stopped, ~25–30 min, same self-service path as S114) and answer
three questions at once, in this order:

1. **Sample drops at the Go binary's own geometry** — `rtl_test -s 268800 -b 1024`, ~5 min,
   locally timestamped: any periodic "lost bytes" reports at ~7.75 s (or an alias) implicate the
   USB/dongle path outright.
2. **Per-packet frequency error and timing** — the deployed `rtldavis` binary standalone with `-v`
   (`-tr 16 -gain 372`), ~15 min: the verbose hop line prints the measured `lastFreqError` per
   packet. A 7.75 s oscillation in that series is a frequency wobble and names the axis; its absence
   pushes toward path or sample-stream mechanisms. Also yields the first received-plus-missed
   sequence with µs timestamps.
3. **In-band RF at sub-period resolution** — `rtl_power` over the full 902–928 MHz at `-i 1`, ~5 min:
   a periodic in-band signal shows as a level that beats at the period; also settles whether the
   400 kHz comb spans the band or stays near the top.

All three tools are present in the prod image (`/usr/local/bin/rtl_test`, `rtl_power`, `rtl_sdr`,
`rtl_fm`, `rtldavis`), so no image change is needed. `exec-ro` takes one whitespace-free token per
argument (no `sh -c` wrappers), so each run is its own invocation.

### What this changes

Blocker 6 stays open but changes shape: it is no longer "which frequency slice" but "what oscillates
at ~7.75 s (or an alias) in the chain the ISS, antenna, dongle and demodulator share." The
channels-46–48 finding is **explained** (an FHSS neighbour on a ~400 kHz comb) and **demoted** to a
~2 pt contributor. `BACKLOG.md`'s ceiling item is rewritten to match. A durable trap goes to
`docs/GOTCHAS.md` §3: harvest a debug window whole before the daily rotation, not the one grep the
current question needs.

## DEC-0134 — Blocker 6 RESOLVED: the ~25% "loss" is the demodulator discarding legitimately received repeat packets as duplicates and booking each one as a miss. Real RF loss measured at 0.3%

**Status:** Accepted (root cause, measured) · **Date:** 2026-09-02 (S115) ·
**Supersedes** the mechanism search in DEC-0128 → DEC-0133 (their measurements stand; their
question is answered) · **closes blocker 6** · **explains** DEC-0035's "double-decode" as a
separate, harmless sub-case · **fix pending** (needs a Go rebuild — S116)

### The capture

DEC-0133's designed capture ran tonight, dongle-exclusive, prod down **20:42:41 → 21:09:10 ET
(26.5 min)**, S114's self-service path (`marvinctl stop` / three `exec-ro` runs / `start`), no
Class C:

1. `rtl_test -s 268800 -b 1024`, 5 min — the Go binary's exact sample rate and block size:
   **zero lost samples** (`Samples per million lost (minimum): 0`, no further output). The
   USB/dongle transport is clean.
2. The deployed `rtldavis` binary standalone, `-tr 16 -tf US -gain 372 -v -fc 0 -ppm 0`, 15 min,
   stderr captured whole (1,601 lines, Go µs timestamps): **295 hops, 214 decoded, 81 "packet
   missed" = 27.5%** — prod's number, reproduced with no weewx, no Python, no pipe in the loop.
3. `rtl_power -f 902M:928M:10k -g 37.2 -i 1`, 5 min (300 rows): floor −45 dBFS; busy ISM band
   (a continuous carrier at 921.6 MHz, bursts to −2 dBFS around 907.9 MHz, heavy activity
   902.6–903.0 / 913.4–913.8 / 924.4–925.0 MHz); no channel's level is periodic at 7.75 s or an
   alias (R ≤ 0.26 everywhere). Kept for the RFI picture; not the mechanism.

### What the standalone log shows

The run logged **89 `duplicate packet:` lines against 81 misses.** Reading them against the loop
(`main.go:393–398`): a decoded packet whose bytes equal the previous decoded packet's bytes is
logged as a duplicate and `continue`d — **the hop handler is skipped**, so the receiver does not
retune and the timer armed at the previous packet (expected visit + 62.5 + 300 ms) fires 0.363 s
later, lands in the "packet missed" branch, increments the per-channel histogram, and only then
hops. In the log that is exactly what happens, every time:

```
   11.250 pkt  8401612C89000511 type 8
   14.061 DUP  8401612C89000511 type 8      ← one hop (2.81 s) later, next channel
   14.425 MISS                              ← 0.363 s after the duplicate
   16.874 pkt  E4014D550103C6BE type E
```

- **89 of 89 duplicates are byte-identical to the immediately preceding decoded packet**
  (same message type, same wind bytes, same payload, same CRC).
- **84 of 89 arrive 2.811–2.813 s after it** — one full ISS interval, on the *next* hop channel.
  A stale re-decode of buffered samples would appear within milliseconds; this is the ISS
  transmitting the same packet again. The remaining 5 arrive within 2 ms of the first decode —
  DEC-0035's within-burst double-decode, which costs nothing (the first decode already hopped).
- **80 of the 81 misses are preceded by a one-hop-later duplicate within 0.6 s.** The one that is
  not (t ≈ 515 s) is the run's only real loss: **1 of 295 hops, 0.3%.**
- Every miss sits at **3.175 s after the last decoded packet** — the timer's own arithmetic
  (2.8125 + 0.3625), not an RF event.
- The repeats come every 2–3 fresh packets (fresh-packets-between-repeats: 2 → 42 times,
  0–1 → 24, 5 → 10) — hence DEC-0133's "every third hop" gap structure. The ISS repeats a packet
  on some cadence of its own (tonight ≈ 8.34 s, Sep 1 ≈ 7.75 s), which is why the period was
  wall-clock, not hop-locked, and why it moved between nights.

### Why every earlier axis was flat

This explains the whole evidence chain at once: gain-flat, window-flat, siting-flat,
offset-flat, frequency-flat, host-independent to 0.01 pt (72.83% vs 72.82% is the *ISS's* repeat
fraction, measured twice), variance binomial, the console single-digit (a Davis console counts a
repeat as a received packet — it *is* one), the miss histogram flat across 51 channels (the repeat
lands on whichever channel is next), and the "pairs" (5.3 pts on Sep 1) as three-identical-in-a-row.
The channels-46–48 RFI (DEC-0133, ~2 pts) and the runs ≥10 (blocker 2's RF-dead class) remain the
only *real* loss mechanisms, and they are small. **`rxCheckPercent` has been under-reporting a
~99% link as ~73% since the receiver was built.** DEC-0035's ~722/day figure was this mechanism's
harmless sibling (the 5-per-15-min within-burst case) — the one-hop-later repeats went to stderr
at DEBUG and were never counted; S114's harvest grepped `missed`, not `duplicate`.

### What the driver sees

The duplicate is dropped before it is written to stdout, so `rtldavis.py` never receives it,
counts the slot against `max_count`, and publishes the deficit as `rxCheckPercent`. The loop
packet cadence therefore has one gap in every ~3.7 slots; the *content* lost is nil (identical
bytes), but consumers get fewer wind samples than the ISS sent and a reception metric that is
wrong by ~26 pts.

### The fix (design, not built here — needs a Go rebuild)

Gate the duplicate check by **time**, not bytes alone: a packet identical to the last one is a
double-decode only if it arrives within the same burst (say < 500 ms); one that arrives ≥ 1 s
later is a new transmission and must be emitted and hopped on. ~3 lines in `main.go` around
`lastRecMsg`. Consequences to design in the same change: (a) `rtldavis.py` will receive
byte-identical consecutive packets — the rain wraparound (DEC-0022) and any "on change" logic
(`log_humidity_raw`) must tolerate repeats (they should: identical bytes means identical counters);
(b) `rxCheckPercent` will jump to ~99% and every campaign baseline, `BACKLOG.md` RF finding, and
dashboard threshold keyed to ~73% becomes stale — dashboard is a separate repo (DEC-0010), notify
via eaglehunt-ops; (c) the image must be rebuilt — DEC-0117's open question (can marvin build
natively?) is now on the critical path; (d) upstream: this affects every `lheijst/rtldavis` user
whose ISS repeats packets — draft an issue/PR (`docs/upstream/`, gitignored; never posted without
an explicit go). Alternative rejected: leaving the Go binary alone and correcting the denominator
in Python — the driver cannot see the discarded packets, so it cannot know which slots were repeats.

### What this changes

**Blocker 6 closes as explained.** ROADMAP P2's "where is the ceiling" is answered: there is no
RF ceiling. The RF-tuning campaigns (A–D) were measuring the ISS's repeat fraction; their
*negative* results (nothing moved the number) are exactly what this predicts and remain valid as
"don't re-sweep" evidence. Reproduction is 15 min: stop weewx, run the standalone binary with
`-v`, count `duplicate packet` lines against `packet missed`. Raw captures (rtl_test log,
demodulator log, full-band CSV) are in local `ARCHIVE/s115-capture/` (gitignored, never tracked).

## DEC-0135 — The duplicate filter is time-gated, the repeat is suppressed one layer up, and the campaigns are not re-run: the fix unbiases the statistic, it does not improve reception

**Status:** Accepted (design + implementation; deploy pending) · **Date:** 2026-09-02 (S116) ·
**Implements** DEC-0134's pending fix · **hardens** DEC-0134's root cause with a test it had not
run · **narrows** DEC-0035's duplicate filter to the population it was actually built for ·
**demotes** the campaign A–D negative results from *settled negative* to *untested* ·
**answers** DEC-0078/DEC-0117's build-host question

### The verification DEC-0134 owed

DEC-0134 rested on payload identity and timing. One alternative survived that evidence and would
have inverted the conclusion: if the packet arriving one loop period later were our own buffer
**replaying** a stale decode rather than a fresh reception, then the transmission really was
missed and the miss booking was honest. Distinguishing them is free — every decode in the S115
capture is preceded by its own demodulator line carrying a correlation magnitude `m1` and a
16-symbol vector `x`. Cross-tabulated against the gap to the previous identical payload:

| gap to prior identical packet | fresh demodulation | replay (identical m1/x) |
|---|---|---|
| < 0.05 s | 8 | 1 |
| 0.05 – 2.5 s | 0 | 0 |
| 2.5 – 3.0 s | **80** | 0 |

**80 of 80** long-gap duplicates were demodulated from fresh samples, on a different channel,
after a retune. They are real over-the-air receptions. Two supporting measurements: the low
cluster medians **2.1 ms** and the high cluster **2.8117 s**, exactly `idLoopPeriods[4]`
(2.5625 + 4 × 0.0625 s), a **1300× separation with nothing in between**; and **89 of 89**
consecutive same-message-type pairs are byte-identical while *no* same-type pair is ever
non-identical — the signature of a deliberate re-send, not of coincidence.

### The fix, in two layers

**Go (`patch/rtldavis-dupgate.patch`, 5 hunks).** `lastRecTime` is added beside `lastRecMsg`; the
byte-equality drop is gated on `curTime - lastRecTime < dupWindow`; survivors fall through to the
normal path (counted, logged, hopped on) and log a distinct `repeat packet:` line. `lastRecTime`
advances **only on acceptance** — advancing it on a drop would let a chain of re-decodes ratchet
the window forward one drop at a time. Default **500 ms**, `-dupwindow` flag: ~240× above the
re-decode cluster and below the shortest possible loop period (2.5625 s, transmitter id 0), so it
cannot swallow a real transmission on any id. The flag exists because rebuilds here are expensive
and it lets the validation run sweep values on one binary.

**Python (`rtldavis.py`).** With repeats now arriving, `self._last_pkt` decides whether one
becomes a loop packet — and it could never fire: `data` carries `curr_cnt0..3`, the Go binary's
cumulative counters, which advance on every packet, so the dict comparison was unconditionally
true. **The guard has been dead code since it was written**, with no test covering it, hidden
because the Go side was dropping repeats itself. Extracted as the pure function `dedup_key()`
(the `rain_delta_tips` precedent) excluding those counters. `_update_stats()` consumes them first
and `rxCheckPercent` is derived from them there, so the metric is untouched. The stale
`else: if packet:` branch — a `NameError` waiting for the first iteration that reached it before
`packet` was bound, unreachable only because the guard could never be false — is fixed in the same
edit. A `repeat_count` stat mirrors `dup_count` so the suppression is measured, not silent.

**Suppress, not emit (owner's call, recommended).** The re-sent payload is byte-identical, so it
carries no information; forwarding it would add ~37% loop packets, InfluxDB points and loop-JSON
writes for nothing. Suppressing keeps downstream volume and cadence exactly as today while the
metric moves. Rain is safe either way (identical counter → delta 0).

### Shipping it

The Go source is not in this repo: `Dockerfile` curls `src.tgz` from `weewx-contrib/weewx-rtldavis`
at an **unpinned `refs/heads/main`**. A tracked patch applied in the build was chosen over forking
upstream (supply-chain weight for four lines) or vendoring the 3 MB Go tree into a WeeWX extension:
it is the smallest reviewable diff in a public repo, it is the upstream PR verbatim, and it **fails
loud** if that unpinned tarball shifts under us. `patch -p1 --batch --forward` plus a
`test "$(grep -c dupwindow main.go)" = "2"` assertion, mirroring the existing `receiveWindow` echo.

**The build-host question on BOOT's critical path is answered: `marvinctl build <path> -t <tag>` is
a tier-2 own-resource verb** — self-service, no owner mediation, no NAS. `/srv/docker/weewx/`
already carries the whole `build-v2.0.4 … build-v2.0.14` tree, so DEC-0078's `git archive` → build
→ `BUILD-EXIT` workflow transfers unchanged; the `docker save`/`load` fallback is not needed.

### What it does NOT do

**It unbiases the statistic; it does not improve reception.** The weather data has been correct
throughout — the discarded packets were byte-identical. The one place a real gain could have hidden
was `maxmissed` re-inits, since a repeat today both fails to reset `chAlarmCnts` and increments it
via the miss branch. Measured over the S115 window, `chAlarmCnts` reached **{1: 74, 2: 7} — max 2,
against a threshold of 51**. That benefit is not real here; the re-inits are genuine RF-dead
episodes (blocker 2), untouched by this.

### The campaigns are not re-run

The argument *for* re-running is real and is recorded so it is not lost: **a flat result from an
insensitive instrument is not evidence of flatness.** Campaigns B–D swept gain, `-ex`, siting and
offset against a metric dominated by a transmitter property, and Campaign B's own run-to-run
scatter (sd 8.47 at gain 496, sd 4.67 at 372) exceeded the entire real signal. DEC-0134's
"negative results remain valid as don't-re-sweep evidence" is therefore **too strong**: those
results are demoted to *untested*, and `docs/ROADMAP.md` / `BACKLOG.md` are reconciled to say so.

They are still not worth re-running. Total remaining headroom is **~6 pts worst case** — 0.3% real
loss in the capture window, ~2 pts of channels 46–48 RFI (DEC-0133), ~4 pts of RF-dead runs ≥10
(blocker 2) — against DEC-0059's **2.0-pt adoption bar**, and both named mechanisms are already
identified and are **not gain-responsive**. Re-sweeping would re-measure axes we have independent
reason to believe are flat, for a prize that mostly is not on them.

**Instead: re-baseline by observation.** Let the fix run several days and read the honest number —
no apparatus, no pre-registration, no prod disruption. ~99% closes the question; materially lower
is a new signal that a campaign could, for the first time, actually resolve. The real prize is
diagnostic: an RF-dead episode is currently buried in ~27% of background pseudo-loss, and against a
flat ~99% baseline **blocker 2 becomes measurable for the first time**.

### Validation before prod

Provable without deploying — rebuild, run the patched binary standalone with `-v` for 15 min as
S115 did. Pre-registered against that baseline (295 hops / 214 decoded / 81 missed / 89 duplicate
lines): `duplicate packet` **89 → ~9**; `repeat packet` **~80** appears; `packet missed`
**81 → ~1**; decoded **214 → ~294**. Only then does it go near prod, bundled with
`REMEDY_MODE=restart_unit` and the v2.0.14 `main` promotion.

Local gates, this session: ruff clean · **466 passed / 17 skipped** (+9 new, `tests/test_dup_time_gate.py`) ·
mypy clean, **67 files** (+1 — the count is the only proof the new file was checked, S76) · secret
gate exit 0 with a positive control that fired. The patched Go source **compiles** (real cgo build,
2.98 MB binary) and its build check was positive-controlled with a deliberate error. The nine new
tests were **mutation-tested**: five mutations (buggy whole-dict compare, gate removed, `dupwindow`
raised above the minimum loop period, reset dropped, log renamed) each failed the suite, and the
restore is green.

### A consequence to record

`rxCheckPercent` is written into every archive record, so post-fix the archive carries ~99% while
all history shows ~73%, with a step at the deploy timestamp. Not bad data — a metric-definition
change — but it will read as a real event to any later analysis, the dashboard's history views
included. It is documented as a dated discontinuity in `docs/DATA_ERRATA.md` so nobody
re-discovers it as an anomaly.

### Rationale

Two lessons the repo keeps re-learning drove the shape of this. First, DEC-0035/DEC-0071's *a
passing test proves nothing if it is structurally blind*: the first draft of these tests asserted
against a **copy** of the dedup expression rather than the shipped one, which would have stayed
green through any change to the driver — hence `dedup_key()` as a real, imported, mutation-tested
function. Second, *a green exit code is not evidence*: `./scripts/check_secrets.sh | tail` reported
exit 0 while the script itself exited 1 — the documented false-zero, met again in the act of
running the secret gate — and the real block was a false positive on a local named `key`, fixed by
renaming the variable rather than widening the scanner's allow-list.

## DEC-0136 — DEC-0135 deployed and confirmed in production: `missed` 81 → 0, and three reception denominators turn out to measure three different things

**Status:** Accepted (deployment + measurement) · **Date:** 2026-09-03 (S117) ·
**Deploys** DEC-0135 · **confirms** DEC-0134's root cause on live production data ·
**corrects** DEC-0135's pre-registered reading of its own validation counters ·
**corrects** the standing assumption that the monitor's ~73% thresholds go stale at this deploy ·
**arms** the remedy path DEC-0074 documented

### What shipped

`v2.0.15`, built on marvin from `origin/dev`@`2fa80a4`, carrying DEC-0135's Go patch and driver
change. Prod cut over at **07:17:53 EDT**, outage 07:01:44 → 07:17:53 (**16m09s**). Gain unchanged
at 372. `REMEDY_MODE` flipped `none` → `restart_unit` at 07:58:59 in a second, receiver-free step.

### Validation, pre-registered and met

15:00 standalone capture on the built image, same flags as S115 (`-tf US -tr 16 -gain 372 -v -fc 0
-ppm 0`), banner confirming `dupWindow=500`:

| metric | S115 (v2.0.14) | pre-registered | measured (v2.0.15) |
|---|---|---|---|
| `packet missed` | 81 | ~1 | **0** |
| `repeat packet` | 0 | ~80 | **79** |
| `duplicate packet` | 89 | ~9 | **6** |
| accepted packets | 214 | ~294 | **274** |
| hops | 297 | — | 276 |

### Confirmed in production, which DEC-0135 could not do

The prod instrument is the driver's own INFO counters, not `ARCHIVE_STATS` (DEBUG-level, absent at
`debug_rtld = 1`). Per ~60 s period:

| | duplicate frames | repeat frames |
|---|---|---|
| 2026-09-02, full day (n=1398) | 6.28 | line did not exist |
| 2026-09-03 pre-restart (n=421) | 6.23 | — |
| **2026-09-03 post-restart (n=37)** | **0.57** | **5.81** |

**The population is conserved** — 0.57 + 5.81 = 6.38 against 6.23 before. **91% of what the
demodulator was calling a duplicate and silently discarding was a real re-send.** At 5.81 repeats
per 21.33 slots that is **27.2% of transmissions**, against DEC-0134's ~27% prediction, measured
this time on production rather than a capture.

### Three denominators, three different questions

The open question was what `276` counts. Read from the upstream Go source rather than inferred: a
hop is emitted on exactly two paths — an accepted packet (`handleNxtPacket`) and a loopTimer
expiry (the `packet missed` branch) — plus init. So **hops = accepted + missed + init**, which
reconciles both captures exactly (274 + 0 + 2 = 276; 214 + 81 + 2 = 297).

| instrument | denominator | what it answers |
|---|---|---|
| `rxCheckPercent` (standalone) | hops = accepted + missed | of slots the receiver tracked, how many decoded |
| slot arithmetic | wall-clock ÷ 2.8125 s | of transmissions the ISS made, how many we took |
| monitor `WINDOW` | `WU_RF_EXPECTED = 21` | distinct 1-second epochs of publish lines |

None is wrong; they are not interchangeable, and DEC-0135's headline used the first while the
natural reading of "reception" is the second.

### Two corrections to DEC-0135's own numbers

**(a) The 85.6% slot-arithmetic shortfall was cold-start acquisition, not loss.** Measured every
inter-arrival gap across the capture: **273 gaps, median 2.800 s, max 2.900 s, zero gaps above
4 s** — locked hard to the 2.8125 s cadence with no dropouts at all. The log shows `Init channels:
wait max 149 seconds` at 11:01:56 and `TRANSMITTER 4 SEEN` at 11:04:04, i.e. **128 s of
acquisition** before the first accepted packet. The steady-state window is **767.8 s**, not 900.
Expected transmissions = 767.8 / 2.8125 = **273.0**; accepted = **274**. Reception over the
measured window is **~100%**. Dividing the full 900 s by the slot period counts 46 slots during
which the receiver was not yet tracking anything.

**(b) A repeat is counted as a decode.** The patched branch logs `repeat packet` and then **falls
through** to the normal path, emitting a `msg.ID=` line and hopping. So the 274 "decoded" already
include the 79 repeats — **unique payloads are 195**. Reception is unaffected (all 274 are genuine
transmissions), but any future reading of these counters must not treat "decoded" as "distinct
readings".

### The monitor's thresholds do NOT go stale — reversing a standing assumption

`BOOT.md` and ops#256 both carried the claim that the monitor's ~73%-keyed thresholds expire at
this deploy. **Measured, they do not.** Seven clean windows post-restart against eight pre-outage:

- pre-fix: 17, 17, 16, 16, 13, 17, 13, 14 → mean **15.38/21 = 73.2%**
- post-fix: 16, 16, 17, 16, 14, 18, 14 → mean **15.86/21 = 75.5%**

A real +28% publish jump would put the mean near 19.7 and be unmissable across seven windows. It is
absent, and the mechanism is DEC-0024's arriving from a new direction: the metric is
`len(set(epochs))` — **distinct one-second epochs**, already counting freqError hop packets as well
as data packets, so the dedup saturates long before the change shows. **The metric is substantially
insensitive to what was fixed.** `WU_RF_MIN_PCT = 60` and the existing thresholds stay valid.

Only a consumer reading `rxCheckPercent` needs re-keying, and prod computes that in
`_update_summaries()` as delta `chTotMsgs` over a **wall-clock** denominator — never hops — so
readings **above 100%** are expected where the floor()'d denominator lands low.

### Deployment is not self-service — four gaps, all found by doing

1. **No transport.** `/srv/docker/weewx` is not a checkout and the tenant has no `git_branch`, so
   `marvinctl pull` refuses. Every past build context is an unpacked tarball snapshot. This release
   rode a one-off owner-authorized `scp -r` of a `git archive` export (126 tracked files, verified
   byte-for-byte by sha256 on both ends).
2. **No image-tag control.** The tag is a literal in `ExecStart` of a `0644 root:root` unit — no
   `EnvironmentFile`, no parameterization — so the cutover required an owner-run `sed` +
   `daemon-reload` + `start`. An `EnvironmentFile` carrying `IMAGE=` in the tenant dir would make
   every future cutover self-service; deliberately **not** bundled into this session's monitor
   batch, because it hands a tenant control over what root launches and that reading is marvin's
   to record first.
3. **No config write.** `weewx.conf` is tenant-owned but `marvinctl` has no write verb, so the
   mounted-config layer is owner-run too.
4. **No ad-hoc archive read.** `rxCheckPercent` reaches a human only through the monitor's
   scheduled email. Cheapest fix is the monitor also `log()`-ing the summary it already computes.

### Stale campaign residue

Campaign D completed 2026-09-01 01:30:39 ("prod restored to baseline"), but two of its artifacts
outlived it. **`campaign.inhibit`** (born 2026-08-31 17:40) was still present, and
`weewx_monitor.py` checks `campaign_inhibited()` at :705 **before** the `REMEDY_MODE` check at
:712 — so flipping `REMEDY_MODE` to `restart_unit` while that file existed would have been a
**silent no-op**, logging `SKIP remedy` forever. Removed in the same step as the flip. Worse, the
lifecycle documented at `ops/weewx-monitor.service:84` ("the campaign script creates this file for
its duration") **does not exist in any code** — nothing creates or removes it.
**`weewx-rx-experiment.timer`** likewise remains armed, firing every 5 minutes against a finished
campaign; harmless (it has written nothing in 2.5 days) but unfiled residue.

### Verification notes

The build ran through `marvinctl build`, so DEC-0078's `BUILD-EXIT` marker — which belongs to
`ops/nas_build.py` — did not exist on this path. Rather than trust a pipeline exit, the artifact
was proven directly: `exec-ro` running `rtldavis -h` on the new image, at **zero outage**, printing
`-dupwindow int … (default 500)`. Generalizes: when the sanctioned proof does not cover the path
taken, prove the artifact, not the pipeline.

Also unresolved and recorded rather than smoothed over: the monitor never logs its remedy mode at
startup, so the armed state cannot be positively confirmed short of a real fault. `remedy_action()`
exists for exactly DEC-0074's reason and is only called at remedy time. Ordering of this session's
flip is guaranteed by the `&&` chain, not by timestamps — the unit mtime and the process start fall
in the same second.

## DEC-0137 — #317: rxCheckPercent denominates by ISS slots between received packets, not floor(wall-clock period / loop period); >100% becomes structurally impossible, not just clamped

**Status:** Accepted (implementation; merged to `dev`, deploy pending as `v2.0.16`) · **Date:**
2026-09-03 (S120) · **Root-causes** #313, superseding its own clamp (PR #315, tracker-recorded, no
DEC) with a fix at the source · **implements** the design `BOOT.md`'s S120 job list wrote into #317

### The bias the clamp could only mask

DEC-0136 already named the mechanism: `_update_summaries()` computed `max_count = period //
loop_time`, floor-dividing a wall-clock archive period by the per-transmitter loop period
(2.8125 s for this ISS). A 60 s period floors 21.33 to 21; a 59 s period (the archive event's own
~1 s jitter) floors 20.13 to 20 — both below the 21.33 real transmissions/minute, so a fully
received minute reads 101–105% (~103% mean). PR #315 (#313, S119) clamped each record at 100 and
relabeled `dropped` a lower bound — correct reporting, but the over-count was still being computed
every period, just capped after the fact. The 2026-09-03 12:00–18:00 email (routed via ops, #317
comment) measured the scale directly: **197 of 360 records (55%) read over 100%** under the old
denominator, at the top of S35's original "a third to a half" estimate — meaning 59 s periods are
at least as common as 60 s ones.

### The fix

`_update_stats` now records each transmitter's **last accepted-packet arrival time**
(`last_pkt_ts[i]`) alongside the existing counters. `_update_summaries` denominates by
`round((last_pkt_ts[i] - prev_pkt_ts[i]) / loop_time[i])` instead of `period // loop_time[i]` — the
ISS's own clock, not the archive engine's. S115's capture measured that clock at **2.8124 s mean,
1.0 ms sd** across 292 gaps, tight enough that `count[i] <= max_count[i]` holds by construction:
the denominator is now the actual number of slots the ISS could have transmitted in, not an
estimate of it. **Over 100% becomes structurally impossible, not just invisible** — PR #315's clamp
stays in place as a defensive floor (a `NaN`/negative-delta guard, not the everyday case) but should
never fire again outside a counter discontinuity.

Counter resets — child respawn, hot-swap, a stall-triggered restart — clear both timestamps so the
baseline never spans a discontinuity and doesn't manufacture a spurious `max_count`.

### Coverage and gates

`tests/test_slot_count_denominator.py` (new): the four synthetic cases from #317, the counter-reset
guard, and a 500-period randomized invariant sweep asserting `count <= max_count` never breaks.
`test_reception_stats.py` and `test_issue_225_qc_fixes.py` updated to seed the new baseline — both
drive `_update_summaries` directly, bypassing `_update_stats`. Squash-merged PR #319 → `dev`@`e158741`.
Gate: ruff clean · 475 passed / 17 skipped (+6) · mypy clean, 68 files · secret gate clean.

### Deploy is the remaining half of this DEC, not a formality

Per this repo's own deploy-layer lesson (`CONSTANTS.md` — the driver is BAKED into the image, never
mounted), a `dev` merge is a silent no-op in prod. #317 stays **open** until `v2.0.16` actually
ships and is verified live — the 55%-clamped baseline above is the pre-measurement; post-deploy the
expectation is ~0. Remaining, per `ops#257` (no self-service tree transport to marvin — no
`git_branch`, no `.git` in the tenant root, so this routes through the same one-off
owner-authorized transport DEC-0136 used for `v2.0.15`): tree transport (owner) → `marvinctl build`
(self-service) → unit image-tag flip (owner) → confirm the 18:00/00:00 monitor emails on the new
denominator → `docs/DATA_ERRATA.md`'s `DISC-0001` second boundary (a metric-definition step change,
same treatment DEC-0135's ~73%→~99% discontinuity got).

## DEC-0138 — DEC-0137 built and deployed as `v2.0.16`: 31 s cutover, artifact verified directly before touching prod, statistical proof still pending the next monitor cycle

**Status:** Accepted (deployment) · **Date:** 2026-09-03 (S121) · **Deploys** DEC-0137 · **advances**
#317 from "merged" to "running in prod, deploy-verified" · does **not** close #317 — that needs the
metric-level proof this DEC explicitly defers

### Transport and build

Same shape as DEC-0136's v2.0.15 precedent, because `ops#257` (self-service `git_branch`/checkout
on the marvin tenant) is still open: `git archive --format=tar.gz` of `dev`@`73acc3d` locally →
owner-authorized `scp` to `/srv/docker/weewx/` (Class C — no restricted key or forced command covers
file transfer to marvin; sha256 `1ca2e768…` verified identical on both ends) → owner `sudo tar -xzf`
extraction into `/srv/docker/weewx/build-v2.0.16/` (a second, distinct Class C wall: the owner's
`marvin-admin` account has no write access to the `t-weewx`-owned tenant root regardless of the
scp-transfer confirmation already given — two different gates, two different mints, discovered by
hitting a plain `Permission denied` after the guard's own token had already been consumed). `marvinctl
build /srv/docker/weewx/build-v2.0.16 -t weatheredscientist/weewx-rtldavis:v2.0.16` then ran
**self-service**, no further gate — confirming DEC-0135's build-host answer still holds.

### Verified directly, not from the pipeline's exit

Per this repo's own `docs/GOTCHAS.md` §1 discipline (a green result is a claim, not proof) and
DEC-0136's precedent (the `BUILD-EXIT` marker doesn't exist on the `marvinctl build` path):
`marvinctl exec-ro weatheredscientist/weewx-rtldavis:v2.0.16 -- grep -n last_pkt_ts
.../rtldavis.py` — confirmed the slot-count fields and denominator logic are actually baked into the
image before the unit file was touched.

### Cutover

Owner root-edited `/etc/systemd/system/weewx.service`'s `ExecStart` (`v2.0.15` → `v2.0.16` literal —
the ops#257 limb-2 `EnvironmentFile IMAGE=` gap, `BOOT.md` job 4, is still open) and ran
`daemon-reload` + `restart`. Journal: `Stopping…` 20:28:35 EDT → `Started…` 20:29:06 EDT — **31 s**,
a same-host container recreate, nowhere near DEC-0136's 16m09s (which included the marvin host-move
build/transfer wait, not repeated here). Container image sha (`1a9daeb6c7…`) matches the build
exactly; driver banner unchanged (`0.20+ws.5` — confirms no regression on the dupgate/ws.5 patch
lineage); `weewxd` reached `Starting main packet loop` and published its first records within
seconds. No `CRITICAL` in the log since restart; the one `ERROR` (`WOW: HTTP Error 429`) matches a
rate-limit pattern present before this deploy too (07:19:16 and 14:07:53 the same day), not a new
fault.

### What this DEC does not claim

**Deploy-verified is not metric-verified.** This confirms the code is genuinely running in prod with
no startup regression — it does not yet show `rxCheckPercent` behaving differently, because that
needs real archive periods to accumulate and compare against the pre-fix 55%-over-100% baseline
(#317 comment, 12:00–18:00 window). Per `BOOT.md`'s own job-1 sequencing, #317 stays open until the
18:00/00:00 ET monitor email confirms the new denominator, and only then gets `DISC-0001`'s second
boundary in `docs/DATA_ERRATA.md` — the same two-step DEC-0135→DEC-0136 pattern this decision
continues.

## DEC-0139 — DEC-0138 confirmed by the metric: the first fully-post-cutover monitor window reads 0 records over 100%, down from 197/360 (55%); #317 closed

**Status:** Accepted (measurement) · **Date:** 2026-09-04 (S122) · **confirms** DEC-0137/DEC-0138 on
production data · **closes** #317 · **completes** the DEC-0135→0136→0137→0138→0139 verification
chain for the rxCheckPercent fixes

### What was checked

`weewx_monitor.py`'s 6-hourly `RECEPTION SUMMARY (rxCheckPercent)` email log
(`/srv/docker/weewx/logs/weewx_monitor.log`, read via `marvinctl grep`/`tail`), across the three
windows spanning the `v2.0.16` cutover (2026-09-03 20:29:06 EDT):

| Window (ET) | Relative to cutover | Records over 100% (clamped) |
|---|---|---|
| 2026-09-03 12:00–18:00 | fully pre-fix | **197 of 360 (55%)** — matches `BOOT.md`'s S121 figure exactly |
| 2026-09-03 18:00–00:00 | spans the cutover | 86 of 358 — already dropping, window is a mix |
| 2026-09-04 00:00–06:00 | fully post-fix | **0 of 360 (0%)** — no "Records reading over 100%" line at all |

The 00:00–06:00 body shows every hour at exactly 100% reception, mean reception 100%, `Packets
dropped (est, lower bound): 4` against 7,680 transmitted (est.) — a real, small, physically
plausible loss, not a divisor artifact. This is the first monitor window entirely after the
20:29:06 EDT cutover, so it is the cleanest possible read: no mixed pre/post records to average
across.

### Why this settles it, not just suggests it

`round((last − prev) / loop_time)` (DEC-0137) makes `count[i] <= max_count[i]` hold **by
construction** — the fix isn't statistical, it's structural, so one clean window is sufficient
confirmation, not a sample requiring a longer run. The 197→86→0 progression across the three
windows is also the expected shape if the fix is real: a step at the deploy instant, not a gradual
drift that could be confused with normal RF variance.

### Actions taken

- `docs/DATA_ERRATA.md`'s `DISC-0001` gets a second boundary (2026-09-03 20:29:06 EDT / `v2.0.16`)
  documenting this as a metric-definition step, same treatment as DEC-0135's ~73%→~99% step —
  historical `rxCheckPercent` values are not corrected, only the boundary is recorded.
- **#317 closed** with this measurement as the closing comment.
- `BOOT.md` job 3 (Docker Hub promotion, `main` tag) and job 5 (campaign-residue retirement) remain
  open — this DEC closes the metric question only, not the release-promotion or cleanup jobs still
  on the S122 list.

## DEC-0140 — `campaign_analyze.py`'s `rx > 100` backstop stays exactly as it is — not raised, not removed (#314 closed as overtaken by #317)

**Status:** Accepted (decision, no code change) · **Date:** 2026-09-04 (S123) · **closes** #314 ·
**depends on** DEC-0137 (the slot-count denominator) and DEC-0139 (its production confirmation)

### Context

#314 was filed at 2026-09-03 12:41 ET, split out of #313. At that moment prod ran `v2.0.15`:
DEC-0135's repeat-packet fix had pushed the numerator to ~100% against the driver's old floored
denominator (`period // 2.8125` → 20 or 21 slots for 21.33 real transmissions/min), so a fully
received minute read 101–105%, and `ops/campaign_analyze.py`'s `partition()` excluded it as
"nonphysical". The issue's own text said any readout over data after 07:17:53 ET was low by
construction — true when written.

Eight hours later, at 20:29:06 ET, #317's fix (`v2.0.16`, DEC-0137/0138) replaced that denominator
with `round((last_pkt_ts − prev_pkt_ts) / loop_time)` per transmitter (`rtldavis.py:1684-1691`).

### What that changes

The new denominator scales with *real elapsed time between received packets*, which has two
consequences the issue could not have anticipated:

1. `count <= max_count` holds by construction, so `rx <= 100` on every good minute — confirmed on
   the first fully-post-cutover window, 0/360 over (DEC-0139).
2. The DEC-0067 absorption artifact — a record stamped `interval=1` that absorbed two minutes and
   read 200% — cannot recur either: both `count` and `max_count` grow with the span, so such a
   record reads ~100.

So across the three driver regimes:

| Data span | Good minutes | The `rx > 100` rule |
|---|---|---|
| Pre-v2.0.15 — every campaign A–D row | ~73%, never >100 | Correct: fires only on the genuine 2026-07-29 03:10 absorption record |
| v2.0.15, 09-03 07:17:53 → 20:29:06 ET (~13 h) | 101–105% | Over-excludes — the **only** affected span; no campaign ran in it |
| Post-v2.0.16 | ≤100 by construction | Dormant: cannot fire on good minutes or on absorption records |

### Options weighed (on Fable, owner's call)

- **A — docstring only.** Record the three-regime analysis in `partition()`'s module docstring;
  close #314. No logic, no test change. **Chosen.**
- **B — raise the threshold to 150 and clamp survivors at 100.** The Sonnet-tier first pass
  recommended this. It is future-proofing against a denominator regression nothing predicts, the
  clamp half is a no-op today (nothing reads >100), and it rewrites two passing tests.
- **C — drop the magnitude rule.** Removes a dormant rule and its tests (churn) and would re-admit
  the 2026-07-29 record into any Campaign A re-read unless `gap_adjacent()` independently catches
  it — likely, but not proven, and not worth proving for a tool whose campaigns are not re-run
  (DEC-0135).

### Why the record matters

The first-pass recommendation was wrong for a reason worth keeping: it evaluated the fix options
without first checking whether the premise still held. The escalation to Fable was requested by
the owner *before* implementation, and the re-read is what found that #317 had already moved the
ceiling. "Moot once #317 ships" was in `BOOT.md`'s own job list; it was not acted on until read
against the driver source. Lands with PR #328; docstring text in `ops/campaign_analyze.py`.


## DEC-0141 — InfluxDB leaves Foundation for marvin as a stopped-server raw tree copy into a weewx-owned `weewx-influxdb.service`; consumers change one URL each

**Status:** Accepted (design; runbook + unit written, nothing executed) · **Date:** 2026-09-04
(S124) · **implements** ops#260 step 3 under OPS-DEC-0188 · **depends on** MARVIN-DEC-0110/0111
(tenant manifest shape), DEC-0100 (the `eh_rollup` Task is dashboard's, inside our container),
DEC-0008 (`docker kill`, never `stop`, on the NAS), DEC-0119 (`ops/backfill_influx.py` fixes) ·
**runbook** `docs/INFLUXDB-MIGRATION.md` · **unit** `ops/weewx-influxdb.service`

### Context

The owner's direction of 2026-09-03 (OPS-DEC-0188) narrows Foundation (the DS918+) to backup duty:
every weather workload moves to marvin, and a Foundation outage must not touch a weather service.
ops#260 inventoried Foundation and sequenced the moves — HLF, then the dashboard's tunnel/proxy, then
**InfluxDB last** ("most stateful; weewx executes as compose owner, marvin hosts, consumers repoint
`INFLUX_URL` once; split into its own ops issue when weewx picks it up"). HLF cut over 2026-09-04
12:26 ET and EHWD ~19:35 ET; ops then posted the owner's ask for weewx's plan and schedule. This
DEC is weewx picking it up.

Measured 2026-09-04 ~21:30 ET, not recalled: Foundation runs `influxdb:2.7` (engine **v2.7.12**,
up since 06-19) from weewx's NAS compose, bind mounts `/volume1/docker/influxdb/{data,config}`,
8086 published on the host; **16.4 MB across 64 shards** (`/metrics`, unauthenticated) — `weewx`
16.1 MB, `eh_rollup` 0.2 MB. All three consumers already run on marvin and reach it by Foundation's
LAN IP: weewx's `influx.py` (`server_url` in `weewx.conf` **and** `weewx.conf.rx-baseline`),
eh-proxy (`secrets/proxy.env`), dashboard's hourly `event-detect` (`secrets/event-detect.env`). HLF
has no runtime Influx use. Marvin's weewx tenant manifest is `units = weewx*.service weewx*.timer`,
`containers = *weewx*`, `paths = /srv/docker/weewx`, uid:gid **996:986**.

Two measurement traps met on the way, both recorded in the runbook: `nasctl ls` of the data dir
returns an **empty listing** because the dir is `0700 uid 1000` and the read-only key is neither — a
permission false-zero (GOTCHAS §1), not an empty store; and the compose file's own comment says
InfluxDB has "NO host port mapping" while `inspect` shows `8086 → 0.0.0.0:8086` — the comment is
stale, the port is what the marvin-side consumers have been using since DEC-0118.

### Decision

1. **Raw copy of `data/` + `config/`, not `influx backup`/`restore`.** Same engine version both
   sides, so the bolt/sqlite metadata and TSM/WAL trees carry the org, both buckets, **every
   token**, the `eh-daily-rollup` Task and the CLI operator config byte-for-byte. That is the
   like-for-like move ops#260's hygiene rule asks for: each consumer changes exactly one thing (the
   URL), nothing is re-minted, nothing is re-created, and a regression can only be the host.
   `restore --full` reaches the same end through a second mechanism with its own semantics to
   verify — no benefit at this size.
2. **The cutover copy is taken from a STOPPED server; a live snapshot is used only for the
   dark-parallel test.** COMPUTE-NODE.md §3's "live pre-rsync then delta" exists to bound the
   outage on a large store; at 16 MB the outage is the owner's gesture time. The pre-copy's real
   value is proving the unit, the uid mapping and the bolt store *before* anything is at stake —
   so stage 1 does exactly that from a live tarball (torn bolt = influxd refuses to start = the
   test working), stopped, and wiped again before stage 2 lays down the real tree.
3. **Name and placement: container and unit `weewx-influxdb`, paths under
   `/srv/docker/weewx/influxdb/`, `weather.slice`.** Both names fall inside the existing weewx
   manifest globs, so `t-weewx` gets start/stop/restart/logs/inspect/journal through `marvinctl`
   with **no manifest change and no new grant**; the store stays weewx-owned as ops#260 arbitrated;
   dashboard's `eh_rollup` bucket and Task live inside it unchanged (DEC-0100). Its own tenant was
   considered (it is "everyone's store") and rejected: it would add a fifth manifest, a fifth key,
   a fifth slice and an arbitration round for a 16 MB service whose only writer is weewx.
4. **`influxdb:2.7.12` pinned, `--pull=never`.** Dashboard's Flux Task was verified against this
   engine's boundary semantics (their `influx/README.md` §1 refuses to install on a changed
   engine); a floating `:2.7` could bump it silently at the first pull on a new host. The owner pulls
   once at install; a missing tag fails loudly (the eh-proxy shape, MARVIN-DEC-0111).
5. **`--user 996:986` (`t-weewx`), copied tree chowned to it.** Foundation's tree is uid 1000
   only because the official image gosu-drops to `influxdb` when started as root; on marvin uid 1000
   is a human account. Started non-root the image skips init/gosu and runs influxd directly —
   upstream-supported, and the only defensible ownership on a multi-tenant box. This is the one
   deliberate divergence from like-for-like, and it is a host-mapping change, not a database
   behaviour change.
6. **No `DOCKER_INFLUXDB_INIT_*` in the unit.** The bolt store is initialised, so they are ignored
   — and they are the admin password and operator token; a unit never carries a secret
   (ACCESS-AUDIT-S7 A6).
7. **`-p 8086:8086`, like-for-like.** eh-proxy is on the default bridge and reaches the host's LAN
   IP; loopback would not be reachable from it. Tightening the bind is a post-move change.
8. **Foundation's instance is stopped with `docker kill -s TERM` (clean WAL flush without
   `docker stop`'s hang, DEC-0008), then `docker update --restart=no`, and RETAINED** — container,
   image, trees — until ops#260 step 4 retires Container Manager after the drill. Explicit
   `--restart=no` because a NAS reboot must not be able to bring a stale second store back on the
   LAN, whatever `unless-stopped`'s treatment of a killed container turns out to be.
9. **The archive-write gap is backfilled from SQLite**, the source of truth, with the DEC-0119-fixed
   `ops/backfill_influx.py` — the copy on marvin is the 2026-06-19 pre-fix version and must be
   transported first. Loop-packet posts lost in the window are lost by design.
10. **Nothing rides along.** Bind tightening, a memory cap, retention, dropping `lease_dir`, the
    consistent-dump timer — each lands before or after as its own change, never inside the cutover
    (ops#260 hygiene; TENANT-MIGRATION-LESSONS §2).

### Consequences

- **Order of operations is load-bearing** (runbook §4): pause the event-detect timer → kill Foundation
  → copy → start marvin → repoint weewx (both conf files, then `restart weewx.service`, ~31 s) →
  repoint dashboard's two files → resume the timer → backfill → confirm Foundation's 8086 refuses.
  The window avoids 01:00–01:30 ET (the Task) and 03:10–03:40 ET (dumps + restic).
- **First backup the weather history has ever had.** Foundation's store was inside no backup
  (Hyper Backup never set up, ops#209). On marvin it sits in restic's nightly `/srv` set; a
  `weewx-influxdb-backup` pre-dump timer (`influx backup`, the `weewx-db-dump` slot) follows as
  stage 3 — a file-level copy of a live TSM/bolt tree is not a backup.
- **`influx.py`'s NAS-LEASE courtesy yield (DEC-0111) becomes moot**, not broken: after the move
  weewx has zero NAS I/O to yield. `lease_dir` stays set (a harmless no-op against the empty dir,
  MARVIN-DEC-0063); `BACKLOG.md`'s cross-host lease wiring item closes as overtaken once the move
  ships; a config-only cleanup may drop the key later.
- **`weewx.conf.rx-baseline` must be edited alongside `weewx.conf`** or the next campaign's
  `restore_baseline` silently points the writer back at a dead host — CONSTANTS.md's DEC-0080 shape.
- **Docs that move with it** (stage 3): `CONSTANTS.md` Infra/deploy-layer rows that still say the NAS
  hosts InfluxDB, `docs/ARCHITECTURE.md`, `docs/INTERFACES.md` §2's "over the Docker `weather-net`
  network" wording; ops `NAS-RUNTIME.md` and `CONSTANTS.md` §5; dashboard `MARVIN-MIGRATION.md`.
- **Rollback** needs no reverse copy: repoint back and `docker start influxdb` on Foundation; the
  `weewx` bucket is regenerable from SQLite, `eh_rollup` from dashboard's Task backfill procedure.
- **What does not change:** the data contract (`docs/INTERFACES.md` §2), every token, the org, the
  buckets, the Task, the engine version, the write cadence, the dashboard's queries.
