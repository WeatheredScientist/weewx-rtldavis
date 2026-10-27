package burstgate

// #459 / DEC-0223: synthetic Davis bursts replayed through the REAL Demodulate and
// Parse (the vendored packages main.go builds against), block by block, the way
// main.go feeds them. It proves the mechanism and the arithmetic the gate rests on:
//
//   - a burst whose preamble run straddles a block boundary is decoded from two
//     consecutive blocks, and its two positions differ by a few samples, far
//     inside the window;
//   - every burst is decoded, and the gate, applied the way main.go applies it,
//     keeps exactly one frame per burst;
//   - the next transmission, 2.5625 s later, is a separate frame and passes;
//   - a CRC-valid corrupted copy planted in the next block (the 1-in-65,536
//     case), which the duplicate filter passes, is dropped; two distinct
//     CRC-valid frames in one block are both dropped.
//
// tests/test_burstgate_patch.py copies this file into the patched tree's
// burstgate/ directory. gateRun mirrors main.go's order of checks; the static
// audit in that test pins main.go's side of the same lines.

import (
	"bytes"
	"math"
	"math/rand"
	"testing"

	"github.com/lheijst/rtldavis/protocol"
)

const (
	sps       = 14     // samples per symbol
	fs        = 268800 // 19,200 baud x 14
	blockSize = 512
	loop0     = 688800 // 2.5625 s, transmitter id 0's loop period, in samples
)

func swapBits(b byte) byte {
	b = ((b & 0xF0) >> 4) | ((b & 0x0F) << 4)
	b = ((b & 0xCC) >> 2) | ((b & 0x33) << 2)
	b = ((b & 0xAA) >> 1) | ((b & 0x55) << 1)
	return b
}

// airBits builds one Davis frame as transmitted: a 0xAA lead-in, the 0xCB89 sync
// word the preamble finder searches for, then the six payload bytes and the
// CRC, each sent least-significant bit first (Parse swaps them back).
func airBits(p *protocol.Parser, payload []byte) []byte {
	body := append([]byte{}, payload...)
	c := p.Checksum(body)
	body = append(body, byte(c>>8), byte(c))
	var bits []byte
	put := func(b byte) {
		for i := 7; i >= 0; i-- {
			bits = append(bits, (b>>uint(i))&1)
		}
	}
	for i := 0; i < 4; i++ {
		put(0xAA)
	}
	put(0xCB)
	put(0x89)
	for _, b := range body {
		put(swapBits(b))
	}
	put(0xAA)
	return bits
}

// stream renders bursts as 8-bit IQ the way the dongle delivers it: continuous
// phase 2-FSK at +/-25 kHz, offset -fs/4 (Demodulate rotates by +fs/4), over a
// low noise floor so the silence between bursts is realistic.
func stream(n int, bursts map[int][]byte, rng *rand.Rand) []byte {
	out := make([]byte, 2*n)
	phase := 0.0
	var cur []byte
	curAt := -1
	for i := 0; i < n; i++ {
		if b, ok := bursts[i]; ok {
			cur, curAt = b, i
		}
		f := -float64(fs) / 4
		amp := 0.0
		if cur != nil {
			k := (i - curAt) / sps
			if k < len(cur) {
				amp = 0.7
				if cur[k] == 1 {
					f += 25000
				} else {
					f -= 25000
				}
			} else {
				cur = nil
			}
		}
		phase += 2 * math.Pi * f / fs
		re := amp*math.Cos(phase) + 0.02*rng.NormFloat64()
		im := amp*math.Sin(phase) + 0.02*rng.NormFloat64()
		out[2*i] = byte(math.Max(0, math.Min(255, math.Round(127.4+127.6*re))))
		out[2*i+1] = byte(math.Max(0, math.Min(255, math.Round(127.4+127.6*im))))
	}
	return out
}

type decode struct {
	block int64
	pos   int64
	data  []byte
}

// demodulate feeds the stream to the real Demodulate and Parse one block at a
// time, numbering blocks the way main.go does (blockNum++ after each read).
func demodulate(iq []byte) (batches [][]decode) {
	p := protocol.NewParser(14, "US")
	var blockNum int64
	for off := 0; off+2*blockSize <= len(iq); off += 2 * blockSize {
		blockNum++
		var batch []decode
		for _, m := range p.Parse(p.Demodulate(iq[off : off+2*blockSize])) {
			batch = append(batch, decode{blockNum, Pos(blockNum, blockSize, m.Idx), m.Data})
		}
		if len(batch) > 0 {
			batches = append(batches, batch)
		}
	}
	return
}

// gateRun applies main.go's checks in main.go's order: the DEC-0135 duplicate
// filter (identical bytes within dupwindow, 500 ms), then the burst conflict,
// then the burst copy, then accept.
func gateRun(window int64, batches [][]decode) (accepted []decode, dups, copies, conflicts int) {
	g := New(window)
	var lastMsg []byte
	var lastPos int64
	const dupWindow = fs / 2 // 500 ms in samples
	for _, batch := range batches {
		pos := make([]int64, len(batch))
		for i, d := range batch {
			pos[i] = d.pos
		}
		conflict := g.Conflicts(pos)
		for i, d := range batch {
			if lastMsg != nil && bytes.Equal(d.data, lastMsg) && d.pos-lastPos < dupWindow {
				dups++
				continue
			}
			if conflict[i] >= 0 {
				conflicts++
				continue
			}
			if g.Copy(d.pos) {
				copies++
				continue
			}
			lastMsg, lastPos = d.data, d.pos
			g.Accept(d.pos)
			accepted = append(accepted, d)
		}
	}
	return
}

