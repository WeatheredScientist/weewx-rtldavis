# SPDX-License-Identifier: GPL-3.0-or-later
"""WeeWX extension installer for influx.py (DEC-0219, weewx-rtldavis#474).

Same extension name, service class and [StdRESTful][[Influx]] stanza as david-lutz/weewx-influx2,
so it replaces that extension in place and an existing weewx.conf keeps working.

Install:  weectl extension install <URL of the weewx-influx-VERSION.zip release asset>
"""
from weecfg.extension import ExtensionInstaller

# Keep equal to influx.VERSION; scripts/build_influx_zip.sh fails the build if they differ,
# or if the release tag disagrees.
VERSION = "0.20+ws.3"


def loader():
    return InfluxInstaller()


class InfluxInstaller(ExtensionInstaller):
    def __init__(self):
        super().__init__(
            version=VERSION,
            name='influx',
            description='Upload weather data to InfluxDB 2.x (patched: Python 3.12+, '
                        'TLS verified by default).',
            author='Matthew Wall; David Lutz; WeatheredScientist',
            author_email='',
            restful_services='user.influx.Influx',
            # replace_me, not an `enable = false` line (DEC-0244): weewx skips the uploader while
            # org, bucket or token is the literal replace_me, so a new install posts nothing until
            # configured. weectl merges only missing keys, so a reinstall over a working config
            # keeps its values; an enable line here would be merged into a config without one and
            # silently switch a working uploader off.
            config={
                'StdRESTful': {
                    'Influx': {
                        'server_url': 'http://localhost:8086',
                        'org': 'replace_me',
                        'bucket': 'replace_me',
                        'token': 'replace_me'}}},
            files=[('bin/user', ['bin/user/influx.py'])],
        )
