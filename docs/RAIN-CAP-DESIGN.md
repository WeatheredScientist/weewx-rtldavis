# Design: the rain-counter cap and elapsed time (outside review C3)

**Status:** A accepted as DEC-0248 (owner's menu choice, S211). C (§6) is built as DEC-0249 with a catch-up
cap of 45 (owner's menu choice, 2026-11-25), on a held branch: it merges after the post-soak image and
ships in its own minor. Rollout: §7. Drafted and built on Opus 5.5.

## 1. The finding

`rain_delta_tips()` rejects any step over 16 tips, however long since the last reading. Both halves
of the review's claim reproduce against `dev`:

| Case | Today | Result |
|---|---|---|
| Loss: counts 20, 40, 41 (20 real tips fell in a gap) | 40 rejected; 41 books 1 | 20 tips (0.20 in) lost |
| Phantom: ISS counter resets from 112 to 0 | read as a wrap | 16 phantom tips (0.16 in) |

The loss is logged at ERROR and emailed (DEC-0056's tripwire). The phantom logs nothing. A reset
books a phantom from a count of 112 to 127 only (16 of 128 values, 1 to 16 tips); from 1 to 111 it
is rejected.

## 2. What the data says now

Measured 2026-11-24 from InfluxDB's archive series (`rain_in`, 2026-05-19 to 11-24, 266,201 records,
23.64 in) and 31 days of driver logs. DEC-0056 had 70 days and 6.25 in.

| | DEC-0056 | Now |
|---|---|---|
| Most tips in 1 minute | 7 | 10 (08-05) |
| Most tips in 2 / 3 / 4 minutes | 12 / 16 / 23 | **19 / 26 / 34** |
| 2 / 3 / 4-minute windows over 16 tips | 0 / 0 / some | 2 / 18 / 53 (1, 5 and 11 days) |
| Archive gaps over 90 s with rain within 15 min | not counted this way | 25 |

- **DEC-0056's "cap 16 is safe at every gap length this station has shown" no longer holds.** Gaps
  of 2 to 4 minutes happen, and 08-05's storm put 19 tips in two minutes.
- **No loss is shown.** In the 25 gaps near rain, the first record afterward held at most 2 tips. That
  bounds nothing inside a gap: a rejected step leaves no tips, and a restart re-seeds the baseline
  (§3). The last 31 days of logs hold 0 counter rejections, recoveries or co-rejections
  (control: the same files hold 6 wind-speed rejections). Little of that time had heavy rain, and
  logs from the summer storms are gone.
- **Exposure is shrinking.** Archive gaps over 90 s by month: 206 in August, 79 in September, 31 in
  October, 7 in November to the 24th. Since DEC-0229 reached prod (11-04 18:36 ET), the one gap with
  the driver running is 11-20 02:23 (4 min). The others are restarts or the receiver move.

Limits: the series is one station, mostly one warm season, and has had errata corrections applied.
Archive gaps stand in for counter-reading gaps. I counted startup lines for ten of the October and
November gaps, not for earlier ones.

## 3. What no cap change can fix

- **A restart re-seeds the counter** (`last_rain_count = None`), so tips that fell during it are
  lost at any cap. Most long gaps are this.
- **`[StdQC]` rejects rain over 0.3 in** in prod's config and in `weewx.conf.example`, so a recovered step
  over 30 tips is discarded anyway. (Corrected at the build: the limit applies to each LOOP packet's `rain`
  as well as to the archive record's, and nulls only that field. The image's starter is
  `weectl station create`'s output, which carries stock WeeWX's `rain = 0, 10, inch`, so a seeded install
  never had 0.3.)
- **A counter that moves more than 127 tips** in a gap is ambiguous.
- **An ISS reset after a long silence** is indistinguishable from a wrap by elapsed time alone: 16
  tips need only about 64 s at the bucket's 4 s-per-tip ceiling, and a battery swap outlasts that.

## 4. Options

**A. Keep 16, correct the record (recommended).** A DEC amending DEC-0056: its safety claim becomes
"rare, loud and recoverable from the console", with §2's numbers, and the existing trigger (a rejection
on a wet day) stays. No code, no changed values.

**B. Time-aware cap.** Allow `max(16, min(30, elapsed_s / 4 + 1))`. Recovers 17 to 30 tips after a
gap over about 64 s. Costs: a corrupt reading after a long quiet gap can book 0.30 in instead of
0.16, and the pure function needs a time input. This is DEC-0056's declined alternative.

**C. Confirm on reject.** Hold a rejected step, and book it only if the next independent reading
continues from it. It can recover real rain without raising the single-reading ceiling. DEC-0056 named this
the escalation. Costs: a state machine that must fit DEC-0218's anchor, and the StdQC cap still
limits the booking to 30.

**D. Refuse an impossible wrap.** Accept a wrap only when its tips fit the elapsed time (about
`elapsed_s / 4 + 2`). It stops a reset phantom seen within seconds, and nothing after a long silence.
It can also reject real wrapped tips if the margin is wrong. Small benefit; not recommended alone.

## 5. Decision (DEC-0248)

**A now, then C with an elapsed-time check, in its own minor after the post-soak image.** A fixed cap
judges one reading by size alone. The counter is cumulative, so real rain persists into the next
transmission and a random corruption almost never does; elapsed time then says whether that much rain was
possible. B relies on time alone, so one corrupt reading after a quiet gap books more than today.

## 6. C, confirm-on-reject

Inputs: the anchor A (last accepted count, with its monotonic time), the previous reading P if it was
rejected (with its time), the new reading n. Everything before step 3 is DEC-0218 unchanged.

1. n plausible against A: book that (P was a glitch).
2. Otherwise apply today's check of n against P. If it rejects n, nothing is booked.
3. If it accepts n, P and n agree that the counter moved. Book `(n - A) mod 128` instead of the few tips
   from P to n, when **all** hold:
   - P and n are at least 2 s apart (one burst can be decoded twice, milliseconds apart, DEC-0035);
   - the total is at most `elapsed_s / 4 + 1`, elapsed since A (the bucket's ceiling);
   - the total is at most the catch-up cap (below);
   - P is not 0 (a reset lands on 0 and persists, so confirmation cannot expose it; the bullet assumes
     an ISS power cycle zeroes the counter).
   If any fails, book what step 2 books today.
4. Log each catch-up at INFO with A, P, n, the total and the elapsed time, in wording that does not match the
   monitor's marker. The ERROR line and email on P stay.

Elapsed time comes from `time.monotonic()`, never the wall clock. A co-rejected frame (DEC-0054) sets
neither A nor P. Every restart clears both.

**Modeled exhaustively** over all 1,818,624 (A, rejected P, n) triples, 300 s elapsed, against the
shipped functions:

| | Catch-up cap 20 | 30 | 45 |
|---|---|---|---|
| Readings accepted or rejected differently | 0 | 0 | 0 |
| Triples whose booked tips change | 1,270 | 13,335 | 45,339 |
| Real catch-ups (17 to cap) booked exactly; today 0 | 1,143 of 1,152 | 4,953 of 4,992 | 10,668 of 10,752 |
| One glitch, then the true count: booked wrong | 0 of 241,536 | 0 of 241,536 | 0 of 241,536 |
| Reset to 0 that books a new phantom, zero rule on / off | 0 / 4 | 0 / 14 | 0 / 29 |

The missed catch-ups are those that land exactly on 0. The model does not cover two corrupt readings that
agree, or an ISS reset during rain with the count already off 0 when first heard.

**The catch-up cap: 45 chosen** (DEC-0249). At 0.3, `[StdQC]` nulls the record's whole `rain`, the other
tips in that minute included, so a 30-tip catch-up in a wet minute would lose more than it saves.

- **20 (default proposal, not chosen):** 20 plus the wettest minute on record (10) is 30, just inside the limit. It recovers
  only 17 to 20 tips, so on stock config C does little.
- **45 (chosen), with `[StdQC]` rain raised to 0.6 in:** 45 plus 10 is 55. 0.6 still refuses the 64-tip and
  128-tip flips DEC-0021 named, and one corrupt reading is still capped at 16. (Corrected at the build: with a
  0.2 mm bucket 64 tips is 0.50 in, which 0.3 refused and 0.6 does not; the driver's own filter still
  rejects it.) It is a change to prod's config and to `weewx.conf.example`, not to the seeded starter, which
  has 10 in (§3). Adopters who copied the example keep 0.3 until they edit it.

Either way the rain lands in the minute it was confirmed, not the minutes it fell; totals are right, and the
per-minute shape is not.

**The reset phantom that exists today** (112 to 127 down to 0, 1 to 16 tips) stays unless D is added. D can't
see a reset after about a minute of silence, and it is the one step that would reject a reading accepted
today. Left out unless the owner asks.

**Not covered:** tips that fall during a restart (`last_rain_count = None`). Saving the count across
restarts has the same confirmation problem and deserves its own design.

**Limits found while building.** The times are when the driver processes a reading, not when the radio
heard it, because frames carry no arrival stamp. If the engine stalls, two copies of one burst could be
processed over 2 s apart; both would also have to be corrupt and agree. And a reset that lands on 0 is
refused only when the first reading heard is 0, as above.

Tests: `tests/test_rain_catch_up_dec0249.py` asserts every row of the table against the shipped functions,
plus the time, 2 s, zero, restart, co-rejection and stale-P cases.

## 7. Rollout (owner-run, when this ships in its own minor)

1. Before the restart onto that image, set `[StdQC]` `[[MinMax]]` `rain = 0, 0.6, inch` in **both** the live
   `weewx-data/weewx.conf` and the tenant-root `weewx.conf.rx-baseline` (a campaign `restore_baseline` copies
   the second over the first, DEC-0080). Both hold 0.3. The config is mounted: the image change alone does
   not do this (DEC-0046), and with 0.3 left in place a catch-up of 31 to 45 tips is nulled.
2. Read both back, restart, check the log for the new banner. Add the row to `CONSTANTS.md`'s live-config
   deviations then, if 0.6 is kept.
3. **Before reconciling a rejection by hand** (DEC-0056's playbook, which the email still points at), grep the
   log after it for `DEC-0249`. A catch-up line means the rain is already booked, and adding it again would double it.
4. Rollback: the previous image. 0.6 with the old driver changes nothing: no reading books over 16 tips.

## 8. Release note (draft)

> **Rain that falls during a reception gap is now recovered.** When the rain counter jumps further than one
> reading can be trusted for (over 16 tips), the driver still rejects that reading. If the next
> one, at least 2 seconds later, continues from it, and that much rain was possible in the time since the last good
> reading, the whole jump (up to 45 tips) is booked; before, it was lost. The rain is recorded in the minute it
> was confirmed, so totals are right and the per-minute shape is not. A jump to exactly 0 is never recovered
> (it looks like an ISS reset), and neither is rain that falls while the driver is stopped. If your `weewx.conf` has
> `rain = 0, 0.3, inch` under `[StdQC]` (copied from our example), change it to `0, 0.6, inch`, or WeeWX will
> discard larger recoveries. A config the image created has WeeWX's own limit and needs no edit. *Why a minor:*
> emitted rain values change; no edit is required to keep running.
