# SPDX-License-Identifier: GPL-3.0-or-later
"""WeeWX extension installer for loop_json_writer.py (DEC-0211, weewx-rtldavis#440).

Install:  weectl extension install <URL of the weewx-loopjson-X.Y.Z.zip release asset>
"""
from weecfg.extension import ExtensionInstaller

# Keep equal to loop_json_writer.__version__; scripts/build_loopjson_zip.sh
# fails the build if they differ, or if the release tag disagrees.
VERSION = '1.0.0'


def loader():
    return LoopJsonInstaller()


class LoopJsonInstaller(ExtensionInstaller):
    def __init__(self):
        super().__init__(
            version=VERSION,
            name='loopjson',
            description='Writes the live loop-data.txt and current.json feed that the '
                        'Eagle Hunt weather dashboard reads, from any WeeWX driver.',
            author='WeatheredScientist',
            author_email='',
            # Appended to the END of process_services, where it has to run: after
            # StdQC and StdWXCalculate, so it sees the final derived values.
            process_services='user.loop_json_writer.LoopJsonWriter',
            config={
                'LoopJsonWriter': {
                    # Relative to WEEWX_ROOT. Mount the feed/ directory into the
                    # proxy, not the two files (renames replace the inode).
                    'path': 'feed/loop-data.txt',
                    'current_path': 'feed/current.json',
                    'current_interval': '60',
                    'ttl_default': '300',
                },
            },
            files=[('bin/user', ['bin/user/loop_json_writer.py'])],
        )
