# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared `marvinctl --tenant weewx` helpers for the read-only ops scripts.

campaign_analyze, stall_baseline and freeze_baseline each carried their own copy of these
(audit item 22). Read-only throughout.
"""
from __future__ import annotations

import json
import subprocess
import sys


def marvinctl(*args: str, input: str | None = None, timeout: int = 60,
              prog: str = "") -> str:
    """One `marvinctl --tenant weewx` call. `prog` prefixes the failure message."""
    proc = subprocess.run(
        ["marvinctl", "--tenant", "weewx", *args],
        input=input, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        prefix = f"{prog}: " if prog else ""
        sys.exit(f"{prefix}marvinctl {args[0]} failed (rc={proc.returncode}): "
                 f"{proc.stderr.strip()[:400]}")
    return proc.stdout


def resolve_image(container: str, prog: str = "") -> str:
    """The live container's own image, e.g. weatheredscientist/weewx-rtldavis:v2.0.16.

    `exec-ro` takes an image, not a container name, and a hardcoded tag goes stale every
    release, so read it off the running container every time.
    """
    info = json.loads(marvinctl("inspect", container, prog=prog))
    return info[0]["Config"]["Image"]
