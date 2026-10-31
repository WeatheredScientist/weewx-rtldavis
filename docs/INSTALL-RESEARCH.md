# Install experience research (S182, 2026-10-29)

Research for P0.8 (public readiness), the basis of DEC-0225: how to make installing this image as easy
and automatic as it can be for an end user, and what a 2-3 page quick start should look like. No
code changed. Companion document: `docs/QUICKSTART.md`, written as it would read once the proposals
below ship, with each proposal-dependent step marked.

Scope: the install path only. Not touched: v2.1.1 release prep, upstream threads, audit 28, or
anything the dashboard owns. DEC-0213 (public face for a new user) and DEC-0217 (host-neutral
monitor defaults) are taken as settled and built on, not reopened.

## 1. Where a new user stumbles today

The README's quick start is six steps and already correct (DEC-0213, proven on a disposable guest
at ops#427). Counted as a user would experience it:

| Step | What the user does | Why it costs |
|---|---|---|
| 1 | Blacklist the DVB kernel module, `rmmod` | Two sudo commands; must know the module name; a reboot is safer than `rmmod` but not said |
| 2 | Write a udev rule with their own gid | A long quoted one-liner; easy to mangle; must re-plug |
| 3 | Seed the config: `mkdir`, `docker create`, `docker cp`, `docker rm` | Four commands to work around the bind mount hiding the baked `weewx.conf` (the bug DEC-0213 found) |
| 4 | Edit `weewx.conf` by hand | A 760-line file; the user must find `[Station]` and `[Rtldavis]` |
| 5 | A 300-character `docker run` line | Ten flags, three of which (`HOME=/tmp`, `BIAS_TEE=0`, `TZ`) are image concerns leaked to the user |
| 6 | `tail` the log and recognize the banner | No "healthy" signal in `docker ps`; nothing says "dongle found, listening on US channel 1" |

Twelve commands, one long file edit, and three things that fail silently or confusingly on a fresh
host: an empty USB bus (`not a device node`, #471), the DVB module re-claiming the dongle after a
reboot if only `rmmod` was run, and a `weewx.conf` missing because step 3 was skipped (crash loop).
`BACKLOG.md` already lists the `BIAS_TEE=1` image default as a hazard (DC onto a shorted antenna)
documented only in a changelog.

The hardware side is already as simple as it gets: the baked config defaults to US band, ISS
channel 1 and the 0.01 in bucket, which is the factory setting of every Davis transmitter (DIP
switches all off). A US user with an untouched ISS has nothing to change under `[Rtldavis]`.

## 2. What comparable projects do

| Project | First-run config | Host prep | Run shape | Worth copying |
|---|---|---|---|---|
| felddy/weewx-docker (the reference WeeWX image) | `docker compose run --rm weewx` generates `weewx.conf` into the bind mount; upgrades via `run --rm weewx station upgrade` with a backup | none needed (serial port) | compose only, `user: uid:gid`, `:5` floating tag | config generated into the mount on first run; compose as the only documented path; arguments pass straight to `weectl` |
| sdr-enthusiasts (readsb and friends, the largest RTL-SDR-in-Docker family) | n/a (env vars only, no config file) | a documented blacklist file with `install <mod> /bin/false` lines plus `update-initramfs -u`; a `docker-install.sh` that does it for you | compose, `--device /dev/bus/usb` whole bus | the blacklist shape that survives reboots and on-demand loads; a host script the docs let you skip the manual section with |
| Debian `librtlsdr0` package | n/a | installs `60-librtlsdr0.rules` (group `plugdev`) and a blacklist for `dvb_usb_rtl28xxu`, `e4000`, `rtl2832` | n/a | on Debian and Ubuntu `apt install rtl-sdr` on the host does steps 1 and 2 for members of `plugdev`; one line instead of four |
| hertzg/rtl_433 | n/a | none documented | `docker run --device /dev/bus/usb/001/003` (single node) | a counterexample: the single-node path changes on re-plug; whole-bus is right |
| linuxserver.io images (general pattern) | entrypoint copies defaults into `/config` only when the file is absent; env vars `PUID`, `PGID`, `TZ` | n/a | compose | "seed if absent, never overwrite" is the convention users expect |

Takeaways: nobody asks the user to `docker create` and `docker cp`; everybody that needs host prep
either scripts it or leans on the distro package; compose is the documented path and `docker run`
is an appendix; `TZ` plus a uid/gid are the only env vars a user is expected to set.

## 3. Proposal, ranked by payoff per unit of change

Each item is incremental (DEC-0014: no rewrite; `entrypoint.sh` is 17 lines and grows to perhaps
60). Version impact follows DEC-0222: these add behavior and change no data contract, so together
they are a minor bump, v2.2.0, never a patch. Items A, B, E, F and G change the image; C, D and H
are repo files and docs only and can land first.

### A. The entrypoint seeds the config when the mount is empty (removes step 3)

Bake the pristine `/opt/weewx-data` a second time at `/opt/weewx-dist/` in the Dockerfile. On
start, if `/opt/weewx-data/weewx.conf` is absent, copy the dist tree in and log one line saying so.
Never touch an existing tree. The mount is already writable by the container's user (that is how
`weewx.sdb` and the log get written today), so no chown is needed. Risk: none for existing users,
whose `weewx.conf` is present; today's behavior on an empty mount is a crash loop. The systemd
unit's `ExecStartPre` config test becomes optional and should be dropped from the example.

