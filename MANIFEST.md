# MANIFEST — weewx-rtldavis

**Always-load, tier 1.** What to pull on demand, and when — never read at session start. *"Working
near it" means read it.* **Classes, not instances** (rule 9): a row names a set and its convention;
instances self-describe at source. **A file in no class gets its own row.** *~1.18K tok vs a 1000
cap — carried, not shaved: coverage beats cap (OPS-DEC-0101), `docs/` rows are rule 9's reserved
exception, and the sweep matches bare filenames. See ops#158/#165. **+82 at S94** for the
`docs/GOTCHAS.md` row — the deliberate other half of BOOT.md's diet: an unindexed artifact is a lost
one, and 82 tokens here bought ~1,700 out of the always-load tier.*

## Governance & history

| Artifact | Load when |
|---|---|
| `docs/DECISIONS.md` + `docs/DECISIONS-FULL.md` — the settled-decision index; full ADR bodies | before working near a settled area. **Scan the index; never re-litigate a listed decision.** Grep the DEC id in FULL, never read it whole |
| `CHANGELOG.md` + `CHANGELOG-ARCHIVE.md` — what shipped when | writing a closeout entry; the archive is forensic |
| `docs/ROADMAP.md` — the sequenced plan, P0–P3 (DEC-0058) | choosing what's next; **updating a line a DEC just shipped (DEC-0057)**. Has its own next-check tripwire |
| `BACKLOG.md` — open ideas · durable RF findings · **standing watches** · long-term direction | RF work, anything horizon-scale, or whether a watch has fired |
| `docs/CONVENTIONS.md` — git workflow, secrets, **the exact gates and the only interpreter with the tooling** | before any gate; before any commit |
| `docs/GOTCHAS.md` — how tools and signals **mislead** (the other rows say what things *are*); §-indexed, ex-`BOOT.md` S94 | **before trusting any tool's zero/empty/green** (§1); a PR/merge or handoff write (§2); any NAS/campaign task (§3); judging a component live or shipped (§4). **New traps land here, never in `BOOT.md`** |
| `docs/PRINCIPLES.md` — durable intent · `docs/ASSESSMENT.md` — governance anchor | weighing a new decision. ASSESSMENT is a dated S23 audit, **pre-DEC-0063** |
| `docs/UPSTREAM-THREADS.md` — the four open upstream threads, and the etiquette | replying upstream, or checking whether one moved |

## Technical

| Artifact | Load when |
|---|---|
| `docs/ARCHITECTURE.md` — ISS→RTL-SDR→driver→WeeWX→sinks, mounts, the **pyc gotcha** | touching any part of that chain |
| `docs/INTERFACES.md` — **the data contract**, loop-JSON + InfluxDB schema | changing anything a consumer reads. The repo's real deliverable |
| `docs/DATA_ERRATA.md` — known-bad observations, corrections (`ERR-####`) | a suspect historical reading, or a retrospective correction (DEC-0025) |
| `CHANGES-FROM-UPSTREAM.md` — the fork's divergence (DEC-0034), one section per file. **Vendored forks:** `rtldavis.py` `influx.py` `ogoxeUploader.py` `wcloud.py`. **Ours, no upstream:** `dewpoint_service.py` `pressure_service.py` `loop_json_writer.py` `owm.py` `windy.py` | changing any of those files' behavior, or confirming whether one has an upstream to check at all; preparing an upstream PR |
| **`weewx_monitor.py` (repo ROOT, not `ops/`) — the NAS-side daemon.** It **is** the USB watchdog (`reset_dongle`, `watchdog_stall` + escalation), the uploader alerter and the reception tracker. Runs on the NAS host, not in the container | **any "what handles X at runtime?" question — read this BEFORE concluding a capability is missing** (DEC-0074) |
| **`ops/*` + `scripts/*` + the root-level NAS scripts (`usb_reset.sh`, `entrypoint.sh`) — the harness**, plus the runbooks `docs/CAMPAIGN-B-RUNBOOK.md` and `docs/INFLUXDB-MIGRATION.md` (the Foundation→marvin InfluxDB move, DEC-0141) | any ops task, the swap night, and the InfluxDB cutover window. **Each script's header is its manual — read it before using or extending one.** `ops/campaign_analyze.py` is the **only** sanctioned campaign readout (DEC-0069); `usb_reset.sh` runs as **root** under a path-scoped sudo grant (DEC-0075) |
| `README.md` · `CONTRIBUTING.md` · `SECURITY.md` · `AGENTS.md` · `LICENSE` — the public face | changing anything user-visible, handling a report, or when another agent tool is involved |

## Not in a clone, never in the load path

| Thing | Why it is not here |
|---|---|
| `ARCHIVE/` | local-only, gitignored, **never tracked** — S16 dumps with credential-shaped strings (DEC-0012). Nothing once *in* the repo is lost: `git log --follow` reaches it |
| `docs/handoffs/` | retired handoffs, kept because live docs cite them **by path**. Never lose `S38-cross-repo-architecture.md` — the family's agent protocol |
| `docs/upstream/` | drafts, gitignored — **never posted without an explicit go**. State lives in `UPSTREAM-THREADS.md` |
| Dashboard code and decisions | `eaglehunt-weather-dashboard` — **don't change the dashboard here** (DEC-0010) |
| Real infra values, coordinates, security follow-ups | the gitignored local-infra doc |
| Cross-repo coordination, shared constants, `~/.claude/` guards | `eaglehunt-ops` — **private**, never a prerequisite (DEC-0063) |
