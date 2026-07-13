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

> **Current session: S38** (2026-07-13) — **v2.0.6 IS ON DOCKER HUB.** The downstream harm is over:
> every `docker pull` now gets the patched driver (DEC-0031), the console-handler fix (DEC-0036) **and
> StdPrint removed (DEC-0041)** — the last was the *real* stdout writer, ~25 MB/day, and v2.0.5 had
> missed it. The secret gate is **proven** rather than merely green (DEC-0039), and the cross-repo
> question is answered: the gap is an **enforcement** gap, not a documentation gap — no master repo
> (DEC-0040). **Prod was fixed and restarted; stdout is now silent.** Full story: CHANGELOG `[S38]`.

_Last updated: 2026-07-13 (S38)._

---

## Active thread

> **▶ Resume here (S38 → S39). Prod is healthy.** It WAS touched: `StdPrint` removed from the live
> `weewx.conf` and the container restarted (DEC-0041). Verified after: stdout growth **0 lines/60 s**
> (was ~36), `Influx: Published record` continuing, `RestartCount: 0`. Backup:
> `weewx.conf.bak-S38-stdprint-*`.
>
> **One thing is owed, and one thing is waiting on the owner:**
>
> 1. **A catch-up deploy of `:v2.0.6` to prod** — attended window, `:v2.0.4` is the rollback. Prod still
>    runs the **`:v2.0.4` image** (its *config* is fixed, but the image is two patches behind). The
>    behavior delta is now **nil** — the config fix already did the work that matters here.
>    **`prod-baseline` has NOT been moved** and must not be until this happens.
> 2. **The upstream contributions are PREPARED but NOT SENT.** Both upstreams forked, both fixes
>    committed, pushed and verified; **no PR opened, nothing posted.** Drafts in the owner's voice at
>    `docs/upstream/` (gitignored). One command each opens them — see that folder. **Explicit go still
>    required.**

## Open threads (not yet shipped)

- **⚠️ Prod runs the `:v2.0.4` IMAGE (DEC-0038/0041, deliberate).** Published `:v2.0.6` ≠ running
  `:v2.0.4`. Prod's *config* is already fixed by hand (StdPrint removed, no console handler), so the
  behavior delta is nil; the image carries those same fixes for **downstream users**, who cannot hand-edit
  our config. Catch-up deploy owed; do not move `prod-baseline` until it lands.

- **⚠️ Prod's bind-mounted `influx.py` has DRIFTED from the repo — OWNER DECISION PENDING.** Running copy
  md5 `8b0d05b3`; repo's is `5f58c204`. The live one still carries `VERSION = "0.20"` (not `0.20+ws.1`),
  the unconditional `ssl._create_unverified_context()`, and the per-record `loginf` calls that spam
  `weewx.log` on every record. **Not a live exposure** — the endpoint is `http://influxdb:8086`, so the
  TLS branch is never taken — but it is the DEC-0031 class again (repo says one thing, prod runs another),
  and it becomes a real hazard the moment anyone points this at InfluxDB Cloud. **`influx.py` IS
  bind-mounted**, so unlike the driver an `scp` + pyc-clear + restart IS the correct deploy here.
- **The log-driver decision — needs ONE command from the owner.** Synology's `db` driver **cannot be
  capped** (proven: `max-size=1m`, 200k lines emitted, 200k retained; it is a proprietary driver and the
  option is *unsupported*, not just undocumented). `json-file` + caps is the only way to bound a log
  here, and it **costs the DSM Container Manager log tab** for that container. The driver is a
  **per-container** choice, so bound only the noisy ones — but nobody knows which those are. Needs root:
  `for c in $(docker ps -q); do printf '%s  ' "$(docker inspect -f '{{.Name}}' $c)"; sudo du -h "$(docker inspect -f '{{.LogPath}}' $c)"; done`
  weewx is no longer a candidate (console now `WARNING`). The unknowns are `hyperlocal-forecast-api`,
  `eh-proxy`, `influxdb`. **The freeze *trigger* is already gone** — the `docker logs` hook blocks it —
  so this is defense in depth, not urgent.
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

