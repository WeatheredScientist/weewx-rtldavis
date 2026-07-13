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

> **Current session: S37** (2026-07-12 → 07-13) — **a 7-hour prod outage, and the CRC question answered.**
> weewx froze solid for 7h18m (DEC-0036, ERR-0003 — recovered, gap backfilled). The fork-identity /
> provenance audit landed (DEC-0034). The duplicate-frame mechanism is **confirmed on our hardware**
> (DEC-0035) — and the test that first said otherwise was broken. Full story: CHANGELOG `[S37]`.

_Last updated: 2026-07-13 (S37)._

---

## Active thread

> **▶ Resume here (S37 → S38). Prod is healthy** — recovered 07:12 EDT 2026-07-13, `RestartCount: 0`,
> `sensor_qc True`, debug state reverted (`debug_rtld = 1`, `user` logger `INFO`).
>
> **Two things are NOT done and are the top of the list:**
>
> 1. **Promote v2.0.4** — `dev` → `main`, tag + `prod-baseline`, **Docker Hub push**, GitHub release.
>    Still the highest-value outstanding item: until the image ships, every downstream user is running
>    the **stock driver** (DEC-0031). Now doubly so — the published image also carries the
>    console-handler hazard that DEC-0036 fixes in `logging.additions`.
> 2. **The upstream post is NOT sent, by owner instruction.** The owner wants the problem fully worked
>    out, then the prose tuned to strike a balance between technical content and human warmth — the
>    draft still reads as Claude, not as him. **DEC-0035 removes the last technical blocker** (he wanted
>    our own confirmation of the duplicate-frame fingerprint before posting; we now have it). Do not post
>    without an explicit go.

## Open threads (not yet shipped)

- **Promote v2.0.4** — `dev` → `main`, tag + `prod-baseline-2026MMDD`, Docker Hub push, GitHub release.
  **The Docker Hub push matters more than usual:** the published compose file was mounting the stock
  driver over the baked one (DEC-0031), so *every downstream user* has been running an unpatched driver.
  The fix is only real for them once the new image + compose are published.
- **⚠️ rainRate's 15-minute hold — OPEN, and the best lead we have (S37).** The phantom rain also
  produced a phantom rain *RATE* (peaks 4.736 / 4.216 in/hr, `rain = 0.0` throughout). **The data is
  corrected** in both stores (S36, 2nd pass — see DATA_ERRATA), but the *mechanism* is not explained: a
  single corrupt packet gives ONE bad reading, yet we see ~16 min of a *stable* rate (raw tip-interval
  drifting only ~7.6 s → 9.6 s), starting at the exact phantom timestamps, twice. That shape resembles
  the **Davis rain-rate timeout** (ISS holds a rate ~15 min after tips), which would mean the ISS itself
  held a non-zero rate state — which DEC-0033's spurious-frame model does **not** explain. `rain` (type
  0xE counter) and `rainRate` (type 0x5 `time_between_tips`) are **separate messages**, so the two
  corruptions co-occurring is a strong clue, not a coincidence. **Don't guess.** The `debug_rtld = 2` capture is
  **off** (DEC-0036: leaving prod at DEBUG is what set the trap for the 7 h freeze). The right instrument
  is the **always-on duplicate/rain-frame counter** proposed in DEC-0035 — one INFO line per archive
  period — not another open-ended debug expedition. This also matters for what we propose
  upstream: `rain_delta_tips` guards the counter and does **nothing** for the rate, whose failure mode
  is a corrupted "no rain" sentinel (`time_between_tips_raw == 0x3FF`).
- **The CRC question is CLOSED (DEC-0033 + DEC-0035).** The demodulator double-decodes a single RF
  burst: **61 duplicate frames in 2 h, median 2.0 ms after the original, ~722/day** — the ISS cannot
  transmit twice 2 ms apart. Confirmed on our own hardware, so the owner's precondition for posting
  upstream is met. **What remains is a WRITING task, not research:** the draft
  (`docs/upstream/rain-wraparound-bug.md`, gitignored) must be rewritten in the owner's voice — balancing
  technical substance with human warmth — and **posted only on an explicit go.**
