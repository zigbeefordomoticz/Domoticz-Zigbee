#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/WebServer/rest_Scenes.py

The module is loaded with a stub of Classes.SceneManagement, so a route is checked
by the scene manager call it makes. The whole path, down to the frames, is in
tests/Classes/test_SceneManagement_end_to_end.py.
"""

import ast
import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


class SceneError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


@pytest.fixture(scope="module")
def rest():
    stub = types.ModuleType("Classes.SceneManagement")
    stub.SceneError = SceneError
    sys.modules.pop("Classes.WebServer.rest_Scenes", None)
    with patch.dict(sys.modules, {"Classes.SceneManagement": stub}):
        module = importlib.import_module("Classes.WebServer.rest_Scenes")
    sys.modules.pop("Classes.WebServer.rest_Scenes", None)
    return module


@pytest.fixture
def server():
    s = types.SimpleNamespace()
    s.logging = MagicMock()
    s.log = MagicMock()
    s.pluginconf = types.SimpleNamespace(pluginConf={})
    s.scenemgt = MagicMock()
    for name in ("groups_view", "group_view", "create_scene", "edit_scene", "capture_scene", "recall_scene", "retry_scene"):
        getattr(s.scenemgt, name).return_value = {"from": name}
    return s


@pytest.mark.parametrize("verb, parameters, body, method, expected", [
    ("GET", [], None, "groups_view", ()),
    ("GET", ["1001"], None, "group_view", ("1001",)),
    ("PUT", ["1001"], b'{"name": "Reading", "transitionTime": 3}', "create_scene", ("1001", "Reading", 3, None, None, None)),
    ("PUT", ["1001"], b'{"name": "Reading", "transitionTime": 3, "sceneId": "2a"}', "create_scene", ("1001", "Reading", 3, "2a", None, None)),
    ("PUT", ["1001"], b'{"name": "Reading"}', "create_scene", ("1001", "Reading", 1, None, None, None)),
    ("PUT", ["1001"], b'{"name": "Reading", "members": ["a-01"]}', "create_scene", ("1001", "Reading", 1, None, None, ["a-01"])),
    ("PUT", ["1001", "03"], b'{"name": "Evening"}', "edit_scene", ("1001", "03", "Evening", None, None)),
    ("PUT", ["1001", "03"], b'{"name": "Evening", "members": ["a-01"]}', "edit_scene", ("1001", "03", "Evening", None, ["a-01"])),
    ("PUT", ["1001", "03", "capture"], None, "capture_scene", ("1001", "03", None, None)),
    ("PUT", ["1001", "03", "capture"], b'{"transitionTime": 5}', "capture_scene", ("1001", "03", 5, None)),
    ("PUT", ["1001", "03", "capture"], b'{"members": ["a-01"]}', "capture_scene", ("1001", "03", None, ["a-01"])),
    ("PUT", ["1001", "03", "recall"], None, "recall_scene", ("1001", "03")),
    ("PUT", ["1001", "03", "retry"], b"{}", "retry_scene", ("1001", "03")),
])
def test_routes(rest, server, verb, parameters, body, method, expected):
    response = rest.rest_scenes(server, verb, body, parameters)
    assert response["Status"] == "200 OK"
    getattr(server.scenemgt, method).assert_called_once_with(*expected)
    assert json.loads(response["Data"]) == {"from": method}


def test_delete(rest, server):
    response = rest.rest_scenes(server, "DELETE", None, ["1001", "03"])
    server.scenemgt.delete_scene.assert_called_once_with("1001", "03")
    assert json.loads(response["Data"]) == {}


def test_a_create_without_a_name_is_left_to_the_scene_manager(rest, server):
    rest.rest_scenes(server, "PUT", None, ["1001"])
    server.scenemgt.create_scene.assert_called_once_with("1001", None, 1, None, None, None)


def test_a_comment_reaches_the_scene_manager(rest, server):
    server.scenemgt.create_scene.return_value = {}
    server.scenemgt.edit_scene.return_value = {}
    rest.rest_scenes(server, "PUT", json.dumps({"name": "Movie", "comment": "Sofa"}).encode(), ["1001"])
    server.scenemgt.create_scene.assert_called_once_with("1001", "Movie", 1, None, "Sofa", None)
    rest.rest_scenes(server, "PUT", json.dumps({"name": "Movie", "comment": "Table"}).encode(), ["1001", "03"])
    server.scenemgt.edit_scene.assert_called_once_with("1001", "03", "Movie", "Table", None)


def test_a_rename_without_a_comment(rest, server):
    server.scenemgt.edit_scene.return_value = {}
    rest.rest_scenes(server, "PUT", json.dumps({"name": "Movie"}).encode(), ["1001", "03"])
    server.scenemgt.edit_scene.assert_called_once_with("1001", "03", "Movie", None, None)


@pytest.mark.parametrize("verb, parameters, body", [
    ("PUT", [], None),
    ("GET", ["1001", "03"], None),
    ("DELETE", ["1001"], None),
    ("PUT", ["1001", "03", "explode"], None),
    ("PUT", ["1001", "03", "recall", "now"], None),
    ("PUT", ["1001"], b"not json"),
    ("PUT", ["1001"], b"[1, 2]"),
])
def test_bad_requests(rest, server, verb, parameters, body):
    response = rest.rest_scenes(server, verb, body, parameters)
    assert response["Status"] == "400 BAD REQUEST"
    assert json.loads(response["Data"]) == {"error": "BAD_REQUEST"}
    assert server.scenemgt.method_calls == []


@pytest.mark.parametrize("code, status", [
    ("NAME_DUPLICATE", "400 BAD REQUEST"),
    ("SCENE_ID_INVALID", "400 BAD REQUEST"),
    ("SCENE_ID_IN_USE", "409 CONFLICT"),
    ("SCENE_ID_CHECK_RUNNING", "409 CONFLICT"),
    ("SCENE_NOT_FOUND", "404 NOT FOUND"),
    ("NO_CAPABLE_MEMBER", "409 CONFLICT"),
    ("COORDINATOR_BUSY", "503 SERVICE UNAVAILABLE"),
])
def test_a_refusal_keeps_its_code(rest, server, code, status):
    server.scenemgt.recall_scene.side_effect = SceneError(code)
    response = rest.rest_scenes(server, "PUT", None, ["1001", "03", "recall"])
    assert response["Status"] == status
    assert json.loads(response["Data"]) == {"error": code}


def test_scenes_not_enabled(rest, server):
    server.scenemgt = None
    response = rest.rest_scenes(server, "GET", None, [])
    assert response["Status"] == "409 CONFLICT"
    assert json.loads(response["Data"]) == {"error": "SCENES_DISABLED"}


def test_scan_is_not_a_rename(rest, server):
    server.scenemgt.scan_group.return_value = {"groupId": "1001", "scan": {"running": True}}
    response = rest.rest_scenes(server, "PUT", None, ["1001", "scan"])
    server.scenemgt.scan_group.assert_called_once_with("1001")
    server.scenemgt.edit_scene.assert_not_called()
    assert json.loads(response["Data"])["scan"] == {"running": True}


def test_a_refusal_logs_under_webserver_and_scene(rest, server):
    server.scenemgt.recall_scene.side_effect = SceneError("SCENE_NOT_FOUND")
    rest.rest_scenes(server, "PUT", None, ["1001", "03", "recall"])
    assert server.log.logging.call_args.args[:2] == (["WebServer", "Scene"], "Debug")
    assert "SCENE_NOT_FOUND" in server.log.logging.call_args.args[2]


def test_an_unexpected_exception_is_not_swallowed(rest, server):
    # do_rest turns it into a 500 with the traceback in the log
    server.scenemgt.groups_view.side_effect = KeyError("boom")
    with pytest.raises(KeyError):
        rest.rest_scenes(server, "GET", None, [])


def test_every_code_raised_has_a_status(rest):
    raised = set()
    for source in ("Classes/SceneManagement.py", "Classes/WebServer/rest_Scenes.py"):
        tree = ast.parse((REPO_ROOT / source).read_text())
        raised |= {
            node.args[0].value for node in ast.walk(tree)
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "SceneError"
        }
    assert raised
    assert raised <= set(rest.ERROR_STATUS)


def test_the_route_takes_no_post():
    # A POST with a text/plain body has no preflight, and nothing else stops another web page
    source = (REPO_ROOT / "Classes/WebServer/dispatcher.py").read_text()
    route = next(line for line in source.splitlines() if '"Name": "scenes"' in line)
    assert "POST" not in route
