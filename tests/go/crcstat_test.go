package crcstat

// Unit tests for crcTracker (patch/rtldavis-crcstats.patch, #458).  Copied into the
// patched rtldavis tree and run with `go test` by tests/test_crcstats_patch.py.

import (
	"math/rand"
	"strings"
	"testing"
)

const ms = int64(1000000)

func newT() *Tracker { return New(100*ms, 60000*ms) }

func TestFailAfterAcceptWithinWindowIsNear(t *testing.T) {
	c := newT()
	c.Accept(1000 * ms)
	c.Fail(1002*ms, 5)
	if c.fails != 1 || c.near != 1 {
		t.Fatalf("fails=%d near=%d", c.fails, c.near)
	}
}

func TestFailLongAfterAcceptIsNotNear(t *testing.T) {
	c := newT()
	c.Accept(1000 * ms)
	c.Fail(1000*ms+100*ms, 5) // exactly the window: not near (strict <)
	c.Fail(5000*ms, 5)
	if c.fails != 2 || c.near != 0 {
		t.Fatalf("fails=%d near=%d", c.fails, c.near)
	}
}

func TestFailBeforeAcceptIsNearWhenAcceptArrives(t *testing.T) {
	c := newT()
	c.Fail(1000*ms, 7)
	if c.near != 0 {
		t.Fatal("near counted before any accept")
	}
	c.Accept(1003 * ms)
	if c.near != 1 {
		t.Fatalf("near=%d", c.near)
	}
	c.Accept(1004 * ms) // a second accept must not recount it
	if c.near != 1 {
		t.Fatalf("recounted: near=%d", c.near)
	}
}

func TestSeveralFailuresBeforeOneAcceptAllCount(t *testing.T) {
	c := newT()
	c.Fail(1000*ms, 1)
	c.Fail(1010*ms, 1)
	c.Fail(1020*ms, 1)
	c.Accept(1030 * ms)
	if c.fails != 3 || c.near != 3 {
		t.Fatalf("fails=%d near=%d", c.fails, c.near)
	}
}

func TestStaleFailureIsNotNearALaterAccept(t *testing.T) {
	c := newT()
	c.Fail(1000*ms, 1)
	c.Accept(3000 * ms)
	if c.near != 0 {
		t.Fatalf("near=%d", c.near)
	}
}

func TestNoDoubleCountWhenNearBothNeighbors(t *testing.T) {
	c := newT()
	c.Accept(1000 * ms)
	c.Fail(1010*ms, 1)  // near the earlier accept
	c.Accept(1020 * ms) // and near this one too
	if c.fails != 1 || c.near != 1 {
		t.Fatalf("fails=%d near=%d", c.fails, c.near)
	}
}

func TestNeverNearWithoutAnyAccept(t *testing.T) {
	c := newT()
	for i := int64(0); i < 10; i++ {
		c.Fail(1000*ms+i*ms, 3)
	}
	if c.near != 0 {
		t.Fatalf("near=%d", c.near)
	}
}

func TestSlotClampAndPerSlotCounts(t *testing.T) {
	c := newT()
	c.Fail(1*ms, -4)
	c.Fail(2*ms, 9999)
	c.Fail(3*ms, 17)
	c.Fail(4*ms, 17)
	if c.perSlot[crcSlots-1] != 2 || c.perSlot[17] != 2 {
		t.Fatalf("perSlot=%v", c.perSlot)
	}
}

func TestPendingIsCapped(t *testing.T) {
	c := newT()
	for i := int64(0); i < 1000; i++ {
		c.Fail(1000*ms+i, 1) // 1000 failures inside one window
	}
	if len(c.pending) > 256 {
		t.Fatalf("pending=%d", len(c.pending))
	}
	if c.fails != 1000 {
		t.Fatalf("fails=%d", c.fails)
	}
}

func TestReportCadenceFormatAndReset(t *testing.T) {
	c := newT()
	if _, ok := c.Report(1000 * ms); ok {
		t.Fatal("first call must only start the clock")
	}
	if _, ok := c.Report(1000*ms + 59999*ms); ok {
		t.Fatal("reported early")
	}
	c.Accept(30000 * ms)
	c.Fail(30005*ms, 17)
	c.Fail(40000*ms, 22)
	line, ok := c.Report(1000*ms + 60000*ms)
	if !ok || line != "crc_stats: crc_fail=2 near=1 slots=17:1,22:1" {
		t.Fatalf("ok=%v line=%q", ok, line)
	}
	line, ok = c.Report(1000*ms + 120000*ms)
	if !ok || line != "crc_stats: crc_fail=0 near=0 slots=-" {
		t.Fatalf("after reset: ok=%v line=%q", ok, line)
	}
	if strings.Contains(line, "\n") {
		t.Fatal("multi-line")
	}
}

// Property: against a brute-force oracle, over random event streams.
func TestMatchesBruteForceOracle(t *testing.T) {
	rng := rand.New(rand.NewSource(458))
	for trial := 0; trial < 3000; trial++ {
		type ev struct {
			t    int64
			fail bool
		}
		var evs []ev
		now := int64(1000) * ms
		n := 5 + rng.Intn(40)
		for i := 0; i < n; i++ {
			now += int64(rng.Intn(400)) * ms / 4 // 0..100 ms steps, so windows overlap a lot
			evs = append(evs, ev{now, rng.Intn(2) == 0})
		}
		c := newT()
		for _, e := range evs {
			if e.fail {
				c.Fail(e.t, rng.Intn(60))
			} else {
				c.Accept(e.t)
			}
		}
		want, wantFails := 0, 0
		for _, f := range evs {
			if !f.fail {
				continue
			}
			wantFails++
			for _, a := range evs {
				if !a.fail && abs(f.t-a.t) < 100*ms {
					want++
					break
				}
			}
		}
		if c.fails != wantFails || c.near != want {
			t.Fatalf("trial %d: got fails=%d near=%d, oracle fails=%d near=%d, events=%v", trial, c.fails, c.near, wantFails, want, evs)
		}
	}
}

func abs(x int64) int64 {
	if x < 0 {
		return -x
	}
	return x
}
