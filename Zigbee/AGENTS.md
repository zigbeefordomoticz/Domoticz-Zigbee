# AGENTS.md — Zigbee / Radio Modules

## Scope

Applies to **zigpy integration and radio backends**, including:
- ZNP (TI), EZSP (Silicon Labs / bellows)
- deCONZ
- ZiGate

Rules **override root AGENTS.md** for this folder.

---

## 🚨 Async & zigpy Rules

- zigpy is **asyncio-driven**
- Preserve event loop integrity

🚫 DO NOT:
- Call `time.sleep()`
- Block event loops
- Start independent asyncio loops
- Mix sync and async code

✅ DO:
- Use existing async helpers
- Schedule tasks via plugin mechanisms
- Respect radio lifecycle

---

## 📡 Radio Backends

- Timing differs per backend
- Retry and error handling are backend-specific

🚫 DO NOT:
- Normalize radio behavior forcibly
- Remove backend-specific cleanup
- Assume all radios behave identically

✅ DO:
- Preserve backend distinctions
- Fix issues inside abstraction
- Test changes against all supported radios

---

## 🧵 Threading

🚫 DO NOT:
- Add threads for timing fixes
- Add uncontrolled retry loops

✅ DO:
- Use plugin helpers
- Maintain Domoticz responsiveness

---

## 🧪 Stability

- Network and coordinator states are sacred
- Device re-interview must remain safe

🚫 NEVER:
- Reset networks automatically
- Force re-pairing silently

