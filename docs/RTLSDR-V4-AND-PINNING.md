# RTL-SDR Blog V4 support and device pinning (S201a findings)

**Status:** findings and the design DEC-0235 adopted (owner: "Approve both"); A to C are built on the S201a branch, nothing is deployed, and prod is unchanged.
**Asked by:** eaglehunt-ops#440: before a second dongle goes anywhere near prod, (1) does the image's
librtlsdr support the Blog V4, and (2) how is prod's dongle pinned. **Date:** 2026-11-12 (S201a,
Opus 5.5). Everything marked *measured* was read from source at the pinned commit or from prod's own
image with `marvinctl --tenant weewx exec-ro` (a fresh container, no device, nothing in prod's
container). Everything marked *inferred* is reasoning from source that has not met the hardware.

## Verdicts

1. **The image already supports the V4. No image change is needed for it, and the v3 path is
   untouched.** BOOT's lead ("needs librtlsdr newer than bookworm's 0.6.0") is true of bookworm hosts
   and wrong for this image, which builds osmocom librtlsdr v2.0.2+2.
2. **Prod has no device pinning today, and `-d` cannot give it any.** The bundled Go decoder parses
   `-d` (serial or index) and then opens index 0 regardless, an upstream bug. Prod opens the right
   stick only because it is the only RTL2832U on marvin. Prod's container is passed the whole USB bus,
   and marvin's udev rule grants `t-weewx` every `0bda:2838`. **A V4 plugged in anywhere on marvin
   would be visible to prod, and libusb's ordering makes it likely to become index 0 on prod's next
   restart (inferred).**
3. **Do not plug the V4 into marvin until the pinning fix below ships in prod's image.** At minimum
   that means a unique serial on the V4 *and* a decoder that honors `-d`. Container isolation on
   marvin is a second wall, and that wall is marvin's to build.

## 1. Which librtlsdr the image builds

**Measured, from `src.tgz` at the Dockerfile's pin (`bfa9e3d9…`, sha256 `7c1a7de1…`, verified):**
`src/librtlsdr/` is a git clone with its `.git` intact. Its origin is `github.com/steve-m/librtlsdr`,
osmocom's GitHub mirror and the canonical upstream. HEAD is `ae0dd6d` (2025-11-09, "Change release
version in CMakeLists.txt to 2.0.2"), `git describe` gives `v2.0.2-2-gae0dd6d`, and the working tree
is clean against that commit. The clone was made 2025-12-20, by the reflog. The build installs
`librtlsdr.so.2.0.2` (SONAME `librtlsdr.so.0`) and the `rtl_*` tools into `/usr/local`.

**Measured in prod's image (`:marvin-live`):**

