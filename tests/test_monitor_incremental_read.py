"""Offline unit tests for the byte-offset incremental log read (M-A + L-B, S28).

Before S28 `weewx_monitor.py` re-read the ENTIRE weewx.log twice per 30s poll:
`get_linecount()` counted every line, then `get_new_lines()` did a second whole-
file `readlines()`. On a 10 MB/day log that is O(n) per poll (M-A), and the two
separate opens raced -- lines appended between them were returned once, then the
`last_line = cur` bookkeeping re-read them next poll (L-B double-count).

The fix: track a byte OFFSET and read from it in a single open. These tests
exercise the REAL `get_new_lines`/`get_log_size` from weewx_monitor.py against a
temp log, so the deployed behaviour is under test:

  * complete appended lines are returned and the offset advances exactly;
  * a consecutive read from the returned offset yields ONLY new lines (no
    re-read -- the L-B guarantee);
  * a trailing partial line (no newline yet) is held back and parsed once, whole;
  * rotation/truncation (size < offset) is detectable by the caller.

weewx_monitor.py writes a pidfile at import; `--test-alert` in argv bypasses that
guard (its intended non-invasive path), letting the module import cleanly.

Run:  python3 -m pytest tests/    OR    python3 tests/test_monitor_incremental_read.py
"""
import os
import sys
import tempfile

# Bypass the module's PID guard so importing it doesn't touch a running monitor.
sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402


def _with_log(contents_bytes, fn):
    """Point wm.WEEWX_LOG_PATH at a temp file holding CONTENTS_BYTES, run FN."""
    orig = wm.WEEWX_LOG_PATH
    fd, path = tempfile.mkstemp(prefix="weewx_test_", suffix=".log")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(contents_bytes)
        wm.WEEWX_LOG_PATH = path
        return fn(path)
    finally:
        wm.WEEWX_LOG_PATH = orig
        os.unlink(path)


def test_reads_complete_lines_and_advances_offset():
    body = b"line one\nline two\nline three\n"
    def check(_path):
        lines, new_off = wm.get_new_lines(0)
        assert lines == ["line one", "line two", "line three"]
        assert new_off == len(body)          # offset stops at EOF (all complete)
    _with_log(body, check)


def test_second_read_from_offset_returns_only_new_lines():
    # The L-B guarantee: nothing already consumed is ever returned again.
    def check(path):
        lines1, off1 = wm.get_new_lines(0)
        assert lines1 == ["alpha", "beta"]
        with open(path, "ab") as f:          # simulate live appends
            f.write(b"gamma\ndelta\n")
        lines2, off2 = wm.get_new_lines(off1)
        assert lines2 == ["gamma", "delta"]  # only the NEW lines, no re-read
        assert off2 == off1 + len(b"gamma\ndelta\n")
    _with_log(b"alpha\nbeta\n", check)


def test_offset_at_eof_returns_nothing():
    body = b"only line\n"
    def check(_path):
        lines, new_off = wm.get_new_lines(len(body))
        assert lines == []
        assert new_off == len(body)
    _with_log(body, check)


def test_partial_trailing_line_held_back_then_completed():
    # A half-written line (no final '\n') must NOT be parsed or advanced past;
    # it is returned once, whole, only after its newline arrives.
    def check(path):
        lines1, off1 = wm.get_new_lines(0)
        assert lines1 == ["done"]            # "half" is withheld
        assert off1 == len(b"done\n")        # offset stops before the partial
        with open(path, "ab") as f:
            f.write(b" and done\n")          # completes the withheld line
        lines2, off2 = wm.get_new_lines(off1)
        assert lines2 == ["half and done"]   # parsed exactly once, in full
        assert off2 == len(b"done\nhalf and done\n")
    _with_log(b"done\nhalf", check)


def test_rotation_is_detectable_by_caller():
    # After rotation the fresh file is smaller than the last offset; the caller's
    # `get_log_size() < last_offset` guard is what resets the offset to 0.
    def check(path):
        _lines, off = wm.get_new_lines(0)
        assert off > 0
        with open(path, "wb") as f:          # truncate == rotation-by-recreate
            f.write(b"fresh\n")
        assert wm.get_log_size() < off        # caller will reset offset -> 0
        lines_after, _ = wm.get_new_lines(0)  # ...and re-read from the top
        assert lines_after == ["fresh"]
    _with_log(b"old line 1\nold line 2\n", check)


def test_missing_file_is_safe():
    orig = wm.WEEWX_LOG_PATH
    wm.WEEWX_LOG_PATH = "/nonexistent/definitely/not/here.log"
    try:
        assert wm.get_log_size() == 0
        assert wm.get_new_lines(0) == ([], 0)
    finally:
        wm.WEEWX_LOG_PATH = orig


ALL_TESTS = [
    test_reads_complete_lines_and_advances_offset,
    test_second_read_from_offset_returns_only_new_lines,
    test_offset_at_eof_returns_nothing,
    test_partial_trailing_line_held_back_then_completed,
    test_rotation_is_detectable_by_caller,
    test_missing_file_is_safe,
]


if __name__ == "__main__":
    passed = 0
    for t in ALL_TESTS:
        try:
            t()
            passed += 1
            print(f"  [PASS] {t.__name__}")
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
    print(f"\n{passed}/{len(ALL_TESTS)} passed")
    sys.exit(0 if passed == len(ALL_TESTS) else 1)