const window = 16*sps + 80*sps // what main.go derives from the packet config

var payloadA = []byte{0x80, 0x12, 0x34, 0x56, 0x78, 0x9A}
var payloadB = []byte{0x80, 0x12, 0x34, 0x56, 0x78, 0x9B}

func TestEveryOffsetDecodesAndTheGateKeepsOneFrame(t *testing.T) {
	p := protocol.NewParser(14, "US")
	bits := airBits(&p, payloadA)
	rng := rand.New(rand.NewSource(1))
	straddles, maxGap := 0, int64(0)
	for start := 4000; start < 4000+blockSize; start++ {
		iq := stream(start+len(bits)*sps+6*blockSize, map[int][]byte{start: bits}, rng)
		batches := demodulate(iq)
		var all []decode
		for _, b := range batches {
			all = append(all, b...)
		}
		if len(all) == 0 {
			t.Fatalf("start %d: the burst was not decoded at all", start)
		}
		for _, d := range all {
			if !bytes.Equal(d.data[:6], payloadA) {
				t.Fatalf("start %d: decoded %02X, want %02X", start, d.data, payloadA)
			}
		}
		if len(batches) > 1 {
			straddles++
			if batches[1][0].block != batches[0][0].block+1 {
				t.Fatalf("start %d: second decode not from the next block", start)
			}
			gap := batches[1][0].pos - batches[0][0].pos
			if gap < 0 {
				gap = -gap
			}
			if gap > maxGap {
				maxGap = gap
			}
		}
		accepted, _, _, _ := gateRun(window, batches)
		if len(accepted) != 1 {
			t.Fatalf("start %d: the gate kept %d frames of one burst", start, len(accepted))
		}
	}
	t.Logf("%d of %d start offsets decoded from two blocks; largest gap %d samples", straddles, blockSize, maxGap)
	if straddles == 0 {
		t.Fatal("no start offset straddled a block boundary: the replay cannot exercise the mechanism")
	}
	if maxGap >= window || maxGap > 2*sps {
		t.Fatalf("a same-burst re-decode sat %d samples away", maxGap)
	}
}

func straddlingStart(t *testing.T, bits []byte) int {
	rng := rand.New(rand.NewSource(2))
	for start := 4000; start < 4000+blockSize; start++ {
		iq := stream(start+len(bits)*sps+6*blockSize, map[int][]byte{start: bits}, rng)
		if len(demodulate(iq)) > 1 {
			return start
		}
	}
	t.Fatal("no straddling start found")
	return 0
}

func TestTheNextTransmissionPasses(t *testing.T) {
	p := protocol.NewParser(14, "US")
	bitsA, bitsB := airBits(&p, payloadA), airBits(&p, payloadB)
	start := straddlingStart(t, bitsA)
	rng := rand.New(rand.NewSource(3))
	n := start + loop0 + len(bitsB)*sps + 6*blockSize
	batches := demodulate(stream(n, map[int][]byte{start: bitsA, start + loop0: bitsB}, rng))
	accepted, dups, _, _ := gateRun(window, batches)
	if len(accepted) != 2 || !bytes.Equal(accepted[1].data[:6], payloadB) {
		t.Fatalf("accepted %d frames, want A then B", len(accepted))
	}
	if dups != 1 {
		t.Fatalf("the straddling burst's identical copy was not the duplicate filter's: dups=%d", dups)
	}
	// The same payload re-sent one loop later is a new transmission too.
	batches = demodulate(stream(n, map[int][]byte{start: bitsA, start + loop0: bitsA}, rng))
	if accepted, _, _, _ := gateRun(window, batches); len(accepted) != 2 {
		t.Fatalf("an unchanged re-send was gated: %d accepted", len(accepted))
	}
}

func TestAPlantedCorruptedCopyIsDropped(t *testing.T) {
	p := protocol.NewParser(14, "US")
	bitsA := airBits(&p, payloadA)
	start := straddlingStart(t, bitsA)
	rng := rand.New(rand.NewSource(4))
	batches := demodulate(stream(start+len(bitsA)*sps+6*blockSize, map[int][]byte{start: bitsA}, rng))
	if len(batches) < 2 {
		t.Fatal("no second decode to plant into")
	}
	// The 1-in-65,536 case: the next block's copy carries different, CRC-valid
	// bytes. The duplicate filter compares bytes, so it lets this through.
	corrupt := append(append([]byte{}, payloadB...), 0, 0)
	batches[1][0].data = corrupt
	accepted, dups, copies, _ := gateRun(window, batches)
	if len(accepted) != 1 || !bytes.Equal(accepted[0].data[:6], payloadA) {
		t.Fatalf("accepted %v, want only the original", accepted)
	}
	if dups != 0 || copies != 1 {
		t.Fatalf("dups=%d copies=%d, want the copy caught by the burst gate", dups, copies)
	}
	// POSITIVE CONTROL: with no window the corrupted copy reaches the driver.
	if accepted, _, _, _ := gateRun(0, batches); len(accepted) != 2 {
		t.Fatalf("with the gate off, %d accepted: the planted copy proves nothing", len(accepted))
	}
}

func TestTwoDistinctFramesInOneBlockAreBothDropped(t *testing.T) {
	batches := [][]decode{{
		{block: 9, pos: 5000, data: append(append([]byte{}, payloadA...), 0, 0)},
		{block: 9, pos: 5003, data: append(append([]byte{}, payloadB...), 0, 0)},
	}}
	accepted, _, _, conflicts := gateRun(window, batches)
	if len(accepted) != 0 || conflicts != 2 {
		t.Fatalf("accepted %d, conflicts %d; want 0 and 2", len(accepted), conflicts)
	}
}
