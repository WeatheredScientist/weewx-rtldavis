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

> **▶ Resume here (S38 → S39). Everything is clean. Exactly TWO things are open, and both are the
> owner's.**
>
> Prod runs **`:v2.0.6`**, `main` == prod (`prod-baseline-20260713`), the image is published, both
> upstream PRs are **open**, and the guards are installed and tested. Nothing is half-done and nothing is
> stranded.
>
> **1. Cross-repo etiquette — the 4th-project question (owner, needs a decision).**
>    DEC-0040 settled the *enforcement* half: no master repo, guards in `~/.claude/hooks/`, share the
>    payload test not the regex. What it did **not** settle is **etiquette** — the human/agent protocol
>    *between* repos: who may touch whose prod, how a finding in repo A is handed to repo B, what an
>    agent may do unattended in a repo it is not "in". The owner wants short, concrete advice, and is
>    leaning toward a small coordinating 4th project. **See `docs/handoffs/S38-cross-repo-architecture.md`
>    §Etiquette.** This is a governance decision, not a code one.
>
> **2. The issue-#15 thread response — drafted, awaiting the owner's review for tone/content.**
>    `docs/upstream/issue-15-response.md` (gitignored). The **PR is already open and needs nothing**
>    ([lheijst#22](https://github.com/lheijst/weewx-rtldavis/pull/22)); this is the *thread* half —
>    explaining the mechanism to the three people who have lived with it since 2022. It credits LloydR's
>    packet dumps, tells gary-hammer his 64 mph gusts are the same bug in a different field, and is
>    honest that the rain-*rate* half is still unexplained. **Owner posts it, or says go.**

## Shipped and closed in S38 — nothing to do here

- **v2.0.5 → v2.0.6 on Docker Hub** (`latest` too). Downstream users get the patched driver (DEC-0031),
  the console handler at `WARNING` (DEC-0036) **and StdPrint removed** (DEC-0041 — the real stdout
  writer, ~25 MB/day, which v2.0.5 missed).
- **Prod is on `:v2.0.6`**, recreated 2026-07-13 11:09 EDT. Verified: `driver version is 0.20+ws.1 (fork
  of lheijst 0.20)`, `sensor_qc True`, `influx service version 0.20+ws.1`, **stdout silent** (0 LOOP
  lines), every uploader publishing, `RestartCount: 0`. `prod-baseline-20260713` tagged — **DEC-0011's
  `main` = production truth invariant is restored.**
- **`influx.py` drift closed.** Prod's bind-mounted copy now matches the repo (md5 `5f58c204`).
- **Both upstream PRs OPEN:** [lheijst#22](https://github.com/lheijst/weewx-rtldavis/pull/22) (rain
  wraparound), [david-lutz#1](https://github.com/david-lutz/weewx-influx2/pull/1) (TLS verification + 4).
- **The enforcement layer is live and tested** (DEC-0040): `~/.claude/hooks/docker-guard.sh` (19/19),
  `~/.claude/hooks/eaglehunt-status.sh` (finds stranded draft PRs across all three repos), and a
  `.zshrc` guard for the human (6/6). `enforce_admins: true` on `main` + `dev`; CI runs the 67 tests.
- **The secret gate is proven** (DEC-0039): 28/28 planted payloads, in CI, ahead of the scan.
- **47 MB reclaimed** — `/weewx`, a container dead since 2026-05-04, still held the largest `log.db` on
  the NAS. Dead containers keep their log store forever.

## Open threads (backlog — none of these block anything)

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

- **✅ CLOSED IN S38:** see "Shipped and closed" above. Prod on `:v2.0.6`, `main` == prod, both upstream
  PRs open, guards installed + tested, secret gate proven, 47 MB reclaimed, `influx.py` drift closed.

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
  Owner-acknowledged; **still owed** — and now the only known live exposure.
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

## Next session actions (S38 done → S39)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S38 (2026-07-13):** merged S37's stranded draft PR #23; **shipped `v2.0.5` then `v2.0.6`**
to Docker Hub; **DEC-0038** (an image tag denotes exactly one tree), **DEC-0039** (the secret gate,
hardened and *proven* — 28/28, in CI), **DEC-0040** (the cross-repo gap is an *enforcement* gap — no
master repo; guards in `~/.claude/hooks/`), **DEC-0041** (**StdPrint removed** — the real stdout writer
that v2.0.5 missed); prod deployed to `:v2.0.6` and `prod-baseline-20260713` tagged; `influx.py` drift
closed; both upstream PRs opened; `enforce_admins: true`; CI now runs the 67 tests. See CHANGELOG `[S38]`.

**▶ ON RETURN (S39) — only two things are open, and both are the owner's:**

1. **Cross-repo ETIQUETTE — the 4th-project question.** DEC-0040 settled *enforcement*; it did not settle
   the human/agent protocol *between* repos. Short concrete advice is in
   `docs/handoffs/S38-cross-repo-architecture.md` §Etiquette. Owner decision.

2. **Post the issue-#15 response** — `docs/upstream/issue-15-response.md` (gitignored), pending the
   owner's review for tone/content. **The PR is already open and needs nothing**
   ([lheijst#22](https://github.com/lheijst/weewx-rtldavis/pull/22)).

**Then, at leisure (nothing is blocked):** cold-load Fix B (`current.json`); the temp/humidity coupling
filter; Reception Layer B (DEC-0024); the always-on duplicate-frame counter (DEC-0035); and the rainRate
15-minute hold, which remains the most interesting unexplained thing in the data.

**Watch for:** replies on the two upstream PRs. `lheijst` was active as recently as 2026-07-09;
`david-lutz` has been quiet since 2023, so that one may simply sit.

**Live access:** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in gitignored
`docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use `env -u GH_TOKEN` for any
`git push`. **The driver is BAKED — never `scp` it (DEC-0031); `influx.py` IS mounted, so scp IS correct
for that one.** **Never run `docker logs` without `--tail N`** — now blocked by a hook in both the agent
and the shell, not merely written down (DEC-0040).
