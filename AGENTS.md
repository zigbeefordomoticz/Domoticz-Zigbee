# AGENTS.md — Zigbee4Domoticz (Domoticz-Zigbee)

## 🎯 Purpose of this File

This file provides **mandatory guidance for AI coding agents** working on the
**Zigbee4Domoticz / Domoticz-Zigbee** repository.

Its goals:
- Provide architecture and runtime context
- Prevent unsafe or incompatible changes
- Align agents with Domoticz + Zigbee + zigpy constraints
- Preserve long-term stability and backward compatibility

Agents **must read and follow this file before proposing changes**.

---

## ✅ Agent Quick Checklist (Read First)

Before writing or proposing any code change, verify ALL of the following:

### Environment
- [ ] Python ≥ 3.11
- [ ] Domoticz ≥ 2025.2
- [ ] Target branch is `stable9` for production

### Architecture
- [ ] `plugin.py` remains thin (orchestration only)
- [ ] Core logic lives in `Modules/` and `Zigbee/`
- [ ] No UI code added here (UI lives in separate repo)

### Zigbee / zigpy Safety
- [ ] No blocking calls (`sleep`, blocking I/O)
- [ ] No new event loops
- [ ] No uncontrolled threads
- [ ] zigpy async model respected

### Devices
- [ ] Device behavior comes from z4d-certified-devices JSON
- [ ] No hardcoded device logic unless unavoidable
- [ ] Existing certified devices are not broken

### Stability
- [ ] No breaking changes
- [ ] No persistent data format changes
- [ ] Upgrades remain safe
- [ ] Bumping `zigpy`/`bellows`/`zigpy-deconz`/`zigpy-znp`/`zigpy-blz` in `constraints.txt`? See
      CLAUDE.md → "Bumping zigpy / zigpy-znp / zigpy-deconz / zigpy-blz / bellows in `constraints.txt`"
      for the required per-library changelog + `Classes/ZigpyTransport` impact assessment — do not
      treat it as a routine dependency update

### Logging & Errors
- [ ] Logs are useful, not noisy
- [ ] Errors are actionable and non-fatal where possible

### Pull Request Scope
- [ ] This PR carries **one** change (one bug fix, or one feature) — see
      "Pull Request Discipline" below
- [ ] Every commit in it serves that one change
- [ ] Unrelated fixes noticed along the way are left for their own PR
- [ ] PR title names the change; the PR template is filled in, not left blank

If **any box cannot be checked**, stop and reassess.

---

## 📌 Project Overview

**Project:** Zigbee4Domoticz (Domoticz-Zigbee)  
**Repo:** https://github.com/zigbeefordomoticz/Domoticz-Zigbee  
**Type:** Domoticz Python plugin  
**Purpose:** Full-featured Zigbee integration for Domoticz using `zigpy` + multiple radio backends.

- Production-grade, long-running, and stateful
- Supports multiple coordinators: ZNP, EZSP, deCONZ (ZiGate: best-effort only, not actively supported)
- Handles hundreds of certified devices via JSON configs

---

## 🧠 High-Level Architecture (Actual Layout)

Domoticz (host)
├── plugin.py # entry point — Domoticz calls
├── Classes/ # core controllers & utilities
├── Modules/ # plugin helpers, parameter management
├── Zigbee/ # zigpy stack & radio adapters
├── DevicesModules/ # per-device logic based on certified JSON
├── Z4D_decoders/ # device decoder definitions
├── Tools/ # CLI, scripts, and maintenance
├── www/z4d/ # minimal web assets (UI lives in separate repo)
└── Config / Data / Logs # persistent user data, network states


---

## 🔌 Zigbee Stack & Dependencies

- `zigpy` core
- Radio libraries: `zigpy-znp`, `bellows`, `deconz` (zigpy-zigate: best-effort only)
- Async-first event model (critical for stability)

🚫 DO NOT:
- Block the event loop
- Mix synchronous calls in async paths
- Start independent event loops

✅ DO:
- Use existing async patterns
- Reuse schedulers
- Respect radio backend differences

---

## 📦 Device Handling

- Device behavior is **driven by JSON configs** from:
  https://github.com/zigbeefordomoticz/z4d-certified-devices

🚫 DO NOT:
- Hardcode devices
- Duplicate certified behavior

✅ DO:
- Extend behavior generically
- Preserve certified device support

---

## 🌐 Web UI

- Web UI is maintained separately:  
  https://github.com/zigbeefordomoticz/Domoticz-Zigbee-UI

🚫 DO NOT add UI logic here or modify assets.

---

## 📚 Documentation

- Wiki and user documentation live here:  
  https://github.com/zigbeefordomoticz/wiki

---

## 🧵 Threading & Concurrency

🚫 DO NOT:
- Add threads casually
- Use `time.sleep()` or blocking I/O
- Spawn event loops

✅ DO:
- Use existing threading / async helpers
- Keep concurrency explicit and minimal
- Preserve Domoticz responsiveness

---

## 🌿 stable9 Branch Discipline

`stable9` is the **production branch**. `stable8` (and earlier: `stable7`, `stable6`) are out of support and locked — no changes target them. It must be:
- Upgrade-safe
- Backward compatible
- Stable for critical automations

🚫 DO NOT:
- Introduce breaking changes
- Modify persistent data formats
- Refactor core behaviors for elegance

