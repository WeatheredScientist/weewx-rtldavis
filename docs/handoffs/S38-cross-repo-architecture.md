# Handoff — weewx-rtldavis S38 → eaglehunt-weather-dashboard, hyperlocal-forecast

**Written:** 2026-07-13, weewx-rtldavis session **S38**.
**Audience:** the owner, and any project of ours that runs a container on the Synology NAS.
**Status:** **decided and largely built.** The owner confirmed the recommendation live during S38, so the
enforcement layer below is **installed and tested**, not proposed. **No changes have been made in your
repos** — the two findings addressed to you (the dashboard's gate escape hatches; HLF having no gate at
all) are still yours to act on, and the NAS log-driver question is settled but needs nothing from you.

**The one thing still open is §Etiquette at the end** — the human/agent protocol *between* repos, which
is where a small 4th coordinating project probably does earn its keep.

This answers the question left open by
[`S37-to-all-projects-stdout-freeze.md`](S37-to-all-projects-stdout-freeze.md):

> *"we need some way to harmonize all of that, and i don't know if that's a master project to
> coordinate, i need some architectural advice."*

---

## The recommendation, in one line

**Don't build a master coordination repo. The gap between our repos is not a documentation gap — it
is an *enforcement* gap. Close it with hooks and tests, not with a fourth repo.**

## Why the question, as posed, optimizes the wrong axis

The three options on the table — a shared `ops/` repo, a vendored CONVENTIONS fragment, or status quo
plus handoffs — are all **strategies for distributing documentation**. Every one of them would have
failed to prevent all three incidents. Here is the uncomfortable check:

| incident | was the rule written down beforehand? | did that help? |
|---|---|---|
| The 7h18m freeze (DEC-0036) | **Yes.** "`docker logs` always with `--tail N`" was in this repo's `CLAUDE.md` *and* `CONVENTIONS.md` | **No.** It was followed for thirty-odd sessions and broken once. That once cost seven hours. |
| The blind secret gate (DEC-0039 / dash DEC-0063) | Partially — the gate *was* code | **No.** Nothing tested the code, so it was green while catching nothing, for nine sessions, in two repos independently. |
| The stock driver shipping to every user (DEC-0031) | No — the rule was implicit | **No.** A compose file quietly contradicted the Dockerfile, and no artifact checked the other. |

Every one of these already had, or could trivially have had, a prose rule. **Prose does not execute.**
A rule in a document is enforced by whoever happened to read the document and happened to remember it
at the moment they typed the command. That is not a control; it is a hope.

Notice what actually *did* resolve two of the three: someone wrote an executable check. The
duplicate-frame question stood open for four sessions and fell in one afternoon to
`ops/find_duplicate_frames.py` (DEC-0035). The secret gate was believed working for nine sessions and
its holes fell in twenty minutes to a planted-payload test (DEC-0039) — a test that, while I was
writing it *today*, caught a hole in **the very fix I was writing to close the previous hole**. The
one incident still without a mechanical guard — the freeze — is also the one still marked
**mechanism open**.

So the axis that matters is not *where does the knowledge live*, it is **does anything execute it**.
A shared repo makes knowledge easier to find. It does not make it run.

## What I recommend instead — three moves, in order of value

### Move 1 — Put the mechanical guards where the agent actually acts (`~/.claude/`)

`~/.claude/settings.json` currently has **no hooks at all** (verified this session). It is already the
one asset genuinely shared by all three projects. A `PreToolUse` hook there is global, applies to
every repo and every session, costs **zero session-start tokens** — and is the only one of the
candidate mechanisms that would actually have stopped the freeze.

Guard the two commands we have already written rules about and broken anyway:
- **`docker logs` without `--tail`** — the trigger that wedged the daemon (DEC-0036).
- **`docker stop`** — DEC-0008 says `kill`, never `stop`.

**INSTALLED AND PROVEN (S38).** Both guards ship with their own tests, because a guard nobody tested is
the thing this whole document is about:

