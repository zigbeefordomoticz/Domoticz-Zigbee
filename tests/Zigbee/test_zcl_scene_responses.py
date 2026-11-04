#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the Scenes cluster responses, from zcl_decoders to the 80ax decoders.

Before this, every response fell through to "Unknown Command". The incoming
payloads are serialised by zigpy from its own definition of the cluster, so the
layout under test does not come from the code under test.

Zigbee.zclDecoders imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the session, so the checks run in a
subprocess.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import sys, types
    from unittest.mock import MagicMock, patch

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)

    # Modules.input cannot be imported on its own: Modules.domoMaj is only reached
    # through a circular import that plugin.py resolves. No scene response updates a widget.
    domo_maj = types.ModuleType("Modules.domoMaj")
    domo_maj.__getattr__ = lambda name: MagicMock(name=name)
    sys.modules["Modules.domoMaj"] = domo_maj

    import Modules.input
    import Zigbee.zclDecoders as decoders
    from zigpy.zcl import foundation
    from zigpy.zcl.clusters.general import Scenes

    NWKID, EP = "c577", "0b"
    GROUP = 0x1001
    FRAME = "018002003cff0001040300010102c57702000018c00a" + "2803"
    SERVER_TO_CLIENT = "19"
    CLIENT_TO_SERVER = "11"

    def plugin():
        p = types.SimpleNamespace()
        p.log = MagicMock()
        p.ListOfDevices = {NWKID: {"Model": "TRADFRI bulb"}}
        p.pluginconf = types.SimpleNamespace(pluginConf={})
        p.zigbee_communication = "zigpy"
        p.DeviceConf = {}
        return p

    def response(name, **fields):
        command = getattr(Scenes.ClientCommandDefs, name)
        return "%02x" % command.id, command.schema(**fields).serialize().hex()

    def decode(command, data, fcf=SERVER_TO_CLIENT, manuf=""):
        with patch.object(decoders, "zcl_raw_default_response"):
            return decoders.zcl_decoders(plugin(), NWKID, EP, "01", "0005", fcf + manuf + "42" + command + data, FRAME)

    def fields(frame):
        return frame[2:6], frame[12:12 + int(frame[6:10], 16)]

    def deliver(frame):
        \"\"\"Hand the frame to the decoder the plugin registers for it.\"\"\"
        msgtype, msgdata = fields(frame)
        p = plugin()
        Modules.input.DECODERS[msgtype](p, {}, msgdata, "c0")
        return p.log.logging.call_args_list
    """
)


def _run(snippet):
    """Execute `snippet` against the real (unstubbed) plugin modules."""
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout.strip()


def test_store_scene_response_success():
    _run(
        """
        command, data = response("store_scene_response", status=foundation.Status.SUCCESS, group_id=GROUP, scene_id=3)
        frame = decode(command, data)
        msgtype, msgdata = fields(frame)
        assert msgtype == "80a4", frame
        # Sqn | Ep | Cluster | Status | GroupId, as in ListOfGroups | SceneId | SrcNwkId
        assert msgdata == "42" + EP + "0005" + "00" + "1001" + "03" + NWKID, msgdata
        logged = deliver(frame)
        assert [c.args[1] for c in logged] == ["Debug"], logged
        assert logged[0].args[3] == NWKID, logged
        """
    )


def test_store_scene_response_table_full_is_a_log():
    _run(
        """
        command, data = response("store_scene_response", status=foundation.Status.INSUFFICIENT_SPACE, group_id=GROUP, scene_id=3)
        frame = decode(command, data)
        assert fields(frame)[1] == "42" + EP + "0005" + "89" + "1001" + "03" + NWKID, frame
        assert [c.args[1] for c in deliver(frame)] == ["Log"]
        """
    )


def test_add_and_remove_scene_responses():
    _run(
        """
        for name, msgtype in (("add_scene_response", "80a1"), ("remove_scene_response", "80a2")):
            command, data = response(name, status=foundation.Status.SUCCESS, group_id=GROUP, scene_id=3)
            frame = decode(command, data)
            assert fields(frame) == (msgtype, "42" + EP + "0005" + "00" + "1001" + "03" + NWKID), frame
            assert deliver(frame)
        """
    )


def test_remove_all_scenes_response_has_no_scene_id():
    _run(
        """
        command, data = response("remove_all_scenes_response", status=foundation.Status.SUCCESS, group_id=GROUP)
        frame = decode(command, data)
        assert fields(frame) == ("80a3", "42" + EP + "0005" + "00" + "1001" + NWKID), frame
        assert deliver(frame)[0].args[3] == NWKID
        """
    )


def test_membership_response_lists_every_scene():
    _run(
        """
        command, data = response(
            "get_scene_membership_response", status=foundation.Status.SUCCESS, capacity=12, group_id=GROUP, scenes=[1, 3, 7])
        frame = decode(command, data)
        assert fields(frame) == ("80a6", "42" + EP + "0005" + "00" + "0c" + "1001" + "03" + "010307" + NWKID), frame
        logged = deliver(frame)
        assert len(logged) == 1 and logged[0].args[1] == "Debug", logged
        assert "['01', '03', '07']" in logged[0].args[2], logged
        assert logged[0].args[3] == NWKID, logged
        """
    )


def test_membership_response_with_a_full_table_is_not_rejected():
    _run(
        """
        # Capacity is what remains: 0 with scenes stored is a full table, not an error
        command, data = response(
            "get_scene_membership_response", status=foundation.Status.SUCCESS, capacity=0, group_id=GROUP, scenes=[1, 2])
        logged = deliver(decode(command, data))
        assert "['01', '02']" in logged[0].args[2], logged
        """
    )


def test_membership_response_failure_carries_no_list():
    _run(
        """
        command, data = response(
            "get_scene_membership_response", status=foundation.Status.INVALID_FIELD, capacity=255, group_id=GROUP)
        frame = decode(command, data)
        assert fields(frame) == ("80a6", "42" + EP + "0005" + "85" + "ff" + "1001" + "00" + NWKID), frame
        logged = deliver(frame)
        assert [c.args[1] for c in logged] == ["Log"], logged
        assert logged[0].args[3] == NWKID, logged
        """
    )


def test_truncated_responses_are_dropped():
    _run(
        """
        for command, data in (("04", "000110"), ("03", "0001"), ("06", "000c0110"), ("06", "000c01100301"), ("06", "00")):
            assert decode(command, data) is None, (command, data)
        """
    )


def test_a_command_towards_the_server_is_not_a_response():
    _run(
        """
        # Get Scene Membership sent by a remote: same id as the response
        assert decode("06", "0110", fcf=CLIENT_TO_SERVER) == FRAME
        """
    )


def test_a_manufacturer_specific_frame_is_not_a_response():
    _run(
        """
        assert decode("04", "00011003", fcf="1d", manuf="7c11") == FRAME
        """
    )


def test_recall_scene_from_a_remote_is_unchanged():
    _run(
        """
        frame = decode("05", "011003", fcf=CLIENT_TO_SERVER)
        assert fields(frame)[0] == "80a5", frame
        """
    )


def test_scene_debug_category_exists_for_tools_debug():
    """In Tools > Debug with the other modules: an unknown module raises a Domoticz error."""
    _run(
        """
        from Classes.PluginConf import SETTINGS
        scene = SETTINGS["VerboseLogging"]["param"]["Scene"]
        assert scene["type"] == "bool" and scene["default"] == 0
        assert scene["restart"] == 0 and not scene["hidden"]
        """
    )


def test_scene_response_debug_follows_the_scene_category():
    _run(
        """
        import Classes.LoggingManagement as lm

        command, data = response("store_scene_response", status=foundation.Status.SUCCESS, group_id=GROUP, scene_id=3)
        module = deliver(decode(command, data))[0].args[0]
        assert module == ["Input", "Scene"], module

        def enqueued(**enabled):
            logger = MagicMock()
            logger.pluginconf.pluginConf = {"Input": 0, "Scene": 0, **enabled}
            with patch.object(lm, "enqueue_logging") as enqueue:
                lm.LoggingManagement.logging(logger, module, "Debug", "message")
            return enqueue.call_count

        assert enqueued() == 0
        assert enqueued(Scene=1) == 1
        assert enqueued(Input=1) == 1
        assert enqueued(Input=1, Scene=1) == 1
        """
    )


def test_raw_scene_command_debug_follows_the_scene_category():
    _run(
        """
        import Zigbee.zclRawCommands as raw

        p = plugin()
        with patch.object(raw, "raw_APS_request"), patch.object(raw, "get_and_inc_ZCL_SQN", return_value="01"), patch.object(raw, "zcl_command_formated_logging"):
            raw.zcl_raw_get_scene_membership(p, NWKID, "01", EP, "1001")
        assert p.log.logging.call_args_list[0].args[0] == ["zclCommand", "Scene"]
        """
    )
