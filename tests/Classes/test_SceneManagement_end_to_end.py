#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A capture through the real commands and decoders, with only the radio replaced:
a fake lamp answers each frame the plugin sends the way a device would, and its
answer goes back through zcl_decoders and the decoder the plugin registers.

The other scene tests stop at a mock on one side or the other, so this is what
shows that the two halves agree on group, scene and endpoint formats.

The real Modules.* package conflicts with the stubs tests/conftest.py installs for
the session, so this runs in a subprocess.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SCRIPT = textwrap.dedent(
    """
    import sys, types
    from unittest.mock import MagicMock, patch

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)

    # Modules.input cannot be imported on its own, see test_zcl_scene_responses.py
    domo_maj = types.ModuleType("Modules.domoMaj")
    domo_maj.__getattr__ = lambda name: MagicMock(name=name)
    sys.modules["Modules.domoMaj"] = domo_maj

    import Modules.input
    import Zigbee.zclDecoders as decoders
    import Zigbee.zclRawCommands as raw
    from Classes.PluginStore import PluginStore
    from Classes.SceneManagement import SceneManagement
    from zigpy.zcl import foundation
    from zigpy.zcl.clusters.general import Scenes

    GROUP, NWKID, EP, IEEE = "1001", "c577", "0b", "a1b2c3d4e5f60708"
    FRAME = "018002003cff0001040300010102c57702000018c00a" + "2803"

    plugin = types.SimpleNamespace()
    plugin.log = MagicMock()
    plugin.pluginconf = types.SimpleNamespace(pluginConf={"trackZclClustersOut": False})
    plugin.zigbee_communication = "zigpy"
    plugin.DeviceConf = {}
    plugin.ListOfDevices = {NWKID: {
        "IEEE": IEEE, "ZDeviceName": "Ceiling", "Model": "TRADFRI bulb",
        "Ep": {EP: {}}, "Epv2": {EP: {"ClusterIn": {"0005": {}, "0006": {}, "0008": {}}}},
    }}
    plugin.IEEE2NWK = {IEEE: NWKID}
    plugin.ControllerLink = MagicMock()
    plugin.ControllerLink.loadTransmit.return_value = 0
    plugin.groupmgt = types.SimpleNamespace(ListOfGroups={GROUP: {"Name": "Living room", "Devices": [[NWKID, EP, IEEE]]}})

    store = PluginStore("Z4D_Scenes", 1)
    plugin.scenemgt = SceneManagement(plugin, store)

    class Lamp:
        \"\"\"Parses what zigpy would receive, keeps its table, answers as a device.\"\"\"
        def __init__(self, store_status=foundation.Status.SUCCESS):
            self.table = {}
            self.store_status = store_status
            self.seen = []

        def receive(self, _plugin, nwkid, ep, cluster, profile, payload, **kwargs):
            assert (nwkid, ep, cluster, profile) == (NWKID, EP, "0005", "0104")
            frame = bytes.fromhex(payload)
            assert frame[0] == 0x11, payload
            command = Scenes.ServerCommandDefs
            definition = next(d for d in vars(command).values() if getattr(d, "id", None) == frame[2])
            request, rest = definition.schema.deserialize(frame[3:])
            self.seen.append(definition.name)
            if definition.name == "add":
                self.table[(request.group_id, request.scene_id)] = request.transition_time
                self.answer("add_scene_response", foundation.Status.SUCCESS, request)
            elif definition.name == "store":
                self.answer("store_scene_response", self.store_status, request)

        def answer(self, name, status, request):
            response = getattr(Scenes.ClientCommandDefs, name)
            data = response.schema(status=status, group_id=request.group_id, scene_id=request.scene_id).serialize().hex()
            with patch.object(decoders, "zcl_raw_default_response"):
                frame = decoders.zcl_decoders(plugin, NWKID, EP, "01", "0005", "1942" + "%02x" % response.id + data, FRAME)
            Modules.input.DECODERS[frame[2:6]](plugin, {}, frame[12:12 + int(frame[6:10], 16)], "c0")

    def capture(lamp):
        with patch.object(raw, "raw_APS_request", lamp.receive), patch.object(raw, "get_and_inc_ZCL_SQN", return_value="3c"):
            return plugin.scenemgt.create_scene(GROUP, "Reading", 4)
    """
)


def _run(snippet):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SCRIPT + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout.strip()


def test_a_lamp_that_stores_the_scene_is_synced():
    _run(
        """
        lamp = Lamp()
        capture(lamp)
        assert lamp.seen == ["add", "store"], lamp.seen
        assert lamp.table == {(0x1001, 1): 4}, lamp.table
        view = plugin.scenemgt.group_view(GROUP)["scenes"][0]
        assert (view["synced"], view["native"]) == (1, 1), view
        assert view["members"][0]["status"] == "synced", view
        assert view["members"][0]["name"] == "Ceiling", view
        """
    )


def test_a_lamp_with_a_full_table_is_failed():
    _run(
        """
        lamp = Lamp(store_status=foundation.Status.INSUFFICIENT_SPACE)
        capture(lamp)
        view = plugin.scenemgt.group_view(GROUP)["scenes"][0]
        assert (view["synced"], view["members"][0]["status"], view["members"][0]["error"]) == (0, "failed", "89"), view
        """
    )
