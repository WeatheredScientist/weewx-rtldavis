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

> **Current session: S36** (2026-07-12) — **v2.0.4 SHIPPED.** SensorQC (DEC-0029) is finally live in
> prod after three sessions staged and never deployed it; the *reason* it kept not shipping was found
> and killed (a compose bind-mount laying the stock driver over the baked one — DEC-0031). All three
> phantom rain events are corrected in both stores (ERR-0001 + new ERR-0002, DEC-0032). The secret
> gate, which had never actually worked, is fixed. Full story: CHANGELOG `[S36]`.

_Last updated: 2026-07-12 (S36)._

---

## Active thread

> **▶ Resume here (S36 → S37).** Prod is on **`:v2.0.4`** and healthy (reception 75–80%,
> `RestartCount: 0`, `sensor_qc True`). Nothing is on fire. The one thing that needs *watching* rather
> than doing: **the first live SensorQC rejections.** Expect `rejecting implausible value` in
> `weewx.log` at ~0.4+/day, clustering at night. Zero so far (deployed 15:49 EDT). If a week passes with
> **zero** rejections, be suspicious — the humidity evidence says they should appear.
>
> Then the promotion: **merge `dev` → `main`, tag `v2.0.4` + a new `prod-baseline`, push the image to
> Docker Hub, cut the GitHub release.** Deliberately held until v2.0.4 has ridden clean for a few days.

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
  corruptions co-occurring is a strong clue, not a coincidence. **Don't guess — the `debug_rtld = 2`
  capture will record the raw type-0x5 frames if it recurs.** This also matters for what we propose
  upstream: `rain_delta_tips` guards the counter and does **nothing** for the rate, whose failure mode
  is a corrupted "no rain" sentinel (`time_between_tips_raw == 0x3FF`).
- **The CRC question is ANSWERED (DEC-0033) — what's left is a DECISION, not research.** The glitches
  are CRC-valid multi-bit corruption, most likely spurious near-duplicate frames from the rtldavis Go
  demodulator (one transmission decoded twice). Confirmed from raw packets in upstream issue
  `lheijst/weewx-rtldavis#15`, open since Oct 2022 with three users reporting the same symptom class.
  **An upstream comment is drafted but NOT posted and deliberately held out of git** (public repo):
  `docs/upstream/rain-wraparound-bug.md`, gitignored. Owner is iffy on posting and wants (a) the prose
  rewritten in his own voice — the draft reads as Claude, not as him — and (b) our own confirmation of
  the duplicate-frame fingerprint first. **Do not post without an explicit go.**
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
- **`qc-capture` is still running on the NAS** (`/volume1/docker/weewx-rtldavis/qc-capture/`, a detached
  `sh` loop appending loop packets to `loop-raw.jsonl`, started by dash S69). It is now capturing
  *post*-fix data. **Harvest it or kill it** — don't leave it running unowned; it won't survive a reboot.
- **Gain 372, interim** (DEC-0017) — awaiting a 24 h averaged no-preamp sweep to settle vs 207.
- **Vestigial `loopdata.py`** — mounted + `[LoopData]` present but in no active service list; safe to
  remove, not urgent.
- **Errata → dashboard contract (cross-repo, dash S69 Q3).** The owner wants corrected points visibly
  asterisked on the water-balance chart. **Half-solved:** InfluxDB corrected points now carry a sparse
  `rain_qc = 1` flag (DEC-0032, documented in INTERFACES.md), so the dashboard can render the marker
  straight from the data with no parallel list. The dashboard side still has to *read* it.

## Needs a check / housekeeping

- **⚠️ FORK-IDENTITY / PROVENANCE AUDIT — own S37 session, prompt below.** We are a **fork of a fork of a
  fork** and we don't say so anywhere. The real chain, verified from the Dockerfile (we build from
  **Vince Skahan's `src.tgz`**, not from Luc's repo directly):
    - *Go decoder:* `bemasher/rtldavis` → `lheijst/rtldavis` → bundled in `weewx-contrib` src.tgz → us
    - *Driver:* `matthewwall/weewx-sdr` + `weewx-meteostick` → merged by **lheijst** into weewx-rtldavis
      v0.20 → repackaged by **Skahan** (`weewx-contrib/weewx-rtldavis`) → **patched by us**
    - plus `steve-m/librtlsdr`, `jpoirier/gortlsdr`, **kobuki** (`calc_wind_speed_ec`), and
      **`david-lutz/weewx-influx2`** — which we also **patched** (Py-3.14 `e.read().decode()`).
  So there are **several modified upstream works** here, not just `rtldavis.py`. Scope:
    1. **GPLv3 §5(a) gap (real, not a nit):** a modified work must "carry prominent notices stating that
       you modified it, and giving a relevant date." `rtldavis.py` carries only *upstream's* header
       (`Copyright 2019 Matthew Wall, Luc Heijst`) and says nothing about our 2026 changes. Same for the
       other vendored/patched files. **Follow Luc's own example** — his header documents that his driver
       is a merge of Matthew Wall's, with links. Inherit the pattern, add our line.
    2. **`DRIVER_VERSION = '0.20'` misrepresents us** — we log as stock upstream while carrying
       rain_delta_tips, SensorQC, H1/H2/M3, windDir, dewpoint honest-null. Use `'0.20+ws.1'` and log
       "(fork of lheijst 0.20)". Same class of dishonesty as the compose clobber (DEC-0031): the
       artifact asserts one thing and does another.
    3. **`CHANGES-FROM-UPSTREAM.md`** — every divergence, with DEC links. Highest-value artifact: it is
       both the "playing nice" document and the checklist for *shrinking* the fork.
    4. **README opening rewrite** — line 3 currently reads as though we ship *Luc's* driver. We don't.
       Say plainly: unofficial Docker distribution, patched driver, not affiliated, links upstream.
    5. **Upstream-first posture:** to contribute, `gh repo fork lheijst/weewx-rtldavis` **separately** and
       send ONE focused PR (the rain fix), not our whole divergence. Our repo correctly stays a normal
       repo, not a GitHub fork — it is a *distribution*, not a fork of the driver.
  **Keep the repo/image name** (published, GPLv3, attribution intact; renaming breaks every
  `docker pull`). This is about honesty, not rebranding.
