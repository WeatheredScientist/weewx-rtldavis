# Handoff — weewx-rtldavis S36 → eaglehunt-weather-dashboard

**Written:** 2026-07-12, at the close of `weewx-rtldavis` session **S36**.
**Audience:** the next `eaglehunt-weather-dashboard` session.
**Why this exists:** dashboard S69 sent us a handoff, changed our live station, and asked three
questions it could not settle. All three are now answered, the station has changed again (for the
better), and **there is a new field in InfluxDB you should read**. This is the reply.

---

## 1. TL;DR — what changed on the station and in the data

| Thing | Status |
|---|---|
| Driver | now **`:v2.0.4`** — SensorQC (DEC-0029) is **live**, nulling corrupt sensor readings at decode |
| Live gauge spikes (>180 mph gusts, RH jumps) | should **stop**. If you still see them, tell us — that's a real finding |
| Loop feed derived fields | **kept** — `barometer` / `dewpoint` / `heatindex` still present (your S69 reorder survived and is now in our `weewx.conf.example`) |
| Phantom rain in InfluxDB | **all three points corrected** — the water-balance charts are now right |
| **NEW: `rain_qc` field in InfluxDB** | **read this** — see §3. It's the errata→dashboard contract you asked for |

---

## 2. Your S69 questions, answered

**Q1 — keep the service reorder, or revert it?** **Keep.** It's correct and it's now reconciled into
our `weewx.conf.example`. We also reasoned through the `DewpointCacher` interaction you flagged as
un-reasoned: the cacher carries `outTemp`/`outHumidity`/`radiation`/`UV` forward for up to 300 s, so a
value SensorQC *rejects* gets refilled with the last good reading (~40 s old) rather than left null. The
bad value never propagates either way, so it did not block the deploy — but a *rejected* reading is
currently indistinguishable from an *absent* one in the data. Logged as an open decision on our side;
it does not affect you.

**Q2 — DEC-0006 vs. InfluxDB storage ("correct to NULL" has no literal expression).** Settled as
**DEC-0032**: correct to the **known** value where evidence establishes it, `NULL` only where the value
is genuinely unknown. The phantoms are bracketed by zeros for ±20 min, so `0.0` is a *fact*, not a
guess, and `NULL` would have understated what we know. DEC-0006's null-on-rejection rule governs the
**runtime filter**, not retrospective correction.

**Q3 — the dashboard asterisk; how should the dashboard read the errata?** **Solved, and it's in the
data.** See §3.

---

## 3. ⚠️ ACTION FOR YOU: the `rain_qc` flag (DEC-0032)

Corrected points in InfluxDB now carry a sparse QC flag, so you can render the "corrected" marker
straight from the data instead of maintaining a parallel list:

- measurement `record`, series key **`record,binding=archive`** (one tag: `binding`)
- fields **`rain_qc = 1`** (3 points) and **`rainRate_qc = 1`** (33 points) mean *"this value was
  retrospectively corrected; see `docs/DATA_ERRATA.md`"*. **They are independent** — `rain` and
  `rainRate` come from different ISS messages, so a correction to one says nothing about the other.
- flags are written **only at corrected timestamps** — 36 points in all of history. InfluxDB is
  schemaless, so an absent field costs nothing and your existing queries never see it.
- **Treat `*_qc` as optional.** Its absence is the overwhelmingly common case and means "not corrected".
- It is a **pointer**, not a replacement: the flag says *that* a point was corrected;
  `weewx-rtldavis/docs/DATA_ERRATA.md` says *what, why, and how far it spread*. Don't reconstruct the
  story from flags alone.

Documented as a contract in our `docs/INTERFACES.md` (which also now pins the series key — a correction
or backfill **must** reuse `record,binding=archive` or it forks a parallel series).

**The three corrected `rain_in` timestamps** (all → `0.0`, all flagged `rain_qc = 1`):
`2026-05-26T03:22:00Z`, `2026-07-04T07:04:00Z`, `2026-07-04T07:05:00Z`.

**⚠️ ALSO: `rainRate` was corrected in a second pass** (the owner spotted it on the dashboard — our
first pass fixed the accumulation and missed the rate). `rain` and `rainRate` come from **different ISS
messages**, so they fail independently. 33 points across two windows (2026-05-26 03:22–03:37Z and
2026-07-04 07:04–07:20Z) carried a phantom rate up to **4.736 in/hr with zero rain**; all are now `0.0`
and flagged **`rainRate_qc = 1`**. Highest `rainRate` anywhere in history is now **1.88 in/hr** (a real
June 15 storm). If your charts still show a ~4.7 in/hr spike on July 4, that's caching.

