"""Regression: pressure_service must never log key material (S57b).

The line this guards used to be:

    log.info("DavisPressureFetcher: api_key=%s station_id=%s", self.api_key[:8], ...)

which put 8 characters of the live WeatherLink key into weewx.log -- and its 30
daily rotations -- on EVERY startup. That matters more than a truncated prefix
normally would, because of WHERE it lands: DEC-0047's read-guard covers configs
(weewx.conf, *.env) and does NOT cover weewx.log. So the ordinary operation of
tailing the log to confirm a restart was clean pulls the value into an agent
transcript, which is a provider egress path. Observed twice on 2026-07-29.

This test asserts the property directly -- that no credential attribute is ever
passed as a log argument -- rather than pinning the exact wording, so a reworded
log line stays green but a reintroduced key does not.
"""
import ast
from pathlib import Path

SERVICE = Path(__file__).resolve().parent.parent / "pressure_service.py"

# Attributes that hold, or are derived from, credential material.
SECRET_ATTRS = {"api_key", "api_secret"}


def _log_calls(tree):
    """Every log.<level>(...) call in the module."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "log":
            yield node


def _mentions_secret(node):
    """True if this expression reads a credential attribute anywhere inside it.

    Catches self.api_key, self.api_key[:8], f-strings interpolating it, and
    str(self.api_secret) alike -- the slice was the original bug, so a check
    that only looked for a bare attribute would have missed it.
    """
    return any(
        isinstance(n, ast.Attribute) and n.attr in SECRET_ATTRS
        for n in ast.walk(node)
    )


def test_no_log_call_passes_credential_material():
    tree = ast.parse(SERVICE.read_text())
    offenders = []
    for call in _log_calls(tree):
        for arg in call.args + [kw.value for kw in call.keywords]:
            if _mentions_secret(arg):
                offenders.append(f"line {call.lineno}: {ast.unparse(arg)}")
    assert not offenders, (
        "credential material passed to a log call -- weewx.log is an egress path "
        "the read-guard does not cover:\n  " + "\n  ".join(offenders)
    )


def test_the_detector_actually_catches_the_original_bug():
    """POSITIVE CONTROL (DEC-0045): a passing test proves nothing until it has
    been seen to fail. Feed the detector the exact line that shipped and assert
    it flags it -- including the [:8] slice form, which is the shape that made
    the original look harmless."""
    original = 'log.info("DavisPressureFetcher: api_key=%s", self.api_key[:8])'
    tree = ast.parse(original)
    flagged = [
        arg for call in _log_calls(tree)
        for arg in call.args if _mentions_secret(arg)
    ]
    assert flagged, "detector no longer catches the original bug; it has lost its teeth"


def _except_bound_names(tree):
    """Names bound by `except ... as <name>:` anywhere in the module."""
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and node.name
    }


def _mentions_raw_exception(node, exc_names):
    """S91: True if `node` is the bare exception object, or a bare str() of
    it, passed directly -- NOT wrapped in any other call such as a redactor.
    That is the shape that leaks: for a requests/urllib3 connection failure,
    str(e) embeds the full request URL, which is exactly where
    fetch_pressure() puts api-key/api-signature. So the exception object is
    credential-shaped even though it is not an api_key/api_secret attribute,
    and the check above cannot see it.
    """
    if isinstance(node, ast.Name) and node.id in exc_names:
        return True
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "str"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id in exc_names
    ):
        return True
    return False


def test_no_log_call_passes_a_raw_exception_object():
    """S91: a raw exception (or str() of one) reaching a log call is
    credential-shaped here, even though it never mentions api_key/api_secret
    by name -- see _mentions_raw_exception. The fix wraps it in
    _redact_secrets(); this asserts nothing bypasses that wrapper.
    """
    tree = ast.parse(SERVICE.read_text())
    exc_names = _except_bound_names(tree)
    offenders = []
    for call in _log_calls(tree):
        for arg in call.args + [kw.value for kw in call.keywords]:
            if _mentions_raw_exception(arg, exc_names):
                offenders.append(f"line {call.lineno}: {ast.unparse(arg)}")
    assert not offenders, (
        "a raw exception object (or str() of one) reached a log call -- for "
        "a requests/urllib3 failure this embeds the full request URL, "
        "credential and all:\n  " + "\n  ".join(offenders)
    )


def test_the_raw_exception_detector_actually_catches_the_original_bug():
    """POSITIVE CONTROL (DEC-0045), same discipline as the test above it."""
    original = (
        "try:\n"
        "    pass\n"
        "except Exception as e:\n"
        '    log.error("DavisPressureFetcher: error fetching pressure: %s", e)\n'
    )
    tree = ast.parse(original)
    exc_names = _except_bound_names(tree)
    flagged = [
        arg for call in _log_calls(tree)
        for arg in call.args if _mentions_raw_exception(arg, exc_names)
    ]
    assert flagged, "detector no longer catches a raw exception passed to a log call"