- **(superseded detail) Our driver lies about its identity (owner question, S36).** `DRIVER_VERSION = '0.20'` — we log as
  **stock upstream v0.20** while carrying the rain-glitch filter (DEC-0021), SensorQC (DEC-0029), the
  H1/H2/M3 reception fixes, the windDir fix and dewpoint honest-null. **None of that exists upstream.**
  We are a fork that hasn't admitted it, and the log line misleads anyone debugging — including us, and
  including anyone we help on upstream issue #15. Same class of dishonesty as the compose clobber: the
  artifact says one thing and does another. **Fix:** (1) version it as a fork (`'0.20+ws.1'` or similar);
  (2) state the relationship plainly in the README (a Docker distribution of Luc Heijst's driver, with
  these patches, not affiliated — GPLv3, attribution already intact); (3) shrink the delta by upstreaming
  (the issue #15 contribution is exactly this). **Keep the repo/image name** — it's published, and
  renaming breaks every downstream `docker pull`.

- **⚠️ PROD IS IN A DEBUG STATE — revert when the Lloyd test is done (S36).** To capture raw frames we
  set, in the live `weewx.conf`: `[Rtldavis] debug_rtld = 2` and `[Logging][[loggers]][[[user]]]
  level = DEBUG`. This adds log volume (raw `data:` line per packet, ~21/min). **Revert both to
  `1` / `INFO` and restart** (`docker kill` + `docker start`) once the test concludes. Backup:
  `weewx-data/weewx.conf.bak-S36-debugrtld-*`.
- **The Lloyd test (DEC-0033) is RUNNING.** `ops/find_duplicate_frames.py` looks for two frames from the
  same transmitter <2 s apart — impossible for a real ISS (it transmits every ~2.5 s) and the fingerprint
  LloydR posted upstream (262 µs apart, 4 bits different, both CRC-valid). The driver logs the raw
  `data:` line *before* the CRC check, so spurious frames are visible **even when they fail CRC** — so
  this should answer in hours, not weeks. Run it against the accumulating log:
  `python3 /volume1/docker/weewx-rtldavis/find_duplicate_frames.py /volume1/docker/weewx-rtldavis/logs/weewx.log`
  First pass (5 min, 34 frames): **0 suspicious pairs** — far too little data to mean anything yet.
  If pairs appear, we can confirm the mechanism on our own hardware and post to upstream issue #15.


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

## Next session actions (S36 done → S37)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S36 (2026-07-12):** v2.0.4 deployed + verified (SensorQC live); DEC-0031 (driver is baked,
never mounted — killed the compose clobber that had shipped the stock driver to every public user);
DEC-0032 (retrospective correction + in-band `rain_qc` flag); DEC-0033 (the CRC question, answered, with
a retraction recorded); ERR-0002 logged and corrected; ERR-0001's InfluxDB correction finally applied;
secret gate fixed (it had never worked); doc staleness swept; cross-repo handoff written. See
CHANGELOG `[S36]`.

**▶ ON RETURN (S37), in order:**
1. **Check the two numbers that tell you whether v2.0.4 is working:**
   `grep -c "rejecting implausible" weewx.log` (expect ~0.4+/day, nocturnal — **zero after a week is
   suspicious, not good**), and the Lloyd test:
   `python3 /volume1/docker/weewx-rtldavis/find_duplicate_frames.py /volume1/docker/weewx-rtldavis/logs/weewx.log`
2. **Then REVERT the debug state** (see housekeeping — `debug_rtld` → 1, `user` logger → INFO, restart).
   Don't leave prod logging raw frames indefinitely.
3. **Promote v2.0.4** once it has ridden clean for a few days: merge `dev` → `main`, tag `v2.0.4` +
   a new `prod-baseline`, **push the image to Docker Hub, cut the GitHub release.** The Docker Hub push
   is the step that actually fixes downstream users — until it lands, everyone installing this extension
   still gets the stock driver via the old compose file (DEC-0031).
4. **Decide on the upstream post** (owner call — see the CRC thread above).
5. Then: cold-load Fix B (`current.json`), the temp/humidity coupling filter, Reception Layer B (v2.0.5).

**Cross-repo:** `docs/handoffs/S36-to-eaglehunt-dashboard.md` is written and answers all three of
dashboard S69's open questions. **The dashboard should read the new `rain_qc` flag** (DEC-0032,
INTERFACES.md) to render corrected-point markers. It also carries a reciprocal finding: the dashboard's
own secret gate still has two live holes we closed here.

**Live access:** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in gitignored
`docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use `env -u GH_TOKEN` for
any `git push` (keyring token, not the PAT). **The driver is BAKED — never `scp` it (DEC-0031).**
