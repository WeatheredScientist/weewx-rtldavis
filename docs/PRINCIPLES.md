# Principles — weewx-rtldavis

**Status:** Source of truth (durable intent)
**Last updated:** 2026-07-04 (S17)

Decisions (DECISIONS.md) record *what* was chosen. Principles record the *durable intent* behind
those choices — the reasons that should outlast any individual decision. When a new decision is
weighed, it should be consistent with these.

## 1. Own the data — and stay source/consumer-adaptable

The founding act is breaking the WeatherLink lock: an RTL-SDR *passively intercepts* the same
915 MHz broadcast the Davis console receives, so the readings become ours — real-time, owned
locally, displayable anywhere. But the driver's identity is not "Davis." Its real contract is the
**data it emits** — the loop-JSON file and the InfluxDB line-protocol schema (INTERFACES.md) — not
weewx internals and not any one consumer. Keep that contract stable and documented so non-Davis
WeeWX stations, other sinks, and eventually CumulusMX can rely on it. A consumer that owns your
schema becomes a wall you can't move past.

## 2. Honest nulls over stale substitutes

When a reading is rejected or missing, propagate `None` — never substitute a stale prior value. A
null is correct when the ISS stops reporting (e.g. a failed vane potentiometer); a substituted
stale value is misleading and harder to diagnose than an honest gap. This is the filter philosophy
across `dewpoint_service.py`, and the model for the rain-spike filter (DEC-0006, DEC-0021).

## 3. Reception is noise-floor limited; tune with evidence, not vibes

At ~150 ft through walls the link budget sits near the noise floor (~67–70%). RF parameters
(gain, fc, ppm, receiveWindow) are set from **measured sweeps averaged over meaningful windows**,
not single short samples or intuition. Short-window results mislead (BACKLOG RF history: rw400 and
larger receiveWindow tested *worse* than baseline). A proper gain/receiveWindow optimum needs a
24 h+ averaged test (ROADMAP).

## 4. Hot-swap what you iterate; bake what you trust

Files under active iteration (the driver, uploaders being tuned) are **volume-mounted** so a change
is edit + clear-pyc + restart — no rebuild, and reversible in seconds. Stable code is baked into the
image. This is what makes prod changes safe to trial (DEC-0004, ARCHITECTURE).

## 5. Prod is sacred

There is exactly one receiver and one dongle — you cannot mirror prod trivially. Every change
proves itself off the live signal where possible (Simulator-backed dev container), and the
unavoidable on-signal check is done via reversible hot-swap with an instant rollback path. Never
change prod config/binaries without an agreed test + rollback plan (DEC-0011).

## 6. Inspectable and dependency-light

Prefer mature, few, Docker-friendly dependencies and plain, readable Python over cleverness. The
system must remain inspectable and deployable on Synology NAS-class hardware. Uploaders follow the
WeeWX `RESTThread` pattern for reliable non-blocking posts rather than hand-rolled threading
(DEC-0007). A heavy dependency for a simple task is a smell — it's why we run a custom
`loop_json_writer.py` instead of weewx-loopdata for the dashboard feed (DEC-0005).

## 7. Incremental over rewrite

Improve in place. Rewrites are a last resort requiring proof the current implementation cannot meet
documented requirements, plus a migration plan and explicit approval (DEC-0014). LLM-assisted work
is especially prone to needless rewrites and band-aid churn; this principle is the guard.

## 8. Discuss before building

Design is resolved in conversation first, then implemented. The expensive mistakes are made before
anyone agreed on the approach.

## 9. Secrets never touch the repo or an LLM prompt

The repo is public and permanent. Credentials live only in gitignored files (`weewx.conf`,
`monitor.env`); committed source carries `YOUR_*` placeholders. Never paste a live secret into an
LLM chat — treat anything that reaches a prompt as compromised and rotate it server-side
(DEC-0012, CONVENTIONS §Secrets).
