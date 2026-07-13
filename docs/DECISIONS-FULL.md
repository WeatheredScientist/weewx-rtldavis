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
