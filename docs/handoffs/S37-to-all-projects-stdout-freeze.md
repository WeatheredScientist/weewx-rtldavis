# Handoff — weewx-rtldavis S37 → eaglehunt-weather-dashboard, hyperlocal-forecast

**Written:** 2026-07-13, weewx-rtldavis session **S37**.
**Audience:** any project of ours that runs a container on the Synology NAS.
**Status:** **advisory — we have made NO changes in your repos.** Read this, verify it against your own
stack, and decide for yourselves. (We are following our own DEC-0031 lesson the hard way: *infrastructure
advice across a repo boundary must be verified in the target repo before it is given, not reasoned about
from the outside.* This document is a lead, not a patch.)

---

## The short version

On 2026-07-12 at 23:53:45, **weewx froze solid for 7 hours 18 minutes.** It did not crash. The process
stayed alive, the container reported `Up`, and **no error or traceback was ever written** — because the
thing that was stuck was the logging itself.

**This is not a weewx bug. It is a container-on-Synology hazard, and `hyperlocal-forecast-api` and
`eh-proxy` are exposed to the same shape.**

## What we know for certain

- weewx's main thread was blocked in kernel state **`pipe_wait`**.
- The Docker daemon's path for **that one container** was wedged: `docker logs`, `docker exec` and
  `docker kill` all hung against it. The other three containers were completely healthy the whole time.
- A **bare `docker logs <container>` with no `--tail`** had been hung since the previous day. Synology's
  Docker log store is a **SQLite `log.db`**.
- Killing the hung clients did **not** free it. Only `sudo synopkg restart ContainerManager` did.
- Recovery required a **full Docker daemon restart**, which bounced all four containers.

## What we do NOT know — stated plainly

Our first diagnosis was *"weewx's INFO-level stdout logging filled the container's stdout pipe."* **We
checked, and it was wrong** — the live config had no console handler at all, so weewx was not writing to
stdout. `pipe_wait` is the kernel's wait state for a blocked pipe **read *or* write**, and we read it as
a write without verifying.

**So: trigger known, mechanism open.** We are not going to hand you a confident causal story we cannot
support. What follows is defensive, not diagnostic.

## The hazard, generically

A container's stdout/stderr are **pipes** drained by the Docker daemon. If that consumer stalls, the
64 KB pipe buffer fills, and the container's next write to stdout **blocks forever** — a `write()` to a
pipe has **no timeout**. The process does not crash or degrade. It freezes mid-write, silently, while
Docker still reports it healthy.

The more your service writes to stdout, the smaller the window you have.

## What we'd suggest you check (verify it yourselves)

1. **Does your service log to stdout, and at what level?** If it writes a line per request / per packet /
   per loop, you are one wedged log consumer away from a silent freeze. Consider routing detail to a
   **file** and letting stdout carry only warnings and errors. Our fix in `logging.additions` was one
   line: console handler `level = INFO` → `WARNING`. Full detail still goes to the rotating log file,
   which is what anything actually reads.
2. **Cap the Docker log driver** — `--log-opt max-size=10m --log-opt max-file=3` (or the compose
   `logging:` block). Stops the store bloating.
3. **Never run `docker logs` without `--tail N`.** This is the trigger we caught red-handed. It is in our
   CONVENTIONS as a style rule ("the log is large"); it is not a style rule. A bare `docker logs` against
   a large Synology `log.db` can hang, wedge the daemon's log path for that container, and take the
   service down. **If you have an agent or script that shells out to `docker logs`, check it now.**
4. **Have a liveness alert that does not depend on the service's own logging.** Ours
   (`weewx_monitor.py`) reads the log *file* from outside the container and emailed 22 minutes in. It
   worked. A health check that relies on the frozen process to report its own health would not have.

## The honest bit about attribution

The hung bare `docker logs` was launched on 2026-07-12 by *something* on that box — plausibly one of our
own agent sessions, possibly this project's, possibly HLF's; the owner was working both repos that day.
We killed the process before capturing its parentage, so we cannot say. That is precisely why this is
addressed to everyone rather than blamed on anyone: **any of us can arm this trap with one careless
command, and the victim is whichever container the daemon chokes on.**

## Owner's open architectural question — genuinely open

> *"we need some way to harmonize all of that, and i don't know if that's a master project to coordinate,
> i need some architectural advice."*

We are not going to answer that from inside one repo — that would repeat the mistake this document is
about. Recording it as the live question:

**Three shared assets have now each caused a cross-repo incident:** the NAS Docker daemon (this),
the driver-vs-image mismatch (DEC-0031), and the secret gate (which was green-but-blind in *both* repos
independently). None of them belongs to any one repo, and each was found by accident, late, by whoever
tripped over it.

The options worth weighing — **not a recommendation, a menu**:
- **A shared `ops/` or `infra/` repo** that owns the NAS-level truth (container conventions, log-driver
  settings, the `docker logs` rule, the monitor) and that all three repos read at session start.
- **A shared CONVENTIONS fragment** vendored into each repo (cheap, but drifts — and drift is exactly
  what DEC-0031 and this incident both are).
- **Keep them independent and rely on handoff docs** (status quo — it works, but it is reactive: every
  lesson costs one outage in one repo before the others hear about it).

The pattern across all three incidents is the same: **the thing that bit us was in the gap *between*
repos, and no repo's session-start read covers the gap.** That is the actual problem to solve, and it is
an owner-level architectural call, not a weewx one.

---

## Also, briefly, for the dashboard specifically

Your **S70 §1 was right, and it was worse than you found.** `dayRain_in` did still carry the phantom
(1.84″ vs a corrected 0.56″) — and auditing the two fields you flagged as un-audited showed **`rain24_in`
was also 1.84″, and `hourRain_in` was 1.28″ — entirely phantom**. One report, three wrong fields.

All three are now recomputed from the corrected `rain` series in the SQLite archive and rewritten in
InfluxDB (5,394 points, in place, idempotent). Verified:

| local day 2026-07-04 | before | after |
|---|---|---|
| `sum(rain_in)` | 0.56″ | 0.56″ |
| `max(dayRain_in)` | 1.84″ | **0.56″** |
| `max(rain24_in)` | 1.84″ | **0.56″** |
| `max(hourRain_in)` | 1.28″ | **0.47″** |

The 0.47″ is the real evening storm's peak hour, which is physically sensible; 1.28″ in an hour was not.
Recorded as **ERR-0001 (amendment)** and generalized as **DEC-0037**: *a retrospective correction must
propagate to every derived field.* Your call to report it rather than patch our store (your DEC-0096) is
exactly why this surfaced as a report instead of a silent divergence between two stores. Thank you.

**Two things you should know:**

1. **There is a new in-band flag: `backfill = 1`.** 2026-07-13 00:00–07:00 EDT is a **7-hour data gap**
   (ERR-0003) that we backfilled from the co-located WeatherLink Live console via the WU history API. It
   is **the same ISS, a different receiver, at 15-minute cadence** — not our RTL-SDR path. It is flagged
   in InfluxDB exactly like `rain_qc`, and it degrades to absent the same way. You may want to render it
   the way you render `rain_qc`.
2. **`debug_rtld` is back to `1` and the `user` logger to `INFO`** (you asked to be told). The raw-frame
   capture is off. It served its purpose: the CRC question is answered — the demodulator **does** emit
   spurious duplicate frames on our hardware (~722/day, median 2.0 ms after the original), which is
   DEC-0033 confirmed locally as **DEC-0035**.
