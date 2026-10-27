package burstgate

// #459 / DEC-0223: the gate's own rules. tests/test_burstgate_patch.py copies this
// file into the patched tree's burstgate/ directory and runs it.

import "testing"

const w = 1344 // one packet's airtime at 14 samples/symbol: 16 + 80 symbols

func TestNothingIsACopyBeforeTheFirstAccept(t *testing.T) {
	g := New(w)
	if g.Copy(0) || g.Copy(5) {
		t.Fatal("a frame was gated with no accepted frame to compare against")
	}
	if g.Gap(5) != -1 {
		t.Fatalf("Gap before any accept = %d, want -1", g.Gap(5))
	}
}

func TestCopyInsideTheWindowIsGated(t *testing.T) {
	g := New(w)
	g.Accept(1000)
	for _, d := range []int64{0, 1, 13, w - 1} {
		if !g.Copy(1000 + d) {
			t.Errorf("frame %d samples after the accepted one passed", d)
		}
		if !g.Copy(1000 - d) {
			t.Errorf("frame %d samples before the accepted one passed", d)
		}
	}
}

func TestTheWindowEdgeAndTheNextTransmissionPass(t *testing.T) {
	g := New(w)
	g.Accept(1000)
	if g.Copy(1000 + w) {
		t.Error("a frame exactly one window away was gated (the window is half-open)")
	}
	// The shortest loop period, transmitter id 0: 2.5625 s at 268,800 samples/s.
	if g.Copy(1000 + 688800) {
		t.Error("the next real transmission was gated")
	}
}

func TestOnlyAcceptMovesTheReference(t *testing.T) {
	g := New(w)
	g.Accept(0)
	// A chain of copies, each inside the window of the previous one but walking
	// past the window of the accepted frame. Copy must not ratchet the reference.
	for pos := int64(0); pos < 3*w; pos += w / 2 {
		g.Copy(pos)
	}
	if g.Gap(3*w) != 3*w {
		t.Fatalf("reference moved without an Accept: Gap = %d", g.Gap(3*w))
	}
	g.Accept(5000)
	if !g.Copy(5010) || g.Copy(10) {
		t.Fatal("Accept did not move the reference")
	}
}

func TestConflictsFlagEveryFrameOfOneBurstAndNothingElse(t *testing.T) {
	g := New(w)
	got := g.Conflicts([]int64{100, 103, 900000})
	want := []int64{3, 3, -1}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("Conflicts = %v, want %v", got, want)
		}
	}
	if c := g.Conflicts([]int64{100}); c[0] != -1 {
		t.Fatalf("a lone frame conflicted: %v", c)
	}
	if c := g.Conflicts(nil); len(c) != 0 {
		t.Fatalf("Conflicts(nil) = %v", c)
	}
	// The nearest neighbor is reported, and the window edge is half-open.
	// w+10 is exactly one window from 10, its nearest neighbor.
	c := g.Conflicts([]int64{0, 10, 4, w + 10})
	if c[0] != 4 || c[1] != 6 || c[2] != 4 || c[3] != -1 {
		t.Fatalf("Conflicts = %v, want [4 6 4 -1]", c)
	}
}

func TestConflictsDoNotDependOnTheReference(t *testing.T) {
	g := New(w)
	g.Accept(100)
	if c := g.Conflicts([]int64{50000}); c[0] != -1 {
		t.Fatalf("Conflicts read the accepted reference: %v", c)
	}
}

func TestPosIsExactAcrossBlocks(t *testing.T) {
	// The same sample seen at offset 520 in block 7 and offset 8 in block 8.
	if Pos(7, 512, 520) != Pos(8, 512, 8) {
		t.Fatal("Pos is not continuous across a block boundary")
	}
	if Pos(8, 512, 9)-Pos(7, 512, 520) != 1 {
		t.Fatal("Pos difference is not a sample count")
	}
}