| Binary | Resolves `librtlsdr.so.0` to |
|---|---|
| `/usr/local/bin/rtldavis` (the Go decoder) | `/usr/local/lib/librtlsdr.so.0` → `librtlsdr.so.2.0.2` (bundled) |
| `/usr/local/bin/rtl_biast` (entrypoint's bias-tee call) | the same bundled library |

`/usr/local/lib` comes first through `/etc/ld.so.conf.d/libc.conf`, and `/usr/local/bin` comes first
on `PATH`. The image also carries Ubuntu's `rtl-sdr` / `librtlsdr0` `2.0.2-2build1` from apt, in both
stages, along with a second set of `rtl_*` tools in `/usr/bin`. Nothing in the run path loads that
copy. It is V4-capable too, so the duplication is harmless. Removing it is a cleanup question, not a
V4 question.

### Does v2.0.2+2 handle the Blog V4?

**Yes. Measured in the tree:**

- `1261fbb` "add rtl-sdr blog v4 support" (2023-08-22) and `138cd05` "add blog v4 upconverter gpio
  switch" (2023-09-20) are both ancestors of `ae0dd6d`.
- **Identification is by EEPROM string descriptors, not USB id.**
  `rtlsdr_check_dongle_model(dev, "RTLSDRBlog", "Blog V4")` compares manufacturer and product. The V4
  shares `0bda:2838` with the v3 and many generic sticks (the id part is from the source's
  known-devices table and the vendor's docs; it is unconfirmed on our unit until first enumeration).
- **R828D tuner:** probed at the R828D I2C address. On a V4 it prints `Found Rafael Micro R828D tuner`
  and `RTL-SDR Blog V4 Detected`. The V4 keeps the 28.8 MHz tuner crystal; other R828D sticks get
  16 MHz.
- **Input switch / triplexer:** `tuner_r82xx.c` picks HF (≤ 28.8 MHz), VHF (< 250 MHz) or UHF.
  **915 MHz takes the UHF / air-in path** (`air_in`, reg 0x05). The notch-filter logic in the same
  branch only touches ≤ 2.2, 85 to 112 and 172 to 242 MHz.
- **HF upconverter:** below 28.8 MHz the tuner adds 28.8 MHz and drives GPIO 5. This is irrelevant
  at 915 MHz.
- **Bias tee:** `rtlsdr_set_bias_tee` is GPIO 0, the same as the v3, so `BIAS_TEE` and `rtl_biast`
  behave the same on both. The vendor documents `rtl_biast -b 1/0` for the V4. (The rtlsdrblog fork's
  EEPROM "bias tee always on" flag is fork-only and ignored here, as the vendor itself notes.)

**Against the alternatives (external sources, checked S201a):**

| Source | Latest | V4 at 915 MHz vs ours |
|---|---|---|
| osmocom (`steve-m/librtlsdr`) | `v2.0.3` (`797f814`), 2026-08-12 | Same UHF path. Adds V4L ("Blog V4L") detection, an HF tracking-filter bypass, and `65f0658` "Fix application hang on USB transfer errors" (see Follow-ups) |
| rtlsdrblog fork (`rtlsdrblog/rtl-sdr-blog`) | `V1.4.0`, 2026-08-10 | Same air-in path. Fork-only changes are R82xx PLL/VCO-current tweaks the fork ties to L-band stability above ~1.5 GHz, plus bias-tee/EEPROM hacks. Nothing needed at 915 MHz. It also lacks osmocom's newer PLL code |
| Ubuntu 26.04 / Debian trixie | `2.0.2-2(build1)` | V4-capable |
| Debian bookworm, Pi OS bookworm | `0.6.0-4` | **No V4.** Source of BOOT's lead and of the weewx-packages note on #514. It affects host installs, not this image |
| Homebrew `librtlsdr` | `2.0.3` | V4-capable (matters for an off-host EEPROM write, §3) |

Vendor guidance has moved. The V4 launch post said it "requires" the RTL-SDR Blog drivers. A later
update and the quick-start guide say the default osmocom branch now supports the V4.

**Prod safety:** the recommendation changes nothing in librtlsdr. The bytes prod's v3 runs on today
are the bytes the V4 would run on. A pin bump to osmocom v2.0.3 is a separate question with its own
cause (Follow-ups).

## 2. How a dongle is chosen today

### The Go decoder ignores `-d` (upstream bug, measured)

`main.go` in `src.tgz`, identical in `lheijst/rtldavis` master (`b95d5d7`, 2020-06-05, checked via the
GitHub API):

```go
deviceString = flag.String("d","0","device serial number or device index")
...
sdrIndex , _ = rtlsdr.GetIndexBySerial(*deviceString)   // serial first
if (sdrIndex <0 ) { sdrIndex = strconv.Atoi(*deviceString) ... }   // then index
dev, err := rtlsdr.Open(0)                               // <- always index 0
```

`sdrIndex` is computed and then thrown away. **`-d <serial>` and `-d 1` are silently discarded.** This
is the "interface accepts an instruction and silently discards it" trap that `docs/GOTCHAS.md` §1
warns about. None of our four patches touches these lines. The decoder logs
`deviceString=<value>` at start, which makes it look honored. The weewx-packages Python port gets
this right: it opens the index it resolved.

### What else picks "index 0" (measured)

| Caller | Selection |
|---|---|
| Go decoder | index 0, always (above) |
| `entrypoint.sh` → `rtl_biast -b 0/1` | no `-d`, so `verbose_device_search("0")` = index 0 |
| `doctor.py` | sysfs entries **sorted by name**, takes the first, then runs `rtl_test -t` with no `-d` (= libusb index 0). The two orders can disagree, so with two sticks `doctor` can report on one and probe the other |
| `rtl_eeprom -d` | **index only** (`atoi`); no serial match at all |
| `rtl_test` / `rtl_biast` / other tools `-d` | `verbose_device_search`: **a numeric string is tried as an index first** (`strtol` base 0, so `0042` → 34, octal, and `0x…` is hex), then exact serial, then serial prefix, then serial suffix |

So **the Go decoder and the `rtl_*` tools disagree on precedence**: serial first in Go, index first
in the tools. A numeric-looking serial can name one stick to the decoder and the other to
`rtl_biast`.

### What "index 0" means (measured in libusb source, consequence inferred)

librtlsdr's index counts known devices in `libusb_get_device_list()` order. libusb 1.0.29, the
image's version, adds each discovered device with `list_add()`, which **prepends**
(`usbi_connect_device`, `core.c:738`). `get_device_list` walks from the head. The udev backend scans
in libudev's syspath order. **So index 0 is the last device scanned, not the lowest bus.** Prod's v3
is at `5-1` (controller `10:00.4`). marvin's spare jacks are `7-1.x` (`11:00.0`). If the syspaths sort
the way the PCI addresses do, a V4 on `7-1.x` scans last and becomes index 0. That makes prod open the
V4 on its next restart, and `rtl_biast` act on the V4. This has not been tested with hardware, and it
should not be tested on prod. The point is that the order is an implementation detail and nobody
guarantees it.

### Prod's walls today (measured)

- `weewx.service`: `--device /dev/bus/usb:/dev/bus/usb`, so prod's container sees every USB device
  present at start.
- `host/etc/udev/rules.d/60-marvin-tenant-devices.rules` (heartofgold): `idVendor=="0bda",
  idProduct=="2838"` → `GROUP="t-weewx", MODE="0660"`. **It matches any `0bda:2838`, so a V4 would
  be granted to prod's uid as well.**
- MARVIN-DEC-0106's `exec_devices` (`check_device`) resolves by `vendor:product` and **refuses on
  more than one match**. That is correct, but with a V4 present, weewx's `exec-ro` device path stops
  working until it keys on something finer.
- The host blacklists `dvb_usb_rtl28xxu`, so a V4 would not be held by the TV driver.
- `marvinctl --tenant weewx usb` (ops#456, self-service, no root) prints the USB tree with id and
  driver. On 2026-11-12 it showed exactly one `0bda:2838`, at `5-1`, driver `usbfs` (held by prod,
  not the TV driver). **Run it before and after the V4 is ever plugged in:** a second `0bda:2838`
  row is the signal that every wall below matters.
- Prod's v3 (from the start log, 2026-11-04): manufacturer `Realtek`, product `RTL2838UHIDIR`, the
  **factory-default serial**. Default serials are widely reported to be the same across sticks
  (`rtl_eeprom`'s OEM preset writes one fixed all-digit value). The vendor does not document the V4's default; read
  it at first enumeration. The real values belong in the local-infra doc only.

## 3. Design (DEC-0235, accepted; A to C built, see "As built" at the end)

**Goal: easy for a new user with one stick (nothing to do), obvious for a user with two, and
impossible for prod to open the wrong stick silently.**

### A. Decoder: honor `-d`, refuse ambiguity, say what it opened (baked, image release)

A fifth patch, `patch/rtldavis-devsel.patch`, gated in the Dockerfile like the other four
(grep-count asserts) and with Go tests under `tests/go/`:

1. Open the resolved index (`rtlsdr.Open(sdrIndex)`). This is the bug fix.
2. **Serial match counts every device.** Exactly one match opens it. More than one is fatal:
   `rtldavis: -d <serial> matches N dongles (indexes …); give each a unique serial (docs/…)`. Today
   librtlsdr silently returns the first match. Zero matches falls back to the index parse, which keeps
   upstream's serial-first order. An out-of-range index is fatal and lists what is present.
3. One start line: `rtldavis: using dongle <i> of <n>: <manufacturer> <product> SN <serial>`. Logged
   always, so the log proves which stick is open. Prod's log never shows the serial publicly; the log
   stays on marvin.
4. **No `-d` and more than one dongle present:** keep opening index 0 (back-compatible), but log a
   WARNING naming every candidate and the fix. One stick and no `-d` stays silent, so a single-dongle
   user sees nothing new.

The behavior change is that a user who passed `-d 1` or a serial that never worked now gets the
stick they asked for, or a clear error. Note it in CHANGES-FROM-UPSTREAM.md, and offer it upstream
(lheijst/rtldavis), owner's go.

### B. One setting for the container: `RTLSDR_DEVICE` (image)

`BIAS_TEE` already sets a hardware property in `.env` on every start. `RTLSDR_DEVICE` (a serial; an
index is accepted but discouraged) joins it:

- `entrypoint.sh` passes `-d "$RTLSDR_DEVICE"` to `rtl_biast`, so the bias tee acts on the same
  stick the decoder opens. **This matters most on a V4: never power a tee into the wrong antenna.**
- The driver appends `-d $RTLSDR_DEVICE` to the decoder command when `cmd` has no `-d`. An explicit
  `-d` in `cmd` that differs from `RTLSDR_DEVICE` stops the start with a one-line error. Two
  disagreeing sources are refused, never silently resolved.
- Unset is today's behavior. Non-Docker users of the driver keep `-d` in `cmd`.

Alternative considered: a `[Rtldavis] device =` key in `weewx.conf`. It was rejected because
`entrypoint.sh`'s bias-tee call runs before weewxd and would need to parse the config. The env var
reaches both with no parsing.

### C. `doctor`: list, identify, warn

Read every RTL2832U from **sysfs** (`manufacturer`, `product`, `serial`, `busnum`/`devnum`, the
port path such as `5-1`). This needs no USB open, so it works while a running station holds the stick.
Then:

- Print one line per stick: `index? · port · manufacturer product · SN · model`. Model is **V4**
  (strings `RTLSDRBlog`/`Blog V4`), **V4L**, **v3 or generic RTL2832U** (anything else; a v3 is not
  distinguishable from a generic stick by strings alone), or the tuner name from `rtl_test -t`.
- Probe the **selected** stick (`rtl_test -d <RTLSDR_DEVICE>`), not "the first", which fixes the
  sysfs-vs-libusb disagreement.
- New exit 15, *ambiguous dongle*: more than one stick and `RTLSDR_DEVICE` unset, or set and matching
  zero or several. The fix it prints is to set `RTLSDR_DEVICE`, or to burn a unique serial.
- A WARNING when two sticks share a serial, or a serial is all digits (the `rtl_*` tools would read it
  as an index).
- A WARNING when a V4 shows strings other than `RTLSDRBlog`/`Blog V4`, which breaks V4 detection; the
  vendor's restore line is `rtl_eeprom -m RTLSDRBlog -p "Blog V4"`.

### D. Unique serials: the owner's gesture, off-host, V4 first

Duplicate default serials defeat any serial pin. **Recommended: give the V4 a unique serial before it
ever touches marvin, on the owner's Mac (Homebrew `librtlsdr` 2.0.3), with only the V4 plugged in,
and leave prod's v3 EEPROM alone.**

- Why off-host: `rtl_eeprom -d` is index-only. With one stick plugged in, index 0 is unambiguous, and
  no prod hardware is written. `rtl_eeprom -s` rewrites only the serial (manufacturer and product are
  read back and kept, measured in `rtl_eeprom.c`). It prints the current config and asks `y/n` before
  writing, so the owner can check that it says `RTLSDRBlog` / `Blog V4` first. Replug, then
  `rtl_test -t` must show the new serial and `Blog V4 Detected`.
- **The serial must contain a letter** and must not start with `0x`. The `rtl_*` tools read
  numeric-looking strings as indexes (§2). Pick the real value then and record it in the local-infra
  doc and the heartofgold inventory (`[confirm]` → value), never on GitHub.
- **Never** pass `-m`, `-p` or `-g` to a V4: changing the strings silently turns it into an R828D
  stick on the wrong crystal (vendor warning, confirmed in source).
- **Prod's v3: optional, deferred, owner's call.** With A and B in place and the V4 unique, prod can
  pin its v3 by its existing serial. A third default-serial stick would then trip A.2's ambiguity
  error rather than open silently. Burning the v3 too means stopping prod (rtl_eeprom needs the stick
  free), a write to the only receiver's EEPROM, and a replug for the new serial to show. That is real
  risk for a small gain while only one other stick exists.

### E. marvin's wall (asks for marvin/heartofgold via ops, not ours to build)

Defense in depth, raised on #440 for marvin to decide:

1. **Narrow the udev grant** from "any `0bda:2838`" to prod's stick, by serial once it is unique or
   by port (`KERNELS=="5-1"`). Then a V4 is not prod's uid's by default.
2. **Pass prod one device node, not the bus.** It has to be resolved at each start (devnum changes
   on re-enumeration), the same resolve-and-refuse-ambiguity shape as `check_device`, keyed on serial
   or port. Inferred: whole-bus `--device` does not follow re-enumeration either, because Docker
   creates the nodes present at start, so a single node is no worse on that axis.
3. `exec_devices`: key on serial or port, or it refuses with two `0bda:2838` sticks present.
4. Whether the V4 belongs on marvin at all, or on another always-on box, stays marvin's call
   (ops#440's open ask). Nothing in A to D depends on it.

### Order of operations (none of it now)

A + B + C ship in an image (minor version, DEC-0222) → prod runs it with `RTLSDR_DEVICE` set to the
v3 (a heartofgold unit edit, owner-run) and the log line shows the right stick → the V4 gets its
serial off-host → marvin's E items as marvin decides → only then is the V4 plugged into marvin, with `marvinctl --tenant weewx usb` read before and
after, and prod's start line checked for the v3.

## 4. A new user with a V4: what they would trip on

| Trap | Today | Fix |
|---|---|---|
| QUICKSTART says "RTL-SDR Blog V3 dongle" | A V4 owner does not know whether theirs works | "V3 or V4 (V4 support is in the image's librtlsdr; first live V4 run: our December A/B)". Don't claim tested until it is |
| Testing on the host with `rtl_test` on bookworm or Pi OS bookworm | 0.6.0 does not know the V4: wrong crystal, poor or no reception. The user concludes the stick is dead | A troubleshooting row: test with `doctor` (the image's librtlsdr), not the host's tools |
| Two sticks (a V4 next to a v3, or an ADS-B stick) | The decoder silently opens index 0; `BIAS_TEE` may power the wrong stick | A + B + C; a short "More than one dongle" section |
| A serial "made unique" with `rtl_eeprom -s 2` | The tools read `2` as an index | doctor's warning; docs say "include a letter" |
| `rtl_eeprom` advice from forums (`-g realtek_oem`, `-m`, `-p`) | Breaks V4 detection silently | Warning in the docs; doctor detects mismatched strings |
| Gain | Prod's `-gain 372` is an R820T-tuned value; the V4 is reported to be hotter | No change: librtlsdr picks the nearest supported step, the R828D shares the R82xx gain table, and `-gain 0` (auto) is the troubleshooting row's first try. The A/B will measure it |
| `host-setup.sh` | Matches `0bda:2838`/`2832`, blacklists the TV driver, writes the udev rule | Already right for a V4 (same id) |

## Not in scope here, and follow-ups

- **osmocom `65f0658`, "Fix application hang on USB transfer errors" (in v2.0.3, not in our pin):**
  `rtlsdr_read_async()` could hang forever on a USB transfer error. Blocker 1 (freeze, DEC-0068/0094)
  and DEC-0083's long tail are hangs of unknown mechanism. This deserves a look on its own, as a
  separate pin-bump DEC with a v3 prod soak. It does not ride this change.
- **The #514 A/B.** Same-host runs need A to D first. cdavis289's run used `-d <serial>` on the Go
  decoder, which this bug ignores; their result still stands if each container saw one stick.
  Mentioning it upstream is the owner's call.
- **The apt `rtl-sdr` duplicate in the image:** a cleanup, not a V4 matter.

## As built (S201a, after the owner's "Approve both")

Not deployed. It reaches prod only with an image release and a unit edit, each the owner's go.

- **A:** `patch/rtldavis-devsel.patch` adds a `devsel/` package and swaps upstream's ignored lookup
  for `devsel.Pick`, `devsel.Describe` and `rtlsdr.Open(sdrIndex)`. The Dockerfile asserts
  `Open(sdrIndex)` once, `Open(0)` never, and three `devsel.` calls. `tests/test_devsel_patch.py`
  audits every changed line against an allow-list (positive control included), runs the Go tests
  and builds the whole program where librtlsdr is installed.
- **One rule, two implementations:** `tests/go/devsel_cases.json` (22 cases) drives both
  `devsel.Pick` (Go) and `doctor.select_dongle` (Python). A positive control shows the table
  rejects librtlsdr's first-match lookup.
- **B:** `rtldavis.apply_device` turns `RTLSDR_DEVICE` into `-d`. A disagreeing or second `-d`
  raises at driver start, and Go's `dongle:` lines are logged at INFO. `entrypoint.sh` resolves the
  value with `doctor.py --resolve` (librtlsdr's own order, the decoder's rule) and gives
  `rtl_biast` that index, which `rtl_biast` always reads as an index. **One refinement over the
  design:** if the value matches no single dongle, the entrypoint leaves the bias tee alone and
  starts, and the decoder then refuses with the reason. A simulator install with a stale setting
  still starts.
- **C:** `doctor` lists every dongle from sysfs (port, strings, serial, model) and picks the
  station's. A serial is matched in sysfs; an index goes through librtlsdr and is mapped back by
  its strings. It checks and probes only the chosen dongle (`rtl_test -d <librtlsdr index>`), so a
  container passed one node no longer fails on the other stick. It exits 15 on ambiguity, with
  the `rtl_eeprom` fix. It warns on shared or all-digit serials, and on an R828D tuner without the
  Blog V4 strings (with the vendor's restore line).
- **Docs:** QUICKSTART ("V3 or V4", two troubleshooting rows, a "More than one dongle" section),
  `.env.example`, the compose comment, the systemd example, and CHANGES-FROM-UPSTREAM (the fifth
  patch, driver row 28).
