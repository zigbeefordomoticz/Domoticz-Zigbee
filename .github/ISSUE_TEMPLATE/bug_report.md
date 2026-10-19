---
name: Bug report
about: Report an identified bug of the plugin (not a device request, not a question)
title: ''
labels: ''
assignees: ''

---

<!--
Issues here are for identified bugs of the plugin only.

* A new device, or a device that is not optimized yet: open an issue on
  https://github.com/zigbeefordomoticz/z4d-certified-devices/issues
* A question or a setup problem: ask on the forums
  English: https://www.domoticz.com/forum/viewforum.php?f=68
  French:  https://easydomoticz.com/forum/viewforum.php?f=28

How to collect useful logs:
https://zigbeefordomoticz.github.io/wiki/en-eng/Troubleshooting_Reporting-a-problem.html
-->

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Environment**
 - Plugin version and branch (the `Z4D starts with ...` log line):
 - Coordinator model and firmware (the `... communication confirmed` log line):
 - Domoticz version:
 - Python version:
 - OS:
 - Browser and version (for a WebUI problem):

**Logs**
Attach the plugin log file excerpt (`Logs/PluginZigbee_<hardware id>.log`) around the problem, with the relevant debug modules enabled in WebUI > Tools > Debug. Please attach it as a text file, not a screenshot.

If the plugin recorded errors, attach the export of WebUI > Tools > Error(s) > Log Error History (json).

For a problem linked to a device, attach the export of WebUI > Tools > Tools > Plugin Raw Devices.

**Additional context**
Add any other context or screenshots about the problem here.
