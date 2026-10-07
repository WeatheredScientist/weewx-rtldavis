"""Helpers for ops/weewx_bump_check.sh, run under the scratch venv's interpreter.

  wu                     assert how StdWunderground wires its two threads
  configure CONF FEEDDIR point a scratch station at the Simulator, our offline services and a
                         dummy non-routable Wunderground target

Nothing here talks to the network. The station id and password are throwaway strings and the
upload target is a closed local port.
"""
import sys
import threading

DEAD_URL = "http://127.0.0.1:9/x"     # discard port: connection refused, nothing leaves the box


def check_wunderground():
    """The live [[Wunderground]] stanza sets rapidfire and archive_post together.

    weewx 5.5.0 built both threads on the archive endpoint and raised TypeError when rtfreq
    was also set. 5.5.1 routes each thread to its own endpoint. Prod must end up with the
    rapidfire thread on rtupdate, so this asserts that outcome rather than merely "no error".
    """
    import configobj
    import weewx
    import weewx.restx as restx

    threading.Thread.start = lambda self: None      # never start a network thread

    class Engine:
        def bind(self, *args, **kwargs):
            pass

    def build(extra):
        cfg = configobj.ConfigObj({
            "WEEWX_ROOT": "/tmp",
            "StdRESTful": {"Wunderground": dict(
                {"enable": "true", "station": "KTEST1", "password": "YOUR_PASSWORD",
                 "rapidfire": "True", "archive_post": "True"}, **extra)},
            "DataBindings": {"wx_binding": {
                "database": "d", "table_name": "archive",
                "manager": "weewx.manager.DaySummaryManager",
                "schema": "schemas.wview_extended.schema"}},
            "Databases": {"d": {"database_name": "x.sdb", "database_type": "SQLite"}},
            "DatabaseTypes": {"SQLite": {"driver": "weedb.sqlite", "SQLITE_ROOT": "/tmp"}},
            "StdArchive": {"data_binding": "wx_binding"},
        })
        svc = restx.StdWunderground(Engine(), cfg)
        return svc.archive_thread, svc.loop_thread

    print("weewx %s" % weewx.__version__)
    failures = 0
    for label, extra in (("live shape", {}), ("with rtfreq", {"rtfreq": "5"})):
        try:
            archive, loop = build(extra)
        except Exception as exc:
            print("  FAIL %-12s raised %s: %s" % (label, type(exc).__name__, exc))
            failures += 1
            continue
        ok = archive.server_url == restx.StdWunderground.pws_url \
            and loop.server_url == restx.StdWunderground.rf_url
        print("  %s %-12s archive=%s loop=%s" % (
            "ok  " if ok else "FAIL", label, archive.server_url, loop.server_url))
        failures += 0 if ok else 1
    return failures


def configure(conf_path, feed_dir):
    import configobj
    conf = configobj.ConfigObj(conf_path)
    conf["Station"]["station_type"] = "Simulator"
    wu = conf["StdRESTful"]["Wunderground"]
    wu.update({"enable": "true", "station": "KTEST1", "password": "YOUR_PASSWORD",
               "rapidfire": "True", "archive_post": "True", "server_url": DEAD_URL})
    engine = conf["Engine"]["Services"]
    engine["process_services"] = list(engine["process_services"]) + [
        "user.dewpoint_service.DewpointCacher", "user.loop_json_writer.LoopJsonWriter"]
    conf["LoopJsonWriter"] = {"path": feed_dir + "/loop-data.txt",
                              "current_path": feed_dir + "/current.json"}
    conf.write()


if __name__ == "__main__":
    if sys.argv[1] == "wu":
        sys.exit(1 if check_wunderground() else 0)
    if sys.argv[1] == "configure":
        configure(sys.argv[2], sys.argv[3])
        sys.exit(0)
    sys.exit("usage: weewx_bump_probe.py wu | configure CONF FEEDDIR")
