#!/usr/bin/env python3
"""Look for spurious near-duplicate frames from the rtldavis Go demodulator.

THE HYPOTHESIS (DEC-0033, from upstream issue lheijst/weewx-rtldavis#15):
the demodulator sometimes emits a SECOND, corrupted frame microseconds after a
good one. A Davis ISS transmits about every 2.5 s, so any two frames from the
same transmitter arriving <2 s apart cannot both be real transmissions. Most such
frames are garbage and fail CRC, so the driver drops them silently and they never
appear in the archive -- but roughly 1 in 65536 passes CRC by chance and delivers
corrupt sensor values (phantom rain, 64 mph gusts, temperature steps).

User LloydR posted the fingerprint in 2022: two frames 262 us apart, differing in
4 bits, BOTH passing CRC (a 4-bit error pattern that happens to be a valid CRC
codeword -- CRC-16 catches every single-bit error but not every multi-bit one).

WHY THIS SCRIPT CAN ANSWER FAST: the driver logs the raw `data:` line BEFORE it
checks the CRC (rtldavis.py ~L684, CRC at ~L688). So we see the spurious frames
even when they fail CRC -- we do not have to wait weeks for the rare one that
passes. If the mechanism is real, sub-2-second pairs should show up within hours.

Requires `debug_rtld = 2` AND the `user` logger at DEBUG in weewx.conf.
Remember to revert both when the investigation is done (they add log volume).

Usage:  python3 find_duplicate_frames.py /var/log/weewx/weewx.log [...]
"""

import re
import sys
from collections import defaultdict

# data: 20:31:04.102918 E401BD56010ED10E 9 0 0 0 0 msg.ID=4
LINE = re.compile(
    r"data:\s+(\d\d):(\d\d):(\d\d)\.(\d{6})\s+([0-9A-F]{16}).*?msg\.ID=(\d+)"
)

SUSPICIOUS_GAP = 2.0    # seconds; real ISS spacing is ~2.5-2.8 s
POLY = 0x1021           # CRC-16/CCITT (XMODEM), init 0 -- same as weewx.crc16


def crc16(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ POLY) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def parse(paths):
    """Yield (seconds_since_midnight, hex, transmitter_id) per logged frame."""
    for path in paths:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                m = LINE.search(line)
                if not m:
                    continue
                hh, mm, ss, us, hexstr, tid = m.groups()
                t = int(hh) * 3600 + int(mm) * 60 + int(ss) + int(us) / 1e6
                yield t, hexstr, int(tid)


def main(paths):
    frames = list(parse(paths))
    if not frames:
        print("No `data:` lines found. Is debug_rtld = 2 and the `user` logger at DEBUG?")
        return 1

    by_tx = defaultdict(list)
    for t, hexstr, tid in frames:
        by_tx[tid].append((t, hexstr))

    total = len(frames)
    suspicious = []
    for tid, seq in by_tx.items():
        seq.sort()
        for (t0, h0), (t1, h1) in zip(seq, seq[1:]):
            gap = t1 - t0
            if 0 <= gap < SUSPICIOUS_GAP:
                suspicious.append((tid, gap, t0, h0, h1))

    print("frames parsed        : %d" % total)
    print("transmitters seen    : %s" % sorted(by_tx))
    print("pairs < %.1fs apart   : %d" % (SUSPICIOUS_GAP, len(suspicious)))
    print()

    if not suspicious:
        print("No sub-2-second pairs. Either the demodulator is not emitting spurious")
        print("frames on this station, or they are rarer here than on LloydR's.")
        return 0

    print("SUSPICIOUS PAIRS (a Davis ISS cannot transmit twice this fast):")
    print()
    for tid, gap, t0, h0, h1 in suspicious:
        b0, b1 = bytes.fromhex(h0), bytes.fromhex(h1)
        c0, c1 = crc16(b0), crc16(b1)
        diff = [i for i in range(64) if (int(h0, 16) >> i & 1) != (int(h1, 16) >> i & 1)]
        print("  tx=%d  gap=%.6f s" % (tid, gap))
        print("    %s  crc=%-5s" % (h0, "OK" if c0 == 0 else "FAIL"))
        print("    %s  crc=%-5s   bits differing: %d" % (
            h1, "OK" if c1 == 0 else "FAIL", len(diff)))
        if c0 == 0 and c1 == 0:
            print("    ^^ BOTH PASS CRC -- this is the LloydR signature; a corrupt frame")
            print("       is reaching the driver with a valid checksum.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["/var/log/weewx/weewx.log"]))
