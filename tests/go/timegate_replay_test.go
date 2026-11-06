package burstgate

// #536 / DEC-0229: synthetic frames replayed through the REAL Demodulate and Parse,
// then through the checks main.go applies, in main.go's order. It proves:
//
//   - a CRC-valid frame off the schedule is dropped and does not move the anchor,
//     so the real frames that follow stay on schedule;
//   - with the gate off the same frame is accepted and moves the anchor, and the
//     next real frame sits a random phase away: the failure the gate exists to stop;
//   - real frames pass at every start offset, across missed slots too;
//   - the first frame always anchors, wherever it falls.
//
// Time here is the sample position, exact to the sample. main.go reads the wall
// clock when it handles the frame, so prod adds the 0.95 ms spread DEC-0229 measured;
// the tolerance is about 100 times that.
//
// tests/test_timegate_patch.py copies this file into the patched tree's burstgate/
// directory beside burst_replay_test.go, whose helpers it uses. timeRun mirrors
// main.go; the static audit in that test pins main.go's side of the same lines.

import (
	"bytes"
	"math/rand"
	"testing"

	"github.com/lheijst/rtldavis/protocol"
	"lheijst/rtldavis/timegate"
)

const (
	loop4     = 756000 // 2.8125 s, transmitter id 4's loop period, in samples
	periodNs  = int64(2812500000)
	tolerance = int64(100000000) // the -tolerance default, in ns
)

func ns(pos int64) int64 {
	return pos * 1000000000 / fs
}

// timeRun applies main.go's checks in main.go's order: the DEC-0135 duplicate
// filter, the burst conflict, the burst copy, the time gate, then accept. As in
// main.go, the gate is inactive until the first frame has anchored the transmitter.
func timeRun(tol int64, batches [][]decode) (accepted []decode, offsched int, anchor int64) {
	g := New(window)
	var lastMsg []byte
	var lastPos int64
	const dupWindow = fs / 2
	synced := false
	for _, batch := range batches {
		pos := make([]int64, len(batch))
		for i, d := range batch {
			pos[i] = d.pos
		}
		conflict := g.Conflicts(pos)
		for i, d := range batch {
			if lastMsg != nil && bytes.Equal(d.data, lastMsg) && d.pos-lastPos < dupWindow {
				continue
			}
			if conflict[i] >= 0 || g.Copy(d.pos) {
				continue
			}
			if synced && timegate.Off(timegate.Offset(ns(d.pos), anchor, periodNs), tol) {
				offsched++
				continue
			}
			lastMsg, lastPos = d.data, d.pos
			g.Accept(d.pos)
			anchor = ns(d.pos)
			synced = true
			accepted = append(accepted, d)
		}
	}
	return
}

var (
	real1 = []byte{0x84, 0x12, 0x34, 0x56, 0x78, 0x01}
	real2 = []byte{0x84, 0x12, 0x34, 0x56, 0x78, 0x02}
	real3 = []byte{0x84, 0x12, 0x34, 0x56, 0x78, 0x03}
	noise = []byte{0xE4, 0xFE, 0x21, 0x00, 0x77, 0x55} // id 4 too: the case that re-anchors
)

// plant renders frames at sample offsets and decodes them.
func plant(t *testing.T, seed int64, frames map[int][]byte) [][]decode {
	t.Helper()
	p := protocol.NewParser(14, "US")
	bursts := map[int][]byte{}
	last := 0
	for at, payload := range frames {
		bursts[at] = airBits(&p, payload)
		if at > last {
			last = at
		}
	}
	rng := rand.New(rand.NewSource(seed))
	return demodulate(stream(last+len(bursts[last])*sps+6*blockSize, bursts, rng))
}

func payloads(accepted []decode) [][]byte {
	var out [][]byte
	for _, d := range accepted {
		out = append(out, d.data[:6])
	}
	return out
}

func same(a, b [][]byte) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if !bytes.Equal(a[i], b[i]) {
			return false
		}
	}
	return true
}

