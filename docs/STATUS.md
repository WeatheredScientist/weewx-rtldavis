# Status — weewx-rtldavis

**In-flight working state (what's on the bench right now).** Read first at the start of a session,
update last before finishing. ROADMAP.md holds the full prioritized plan; this file holds only what
is actively in motion, parked, or needs a check.

- DECISIONS.md records *settled* decisions. **This file records open ones.**
- CHANGELOG.md records *shipped* work. **This file records work not yet shipped.**
- **This file is the single source of truth for the current session number and the next-session
  handoff** (DEC-0023). Every other doc — and Claude memory — points *at* this; none carries its own
  copy. Handoff state lives here (in the repo, visible on GitHub), never only in private memory.

When something here becomes permanent (a decision is made, a feature ships), move it to
DECISIONS.md / CHANGELOG.md and delete it here. Keep this file short — **prune at every session
close** (DEC-0030): shipped blocks out, superseded notes out; if CHANGELOG or a DEC already tells
the story, this file only points at it.

> **Current session: S40** (2026-07-13) — **a comment is not an exemption.** The secret gate let a
> commented-out credential into a **public** repo — and its own planted-payload test **asserted that was
> correct**, as part of DEC-0039's "28/28, proven". The proof had certified the hole. `ALLOW (1)` is
> deleted, comments are now scanned exactly like code, **no exemption was added**, and a **full-history
> scan of all 333 blobs found the hole was never exploited** (DEC-0045). S39's PR #34 also merged to
> `dev`. Full story: CHANGELOG `[S40]`.

_Last updated: 2026-07-13 (S40)._

---

## Active thread

> **▶ Resume here (S40 → S41).**
>
> **1. v2.0.7 is built but NOT released — this is the biggest open item.** The `[[root]]` logging fix
> (DEC-0043) is **merged to `dev`** (PR #34, S39) but not shipped. It needs: `dev` → `main`, tag, **Docker
> Hub push**, GitHub release. Until it ships, every downstream user still sees 15 tracebacks on
> `docker run` and loses their startup diagnostics. Prod is **not** affected by the noise (bounded burst,
> steady state silent), so there is no urgency to restart the station for it — fold the prod deploy into
> the release in **one attended window**, which also activates the raw-humidity capture below.
>
> **2. The raw-humidity capture is ARMED but NOT ACTIVE.** `log_humidity_raw = true` is in the live
> `weewx.conf` and parses, but **weewx reads its config only at startup — it takes effect on the next
> container restart.** The v2.0.7 deploy is the natural moment. Once running, the **next midday humidity
> spike** logs its raw `pkt[3]`/`pkt[4]` and settles the nibble question deterministically (DEC-0044).
> Spikes run ~2–3/week, clustered 11:00–16:00.
>
> **3. Cross-repo etiquette / the 4th-project question — STILL PARKED FOR FABLE** (owner's call). Do
> **not** re-litigate or start building it. Everything is in
> `docs/handoffs/S38-cross-repo-architecture.md` §Etiquette. DEC-0040 settled the *enforcement* half
> (no master repo; guards in `~/.claude/hooks/`); this is only the *etiquette* half.

## Upstream — all three landed (S38)

- **[lheijst/weewx-rtldavis#22](https://github.com/lheijst/weewx-rtldavis/pull/22)** — the rain-counter
  wraparound fix. OPEN.
- **[Issue #15 comment](https://github.com/lheijst/weewx-rtldavis/issues/15#issuecomment-4960224128)** —
  **POSTED 2026-07-13** (owner-approved). The first comment on that thread since **2022-11-14**. Explains
  the duplicate-frame mechanism, the wraparound bug, and — new at S38 — that the phantom **rainRate is
  ISS-side, not a driver bug** (DEC-0042), which three people there had been hunting in software.
- **[david-lutz/weewx-influx2#1](https://github.com/david-lutz/weewx-influx2/pull/1)** — TLS verification
  on by default + four more. OPEN; that repo's first-ever PR, and it has been quiet since 2023, so it may
  simply sit.

**Watch for replies.** `lheijst` was active as recently as 2026-07-09.

## Shipped — nothing to do here

- **S38** (v2.0.5 → **v2.0.6** on Docker Hub; prod recreated + verified; `prod-baseline-20260713` tagged;
  `influx.py` drift closed; the `~/.claude/hooks/` enforcement layer live and tested; 47 MB reclaimed):
  see CHANGELOG `[S38]` and DEC-0038/0039/0040/0041/0042.
- **S39** (root-logger fix DEC-0043; nibble theory falsified DEC-0044): CHANGELOG `[S39]`. **On `dev`,
  not released** — see "Active thread" item 1.
- **S40** (the secret gate scans comments like code — DEC-0045; suite 28 → 41; a full-history scan of all
  333 blobs proved the hole was never exploited): CHANGELOG `[S40]`. **DEC-0039's "28/28 proven" is
  superseded** — two of those 28 asserted a *commented-out* credential must PASS.

## Open threads (backlog — none of these block anything)

- **✅ rainRate — ANSWERED (DEC-0042).** ISS-side sensor artifact, not RF and not the driver: condensation
  trips the reed switch enough to start the rate timer, never enough to tip the bucket. **Next step is
  physical (inspect the bucket + reed switch), not software** — a third event is predictable on the next
  calm, saturated, cooling night. Full evidence in DEC-0042; **do not re-derive it.**
- **✅ Cross-sensor coupling filter — PARKED, DELIBERATELY NOT BUILT (DEC-0044).** Do **not** pick this up
  as specced; its premise failed on our own data. **The mechanism is the open question, not the
  threshold** — the raw-byte capture in "Active thread" is what settles it. Full reasoning in DEC-0044.
- **Monitor alert on the new rejection signature (S33 follow-up #1)** — extend `weewx_monitor.py`'s
  rain-glitch email to SensorQC rejections; needs its own pattern + a rate cap so a flapping sensor
  can't spam. Only worth doing once we see the real rejection rate.
- **Reception Layer B (DEC-0024)** — driver stops publishing dataless freqError packets + persists raw
  `count`/`missed`. Deferred to **v2.0.5** (S34) so v2.0.4 stayed single-purpose. Needs design + approval
  (No-Rewrite).
- **Cold-load Fix B (`current.json`)** — `loop_json_writer.py` also writes an atomic `current.json` the
  dashboard fetches first at boot, so a *first-time* visitor doesn't see em-dashes. Richer than
  originally scoped now: the loop packet gained `barometer`/`dewpoint`/`heatindex`.
- **`DewpointCacher` × `SensorQC` interaction (S36, undecided).** The cacher carries `outTemp`/
  `outHumidity`/`radiation`/`UV` forward for up to 300 s, so a value SensorQC *rejects* gets refilled
  with the last good reading (~40 s old) rather than left null. The bad value never propagates either
  way — so this did **not** block v2.0.4 — but a rejected reading is currently indistinguishable from an
  absent one in the data (the rejection is still logged loudly). Decide whether that's right.
- **Gain 372, interim** (DEC-0017) — awaiting a 24 h averaged no-preamp sweep to settle vs 207.
- **Vestigial `loopdata.py`** — mounted + `[LoopData]` present but in no active service list; safe to
  remove, not urgent.
- **Errata → dashboard contract (cross-repo, dash S69 Q3).** The owner wants corrected points visibly
  asterisked on the water-balance chart. **Half-solved:** InfluxDB corrected points now carry a sparse
  `rain_qc = 1` flag (DEC-0032, documented in INTERFACES.md), so the dashboard can render the marker
  straight from the data with no parallel list. The dashboard side still has to *read* it.

## Needs a check / housekeeping

- **⚠️ The freeze MECHANISM is still open (DEC-0036) — but the trigger and the fuel are both gone.**
  We never proved exactly which write blocked, and the evidence is gone. Do **not** invent one. What we
  now know for certain: the **trigger** (a bare `docker logs`) is blocked by a hook in both the agent and
  the shell; the **fuel** (StdPrint, ~25 MB/day to stdout) is removed (DEC-0041); and Synology's `db` log
  driver **cannot be size-capped** — it accepts `max-size` and ignores it (measured, and confirmed
  against the literature). If it ever recurs, capture `/proc/1/task/*/wchan` and `/proc/1/fd/*` **before**
  restarting anything.

- **The `db` log driver is uncapped and always will be.** All containers still run on it. That is now an
  accepted risk, not an oversight: the trigger is guarded, weewx's stdout is silent, and `influxdb`
  (~0.5 MB/day) plus HLF/eh-proxy (tens of KB) are not credible wedge candidates. Switching a container
  to `json-file` is the only way to bound its log, and it costs that container's DSM log tab. **Revisit
  only if a container starts generating real stdout volume.**

- **Rotate the exposed WU API key** (NAS `wxcheck.sh`; scrubbed from repo S16, real key still live).
  Owner-acknowledged; **still owed** — and it remains the only known live exposure. **S40 confirmed nothing
  else joined it:** a scan of every blob that ever existed in this repo (333 unique, all refs) for a
  *commented-out* credential — the class DEC-0045 just closed — found **zero**. The gate's hole was real
  but never exploited, so no revocation and no history rewrite is warranted.
- **Unported from the dashboard:** its `.claude/agents/` routing definitions (its DEC-0093).
- **The dashboard has a stranded draft PR (#22, S71 Beaufort)** — found by the new session-start hook on
  its first run. Not ours to merge; flag it when next in that repo.
- **NAS boot task fragility (S32):** after the next DSM update/reboot, verify the `weewx_monitor`
  scheduler task still runs as root (symptom: `sudo: a terminal is required` spam, no pidfile).
- **Docker Hub README auto-sync:** add repo secrets `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` to activate
  `.github/workflows/dockerhub-description.yml` (green no-op until then). Owner action.
- **Branch/tag cleanup:** delete merged `feature/rain-spike-filter` + `s32-reconcile-main`; retire the
  misnomer `rw250-test` image tag.
- **Snow / freezing / no heating tape** (parked, owner's future thread). 2026 = learning year.

## Next session actions (S40 done → S41)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S40 (2026-07-13).** **DEC-0045 — a comment is not an exemption.** The secret gate's `ALLOW (1)`
waved through *any* full-line comment, so a commented-out credential shipped clean into a **public** repo.
The rule was not a blind spot the test missed: **the test asserted it** — two commented credentials sat
under *"must PASS"* and were part of DEC-0039's "28/28, proven". The proof had certified the hole.
`ALLOW (1)` is deleted, comments are scanned like code, **no exemption was added** (the gate's own
illustrative literals moved into the test, where they execute — DEC-0040 applied to the gate itself), and a
**full-history scan of all 333 blobs confirmed the hole was never exploited.** Suite 28 → **41/41**; a
mutation test proves the fix is load-bearing. Also **merged S39's PR #34** to `dev`. See CHANGELOG `[S40]`.

**▶ ON RETURN (S41), in order:**

1. **Release v2.0.7 and deploy prod — one attended window, two jobs at once.** The S39 fix is already on
   `dev` (PR #34 merged in S40). Remaining: `dev` → `main`, tag, **push to Docker Hub**, GitHub release.
   Then recreate prod on `:v2.0.7`. That restart is also what **activates `log_humidity_raw`** (weewx reads
   its config only at startup), so the release and the instrument arm together. Verify after:
   `docker logs --tail 40` shows **no** `--- Logging error ---`, and `weewx.log` now contains
   `weewxd INFO Starting up weewx version 5.4.0` — a line that has never appeared there before.

2. **Then watch for the next humidity spike.** ~2–3/week, clustered **11:00–16:00**. With the capture
   running it logs `rtldavis-luc: humidity_raw= XXXX` — the full `pkt[4]`/`pkt[3]`. That settles the
   nibble question **deterministically**: invert the bytes, re-decode under `0x2`/`0x8`/`0xE` (humidity's
   real single-bit neighbours — *not* solar or UV, which are 2 and 3 bits away), and compare with the
   concurrent archived sensor. The method and the arithmetic are in DEC-0044; **do not re-derive them.**

3. **Do NOT rebuild the coupling filter** (DEC-0044). Its premise failed on our own data. The mechanism
   is the open question, not the threshold.

4. Then the ordinary backlog: **cold-load Fix B (`current.json`)**, **Reception Layer B (DEC-0024)**, and
   the **always-on duplicate-frame counter (DEC-0035)**.

**Still parked for Fable, not ours to move:** the cross-repo / 4th-project etiquette question
(`docs/handoffs/S38-cross-repo-architecture.md` §Etiquette).

**Physical, not software (DEC-0042):** inspect the tipping bucket, the reed switch and its wiring. The
phantom rainRate is an ISS sensor artifact — condensation trips the rate timer without tipping the
bucket. **A third event is predictable on the next calm, saturated, cooling night**, which is a free test.

**Watch:** replies on [lheijst#22](https://github.com/lheijst/weewx-rtldavis/pull/22),
[issue #15](https://github.com/lheijst/weewx-rtldavis/issues/15) and
[david-lutz#1](https://github.com/david-lutz/weewx-influx2/pull/1).

**Also owed:** rotate the exposed WU API key (NAS `wxcheck.sh`) — the only known live exposure. The
dashboard has a stranded draft PR (#22) that our session-start hook found; flag it when next in that repo.

**Live access:** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in gitignored
`docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use `env -u GH_TOKEN` for any
`git push`. **The driver is BAKED — never `scp` it (DEC-0031); `influx.py` IS mounted, so scp IS correct
for that one.** **`docker logs` without `--tail` is now blocked by a hook** in both the agent and the
shell — it is no longer merely a written rule (DEC-0040).
