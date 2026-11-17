# A dev/test receiver on Zaphod: WSL2, Docker Engine, usbipd-win, the V4L

**Status:** Proposed and independently reviewed. Nothing is built, and nothing on Zaphod or marvin
has changed. The owner answered the two questions that shape it (§1): the receiver is for dev and
test, and it reuses the V4L once the NAS no longer needs it. The DEC number is assigned when the
plan is accepted, so a parallel session can't take the same one. **Session:** S204z (Opus 5.5),
2026-11-16 · **Build tracker:** the issue linked from the PR · **Applies:** DEC-0011, DEC-0012,
DEC-0014, DEC-0147, DEC-0154, DEC-0225, DEC-0235, DEC-0237, DEC-0238 · **Orders against:**
DEC-0236

Zaphod is the owner's Windows 11 Pro gaming PC. It never sleeps, and it's a satellite of the home
estate with its own repo and Claude session. **Every step on Zaphod goes through Zaphod's own
session, on the owner's yes in that chat.** No session in this repo runs anything there.

---

## 0. What exists today (measured, not assumed)

Read 2026-11-16 from Zaphod's own inventory, collected 2026-11-15/16. Only facts that bear on
this design are here; the rest stays in Zaphod's private repo.

- **Virtualization:** WSL2 (`VirtualMachinePlatform`) is on and VBS is running; the Hyper-V
  feature is off. **WSL** has one distro, an `Ubuntu` left from May, and its version is behind the
  current release.
- **The May build:** a VirtualBox + Vagrant VM named `weewx-rtldavis` (last written 2026-05-27),
  with VirtualBox's boot-start kernel drivers and a VirtualBox version behind its security
  releases. **usbipd-win 5.3.0** is installed with the installer's default firewall rule ("allow all
  local subnets") and no device bound.
- **Retirement in flight (not this plan's work).** On 2026-11-16 the owner decided to retire the May
  VM. Zaphod's session is exporting it to Foundation, then removing it, VirtualBox and Vagrant,
  and deciding about usbipd-win. If usbipd-win is kept, its default rule should go now (nothing is
  bound, nothing needs it), and this plan's build narrows it per §4.1. If it's removed, the build
  installs the current release.
- **The radio:** the owner's second stick is an RTL-SDR Blog **V4L** (R828S). It's on the NAS now
  for DEC-0236's reference-receiver run. Only librtlsdr v2.0.3 drives it (the S202 addendum in
  `docs/RTLSDR-V4-AND-PINNING.md`). DEC-0238 moves the image to v2.0.3 after a prod soak. Until
  then, the test tag `v2.4.0-v4l-test` is the only image that drives it.
