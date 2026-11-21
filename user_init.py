# SPDX-License-Identifier: GPL-3.0-or-later
"""The image's `user` package (DEC-0244). The Dockerfile copies this file to the venv's
site-packages/user/__init__.py.

The image bakes its modules (the patched driver, the services, the uploaders) into the venv's
`user` package, so they win over anything in the data mount (DEC-0031). Being a package there
also hides the mount's own bin/user, which is where `weectl extension install` puts a module:
WeeWX appends that directory to sys.path, but Python stops at the first `user` package it finds.
Before this file, an extension installed into the mount was listed in weewx.conf and then failed
to import when weewxd started.

The line below adds the mount's bin/user to the end of the package's search path. The baked
modules are still found first, so the stock rtldavis.py that the mount carries never replaces the
patched driver; a module the image does not bake is found in the mount.
"""
import os
import sys

MOUNT_USER_DIR = '/opt/weewx-data/bin/user'

_search_path = sys.modules[__name__].__path__   # this package's __path__, set before __init__ runs
if os.path.isdir(MOUNT_USER_DIR) and MOUNT_USER_DIR not in _search_path:
    _search_path.append(MOUNT_USER_DIR)
