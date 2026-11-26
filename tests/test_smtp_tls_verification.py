"""Regression: every smtplib connection in this repo must verify TLS (S91).

smtplib.SMTP.starttls() and smtplib.SMTP_SSL.__init__(), called with no
`context=`, fall back to ssl._create_stdlib_context() -- which is a bare
alias for ssl._create_unverified_context() (CERT_NONE, check_hostname=False).
An on-path attacker can intercept either connection with any certificate and
capture GMAIL_PASS (a full-mailbox app password, bypasses 2FA), or silently
swallow the message -- for ops/rx_experiment.sh's send_mail(), the one
channel designed to reach a human independent of weewx_monitor.py itself.

influx.py's post_request() already does this correctly; weewx_monitor.py and
rx_experiment.sh simply never got the same fix. Found by the S91 full-repo
security audit; see docs/DECISIONS-FULL.md DEC-0101. rx_experiment.sh and its
starttls check moved to ARCHIVE/rx-campaign/ with the apparatus (DEC-0250).
"""
import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MONITOR = REPO / "weewx_monitor.py"


def _smtp_calls_without_context(tree):
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
        if name not in ("SMTP_SSL", "SMTP"):
            continue
        if not any(kw.arg == "context" for kw in node.keywords):
            offenders.append(f"line {node.lineno}: {ast.unparse(node)}")
    return offenders


def test_weewx_monitor_smtp_calls_verify_tls():
    tree = ast.parse(MONITOR.read_text())
    offenders = _smtp_calls_without_context(tree)
    assert not offenders, (
        "smtplib call with no context= -- defaults to unverified TLS "
        "(CERT_NONE), exposing GMAIL_PASS to an on-path attacker:\n  "
        + "\n  ".join(offenders)
    )


def test_the_monitor_detector_actually_catches_the_original_bug():
    """POSITIVE CONTROL (DEC-0045)."""
    original = "smtplib.SMTP_SSL('smtp.gmail.com', 465)"
    tree = ast.parse(original)
    assert _smtp_calls_without_context(tree), (
        "detector no longer catches an unverified SMTP_SSL call"
    )
