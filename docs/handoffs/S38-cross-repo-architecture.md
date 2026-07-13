# Handoff — weewx-rtldavis S38 → eaglehunt-weather-dashboard, hyperlocal-forecast

**Written:** 2026-07-13, weewx-rtldavis session **S38**.
**Audience:** the owner, and any project of ours that runs a container on the Synology NAS.
**Status:** **a recommendation, and a request for a decision.** No changes have been made in your
repos. Two of the three moves below are already done *here* and can be copied when you want them.

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

Ready to paste, not installed (it is your global config, and it would affect dashboard and HLF
sessions mid-flight, so it is your call, not mine):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.command' | grep -qE 'docker[[:space:]]+(-[^[:space:]]+[[:space:]]+)*logs' && ! jq -r '.tool_input.command' | grep -qE '(--tail|-n[[:space:]])' && { echo 'BLOCKED: bare `docker logs` wedged the Synology daemon and froze prod for 7h18m (DEC-0036). Use --tail N.' >&2; exit 2; }; exit 0"
          }
        ]
      }
    ]
  }
}
```

**Caveat, stated plainly:** we never established *who* ran the bare `docker logs` — it was plausibly
an agent session, possibly the owner at a terminal, and we killed the process before capturing its
parentage. A Claude hook only guards the agent. Guard the human too, with a shell function in
`.zshrc` that refuses a bare `docker logs`. Both are cheap; neither is sufficient alone.

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

**A correction to the S37 handoff, which the S37 author could not have known.** That doc's advice #2
was *"cap the Docker log driver — `--log-opt max-size=10m --log-opt max-file=3`."* Those are
**`json-file` options**, and this daemon defaults to `db`. Tested today: the daemon *accepts and
records* `max-size` on the `db` driver (`cfg=map[max-size:10m]`) — but **recorded is not enforced**,
and I did not prove the `db` driver honors it. `json-file` with caps works and `docker logs` still
functions normally against it.

So the actual choice, which is **yours and needs one decision**:

- **`json-file` + caps** — known-good, standard, bounded. Cost: Synology's Container Manager UI reads
  `log.db`, so the DSM log viewer likely stops showing those containers' logs. We read log *files*
  anyway (`weewx_monitor.py` does, and it is what worked during the outage), so this may cost nothing
  we use.
- **Stay on `db`, add `max-size`** — keeps the DSM UI. **Requires proving the driver enforces it**
  before anyone relies on it. Don't skip that proof; "it was accepted" is precisely the class of
  evidence (a green exit code) that this whole document is about.

Either way this is a three-line change to three compose files, in three repos, and **I have not made
it** — per your instruction and per the DEC-0031 lesson: *infrastructure advice across a repo boundary
must be verified in the target repo before it is given.* I verified the daemon; I did not verify what
your services do with their stdout.

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

## The decision I need from you

1. **Install the `docker logs` hook globally?** (yes / no — I will not touch `~/.claude/` without a go)
2. **`json-file` + caps, or prove `db` enforces `max-size`?** — then the three compose changes follow.
3. **Confirm: no `eaglehunt-ops` repo for now?** (my recommendation — say so and I will stop
   re-raising it, and record it as a DEC so the next session does not re-litigate it)

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
