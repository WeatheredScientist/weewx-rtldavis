"""Offline guards for the arm64 publishing path (DEC-0215).

Two kinds of check:
- scripts/oci_platforms.py, which join_multiarch.sh trusts to say which manifest is which platform
  and which commit the arm64 image was built from, is tested against the three shapes imagetools
  emits (a one-platform index with an attestation, a bare manifest, a multi-platform index).
- the workflows keep their security shape: the publish job holds only GITHUB_TOKEN with
  `packages: write`, never runs on a pull request or a self-hosted runner, and pins its actions
  to a commit; image.yml stays secret-free and read-only (DEC-0214).

Run:  python3 -m pytest tests/
"""
import importlib.util
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")

_spec = importlib.util.spec_from_file_location(
    "oci_platforms", os.path.join(ROOT, "scripts", "oci_platforms.py"))
assert _spec is not None and _spec.loader is not None
oci = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oci)

INDEX = "application/vnd.oci.image.index.v1+json"
MANIFEST = "application/vnd.oci.image.manifest.v1+json"
ATTESTATION = {"mediaType": MANIFEST, "digest": "sha256:att",
               "platform": {"architecture": "unknown", "os": "unknown"}}


def _config(arch, revision=None, variant=None):
    cfg = {"architecture": arch, "os": "linux",
           "config": {"Labels": {"org.opencontainers.image.revision": revision} if revision else {}}}
    if variant:
        cfg["variant"] = variant
    return cfg


def _read(name):
    with open(os.path.join(WORKFLOWS, name)) as f:
        return f.read()


# --- oci_platforms.summarize --------------------------------------------------------------------

def test_single_platform_index_drops_the_attestation():
    # The shape marvin's builds have on Hub (v2.0.20, measured S156).
    out = oci.summarize({
        "manifest": {"mediaType": INDEX, "digest": "sha256:idx", "manifests": [
            {"mediaType": MANIFEST, "digest": "sha256:amd",
             "platform": {"architecture": "amd64", "os": "linux"}}, ATTESTATION]},
        "image": _config("amd64"),
    })
    assert out == {"digest": "sha256:idx",
                   "platforms": {"linux/amd64": {"digest": "sha256:amd", "revision": None}}}


def test_bare_manifest_takes_platform_and_revision_from_config():
    out = oci.summarize({
        "manifest": {"mediaType": MANIFEST, "digest": "sha256:arm"},
        "image": _config("arm64", revision="abc123", variant="v8"),
    })
    assert out == {"digest": "sha256:arm",
                   "platforms": {"linux/arm64": {"digest": "sha256:arm", "revision": "abc123"}}}


def test_multi_platform_index_maps_configs_and_normalizes_arm64_variant():
    out = oci.summarize({
        "manifest": {"mediaType": INDEX, "digest": "sha256:joined", "manifests": [
            {"mediaType": MANIFEST, "digest": "sha256:amd",
             "platform": {"architecture": "amd64", "os": "linux"}},
            {"mediaType": MANIFEST, "digest": "sha256:arm",
             "platform": {"architecture": "arm64", "os": "linux", "variant": "v8"}},
            ATTESTATION]},
        "image": {"linux/amd64": _config("amd64"), "linux/arm64": _config("arm64", "abc123")},
    })
    assert out["digest"] == "sha256:joined"
    assert out["platforms"] == {
        "linux/amd64": {"digest": "sha256:amd", "revision": None},
        "linux/arm64": {"digest": "sha256:arm", "revision": "abc123"},
    }


def test_32bit_arm_variants_stay_distinct():
    out = oci.summarize({
        "manifest": {"mediaType": INDEX, "digest": "sha256:i", "manifests": [
            {"mediaType": MANIFEST, "digest": "sha256:v6",
             "platform": {"architecture": "arm", "os": "linux", "variant": "v6"}},
            {"mediaType": MANIFEST, "digest": "sha256:v7",
             "platform": {"architecture": "arm", "os": "linux", "variant": "v7"}}]},
        "image": {"linux/arm/v6": _config("arm"), "linux/arm/v7": _config("arm")},
    })
    assert sorted(out["platforms"]) == ["linux/arm/v6", "linux/arm/v7"]


# --- workflow security shape --------------------------------------------------------------------

def test_publish_workflow_holds_no_stored_secret():
    assert "secrets." not in _read("image-publish.yml")


def test_publish_workflow_permissions_are_exactly_read_and_packages():
    text = _read("image-publish.yml")
    blocks = re.findall(r"^permissions:\n((?:  \S.*\n)+)", text, re.M)
    assert blocks == ["  contents: read\n  packages: write\n"], blocks
    assert not re.search(r"^[ \t]+permissions:", text, re.M), "no job may widen permissions"


def test_publish_workflow_never_runs_on_pull_requests():
    text = _read("image-publish.yml")
    on = text.split("\non:", 1)[1].split("\npermissions:", 1)[0]
    assert "pull_request" not in on
    assert "tags:" in on


def test_publish_workflow_runs_native_arm64():
    assert re.findall(r"runs-on:\s*(\S+)", _read("image-publish.yml")) == ["ubuntu-24.04-arm"]


def test_publish_workflow_pins_actions_to_a_commit():
    uses = re.findall(r"uses:\s*(\S+)", _read("image-publish.yml"))
    assert uses
    for u in uses:
        assert re.search(r"@[0-9a-f]{40}$", u), "not pinned to a commit: %s" % u


def test_no_workflow_uses_a_self_hosted_runner():
    for name in os.listdir(WORKFLOWS):
        for runner in re.findall(r"runs-on:\s*(.+)", _read(name)):
            assert "self-hosted" not in runner, name  # OPS-DEC-0117


def test_prove_workflow_stays_secret_free_and_read_only():
    text = _read("image.yml")
    assert "secrets." not in text
    assert re.search(r"^permissions:\n  contents: read\n(?!  )", text, re.M)
    assert "docker push" not in re.sub(r"(?m)^\s*#.*$", "", text).split("\njobs:", 1)[1], \
        "image.yml must not push an image"
