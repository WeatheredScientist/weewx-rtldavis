package timegate

// #536 / DEC-0229: the gate's own rules. tests/test_timegate_patch.py copies this
// file into the patched tree's timegate/ directory and runs it.

import (
	"math/rand"
	"testing"
)

const (
	ms     = int64(1000000)
	period = 2812500 * int64(1000) // transmitter id 4, in ns
	tol    = 100 * ms
	anchor = int64(1730000000) * 1000000000
)

func TestAFrameOnScheduleHasNoOffset(t *testing.T) {
	for k := int64(0); k < 60; k++ {
		if d := Offset(anchor+k*period, anchor, period); d != 0 {
			t.Fatalf("slot %d: offset %d", k, d)
		}
	}
}

func TestTheOffsetIsSignedAndFoldsToTheNearestSlot(t *testing.T) {
	for _, c := range []struct{ arrival, want int64 }{
		{period + 7*ms, 7 * ms},
		{period - 7*ms, -7 * ms},
		{5*period + 40*ms, 40 * ms},
		{5*period - 40*ms, -40 * ms},
		{period / 2, period / 2},        // the farthest a frame can be
		{period/2 + 1, -(period/2 - 1)}, // one past it belongs to the next slot
		{-3*period + 9*ms, 9 * ms},      // before the anchor: another transmitter's handling can leave it ahead
		{-3*period - 9*ms, -9 * ms},
	} {
		if d := Offset(anchor+c.arrival, anchor, period); d != c.want {
			t.Errorf("arrival %d: offset %d, want %d", c.arrival, d, c.want)
		}
	}
}

func TestTheOffsetNeverExceedsHalfAPeriod(t *testing.T) {
	rng := rand.New(rand.NewSource(1))
	for i := 0; i < 100000; i++ {
		d := Offset(anchor+rng.Int63n(100*period)-50*period, anchor, period)
		if d > period/2 || d < -period/2 {
			t.Fatalf("offset %d", d)
		}
	}
}

func TestNoAnchorMeansNoSchedule(t *testing.T) {
	if d := Offset(anchor+123*ms, 0, period); d != 0 {
		t.Fatalf("offset %d with no anchor", d)
	}
}

func TestTheToleranceEdgeIsInclusive(t *testing.T) {
	for _, d := range []int64{0, 1, -1, tol, -tol} {
		if Off(d, tol) {
			t.Errorf("offset %d was gated", d)
		}
	}
	for _, d := range []int64{tol + 1, -tol - 1, period / 2} {
		if !Off(d, tol) {
			t.Errorf("offset %d passed", d)
		}
	}
}

func TestToleranceZeroTurnsTheGateOff(t *testing.T) {
	if Off(period/2, 0) || Off(-period/2, 0) || Off(period/2, -1) {
		t.Fatal("a tolerance of zero or less still gated a frame")
	}
}

// The real-frame case the tolerance must hold: the schedule through the last
// accepted frame advances at the nominal period while misses are booked, so the
// transmitter's clock error accumulates for up to 51 slots before a re-init. 100 ms
// covers a clock off by more than 600 ppm; the measured spread is 0.95 ms a frame.
func TestAClockErrorAcrossAFullMissRunStaysInside(t *testing.T) {
	const ppm = 600
	const maxmissed = 51
	real := period + period*ppm/1000000
	arrival := anchor + (maxmissed+1)*real
	if d := Offset(arrival, anchor, period); Off(d, tol) {
		t.Fatalf("a %d ppm clock was gated after %d misses: offset %d ms", ppm, maxmissed, d/ms)
	}
}

// The number DEC-0229 rests on: a random-phase frame passes 200 of 2812 ms.
func TestARandomPhaseFramePassesAboutSevenPercent(t *testing.T) {
	rng := rand.New(rand.NewSource(2))
	const n = 200000
	pass := 0
	for i := 0; i < n; i++ {
		if !Off(Offset(anchor+rng.Int63n(period), anchor, period), tol) {
			pass++
		}
	}
	if f := float64(pass) / n; f < 0.066 || f > 0.076 {
		t.Fatalf("pass fraction %.4f", f)
	}
}
