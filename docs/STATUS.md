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
- **The CRC question — the true root cause, and the owner wants a community bug report.** How is
  multi-bit corruption passing `_check_crc()` at all? Three rain phantoms are clean 2⁶/2⁷ flips and the
  humidity glitches are clean 2⁷/2⁸ flips — all CRC-valid. SensorQC is a *symptom* filter; the decoder
  accepting corrupt frames is the disease. This is the highest-value remaining thread.
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

**✅ Done in S36 (2026-07-12):** v2.0.4 deployed + verified; DEC-0031 (driver is baked, never mounted);
DEC-0032 (retrospective correction + in-band `rain_qc` flag); ERR-0002 logged and corrected; ERR-0001's
InfluxDB correction finally applied; secret gate fixed; doc staleness swept. See CHANGELOG `[S36]`.

**▶ ON RETURN (S37):**
1. **Check the rejection log first** — `grep -c "rejecting implausible" weewx.log`. This is the single
   number that tells you whether v2.0.4 is doing its job. Nonzero and nocturnal = working as designed.
2. **Promote v2.0.4** if it has ridden clean (see Active thread) — merge, tag, Docker Hub, release.
3. Then pick up **the CRC bug report** (highest value) or the **temp/humidity coupling filter** (v2.0.5).

**Live access:** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in gitignored
`docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use `env -u GH_TOKEN` for
any `git push` (keyring token, not the PAT). **The driver is BAKED — never `scp` it (DEC-0031).**
