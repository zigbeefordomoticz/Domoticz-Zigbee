#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guard: no WebServer REST endpoint may call the Domoticz widget API.

Classes/WebServer/com.py starts a thread per client (handle_client), so every
rest_*.py handler runs off the thread Domoticz calls the plugin on. The Domoticz
Python plugin API is not usable from there: CUnitEx_insert and friends mutate the
plugin's own device dictionary and release the GIL around their SQL
(hardware/plugins/PythonObjectEx.cpp). Work that touches widgets must therefore be
handed to the heartbeat - see Modules/domoCreate.py: request_widget_creation() /
process_widget_creation_requests().

This is checked by parsing the endpoint sources rather than by running them: the
property being protected is "this code never reaches the Domoticz API from this
thread", which is a property of the call graph, and a future endpoint would
otherwise reintroduce the bug untested.
"""

import ast
import unittest
from pathlib import Path

WEBSERVER_DIR = Path("Classes/WebServer")

# Helpers that end up calling the Domoticz plugin API (Unit().Create()/Delete()).
FORBIDDEN_NAMES = {
    "CreateDomoDevice",
    "createDomoticzWidget",
    "create_native_widget",
    "create_switch_selector_widget",
    "create_xcube_widgets",
    "domo_create_api",
    "domo_delete_widget",
    "remove_all_widgets",
    "remove_widget",
    "retry_failed_widget_creation",
    "process_widget_creation_requests",
}

# Deliberate exceptions, with the reason they are safe.
ALLOWED = {
    # Not an endpoint: it is the heartbeat's own entry point, called from
    # Modules/heartbeat.py on Domoticz's thread.
}


def _endpoint_sources():
    files = sorted(WEBSERVER_DIR.glob("*.py"))
    assert files, "no WebServer sources found - is the test running from the repo root?"
    return files


class TestWebServerDoesNotTouchTheDomoticzWidgetApi(unittest.TestCase):

    def test_no_endpoint_imports_a_widget_api_helper(self):
        offenders = []
        for path in _endpoint_sources():
            if path.name in ALLOWED:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name in FORBIDDEN_NAMES:
                            offenders.append("%s imports %s" % (path.name, alias.name))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[-1] in FORBIDDEN_NAMES:
                            offenders.append("%s imports %s" % (path.name, alias.name))

        self.assertEqual(
            offenders, [],
            "A WebServer endpoint reached for the Domoticz widget API. These handlers run "
            "in a per-client thread (com.py: handle_client) and must queue the work instead "
            "- use Modules.domoCreate.request_widget_creation(). Offenders: %s" % offenders)

    def test_no_endpoint_calls_a_widget_api_helper(self):
        offenders = []
        for path in _endpoint_sources():
            if path.name in ALLOWED:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name in FORBIDDEN_NAMES:
                    offenders.append("%s:%s calls %s" % (path.name, node.lineno, name))

        self.assertEqual(
            offenders, [],
            "A WebServer endpoint called the Domoticz widget API from its own thread. "
            "Queue the work for the heartbeat instead - use "
            "Modules.domoCreate.request_widget_creation(). Offenders: %s" % offenders)

    def test_the_two_known_endpoints_queue_their_request(self):
        # These are the handlers that used to call CreateDomoDevice directly; keep
        # them wired to the queue so the guard above cannot be satisfied by simply
        # dropping the feature.
        for name in ("rest_recreateWidget.py", "rest_change_ModelName.py"):
            source = (WEBSERVER_DIR / name).read_text(encoding="utf-8")
            self.assertIn("request_widget_creation", source,
                          "%s no longer requests a widget creation at all" % name)

    def test_model_change_still_asks_for_the_old_widgets_to_go(self):
        source = (WEBSERVER_DIR / "rest_change_ModelName.py").read_text(encoding="utf-8")
        self.assertIn("remove_existing_widgets=True", source)


if __name__ == "__main__":
    unittest.main()
