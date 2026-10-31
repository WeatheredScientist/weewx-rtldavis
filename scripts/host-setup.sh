#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Prepare a Debian, Ubuntu or Raspberry Pi OS computer to run weewx-rtldavis (DEC-0225, proposal C).
#
#   bash host-setup.sh [--dry-run] [--user NAME] [--dir DIR] [--from-dir CHECKOUT] [--skip-dongle-check]
#
# Download it, read it, then run it. Never pipe it into a shell. Safe to run twice: every step
# checks before it writes, and an existing .env or docker-compose.yml is left alone.
#
# What it does, in order:
#   1. checks that a Realtek RTL-SDR dongle (0bda:2838 or 0bda:2832) is plugged in
#   2. stops the kernel's TV drivers from claiming the dongle, now and after a reboot
#   3. writes a udev rule so NAME's primary group can open the dongle without root
#   4. creates DIR/weewx-data and DIR/logs
#   5. offers to install Docker (it asks first) and adds NAME to the docker group
#   6. puts docker-compose.yml and .env in DIR, with your time zone, uid and gid filled in
#
# --dry-run     print what would happen, change nothing
# --user NAME   the user that will run the container (default: the user who invoked sudo, or you)
# --dir DIR     where the stack lives (default: ./weewx)
# --from-dir D  take docker-compose.yml and .env.example from a repository checkout instead of
#               downloading them from the release
# --skip-dongle-check   carry on without a dongle (for WEEWX_DRIVER=simulator)
set -euo pipefail

RELEASE="v2.2.0"
BASE_URL="https://github.com/WeatheredScientist/weewx-rtldavis/releases/download/${RELEASE}"
BLACKLIST=/etc/modprobe.d/blacklist-rtl-sdr.conf
UDEV_RULE=/etc/udev/rules.d/60-rtl-sdr.rules

dry=0; target_user=""; dir="./weewx"; from_dir=""; skip_dongle=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) dry=1 ;;
    --user) target_user="${2:?--user needs a name}"; shift ;;
    --dir) dir="${2:?--dir needs a path}"; shift ;;
    --from-dir) from_dir="${2:?--from-dir needs a path}"; shift ;;
    --skip-dongle-check) skip_dongle=1 ;;
    -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
die() { printf 'host-setup: %s\n' "$*" >&2; exit 1; }

# Run a command, or only show it under --dry-run.
run() {
  if [ "$dry" = 1 ]; then printf '  would run: %s\n' "$*"; else "$@"; fi
}
# Same, with root rights when we do not have them already.
as_root() {
  if [ "$(id -u)" = 0 ]; then run "$@"; else run sudo "$@"; fi
}
# Write stdin to a root-owned file.
write_root() {
  local path="$1" content; content="$(cat)"
  if [ "$dry" = 1 ]; then printf '  would write %s:\n%s\n' "$path" "    ${content//$'\n'/$'\n'    }"; return; fi
  if [ "$(id -u)" = 0 ]; then printf '%s\n' "$content" > "$path"; else printf '%s\n' "$content" | sudo tee "$path" >/dev/null; fi
}
confirm() {
  local answer
  [ -t 0 ] || return 1
  read -r -p "$1 [y/N] " answer
  [ "$answer" = y ] || [ "$answer" = Y ]
}

# ---- who and where ---------------------------------------------------------
[ "$(uname -s)" = Linux ] || die "this runs on Linux only. Windows and macOS pass USB through a virtual machine, which breaks the radio's timing."
# shellcheck disable=SC1091
. /etc/os-release 2>/dev/null || die "no /etc/os-release, so I cannot tell which Linux this is"
case " ${ID:-} ${ID_LIKE:-} " in
  *" debian "*|*" ubuntu "*|*" raspbian "*) ;;
  *) die "${PRETTY_NAME:-this system} is not Debian, Ubuntu or Raspberry Pi OS. Do the manual steps in docs/DEPLOY.md, or on Debian-like systems: sudo apt install rtl-sdr && sudo usermod -aG plugdev USER" ;;
esac

[ -n "$target_user" ] || target_user="${SUDO_USER:-$(id -un)}"
id "$target_user" >/dev/null 2>&1 || die "no such user: $target_user"
uid="$(id -u "$target_user")"; gid="$(id -g "$target_user")"; group="$(id -gn "$target_user")"
[ "$uid" != 0 ] || die "refusing to set the container up as root. Pass --user with a normal account."

say "Setting up for user $target_user (uid $uid, group $group), files in $dir"
[ "$dry" = 1 ] && say "Dry run: nothing will be changed."