- **✅ CLOSED IN S38:** v2.0.5 published to Docker Hub (`v2.0.5` + `latest`, 12:55) — **the downstream
  hazard from DEC-0031 *and* DEC-0036 is fixed for every new install**; S37's stranded draft PR #23
  merged; the secret gate hardened **and proven** (DEC-0039); the cross-repo architecture decided
  (DEC-0040); `enforce_admins: true` on `main` + `dev`; CI now runs the 67 tests; both upstream forks
  prepared.

- **✅ CLOSED IN S37:** debug state reverted; the Lloyd test **answered** (DEC-0035); the fork-identity
  audit **done** (DEC-0034); `qc-capture` gone.

- **The guards live in `~/.claude/hooks/` — global, all three repos, zero session-boot cost (DEC-0040).**
  `docker-guard.sh` (`PreToolUse`) blocks bare `docker logs` + `docker stop`; `eaglehunt-status.sh`
  (`SessionStart`) surfaces draft PRs / stranded branches / uncommitted work across all three repos.
  **Both ship with tests. If you change one, run its test** — that is the whole point (DEC-0039 §3).

- **A `.zshrc` guard for the human is still owed.** The Claude hook only guards the agent, and we never
  established who ran the bare `docker logs` that froze prod — it may have been the owner at a terminal.

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

## Next session actions (S38 done → S39)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S38 (2026-07-13):** merged S37's **stranded draft PR #23** (it had never landed on `dev`);
**shipped `v2.0.5` + `latest` to Docker Hub** — the downstream stock-driver (DEC-0031) and
console-handler-freeze (DEC-0036) hazards are fixed for every new install; **DEC-0038** an image tag
denotes exactly one tree (why v2.0.5, not a second v2.0.4); **DEC-0039** the secret gate hardened and
**proven** with a planted-payload harness (28/28), now in CI, plus the 67 unit tests CI never ran;
**DEC-0040** the cross-repo gap is an **enforcement** gap — no master repo; global hooks in
`~/.claude/hooks/` (docker guard 19/19, cross-repo session-start check); `enforce_admins: true` on
`main` + `dev`; both upstream forks prepared and verified. See CHANGELOG `[S38]`.

**▶ ON RETURN (S39), in order:**

1. **Catch-up deploy `:v2.0.5` to prod** (attended; `:v2.0.4` = rollback). Then **move
   `prod-baseline`** — it was deliberately NOT moved (DEC-0038), so `main` is currently ahead of the
   station. Behavior delta is nil; this is bookkeeping, but it is the last open thread from the release.

2. **The upstream contributions — owner's call, one command each.** Everything is staged and verified;
   **nothing has been posted.** Read `docs/upstream/rain-wraparound-bug.md` and
   `docs/upstream/influx2-fixes.md` (gitignored), both written in the owner's voice. The rain fix is
   proven against LloydR's own counter values from issue #15. The influx2 set is led by a **silent TLS
   verification bypass** affecting every user of that uploader on https. **Explicit go required.**

3. **The log-driver decision** — one `sudo du` command (see Open threads). Not urgent: the freeze
   *trigger* is now blocked by the hook. This is defense in depth.

4. **A `.zshrc` guard** so the human is covered too, not just the agent.

5. Then: cold-load Fix B (`current.json`), the temp/humidity coupling filter, Reception Layer B, and the
   always-on duplicate-frame counter (DEC-0035).

**Cross-repo:** `docs/handoffs/S38-cross-repo-architecture.md` carries the DEC-0040 recommendation and
two things the other repos need to act on: (a) the **dashboard's own hardened gate still has
free-floating escape hatches** — steal payloads 8–12 from our `scripts/test_check_secrets.sh`, and do
**not** port our regex verbatim; (b) **hyperlocal-forecast has no secret gate at all**, and both repos
run uncapped containers on the same `db` log driver that wedged.

**Live access:** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in gitignored
`docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use `env -u GH_TOKEN` for any
`git push`. **The driver is BAKED — never `scp` it (DEC-0031).** **Never run `docker logs` without
`--tail N`** — now enforced by a hook, not just a rule (DEC-0040).