- **Cross-sensor consistency filter (S33 follow-up #2) — now has a concrete, validated discriminator.**
  From dash S69: *a humidity move >6 %/min with temperature essentially flat is physically impossible*
  (a real moist parcel is also a cooler one). It correctly spares the 2026-05-23 gust front, where temp
  and humidity moved *together*. 3-for-3 on the bad events, 0 false positives. Design for v2.0.5.
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

- **✅ CLOSED IN S37:** the debug state is reverted (`debug_rtld = 1`, `user` logger `INFO`); the Lloyd
  test is **answered** (DEC-0035); the fork-identity audit is **done** (DEC-0034); `qc-capture` on the NAS
  is **gone** (it did not survive the restart — nothing to harvest, nothing to kill).

- **⚠️ NEW — the published image carries a hazard our prod does not (DEC-0036).** `logging.additions`
  (baked into the image) defines a console handler at **INFO**; the live bind-mounted `weewx.conf` has
  **no console handler at all**. The repo and the running station have **drifted**. Every downstream user
  is logging INFO to stdout, which is the DEC-0036 freeze hazard. Fixed in `logging.additions` (→
  `WARNING`) but **it only reaches users when v2.0.4 is pushed to Docker Hub.** Same shape as DEC-0031.

- **⚠️ The freeze mechanism is OPEN (DEC-0036).** Trigger identified (a bare `docker logs`, no `--tail`,
  wedged the Synology daemon's log path for that container). The exact blocked write is **not** known and
  the evidence is gone. Do not invent one. Mitigations are banked. If it recurs, capture
  `/proc/1/task/*/wchan` and `/proc/1/fd/*` **before** restarting anything.

- **Rotate the exposed WU API key** (NAS `wxcheck.sh`; scrubbed from repo S16, real key still live).
  Owner-acknowledged; **still owed** — and now the only known live exposure.
- **Unported from the dashboard:** its `.claude/agents/` routing definitions (its DEC-0093). The
  docs-diet half (DEC-0081) landed here as DEC-0030 in S35.
- **NAS boot task fragility (S32):** after the next DSM update/reboot, verify the `weewx_monitor`
  scheduler task still runs as root (symptom: `sudo: a terminal is required` spam, no pidfile).
- **Docker Hub README auto-sync:** add repo secrets `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` to activate
  `.github/workflows/dockerhub-description.yml` (green no-op until then). Owner action.
- **Branch/tag cleanup:** delete merged `feature/rain-spike-filter` + `s32-reconcile-main`; retire the
  misnomer `rw250-test` image tag (nothing references it now that compose is fixed).
- **Snow / freezing / no heating tape** (parked, owner's future thread) — cold-weather failure modes we
  haven't designed for. 2026 = learning year.

## Next session actions (S37 done → S38)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S37 (2026-07-12 → 07-13):** health check + debug revert; **DEC-0034** fork-identity /
provenance audit (modification notices on all four patched upstream files, `0.20+ws.1`,
`CHANGES-FROM-UPSTREAM.md`, README rewrite); **DEC-0035** the duplicate-frame mechanism CONFIRMED here
(~722/day) *and* the broken test that first denied it, fixed; **DEC-0036** the 7h18m freeze (recovered,
mitigations banked, mechanism open); **DEC-0037** corrections must propagate to derived fields;
**ERR-0003** the gap, backfilled; **ERR-0001 amendment** — `dayRain_in`/`rain24_in`/`hourRain_in` still
carried the phantom, now recomputed. See CHANGELOG `[S37]`.

**▶ ON RETURN (S38), in order:**

1. **CROSS-REPO ARCHITECTURE — owner decision, do this FIRST.** It gates the other two repos.
   `docs/handoffs/S37-to-all-projects-stdout-freeze.md` frames it: **three shared assets have each now
   caused a cross-repo incident** — the NAS Docker daemon (DEC-0036), the driver-vs-image mismatch
   (DEC-0031), and the secret gate (green-but-blind in *both* repos, independently). **None belongs to
   any one repo, and no repo's session-start read covers the gap between them.** Options on the table:
   a shared `ops/`-`infra/` repo owning NAS-level truth; a vendored CONVENTIONS fragment (cheap, drifts —
   and drift *is* DEC-0031 and DEC-0036); or status quo + handoffs (reactive: every lesson costs one
   outage in one repo before the others hear). **Decide the model, then propagate.**

2. **Promote v2.0.4** — `dev` → `main`, tag + `prod-baseline`, **Docker Hub push**, GitHub release.
   Carries **two** downstream fixes now: the **stock driver** still shipping to every user (DEC-0031)
   *and* the **console-handler freeze hazard** (DEC-0036) that our own prod escaped only through config
   drift. Neither is fixed for anyone until the image lands.

3. **Upstream contribution (provenance follow-through).** DEC-0034 made us honest *internally*; the
   outward half is unfinished. Fork `lheijst/weewx-rtldavis` **separately** and send **one focused PR**
   (the rain-counter wraparound), not our whole divergence. The research is done (DEC-0035); what remains
   is **prose in the owner's voice** — technical substance balanced with human warmth. Draft is gitignored
   at `docs/upstream/rain-wraparound-bug.md`. **Do not post without an explicit go.**
   Same for `david-lutz/weewx-influx2` (four real bugs, incl. a TLS-verification fix).

4. **The five secret-gate holes** the dashboard found (their S70 §3). Our repo is **public**, so these
   matter more here. Steal their `test_check_secrets.sh` harness (plant payloads that MUST be caught).
   **Do not port their anchor verbatim** — theirs runs on raw lines, ours on `grep -n` output; a verbatim
   port silently re-opens the hole it closes.

5. Then: cold-load Fix B (`current.json`), temp/humidity coupling filter, Reception Layer B, and the
   always-on duplicate-frame counter (DEC-0035, replaces ever running prod at `debug_rtld = 2` again).

**Live access:** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in gitignored
`docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use `env -u GH_TOKEN` for any
`git push`. **The driver is BAKED — never `scp` it (DEC-0031).** **Never run `docker logs` without
`--tail N`** — a bare one wedged the daemon and froze prod for 7 hours (DEC-0036).