### B. First-run station settings from the environment (removes step 4 for most users)

At seed time only, apply `WEEWX_LATITUDE`, `WEEWX_LONGITUDE`, `WEEWX_ALTITUDE` (`"120,foot"`),
`WEEWX_LOCATION` and `WEEWX_UNITS` through `weectl station reconfigure --no-prompt` (every one is a
documented flag in WeeWX 5.1+; unspecified values keep their defaults), and `RTLDAVIS_BAND`
(`US`/`EU`/`NZ`), `RTLDAVIS_ISS_CHANNEL` and `RTLDAVIS_RAIN_BUCKET` by a scoped `sed` on
`[Rtldavis]`. After the first run `weewx.conf` is the only truth: the env vars are read once and
logged as applied, so DEC-0046's "which layer wins" question has a one-line answer (the file). A
compose file with five edited lines is then a complete install. Edge: a user who sets an env var
after first run and expects it to apply; the log line at seed time and a comment in the compose
file cover it.

### C. `host-setup.sh` (collapses steps 1 and 2, adds the checks that fail silently today)

One script in the repo and attached to each release with its sha256 in the notes. The docs say
download it, read it, run it (never `curl | sh`; the research consensus is download-inspect-run
with a pinned release URL). Debian, Ubuntu and Raspberry Pi OS only, stated up front; others get the
manual two steps in `docs/DEPLOY.md`. Idempotent, `--dry-run` prints what it would do. It:

1. Checks `lsusb` for `0bda:2838` or `0bda:2832` and stops with a plain message if none (prevents
   the `not a device node` failure, #471).
2. Writes the blacklist in the sdr-enthusiasts shape (`blacklist` plus `install … /bin/false` for
   `dvb_usb_rtl28xxu`, `rtl2832`, `rtl2830`, `rtl2832_sdr`), runs `modprobe -r`, and
   `update-initramfs -u` where it exists, so the fix survives reboot and on-demand loading.
3. Writes `/etc/udev/rules.d/60-rtl-sdr.rules` for the invoking user's primary group (or
   `--user weewx` for the systemd path), reloads, triggers, and asks for a re-plug.
4. Creates `weewx-data/` and `logs/` next to the compose file.
5. Offers Docker via Docker's own `get.docker.com` if `docker` is absent, after a y/n, and adds the
   user to the `docker` group.
6. Writes `TZ`, uid and gid into `.env` next to the compose file, so the user edits only station
   values.

