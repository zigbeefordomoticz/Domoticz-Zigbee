#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the page the plugin adds to the Domoticz custom menu
(Modules/domoticzCustomMenu.py, written by plugin.py install_Z4D_to_domoticz_custom_ui).

The page pointed to "http://" + location.hostname + ":<Plugin WebUI port>/z4d/",
with the parameter pasted in as it is. A Plugin WebUI port of 127.0.0.1:9440,
the setting advised behind a reverse proxy, gave http://<host>:127.0.0.1:9440/z4d/.
Now an address:port parameter only puts the port in the URL, and a loopback
address (reached through a reverse proxy only) gives the relative /z4d/.
The scheme follows the WebUI (https with a usable certificate); an https
Domoticz page with an http WebUI shows a link instead of a blank frame; and
with the WebUI turned off (Mode4 "None") no page is written.
"""

import json
import re
import shutil
import subprocess

import pytest

from Modules.domoticzCustomMenu import (MIXED_CONTENT_NOTE, OPEN_WEBUI_LINK,
                                        custom_menu_html, is_loopback,
                                        split_webui_port, webui_enabled)


def iframe_src(page):
    """The JavaScript expression the iframe src is computed from."""
    return re.search(r"var src = (.*);\n", page).group(1)


@pytest.mark.parametrize("webui_port, expected", [
    ("9440", (None, "9440")),
    (" 9440 ", (None, "9440")),
    ("127.0.0.1:9440", ("127.0.0.1", "9440")),
    ("192.168.1.10:9441", ("192.168.1.10", "9441")),
    ("localhost:9440", ("localhost", "9440")),
    ("[::1]:9440", ("::1", "9440")),
])
def test_split_webui_port(webui_port, expected):
    assert split_webui_port(webui_port) == expected


@pytest.mark.parametrize("address, expected", [
    (None, False),
    ("", False),
    ("127.0.0.1", True),
    ("127.1.2.3", True),
    ("::1", True),
    ("localhost", True),
    ("LocalHost", True),
    ("0.0.0.0", False),
    ("192.168.1.10", False),
    ("domoticz.lan", False),
])
def test_is_loopback(address, expected):
    assert is_loopback(address) is expected


def test_port_only_points_to_the_domoticz_host():
    """Unchanged behaviour for the default setting."""
    page = custom_menu_html("Zigbee", "9440")
    assert iframe_src(page) == '"http://" + location.hostname + ":" + "9440" + "/z4d/"'


@pytest.mark.parametrize("webui_port", ["9440", "192.168.1.10:9440"])
def test_webui_with_certificate_uses_https(webui_port):
    page = custom_menu_html("Zigbee", webui_port, webui_tls=True)
    assert iframe_src(page) == '"https://" + location.hostname + ":" + "9440" + "/z4d/"'


def test_loopback_ignores_the_webui_certificate():
    """Behind the proxy, the browser talks to the proxy: the page's own scheme applies."""
    page = custom_menu_html("Zigbee", "127.0.0.1:9440", webui_tls=True)
    assert iframe_src(page) == '"/z4d/"'


@pytest.mark.parametrize("webui_port, expected", [
    ("9440", True),
    ("127.0.0.1:9440", True),
    ("None", False),
    ("none", False),
    ("", False),
])
def test_webui_enabled(webui_port, expected):
    assert webui_enabled(webui_port) is expected


def test_lan_address_keeps_only_the_port():
    page = custom_menu_html("Zigbee", "192.168.1.10:9440")
    assert iframe_src(page) == '"http://" + location.hostname + ":" + "9440" + "/z4d/"'
    assert "192.168.1.10" not in page


@pytest.mark.parametrize("webui_port", ["127.0.0.1:9440", "localhost:9440", "[::1]:9440"])
def test_loopback_address_uses_the_proxy_path(webui_port):
    page = custom_menu_html("Zigbee", webui_port)
    assert iframe_src(page) == '"/z4d/"'
    assert "9440" not in page


def test_page_layout():
    page = custom_menu_html("Zigbee", "9440")
    assert page.startswith(
        '<iframe id="Zigbee" style="width:100%;height:800px;overflow:scroll;">\n'
        "</iframe>\n"
        "\n"
        "<script>\n"
        "(function () {\n"
        '  var frame = document.getElementById("Zigbee");\n'
        '  var src = "http://" + location.hostname + ":" + "9440" + "/z4d/";\n'
    )
    assert page.endswith("})();\n</script>\n")
    assert page.count("<script>") == 1


def test_hardware_name_is_escaped():
    name = 'Zig"bee</script><b>'
    page = custom_menu_html(name, "9440")
    assert 'id="Zig&quot;bee&lt;/script&gt;&lt;b&gt;"' in page
    assert 'getElementById("Zig\\"bee<\\/script><b>")' in page
    assert page.count("</script>") == 1


# The page's script, run in Node against a minimal DOM: which branch the
# browser takes for each Domoticz scheme / WebUI scheme pair.
NODE_HARNESS = r"""
const page = require("fs").readFileSync(0, "utf8");
const script = page.split("<script>\n")[1].split("</script>")[0];
const [protocol, hostname] = process.argv.slice(1);
function element(tag) {
  return { tag: tag, children: [], appendChild(c) { this.children.push(c); } };
}
const frame = element("iframe");
const parent = { replaced: null, replaceChild(n, o) { if (o === frame) this.replaced = n; } };
frame.parentNode = parent;
const document = {
  getElementById(id) { return id === "Zigbee" ? frame : null; },
  createElement: element,
};
const location = { protocol: protocol, hostname: hostname };
new Function("document", "location", script)(document, location);
const shown = parent.replaced;
console.log(JSON.stringify({
  src: frame.src || null,
  note: shown ? shown.textContent : null,
  link: shown ? { href: shown.children[0].href, target: shown.children[0].target,
                  rel: shown.children[0].rel, text: shown.children[0].textContent } : null,
}));
"""


def run_page(page, protocol, hostname="domoticz.lan"):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run(
        [node, "-e", NODE_HARNESS, protocol, hostname],
        input=page, capture_output=True, text=True, check=True, timeout=30,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("protocol, webui_tls, expected_src", [
    ("http:", False, "http://domoticz.lan:9440/z4d/"),
    ("http:", True, "https://domoticz.lan:9440/z4d/"),
    ("https:", True, "https://domoticz.lan:9440/z4d/"),
])
def test_browser_loads_the_frame(protocol, webui_tls, expected_src):
    shown = run_page(custom_menu_html("Zigbee", "9440", webui_tls=webui_tls), protocol)
    assert shown == {"src": expected_src, "note": None, "link": None}


def test_https_domoticz_with_http_webui_shows_a_link():
    """The browser would block the http frame: open the WebUI in a new tab instead."""
    shown = run_page(custom_menu_html("Zigbee", "9440"), "https:")
    assert shown["src"] is None
    assert shown["note"] == MIXED_CONTENT_NOTE
    assert shown["link"] == {
        "href": "http://domoticz.lan:9440/z4d/",
        "target": "_blank",
        "rel": "noopener",
        "text": OPEN_WEBUI_LINK,
    }


@pytest.mark.parametrize("protocol", ["http:", "https:"])
def test_proxy_path_is_always_framed(protocol):
    shown = run_page(custom_menu_html("Zigbee", "127.0.0.1:9440"), protocol)
    assert shown == {"src": "/z4d/", "note": None, "link": None}
