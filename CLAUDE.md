# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Zigbee for Domoticz** is a production-grade Python plugin that integrates Zigbee devices into the Domoticz home automation system using the `zigpy` library and multiple Zigbee radio backends (ZNP, EZSP/Bellows, deCONZ, BLZ).

- **Type**: Domoticz Python Plugin (long-running, async-first, stateful)
- **Python**: 3.11+ required
- **Domoticz**: 2025.1+ required
- **Key Dependencies**: zigpy, zigpy-znp, bellows, zigpy-deconz, z4d-certified-devices
- **ZiGate**: best-effort only — not actively supported; do not write ZiGate-specific code

## Architecture Overview

The plugin uses a modular, layered architecture:

```
plugin.py (entry point, ~2000 lines)
├── Classes/
│   ├── PluginConf.py          # Configuration management
│   ├── WebServer/             # REST API endpoints for WebUI
│   ├── ZigpyTransport/        # Async zigpy thread & radio backends
│   ├── ZigateTransport/       # Legacy Zigate support (deprecated)
│   ├── OTA.py, IAS.py         # Feature implementations
│   └── ...                    # Admin widgets, database, network topology
├── Modules/
│   ├── heartbeat.py           # Main periodic task loop
│   ├── database.py            # Device list load/save, persistence
│   ├── command.py             # Domoticz onCommand handler
│   ├── input.py               # Domoticz message reception
│   ├── domoCreate.py          # Widget creation
│   ├── domoMaj.py             # Widget updates
│   ├── readAttributes.py      # Attribute reading requests
│   ├── tools.py               # Utility helpers
│   └── ~90 other modules      # Device-specific logic, clusters, features
├── Zigbee/
│   ├── zclCommands.py         # ZCL cluster command definitions
│   ├── zclDecoders.py         # ZCL message decoding
│   ├── zdpCommands.py         # ZDP (device discovery) commands
│   └── helperDefautResponse.py
├── Z4D_decoders/              # Device-specific decoders (Zigpy responses)
├── DevicesModules/            # Custom device implementations (Tuya, Ikea, etc.)
├── Conf/
│   ├── ZclDefinitions/        # ZCL cluster attribute definitions
│   └── Local-Devices/         # User device configurations
├── OTAFirmware/               # Over-The-Air firmware for devices
├── Tools/                     # CLI scripts and maintenance utilities
└── www/z4d/                   # Minimal web assets (full UI lives in Domoticz-Zigbee-UI repo)
└── tests/                     # Unit tests files
```

### Key Design Patterns

1. **Async-First Event Loop**: All Zigbee communication runs in a dedicated async thread (`ZigpyTransport`). Non-blocking patterns are critical.
2. **Queue-Based IPC**: Messages pass between Domoticz (synchronous) and zigpy thread (asynchronous) via queues.
3. **Device Abstraction**: Device behavior is driven by JSON configs from `z4d-certified-devices` repository, not hardcoded logic.
4. **Modular Command Handlers**: Each Domoticz command is routed through `Modules/command.py` to device-specific handlers.
5. **Stateful Device Database**: Plugin maintains persistent `ListOfDevices` dict (serialized to JSON) and live `IEEE2NWK` mappings.

## Critical Architecture Constraints

### From AGENTS.md (Must Follow)

**Stability Requirements:**
- No breaking changes to stable9 branch
- Preserve long-term backward compatibility
- No persistent data format changes without migration
- Upgrades must remain safe

**Zigbee/zigpy Safety:**
- Never block the event loop (no `time.sleep()`, blocking I/O)
- No independent event loops or uncontrolled threads
- Respect async patterns; reuse existing schedulers
- Radio backend differences must be handled generically

**Device Handling:**
- Device behavior comes from z4d-certified-devices JSON configs
- Avoid hardcoding device-specific logic unless unavoidable
- Never break existing certified device support

**Architecture Rules:**
- `plugin.py` remains orchestration-only (thin entry point)
- Core logic lives in `Modules/` and `Zigbee/`
- No UI code here (UI lives in separate Domoticz-Zigbee-UI repository)
- No new independent threads without explicit approval

**Environment:**
- Python >= 3.11
- Domoticz >= 2025.2 (2025.1 minimum)
- Target stable9 branch for production changes

## Development Workflow

### Initial Setup

```bash
# Clone and install dependencies
git clone https://github.com/zigbeefordomoticz/Domoticz-Zigbee.git
cd Domoticz-Zigbee
pip install -r requirements.txt
pip install bandit black codespell flake8 isort mypy pytest pyupgrade
```

### Code Quality & Testing

**Run All Checks (as CI does):**
```bash
# Security scan
bandit -r .

# Linting (flake8 syntax errors only, per CI config)
flake8 . --builtins=Devices,Parameters,Connection --count --select=E9,F63,F7,F82 --show-source --statistics

# Unit tests
pytest .

# Code upgrade (Python 3.6+ syntax)
pyupgrade --py36-plus **/*.py
```

