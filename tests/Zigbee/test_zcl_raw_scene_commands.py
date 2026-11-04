#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the cluster 0x0005 commands of Zigbee/zclRawCommands.py

The payloads are compared with what zigpy serialises from its own definition of
the Scenes cluster, so an error of field order, width or byte order cannot be
copied from the code into the expected value.

Coverage:
  - every command matches the zigpy schema, the optional Recall transition included
  - the frame is cluster specific, Client to Server, Disable Default Response set
  - only Recall goes out in group mode, with the group as address

Zigbee.zclRawCommands imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the rest of the session. The checks are
therefore executed in a subprocess, fully isolated from the pytest session.
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
    import Zigbee.zclRawCommands as zcl
    from zigpy.zcl.clusters.general import Scenes

    GROUP, SCENE = 0x1001, 0x03

    def sent(function, *args, **kwargs):
        p = types.SimpleNamespace()
        p.log = MagicMock()
        p.pluginconf = types.SimpleNamespace(pluginConf={"trackZclClustersOut": False})
        with patch.object(zcl, "raw_APS_request") as raw_aps, patch.object(zcl, "get_and_inc_ZCL_SQN", return_value="3c"):
            sqn = function(p, "d841", "01", "0b", *args, **kwargs)
        assert sqn == "3c"
        raw_aps.assert_called_once()
        return raw_aps.call_args

    def check(function, command, schema, *args, **kwargs):
        call = sent(function, *args, **kwargs)
        assert call.args[1:5] == ("d841", "0b", "0005", "0104"), call
        payload = call.args[5]
        expected = "113c%02x" % command.id + schema.serialize().hex()
        assert payload == expected, (payload, expected)
        assert call.kwargs["groupaddrmode"] is False, call
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


def test_store_scene():
    _run(
        """
        command = Scenes.ServerCommandDefs.store
        check(zcl.zcl_raw_store_scene, command, command.schema(group_id=GROUP, scene_id=SCENE), "1001", "03")
        """
    )


def test_store_scene_frame_byte_by_byte():
    _run(
        """
        # FCF 11 | TSN 3c | Store Scene 04 | group 0x1001 little endian | scene 03
        call = sent(zcl.zcl_raw_store_scene, "1001", "03")
        assert call.args[5] == "113c04011003", call
        """
    )


def test_add_scene_carries_the_transition_time_and_an_empty_name():
    _run(
        """
        command = Scenes.ServerCommandDefs.add
        schema = command.schema(group_id=GROUP, scene_id=SCENE, transition_time=300, scene_name="")
        check(zcl.zcl_raw_add_scene, command, schema, "1001", "03", transition_time=300)
        """
    )


def test_remove_scene():
    _run(
        """
        command = Scenes.ServerCommandDefs.remove
        check(zcl.zcl_raw_remove_scene, command, command.schema(group_id=GROUP, scene_id=SCENE), "1001", "03")
        """
    )


def test_remove_all_scenes():
    _run(
        """
        command = Scenes.ServerCommandDefs.remove_all
        check(zcl.zcl_raw_remove_all_scenes, command, command.schema(group_id=GROUP), "1001")
        """
    )


def test_get_scene_membership():
    _run(
        """
        command = Scenes.ServerCommandDefs.get_scene_membership
        check(zcl.zcl_raw_get_scene_membership, command, command.schema(group_id=GROUP), "1001")
        """
    )


def test_recall_scene_without_transition_leaves_the_optional_field_out():
    _run(
        """
        command = Scenes.ServerCommandDefs.recall
        check(zcl.zcl_raw_recall_scene, command, command.schema(group_id=GROUP, scene_id=SCENE), "1001", "03")
        """
    )


def test_recall_scene_with_transition():
    _run(
        """
        command = Scenes.ServerCommandDefs.recall
        schema = command.schema(group_id=GROUP, scene_id=SCENE, transition_time=25)
        check(zcl.zcl_raw_recall_scene, command, schema, "1001", "03", transition_time=25)
        """
    )


def test_recall_scene_group_cast_is_addressed_to_the_group():
    _run(
        """
        p = types.SimpleNamespace(log=MagicMock(), pluginconf=types.SimpleNamespace(pluginConf={"trackZclClustersOut": False}))
        with patch.object(zcl, "raw_APS_request") as raw_aps, patch.object(zcl, "get_and_inc_ZCL_SQN", return_value="3c"):
            zcl.zcl_raw_recall_scene(p, "1001", "01", "01", "1001", "03", groupaddrmode=True)
        raw_aps.assert_called_once()
        assert raw_aps.call_args.args[1] == "1001", raw_aps.call_args
        assert raw_aps.call_args.kwargs["groupaddrmode"] is True, raw_aps.call_args
        """
    )
