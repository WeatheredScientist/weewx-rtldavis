"""Offline unit test for AsyncReader's EOF handling (issue #219, finding #2).

AsyncReader.run() compared readline()'s return value against the str '', but
ProcManager.startup()'s Popen() has no text=True, so the pipes are binary and
EOF is b'' -- never the str ''. b'' != '' always, so the old code never
recognized EOF: once the child exited, readline() returned b'' forever
without blocking, and the loop busy-spun (measured ~700K queue.put(b'')/sec
against a real subprocess) instead of stopping.

This test drives the real AsyncReader through a real thread against a fake
binary-mode fd, with a bounded join() -- if the busy-spin regresses, the
test fails in 2s instead of hanging the whole suite.

weewx is not installed in the test/CI environment, so we stub it (same
pattern as test_procmanager_reap.py / test_stderr_drain.py).

Run:  python3 -m pytest tests/ (pytest only)
"""
import itertools

import rtldavis  # noqa: E402


class _FakeBinaryPipe:
    """Minimal readline()-only fake matching a real closed pipe's shape: a
    fixed sequence of lines, then b'' forever -- never blocks, never raises,
    exactly EOF's real behavior once a child process exits."""
    def __init__(self, lines):
        self._it = itertools.chain(lines, itertools.repeat(b''))

    def readline(self):
        return next(self._it)


def test_async_reader_stops_on_binary_eof():
    """Pre-fix, b'' is never recognized as EOF (compared against the str
    ''), so the reader thread never stops on its own -- reader.join(2)
    times out and is_alive() stays True. Post-fix, the very first b''
    readline() return stops the loop without entering its body, so the
    thread finishes almost immediately and only the two real lines --
    never a sentinel -- ever reach the queue."""
    q = rtldavis.queue.Queue()
    fd = _FakeBinaryPipe([b"line one\n", b"line two\n"])
    reader = rtldavis.AsyncReader(fd, q, "test-reader")
    reader.start()
    reader.join(timeout=2)
    assert not reader.is_alive(), (
        "reader did not stop on EOF within 2s -- busy-spin regression")
    got = []
    while not q.empty():
        got.append(q.get())
    assert got == [b"line one\n", b"line two\n"]