**Linting Configuration:**
- Max line length: 160 (black)
- Flake8 ignores: E501, E302, E201, E202, E231, E503, etc. (see `.flake8`)
- Builtins allowed: `Devices`, `Parameters`, `Connection` (Domoticz framework globals)
- Per-file ignores: `DevicesModules/custom_GammaTroniques.py` (E221, E241 alignment)

**Run a Single Test:**
```bash
pytest tests/test_zigbee_default_response.py::TestMustSendDefaultResponse::test_disable_default_response_bit -v
```

### Testing

Current test coverage is minimal (1 test file, 14 test cases). The test file demonstrates unit testing for the Zigbee default response logic:

```bash
# See tests/test_zigbee_default_response.py for pattern
# Tests use unittest.TestCase and import from Zigbee.helperDefautResponse
```

### CI/CD Pipeline

**GitHub Actions** (`.github/workflows/Python-CI-Security-Scan.yml`):
- Python 3.11, 3.12 matrix
- Bandit security scan
- Flake8 linting (E9, F63, F7, F82 only)
- Pytest execution
- CodeQL analysis (weekly + on-demand)

**No Black/isort enforcement** (commented out in CI, but tools are available).

## Module Reference

### Entry Point: plugin.py

The `BasePlugin` class implements Domoticz plugin lifecycle:

```python
def onStart(self)       # Initialization, transport startup
def onHeartbeat(self)   # Periodic tasks (attribute reading, device polling, pairing)
def onCommand(self, Unit, Command, Level, Color)  # Widget commands
def onMessage(self, Connection, Data)  # Zigbee message reception
def onDisconnect(self, Connection)     # Cleanup
def onStop(self)        # Shutdown
```

**Key Instance Attributes:**
- `self.ListOfDevices`: Main device database (dict of dicts)
- `self.IEEE2NWK`: IEEE address to network address mapping
- `self.pluginconf`: Configuration settings (PluginConf instance)
- `self.transport`: ZigpyTransport or ZigateTransport instance
- `self.ZigateComm`: Communication queue handler
- `self.writer_queue`, `self.forwarder_queue`: Inter-thread queues

### Modules/ - Device Logic & Helpers

**Core:**
- `heartbeat.py`: Main periodic loop; calls attribute reading, polling, device maintenance
- `database.py`: Load/save device list, migrations, device validation
- `command.py`: Routes Domoticz commands to device-specific handlers
- `input.py`: Processes incoming Zigbee messages
- `domoCreate.py`, `domoMaj.py`: Widget creation and updates

**Features:**
- `readAttributes.py`: Request attribute reads (extensive, ~90KB)
- `readClusters.py`: Cluster discovery (~98KB)
- `tools.py`: General utilities (~76KB)

**Device-Specific:**
- `tuya.py`: Tuya device implementations (~86KB)
- `schneider_wiser.py`: Schneider Wiser thermostats (~97KB)
- `lumi.py`: Lumi/Aqara devices (~49KB)
- `ikeaTradfri.py`: IKEA Tradfri devices (~22KB)
- `danfoss.py`, `philips.py`, `legrand_netatmo.py`, etc.

**Cluster Logic:**
- `ConfigureReporting.py`: Report configuration
- `bindings.py`: Binding management
- `zclClusterHelpers.py`: ZCL helper functions
- `basicInputs.py`, `basicOutputs.py`: On/Off, levels, colors

### Classes/ - Core Controllers

- `PluginConf.py`: Extensible configuration schema (categories, per-setting metadata)
- `ZigpyTransport/`: Async event loop, radio backend initialization, command dispatch
  - `zigpyThread.py`: Main async loop handler (~2000 lines)
  - `AppGeneric.py`, `AppZnp.py`, `AppBellows.py`, `AppDeconz.py`, `AppBlz.py`: Radio-specific setup
- `WebServer/`: REST endpoints for the separate WebUI
  - `WebServer.py`: Main server (~2000 lines)
  - `rest_*.py`: Endpoint implementations (groups, OTA, topology, etc.)
- `OTA.py`: Firmware upgrade logic
- `IAS.py`: IAS Zone (security) management
- `LoggingManagement.py`: Plugin logging
- `DomoticzDB.py`: Domoticz database API client

### Zigbee/ - Protocol & Encoding

- `zclCommands.py`: ZCL command definitions (~44KB)
- `zclDecoders.py`: ZCL message decoding (~42KB)
- `zdpCommands.py`: ZDP discovery commands
- `zdpDecoders.py`: ZDP response decoding
- `helperDefautResponse.py`: ZCL default response logic (tested)
- `encoder_tools.py`: Encoding utilities

### Z4D_decoders/ - Zigpy Protocol Decoders

Custom decoders for Zigpy protocol messages (distinct from ZCL):
- `z4d_decoder_Data_Indication.py`: Incoming data frames
- `z4d_decoder_IAS.py`: IAS zone status
- `z4d_decoder_Remotes.py`: Remote controls
- `z4d_decoder_helpers.py`: Shared decoding utilities

### DevicesModules/ - Specialized Device Support

