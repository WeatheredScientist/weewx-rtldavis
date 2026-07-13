"""Regression tests for the ROOT logger override (DEC-0043, S39).

weewx's own defaults (weeutil/logger.py, LOGGING_STR) point the ROOT logger at a
syslog handler on /dev/log. A container has no syslog daemon, so every record
that reaches root raises inside SysLogHandler.emit() and Python's logging module
dumps the traceback to stderr -- ~15 tracebacks (~515 lines) per container start.

Overriding only the `weewx` and `user` loggers does NOT fix this: `weewxd` and
`weeutil.*` are in neither namespace, so they fall through to root. That is why
weewx.log had never contained a single startup line -- not the version banner,
not the config path -- for the entire life of the image.

These tests assert the shipped configs carry the fix. They are config assertions,
not behavioural ones: the behaviour was verified A/B inside the real container
(see DEC-0043), but this is what stops a future edit from silently dropping it.

Run:  python -m pytest tests/
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

LOGGING_ADDITIONS = os.path.join(ROOT, 'logging.additions')
CONF_EXAMPLE = os.path.join(ROOT, 'weewx.conf.example')
DOCKERFILE = os.path.join(ROOT, 'Dockerfile')


def _logging_section(text):
    """Return the [Logging] block of a weewx config, as text."""
    m = re.search(r'^\[Logging\]$(.*?)(?=^\[[A-Za-z]|\Z)', text, re.M | re.S)
    return m.group(1) if m else ''


def _root_handlers(text):
    """Return the handler list declared under [[root]], or None if absent."""
    sec = _logging_section(text)
    # non-greedy across lines to reach [[root]]'s own `handlers =`, but the
    # capture itself must stay on ONE line ([^\n]+, not .+ under re.S)
    m = re.search(r'^\s*\[\[root\]\].*?^\s*handlers\s*=\s*([^\n]+)', sec, re.M | re.S)
    if not m:
        return None
    return [h.strip() for h in m.group(1).split(',') if h.strip()]


def _read(path):
    with open(path) as f:
        return f.read()


def test_logging_additions_overrides_root():
    """The baked image config must override root (DEC-0043)."""
    handlers = _root_handlers(_read(LOGGING_ADDITIONS))
    assert handlers is not None, \
        "logging.additions has no [[root]] section: weewx's default " \
        "`handlers = syslog,` survives and the image ships the traceback bug"
    assert 'rotate' in handlers, \
        "root must log to the rotating FILE handler -- that is where the " \
        "startup banner has to land (it never has)"


def test_conf_example_overrides_root():
    """The published example config must override root too (DEC-0043)."""
    handlers = _root_handlers(_read(CONF_EXAMPLE))
    assert handlers is not None, \
        "weewx.conf.example has no [[root]] section"
    assert 'rotate' in handlers


def test_root_never_uses_syslog():
    """/dev/log does not exist in a container. Root must never point at it."""
    for path in (LOGGING_ADDITIONS, CONF_EXAMPLE):
        handlers = _root_handlers(_read(path))
        assert handlers is not None
        assert 'syslog' not in handlers, (
            "%s routes root to syslog. There is no syslog daemon in a "
            "container: every record raises in SysLogHandler.emit() and the "
            "traceback goes to stderr -- the pipe DEC-0036/DEC-0041 exist to "
            "keep quiet." % os.path.basename(path))


def test_root_handlers_are_defined():
    """A root handler that isn't declared makes dictConfig fail at startup."""
    for path in (LOGGING_ADDITIONS, CONF_EXAMPLE):
        text = _read(path)
        sec = _logging_section(text)
        declared = set(re.findall(r'^\s*\[\[\[(\w+)\]\]\]\s*$', sec, re.M))
        for h in _root_handlers(text):
            assert h in declared, (
                "%s: root references handler '%s', which is not declared in "
                "[[handlers]]" % (os.path.basename(path), h))


def test_dockerfile_asserts_root_survives_the_bake():
    """The Dockerfile must fail the build if [[root]] doesn't reach the image.

    Same reasoning as DEC-0041's StdPrint assertion: an edit that silently
    no-ops is how the previous two versions shipped the bug they claimed to fix.
    """
    text = _read(DOCKERFILE)
    # the grep pattern in the Dockerfile is shell-escaped (\[\[root\]\]), so
    # match loosely on the assertion's shape rather than its exact escaping
    assert re.search(r'grep -q[^\n]*root[^\n]*weewx\.conf', text), \
        "Dockerfile does not grep the baked config for [[root]]"
    assert re.search(r'FATAL:.*root', text), \
        "Dockerfile does not fail the build when [[root]] is missing"


if __name__ == '__main__':
    import sys
    import pytest
    sys.exit(pytest.main([__file__, '-v']))
