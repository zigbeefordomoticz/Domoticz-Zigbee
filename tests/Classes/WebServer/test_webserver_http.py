#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP behaviour of the WebUI server: file serving, cookies and caching.

Classes/WebServer/com.py is a raw-socket HTTP server bound to 0.0.0.0:9440 with
no authentication, so what it serves and which headers it sends are the whole
security boundary. These tests drive the real request path --
parse_http_request() -> onMessage() -> sendResponse() -- against a fake socket
and assert on the bytes that would go on the wire.
"""

import types
from dataclasses import dataclass

import pytest

from Classes.WebServer.com import decode_http_data, parse_http_request
from Classes.WebServer.onMessage import onMessage
from Classes.WebServer.sendresponse import sendResponse

HASHED_BUNDLE = "main.0123456789abcdef.js"
SECRET = b"TOP-SECRET-OUTSIDE-WWW"


class FakeSocket:
    def __init__(self):
        self.sent = b""

    def sendall(self, data):
        self.sent += data

    def close(self):
        pass


class FakeWebServer:
    """The attributes of Classes.WebServer.WebServer that the request path reads."""

    def __init__(self, home, **conf):
        self.homedirectory = str(home) + "/"
        self.pluginconf = types.SimpleNamespace(pluginConf={
            "enableKeepalive": 1,
            "enableCache": 1,
            "enableGzip": 0,
            "enableDeflate": 0,
            "enableChunk": 0,
            "WebUIReactTime": 0,
            "pluginLogs": str(home / "Logs"),
            **conf,
        })
        self.logs = []

    def logging(self, level, message):
        self.logs.append((level, message))

    def sendResponse(self, connection, response, AcceptEncoding=None):
        sendResponse(self, connection, response, AcceptEncoding)

    def do_rest(self, connection, verb, data, version, command, parameters):
        raise AssertionError(f"unexpected REST call {command}")


@dataclass
class Reply:
    status: int
    headers: dict
    body: bytes


def get(ws, path, headers=None):
    raw = f"GET {path} HTTP/1.1\r\nHost: pi:9440\r\n"
    raw += "".join(f"{name}: {value}\r\n" for name, value in (headers or {}).items())
    raw += "\r\n"
    method, url, request_headers, body = parse_http_request(raw)
    sock = FakeSocket()
    onMessage(ws, sock, decode_http_data(ws, method, url, request_headers, body.encode("utf-8")))

    head, _, payload = sock.sent.partition(b"\r\n\r\n")
    status_line, *header_lines = head.decode("utf-8").split("\r\n")
    response_headers = {}
    for line in header_lines:
        name, value = line.split(":", 1)
        response_headers[name.strip()] = value.strip()
    return Reply(int(status_line.split()[1]), response_headers, payload)


@pytest.fixture
def home(tmp_path):
    (tmp_path / "www" / "z4d" / "assets").mkdir(parents=True)
    (tmp_path / "www" / "z4d" / "index.html").write_bytes(b"<html>index</html>")
    (tmp_path / "www" / "z4d" / HASHED_BUNDLE).write_bytes(b"console.log(1)")
    (tmp_path / "www" / "z4d" / "assets" / "z4d_logo.png").write_bytes(b"\x89PNG")
    (tmp_path / "Logs").mkdir()
    (tmp_path / "Logs" / "PluginZigbee_01.log").write_bytes(b"plugin log line")
    (tmp_path / "secret.txt").write_bytes(SECRET)
    return tmp_path


@pytest.fixture
def ws(home):
    return FakeWebServer(home)


# ─── Static files stay under www/ ─────────────────────────────────────────────

def test_serves_a_file_under_www(ws):
    reply = get(ws, "/z4d/" + HASHED_BUNDLE)
    assert reply.status == 200
    assert reply.body == b"console.log(1)"


def test_query_string_is_not_part_of_the_filename(ws):
    reply = get(ws, "/z4d/" + HASHED_BUNDLE + "?v=1")
    assert reply.body == b"console.log(1)"


@pytest.mark.parametrize("path", ["/../secret.txt", "/z4d/../../secret.txt", "/z4d/assets/../../../secret.txt"])
def test_dot_dot_cannot_leave_www(ws, path):
    # Refused and answered, like any wrong path, with the WebUI index.html
    reply = get(ws, path)
    assert reply.body == b"<html>index</html>"
    assert SECRET not in reply.body
    assert any("outside of www/" in message for _level, message in ws.logs)


def test_dot_dot_inside_www_is_allowed(ws):
    reply = get(ws, "/z4d/assets/../index.html")
    assert reply.status == 200
    assert reply.body == b"<html>index</html>"
