# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S46] — 2026-07-24 — Humidity-spike watch checked directly (still unfired); OPS-DEC-0019 rollout closed cross-repo; dev housekeeping

Ran the DEC-0044 humidity-spike check directly against the live NAS logs rather than deferring it:
fetched every `log_humidity_raw` packet captured since the capture went live (2026-07-13 15:27, S41)
through the current log — 11 days, 8,852 raw packets, ~3x the largest prior sample (S43's 2,056).
Decoded per the driver's own formula (`rtldavis.py:1543-1550`) and searched for a single-step raw jump
of 16-37 %RH (the DEC-0044 signature). **Zero matches.** Largest swing: -9.86 %/min (2026-07-17
13:16→13:17, 60.5%→51.3%) — larger than S43/S44's reported 7.5 %/min purely from sample size, still
ordinary midday humidity movement, clustered in the predicted 11:00-16:00 window. Watch remains open,
unfired.

Closed [eaglehunt-ops#37](https://github.com/WeatheredScientist/eaglehunt-ops/issues/37) (OPS-DEC-0019
env-twin rollout): confirmed all three Eagle Hunt repos had merged their portion (weewx-rtldavis#59 in
S45, hyperlocal-forecast#135, eaglehunt-weather-dashboard#102+#112) — commented and closed.

Housekeeping: local `dev` was 2 commits behind `origin/dev` (PR #61, `ops-53-settings-consolidation`)
— pulled forward; removed the resulting stale merged worktree
(`.claude/worktrees/ops-53-settings-consolidation`) and its local branch. Checked eaglehunt-ops' open
issues and both sibling repos for anything owed here: nothing tagged `repo:weewx`, nothing outstanding.

No code changed, no release, no PR from this repo.

---

## [S45] — 2026-07-20 — PR #59 merged: OPS-DEC-0019 env-twin permission rules (cross-repo)

`.claude/settings.json` gained two ask-rule entries: `Bash(env * git merge * main)` and
`Bash(env * git merge * dev)`. Env-wrapping (`env -u GH_TOKEN git merge …`) defeats ask-rule
pattern matching, since `env` isn't stripped before the match runs — the existing `git merge * main`/
`git merge * dev` rules never fired for an env-wrapped call, which fell through to the auto-mode
classifier instead of resolving by rule. `git push` already carried its env-wrapped twin; this fills
in the same gap for the two protected-branch merge rules. Mechanical, no code touched, part of the
cross-repo OPS-DEC-0019 rollout (`eaglehunt-ops#37`) landing the same fix in all three Eagle Hunt
repos. CI green (lint/secret-scan/tests). The branch and commit were already staged when this session
started; this session's contribution was flipping draft PR #59 to ready and merging it to `dev`.

Humidity-spike watch and the DEC-0049 rainRate prediction: unchanged, still unfired (see [S44]).

---

## [S44] — 2026-07-19 — Soak-check phantom-rain false positive fixed; shared closeout skeleton adopted (DEC-0052)

`ops/soak_check.sh` on the still-running v2.0.8 (up 98h) flagged 49 archive rows as a possible
DEC-0049-predicted phantom-rainRate event. Cross-checked against the full 2026-07-18 archive: it
wasn't one — 3 real bucket tips that day, a falling barometer (29.93→29.78 in) and rising gusts (to
8 mph) confirm a real storm, and every flagged row is the ISS's own rain-rate message decaying after
a real tip (one decay tail ran 38 minutes, past the light-rain formula's nominal ~1022s ceiling).
**Fixed:** the detector now excludes any row with a real tip in the preceding hour. Re-verified
live: 49 → 0 false positives, all other soak checks unchanged. The DEC-0049 prediction itself (a real
condensation event, tip counter not advancing) remains unfired.

**DEC-0052:** adopted eaglehunt-ops' locked closeout skeleton (OPS-DEC-0016), adapted. `CLAUDE.md`'s
closeout ritual — previously split across two paragraphs ("Session ritual — End" and a separate
"Docs-diet ritual at close") — is now one 6-step numbered list; the docs-diet ritual and this repo's
stricter local commit/push rule are kept as addenda, per the template's own pattern. The only
genuinely new content is step 5, a model-tier restore check — the third repo (after
hyperlocal-forecast, coffeeradar) to independently land on that same assessment. Closes
weewx-rtldavis#56; outcome reported to eaglehunt-ops#22.

Both changes landed via PR #57 (`s44-ops-closeout-and-rain-fix` → `dev`), checks green
(lint/secret-scan/tests).

Humidity-spike watch: still negative, 894 samples this container lifetime, largest jump ~7.5 %RH/min
— same magnitude as S43, no qualifying spike.
