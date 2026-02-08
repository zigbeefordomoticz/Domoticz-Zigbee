# AGENTS.md — Modules Helpers

## Scope

Applies to **Modules/** folder helpers:
- Parameter management
- Polling & scheduler helpers
- Device creation flows
- Misc plugin utilities

---

## Rules

- Keep core logic in `Modules/` clean and reusable
- Do not embed device-specific logic here
- Respect async and Domoticz callback rules

🚫 DO NOT:
- Block Domoticz callbacks
- Spawn threads without coordination
- Modify zigpy stack here (use Zigbee/ folder)

✅ DO:
- Implement helpers that support multiple devices
- Respect concurrency guidelines
- Keep code testable

