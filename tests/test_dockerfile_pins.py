"""Offline guard: every upstream download in the Dockerfile is pinned and checksummed (DEC-0214).

Until S156 the image fetched `src.tgz` from `refs/heads/main` and weewx-influx2 from
`archive/master.zip`: whatever upstream held on build day, unchecked. Public builds were not
reproducible, and a replaced upstream file would have slipped in silently. This test fails if a
branch-tracking URL comes back, if a fetched file loses its sha256 check, or if a pin ARG is not a
full commit id / full sha256.

Since DEC-0219 the image installs `influx.py` from this repo's extension, so `src.tgz` is the one
remaining download; the checks below no longer expect two.

Run:  python3 -m pytest tests/    OR    python3 tests/test_dockerfile_pins.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _dockerfile():
    with open(os.path.join(ROOT, "Dockerfile")) as f:
        return f.read()


def _args():
    return dict(re.findall(r"^ARG (\w+)=(\S+)$", _dockerfile(), re.M))


def _urls():
    return re.findall(r"https?://[^\s\"']+", _dockerfile())


def test_no_branch_tracking_urls():
    bad = [u for u in _urls() if re.search(r"refs/heads/|/(master|main)\.(zip|tar\.gz|tgz)$", u)]
    assert not bad, "unpinned upstream fetch: %r" % bad


def test_every_github_fetch_names_a_commit_arg():
    fetches = [u for u in _urls() if "github.com" in u]
    assert len(fetches) >= 1, "Dockerfile URL parse found too few fetches: %r" % fetches
    for u in fetches:
        m = re.search(r"\$\{(\w+_COMMIT)\}", u)
        assert m, "fetch not pinned to a commit ARG: %s" % u
        assert m.group(1) in _args(), "pin ARG %s has no default in the Dockerfile" % m.group(1)


def test_pin_args_are_full_ids():
    args = _args()
    commits = {k: v for k, v in args.items() if k.endswith("_COMMIT")}
    shas = {k: v for k, v in args.items() if k.endswith("_SHA256")}
    assert len(commits) >= 1 and len(commits) == len(shas), args
    for k, v in commits.items():
        assert re.fullmatch(r"[0-9a-f]{40}", v), "%s is not a full commit id: %s" % (k, v)
        assert k.replace("_COMMIT", "_SHA256") in shas, "%s has no matching _SHA256 ARG" % k
    for k, v in shas.items():
        assert re.fullmatch(r"[0-9a-f]{64}", v), "%s is not a full sha256: %s" % (k, v)


def test_every_downloaded_file_is_checked_before_use():
    text = _dockerfile()
    outputs = re.findall(r"curl [^\n]*-o (\S+)", text)
    assert len(outputs) >= 1, outputs
    for out in outputs:
        assert re.search(r"_SHA256\}  %s\" \| sha256sum -c -" % re.escape(out), text), (
            "%s is downloaded but never checked with sha256sum -c" % out)


def test_dupgate_assertion_kept():
    assert 'test "$(grep -c dupwindow main.go)" = "2"' in _dockerfile()


def test_no_brace_expansion_in_run_lines():
    # /bin/sh is dash: `rm -rf /x/{a,b}` removes nothing (audit 15, #468's sibling)
    bad = [ln for ln in _dockerfile().splitlines()
           if re.search(r"\{[^}$ ]*,[^} ]*\}", ln) and not ln.lstrip().startswith("#")]
    assert not bad, "brace expansion is a no-op under dash: %r" % bad


def test_seed_config_backups_removed_after_last_weectl():
    # weectl leaves weewx.conf.<timestamp> beside the config (#468)
    text = _dockerfile()
    cleanup = text.index("rm -f /opt/weewx-data/weewx.conf.[0-9]*")
    assert cleanup > text.rindex("weectl station reconfigure")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
