# Design: wind gust plausibility (#584) — DRAFT, no DEC yet

**Status:** B accepted as DEC-0245 (owner's menu choice, S211); not built. C and A were not chosen.
The build waits on a re-run of §6 after a wind event over 25 mph. Drafted S211 on Sonnet; §6's measurement ran
the same day (24 days of calm data, no strong wind in the window).

## 1. The problem

Issue #584 (an adopter's Go/Python A/B run): one CRC-valid frame, `A7 3A 30 30 3B 05 03 AF`
(message type 0xA, wind byte `0x3A` = 58 mph, direction byte `0x30`), arrived between zero-wind
frames. The ISS then reported a 10-minute gust of 58 mph for three archive intervals while the average
stayed near 0. The spike is a bad ISS reading, not a radio bit error (S210's reply on the issue:
a receiver error cannot make the ISS's own Type 9 gust read 58 for ten minutes).

It is the mirror image of ERR-0012 (2026-10-31): there a CRC-valid frame carried a bad *sample* (30 mph)
and the ISS's own 10-minute gust stayed at 4 mph.

| | Bad value | Trustworthy reference | Seen in |
|---|---|---|---|
| Class A | one received wind sample (`windSpeed`/`windGust`) | the ISS's Type 9 gust (`windGust10`) | ERR-0012 |
| Class B | the ISS's Type 9 gust (`windGust10`) | the samples we received over the same 10 minutes | #584 |

## 2. What already guards wind

- **Sample, loop level:** bounds 0..89.4 m/s and a 20 m/s step limit on `wind_speed` (DEC-0029,
  `SENSOR_QC_DEFAULTS`). The #584 sample is about 25.9 m/s from a 0 reading 3 s earlier, so our driver
  would very likely have nulled it (checked against the filter logic only, not replayed).
- **Frame level:** a bounds failure on any field nulls the frame's siblings (DEC-0054); a message type no
  Davis sends does the same (DEC-0203). Neither fires here.
- **Archive level:** DEC-0110 nulls the wind triple when `rxCheckPercent` < 20% and gust > 10 mph.
  Reception was 99–100% in both incidents, so it cannot fire.
- **Type 9 gust itself:** bounds only (`wind_gust_10`, 0..89.4 m/s, no delta, DEC-0224). **This is the
  gap:** a bad ISS reading rides `windGust10` for its full ten minutes into the loop feed, InfluxDB and,
  since DEC-0232, the archive column.

Net: for #584 our `windSpeed`/`windGust` are probably already clean. What is unguarded is `windGust10`
and every consumer that trusts it, including the dashboard's gust spike guard (dash DEC-0427), which
uses it as the reference for Class A. A wrong reference weakens that guard. (Dashboard changes are a
separate repo and out of scope here, DEC-0010; this only notes the dependency.)

## 3. Options

**A. Document only.** Add an ERR entry and a README note: `windGust10` is the ISS's own value and can
be wrong. Zero risk, no protection.

**B. Driver cross-check of `wind_gust_10` against received wind (recommended).** Keep a rolling
maximum of *accepted* `wind_speed` over the last N minutes. When a Type 9 frame carries
`wind_gust_10` more than a margin above that maximum, and the window has enough coverage, set it to
None (honest null, DEC-0006) and log a `rejecting implausible` line in the existing family. Wind is
continuous: a 58 mph gust cannot be preceded and followed by calm 2.5 s samples, and at 99% reception
the chance that we missed the whole event is negligible. Pure logic, unit-testable like `SensorQC`.

**C. Archive-time cross-check of `windGust` against `windGust10` (Class A).** In
`DewpointCacher.new_archive_record`, null the wind triple when our interval gust exceeds a fresh
`windGust10` by more than a margin. A real gust we received can never exceed the ISS's own maximum
(allowing ±1 mph for quantization and the correction table). S187 measured that ERR-0012's minute is
the only one in five days where our per-minute peak beat `windGust10` by more than 8 mph, so false
positives look rare. **This reverses the owner's S187 call on ERR-0012 ("record it, leave the data")**,
so it is separable and needs its own yes; B does not depend on it.

**D. Dashboard only.** Already done for Class A (DEC-0427). Does nothing for the wire, InfluxDB or
other consumers.

## 4. Recommendation

Build **B**; offer **C** as an optional second DEC. Reasons: B closes the one unguarded field named in
#584 with parameter-light logic and no cross-repo change; C is a policy reversal and belongs to the
owner. A alone leaves the gap open but is the right fallback if §6's measurement shows the margin
cannot be set without false positives.

## 5. Sketch of B

- State: a deque of (time, `wind_speed` m/s, accepted-frame flag) for samples that **passed** QC, 11
  minutes deep (one minute over the ISS's 10 to absorb window-edge jitter), plus a count of frames
  received vs. expected for coverage.
- Check (on a Type 9 frame with non-zero `wind_gust_10`): reject if
  `wind_gust_10 > max(window) + GUST10_MARGIN_MS` **and** coverage over the window ≥ `GUST10_MIN_COVERAGE`.
  Otherwise accept.
- Cold start: no judgement until the window holds `GUST10_MIN_SECONDS` of samples (reseed behavior like
  `QC_RESEED_SECONDS`), so a restart never rejects on an empty window. An unjudged value passes, as
  today.
- The rejected value does not move any state; the next Type 9 frame is judged afresh, so a genuine
  rise is accepted as soon as received samples catch up.
- Co-rejection stays as is: B nulls only `wind_gust_10`; it is not frame-level proof (the frame's other
  fields are fine), exactly as a delta trip does not trigger DEC-0054.
- Config: `[Rtldavis]` `qc_wind_gust_10_margin`, with `sensor_qc = false` disabling it with the rest.
  Baked driver change, banner bump, ships in the next minor image.

## 6. Measure before fixing numbers (DEC-0110's precedent; run S211, results below)

Values after the §6 readout: margin `max(10 mph, 50% of windGust10)` (about 4.5 m/s at the floor),
`GUST10_MIN_COVERAGE` ≈ 90%, window 11 min, `GUST10_MIN_SECONDS` ≈ 600. The data is the archive's
`windGust10` and per-minute `windGust`:

1. Distribution of `windGust10 − rolling max(windGust, 10 min)` per minute; find the largest real
   value and the true-positive floor (#584's 58 vs ~0).
2. Count of minutes B would have rejected, listed, each checked by hand.
3. The same for C: `windGust − windGust10` over the same minutes (S187's 5-day figure, extended).

The adopter's frame and the 10-31 minute are the two positive controls; a negative control is a real
squall day.

### Results (S211, 2026-11-21)

Source: a read-only copy of the live archive (`integrity_check` ok, US units), 2026-10-28 12:30 to
2026-11-21 15:43 ET, 22,480 minutes with both `windGust10` and a full 11-minute window of `windGust`.
The `windGust10` column starts at DEC-0224's deploy, so this is 24 days, not the station's history.

**B: `windGust10` minus the rolling 11-minute maximum of `windGust` (mph).**

| Diff | Minutes |
|---|---|
| −10 to −2 (ISS below our max) | 5,809 |
| 0 to +1 | 16,547 |
| +2 | 124 |
| ≥ +3 | 0 |

The largest value is **+2 mph** (a 13 vs 11 stretch on 11-10, 9 minutes; the others are 6 vs 4 and
2 vs 0). Nothing came within 8 mph of a 10 mph margin. #584's shape would read about **+58**.

**A: `windGust` minus `windGust10` (mph).**

| Diff | Minutes |
|---|---|
| ≤ +1 | 22,330 (almost all negative or zero) |
| +2 to +3 | 133 |
| +4 to +5 | 13 |
| +6 to +8 | 3 |
| +26 (ERR-0012, 10-31 10:04) | 1 |

The 3 minutes at +6 to +8 are the next largest after ERR-0012: small values at low wind, with
`rxCheckPercent` 100, so likely a stale `windGust10` or window-edge alignment, not corruption.

**What this supports.** B has about two orders of magnitude between the largest real diff (+2) and
the #584 shape (+58). C separates ERR-0012 (+26) from the next case (+8) by a factor of three, a
thinner margin than B's.

**What it does not.** The window holds no strong wind: the maximum `windGust10` in 24 days is
**14 mph**. The false-positive risk of any margin in a real squall is unmeasured, which is why §5's
margin is `max(10 mph, 50% of windGust10)` rather than a flat 10 mph, and why B fails open on low
coverage. Re-run this readout after the first month with a wind event over 25 mph, and before the
next minor image if one occurs earlier. The script is a 40-line SQLite query over `archive`; it
belongs in `ops/` if the design is accepted.

## 7. Tests (when approved)

Replay #584's sequence (0 mph frames, the `A7 3A 30 30 3B 05 03 AF` frame, then a Type 9 frame
reading 58 mph): sample nulled by the delta filter, Type 9 value nulled by B, log line present. Replay
a genuine squall with a real Type 9 gust: accepted. Cold start, low coverage and a missed single peak
all pass the value through. `tests/test_sensor_qc.py` style; a positive control on the check itself
(a mutated margin must fail a test).

## 8. Risks

- A real gust where reception dipped: the coverage gate passes the value through (fail open).
- Quantization: the ISS reports whole mph through a correction table; the margin covers it.
- A wrong threshold hides a real gust from `windGust10` only; `windGust` and the archive are untouched.
- Public-repo hygiene: nothing here carries a host, IP or coordinate.

## 9. Questions for the owner

1. B: yes or document-only (A)?
2. C: reverse the S187 call on ERR-0012 and null Class A at archive time, or leave the dashboard's
   guard as the only defense?
3. Run §6's measurement first and set numbers from it (recommended)?
