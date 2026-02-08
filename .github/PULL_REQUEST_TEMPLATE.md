# Pull Request Template — Zigbee4Domoticz (Domoticz-Zigbee)

Thank you for contributing! All PRs **must comply with the AGENTS.md guidance**:
https://github.com/zigbeefordomoticz/Domoticz-Zigbee/blob/stable8/AGENTS.md

---

## 📝 PR Type

- [ ] Bug Fix
- [ ] Stability Improvement
- [ ] Device Support
- [ ] Documentation / Wiki Update
- [ ] Other (specify below)

---

## 🔖 Target Branch

**Production branch:** `stable8`  
- [ ] This PR targets `stable8`
- [ ] This PR targets a development/testing branch

> ⚠️ Only bug fixes or backward-compatible enhancements are allowed on `stable8`.

---

## ✅ Checklist Before Submitting

**Environment**
- [ ] Python ≥ 3.11
- [ ] Domoticz ≥ 2025.2

**Code Guidelines**
- [ ] `plugin.py` remains thin (orchestration only)
- [ ] Core logic is in `Modules/` or `Zigbee/`
- [ ] No UI changes (UI lives in separate repo)
- [ ] No breaking persistent data changes
- [ ] Async / threading patterns respected
- [ ] Logs are informative and not excessive

**Device Handling**
- [ ] Device behavior uses certified JSON (z4d-certified-devices)
- [ ] No hardcoding of devices
- [ ] Backward compatibility maintained

**Testing**
- [ ] All relevant tests pass
- [ ] Network, coordinator, and devices verified
- [ ] Changes tested on at least one real coordinator

---

## 🔧 Description of Changes

*(Provide a short, technical description of what is changed and why. Include references to any issues fixed.)*

---

## ⚠️ Known Limitations / Risks

*(List any potential backward-compatibility issues, network risks, or unstable behavior.)*

---

## 🧪 Testing Notes

- [ ] Describe steps to reproduce/test changes
- [ ] Include any special setup required (coordinator type, devices)

---

## 📌 Additional Notes for Reviewers / Agents

- All changes must be **conservative, safe, and backward-compatible**
- Changes impacting `Zigbee/` or async behavior must be **checked against all supported radios**
- Changes impacting `Modules/` must **not interfere with core Zigbee async flow**
- Human reviewers should check that **stable8 discipline** rules are followed

