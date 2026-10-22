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

import gzip
import types
from dataclasses import dataclass

import pytest

from Classes.WebServer.com import (decode_http_data, handle_client,
                                   parse_http_request)
from Classes.WebServer.onMessage import onMessage
from Classes.WebServer.sendresponse import sendResponse

HASHED_BUNDLE = "main.0123456789abcdef.js"
SECRET = b"TOP-SECRET-OUTSIDE-WWW"
# Domoticz session cookie: browsers send it to :9440 too, cookies are not scoped by port
DOMOTICZ_COOKIE = "DMZSID=0123abcd_c2VjcmV0dG9rZW4.1790000000"


class FakeSocket:
    def __init__(self):
        self.sent = b""

    def sendall(self, data):
        self.sent += data

    def close(self):
        pass


class FakeClientSocket(FakeSocket):
    """A client connection that sends one request, then closes."""

    def __init__(self, request):
        super().__init__()
        self.pending = [request.encode("utf-8")]

    def settimeout(self, timeout):
        pass

    def recv(self, size):
        return self.pending.pop(0) if self.pending else b""


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

    def onMessage(self, connection, data):
        onMessage(self, connection, data)


@dataclass
class Reply:
    status: int
    headers: dict
    body: bytes
    raw: bytes


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
    return Reply(int(status_line.split()[1]), response_headers, payload, sock.sent)


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


# ─── /download serves the plugin log files only ───────────────────────────────

def _log_url(home, name="PluginZigbee_01.log"):
    # The URL rest_logging.rest_logPlugin() hands to the WebUI
    return "/download" + str(home / "Logs") + "/" + name


def test_download_serves_the_plugin_log(ws, home):
    reply = get(ws, _log_url(home))
    assert reply.status == 200
    assert reply.body == b"plugin log line"


@pytest.mark.parametrize("target", [
    lambda home: "/download/etc/hosts",
    lambda home: "/download" + str(home / "secret.txt"),
    lambda home: _log_url(home, "../secret.txt"),
    lambda home: "/download",
])
def test_download_refuses_anything_outside_the_log_directory(ws, home, target):
    # Refused and answered, like any wrong path, with the WebUI index.html
    reply = get(ws, target(home))
    assert reply.body == b"<html>index</html>"
    assert any("not a plugin log file" in message for _level, message in ws.logs)


def test_download_of_a_missing_log_falls_back_to_index_html(ws, home):
    reply = get(ws, _log_url(home, "PluginZigbee_99.log"))
    assert reply.body == b"<html>index</html>"


def test_download_refused_when_the_log_directory_is_unknown(home):
    ws = FakeWebServer(home, pluginLogs="")
    assert get(ws, _log_url(home)).body == b"<html>index</html>"


# ─── The Domoticz session cookie is never sent back ───────────────────────────

@pytest.mark.parametrize("path", ["/z4d/index.html", "/z4d/devices", "/z4d/" + HASHED_BUNDLE])
def test_request_cookie_is_not_echoed_in_the_response(ws, path):
    # A response "Cookie" header made DMZSID (HttpOnly) readable by any script on :9440
    reply = get(ws, path, {"Cookie": DOMOTICZ_COOKIE})
    assert reply.status == 200
    assert "Cookie" not in reply.headers
    assert b"DMZSID" not in reply.raw


# ─── Credentials never reach the plugin log ───────────────────────────────────

CREDENTIALS = {"Cookie": DOMOTICZ_COOKIE, "Authorization": "Basic YWRtaW46c2VjcmV0"}


def _logged(ws):
    return "\n".join(message for _level, message in ws.logs)


def test_onmessage_debug_log_redacts_credentials(ws):
    get(ws, "/z4d/index.html", CREDENTIALS)
    assert "/z4d/index.html" in _logged(ws)
    assert "DMZSID" not in _logged(ws)
    assert "YWRtaW46c2VjcmV0" not in _logged(ws)


@pytest.mark.parametrize("cookie_header", ["Cookie", "cookie", "COOKIE"])
def test_handle_client_debug_log_redacts_credentials(ws, cookie_header):
    ws.clients, ws.webui_running = {}, True
    request = (f"GET /z4d/index.html HTTP/1.1\r\nHost: pi:9440\r\n{cookie_header}: {DOMOTICZ_COOKIE}\r\n"
               "Authorization: Basic YWRtaW46c2VjcmV0\r\n\r\n")
    client = FakeClientSocket(request)

    handle_client(ws, client, ("192.0.2.1", 50000))

    assert client.sent.startswith(b"HTTP/1.1 200 OK")
    assert "<redacted>" in _logged(ws)
    assert "DMZSID" not in _logged(ws)
    assert "YWRtaW46c2VjcmV0" not in _logged(ws)


# ─── Header names are case-insensitive ────────────────────────────────────────

def test_parse_http_request_canonicalises_header_names():
    method, path, headers, body = parse_http_request(
        "POST /rest-z4d/1/x HTTP/1.1\r\nhost: pi\r\ncontent-length: 5\r\nIF-MODIFIED-SINCE: x\r\n\r\nhello")
    assert headers == {"Host": "pi", "Content-Length": "5", "If-Modified-Since": "x"}
    assert body == "hello"


@pytest.mark.parametrize("name", ["Accept-Encoding", "accept-encoding"])
def test_gzip_is_negotiated_whatever_the_header_case(home, name):
    ws = FakeWebServer(home, enableGzip=1)
    reply = get(ws, "/z4d/" + HASHED_BUNDLE, {name: "gzip, deflate"})
    assert reply.headers["Content-Encoding"] == "gzip"
    assert gzip.decompress(reply.body) == b"console.log(1)"
