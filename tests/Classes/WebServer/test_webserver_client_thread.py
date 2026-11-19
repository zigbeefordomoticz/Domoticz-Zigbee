#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_webserver_client_thread.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit test for the name of the thread serving a WebUI connection
(Classes/WebServer/com.py: server_loop).

Several instances of the plugin can run in one Domoticz. Every plugin thread carries the
HardwareID of its instance in its name, so the thread audit after onStart() and the
thread name in each log line tell the instances apart. The thread server_loop starts for
each accepted connection follows the same rule.

Run with:
    pytest tests/Classes/WebServer/test_webserver_client_thread.py -v
"""

import socket
import threading
from types import SimpleNamespace
from unittest.mock import patch

# tests/conftest.py installs the DomoticzEx fake at import time, before collection
import Classes.WebServer.com as com  # noqa: E402

HARDWARE_ID = 3


class _OneClientServer:
    """Accept one client, then stop the loop on the next accept()."""

    def __init__(self, ws):
        self.ws = ws
        self.accepted = False

    def accept(self):
        if self.accepted:
            self.ws.webui_running = False
            raise socket.timeout()
        self.accepted = True
        return object(), ("127.0.0.1", 50000)

    def close(self):
        pass


def test_client_thread_carries_the_hardware_id():
    ws = SimpleNamespace(hardwareID=HARDWARE_ID, client_threads=[], logging=lambda *a, **k: None)
    ws.server = _OneClientServer(ws)

    names = []
    served = threading.Event()

    def fake_handle_client(_self, _sock, _addr):
        names.append(threading.current_thread().name)
        served.set()

    with patch.object(com, "handle_client", fake_handle_client), \
         patch.object(com, "set_keepalive", lambda sock: None), \
         patch.object(com, "close_all_clients", lambda self: None):
        com.server_loop(ws)

    assert served.wait(2)
    assert names == [f"ZigbeeWebUIClient_{HARDWARE_ID}"]
