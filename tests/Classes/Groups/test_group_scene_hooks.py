"""
tests/Classes/Groups/test_group_scene_hooks.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A device leaving a group has to hear about its scenes first: once it has left, it
refuses a scene command for that group. So the scene manager is told before Remove
Group goes out, on the two paths the plugin removes a member from a group.

The module is loaded in isolation against stubs, as in test_legrand_group_recovery.py.
"""

import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

NWKID = "5c3e"
EP = "0b"
IEEE = "a1b2c3d4e5f60708"
GROUP = "1001"


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def _deps():
    return {
        "Classes.GroupMgtv2.GrpCallBackResponses": dict(checkToCreateOrUpdateGroup=MagicMock()),
        "Classes.GroupMgtv2.GrpCommands": dict(
            add_group_member_ship=MagicMock(),
            check_group_member_ship=MagicMock(),
            look_for_group_member_ship=MagicMock(),
            remove_group_member_ship=MagicMock(),
            send_group_member_ship_identify_effect=MagicMock(),
        ),
        "Classes.GroupMgtv2.GrpDatabase": dict(
            check_if_group_empty=MagicMock(return_value=False),
            checkNwkIdAndUpdateIfAny=MagicMock(side_effect=lambda self, nwkid, ieee: nwkid),
            create_group=MagicMock(),
            remove_group=MagicMock(),
            remove_nwkid_from_all_groups=MagicMock(),
        ),
        "Classes.GroupMgtv2.GrpDomoticz": dict(
            LookForGroupAndCreateIfNeeded=MagicMock(),
            create_domoticz_group_device=MagicMock(),
            group_widget_unit=MagicMock(return_value=1),
            is_scene_selector=MagicMock(return_value=False),
            remove_domoticz_group_device=MagicMock(),
            scene_selector_unit=MagicMock(return_value=None),
            update_domoticz_group_name=MagicMock(),
        ),
        "Classes.GroupMgtv2.GrpIkeaRemote": dict(
            checkIfIkeaRound5BToBeAdded=MagicMock(return_value=False),
            checkIfIkeaRound5BToBeRemoved=MagicMock(return_value=False),
        ),
        "Modules.domoticzAbstractLayer": dict(domo_units=MagicMock(return_value=[1])),
        "Modules.tools": dict(mainPoweredDevice=MagicMock(return_value=True)),
        "Modules.zigateConsts": dict(LEGRAND_REMOTES=("Double gangs remote switch",)),
    }


@pytest.fixture(scope="module")
def grp():
    module_path = pathlib.Path(__file__).parents[3] / "Classes" / "GroupMgtv2" / "GrpServices.py"

    deps = _deps()
    saved = {name: sys.modules.pop(name, None) for name in deps}
    for name, attrs in deps.items():
        sys.modules[name] = _make_stub(name, **attrs)

    spec = importlib.util.spec_from_file_location("Classes.GroupMgtv2.GrpServices", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    yield module

    for name in deps:
        sys.modules.pop(name, None)
        if saved.get(name) is not None:
            sys.modules[name] = saved[name]


@pytest.fixture
def groupmgt(grp):
    grp.remove_group_member_ship.reset_mock()
    grp.domo_units.return_value = [1]
    grp.is_scene_selector.return_value = False
    manager = MagicMock()
    grp.remove_group_member_ship.side_effect = lambda *args: manager.remove_group_member_ship()
    groups = MagicMock()
    groups.ListOfGroups = {GROUP: {"Devices": [[NWKID, EP, IEEE]]}}
    groups.scenemgt = manager
    yield groups
    grp.remove_group_member_ship.side_effect = None


def test_update_tells_the_scene_manager_before_remove_group(grp, groupmgt):
    grp.update_group_and_remove_devices(groupmgt, GROUP, [[NWKID, EP, IEEE]])
    names = [c[0] for c in groupmgt.scenemgt.method_calls]
    assert names == ["member_removed", "remove_group_member_ship"]
    groupmgt.scenemgt.member_removed.assert_called_once_with(GROUP, NWKID, EP, IEEE)


def test_full_remove_tells_the_scene_manager_before_remove_group(grp, groupmgt):
    grp.FullRemoveOfGroup(groupmgt, 1, GROUP)
    names = [c[0] for c in groupmgt.scenemgt.method_calls]
    assert names == ["member_removed", "remove_group_member_ship"]


def test_the_widget_of_a_group_with_a_selector_keeps_the_members(grp, groupmgt):
    grp.domo_units.return_value = [1, 2]
    grp.FullRemoveOfGroup(groupmgt, 1, GROUP)
    grp.remove_group_member_ship.assert_not_called()
    groupmgt.scenemgt.member_removed.assert_not_called()
    assert "keeps its members" in groupmgt.logging.call_args.args[1]


def test_the_selector_of_a_group_with_a_widget_keeps_the_members(grp, groupmgt):
    grp.domo_units.return_value = [1, 2]
    grp.is_scene_selector.return_value = True
    grp.FullRemoveOfGroup(groupmgt, 2, GROUP)
    groupmgt.scenemgt.selector_removed.assert_called_once_with(GROUP)
    grp.remove_group_member_ship.assert_not_called()


def test_the_last_widget_takes_the_members(grp, groupmgt):
    grp.domo_units.return_value = [2]
    grp.is_scene_selector.return_value = True
    grp.FullRemoveOfGroup(groupmgt, 2, GROUP)
    groupmgt.scenemgt.selector_removed.assert_called_once_with(GROUP)
    grp.remove_group_member_ship.assert_called_once()


def test_a_selector_removed_by_the_plugin_was_the_last_widget(grp, groupmgt):
    grp.domo_units.return_value = []
    grp.FullRemoveOfGroup(groupmgt, None, GROUP)
    grp.remove_group_member_ship.assert_called_once()


def test_a_selector_outliving_its_group(grp, groupmgt):
    grp.is_scene_selector.return_value = True
    groupmgt.ListOfGroups = {}
    grp.FullRemoveOfGroup(groupmgt, 2, GROUP)
    groupmgt.scenemgt.selector_removed.assert_called_once_with(GROUP)
    grp.remove_group_member_ship.assert_not_called()


def test_scenes_not_enabled(grp, groupmgt):
    groupmgt.scenemgt = None
    grp.update_group_and_remove_devices(groupmgt, GROUP, [[NWKID, EP, IEEE]])
    grp.remove_group_member_ship.assert_called_once()


def test_the_hook_logs_under_groups_and_scene(grp, groupmgt):
    grp.scenes_member_removed(groupmgt, GROUP, NWKID, EP, IEEE)
    assert groupmgt.log.logging.call_args.args[:2] == (["Groups", "Scene"], "Debug")
