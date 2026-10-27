# weewx-influx

A WeeWX service that uploads each archive record to InfluxDB 2.x. It is `david-lutz/weewx-influx2`
(itself `matthewwall/weewx-influx`) with the fixes that file needs on a current system. It works
with any WeeWX driver and does not need the rtldavis driver or this repository's Docker image.

## Why this copy

The upstream port has not changed since 2021. As published it:

- imports `distutils`, which Python 3.12 removed, so WeeWX will not start on a current system;
- turns TLS certificate verification off for every `https` server;
- raises `AttributeError` while reporting an HTTP error from the server, hiding the reason an
  upload failed.

This version fixes those three and a few smaller things. The full list, with dates and reasons, is
in [CHANGES-FROM-UPSTREAM.md](https://github.com/WeatheredScientist/weewx-rtldavis/blob/main/CHANGES-FROM-UPSTREAM.md).
The log line `service version is 0.20+ws.N` tells you which one you are running: `0.20` is stock
upstream.

## Install

```
weectl extension install https://github.com/WeatheredScientist/weewx-rtldavis/releases/download/influx-v0.20%2Bws.2/weewx-influx-0.20+ws.2.zip
```

The extension has the same name (`influx`) as the upstream one, so installing it replaces the
upstream copy. The service class stays `user.influx.Influx` and the section stays
`[StdRESTful]` / `[[Influx]]`, so an existing configuration keeps working untouched. Restart WeeWX
afterward. The URL names a version on purpose; bump it when a new release comes out.

If you have no `[[Influx]]` section yet, the installer adds one with `YOUR_INFLUX_*` placeholders.
Fill in these four:

```
[StdRESTful]
    [[Influx]]
        server_url = http://localhost:8086
        org = YOUR_INFLUX_ORG
        bucket = YOUR_INFLUX_BUCKET
        token = YOUR_INFLUX_TOKEN
```

## What changed that you might notice

- `https` servers are verified against the system CA store. If yours uses a self-signed or
  internal certificate, either add the CA to the system store or set `verify_ssl = false` in
  `[[Influx]]`. That setting is new; the upstream behavior was always "do not verify".
- Per-record messages that upstream logged at INFO are now DEBUG.
- Optional `lease_dir` (off unless set): yield uploads while a shared-host lease file says another
  job holds the machine. Most installs never set it.

The InfluxDB line-protocol schema the uploader writes is described in
[INTERFACES.md section 2](https://github.com/WeatheredScientist/weewx-rtldavis/blob/main/docs/INTERFACES.md#2-influxdb--archivetime-series-surface).

## License

GPL-3.0-or-later, the same as upstream and the rest of this repository. The modification notice
(GPLv3 section 5(a)) is at the top of `influx.py`.
