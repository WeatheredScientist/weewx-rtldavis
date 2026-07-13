#!/usr/bin/env python3
"""Census of spurious duplicate frames from the rtldavis Go demodulator.

THE MECHANISM (DEC-0033, confirmed locally in DEC-0035):
the demodulator sometimes decodes a single RF burst TWICE, emitting a second
frame milliseconds after the first. A Davis ISS transmits about every 2.8 s, so
two frames from the same transmitter arriving <2 s apart cannot both be real
transmissions -- the receiver made the second one. When that second decode is
clean, the copy is byte-identical and harmless. When it picks up bit errors it
becomes a corrupted near-duplicate, and roughly 1 in 65536 of those passes CRC by
chance and delivers garbage sensor values (phantom rain, humidity spikes).

READ THIS BEFORE TRUSTING A ZERO -- the pipeline is not what it looks like.
An earlier version of this script parsed the driver's `data:` lines and reported
"0 suspicious pairs". That was wrong twice over (DEC-0035):

  1. `data:` lines are POST-DEDUP. main.go (~L394) compares each message to the
     previous one and, on a byte-for-byte match, logs `duplicate packet:` and
     `continue`s -- the duplicate never reaches the driver, so it never appears
     in a `data:` line. Every exact duplicate had already been stripped out of
     the data the script was reading. The gaps looked perfectly quantized at the
     ISS period BECAUSE Go had removed everything that wasn't.
  2. The CRC check happens in GO, not (only) in Python. protocol.go ~L218 --
     "If the checksum fails, bail" -- drops every CRC-failing packet inside the
     Go binary. Python only ever sees CRC-valid frames. So the old claim that we
     would see spurious frames "even when they fail CRC" was false.

So we count what Go itself reports: the `duplicate packet:` lines. Those ARE the
double-decodes -- the clean ones, at least. Corrupted copies that fail CRC are
dropped invisibly upstream, which makes this count a LOWER BOUND.

Separating the two populations is the whole job:
  * gap ~2.8 s  -> the ISS transmitted the same payload twice. Transmitter
                   cadence, genuine, harmless.
  * gap ~ms     -> the RECEIVER manufactured the second frame. The mechanism.

Requires `debug_rtld = 1` (or higher) AND the `user` logger at DEBUG in
weewx.conf -- the line is emitted via dbg_rtld(1) -> log.debug. That is noisy;
do not leave it on indefinitely. The standing fix is an always-on counter in the
driver (one summary line per archive period at INFO) -- see DEC-0035.

Usage:  python3 find_duplicate_frames.py /var/log/weewx/weewx.log [...]
"""

import re
import sys
from collections import Counter

# driver line:  ... data: 20:31:04.102918 E401BD56010ED10E 9 0 0 0 0 msg.ID=4
ACCEPTED = re.compile(
    r"data:\s+(\d\d):(\d\d):(\d\d)\.(\d{6})\s+([0-9A-F]{16})"
)
# Go line via driver:  ... info: 20:31:04.104955 duplicate packet: E401BD56010ED10E
DROPPED = re.compile(
    r"info:\s+(\d\d):(\d\d):(\d\d)\.(\d{6})\s+duplicate packet:\s+([0-9A-F]{16})"
)

ISS_PERIOD = 2.8       # seconds between real transmissions
SUSPICIOUS_GAP = 2.0   # anything closer than this cannot be the transmitter


def _secs(hh, mm, ss, us):
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(us) / 1e6


def parse(paths):
    """Yield (t, hex, kind) for every frame the demodulator produced."""
    for path in paths:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                m = ACCEPTED.search(line)
                if m:
                    hh, mm, ss, us, hexstr = m.groups()
                    yield _secs(hh, mm, ss, us), hexstr, "accepted"
                    continue
                m = DROPPED.search(line)
                if m:
                    hh, mm, ss, us, hexstr = m.groups()
                    yield _secs(hh, mm, ss, us), hexstr, "duplicate"


def main(paths):
    events = sorted(parse(paths))
    if not events:
        print("No frames found. Is debug_rtld >= 1 and the `user` logger at DEBUG?")
        return 1

    accepted = sum(1 for e in events if e[2] == "accepted")
    dups = [e for e in events if e[2] == "duplicate"]

    # Match each duplicate back to the most recent frame carrying the same payload,
    # then split by how long ago that was. Only the transmitter can be 2.8 s away.
    receiver_dups = []
    transmitter_dups = 0
    for i, (t, hexstr, kind) in enumerate(events):
        if kind != "duplicate":
            continue
        for j in range(i - 1, -1, -1):
            if events[j][1] == hexstr:
                gap = t - events[j][0]
                if gap < SUSPICIOUS_GAP:
                    receiver_dups.append((gap, t, hexstr))
                else:
                    transmitter_dups += 1
                break

    span_min = (events[-1][0] - events[0][0]) / 60.0
    print("window                    : %.1f min" % span_min)
    print("frames accepted           : %d" % accepted)
    print("frames dropped as dup     : %d" % len(dups))
    print()
    print("  of those dropped:")
    print("    transmitter repeats   : %d   (gap ~%.1f s -- genuine, harmless)"
          % (transmitter_dups, ISS_PERIOD))
    print("    RECEIVER duplicates   : %d   (gap <%.0f s -- the ISS cannot do this)"
          % (len(receiver_dups), SUSPICIOUS_GAP))
    print()

    if not receiver_dups:
        print("No sub-%.0f-second duplicates. Either the demodulator is not"
              % SUSPICIOUS_GAP)
        print("double-decoding on this station, or the window is too short.")
        return 0

    gaps = sorted(g for g, _, _ in receiver_dups)
    per_hour = len(receiver_dups) / (span_min / 60.0) if span_min else 0
    print("THE DEMODULATOR IS DOUBLE-DECODING (DEC-0035).")
    print("  fastest gap : %.6f s" % gaps[0])
    print("  median gap  : %.6f s" % gaps[len(gaps) // 2])
    print("  slowest gap : %.6f s" % gaps[-1])
    print("  rate        : %.1f/hour  (~%.0f/day)" % (per_hour, per_hour * 24))
    print()
    print("  This is a LOWER BOUND. A double-decode whose second copy picked up")
    print("  bit errors is not byte-identical, so Go's exact-match dedup misses")
    print("  it; if it then fails CRC it is dropped invisibly (protocol.go L218).")
    print("  Only the ~1-in-65536 that passes CRC reaches the driver -- as a")
    print("  valid-looking packet full of garbage. That is the glitch.")
    print()

    buckets = Counter()
    for g in gaps:
        if g < 0.001:
            buckets["< 1 ms"] += 1
        elif g < 0.010:
            buckets["1-10 ms"] += 1
        elif g < 0.100:
            buckets["10-100 ms"] += 1
        else:
            buckets["100 ms - 2 s"] += 1
    print("  gap distribution:")
    for label in ("< 1 ms", "1-10 ms", "10-100 ms", "100 ms - 2 s"):
        n = buckets.get(label, 0)
        if n:
            print("    %-14s : %4d  %s" % (label, n, "#" * min(n, 50)))
    print()
    print("  first few:")
    for gap, _t, hexstr in receiver_dups[:5]:
        print("    %s  +%.6f s after an identical frame" % (hexstr, gap))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["/var/log/weewx/weewx.log"]))
