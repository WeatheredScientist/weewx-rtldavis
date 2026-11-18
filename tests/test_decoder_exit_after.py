"""DEC-0237 (#579): a lost dongle becomes an exit.

The driver counts consecutive decoder exits ("rtldavis process is not running") and, at
RTLDAVIS_EXIT_AFTER of them (default 3, 0 off), raises RtldavisDecoderFatal so weewxd exits and the
supervisor recreates the container. Pinned here:

  1. the env parsing: unset is 3, 0 is off, junk falls back to 3 and says so;
  2. the exception is NOT an IOError/OSError, because weewxd retries those in-process;
  3. the count: the Nth exit in a row raises it, earlier ones raise WeeWxIOError, and the
     count survives a fresh driver (weewxd builds one per retry);
  4. a received packet resets the count, and a stall raise is never counted;
  5. 0 never raises it, however many exits.

The end-to-end container test (a stub decoder that exits at once) is scripts/exit_after_image.sh,
run by .github/workflows/image.yml after the smoke test.
"""
import pytest

import rtldavis
from test_hotswap_control import _loop_driver, _run


def _exit_once(monkeypatch, packet=False):
    """One genLoopPackets run that ends because the decoder stopped.

    packet=True lets one hop packet through first, which is what resets the count."""
    clock = [1000.0]
    monkeypatch.setattr(rtldavis.time, "time", lambda: clock[0])
    d = _loop_driver(clock, step=1, alive_passes=3, swap_on_pass=None)
    if packet:
        monkeypatch.setattr(rtldavis.RtldavisDriver, "_cache_pending_freq_fields",
                            lambda self, data: None)
        calls = [0]

        def _get_stderr(_self=None):
            calls[0] += 1
            return iter([[]]) if calls[0] == 1 else iter(())

        d._mgr.get_stderr = _get_stderr
        monkeypatch.setattr(
            rtldavis.PacketFactory, "create",
            lambda _self, lines: [{"dateTime": 1000, "usUnits": 16}] if calls[0] == 1 else [])
    _run(d)


def _expect_plain(monkeypatch, **kw):
    with pytest.raises(rtldavis.weewx.WeeWxIOError, match="is not running"):
        _exit_once(monkeypatch, **kw)


def _expect_fatal(monkeypatch, **kw):
    with pytest.raises(rtldavis.RtldavisDecoderFatal):
        _exit_once(monkeypatch, **kw)


# ── 1. the setting ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", [None, "", "   "])
def test_unset_or_blank_is_the_default(raw):
    assert rtldavis.exit_after_limit(raw) == rtldavis.EXIT_AFTER_DEFAULT == 3


@pytest.mark.parametrize("raw,want", [("0", 0), ("1", 1), ("3", 3), (" 7 ", 7), ("12", 12)])
def test_a_whole_number_is_taken(raw, want):
    assert rtldavis.exit_after_limit(raw) == want


@pytest.mark.parametrize("raw", ["off", "-1", "2.5", "three", "0x3"])
def test_junk_falls_back_to_the_default_and_says_so(raw, monkeypatch):
    seen = []
    monkeypatch.setattr(rtldavis, "logerr", lambda m: seen.append(m))
    assert rtldavis.exit_after_limit(raw) == 3
    assert seen and "RTLDAVIS_EXIT_AFTER" in seen[0]


# ── 2. the class ──────────────────────────────────────────────────────────────

def test_the_exception_is_not_something_weewxd_retries():
    """weewxd 5.5.2 retries WeeWxIOError and IOError and treats anything else as
    unrecoverable. WeeWxIOError subclasses IOError (OSError), so this must not."""
    assert issubclass(rtldavis.RtldavisDecoderFatal, Exception)
    assert not issubclass(rtldavis.RtldavisDecoderFatal, OSError)
    assert not issubclass(rtldavis.RtldavisDecoderFatal, rtldavis.weewx.WeeWxIOError)


# ── 3. the count ──────────────────────────────────────────────────────────────

def test_the_third_exit_in_a_row_is_fatal(monkeypatch):
    monkeypatch.delenv("RTLDAVIS_EXIT_AFTER", raising=False)
    _expect_plain(monkeypatch)
    _expect_plain(monkeypatch)
    _expect_fatal(monkeypatch)


def test_the_count_survives_a_new_driver(monkeypatch):
    """_loop_driver builds a fresh driver every call, as weewxd does on each retry."""
    monkeypatch.setenv("RTLDAVIS_EXIT_AFTER", "2")
    _expect_plain(monkeypatch)
    _expect_fatal(monkeypatch)


def test_the_limit_is_read_at_each_exit(monkeypatch):
    monkeypatch.setenv("RTLDAVIS_EXIT_AFTER", "5")
    _expect_plain(monkeypatch)
    _expect_plain(monkeypatch)
    monkeypatch.setenv("RTLDAVIS_EXIT_AFTER", "3")
    _expect_fatal(monkeypatch)


def test_one_means_the_first_exit_is_fatal(monkeypatch):
    monkeypatch.setenv("RTLDAVIS_EXIT_AFTER", "1")
    _expect_fatal(monkeypatch)


def test_the_fatal_exit_logs_why(monkeypatch):
    monkeypatch.setenv("RTLDAVIS_EXIT_AFTER", "1")
    seen = []
    monkeypatch.setattr(rtldavis, "logerr", lambda m: seen.append(m))
    _expect_fatal(monkeypatch)
    assert any("exited 1 times in a row" in m and "RTLDAVIS_EXIT_AFTER=1" in m for m in seen)


# ── 4. what resets it, and what must not count ───────────────────────────────

def test_a_received_packet_restarts_the_count(monkeypatch):
    monkeypatch.delenv("RTLDAVIS_EXIT_AFTER", raising=False)
    _expect_plain(monkeypatch)
    _expect_plain(monkeypatch)
    _expect_plain(monkeypatch, packet=True)   # a packet, then the exit: count is 1 again
    _expect_plain(monkeypatch)
    _expect_fatal(monkeypatch)


def test_positive_control_without_the_packet_the_same_run_is_fatal(monkeypatch):
    """Proves the packet's reset is what saved the run above."""
    monkeypatch.delenv("RTLDAVIS_EXIT_AFTER", raising=False)
    _expect_plain(monkeypatch)
    _expect_plain(monkeypatch)
    _expect_fatal(monkeypatch)


def test_a_stall_is_not_counted(monkeypatch):
    """DEC-0081's RF-dead episodes stall with the decoder alive; a restart cannot help them."""
    monkeypatch.setenv("RTLDAVIS_EXIT_AFTER", "1")
    clock = [1000.0]
    monkeypatch.setattr(rtldavis.time, "time", lambda: clock[0])
    d = _loop_driver(clock, step=200, alive_passes=4, swap_on_pass=None)
    with pytest.raises(rtldavis.weewx.WeeWxIOError, match="stalled"):
        _run(d)
    assert rtldavis._decoder_exits == 0


# ── 5. off ────────────────────────────────────────────────────────────────────

def test_zero_never_raises_it(monkeypatch):
    monkeypatch.setenv("RTLDAVIS_EXIT_AFTER", "0")
    for _ in range(10):
        _expect_plain(monkeypatch)
