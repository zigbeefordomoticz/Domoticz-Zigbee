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
- [ ] Target branch is `stable8` for production

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

### Logging & Errors
- [ ] Logs are useful, not noisy
- [ ] Errors are actionable and non-fatal where possible

If **any box cannot be checked**, stop and reassess.

---

## 📌 Project Overview

**Project:** Zigbee4Domoticz (Domoticz-Zigbee)  
**Repo:** https://github.com/zigbeefordomoticz/Domoticz-Zigbee  
**Type:** Domoticz Python plugin  
**Purpose:** Full-featured Zigbee integration for Domoticz using `zigpy` + multiple radio backends.

- Production-grade, long-running, and stateful
- Supports multiple coordinators: ZiGate, ZNP, EZSP, deCONZ
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
- Radio libraries: `zigpy-znp`, `bellows`, `deconz`, `zigpy-zigate`
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

## 🌿 stable8 Branch Discipline

`stable8` is the **production branch**. It must be:
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


