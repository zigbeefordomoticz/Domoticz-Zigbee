#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests: the REST request body is parsed as JSON, never evaluated.

PUT /rest-z4d/1/change-model, /recreate-widgets and /full-reprovisionning decode
the request body with json.loads(); anything other than a JSON object is refused
with an Error REST0001 and the device is left untouched.

Classes.WebServer.WebServer imports the real Modules.* package, which conflicts
with the stubs tests/conftest.py installs for the session, so the calls run in
a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

ROUTES = {
    # route: WebServer method
    "change-model": "rest_change_model_name",
    "recreate-widgets": "rest_recreate_widgets",
    "full-reprovisionning": "rest_full_reprovisionning",
}


def python_expression(marker):
    """A body that writes `marker` if it were evaluated as Python instead of parsed."""
    return "__import__('pathlib').Path(%r).write_text('evaluated')" % str(marker)


BODIES = {
    # name: (body, the body is a valid request)
    "json_object": (json.dumps({"NWKID": "8012", "Model": "new-model"}), True),
    "python_expression": (None, False),  # filled in with the marker path
    "python_literal": ("{'NWKID': '8012', 'Model': 'new-model'}", False),
    "json_list": (json.dumps([{"NWKID": "8012"}]), False),
    "json_string": (json.dumps("NWKID"), False),
    "not_utf8": ("\udcff", False),  # sent as the byte 0xff
    "empty": ("", False),
}


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    marker_dir = tmp_path_factory.mktemp("eval-marker")
    bodies = {}
    for name, (body, _valid) in BODIES.items():
        bodies[name] = python_expression(marker_dir / name) if name == "python_expression" else body

    snippet = textwrap.dedent(
        """
        import json, sys, types
        from unittest.mock import MagicMock
        for name in ("Domoticz", "DomoticzEx"):
            mod = types.ModuleType(name)
            mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
            sys.modules[name] = mod
        import Classes.WebServer.rest_change_ModelName as change_model
        import Classes.WebServer.rest_recreateWidget as recreate
        from Classes.WebServer.WebServer import WebServer

        requested = []
        change_model.update_model_name = lambda self, nwkid, model: requested.append(("update_model_name", nwkid, model))
        change_model.request_widget_creation = lambda self, nwkid, reason, **kw: requested.append(("widgets", nwkid))
        recreate.request_widget_creation = lambda self, nwkid, reason, **kw: requested.append(("widgets", nwkid))

        class PluginConf:
            pluginConf = {}

        class Log:
            def __init__(self):
                self.errors = []
            def logging(self, module, level, message, nwkid=None, context=None):
                if level == "Error":
                    self.errors.append({"message": message, "context": context})

        class Plugin:
            def __init__(self):
                self.pluginconf = PluginConf()
                self.log = Log()
                self.ListOfDevices = {"8012": {"IEEE": "00124b000425ea71", "Model": "old-model", "Status": "inDB", "Ep": {}}}
                self.IEEE2NWK = {"00124b000425ea71": "8012"}
            def logging(self, level, message):
                self.log.logging("WebServer", level, message)

        routes, bodies = json.loads(sys.argv[1]), json.loads(sys.argv[2])
        out = {}
        for route, method in routes.items():
            for name, body in bodies.items():
                plugin = Plugin()
                del requested[:]
                raw = body.encode("utf8", "surrogateescape")
                try:
                    response = getattr(WebServer, method)(plugin, "PUT", raw, [])
                    data = response["Data"]
                    data = sorted(data) if isinstance(data, set) else data
                    error = None
                except Exception as exc:
                    data, error = None, "%s: %s" % (type(exc).__name__, exc)
                out["%s|%s" % (route, name)] = {
                    "data": data,
                    "exception": error,
                    "errors": plugin.log.errors,
                    "status": plugin.ListOfDevices["8012"]["Status"],
                    "requested": requested[:],
                }
        print(json.dumps(out, default=str))
        """
    )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(ROUTES), json.dumps(bodies)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return {"marker_dir": marker_dir, "calls": json.loads(result.stdout.strip().splitlines()[-1])}


@pytest.mark.parametrize("route", ROUTES)
def test_python_expression_is_not_evaluated(results, route):
    assert not (results["marker_dir"] / "python_expression").exists()
    call = results["calls"]["%s|python_expression" % route]
    assert call["exception"] is None
    assert call["requested"] == []
    assert call["status"] == "inDB"


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("name", [name for name, (_body, valid) in BODIES.items() if not valid])
def test_body_that_is_not_a_json_object_is_refused(results, route, name):
    call = results["calls"]["%s|%s" % (route, name)]
    assert call["exception"] is None
    assert call["requested"] == []
    assert call["status"] == "inDB"
    assert [error["context"] for error in call["errors"]] == [{"Error code": "REST0001", "Route": route}]
    assert "not a JSON object" in str(call["data"])


def test_change_model_with_json_body(results):
    call = results["calls"]["change-model|json_object"]
    assert call["errors"] == [] and call["exception"] is None
    assert call["requested"] == [["update_model_name", "8012", "new-model"], ["widgets", "8012"]]


def test_recreate_widgets_with_json_body(results):
    call = results["calls"]["recreate-widgets|json_object"]
    assert call["errors"] == [] and call["exception"] is None
    assert call["requested"] == [["widgets", "8012"]]
    assert json.loads(call["data"])["Status"] == "Ok"


def test_full_reprovisionning_with_json_body(results):
    call = results["calls"]["full-reprovisionning|json_object"]
    assert call["errors"] == [] and call["exception"] is None
    assert call["status"] == "provREQ"
