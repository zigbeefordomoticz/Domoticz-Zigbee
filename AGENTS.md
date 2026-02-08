# AGENTS.md — Zigbee4Domoticz (Domoticz-Zigbee)

## ✅ Agent Quick Checklist (Read First)

Before writing or proposing any code change, verify ALL of the following:

### Environment
- [ ] Python ≥ 3.11
- [ ] Domoticz ≥ 2025.2
- [ ] Target branch is correct (`stable8` for production)

### Architecture
- [ ] `plugin.py` remains thin (no business logic added)
- [ ] Core logic lives in `Modules/`
- [ ] No UI code added (UI lives in separate repo)

### Zigbee / zigpy Safety
- [ ] No blocking calls (`sleep`, blocking I/O)
- [ ] No new event loops
- [ ] No uncontrolled threads
- [ ] zigpy async model respected

### Devices
- [ ] Device behavior comes from z4d-certified-devices JSON
- [ ] No hardcoded device logic unless absolutely unavoidable
- [ ] Existing certified devices are not broken

### Stability
- [ ] No breaking changes
- [ ] No persistent data format changes
- [ ] Upgrades from previous versions remain safe

### Logging & Errors
- [ ] Logs are useful, not noisy
- [ ] Errors are actionable and non-fatal where possible

If **any box cannot be checked**, stop and reassess.


## 🎯 Purpose of this File

This file defines **mandatory guidance for AI coding agents** working on the
**Zigbee4Domoticz / Domoticz-Zigbee** project.

Its goals are to:
- Provide architectural and runtime context
- Prevent unsafe or incompatible changes
- Align agents with Domoticz, Zigbee, and zigpy constraints
- Preserve long-term stability and backward compatibility

Agents **must read and follow this file before proposing changes**.

---

## 📌 Project Overview

**Project:** Zigbee4Domoticz (Domoticz-Zigbee)  
**Repository:** https://github.com/zigbeefordomoticz/Domoticz-Zigbee  
**Type:** Domoticz Python plugin  
**Purpose:** Full-featured Zigbee integration for Domoticz using `zigpy`
and multiple radio backends.

This project is:
- Production-grade
- Long-running and stateful
- Used in real homes and critical automation setups
- Strongly focused on **stability over novelty**

---

## ⚙️ Supported Runtime Environment (Strict)

### Python

- **Python 3.11 or above**
- Runs inside **Domoticz embedded Python**
- No assumptions about:
  - virtualenv availability
  - pip version
  - internet access
  - system-wide packages

### Domoticz

- **Domoticz 2025.2 or above**
- Plugin lifecycle, threading, and logging are controlled by Domoticz

🚫 **Blocking Domoticz callbacks will freeze Domoticz**

---

## 🌿 Branching & Release Model

- **Production branch:** `stable8`
- Other branches may exist for development or testing
- Agents must assume `stable8` is:
  - Backward compatible
  - Upgrade-safe
  - User-facing

🚫 Do not introduce breaking changes on `stable8`

---

## 🧠 High-Level Architecture

Domoticz-Zigbee
└── plugin.py (entry point, Domoticz callbacks)
├── Classes/ (core logic: radios, zigpy )
├── Modules/ (core logic: clusters, devices)
├── Tools/ (utilities, scripts, helpers)
└── www/ (minimal static assets, if any)


### Key Structural Rules

- `plugin.py` is the **only entry point**
- `Modules/` contains most of the logic:
  - zigpy integration
  - radio handling
  - clusters
  - device support
  - network management
- Keep `plugin.py` thin — orchestration only

---

## 🔌 Zigbee Stack & Dependencies

This plugin uses:

- `zigpy`
- Radio libraries:
  - `zigpy-znp`
  - `bellows`
  - `deconz`
  - `zigpy-zigate`

### Important Notes

- zigpy is **asyncio-based**
- Radio behavior differs per backend
- Timing, retries, and state handling are critical

🚫 DO NOT:
- Block the event loop
- Mix blocking I/O with zigpy calls
- Start new event loops inside running ones
- Add async logic without understanding existing flow

