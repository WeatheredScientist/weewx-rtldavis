# weewx-loopjson

A WeeWX service that writes the live weather feed the Eagle Hunt weather dashboard reads: a JSON
file rewritten on every LOOP packet, and a second copy for first page loads. It works with any
WeeWX driver. It does not need the rtldavis driver or this repository's Docker image.

## Install

```
weectl extension install https://github.com/WeatheredScientist/weewx-rtldavis/releases/download/loopjson-v1.0.0/weewx-loopjson-1.0.0.zip
```

Then restart WeeWX. The URL names a version on purpose; bump it when a new release comes out.

The installer does two things:

- Copies `loop_json_writer.py` into WeeWX's `user` directory.
- Adds `user.loop_json_writer.LoopJsonWriter` to the **end** of `process_services` and writes a
  `[LoopJsonWriter]` section into `weewx.conf`.

**It has to be last in `process_services`.** The writer reads the final values after StdQC and
StdWXCalculate have run, and a service listed after it would change them unseen. If you install
another extension later that adds to `process_services`, it lands after this one. Move
`user.loop_json_writer.LoopJsonWriter` back to the end by hand.

## Configuration

```
[LoopJsonWriter]
    path = feed/loop-data.txt
    current_path = feed/current.json
    current_interval = 60
    ttl_default = 300
```

- `path`, `current_path`: output files. A relative path resolves against `WEEWX_ROOT`. The writer
  creates the directory at startup.
- `current_interval`: seconds between writes of `current.json`. `0` writes it on every packet.
- `ttl_default`: how long, in seconds, a value from an earlier packet may stand in for a field the
  current packet lacks. Past that the field is left out rather than served stale.

If you also have a `[DavisPressure]` section, `barometer_inHg` uses twice its `fetch_interval` as
its TTL. Without one it uses `ttl_default`.

## Cadence and files

- `loop-data.txt` is written on every packet. Its `dateTime` is a liveness signal, so a consumer
  can tell the station has stopped. Do not throttle it.
- `current.json` is a cold-load snapshot, written at most once per `current_interval`. Do not use
  its `dateTime` for liveness.
- Both are written to a temporary file and renamed into place. **If you mount the files into a
  container, mount their directory, not the files**: a single-file mount pins the old inode and
  the reader sees a frozen file.

## Fields

The field table, units and caching rules are in
[INTERFACES.md section 1](https://github.com/WeatheredScientist/weewx-rtldavis/blob/loopjson-v1.0.0/docs/INTERFACES.md#1-loop-json--real-time-surface),
pinned to the release tag so it matches this version. Every write carries
`"writer": "loop_json_writer/1.0.0"`.

Versions follow the field contract: major when a key is renamed, removed or changes units; minor
for a new optional key; patch for a behavior fix.

## Not the same as weewx-loopdata

chaunceygardiner's [weewx-loopdata](https://github.com/chaunceygardiner/weewx-loopdata) also writes
a file called `loop-data.txt`, with a different key shape. This extension is not interchangeable
with it. Run one or the other, and point the dashboard at the one you run.

## License

GPL-3.0-or-later, the same as the rest of this repository.
