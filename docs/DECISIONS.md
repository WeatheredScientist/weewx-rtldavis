# Decision Log — weewx-rtldavis

**Status:** Source of truth
**Last updated:** 2026-07-05 (S29 — DEC-0025 known-bad-data policy; see docs/DATA_ERRATA.md)

This file records accepted, superseded, and deferred decisions so future sessions don't
re-litigate settled choices. Append-only: a decision is never edited in place — it is
**superseded** by a later entry that references it.

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
chart title, the InfluxDB org name). *Follow-up:* rotate the exposed WU key (BACKLOG).

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

## DEC-0022 — Sensor-QC hardening deferred to S19 (OPEN)

**Status:** Deferred · **Date:** 2026-07-04 (S18)

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

**Status:** Layer A implemented (S22) — pending a monitor-restart deploy; Layer B deferred ·
**Date:** 2026-07-04 (S21), updated 2026-07-05 (S22)

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