✅ DO:
- Follow existing async patterns
- Reuse established schedulers and helpers
- Respect radio-specific abstractions

---

## 🧵 Threading & Concurrency Rules (Critical)

Concurrency in this project is **carefully controlled**.

🚫 DO NOT:
- Add new threads casually
- Use `time.sleep()`
- Use `asyncio.run()` in plugin context
- Spawn background threads without coordination

✅ DO:
- Use existing threading / async helpers
- Keep concurrency explicit and minimal
- Preserve Domoticz responsiveness

If unsure → **do not add concurrency**

---

## 🧩 Device Handling & Certification

- Devices are **not hardcoded**
- Device definitions are driven by JSON files from:

👉 https://github.com/zigbeefordomoticz/z4d-certified-devices

### Implications

🚫 DO NOT:
- Embed device-specific logic where JSON config exists
- Duplicate certified device behavior
- Break compatibility with existing device definitions

✅ DO:
- Extend or fix behavior in a generic way
- Respect the certification mechanism

---

## 🌐 Web UI (Important Separation)

- The Web UI is **NOT in this repository**
- It lives in a separate project:

👉 https://github.com/zigbeefordomoticz/Domoticz-Zigbee-UI

🚫 DO NOT:
- Add UI logic here
- Modify UI assets in this repo
- Introduce frontend dependencies

This repository focuses on **backend/plugin logic only**.

---

## 📚 Documentation & Wiki

- Documentation and user guides live here:

👉 https://github.com/zigbeefordomoticz/wiki

🚫 Do not embed long documentation in code
✅ Prefer clear comments + external documentation updates

---

## 📝 Coding Style & Practices

### Python Style

- Match existing code style
- 4 spaces indentation
- Explicit and readable logic preferred

### Error Handling

- Avoid blanket `try/except`
- Errors should be:
  - Logged
  - Actionable
  - Non-fatal when possible

### Logging

- Use Domoticz logging mechanisms
- Avoid noisy logs in hot paths
- Logs must help diagnose Zigbee issues

---

## 🧪 Stability, Compatibility & Persistence

This plugin manages:
- Persistent Zigbee networks
- Device databases
- User configurations

🚫 DO NOT:
- Change data formats lightly
- Reset networks implicitly
- Break upgrades from older versions

Backward compatibility is **mandatory** unless explicitly coordinated.

---

## 🚨 What NOT To Do (Summary)

❌ Do NOT:
- Rewrite large architectural components
- Introduce blocking calls
- Add uncontrolled threads
- Assume latest OS or hardware
- Hardcode device behavior
- Modify UI or documentation repos from here

✅ DO:
- Make small, focused changes
- Respect existing patterns
- Think like a long-term maintainer
- Prioritize reliability and predictability

---

## 🤝 Final Guidance for Agents

If a proposed change:
- Touches zigpy or radio logic
- Impacts devices or clusters
- Alters async or threading behavior
- Affects persistent data

➡️ Proceed conservatively and **explain the reasoning clearly**

**Stability > Performance**  
**Compatibility > Elegance**  
**Predictability > Cleverness**

## 🌿 stable8 Branch Discipline (Strict)

`stable8` is the **production branch**.

It is assumed to be:
- Running in real homes
- Controlling critical automations
- Upgraded in-place by users

### Rules for stable8

🚫 DO NOT:
- Introduce breaking changes
- Change persistent data formats
- Refactor for “cleanliness”
- Modify zigpy behavior broadly
- Change device semantics

✅ ALLOWED:
- Bug fixes
- Targeted stability improvements
- Radio-specific fixes
- Backward-compatible enhancements

### Change Evaluation Test

Before modifying `stable8`, ask:

1. Will existing installations behave the same?
2. Will upgrades be safe without user action?
3. Will Zigbee networks remain untouched?
4. Would I deploy this to my own home?

If **any answer is “no”**, the change does not belong in `stable8`.

---

stable8 favors:
**Predictability > Innovation**  
**Safety > Performance**  
**Continuity > Refactoring**

