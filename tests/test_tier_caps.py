"""Tier-file size caps, gated on every PR (ops#457, DEC-0239).

eaglehunt-ops' `checks/tier-sweep.sh` reads `dev` after the fact and files an inbox issue
when a tier file crosses its STANDARD §1 cap. It found MANIFEST.md over three times (#554,
ops#457 twice), each a doc-only regrowth at a session close. This test is the same
measurement moved in front of the merge: CI fails the PR instead of the sweep filing later.

Same math as the sweep: characters / 4, characters counted as code points (`wc -m` under a
UTF-8 locale, which Python's len() on decoded text equals). Same caps: BOOT.md ~2,500,
MANIFEST.md ~1,000. Over a cap, the remedy is STANDARD rule 9 (index classes, not
instances) or ARCHIVE/, never a bigger number here.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

CAPS = {"BOOT.md": 2500, "MANIFEST.md": 1000}


def tokens(text: str) -> int:
    return len(text) // 4


def test_tokens_counts_code_points_not_bytes() -> None:
    # A multi-byte glyph is one character for the sweep (LC_ALL=en_US.UTF-8 wc -m).
    assert tokens("§" * 8) == 2
    assert len("§".encode()) == 2


@pytest.mark.parametrize("name", sorted(CAPS))
def test_tier_file_under_cap(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    measured = tokens(text)
    # Compare characters to cap*4, as the sweep does (`chars -le CHAR_CAP`): comparing the
    # floored token count would pass a 4,001-character MANIFEST the sweep files on.
    assert len(text) <= CAPS[name] * 4, (
        f"{name} is {measured} tok, over its {CAPS[name]} cap (STANDARD §1). "
        "Remedy: rule 9 (index classes, not instances) or move text to ARCHIVE/."
    )