- **Side finding, this repo:** the image's starter config (`weewx.conf.example`) ships eight
  uploaders with `enable = true` and `YOUR_*` placeholders (AWEKAS, CWOP, PWSweather, WOW,
  WOW-BE, Wunderground, Influx, OgoXe). The entrypoint seeds and then starts `weewxd` in one step
  (`entrypoint.sh`, DEC-0225). **A plain first start therefore runs every one of those uploaders
  against placeholder credentials.** `[DavisPressure]` is listed in the services too. Its
  placeholder station id makes it inert (#451), so it makes no API call. §5 works around the
  uploaders here; the product question (should the starter ship them off?) is #587.

## 1. Purpose (owner, 2026-11-16)

**A dev/test receiver for the fork.** The ROADMAP's blocker discipline (under DEC-0011) says
there's "no drop-in dev receiver", so RF-dependent verification today waits for a reversible hot
swap on prod. A second receiver on a second host closes that gap: a dev build, a decoder patch or a
librtlsdr bump can run against live RF for days without touching prod. It also proves the
Windows-through-WSL install path, which heartofgold's MARVIN-DEC-0228 wanted proven ("the weewx
stack is meant to run anywhere").

**What it isn't:**

- **Not a backup for prod.** It never uploads, holds no production credential, and nothing reads
  its data. A warm standby would put production credentials on a gaming PC and needs failover
  logic: a different design, and one that §4.3's residual rules out on this box (§8).
- **Not a reference receiver.** DEC-0236 judges the NAS stream. Zaphod's numbers judge only the
  build under test, against Zaphod's own earlier runs.
- **Not always on.** It runs for a campaign (a build under test, a soak), then stops. Between
  campaigns it costs nothing: no listener, no running VM, no attached device.

**Prod is untouched by construction.** It uses a different host, dongle and network path, and
there's no read of marvin beyond §5's one redacted section read. Reception is passive: a second
receiver doesn't transmit and can't disturb the ISS link prod hears.

## 2. Radio: its own stick, the V4L, after DEC-0236

**Zaphod can't share marvin's v3.** One process opens an RTL2832U at a time. Moving the v3, or
exporting it over USB/IP from marvin, would put a network hop and a second host in prod's receive
path, which is exactly what service uptime rules out.

**Owner's call: reuse the V4L once DEC-0236 releases it**, not a third stick. Consequences:

1. **The build waits.** BOOT's order: marvin's move (heartofgold A9); DEC-0238's swap at least 2
   days after it; the soak (24 h settle plus seven days 00:00 to 00:00); DEC-0236 from the day
   after the soak ends (24 h burn-in plus seven days). **The V4L is free about 19 days after
   marvin's move at the earliest**, later if any window slips or restarts. The issue tracks the
   real date. The Windows side isn't built earlier: usbipd and a WSL distro with nothing to serve
   are exactly the footprint §4 avoids.
2. **The image must carry librtlsdr v2.0.3.** If DEC-0238 has passed by then, that's the next
   minor image. If not, it's `v2.4.0-v4l-test` (`b599bf27…`), a fine dev-receiver image because
   it's v2.4.0 with only the library swapped.
3. **Burn a unique serial into the V4L before it moves (DEC-0235).** It's the only stick on
   Zaphod, but `RTLSDR_DEVICE=<serial>` is the pinning the next image ships, and a dev receiver
   should run the pinning path prod will run. Do it off-host at the NAS teardown, never on marvin.
4. **Antenna and siting are unmeasured.** The V4L needs a 915 MHz antenna at Zaphod; the NAS's
   antenna goes with it or Zaphod gets its own. Zaphod's distance and walls to the ISS are
   unknown, so phase D measures reception. **A dev receiver is useful for RF work at a mean
   `rxCheckPercent` ≥ 90 over 24 h. Below that it still serves install and software tests, but not
   gap or decoder work.** That's a recommendation, not a prod bar.
5. **`BIAS_TEE=0`** (the image default). There's no LNA.

## 3. Runtime: WSL2 + Docker Engine in a dedicated distro

### 3.1 Options compared

| | **WSL2 distro + Docker Engine** (chosen) | Hyper-V VM | VirtualBox + Vagrant (the May build) | Docker Desktop |
|---|---|---|---|---|
| USB to the dongle | usbipd-win `attach --wsl`, documented by Microsoft | **No generic USB passthrough** on client Hyper-V (DDA is Windows Server only), so still usbipd, now over a virtual switch the VM reaches as a network peer | Native USB filter, through boot-start kernel drivers, one an NDIS filter on every NIC | usbipd to WSL; the engine runs in Desktop's own distro |
| New hypervisor or kernel drivers on a gaming PC | None: WSL2 is already on | Enables the Hyper-V feature and its management stack | Yes. With VBS on, VirtualBox runs on top of Hyper-V anyway | None beyond WSL; adds a tray app, a background service and its own update channel |
| Isolation from Windows | Weak: one shared VM, and root in a distro can reach Windows (§4.3) | Strongest: a separate guest | Separate guest | Same as WSL, plus Desktop's integration surface |
| Matches prod | Docker Engine on Debian, as on marvin | Same, inside a full VM | Ubuntu 22.04 cloud image in May | A different engine build and networking |
| Footprint when idle | Zero: the WSL VM stops when nothing holds it | A VM to patch and size; it idles only if stopped by hand | VM plus Vagrant's toolchain | Desktop's service and VM, usually at login |
| Upkeep, as measured on Zaphod | WSL behind; `wsl --update` fixes it | n/a | **Left behind on security releases** since May | n/a |

**Decision: a dedicated WSL2 distro running Debian's Docker Engine.**

- **Hyper-V is rejected for this purpose.** It doesn't remove usbipd. It still needs it, now
  carried over a virtual network to a full guest with its own patch cycle. Its real advantage is
  isolation, and this instance doesn't need it because it holds nothing worth isolating (§5). That
  trade is recorded as a residual (§4.3), and it's the first thing §8 reopens.
- **VirtualBox and Vagrant are rejected.** They add boot-start kernel drivers on every NIC of a
  gaming PC. They duplicate WSL, which is already present. With VBS on, VirtualBox runs over
  Hyper-V anyway. And the May install shows the upkeep cost in practice: months without the
  security releases.
- **Docker Desktop is rejected.** It adds a service, a tray app and a second update channel for
  nothing the engine inside the distro doesn't already do. And its engine isn't prod's.

### 3.2 Shape

- **A new distro, named `weewx-dev`, from the Debian image.** Use `wsl --install -d Debian --name
  weewx-dev` if the updated WSL has `--name`; otherwise install it, then export and import it under
  that name. First run asks for a Linux user and password, which is an owner gesture. Check
  `/etc/debian_version` and use 13 if the image offers it, to match marvin.
- **The May `Ubuntu` distro isn't reused, and it doesn't run during a campaign.** All WSL2 distros
  share one VM and one kernel. A device attached to WSL is visible to every running distro, and
  that distro runs with default automount and interop. **Unregistering it is the clean answer, and
  that's Zaphod's call** (its backlog C19). At the least, it's stopped and never started while a
  campaign runs (phase D checks `wsl -l -v`).
- **Packages in the distro:** `usbip` (the client `usbipd attach --wsl` drives) and `hwdata`;
  Docker Engine from Debian's own packages (`docker.io`), so `unattended-upgrades` covers it.
  **Compose must be v2.24 or later**, because the repo's compose file uses `env_file: {path,
  required: false}`. Phase C checks `docker compose version`. If Debian's package is older or v1,
  use Debian's `docker-compose` v2 package if trixie carries it, else Docker's own apt repository.
  The daemon listens on its unix socket only, never TCP.
- **A udev rule for the dongle**, the same one `scripts/host-setup.sh` writes (`0bda:2838`/`2832`,
  the user's group, `MODE="0660"`), so the container's non-root uid can open the usbip-attached
  node (DEC-0147).
- **The distro user is not in the `docker` group.** Compose runs through `sudo`, which asks for
  the distro password. That way a compromised user shell isn't root in the VM by default.
- **The image comes from Docker Hub by tag and digest**, or from a local build of `dev` inside the
  distro (amd64, the same as marvin). The source comes over **public HTTPS, read-only**. Zaphod
  holds no GitHub credential for this repo; pushes happen from the Mac.
- **The repo's compose file, one change:** `user:` the non-root uid, `cap_drop: [ALL]`,
  `no-new-privileges`, `restart: unless-stopped`, **no `ports:`**, `/dev/bus/usb` mapped whole (the
  WSL VM holds only this stick), and a `mem_limit` sized above the peak measured in phase D. The
  one change is a project-local override file for that limit; the image and compose shape stay as
  shipped. An unsized cap SIGKILLs past cleanup. DEC-0236's < 200 MB bar on the NAS is a guide,
  not the number.
- **The campaign runner holds the VM up.** WSL stops a distro soon after its last `wsl.exe` client
  exits, systemd services and containers included, and it stops on Windows sign-out; the attach is
  lost with it. The start script therefore launches, hidden, `usbipd attach --wsl --busid <id>
  --auto-attach` (which also re-attaches after a USB drop) and a keep-alive `wsl -d weewx-dev
  --exec sleep infinity`. The stop script ends both. Phase D proves it: close every terminal, wait
  10 minutes, and the receiver is still writing records.
- **Recovery has limits.** DEC-0237 exits the container after three decoder exits, and `restart:
  unless-stopped` brings it back. If the stick re-enumerates over usbip, `--auto-attach` brings it
  back to the VM. But a running container can hold a stale view of `/dev/bus/usb` (DEC-0154), so a
  re-enumeration needs `compose up -d --force-recreate`, not just a restart. A dev receiver accepts
  that; the readout notes any recreate.
- **The WSL VM is capped** in `%UserProfile%\.wslconfig` (`memory=4GB`, `processors=4`). The file
  is global to all distros, so the values leave room for other uses.

## 4. Security posture

The goal: **nothing new listens on the LAN, no default or shared credential exists, and the
instance holds nothing worth stealing.**

### 4.1 usbipd-win: reachable from WSL only

usbipd-win has **no listen-address setting.** The server binds every interface, and the project
documents only its firewall rule ("allow all local subnets … You can modify this firewall rule").
The policy design rules out client selection ("currently out of scope"). Access control is
therefore **Windows Firewall, not binding devices, and not running the service**:

1. **Delete the installer's `usbipd` rule.**
2. **Add one inbound rule:** program `usbipd.exe`, TCP local port 3240, **interface = WSL's
   vEthernet adapter only**, profile set explicitly to the profile that adapter reports (often
   Public), action Allow. Read the alias with `Get-NetAdapter` at each campaign start, never typed
   from memory; WSL's NAT subnet changes per boot, which is why the scope is the interface and not
   an address. In NAT mode (WSL's default, used here) WSL reaches the server at the host's address
   on that adapter. Inbound 3240 on every other adapter falls to the default inbound block.
3. **Bind only the V4L, by busid, without `--force`.** No `usbipd policy` auto-bind rules
   (`usbipd policy list` empty). No device is shared until bound ("By default devices are not
   shared with USBIP clients"), so a reachable server has nothing to hand out.
4. **The usbipd service is set to Manual and runs only during a campaign.** The start script starts
   it; the stop script stops it. No listener between campaigns, on any interface.
5. **Re-check after every usbipd or WSL upgrade, as a command:** no rule named `usbipd`, exactly
   one 3240 rule and its interface is the WSL adapter, the service start type Manual, `usbipd
   policy list` empty. An upgrade that recreates the default rule or resets the start type
   silently reopens the LAN. v5.3.0's "improves installer to allow smoother future updates" says
   installer behavior is still moving.

**Mirrored networking isn't used.** usbipd-win supports it (since 4.0), but in mirrored mode WSL
listeners appear on the host's LAN interfaces under a second firewall (Hyper-V's). NAT mode keeps
the boundary in one place.

### 4.2 Nothing else listens

The container publishes no port. WeeWX here has no web server: reports are files. InfluxDB isn't
part of this instance. The Docker daemon is socket-only. If a later test needs a consumer (a local
InfluxDB, a dashboard proxy), it goes in the same compose project on an internal network with no
published port, and its credentials are generated for it, never defaults (§9).

### 4.3 What the distro can reach on Windows, honestly

`weewx-dev`'s `/etc/wsl.conf` turns off the conveniences:

```
[automount]
enabled = false
mountFsTab = false
[interop]
enabled = false
appendWindowsPath = false
[boot]
systemd = true
```

With these settings, no `/mnt/c` appears and Linux can't launch Windows programs **for a non-root
process**. **They aren't a boundary against root in the VM.** Root can mount a Windows drive by
hand (drvfs) and can re-register interop. And every running distro shares the VM. **The walls
that matter are:**

1. **The container**: a non-root uid, `cap_drop: ALL`, `no-new-privileges`, no Docker socket
   mounted, and only this repo's image.
2. **The distro user isn't root by default** (§3.2: no `docker` group; `sudo` asks).
3. **No other distro runs during a campaign** (§3.2).

**Residual, stated:** a container escape to root in the VM, or root in any running distro, can
reach the owner's Windows files. **It's accepted because the instance holds no secret, runs only
this repo's image, isn't always on, and has no port open.** A Hyper-V guest would remove the
residual, at §3.1's cost. Phase D tries a manual drvfs mount as the distro user without `sudo` (it
must fail) and records that root can do it, so the residual is measured, not assumed. Phase D also
proves `usbipd attach --wsl` works with interop off (it drives the distro from Windows). If it
doesn't, the plan stops and comes back rather than turning interop on.

### 4.4 Accounts and credentials

- The distro user's password is set by the owner at install. It isn't the owner's Windows or NAS
  password, and it's written into no repo.
- **No default or shared credential exists in this instance**: there's no web UI, no database
  password and no upload key (§5).

### 4.5 Updates

| Layer | How it stays current | Who |
|---|---|---|
| Windows | Zaphod's own update policy | Zaphod |
| WSL | `wsl --update` before the build, then at each campaign start | Zaphod session |
| usbipd-win | `winget upgrade dorssel.usbipd-win` at each campaign start, then §4.1 step 5 | Zaphod session |
| Debian, Docker Engine, usbip | `unattended-upgrades` (security), `apt full-upgrade` at each campaign start | inside the distro |
| Image | pinned by tag and digest; a campaign names the build it tests | this repo |

A campaign that starts on stale components is a finding, not a footnote.

### 4.6 Footprint on a gaming PC

- No new boot-start drivers and no new always-on service. usbipd is Manual, and the WSL VM stops
  when the campaign runner ends.
- Data lives in the distro's own ext4 disk (its VHDX under the user profile), not in `C:\`'s root
  folders, and never on SMB (no SQLite over a share).
- Nothing starts at sign-in, and a reboot ends a campaign: the attach and the runner don't
  survive it, but the binding does. Auto-start is out of scope until a campaign needs unattended
  restarts, and then it's its own decision.
- CPU: the Go decoder plus WeeWX is light on marvin. Phase D reads it on Zaphod during a game, so
  the owner can decide whether to stop the receiver while gaming.

## 5. Secrets and station identity

**The instance has no secrets.** That's the design: every uploader that needs a key stays off, so
there's nothing to leak, rotate or keep out of a commit.

- **The config is seeded, never copied, and edited before the first start.** A plain first start
  runs the starter's uploaders (§0's side finding). So phase C runs the seeder alone first
  (`--entrypoint` the venv Python on `/opt/seed_config.py`; it copies the starter into the empty
  mount and applies the environment, then exits). Then it sets `enable = false` on every
  `[StdRESTful]` uploader and `[[Influx]]`, removes `DavisPressure` from the services list (it's inert
  with the placeholder, but no service this instance doesn't use should load), and only then starts
  `weewxd`. Phase D greps the conf: no `enable = true` under
  `[StdRESTful]`, and no `DavisPressure` service.
- **The seed variables** (DEC-0225, `seed_config.py`): `WEEWX_DRIVER` unset (the radio),
  `WEEWX_LOCATION=weewx-dev` (the `[Station] location` text), `WEEWX_LATITUDE` and
  `WEEWX_LONGITUDE` **rounded to one decimal** (enough for the almanac, nowhere near the station),
  `WEEWX_ALTITUDE` in `N,foot` form, `RTLDAVIS_BAND=US`, `RTLDAVIS_ISS_CHANNEL` (a radio fact, not a
  secret), `RTLDAVIS_RAIN_BUCKET`. Plus `TZ` and `RTLSDR_DEVICE=<serial>` once the image honors it.
  The `.env` lives on Zaphod inside the distro, mode 0600, and is never committed. Repo placeholders
  stay `YOUR_*` (DEC-0012).
- **Prod's `weewx.conf` is never copied, read in full, or printed.** If a dev setting must match
  prod (a calibration correction, `[Rtldavis]` `cmd` flags), the Mac reads that one section through
  the redacting reader: `marvinctl --tenant weewx conf <live conf path> <SECTION>`, with no
  trailing pipe. The owner or Zaphod's session then retypes the non-secret values. The calibration
  corrections are already verbatim in `weewx.conf.example`.
- **No upload under prod's station identity, ever** (MARVIN-DEC-0228's constraint on a second
  receiver, carried over).
- **A test that needs `[DavisPressure]`** gets a **separate** WeatherLink key pair, because prod's
  shares a quota (DEC-0113). The owner types it at Zaphod's terminal into the 0600 conf. It never
  goes through a chat or an LLM prompt (CONVENTIONS §Secrets), and it's revoked at teardown.
- **Before anything lands here:** `scripts/check_secrets.sh` plus the identifier sweep, as for
  every commit. A campaign readout posted to this public repo quotes no coordinates, IPs, usernames
  or Windows paths.

## 6. Phases

Each step on Zaphod is a gesture through Zaphod's session, on the owner's yes there. Zaphod's
session records it in its own repo; heartofgold gets the estate rows ("Owed on the Mac").

| Phase | When | What | Done when |
|---|---|---|---|
| **A. Retire May's build** | now, in flight | Zaphod's session: export VM; remove VM, VirtualBox and Vagrant; usbipd removed, or its default rule deleted | no VirtualBox drivers or adapters; no LAN rule for 3240 |
| **B. Prepare** | after DEC-0236 ends | V4L off the NAS; unique serial burned (DEC-0235); antenna decided; image chosen (§2 item 2) | serial read back off-host; image digest named on the issue |
| **C. Build on Zaphod** | after B | `wsl --update`; `weewx-dev` with `wsl.conf` (§4.3); `usbip`, `hwdata`, Docker Engine, Compose ≥ 2.24, udev rule; user not in `docker`; usbipd current, Manual, §4.1 rule; `.wslconfig`; seed alone, disable uploaders, then start (§5); start and stop scripts (§3.2) | each item read back on Zaphod |
| **D. Acceptance** | after C | the checks below | all pass, results on the issue |
| **E. Use** | per campaign | start: updates, §4.1 step 5 check, start usbipd, runner (attach + keep-alive), `compose up`. Stop reverses it and stops the service | — |

**Phase D checks:**

1. From the Mac, a TCP connect to Zaphod's IPv4 **and** IPv6 addresses on 3240 fails, both with the
   receiver running and with it stopped. On Zaphod, `Get-NetFirewallRule` shows no 3240 allow on
   any adapter but WSL's.
2. Zaphod's listening and firewall collectors, before vs after: the only new rule is §4.1's; the
   default `usbipd` rule is gone; `usbipd policy list` is empty; the service is Manual.
3. In the distro: no `/mnt/c`; `cmd.exe` doesn't launch; a drvfs mount without `sudo` fails (and
   the doc records that root can do it); `ss -tlnp` shows no TCP listener; the user isn't in
   `docker`.
4. `doctor` exits 0 inside the container and names the V4L by serial; `wsl -l -v` shows only
   `weewx-dev` running.
5. The seeded conf has no enabled uploader and no `DavisPressure` (§5); `weewx.log` has no
   uploader line over the run.
6. 24 h run: archive records every 60 s; the gap check from BOOT (`grep Added`, steps over 90 s);
   mean `rxCheckPercent` reported against §2's ≥ 90 bar.
7. Close every terminal and wait 10 minutes: records keep coming (the runner holds the VM).
8. Peak container memory read, and `mem_limit` set above it. CPU read during a game.
9. Reboot test: after a Windows restart, nothing listens on 3240 and nothing starts. The start
   script brings it back.

## 7. Teardown

Order, each step on Zaphod through its session:

1. Stop script: `compose down`, end the runner, stop the usbipd service.
2. `usbipd detach --busid <id>`, then `usbipd unbind --busid <id>` (admin); `usbipd policy list`
   empty.
3. `wsl --unregister weewx-dev`. **This deletes the distro's disk and isn't reversible.** The data
   is test data with no consumer, so nothing is exported unless a campaign's readout still needs its
   logs; if so, copy those out first.
4. Remove §4.1's firewall rule. If nothing else on Zaphod uses usbipd-win, uninstall it (`winget
   uninstall dorssel.usbipd-win`).
5. Revert `.wslconfig` if this plan created it. WSL itself stays unless Zaphod decides otherwise.
6. Revoke any separate WeatherLink key issued for a test (§5).
7. Unplug the V4L and record where it went (heartofgold inventory).
8. Records: a `CHANGELOG.md` line here; Zaphod's repo and heartofgold's `CHANGELOG.md` for the box
   and the stick.

**Done when:** from the Mac, 3240 is closed on IPv4 and IPv6. Zaphod's collectors show no
`weewx-dev` distro, no 3240 rule, and no usbipd service, or a stopped one with no binding if kept.

## 8. Revisit if

- **The purpose changes to warm standby, or to anything that holds a production credential.**
  §4.3's residual isn't acceptable then. Use a Hyper-V guest, or keep the standby off the gaming PC
  entirely. MARVIN-DEC-0228 names "another always-on box" as the next candidate after the NAS.
- **usbipd-win gains a listen-address setting.** Bind it to the WSL adapter in addition to the
  firewall rule.
- **Reception at Zaphod is under the bar** (§2 item 4) and the owner wants RF work. Then move the
  antenna, or move the receiver closer to the ISS.
- **WSL changes its networking default, its idle behavior, or its USB story.** A native USB
  passthrough would remove usbipd entirely.

## 9. Not decided here

- Auto-start and unattended restart across reboots (§4.6).
- A local consumer (InfluxDB or dashboard) for end-to-end tests (§4.2).
- Whether the starter config should ship its uploaders disabled (§0's side finding). That's a
  product change for every user, so it gets its own tracker item.
- Whether the May `Ubuntu` distro, WSL itself, or SDR# stay on Zaphod. Those are Zaphod's calls.
