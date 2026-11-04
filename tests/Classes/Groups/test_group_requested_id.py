"""
tests/Classes/Groups/test_group_requested_id.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A new group asking for its id, through PUT /zgroup.

The functions under test are taken from the source and run on their own: importing
the real modules here would break unrelated tests through the conftest stubs.

Run with:
    python -m pytest tests/Classes/Groups/test_group_requested_id.py -v
"""

import ast
import json
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[3]
SERVICES = ROOT / "Classes" / "GroupMgtv2" / "GrpWebServices.py"
ERRORS = ROOT / "Classes" / "GroupMgtv2" / "GrpErrorCodes.py"
REST = ROOT / "Classes" / "WebServer" / "rest_Groups.py"
LAMP = {"_NwkId": "8c11", "Ep": "0b", "IEEE": "0017880102a3b4c5"}


def source_of(path, *names):
    source = path.read_text()
    found = {node.name: ast.get_source_segment(source, node) for node in ast.parse(source).body
             if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names}
    assert set(found) == set(names), set(names) - set(found)
    return "\n\n".join(found[name] for name in names)


def constant(path, name):
    source = path.read_text()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
            return ast.get_source_segment(source, node)
    raise AssertionError(name)


@pytest.fixture
def services():
    namespace = {
        "re": re,
        "create_new_group_and_attach_devices": MagicMock(),
        "SendGroupIdentifyEffect": MagicMock(),
        "updateGroupName": MagicMock(),
        "updateGroup": MagicMock(),
        "delGroup": MagicMock(),
        "fullGroupRemove": MagicMock(),
        "get_group_id": MagicMock(return_value="0003"),
        "diff": lambda first, second: [item for item in first if item not in second],
    }
    exec(source_of(ERRORS, "GroupRequestError"), namespace)
    exec(constant(SERVICES, "MAX_GROUP_ID"), namespace)
    exec(constant(SERVICES, "GROUP_ID_FORMAT"), namespace)
    exec(source_of(SERVICES, "requested_group_id", "newGroup", "process_web_request"), namespace)
    return namespace


@pytest.fixture
def manager():
    fake = MagicMock()
    fake.ListOfGroups = {"0001": {"Name": "Living room"}, "fff4": {"Name": "Remote"}}
    fake.ListOfDevices = {}
    fake.pluginconf.pluginConf = {"pingViaGroup": 0x1234}
    return fake


def request(requested=None, **more):
    item = {"GroupName": "New", "devicesSelected": [LAMP], **more}
    if requested is not None:
        item["requestedGroupId"] = requested
    return [item]


def created(services):
    return services["create_new_group_and_attach_devices"].call_args.args[1]


def test_without_a_request_the_plugin_chooses(services, manager):
    services["process_web_request"](manager, request())
    assert created(services) == "0003"


@pytest.mark.parametrize("requested, expected", [("0a2b", "0a2b"), ("0A2B", "0a2b"), ("fff7", "fff7"), ("0002", "0002")])
def test_the_id_asked_for_is_used(services, manager, requested, expected):
    services["process_web_request"](manager, request(requested))
    assert created(services) == expected
    services["get_group_id"].assert_not_called()


@pytest.mark.parametrize("requested", ["1", "123", "12345", "zzzz", "+123", " 123", 4660, ""])
def test_a_malformed_id_is_refused(services, manager, requested):
    with pytest.raises(services["GroupRequestError"]) as caught:
        services["process_web_request"](manager, request(requested))
    assert caught.value.code == "GROUP_ID_INVALID"


@pytest.mark.parametrize("requested", ["0000", "fff8", "ffff", "1234"])
def test_a_reserved_id_is_refused(services, manager, requested):
    with pytest.raises(services["GroupRequestError"]) as caught:
        services["process_web_request"](manager, request(requested))
    assert caught.value.code == "GROUP_ID_RESERVED"


@pytest.mark.parametrize("requested", ["0001", "FFF4"])
def test_an_id_in_use_is_refused(services, manager, requested):
    with pytest.raises(services["GroupRequestError"]) as caught:
        services["process_web_request"](manager, request(requested))
    assert caught.value.code == "GROUP_ID_IN_USE"


def test_a_refusal_changes_nothing(services, manager):
    with pytest.raises(services["GroupRequestError"]):
        services["process_web_request"](manager, request("0001"))
    services["create_new_group_and_attach_devices"].assert_not_called()
    services["delGroup"].assert_not_called()


def test_the_id_asked_for_does_not_remove_the_other_groups(services, manager):
    services["process_web_request"](manager, request("0a2b"))
    services["delGroup"].assert_not_called()


def test_an_unknown_group_id_is_still_not_a_way_to_create_one(services, manager):
    # Why requestedGroupId exists: it removes every group not in the list
    services["process_web_request"](manager, request(_GroupId="0a2b"))
    services["create_new_group_and_attach_devices"].assert_not_called()
    assert [call.args[1] for call in services["delGroup"].call_args_list] == ["0001", "fff4"]


def test_an_existing_group_ignores_the_request(services, manager):
    services["process_web_request"](manager, request("0a2b", _GroupId="0001") + [{"GroupName": "Remote", "_GroupId": "fff4"}])
    services["updateGroup"].assert_called()
    services["create_new_group_and_attach_devices"].assert_not_called()
    assert "0a2b" not in str(services["updateGroupName"].call_args_list)


class TestRest:

    @pytest.fixture
    def put(self, services):
        namespace = {
            "json": json,
            "GroupRequestError": services["GroupRequestError"],
            "prepResponseMessage": lambda _self, _headers: {"Status": "200 OK"},
            "setupHeadersResponse": dict,
        }
        exec(constant(REST, "GROUP_ERROR_STATUS"), namespace)
        exec(source_of(REST, "_zgroup_put"), namespace)
        return namespace["_zgroup_put"]

    @pytest.mark.parametrize("code, status", [
        ("GROUP_ID_INVALID", "400 BAD REQUEST"),
        ("GROUP_ID_RESERVED", "400 BAD REQUEST"),
        ("GROUP_ID_IN_USE", "409 CONFLICT"),
    ])
    def test_a_refusal_reaches_the_client(self, put, services, code, status):
        server = MagicMock()
        server.groupmgt.process_web_request.side_effect = services["GroupRequestError"](code)
        response = put(server, b"[]", [])
        assert response["Status"] == status
        assert json.loads(response["Data"]) == {"error": code}

    def test_a_request_served_answers_as_before(self, put):
        response = put(MagicMock(), b"[]", [])
        assert response == {"Status": "200 OK", "Data": {}}
