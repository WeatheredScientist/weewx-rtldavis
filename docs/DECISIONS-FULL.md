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
(BACKLOG, ROADMAP).

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
6-step closeout skeleton (OPS-DEC-0016, locked OPS-DEC-0019 once three of four repos had adopted)
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