Alternative considered: tell Debian users `sudo apt install rtl-sdr` and `usermod -aG plugdev`,
which installs the rules and blacklist for them. That is the fallback the script prints when it
refuses an unknown distro; it is not the primary path because the group in the package's rule is
`plugdev`, which the container user is not in without `--group-add`.

### D. Compose is the documented path; `docker run` moves to an appendix

Ship `docker-compose.yml` plus `.env.example` with every user value in `.env` (`TZ`, `PUID`,
`PGID`, the station values of B). The compose file already has the hardened shape from DEC-0213.
`docker run` stays in `docs/DEPLOY.md` for people who want it, with the systemd unit.

### E. A `doctor` command, a `HEALTHCHECK`, and a one-line startup summary (fixes step 6)

- `docker compose run --rm weewx doctor`: runs `rtl_test -t` for two seconds, checks the kernel
  module is not loaded on the host (visible through `/sys/bus/usb/devices/*/driver`), checks the
  device node is readable by the current uid, prints the band and channel from `weewx.conf`, and
  exits non-zero with the matching README troubleshooting line. The entrypoint dispatches on its
  first argument (`doctor`, `weectl …`, default `weewxd`), the felddy pattern.
- `HEALTHCHECK` in the Dockerfile: `loop-data.txt` (or `weewx.log`) modified within the last 300 s.
  `docker ps` then shows `healthy`/`unhealthy`, and compose can restart on unhealthy. Note the
  freeze-mechanism blocker (DEC-0068/0094): a health check that restarts on a stale log is also the
  cheapest stall remedy the project has never had in-container; worth a separate DEC, not folded in
  here.
- Startup: `rtldavis: US band, ISS channel 1, bucket 0.01 in, gain auto; config /opt/weewx-data/
  weewx.conf; log /var/log/weewx/weewx.log`. One line, after the driver banner.

### F. Simulator mode for try-before-hardware

`WEEWX_DRIVER=simulator` at seed time (or a compose profile `sim`) runs WeeWX's Simulator with the
same uploaders, loop writer and log layout, so a user can bring up the stack, the dashboard and an
upload before the dongle or antenna arrive, then re-seed with the real driver. CI already proves
the writer this way (`scripts/prove_loopjson.sh`). Cheap, and it turns "it does not work" reports
into "radio" versus "everything else" in one step.

### G. Image defaults that stop leaking into the run line

