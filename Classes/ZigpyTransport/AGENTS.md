# AGENTS.md — Zigpy & Radio Modules

## Scope

This file applies to **zigpy integration and radio backends**, including:
- zigpy core usage
- ZNP (TI)
- EZSP (Silicon Labs / bellows)
- deCONZ

Rules here **override** the root AGENTS.md when working in this area.

---

## 🚨 Zigpy Is Async-First

zigpy is **asyncio-driven**.

🚫 DO NOT:
- Call `time.sleep()`
- Perform blocking I/O
- Use `asyncio.run()`
- Create independent event loops
- Assume synchronous execution

✅ DO:
- Use existing async helpers
- Schedule tasks via existing mechanisms
- Respect zigpy lifecycle (startup, permit join, shutdown)

---

## 📡 Radio-Specific Rules

Each radio backend has:
- Different timing constraints
- Different retry semantics
- Different failure modes

🚫 DO NOT:
- Normalize behavior by force
- Assume radios behave identically
- Remove backend-specific handling for “cleanup”

✅ DO:
- Preserve backend distinctions
- Fix issues **within the backend abstraction**
- Test logic mentally against *all* radios

---

## 🧵 Threading (Extra Strict Here)

🚫 DO NOT:
- Add threads to “fix timing”
- Add watchdog loops
- Add retry loops without backoff awareness

Most radio bugs are:
➡️ timing + async ordering problems  
➡️ NOT thread starvation problems

---

## 🧪 Stability Rules (Zigbee Core)

- Network state is sacred
- Coordinator state must survive restarts
- Device re-interview must remain safe

🚫 Never introduce:
- Automatic network resets
- Forced re-pairing logic
- Silent state invalidation

---

## 🧠 Design Mindset

When touching zigpy or radios, think like:
> “This network has been running for 2 years without downtime.”

If your change would scare that user → don’t do it.

