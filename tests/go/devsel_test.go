package devsel

// DEC-0235: the dongle-selection rules. tests/test_devsel_patch.py copies this file
// and devsel_cases.json into the patched tree's devsel/ directory and runs it. The
// same table drives doctor.select_dongle (tests/test_devsel.py), so the decoder and
// the doctor cannot pick differently.

import (
	"encoding/json"
	"os"
	"strings"
	"testing"
)

type tcase struct {
	Name    string      `json:"name"`
	Serials []string    `json:"serials"`
	Arg     string      `json:"arg"`
	Given   bool        `json:"given"`
	Outcome interface{} `json:"outcome"`
	Warn    bool        `json:"warn"`
}

func load(t *testing.T) []tcase {
	raw, err := os.ReadFile("devsel_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var table struct {
		Cases []tcase `json:"cases"`
	}
	if err := json.Unmarshal(raw, &table); err != nil {
		t.Fatal(err)
	}
	if len(table.Cases) < 20 {
		t.Fatalf("only %d cases loaded", len(table.Cases))
	}
	return table.Cases
}

func dongles(serials []string) []Dongle {
	ds := make([]Dongle, len(serials))
	for i, s := range serials {
		ds[i] = Dongle{"Maker", "Stick", s}
	}
	return ds
}

func TestTheSharedCaseTable(t *testing.T) {
	for _, c := range load(t) {
		i, warn, err := Pick(c.Arg, c.Given, dongles(c.Serials))
		if c.Outcome == "error" {
			if err == nil {
				t.Errorf("%s: picked %d, want an error", c.Name, i)
			}
			continue
		}
		want := int(c.Outcome.(float64))
		if err != nil || i != want {
			t.Errorf("%s: got %d, %v; want %d", c.Name, i, err, want)
		}
		if (warn != "") != c.Warn {
			t.Errorf("%s: warning %q, want one: %v", c.Name, warn, c.Warn)
		}
	}
}

func TestErrorsAndWarningsNameEveryDongleAndTheFix(t *testing.T) {
	ds := []Dongle{{"Realtek", "RTL2838UHIDIR", "DUP"}, {"RTLSDRBlog", "Blog V4", "DUP"}}
	_, _, err := Pick("DUP", true, ds)
	if err == nil || !strings.Contains(err.Error(), "unique serial") ||
		!strings.Contains(err.Error(), "0: Realtek RTL2838UHIDIR SN DUP") ||
		!strings.Contains(err.Error(), "1: RTLSDRBlog Blog V4 SN DUP") {
		t.Fatalf("ambiguity error: %v", err)
	}
	ds[1].Serial = "WXV4"
	_, warn, _ := Pick("0", false, ds)
	if !strings.HasPrefix(warn, "dongle: WARNING:") || !strings.Contains(warn, "set -d to a serial") {
		t.Fatalf("warning: %q", warn)
	}
}

func TestDescribeNamesTheOpenedDongle(t *testing.T) {
	ds := []Dongle{{"Realtek", "RTL2838UHIDIR", "SER1"}, {"RTLSDRBlog", "Blog V4", "WXV4"}}
	if got := Describe(1, ds); got != "dongle: using 1 of 2: RTLSDRBlog Blog V4 SN WXV4" {
		t.Fatalf("got %q", got)
	}
}
