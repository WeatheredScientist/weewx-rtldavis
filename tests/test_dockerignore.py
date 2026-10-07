"""Offline guard: the .dockerignore allowlist admits every Dockerfile COPY source (S144).

.dockerignore excludes everything (`*`) and lets back in only the build inputs, because on
marvin the build context is the tenant root: a live checkout that also holds weewx-data/ (the
archive, and conf backups with credentials), influxdb/ and logs/. A COPY source added to the
Dockerfile without its allowlist line fails the build on marvin; this test fails it in CI first.

Run:  python3 -m pytest tests/    OR    python3 tests/test_dockerignore.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _copy_sources():
    srcs = []
    with open(os.path.join(ROOT, "Dockerfile")) as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3 and parts[0] == "COPY" and not parts[1].startswith("--"):
                srcs.append(parts[1])
    return srcs


def _allowlist():
    with open(os.path.join(ROOT, ".dockerignore")) as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
    return lines


def _admitted(path, allow):
    return any(path == a or path.startswith(a.rstrip("/") + "/") for a in allow)


def test_allowlist_starts_by_excluding_everything():
    assert _allowlist()[0] == "*"


def test_every_copy_source_is_admitted():
    allow = [ln[1:] for ln in _allowlist() if ln.startswith("!")]
    srcs = _copy_sources()
    assert len(srcs) >= 10, "Dockerfile COPY parse found too few sources: %r" % srcs
    missing = [s for s in srcs if not _admitted(s, allow)]
    assert not missing, "add these COPY sources to .dockerignore: %r" % missing


def test_allowlist_names_only_existing_paths_and_no_data_dirs():
    allow = [ln[1:].rstrip("/") for ln in _allowlist() if ln.startswith("!")]
    for a in allow:
        assert os.path.exists(os.path.join(ROOT, a)), "stale allowlist entry: %s" % a
        assert a.split("/")[0] not in ("weewx-data", "influxdb", "logs", "conf-archive"), a


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
