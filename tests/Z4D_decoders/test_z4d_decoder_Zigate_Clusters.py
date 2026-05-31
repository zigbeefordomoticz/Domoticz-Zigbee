"""
Tests for Z4D_decoders/z4d_decoder_Zigate_Clusters.py

Decode8003 — stores a list of cluster IDs in ControllerData.
Decode8004 — stores a list of attribute IDs in ControllerData.
Decode8005 — stores a list of command IDs in ControllerData.
All three log a Status message.
"""

import sys
import importlib
import pytest

_MOD = "Z4D_decoders.z4d_decoder_Zigate_Clusters"


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


LQI = "ff"
# Layout: EP(2) + ProfileID(4) + items(4 each)
_BASE = "01" + "0104"


class TestDecode8003:

    def test_stores_cluster_list(self, mod, plugin):
        plugin.ControllerData = {}
        mod.Decode8003(plugin, {}, _BASE + "0006" + "0008", LQI)
        assert plugin.ControllerData["Cluster List"] == ["0006", "0008"]

    def test_empty_clusters(self, mod, plugin):
        plugin.ControllerData = {}
        mod.Decode8003(plugin, {}, _BASE, LQI)
        assert plugin.ControllerData["Cluster List"] == []

    def test_logs_status(self, mod, plugin):
        mod.Decode8003(plugin, {}, _BASE + "0006", LQI)
        assert any(c.args[1] == "Status" for c in plugin.log.logging.call_args_list)


class TestDecode8004:

    def test_stores_attribute_list(self, mod, plugin):
        plugin.ControllerData = {}
        # EP(2)+ProfileID(4)+ClusterID(4)+attributes(4 each)
        mod.Decode8004(plugin, {}, _BASE + "0006" + "0000" + "0001", LQI)
        assert plugin.ControllerData["Device Attributs List"] == ["0000", "0001"]

    def test_logs_status(self, mod, plugin):
        mod.Decode8004(plugin, {}, _BASE + "0006" + "0000", LQI)
        assert any(c.args[1] == "Status" for c in plugin.log.logging.call_args_list)


class TestDecode8005:

    def test_stores_command_list(self, mod, plugin):
        plugin.ControllerData = {}
        # EP(2)+ProfileID(4)+ClusterID(4)+commands(4 each)
        mod.Decode8005(plugin, {}, _BASE + "0006" + "0001" + "0002", LQI)
        assert plugin.ControllerData["Device Attributs List"] == ["0001", "0002"]

    def test_logs_status(self, mod, plugin):
        mod.Decode8005(plugin, {}, _BASE + "0006" + "0001", LQI)
        assert any(c.args[1] == "Status" for c in plugin.log.logging.call_args_list)