✅ DO:
- Bug fixes
- Targeted stability improvements
- Backward-compatible enhancements

---

## 🔀 Pull Request Discipline — One PR, One Change

**Rule: one PR = one feature, or one bug fix.** A PR that bundles several unrelated
changes is rejected on scope alone, before its code is reviewed.

This is not a style preference. On a production branch it is a safety control:

- **Reviewability** — a reviewer can hold one change in their head and verify it
  properly. Five unrelated hunks get a shallow pass, and a regression rides along in
  the one nobody looked at twice.
- **Revertability** — `stable9` runs people's heating, lighting and alarms. When one
  change turns out to be wrong in the field, it has to be revertable on its own,
  without taking four unrelated fixes down with it.
- **Bisectability** — a bundled PR collapses into one merge point, so
  `git bisect` lands on "this PR" instead of on the actual culprit.
- **Independent cadence** — a one-line fix should not wait on the risky change next
  to it, and a risky change should not be waved through because it shares a PR with
  an obvious fix.

### What counts as one change

One change is one *reason to change*. If the parts would be described to a user as
separate items in the release notes, they are separate PRs.

| Acceptable in one PR | Must be split |
| --- | --- |
| A fix plus its unit test | Two unrelated bug fixes |
| A fix plus the comment/docstring explaining it | A bug fix plus a behavioural default change |
| One feature across several files, if the files only change for that feature | A device fix plus a CI change |
| Several commits that are iterations on the same change | A fix plus "while I was in here" cleanups |

Several commits in one PR are fine — and normal — as long as every one of them
serves that single change. The rule is about one *subject* per PR, not one commit.

### Changes that always get their own PR

Never fold these into a PR about something else, however small the diff:

- A change to a user-visible **default** in `Classes/PluginConf.py` (especially
  privacy/telemetry settings such as `MatomoOptIn`) — a product decision the
  maintainer signs off on, with the migration impact on existing installs stated
- A dependency bump in `constraints.txt` or `requirements.txt`
- A CI / workflow change under `.github/`
- Anything touching persistent data format or the device database schema
- A change to plugin lifecycle (`onStart`, `onHeartbeat`, `onStop`) or zigpy thread
  management

### Review outcome for a bundled PR

Ask the author to split it, and say which hunks belong together. Take the parts that
are correct and self-contained as their own PRs rather than merging the bundle to
avoid round-trips. Specifically, do **not**:

- merge a bundled PR "because most of it is fine"
- cherry-pick the good hunks into the integration branch and leave the PR open
  misrepresenting what was merged

### Commented-out code

Do not leave the previous version of a line commented out next to the new one. The
replaced code is in git history. Commented-out code in a diff is a sign the change
is not finished being decided.

---

## 📝 Release Notes — PR List and Contributors

Every release section in `ReleaseNotes.md` opens with two lines, before the
`[Feature]` / `[Issue]` / `[Technical]` bullets:

```markdown
## October 2026 - stable9 9.1.007 (2026.13)

Pull requests in this release: #2051, #2052, ...

Contributors: @pipiche38 (36 commits), @shger21 (2 commits, #2079), @GMLinky (#2055, #2056, #2057 carried into #2058, #2062 into #2064)
```

**Pull requests** — every PR whose changes are in the release, in ascending order. The
release PR itself is not listed; it carries the release, it is not a change in it.
Derive the list from the history, never from the bullets below it: a bullet may cite an
issue number (`#2050`) beside its PR number, and once written down the two are
indistinguishable.

- When the release branch merged the PR branches, the merge subjects are the list:
  `git log --merges --format='%s' <prev tag>..HEAD`
- Otherwise ask GitHub which PR owns each commit — authoritative, and it gives the
  author too:
  `gh api repos/zigbeefordomoticz/Domoticz-Zigbee/commits/<sha>/pulls --jq '.[]|"#\(.number) @\(.user.login)"'`
  This answers nothing for a commit that was **cherry-picked or re-authored**: the SHA on
  the release branch was never in the PR. Those contributions have to be credited by hand
  (see below).

**Contributors** — everyone whose work is in the release, with their commit count where
they have one:

- `git shortlog -sne --no-merges <prev tag>..HEAD` gives the commit authors. Dedupe by
  **email**, not name — the same person appears under more than one `user.name`.
- Exclude bots (`claude[bot]`, dependabot). They are not contributors.
- **Credit re-authored work explicitly.** When a contributor's PR was superseded,
  rewritten or cherry-picked instead of merged, git keeps no record of them — no author,
  no `Co-Authored-By` — so they are missing from every mechanical list, and the release
  that drops them is the one that owes them the credit. Name them with the PRs they
  opened and where the work landed, as with `@GMLinky` above. Better still, add a
  `Co-Authored-By:` trailer when the commit is written; once it is merged, the release
  notes are the only place left to carry it.
- Field reporters who never opened a PR are worth crediting too, with the issue or forum
  thread they reported.

This is part of cutting the release, not an afterthought: the PR list is how a user
reading a one-line entry gets to the discussion behind it.

---

## 🚨 What NOT To Do (Summary)

❌ Do NOT:
- Rewrite large architecture
- Introduce blocking calls or uncontrolled threads
- Hardcode device logic
- Modify UI or docs here

✅ DO:
- Make small, targeted changes
- Respect existing async patterns
- Preserve long-term stability



