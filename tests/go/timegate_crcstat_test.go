package crcstat

// #536 / DEC-0229: the time gate's count in the crc_stats line. Lives apart from
// crcstat_test.go, which runs against the crcstats patch alone, where the line has
// no offsched field. tests/test_timegate_patch.py copies this file into the patched
// tree's crcstat/ directory and runs it.

import "testing"

func TestOffSchedIsReportedAndResets(t *testing.T) {
	const every = int64(60e9)
	c := New(int64(100e6), every)
	c.Report(1)
	c.Fail(2, 17)
	c.OffSched()
	c.OffSched()
	line, ok := c.Report(1 + every)
	if !ok || line != "crc_stats: crc_fail=1 near=0 offsched=2 slots=17:1" {
		t.Fatalf("got %q", line)
	}
	line, ok = c.Report(1 + 2*every)
	if !ok || line != "crc_stats: crc_fail=0 near=0 offsched=0 slots=-" {
		t.Fatalf("got %q", line)
	}
}

func TestOffSchedDoesNotTouchTheFailureCounts(t *testing.T) {
	const every = int64(60e9)
	c := New(int64(100e6), every)
	c.Report(1)
	c.OffSched()
	if c.fails != 0 || c.near != 0 || c.lastAccept != 0 {
		t.Fatalf("fails=%d near=%d lastAccept=%d", c.fails, c.near, c.lastAccept)
	}
}