Custom implementations for non-standard devices:
- `custom_Chameleon.py`: Chameleon remote
- `custom_GammaTroniques.py`: GammaTroniques devices (formatting alignment exceptions)
- `custom_zlinky.py`: French ZLinky meter
- `custom_Sonoff.py`, `custom_Schneider.py`, `custom_namron.py`: Brand-specific

## Data Persistence

**Device Database:**
- Legacy format: `Data/DeviceList.txt` (JSON-based, human-readable)
- Modern format: Stored in Domoticz database (via `useDomoticzDb` config)
- Loaded at startup, written on significant changes
- Contains all device state, clusters, attributes, firmware versions

**Key Fields in ListOfDevices:**
```python
ListOfDevices[ieee_address] = {
    'Name': str,
    'Status': 'Paired'|'Leave'|...,
    'MacAddress': ieee,
    'Model': str,
    'Manufacturer': str,
    'EP': {...},  # Endpoints
    'Cluster': {...},  # Cluster list
    ...
}
```

## Logging

**Logging via `self.log`:**
```python
self.log("info", "Message")  # or .error(), .warning()
self.log("debug", "Details", "ModuleName")
```

**Verbose Logging:** Controlled by `PluginConf.VerboseLogging` categories (e.g., "Heartbeat", "Input", "Device", etc.).

**Log Files:** Stored in `Logs/` directory (or configured path).

**Logging discipline:** Logs must be useful, not noisy. Errors should be actionable and non-fatal where possible.

## Common Tasks

### Adding a New Device Model

1. Add configuration to `z4d-certified-devices` repository (JSON)
2. If custom logic needed, add handler to `Modules/` or `DevicesModules/`
3. Register in cluster handlers if new clusters are involved
4. Test with actual device; validate attribute reading and commands

### Adding a New Cluster Feature

1. Define ZCL cluster in `Zigbee/zclCommands.py` if not present
2. Add decoder in `Zigbee/zclDecoders.py`
3. Add read/write handlers in `Modules/readAttributes.py` or `Modules/basicOutputs.py`
4. Add command handler in `Modules/command.py` if user-facing
5. Add configuration reporting setup in `Classes/ConfigureReporting.py` if applicable

### Debugging

1. Enable verbose logging via WebUI > Tools > Debug (or `PluginConf.VerboseLogging`)
2. Check `Logs/plugin_zigbee.log` for detailed traces
3. Use `self.log("debug", ...)` liberally in new code
4. Test with `pytest` for isolated logic; use WebUI for integration tests

### Handling Radio Backend Differences

Each backend (ZNP, EZSP, deCONZ, BLZ) has:
- Radio-specific app class: `Classes/ZigpyTransport/App*.py`
- Generic interface via `zigpyThread.py`
- Check `self.pluginconf['Zigpy']` for backend type
- Avoid backend-specific code in device modules; use generic API

## Guidelines

**Before Proposing Changes:**
- Read and follow AGENTS.md (mandatory)
- Ensure changes are backward compatible (stable9 requirement)
- No blocking calls in Zigpy thread
- Test with `pytest . && flake8 .`
- Keep plugin.py thin; move logic to Modules/
- Preserve device config JSON structure; migrations required for breaking changes
- Avoid hardcoding device behavior; use certified configs

**Commit Message Style:**
- Follow existing patterns (see recent commits)
- Reference issues if applicable
- Be descriptive; avoid generic messages

**Before Running `git commit` (GPG signing):**
- Commits in this repo are GPG-signed (`commit.gpgsign=true`). Claude Code's Bash tool has no real TTY, so gpg-agent/pinentry can fail to prompt for the key passphrase on the first signing attempt in a session (error: `gpg failed to sign the data`).
- Before attempting the first commit in a session, ask the user to unlock the key from a real terminal window by running:
  `"test" | gpg --clearsign -u EE19D8BB30B19ED276D7413D1F8D08C104E0238E`
- Do not work around this by disabling signing (`--no-gpg-sign` or `commit.gpgsign=false`) — that bypasses a deliberate security control and must never be done without the user explicitly asking for it.

**Safe Refactoring Areas:**
- Utility functions in `Modules/tools.py`
- Cluster helpers in `Modules/zclClusterHelpers.py`
- Adding new modules (not reorganizing existing)
- Internal variable renaming (if tested)

**Risky Changes (Requires Caution):**
- Device database schema changes
- Plugin lifecycle (onStart, onHeartbeat, onStop)
- Zigpy thread management
- Configuration schema
- WebServer routing

## Useful References

- **Wiki**: https://zigbeefordomoticz.github.io/wiki
- **Issues**: GitHub issue tracker
- **Device Support**: https://zigbee.blakadder.com/z4d.html
- **zigpy docs**: https://zigpy.readthedocs.io/
- **Domoticz Forum (English)**: https://www.domoticz.com/forum/viewforum.php?f=68
- **Domoticz Forum (French)**: https://easydomoticz.com/forum/viewforum.php?f=28

## Version & Branch Info

- **stable9**: Recommended for production (version 9.1.xxx)
- **stable8**: Out of support, locked (version 8.1.xxx)
- **stable7**: Out of support, locked (version 7.1.xxx)
- Current version: 9.1.002 (2026.8)
