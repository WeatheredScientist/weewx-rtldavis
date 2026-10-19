package protocol

// Differential probe (#458): feeds the REAL Parse a fixed sequence of synthetic frames
// and writes what it returned to $PARSE_OUT. tests/test_crcstats_patch.py runs it on
// the unpatched and the patched tree and requires the accepted messages to be
// byte-identical.  CRCFailTimes is read by reflection so the file compiles on both.

import (
	"fmt"
	"os"
	"reflect"
	"strings"
	"testing"

	"github.com/lheijst/rtldavis/dsp"
)

func frame(p *Parser, payload []byte, flip int) dsp.Packet {
	body := make([]byte, 0, 8)
	body = append(body, payload...)
	c := p.Checksum(body)
	body = append(body, byte(c>>8), byte(c))
	if p.Checksum(body) != 0 {
		panic("test frame CRC does not close")
	}
	raw := append([]byte{0xCB, 0x89}, body...) // two sync bytes, then the checked part
	if flip >= 0 {
		raw[2+flip/8] ^= 1 << (uint(flip) % 8)
	}
	for i := range raw {
		raw[i] = SwapBitOrder(raw[i]) // Parse swaps bit order first; undo it
	}
	return dsp.Packet{Idx: 0, Data: raw}
}

func TestParseProbe(t *testing.T) {
	out := os.Getenv("PARSE_OUT")
	if out == "" {
		t.Skip("PARSE_OUT not set")
	}
	var sb strings.Builder
	cases := [][]struct {
		payload []byte
		flip    int
	}{
		{{[]byte{0x80, 1, 2, 3, 4, 5}, -1}, {[]byte{0x80, 1, 2, 3, 4, 5}, 9}, {[]byte{0x80, 1, 2, 3, 4, 5}, -1}},
		{{[]byte{0x41, 9, 8, 7, 6, 5}, 3}, {[]byte{0x41, 9, 8, 7, 6, 5}, -1}},
		{{[]byte{0x22, 0, 0, 0, 0, 0}, 40}, {[]byte{0x22, 0, 0, 0, 0, 0}, 41}},
		{{[]byte{0x03, 7, 7, 7, 7, 7}, -1}, {[]byte{0x13, 7, 7, 7, 7, 7}, -1}},
	}
	for i, c := range cases {
		p := NewParser(14, "US")
		p.Demodulator.Discriminated = make([]float64, 100000)
		var pkts []dsp.Packet
		for _, f := range c {
			pkts = append(pkts, frame(&p, f.payload, f.flip))
		}
		msgs := p.Parse(pkts)
		fmt.Fprintf(&sb, "case%d msgs=%d\n", i, len(msgs))
		for _, m := range msgs {
			fmt.Fprintf(&sb, "case%d msg id=%d data=%02X\n", i, m.ID, m.Data)
		}
		if f := reflect.ValueOf(&p).Elem().FieldByName("CRCFailTimes"); f.IsValid() {
			fmt.Fprintf(&sb, "FAILS case%d %d\n", i, f.Len())
		}
	}
	if err := os.WriteFile(out, []byte(sb.String()), 0644); err != nil {
		t.Fatal(err)
	}
}
