"""
Tests for Z4D_decoders/z4d_decoder_Read_Attribute_Request.py

Decode0100 — read attribute request; dispatches to model-specific handlers
or responds with a default value for standard attributes.
"""

import sys
import importlib
import pytest
from unittest.mock import MagicMock

_MOD = "Z4D_decoders.z4d_decoder_Read_Attribute_Request"

LQI  = "ff"
ADDR = "abcd"
EP   = "01"

# Layout: sqn(2)+srcAddr(4)+srcEp(2)+dstEp(2)+clusterId(4)+dir(2)+
#         manufSpec(2)+manufCode(4)+nbAttr(2)+attributes(4 each)
def _msg(addr=ADDR, cluster="0000", attr="0000", nb="01", manuf_name="",
         manuf_spec="00", manuf_code="0000"):
    return (
        "01"            # sqn
        + addr          # srcAddr
        + EP            # srcEp
        + EP            # dstEp
        + cluster
        + "00"          # direction
        + manuf_spec
        + manuf_code
        + nb
        + attr
    )


@pytest.fixture(scope="module")
def mod():
    sys.modules.pop(_MOD, None)
    return importlib.import_module(_MOD)


class TestDecode0100:

    def test_unknown_device_calls_handle_unknow(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        sanity = MagicMock(return_value=False)
        handle = MagicMock()
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", sanity)
        monkeypatch.setattr(mod, "handle_unknow_device", handle)
        mod.Decode0100(plugin, {}, _msg(), LQI)
        handle.assert_called_once_with(plugin, ADDR)

    def test_livolo_model_calls_livolo_handler(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {ADDR: {"Model": "TI0001", "Manufacturer Name": ""}}
        livolo = MagicMock()
        monkeypatch.setattr(mod, "livolo_read_attribute_request", livolo)
        mod.Decode0100(plugin, {}, _msg(addr=ADDR), LQI)
        livolo.assert_called_once()

    def test_basic_cluster_attr_0000_calls_read_attr_response(self, mod, plugin, monkeypatch):
        """Cluster 0000 / attribute 0000 → read_attribute_response called."""
        plugin.ListOfDevices = {ADDR: {"Model": "SomeModel", "Manufacturer Name": "",
                                       "Manufacturer": ""}}
        rar = MagicMock()
        monkeypatch.setattr(mod, "read_attribute_response", rar)
        mod.Decode0100(plugin, {}, _msg(cluster="0000", attr="0000"), LQI)
        rar.assert_called_once()

    def test_time_cluster_answered_once_for_all_attributes(self, mod, plugin, monkeypatch):
        """Cluster 000a → one timeserver_multiple_read_attribute_request call carrying every attribute."""
        plugin.ListOfDevices = {ADDR: {"Model": "SomeModel", "Manufacturer Name": "",
                                       "Manufacturer": ""}}
        multi = MagicMock()
        rar = MagicMock()
        monkeypatch.setattr(mod, "timeserver_multiple_read_attribute_request", multi)
        monkeypatch.setattr(mod, "read_attribute_response", rar)
        mod.Decode0100(plugin, {}, _msg(cluster="000a", attr="000000020007", nb="03"), LQI)
        multi.assert_called_once()
        assert multi.call_args[0][9] == "000000020007"
        rar.assert_not_called()

    def test_other_cluster_logs(self, mod, plugin, monkeypatch):
        """Unknown cluster/attribute → logs Read Attribute Request."""
        plugin.ListOfDevices = {ADDR: {"Model": "SomeModel", "Manufacturer Name": "",
                                       "Manufacturer": ""}}
        monkeypatch.setattr(mod, "read_attribute_response", MagicMock())
        plugin.log.logging.reset_mock()
        mod.Decode0100(plugin, {}, _msg(cluster="ffff", attr="ffff"), LQI)
        assert plugin.log.logging.called

    def test_upd_lqi_called_even_for_unknown_device(self, mod, plugin, monkeypatch):
        plugin.ListOfDevices = {}
        upd = MagicMock()
        monkeypatch.setattr(mod, "updLQI", upd)
        monkeypatch.setattr(mod, "zigpy_plugin_sanity_check", MagicMock(return_value=False))
        monkeypatch.setattr(mod, "handle_unknow_device", MagicMock())
        mod.Decode0100(plugin, {}, _msg(), LQI)
        upd.assert_called()


class TestDecode0100LegrandOperatingTime:
    """
    Cluster 0000 attribute f000 is Legrand's operating time: the remote reads it from
    the coordinator and the plugin answers with its uptime.

    The branch used to be gated on the stored 'Manufacturer Name' alone, which is read
    from Basic attribute 0004 and is not necessarily there yet. A remote that asked
    seconds after joining, before 0004 came back, fell through to the default branch and
    got no answer. The request itself carries the manufacturer code, so it is enough to
    identify the device.
    """

    LEGRAND_FRAME = dict(cluster="0000", attr="f000", manuf_spec="01", manuf_code="1021")

    def _run(self, mod, plugin, monkeypatch, device, compatibility_mode=True, **frame):
        plugin.ListOfDevices = {ADDR: device}
        plugin.pluginconf.pluginConf["LegrandCompatibilityMode"] = compatibility_mode
        plugin.statistics._start = 0
        rar = MagicMock()
        monkeypatch.setattr(mod, "read_attribute_response", rar)
        mod.Decode0100(plugin, {}, _msg(**{**self.LEGRAND_FRAME, **frame}), LQI)
        return rar

    def test_answered_from_the_frame_manufacturer_code_alone(self, mod, plugin, monkeypatch):
        """The regression: nothing stored about the manufacturer yet, mid-pairing."""
        rar = self._run(mod, plugin, monkeypatch, {"Model": "Double gangs remote switch"})
        rar.assert_called_once()

    def test_answered_from_the_stored_manufacturer_name(self, mod, plugin, monkeypatch):
        """The path that already worked: no manufacturer code in the frame."""
        rar = self._run(
            mod, plugin, monkeypatch,
            {"Model": "Double gangs remote switch", "Manufacturer Name": "Legrand"},
            manuf_spec="00", manuf_code="0000",
        )
        rar.assert_called_once()

    def test_answered_from_the_stored_manufacturer_code(self, mod, plugin, monkeypatch):
        """'1021' is a code, so it belongs against 'Manufacturer', not 'Manufacturer Name'."""
        rar = self._run(
            mod, plugin, monkeypatch,
            {"Model": "Double gangs remote switch", "Manufacturer": "1021"},
            manuf_spec="00", manuf_code="0000",
        )
        rar.assert_called_once()

    def test_not_answered_when_nothing_identifies_legrand(self, mod, plugin, monkeypatch):
        rar = self._run(
            mod, plugin, monkeypatch,
            {"Model": "SomeModel", "Manufacturer": "117c", "Manufacturer Name": "IKEA of Sweden"},
            manuf_spec="00", manuf_code="0000",
        )
        rar.assert_not_called()

    def test_not_answered_when_compatibility_mode_is_off(self, mod, plugin, monkeypatch):
        """Widening the identification must not start answering with the option disabled."""
        rar = self._run(
            mod, plugin, monkeypatch,
            {"Model": "Double gangs remote switch"},
            compatibility_mode=False,
        )
        rar.assert_not_called()

    def test_response_carries_the_attribute_datatype_and_manufacturer_code(self, mod, plugin, monkeypatch):
        rar = self._run(mod, plugin, monkeypatch, {"Model": "Double gangs remote switch"})
        args, kwargs = rar.call_args
        assert args[4] == "0000"    # cluster
        assert args[5] == "00"      # status
        assert args[6] == "23"      # datatype, uint32
        assert args[7] == "f000"    # attribute
        assert kwargs["manuf_code"] == "1021"

