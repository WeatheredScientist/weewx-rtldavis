"""Characterization test for the driver's decode -> QC -> loop-packet path (S180b, audit 24).

Pins what the driver emits, byte for byte, so a refactor of _data_to_packet's QC block
or genLoopPackets can prove it changed nothing. A seeded stream of Go stderr lines
(DATA frames, channel hops, and the dup/CRC/burst/repeat bookkeeping lines) runs through
the REAL PacketFactory, parse_raw, _update_stats, _data_to_packet and genLoopPackets.
Only the process (ProcManager), the clock and the hot-swap poll are stand-ins.

The snapshot is every log record (level and text, debug included) and every yielded
loop packet, interleaved in emission order, plus the end-state counters, the rain
anchors and the QC baselines. It is compared by SHA-256: a mismatch writes the full
snapshot to a temp file and names it, so the difference can be read with a diff.

The frames are synthetic. Each payload byte walks a little from frame to frame, with
occasional jumps to a random value, so the stream carries clean readings, delta trips,
out-of-range values, impossible message types, calm wind, rain-counter glitches and
recoveries, and byte-identical repeats. test_stream_exercises_every_path asserts that
each of those reached the log, so a change to the generator cannot quietly drop one.

If a change is MEANT to alter the driver's output, regenerate the digest: run this file,
read the written snapshot, and paste the printed digest in only after reviewing it.
"""
import hashlib
import json
import logging
import random
import tempfile

import rtldavis
from conftest import DEFAULT_CHANNELS, make_driver

# Changed once, deliberately, in S180b: dropping parse_raw's dead windBatteryStatus line
# (audit 24c) removes a None-valued key from 36 DEBUG dict reprs; nothing else moved.
EXPECTED_SHA256 = "2d45e308a9083bf8bcf5f16386ca52b3dffa58e6e94fa76a9ae807da3842fa27"

T0 = 1_800_000_000.0
MSG_TYPES = [0x8, 0x8, 0xA, 0xA, 0xE, 0xE, 0x5, 0x4, 0x6, 0x9, 0x2, 0x7, 0x3, 0xC,
             0x0, 0x1, 0xB, 0xD, 0xF]


def _frames(seed=24, n=600):
    """Yield (gap seconds, payload hex) pairs."""
    rng = random.Random(seed)
    state = {t: [rng.randrange(256) for _ in range(3)] for t in set(MSG_TYPES)}
    state[0x8] = [0x03, 0x20, 0x00]       # ~20 C
    state[0xA] = [0x26, 0x70, 0x00]       # a mid-range humidity
    state[0xE] = [0x40, 0x00, 0x00]       # rain counter
    wind = [5, 128]
    prev = None
    for _ in range(n):
        if prev is not None and rng.random() < 0.06:
            yield rng.choice([0, 1, 3]), prev    # byte-identical repeat
            continue
        t = rng.choice(MSG_TYPES)
        s = state[t]
        if t == 0xE:
            s[0] = (s[0] + rng.choice([0, 0, 0, 1])) & 0x7F
        else:
            s[0] = max(0, min(255, s[0] + rng.choice([-1, 0, 0, 1])))
        s[1] = rng.randrange(256)
        b3 = s[0]
        if rng.random() < 0.05:
            b3 = rng.randrange(256)              # glitch: one frame's byte at random
        r = rng.random()
        if r < 0.06:
            wind = [rng.randrange(3), 0]         # calm-air floor
        elif r < 0.10:
            wind = [rng.randrange(256), rng.randrange(256)]
        else:
            wind = [max(0, min(255, wind[0] + rng.choice([-2, -1, 0, 1, 2]))),
                    rng.randrange(1, 256)]
        w = wind
        if t == 0xE and rng.random() < 0.15:
            w = [255, rng.randrange(256)]        # out-of-range wind on a rain frame
        bat = 0x8 if rng.random() < 0.03 else 0x0
        b = [(t << 4) | bat, w[0], w[1], b3, s[1], s[2], rng.randrange(256),
             rng.randrange(256)]
        prev = "".join("%02X" % x for x in b)
        yield rng.choice([2, 3, 3, 60, 140]), prev