func TestANoiseDecodeIsDroppedAndTheStationStaysOnSchedule(t *testing.T) {
	const start = 4000
	const off = 300000 // 1.116 s after the second frame: a random phase
	batches := plant(t, 5, map[int][]byte{
		start:               real1,
		start + loop4:       real2,
		start + loop4 + off: noise,
		start + 2*loop4:     real3,
	})
	accepted, offsched, anchor := timeRun(tolerance, batches)
	if !same(payloads(accepted), [][]byte{real1, real2, real3}) {
		t.Fatalf("accepted %02X", payloads(accepted))
	}
	if offsched != 1 {
		t.Fatalf("offsched=%d", offsched)
	}
	if d := timegate.Offset(anchor, ns(accepted[0].pos), periodNs); timegate.Off(d, 1000000) {
		t.Fatalf("the anchor moved %d ns off the first frame's schedule", d)
	}

	// POSITIVE CONTROL: with the gate off the same frame is accepted and re-anchors,
	// which puts the next real frame most of a second off the clock.
	accepted, offsched, _ = timeRun(0, batches)
	if len(accepted) != 4 || offsched != 0 {
		t.Fatalf("gate off: accepted %d, offsched %d", len(accepted), offsched)
	}
	if !bytes.Equal(accepted[2].data[:6], noise) {
		t.Fatalf("gate off: third frame %02X, want the noise decode", accepted[2].data)
	}
	if d := timegate.Offset(ns(accepted[3].pos), ns(accepted[2].pos), periodNs); !timegate.Off(d, tolerance) {
		t.Fatalf("gate off: the noise decode left the next real frame only %d ns off", d)
	}
}

func TestRealFramesPassAtEveryStartOffset(t *testing.T) {
	for start := 4000; start < 4000+blockSize; start += 7 {
		batches := plant(t, int64(start), map[int][]byte{
			start:         real1,
			start + loop4: real2,
		})
		accepted, offsched, _ := timeRun(tolerance, batches)
		if len(accepted) != 2 || offsched != 0 {
			t.Fatalf("start %d: accepted %d, offsched %d", start, len(accepted), offsched)
		}
		if d := timegate.Offset(ns(accepted[1].pos), ns(accepted[0].pos), periodNs); d > 1000000 || d < -1000000 {
			t.Fatalf("start %d: a real frame sat %d ns off", start, d)
		}
	}
}

func TestARealFrameAfterMissedSlotsPasses(t *testing.T) {
	const start = 4100
	batches := plant(t, 6, map[int][]byte{
		start:           real1,
		start + 3*loop4: real2, // two slots with nothing heard
	})
	accepted, offsched, _ := timeRun(tolerance, batches)
	if len(accepted) != 2 || offsched != 0 {
		t.Fatalf("accepted %d, offsched %d", len(accepted), offsched)
	}
}

func TestTheFirstFrameAnchorsWhereverItFalls(t *testing.T) {
	const start = 123457
	accepted, offsched, anchor := timeRun(tolerance, plant(t, 7, map[int][]byte{start: real1}))
	if len(accepted) != 1 || offsched != 0 || anchor != ns(accepted[0].pos) {
		t.Fatalf("accepted %d, offsched %d", len(accepted), offsched)
	}
}

// The known limit, 7% of noise decodes: a frame inside the tolerance is accepted and
// moves the anchor by its offset. The next real frame still passes, and the driver's
// payload filters stay the second net (DEC-0229).
func TestANoiseDecodeInsideTheToleranceIsTheKnownLimit(t *testing.T) {
	const start = 4000
	const off = 13440 // 50 ms
	accepted, offsched, _ := timeRun(tolerance, plant(t, 8, map[int][]byte{
		start:               real1,
		start + loop4 + off: noise,
		start + 2*loop4:     real3,
	}))
	if len(accepted) != 3 || offsched != 0 {
		t.Fatalf("accepted %d, offsched %d", len(accepted), offsched)
	}
}