# ---- 1. the dongle ----------------------------------------------------------
if [ "$skip_dongle" = 0 ]; then
  command -v lsusb >/dev/null 2>&1 || die "lsusb is missing. Install it with: sudo apt install usbutils"
  if lsusb | grep -qiE '0bda:(2838|2832)'; then
    say "ok: found a Realtek RTL-SDR dongle"
  else
    die "no RTL-SDR dongle (0bda:2838 or 0bda:2832) in lsusb. Plug it in and run this again. For a try without hardware, add --skip-dongle-check and set WEEWX_DRIVER=simulator in .env."
  fi
fi

# ---- 2. keep the kernel's TV drivers off the dongle --------------------------
mods="dvb_usb_rtl28xxu rtl2832 rtl2830 rtl2832_sdr"
bl="$(for m in $mods; do printf 'blacklist %s\ninstall %s /bin/false\n' "$m" "$m"; done)"
if [ -f "$BLACKLIST" ] && [ "$(cat "$BLACKLIST")" = "$bl" ]; then
  say "ok: $BLACKLIST is in place"
else
  say "writing $BLACKLIST"
  write_root "$BLACKLIST" <<<"$bl"
  if command -v update-initramfs >/dev/null 2>&1; then as_root update-initramfs -u; fi
fi
for m in $mods; do
  if awk '{print $1}' /proc/modules 2>/dev/null | grep -qx "$m"; then as_root modprobe -r "$m" || say "note: could not unload $m now; reboot to finish"; fi
done

# ---- 3. let the user open the dongle -----------------------------------------
rule="$(for p in 2838 2832; do printf 'SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="%s", GROUP="%s", MODE="0660"\n' "$p" "$group"; done)"
if [ -f "$UDEV_RULE" ] && [ "$(cat "$UDEV_RULE")" = "$rule" ]; then
  say "ok: $UDEV_RULE is in place"
else
  say "writing $UDEV_RULE"
  write_root "$UDEV_RULE" <<<"$rule"
  as_root udevadm control --reload-rules
  as_root udevadm trigger
  say "Unplug the dongle and plug it back in so the new rule applies."
fi

# ---- 4. folders --------------------------------------------------------------
for d in "$dir/weewx-data" "$dir/logs"; do
  if [ -d "$d" ]; then say "ok: $d exists"; else say "creating $d"; run mkdir -p "$d"; fi
done
if [ "$(id -u)" = 0 ] && [ "$dry" = 0 ]; then chown -R "$uid:$gid" "$dir"; fi

# ---- 5. Docker ---------------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
  say "ok: docker is installed"
else
  say "Docker is not installed."
  if confirm "Install it with Docker's own script from get.docker.com?"; then
    tmp="$(mktemp)"
    run curl --fail --silent --show-error --location https://get.docker.com --output "$tmp"
    say "Downloaded Docker's installer to $tmp. Read it if you like; running it now."
    as_root sh "$tmp"
    rm -f "$tmp"
  else
    say "Skipped. Install Docker yourself (https://docs.docker.com/engine/install/), then run this again."
  fi
fi
if getent group docker >/dev/null 2>&1 && ! id -nG "$target_user" | tr ' ' '\n' | grep -qx docker; then
  say "adding $target_user to the docker group (log out and back in for it to apply)"
  as_root usermod -aG docker "$target_user"
fi

# ---- 6. compose file and .env ------------------------------------------------
fetch() {  # fetch NAME DEST [ASSET]; GitHub renames a dotfile release asset, so .env.example ships as env.example
  if [ -n "$from_dir" ]; then run cp "$from_dir/$1" "$2"
  else run curl --fail --silent --show-error --location "$BASE_URL/${3:-$1}" --output "$2"; fi
}
if [ -f "$dir/docker-compose.yml" ]; then
  say "ok: $dir/docker-compose.yml exists, leaving it alone"
else
  say "writing $dir/docker-compose.yml"
  fetch docker-compose.yml "$dir/docker-compose.yml"
fi
if [ -f "$dir/.env" ]; then
  say "ok: $dir/.env exists, leaving it alone"
else
  say "writing $dir/.env"
  tz="$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo UTC)"
  tmpl="$(mktemp)"
  fetch .env.example "$tmpl" env.example
  if [ "$dry" = 1 ]; then
    say "  would fill in TZ=$tz PUID=$uid PGID=$gid"
  else
    sed -e "s|^TZ=.*|TZ=$tz|" -e "s|^PUID=.*|PUID=$uid|" -e "s|^PGID=.*|PGID=$gid|" "$tmpl" > "$dir/.env"
    chmod 0600 "$dir/.env"
    [ "$(id -u)" = 0 ] && chown "$uid:$gid" "$dir/.env" "$dir/docker-compose.yml"
  fi
  rm -f "$tmpl"
fi

say ""
say "Done. Next: edit $dir/.env (location, latitude, longitude, altitude), then:"
say "  cd $dir && docker compose up -d"
