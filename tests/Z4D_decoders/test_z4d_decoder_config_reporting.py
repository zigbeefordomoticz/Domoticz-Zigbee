"""
Tests for Z4D_decoders/z4d_decoder_config_reporting.py

Covers:
  - Decode8120  – configure-reporting response (single and multi-attribute)
  - Decode8122  – read-report-configure response (zigpy)
  - Decode8120_attribute – per-attribute delegate
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock, call

_MOD = "Z4D_decoders.z4d_decoder_config_reporting"

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mod():
    """Import the real decoder module (clearing any stub from test_input.py)."""
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


# ─── Message helpers ──────────────────────────────────────────────────────────
#
# Decode8120 message layout (all hex pairs):
#   [0:2]   SQN
#   [2:6]   SrcAddr
#   [6:8]   SrcEp
#   [8:12]  ClusterId
#   [12:14] Status               (when len == 14, single "global" status)
#   [12:16] AttributeId          (when len > 14)
#   [16:18] Status per attribute (when len > 14)
#   … repeated …

SQN    = "01"
ADDR   = "1234"
EP     = "01"
CLUST  = "0006"
STATUS = "00"
ATTR1  = "0001"
ATTR2  = "0002"

# Minimal 14-char message – single global status
MSG_SINGLE = SQN + ADDR + EP + CLUST + STATUS   # 14 chars

# 18-char message – one attribute + status
MSG_ONE_ATTR = SQN + ADDR + EP + CLUST + ATTR1 + STATUS  # 18 chars

# 24-char message – two attributes + statuses
MSG_TWO_ATTR = SQN + ADDR + EP + CLUST + ATTR1 + STATUS + ATTR2 + STATUS  # 24 chars

LQI = "ff"


# ─── Decode8120 ───────────────────────────────────────────────────────────────

class TestDecode8120:

    def test_too_short_logs_error(self, mod, plugin):
        mod.Decode8120(plugin, {}, "0112340100", LQI)  # 10 chars < 14
        assert any(
            c.args[1] == "Error"
            for c in plugin.log.logging.call_args_list
        )

    def test_too_short_returns_early(self, mod, plugin, monkeypatch):
        called = []
        monkeypatch.setattr(mod, "timeStamped", lambda *a: called.append(a))
        mod.Decode8120(plugin, {}, "0112340100", LQI)
        assert called == []

    def test_unknown_device_logs_error(self, mod, plugin):
        plugin.ListOfDevices = {}  # device "1234" not present
        mod.Decode8120(plugin, {}, MSG_SINGLE, LQI)
        assert any(
            c.args[1] == "Error"
            for c in plugin.log.logging.call_args_list
        )

    def test_unknown_device_calls_sanity_check(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        sanity = MagicMock(return_value=True)
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", sanity)
        mod.Decode8120(plugin, {}, MSG_SINGLE, LQI)
        sanity.assert_called_once_with(plugin, ADDR)

    def test_unknown_device_calls_handle_unknown_when_sanity_fails(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", MagicMock(return_value=False))
        handle = MagicMock()
        monkeypatch.setattr(mod, "handle_unknow_device", handle)
        mod.Decode8120(plugin, {}, MSG_SINGLE, LQI)
        handle.assert_called_once_with(plugin, ADDR)

    def test_known_device_updates_timestamp(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}}
        ts = MagicMock()
        monkeypatch.setattr(mod, "timeStamped", ts)
        mod.Decode8120(plugin, {}, MSG_SINGLE, LQI)
        ts.assert_called_once_with(plugin, ADDR, 0x8120)

    def test_known_device_updates_sqn(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}}
        usqn = MagicMock()
        monkeypatch.setattr(mod, "updSQN", usqn)
        mod.Decode8120(plugin, {}, MSG_SINGLE, LQI)
        usqn.assert_called_once_with(plugin, ADDR, SQN)

    def test_known_device_updates_lqi(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}}
        ulqi = MagicMock()
        monkeypatch.setattr(mod, "updLQI", ulqi)
        mod.Decode8120(plugin, {}, MSG_SINGLE, LQI)
        ulqi.assert_called_once_with(plugin, ADDR, LQI)

    def test_single_status_calls_attribute_with_none_attrid(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}}
        attr_fn = MagicMock()
        monkeypatch.setattr(mod, "Decode8120_attribute", attr_fn)
        mod.Decode8120(plugin, {}, MSG_SINGLE, LQI)
        attr_fn.assert_called_once_with(plugin, SQN, ADDR, EP, CLUST, None, STATUS)

    def test_multi_attr_calls_attribute_for_each(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}}
        attr_fn = MagicMock()
        monkeypatch.setattr(mod, "Decode8120_attribute", attr_fn)
        mod.Decode8120(plugin, {}, MSG_TWO_ATTR, LQI)
        assert attr_fn.call_count == 2
        attr_fn.assert_any_call(plugin, SQN, ADDR, EP, CLUST, ATTR1, STATUS)
        attr_fn.assert_any_call(plugin, SQN, ADDR, EP, CLUST, ATTR2, STATUS)

    def test_one_attr_message_calls_attribute_once(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices[ADDR] = {"Ep": {}}
        attr_fn = MagicMock()
        monkeypatch.setattr(mod, "Decode8120_attribute", attr_fn)
        mod.Decode8120(plugin, {}, MSG_ONE_ATTR, LQI)
        assert attr_fn.call_count == 1
        attr_fn.assert_called_once_with(plugin, SQN, ADDR, EP, CLUST, ATTR1, STATUS)


# ─── Decode8122 ───────────────────────────────────────────────────────────────

class TestDecode8122:

    def test_no_configure_reporting_does_nothing(self, mod, plugin):
        plugin.configureReporting = None
        # Should not raise
        mod.Decode8122(plugin, {}, MSG_SINGLE, LQI)

    def test_with_configure_reporting_delegates(self, mod, plugin):
        plugin.configureReporting = MagicMock()
        mod.Decode8122(plugin, {}, MSG_SINGLE, LQI)
        plugin.configureReporting.read_report_configure_response.assert_called_once_with(
            MSG_SINGLE, LQI
        )


# ─── Decode8120_attribute ─────────────────────────────────────────────────────

class TestDecode8120Attribute:

    def test_no_configure_reporting_does_nothing(self, mod, plugin):
        plugin.configureReporting = None
        # Should log but not crash
        mod.Decode8120_attribute(plugin, SQN, ADDR, EP, CLUST, ATTR1, STATUS)

    def test_with_configure_reporting_delegates(self, mod, plugin):
        plugin.configureReporting = MagicMock()
        mod.Decode8120_attribute(plugin, SQN, ADDR, EP, CLUST, ATTR1, STATUS)
        plugin.configureReporting.read_configure_reporting_response.assert_called_once_with(
            SQN, ADDR, EP, CLUST, ATTR1, STATUS
        )

    def test_none_attribute_id_is_forwarded(self, mod, plugin):
        plugin.configureReporting = MagicMock()
        mod.Decode8120_attribute(plugin, SQN, ADDR, EP, CLUST, None, STATUS)
        plugin.configureReporting.read_configure_reporting_response.assert_called_once_with(
            SQN, ADDR, EP, CLUST, None, STATUS
        )
