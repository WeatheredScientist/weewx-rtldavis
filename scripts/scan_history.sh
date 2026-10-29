#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# scan_history.sh — run the WHOLE current secret gate over every blob git history
# reaches (S154, ops#404). check_secrets.sh only ever sees the staged diff or the
# tracked tree; a detector change says nothing about what the old blobs hold. S153's
# first full-history pass found a credential public for months that two earlier
# history searches had called absent, because each searched only the spellings it had
# just fixed (DEC-0076, DEC-0084).
#
#   bash scripts/scan_history.sh            compare against scripts/history_scan_known.txt
#   bash scripts/scan_history.sh --print    print the aggregated findings (to rebuild the list)
#
# Run it after ANY change to check_secrets.sh (docs/CONVENTIONS.md, Secrets).
#
# OUTPUT RULE: only the gate's own `SECRET-SCAN:` header lines are ever printed, which
# carry a kind and a path and never a matched line. The matched text is dropped here, at
# the source, because whatever a tool prints lands in the session transcript (S153 printed
# a live value that way). Do not add a line-printing mode.
#
# POSITIVE CONTROL: history is immutable, so the known findings never go away. The known
# list is the control. A run that no longer reports a known finding exits 3, because a
# gate that stopped catching what it used to catch is the failure this exists to expose.
# A finding that is not in the list exits 1.
#
# Exit: 0 history matches the known list · 1 new finding(s) · 2 cannot run (no identifier
# list, bad repo) · 3 a known finding is no longer reported (control dead).
set -u
mode="${1:-compare}"
case "$mode" in compare|--print) ;; *) echo "usage: $0 [--print]" >&2; exit 2 ;; esac

repo="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "scan_history: not in a git repo" >&2; exit 2; }
gate="$repo/scripts/check_secrets.sh"
known="${HISTORY_SCAN_KNOWN:-$repo/scripts/history_scan_known.txt}"
[ -f "$gate" ] || { echo "scan_history: $gate missing" >&2; exit 2; }

# The identifier check must run. A git worktree does not carry the gitignored list, and
# a silently skipped check would turn every known identifier hit into a "control dead".
export CHECK_SECRETS_REQUIRE_IDENTIFIERS=1

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
raw="$work/raw"; : > "$raw"
tree="$work/tree"; mkdir "$tree"

# Unique (blob, path) pairs. The gate keys its skips on the path, so the path is kept.
git -C "$repo" rev-list --all --objects \
  | git -C "$repo" cat-file --batch-check='%(objecttype) %(objectname) %(rest)' \
  | awk '$1=="blob" && NF>=3 { sha=$2; $1=""; $2=""; sub(/^  /,""); print sha "\t" $0 }' \
  | sort -u > "$work/pairs"

total=$(wc -l < "$work/pairs" | tr -d ' ')
[ "$total" -gt 0 ] || { echo "scan_history: no blobs enumerated" >&2; exit 2; }

while IFS=$'\t' read -r sha path; do
  [ -n "$path" ] || continue
  mkdir -p "$tree/$(dirname "$path")"
  git -C "$repo" cat-file blob "$sha" > "$tree/$path"
  out="$(cd "$tree" && bash "$gate" "$path" 2>&1)"
  rc=$?
  if [ "$rc" -eq 2 ]; then
    echo "scan_history: the gate cannot run (exit 2); stopping" >&2
    printf '%s\n' "$out" | grep -E '^SECRET-SCAN: ' >&2
    exit 2
  fi
  printf '%s\n' "$out" | grep -E '^SECRET-SCAN: [a-z]' | grep -vE '^SECRET-SCAN: note:' >> "$raw"
  rm -rf "${tree:?}"/*
done < "$work/pairs"

# Aggregate to "<count><TAB><header>", sorted.
sort "$raw" | uniq -c | awk '{ n=$1; $1=""; sub(/^ /,""); print n "\t" $0 }' | sort -t$'\t' -k2 > "$work/found"

echo "scan_history: $total blobs scanned" >&2
if [ "$mode" = "--print" ]; then cat "$work/found"; exit 0; fi

[ -f "$known" ] || { echo "scan_history: $known missing; run with --print to build it" >&2; exit 2; }
grep -vE '^[[:space:]]*(#|$)' "$known" | sort -t$'\t' -k2 > "$work/known"

new=$(comm -13 "$work/known" "$work/found")
gone=$(comm -23 "$work/known" "$work/found")
if [ -n "$gone" ]; then
  echo "scan_history: CONTROL DEAD: a known finding is no longer reported (or its count changed):" >&2
  printf '%s\n' "$gone" >&2
  rc=3
fi
if [ -n "$new" ]; then
  echo "scan_history: NEW finding(s) in history, not in scripts/history_scan_known.txt:"
  printf '%s\n' "$new"
  exit 1
fi
[ "${rc:-0}" -eq 0 ] && echo "scan_history: history matches the known list ($(wc -l < "$work/found" | tr -d ' ') finding lines)"
exit "${rc:-0}"