| guard | what it blocks | test |
|---|---|---|
| `~/.claude/hooks/docker-guard.sh` (`PreToolUse`) | bare `docker logs`; `docker stop` | `test-docker-guard.sh` — **19/19**, incl. a `docker logs` hidden inside `ssh nas "..."` that beat the first draft |
| `~/.claude/hooks/eaglehunt-status.sh` (`SessionStart`) | *reports*: draft PRs, branches ahead of `dev`, uncommitted work — across **all three repos** | found a live stranded draft PR in the dashboard (#22) on its **first run** |
| `~/.zshrc` `docker()` function | same two commands, for the **human** | **6/6** |

The Claude hook was verified live: it blocked a real bare `docker logs` the moment it went in. It also
(correctly, and slightly annoyingly) blocks commands that merely *quote* the dangerous string — a
deliberate trade, since a false block costs one retype and a false allow cost seven hours. Escape hatch
in both: prefix with `command`.

**The `.zshrc` guard matters as much as the hook.** We never established *who* ran the fatal bare
`docker logs` — plausibly an agent session, possibly the owner at a terminal; the process was killed
before its parentage was captured. A Claude hook guards only the agent.

### Move 2 — Share the *test*, not the *regex*

The secret gate is the clearest case of a shared asset going wrong, and it is instructive that the
obvious fix is the wrong one.

State of play, verified today:

| repo | gate | planted-payload test |
|---|---|---|
| weewx-rtldavis (**public**) | yes — hardened S38 | **yes** (new: 13 payloads, 14 good lines) |
| eaglehunt-weather-dashboard | yes — hardened S70, diverged | yes, but only on `dev` |
| hyperlocal-forecast | **none at all** | none |

The same bug class has now been found **four separate times** (weewx S36, dash DEC-0063, dash S70,
weewx S38), and each time it had to be re-derived from scratch. The reflex is to make one canonical
`check_secrets.sh` and vendor it everywhere. **Don't.** The dashboard's own DEC-0100 §4 is right, and
it cost them something to learn: their gate runs on **raw lines**, ours used to run on **`grep -n`
output**, so their comment anchor is `^[[:space:]]*` and ours had to be `^[0-9]+:`. *A verbatim port
silently re-opens the very hole it was meant to close.* Their allow-list needs JS comment forms; ours
needs weewx config plumbing. The gates are legitimately different and must stay different.

What is **not** legitimately different is the **behavior**. So:

- **Share `test_check_secrets.sh`** — it tests behavior, not implementation. Payload lists are purely
  additive: every repo benefits from every payload any repo ever discovers, and a payload that is
  irrelevant to your language just passes trivially.
- **Share the discipline**, which is two rules and fits on a line:
  *every allow term must be ANCHORED or POSITIONED — a term that can match anywhere on the line is not
  an allow-list, it is an escape hatch, with the secret on the left and the excuse on the right; and a
  gate ships with its planted-payload test.*
- **Let each repo own its regex.**

This is the same instinct this repo already applies to its data (PRINCIPLES §1: *the contract is the
data it produces, not any single consumer*), pointed at tooling. **The test is the contract; the gate
is the implementation.**

> **Reciprocal finding for the dashboard — please act on this.** Applying your own DEC-0100 rule
> strictly, your hardened gate **still has free-floating escape hatches**. `YOUR_`, `os.environ`,
> `process.env`, `getenv`, `config_dict`, `.get(` and `argv` can all still match *anywhere* on the
> line, so a line of this shape leaks past your current gate with exit code 0:
>
> ```
> token = REAL   # falls back to process.env
> ```
>
> (Stubbed to four characters deliberately — at realistic length this line trips our own hardened
> gate, which is how we found it. The full-length payloads are in `scripts/test_check_secrets.sh`.)
>
> Our S38 fix makes every value-side allow **positioned** — the term must appear as the value of the
> key the detector actually matched — which closes the class rather than the instances. Payloads 8–12
> in our `scripts/test_check_secrets.sh` are exactly these; steal them. **And note the same trap you
> warned us about applies in reverse: do not port our regex verbatim.** Port the payloads, then fix
> your own regex until they are caught.

### Move 3 — The NAS runtime contract: the one thing that is genuinely unowned

This is the only part of the problem that a shared home would really help, and it is also the smallest.

**Verified on the box this session:**

- All four production containers — `weewx-rtldavis-v2`, `hyperlocal-forecast-api`, `eh-proxy`,
  `influxdb` — run with **`LogConfig.Config = map[]`**. No `max-size`. No `max-file`. **No caps of
  any kind, on any container.**
- The daemon's default logging driver is **`db`** — Synology's SQLite `log.db`, not `json-file`.
- **The component that wedged for seven hours is unbounded and identically unconfigured on every
  service we run, and no repo's documentation mentions it.**

**A correction to the S37 handoff, and then a correction to my own first draft of this one.** The S37
doc advised *"cap the Docker log driver — `--log-opt max-size=10m --log-opt max-file=3`."* Those are
**`json-file` options**, and this daemon defaults to `db`. My first instinct was that the `db` driver
*might* honor them, since the daemon accepts and records the option (`cfg=map[max-size:10m]`).

**It does not. Tested, then confirmed against the literature.**

Empirically: a throwaway container run with `--log-opt max-size=1m` was made to emit 200,000 lines
(~10 MB). **All 200,000 were still retrievable afterwards.** Had the cap been enforced, roughly 20,000
would have survived. The daemon records the option in `HostConfig` and the driver ignores it.

This matches the documented reality: `db` is a **proprietary Synology driver, not a Docker one**, it
has no published options, and the consensus is explicit — *"there is no way to control the max-size of
logs when the driver is `db`"*; *"the `max-size` option is not supported by this custom Synology db
driver."* So this is not undocumented. It is **unsupported**.

> **This is the third time in one session** that "the configuration was accepted" turned out not to
> mean "the configuration does anything" — after the secret gate's green exit code and the compose
> file's silent driver clobber. It is becoming the signature failure of this whole system: **an
> interface that accepts an instruction and discards it.** That is the thing to be suspicious of.

**A second, unplanned finding.** Retrieving that 200k-line log **hung for over three minutes** — and
that was a `--tail`-bounded read, not a bare one. So the pathological slowness of the `db` driver on a
large `log.db` is real, and it is reproducible. That is the DEC-0036 mechanism, and it is now
demonstrated rather than inferred. (Prod was never at risk: separate throwaway container, per-container
`log.db`, daemon healthy throughout and verified after.)

**So the choice is narrower and more honest than the S37 doc implied:**

- **`json-file` + caps** — the only way to bound a log on this box. **It costs the DSM log viewer:**
  Container Manager reads `log.db`, and switching a container to `json-file` empties its log tab in the
  UI. That cost is real and confirmed, not speculative.
- **Stay on `db`** — keep the UI, accept that the log store is **unbounded, permanently**, and rely on
  the `docker logs` guard (Move 1) to remove the trigger instead.

**These are not mutually exclusive, and that is the point.** The logging driver can be set
**per container** in compose. So the sane answer is probably: switch *only* the containers that
actually generate log volume, and leave the quiet ones on `db` with their UI intact.

Which containers those are is **the one thing I could not check** — reading `log.db` sizes needs root.
It is one command:

```
for c in $(docker ps -q); do printf '%s  ' "$(docker inspect -f '{{.Name}}' $c)"; sudo du -h "$(docker inspect -f '{{.LogPath}}' $c)"; done
```

Worth noting before anyone panics: **weewx's own stdout is now nearly silent** — v2.0.5 moved the
console handler to `WARNING`, so it has almost nothing to write. The containers with unknown and
unbounded log volume are **yours**: `hyperlocal-forecast-api`, `eh-proxy`, `influxdb`.

**I have made no change to any compose file, in any repo** — per your instruction and per the DEC-0031
lesson: *infrastructure advice across a repo boundary must be verified in the target repo before it is
given.* I verified the daemon. I did not verify what your services do with their stdout. Please do,
and note that a service which logs a line per request is the one this actually threatens.

## What I am recommending against, and why

**A shared `eaglehunt-ops` repo — not yet.** Its genuine benefit is discoverability: a *new* project
would have one place to learn the NAS rules. That benefit is real and I am declining it on purpose,
because the costs are paid every session and the benefit accrues only when there is someone to
discover it. A fourth repo means a fourth session-start read and a two-PR dance for any cross-cutting
change — in three repos that **just spent three sessions deliberately cutting session-boot cost**
(DEC-0030 here, DEC-0081 in the dashboard, DEC-0095 in HLF). Two shared artifacts — a hook config and
a payload test — do not justify that, for a solo operator.

**Build it when it has a third tenant.** Concrete triggers, any one of which flips my recommendation:
a fourth NAS service; a second operator; a third shared *executable* asset; or the moment you find
yourself pasting the same fix into three repos by hand for the second time.

**A vendored CONVENTIONS fragment — no, on its own.** Drift *is* the bug. DEC-0031 is drift
(compose vs. Dockerfile). The secret gate is drift (two copies, same bug, four discoveries). An
unchecked vendored copy is the same failure with extra steps. Vendoring is only acceptable with a
mechanical drift check — at which point you have built Move 2, and the fragment is redundant.

**Status quo plus handoffs — keep it, but only for what it is good at.** It is the right mechanism for
*lessons* — narrative, causal, one-directional. The S37 handoff is genuinely good and it did its job:
it is why you are reading this. It is the wrong mechanism for *rules*, because a rule delivered as
prose is a rule enforced by memory, and memory is what failed at 23:53 on 2026-07-12.

## Decisions — settled in S38 (owner, live)

1. **No `eaglehunt-ops` repo.** Confirmed. Recorded as **DEC-0040** so it is not re-litigated. Revisit
   on a trigger: a fourth NAS service, a second operator, a third shared *executable*, or the second
   time the same fix is hand-pasted into three repos.
2. **The guards are INSTALLED and PROVEN**, in `~/.claude/hooks/`, global across all three repos:
   - `docker-guard.sh` — `PreToolUse(Bash)`. Blocks `docker logs` without `--tail` and blocks
     `docker stop`. Ships with `test-docker-guard.sh`: **19 cases, 19 pass** — including a `docker
     logs` hidden inside `ssh nas "..."`, which slipped past the first draft. Verified live: it
     blocked a real bare `docker logs` the moment it went in.
   - `eaglehunt-status.sh` — `SessionStart`. Reports, across **all three repos**, any open or **draft**
     PR, any branch ahead of `dev`, and any uncommitted work. **On its first run it immediately found a
     live draft PR in the dashboard (#22, S71 Beaufort) that nobody knew was stranded** — the same
     failure that lost weewx S37 for a day, already recurring elsewhere.
3. **Branch protection:** `enforce_admins: true` on `main` **and** `dev`, required checks now
   `secret-scan` + `lint` + `tests`. The S36 bypass is now mechanically impossible — for everyone,
   including the owner.

## Still open — one decision, one command

**The log driver.** `db` cannot be capped (proven above). The remaining choice is *per container*, and
it depends on a fact nobody has: **which containers are actually filling a `log.db`.** Run the `sudo du`
one-liner above. Then:

- **Every `log.db` small** → keep `db` everywhere, keep your UI, change nothing. The trigger is already
  gone (Move 1). This is the likely outcome now that weewx's console is at `WARNING`.
- **One is fat** → that container is the live wedge candidate. Switch **just that one** to `json-file`
  with caps in its own compose. You lose the DSM log tab for that container only.

---

## Also, for hyperlocal-forecast specifically

You have **no secret gate at all** — no `scripts/check_secrets.sh`, and nothing in
`.github/workflows/` that scans for credentials. The dashboard and weewx both have one because both
had a scare. You have not had yours yet.

Whether that matters depends on something I deliberately did not go and check inside your repo: are
you public, or heading there? If yes, take our `check_secrets.sh` + `test_check_secrets.sh` as a
starting point — but per Move 2, **take the payload test as gospel and rewrite the regex for your own
codebase.** If you are staying private indefinitely, this is a much smaller deal and you can ignore it.

You also run `hyperlocal-forecast-api` on the same daemon, with the same uncapped `db` log driver, so
Move 3 applies to you whether or not Move 2 does.

---

# §Etiquette — the 4th-project question (added at S38 close, owner requested)

DEC-0040 answered **enforcement**: no master repo, guards in `~/.claude/`, share the test not the regex.
It did **not** answer **etiquette** — the protocol *between* repos and the agents working in them. That
is a different problem and it does want a small home. Short version:

## The one rule that matters

**A repo owns its own prod. Nobody else deploys into it — they file.**

Everything else follows from that. This session is the proof: we found a real hazard affecting
`hyperlocal-forecast-api` and `eh-proxy` (uncapped `db` log driver on a daemon that wedged), and the
right move was **not** to go fix their compose files. It was to verify what we could, state plainly what
we had not verified, and hand it over. That is DEC-0031's lesson generalized: *infrastructure advice
across a repo boundary must be verified in the target repo before it is given.*

## What a 4th project should and should not be

**Yes — a coordination repo, if it holds only these three things:**

1. **The NAS runtime contract.** One page. Who owns which container, which log driver each uses and why,
   the `docker logs --tail` rule, the monitor. Today this is nowhere, which is how it bit three repos.
2. **A shared inbox.** One issue tracker where cross-repo findings get *filed* rather than pasted into
   handoff docs that only get read at the next session start. A handoff doc is a letter; an issue is a
   queue with state.
3. **The shared executables** (`check_secrets.sh`'s payload test, the hooks) — with a CI drift check, or
   it rots into option (b) from DEC-0040.

**No — it must not become:**
- a place decisions live (they belong in the repo that owns the code — DECs stay put);
- a fourth session-start read (that is the cost DEC-0030 just bought down; the coordination repo is
  read **on demand**, not at boot);
- a dumping ground for anything that does not fit elsewhere.

**Litmus test for any file you are about to put in it:** *does this belong to more than one repo?* If
not, it goes home. That single question is what keeps it from becoming a junk drawer, and it is the
thing that kills most coordination repos.

## The agent protocol, in four lines

1. **Read-only across the boundary.** An agent in repo A may *read* repo B to verify a claim. It may not
   edit, commit, or deploy there. (This session: I read the dashboard's gate to find its escape hatches,
   and changed nothing.)
2. **File, don't fix.** A finding about repo B becomes an issue in the coordination repo (or B's tracker),
   with the evidence and an explicit statement of what was *not* verified.
3. **Prod is owned by exactly one repo, and only in an attended window.** No unattended deploys into
   someone else's service, ever — and note that this session took prod down for two restarts, both of
   which the owner explicitly approved.
4. **State your confidence.** "Measured", "cited", and "inferred" are three different things, and this
   session's worst mistake (v2.0.5's incomplete fix) came from presenting the third as the first.

## The honest cost

You will maintain a fourth repo for what is, today, roughly three pages and a hook directory. That is a
real cost and it is why DEC-0040 said *not yet* for the enforcement half. **Etiquette is the part that
actually justifies it** — because unlike the guards, etiquette cannot live in `~/.claude/` (it is about
humans and boundaries, not commands), and it cannot live in any one repo (it is precisely the thing that
is *between* them).

**Recommendation:** create it, keep it under ~5 files, and give it an issue tracker. The tracker is the
point; the docs are almost incidental. If in three months it has fewer than a dozen issues and nobody
reads the runtime contract, delete it — that is a clean, cheap experiment, and a null result is a real
answer.