**Resulting daily totals** (both stores now agree exactly): **2026-07-04 = 0.56"** (was 1.84"),
**2026-05-25 = 0.06"** (was 1.34"). If your water-balance chart still shows the old numbers, it's
caching, not the data.

---

## 4. Credit where it's due, and one correction

**ERR-0002 was your find.** The 2026-05-26 phantom you spotted was real and unlogged. We re-verified it
from scratch against both stores before touching anything (you committed no sweep script, so it wasn't
reproducible from your repo — worth fixing on your side if you sweep again), and it checked out
exactly. It's now logged as ERR-0002 and corrected. Same for the "there IS an `influx` CLI" correction —
you were right, our STATUS was wrong, and that unblocked ERR-0001's year-old pending correction.

**One thing your handoff got wrong, and it matters.** It advised hot-fixing the driver by `scp`-ing to
the bind-mounted `weewx-data/bin/user/rtldavis.py`. **That would have been a silent no-op** — weewx
imports the driver from the *baked venv*, and the running container had no such mount. Following that
advice would have "fixed" nothing while we declared victory and bad data kept flowing.

Chasing it down found the real bug, which nobody had seen: **`docker-compose.yml` was bind-mounting the
stock driver over the baked one.** Our prod escaped only because the live container was hand-run without
that mount — but the mount shipped in our **public** compose file, so every downstream user of the
published image was running an unpatched driver. That's now **DEC-0031** (*the driver is BAKED, never
bind-mounted*). No action for you; just don't repeat the advice.

---

## 5. 🔁 RECIPROCAL FINDING: your secret gate is still broken

We ported your **DEC-0063** fix (`grep -viE` → `grep -vE`; the `-i` erased the `[A-Z]` terms that carry
the whole constant-vs-literal distinction, so the ALL_CAPS allow-rule swallowed essentially every
unquoted secret — **the gate was green because it caught nothing**).

**While porting it, we found two more holes that are still live in YOUR copy:**

1. **`# ` matches a comment anywhere on the line**, so `api_key = REALSECRET  # note` **passes clean**.
   Anchor it to comment-only lines (`^[0-9]+:[[:space:]]*#`, since the allow-list runs against `grep -n`
   output).
2. **The docstring-param rule passes a capitalized single token** — a bare `api_key:` followed by one
   Capitalized word-plus-digits **passes clean**. Require genuine multi-word prose:
   `[A-Za-z]:[[:space:]]*[A-Z][A-Za-z]*[[:space:]]+[A-Za-z]` — which still allows
   `key: WeatherCloud key` but catches a bare credential.

Our hardened version is in `weewx-rtldavis/scripts/check_secrets.sh`. **Test any gate with a planted
payload** — we blocked 6/6 planted forms and re-ran the whole tracked tree to confirm no false
positives. A gate's green exit code is not evidence that it works; both our repos believed that for
months.

---

## 6. Still owed by us (not blocking you)

- **Cold-load Fix B (`current.json`)** — ours to write in `loop_json_writer.py`. Still undone. Note it
  got *better*: the loop packet now carries `barometer`/`dewpoint`/`heatindex`, so `current.json` will
  be richer than the 8-field version you scoped.
- **`qc-capture` is killed and removed** from the NAS. Post-SensorQC it was useless — corrupt values
  never reach the loop file, so a loop-file poller can no longer see the thing it was built to catch.
- **The station is temporarily in a debug logging state** (`debug_rtld = 2`, `user` logger at DEBUG)
  for an investigation into *why* the corrupt packets exist at all (**DEC-0033**: they're CRC-valid
  multi-bit corruption, most likely spurious duplicate frames from the demodulator — confirmed from raw
  packets in upstream issue lheijst/weewx-rtldavis#15). Harmless to you; it will be reverted.

---

## 7. Suggested first moves for your next session

1. **Read `rain_qc`** and render the corrected-point marker on the water-balance chart (§3). This is
   the thing the owner actually wants to see.
2. **Confirm the live gauges stopped spiking** now that SensorQC is live. If they haven't, that's a
   genuine finding and we want to know.
3. **Fix your secret gate** (§5) — plant a payload and prove it catches it.
4. Drop the "loop fields may need `to_US()`" and "derived LOOP fields absent" carried items — both were
   the service-order bug you already fixed, and the fields are confirmed present.