def _batches():
    """(clock, hot-swap flag, stderr lines) per loop pass."""
    rng = random.Random(180)
    clock = T0
    cnt = 0
    out = []
    for i, (gap, hexpay) in enumerate(_frames()):
        clock += gap
        cnt += 1
        stamp = "%02d:%02d:%02d.%06d" % (i // 3600 % 24, i // 60 % 60, i % 60, i)
        lines = []
        if rng.random() < 0.3:
            lines.append("%s Hop: {ChannelIdx:%d ChannelFreq:902355835 FreqError:%d "
                         "Transmitter:0}\n" % (stamp, rng.randrange(5), rng.randrange(-900, 900)))
        lines.append("%s %s %d 0 0 0\n" % (stamp, hexpay, cnt))
        extra = rng.random()
        if extra < 0.05:
            lines.append("duplicate packet: %s (0.002 s) (+%d smp)\n" % (hexpay, rng.randrange(1, 20)))
        elif extra < 0.08:
            lines.append("repeat packet: %s (2.812 s)\n" % hexpay)
        elif extra < 0.10:
            lines.append("burst %s: %s (+%d smp)\n" % (rng.choice(["copy", "conflict"]), hexpay,
                                                        rng.randrange(1, 9)))
        elif extra < 0.12:
            lines.append("crc_stats: crc_fail=3 near=1 slots=0:2,3:1\n")
        elif extra < 0.14:
            lines.append("some unrelated Go chatter\n")
        out.append((clock, False, lines))
        if i == 300:
            out.append((clock + 1, True, []))    # a hot swap mid-stream
            clock += 1
    for k in range(1, 6):                        # a data drought: hops only, no DATA
        clock += 100
        out.append((clock, False, ["%02d:00:00.000000 Hop: {ChannelIdx:%d ChannelFreq:902355835 "
                                   "FreqError:%d Transmitter:0}\n" % (k, k % 5, 10 * k),
                                   "just noise\n"]))
    return out


class _Mgr:
    """ProcManager stand-in: each running() call advances to the next scripted pass."""

    def __init__(self, batches, clock, stall_at_end):
        self.batches = list(batches)
        self.clock = clock
        self.stall_at_end = stall_at_end
        self.current = (T0, False, [])

    def running(self):
        if not self.batches:
            if self.stall_at_end:
                self.clock[0] += 10_000          # past any stall timeout
                return True
            return False
        self.current = self.batches.pop(0)
        self.clock[0] = self.current[0]
        return True

    def get_stderr(self):
        return iter([list(self.current[2])])

    def drain_stderr(self, max_lines=50):
        return ["last words"]


class _Capture(logging.Handler):
    def __init__(self, events):
        super().__init__(level=logging.DEBUG)
        self.events = events

    def emit(self, record):
        self.events.append(["log", record.levelname, record.getMessage()])


def _driver(mgr):
    d = make_driver(active_tr_ids=(0,))
    d.tr_count = 1
    d.frequency = 'US'
    d.channels = dict(DEFAULT_CHANNELS)
    d.sensor_map = dict(rtldavis.RtldavisDriver.DEFAULT_SENSOR_MAP)
    d.rain_per_tip = 0.254
    d.last_rain_count = None
    d.last_accepted_rain_count = None
    d.last_hum = None
    d._sensor_qc_enabled = True
    d._sensor_qc = rtldavis.SensorQC()
    d._log_humidity_raw = True
    d._last_pkt = None
    d._stderr_sample_count = 0
    d._pending_freq_fields = {}
    d._mgr = mgr
    d._maybe_hotswap = lambda: mgr.current[1]
    return d


def _run(monkeypatch, stall_at_end):
    events = []
    clock = [T0]
    monkeypatch.setattr(rtldavis.time, 'time', lambda: clock[0])
    for name in ('DEBUG_PARSE', 'DEBUG_RTLD', 'DEBUG_RAIN'):
        monkeypatch.setattr(rtldavis, name, 3)
    handler = _Capture(events)
    old_level = rtldavis.log.level
    rtldavis.log.addHandler(handler)
    rtldavis.log.setLevel(logging.DEBUG)
    mgr = _Mgr(_batches(), clock, stall_at_end)
    d = _driver(mgr)
    try:
        for packet in d.genLoopPackets():
            events.append(["packet", sorted(packet.items())])
    except rtldavis.weewx.WeeWxIOError as e:
        events.append(["exit", str(e)])
    finally:
        rtldavis.log.removeHandler(handler)
        rtldavis.log.setLevel(old_level)
    stats = {k: d.stats[k] for k in ('dup_count', 'repeat_count', 'crc_fail', 'crc_near',
                                     'crc_slots', 'burst_copy', 'burst_conflict',
                                     'dup_gap_max', 'count', 'missed')}
    state = {'last_rain_count': d.last_rain_count,
             'last_accepted_rain_count': d.last_accepted_rain_count,
             'qc_baseline': sorted(d._sensor_qc._baseline.items()),
             'pending_freq': sorted(d._pending_freq_fields.items())}
    return {'events': events, 'stats': stats, 'state': state}


def _snapshot(monkeypatch):
    return {'stall': _run(monkeypatch, True), 'exit': _run(monkeypatch, False)}


def _digest(snap):
    return hashlib.sha256(json.dumps(snap, sort_keys=True, default=repr)
                          .encode()).hexdigest()


def test_emitted_packets_and_log_lines_are_unchanged(monkeypatch):
    snap = _snapshot(monkeypatch)
    digest = _digest(snap)
    if digest != EXPECTED_SHA256:
        with tempfile.NamedTemporaryFile('w', suffix='.json', prefix='driver_snapshot_',
                                         delete=False) as f:
            json.dump(snap, f, indent=1, sort_keys=True, default=repr)
        raise AssertionError("driver output changed: digest %s, snapshot written to %s"
                             % (digest, f.name))


def test_stream_exercises_every_path(monkeypatch):
    """The digest only means something if the stream reaches every branch the refactor
    touches. Each needle below is a log line one of those branches writes."""
    snap = _snapshot(monkeypatch)
    text = "\n".join(e[2] for e in snap['stall']['events'] if e[0] == 'log')
    needles = [
        "out of sensor range",                       # bounds reject (pre-pass)
        "frame failed bounds proof",                 # co-rejection, bounds
        "frame failed message-type proof",           # co-rejection, impossible type
        "frame failed bounds + message-type proof",  # both proofs at once
        "exceeds",                                   # delta reject (check())
        "wind_speed: rejecting",                     # the wind_dir side effect
        "rain: skipping counter from co-rejected frame",
        "rain: rejecting implausible counter delta",
        "rain: counter recovered",
        "ignoring repeat packet",
        "Go burst gate dropped a frame",
        "DATA DROUGHT",
        "STALL DIAGNOSIS",
    ]
    missing = [n for n in needles if n not in text]
    assert not missing, missing
    packets = [dict(e[1]) for e in snap['stall']['events'] if e[0] == 'packet']
    assert any(p.get('windSpeed') == 0.0 and p.get('windDir') is None for p in packets)
    assert snap['exit']['events'][-1] == ['exit', 'rtldavis process is not running']