- `ENV HOME=/tmp` in the Dockerfile (the reason it exists, DEC-0147, applies to every non-root
  user, not only prod's).
- `BIAS_TEE` default `0` (the safe state; `BACKLOG.md` already flags the current default). A
  release note and a startup log line carry the change.
- `TZ` unset is logged loudly as "UTC, daily rain resets at 00:00 UTC; set TZ".
The run line then needs the mounts, the device and the user, nothing else.

### H. Docs: one 2-page quick start, README as the overview, DEPLOY as the service doc

- `docs/QUICKSTART.md` (draft attached): what you need, four steps, no-hardware-yet, five-line
  troubleshooting, what next. Nothing else.
- README: keep the overview, "what is different", requirements, the uploads table, data contract,
  versions, credits; replace the six-step quick start with a link and the four-line summary. The
  Docker Hub overview syncs from README, so the four lines are what Hub visitors see.
- `docs/DEPLOY.md`: systemd (hardened, dedicated user), `docker run`, Synology, monitoring.
  Unchanged in substance; it loses the "do README steps 1-4 first" dependency once C exists.

### I. Later, out of this scope

- A GHCR mirror of the image, so an unauthenticated Pi is not rate-limited by Docker Hub. CI already
  pushes arm64 to GHCR (DEC-0215); publishing the joined index there too is small.
- A Home Assistant add-on. The largest pool of RTL-SDR-curious weather users is on HA (rtl_433's
  add-on is the model). It is a separate repository and a different config surface; the data
  contract makes it feasible without touching this image. Highest reach, highest cost.
- A Raspberry Pi image (pi-gen) with Docker, the host prep and the compose file baked in. Only
  worth it after C and D have run on a stock Pi OS for a while.

## 4. Positioning: who this is for, and the non-Davis reader

- Best suited: a Davis Vantage Pro2, Pro2 Plus or Vue owner who wants the data without the
  console's WeatherLink path, on a small always-on Linux box within radio range of the ISS. A
  Raspberry Pi 4 or 5 on a 64-bit OS, a mini PC, a home server or a NAS with Docker. Not a laptop,
  not Windows or macOS (USB through a VM adds the timing jitter that breaks hop tracking; the README
  says this already).
- The console can stay. Interception is passive; this adds a second receiver and changes nothing at
  the ISS.
- A non-Davis WeeWX user gets two things from this repository today, and the quick start should say
  so in one paragraph: the loop-JSON writer and the InfluxDB 2 uploader, both installable with
  `weectl extension install <release zip>` on any driver, no Docker needed. That is the
  "re-pointable contract" of PRINCIPLES §1 made visible.
- A non-Davis RTL-SDR user (Acurite, Ecowitt, LaCrosse and the rest of the 433 MHz world) is not
  served by this image and should be sent to `weewx-sdr` plus `rtl_433` in one sentence, so they do
  not file issues here.

## 5. How to know it worked

- Count: commands a user types before the first LOOP packet, today 12 plus a file edit. Target
  after C and D: 4 (download script, run script, edit `.env`, `docker compose up -d`) and no file
  edit for a US station with factory DIP switches.
- Acceptance test: a stock Raspberry Pi OS 64-bit image plus the quick start, timed, by someone who
  has not read the repository. The ops#439 guest with a virtual USB device can prove everything but
  RF; the first LOOP needs the owner's hardware or an adopter.
- The quick start stays under three printed pages; `wc -w` under 900.

## 6. Open questions for the owner

1. Scope of v2.2.0: A, B, E, F, G together, or A plus G first as a smaller step? (Recommendation:
   all of A, B, G and the startup line in one minor release; `doctor`, `HEALTHCHECK` and the
   Simulator profile can follow, each a patch or minor on its own.)
2. `host-setup.sh`: in this repository, or is a host script outside the "driver plus Docker build"
   remit? (Recommendation: here, under `scripts/`, attached to releases. It is the step every
   comparable project either scripts or delegates to a package.)
3. The `HEALTHCHECK` restart-on-unhealthy question touches the freeze blocker. Separate DEC, or
   leave the health check informational only in the first cut? (Recommendation: informational
   first.)

## 7. Sources

- felddy/weewx-docker README: https://github.com/felddy/weewx-docker
- sdr-enthusiasts readsb README, kernel module section: https://github.com/sdr-enthusiasts/docker-readsb-protobuf/blob/main/README.md
- Debian rtl-sdr README.Debian (udev rules, plugdev, blacklist): https://metadata.ftp-master.debian.org/changelogs/main/r/rtl-sdr/rtl-sdr_2.0.3-1_README.Debian
- WeeWX 5.1 `weectl station` reference (create/reconfigure flags, `--no-prompt`): https://weewx.com/docs/5.1/utilities/weectl-station/
- hertzg/rtl_433 Docker image: https://git.tdem.in/hertzg/rtl_433_docker
- Davis transmitter ID factory default (all DIP switches off = ID 1): https://www.manualslib.com/manual/586586/Davis-Instruments-Anemometer-Transmitter-Kit.html
- Install-script hygiene (download, inspect, pin, `curl --fail`, checksum in release notes): https://camel.apache.org/download/camel-cli-launcher/ and https://github.com/boostsecurityio/poutine/pull/130/files
- Volume seeding conventions: https://forums.docker.com/t/how-to-generate-default-data-for-docker-volumes-ex-apache-config-folder/127998
- In-repo: DEC-0213, DEC-0217, DEC-0147 (`HOME=/tmp`), DEC-0222 (version rule), DEC-0046 (which layer wins), ROADMAP P0.8 phase 1, `BACKLOG.md` session-A doc debts, ops#427 and #471.
