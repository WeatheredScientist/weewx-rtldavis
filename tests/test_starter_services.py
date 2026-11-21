# SPDX-License-Identifier: GPL-3.0-or-later
"""What the image's starter runs, checked offline (DEC-0244, #596, #597).

The image seeds a config that `weectl station create` writes at build time, not
weewx.conf.example, so these tests read the inputs that build uses: the Dockerfile, the influx
installer and the venv package's __init__. scripts/smoke_image.sh checks the seeded file itself
in a built image, and runs weewxd on it.

Run:  .venv/bin/python -m pytest tests/test_starter_services.py
"""
import importlib
import importlib.util
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return f.read()


def _load_installer(rel, name):
    """Load an extension's install.py with a stand-in weecfg.extension (WeeWX is not in .venv)."""
    captured = {}

    class ExtensionInstaller:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    weecfg = types.ModuleType('weecfg')
    ext = types.ModuleType('weecfg.extension')
    ext.ExtensionInstaller = ExtensionInstaller
    saved = {k: sys.modules.get(k) for k in ('weecfg', 'weecfg.extension')}
    sys.modules['weecfg'], sys.modules['weecfg.extension'] = weecfg, ext
    try:
        spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.loader()
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return captured


# --- #596: the influx extension adds a section that posts nothing until configured ---------------

def test_influx_installer_uses_replace_me_for_every_key_weewx_checks():
    cfg = _load_installer('extensions/influx/install.py', '_influx_install')['config']
    section = cfg['StdRESTful']['Influx']
    # influx.py calls get_site_dict(cfg, 'Influx', 'org', 'bucket', 'token'); weewx skips the
    # service when any of these is the literal replace_me.
    for key in ('org', 'bucket', 'token'):
        assert section[key] == 'replace_me', key
    src = _read('influx.py')
    assert "get_site_dict(cfg_dict, 'Influx', 'org', 'bucket', 'token')" in src


def test_influx_installer_has_no_enable_line():
    # weectl merges only missing keys: an enable line here would land in a working config that has
    # none and switch its uploader off on a reinstall.
    section = _load_installer('extensions/influx/install.py', '_influx_install')['config']['StdRESTful']['Influx']
    assert 'enable' not in section


# --- #597: the starter runs the loop writer and DewpointCacher ------------------------------------

def test_dockerfile_installs_the_loopjson_extension_into_the_starter():
    df = _read('Dockerfile')
    assert 'COPY extensions/loopjson/install.py /tmp/weewx-loopjson/install.py' in df
    assert 'COPY loop_json_writer.py /tmp/weewx-loopjson/bin/user/loop_json_writer.py' in df
    assert 'weectl extension install /tmp/weewx-loopjson --yes' in df


def test_dockerfile_bakes_the_loop_writer_into_the_venv():
    df = _read('Dockerfile')
    assert ('COPY loop_json_writer.py '
            '/opt/weewx-venv/lib/python3.14/site-packages/user/loop_json_writer.py') in df


def test_dockerfile_asserts_the_final_process_services_line():
    df = _read('Dockerfile')
    want = ('weewx\\.wxservices\\.StdWXCalculate, user\\.dewpoint_service\\.DewpointCacher, '
            'user\\.loop_json_writer\\.LoopJsonWriter$')
    assert want in df
    assert 'pressure_service.DavisPressureFetcher' not in df.split('# Copy custom service files')[0]


def test_loopjson_installer_appends_the_writer():
    kw = _load_installer('extensions/loopjson/install.py', '_loopjson_install')
    assert kw['process_services'] == 'user.loop_json_writer.LoopJsonWriter'


# --- #597 question 3: a module installed into the mount imports ------------------------------------

def test_dockerfile_installs_user_init_as_the_package_init():
    df = _read('Dockerfile')
    assert 'COPY user_init.py /opt/weewx-venv/lib/python3.14/site-packages/user/__init__.py' in df
    assert 'touch /opt/weewx-venv/lib/python3.14/site-packages/user/__init__.py' not in df


def _make_user_package(tmp_path, mount):
    venv = tmp_path / 'site'
    pkg = venv / 'user'
    pkg.mkdir(parents=True)
    src = _read('user_init.py').replace("'/opt/weewx-data/bin/user'", repr(str(mount)))
    assert repr(str(mount)) in src
    (pkg / '__init__.py').write_text(src)
    (pkg / 'baked.py').write_text("WHERE = 'venv'\n")
    return venv


def _fresh_import(venv, monkeypatch):
    monkeypatch.syspath_prepend(str(venv))
    for k in [k for k in sys.modules if k == 'user' or k.startswith('user.')]:
        monkeypatch.delitem(sys.modules, k)
    importlib.invalidate_caches()


def test_baked_module_wins_and_a_mount_only_module_imports(tmp_path, monkeypatch):
    mount = tmp_path / 'data' / 'bin' / 'user'
    mount.mkdir(parents=True)
    (mount / 'baked.py').write_text("WHERE = 'mount'\n")      # the stock-driver situation
    (mount / 'mount_only.py').write_text("WHERE = 'mount'\n")  # a weectl-installed extension
    venv = _make_user_package(tmp_path, mount)
    _fresh_import(venv, monkeypatch)
    assert importlib.import_module('user.baked').WHERE == 'venv'
    assert importlib.import_module('user.mount_only').WHERE == 'mount'


def test_no_mount_directory_leaves_the_package_alone(tmp_path, monkeypatch):
    mount = tmp_path / 'absent'
    venv = _make_user_package(tmp_path, mount)
    _fresh_import(venv, monkeypatch)
    user = importlib.import_module('user')
    assert list(user.__path__) == [str(venv / 'user')]
    assert importlib.import_module('user.baked').WHERE == 'venv'
