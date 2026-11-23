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
"""

import re

import pytest

from Modules.domoticzCustomMenu import (custom_menu_html, is_loopback,
                                        split_webui_port)


def iframe_src(page):
    """The JavaScript expression assigned to the iframe src."""
    return re.search(r"\.src = (.*);\n", page).group(1)


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
    assert page == (
        '<iframe id="Zigbee" style="width:100%;height:800px;overflow:scroll;">\n'
        "</iframe>\n"
        "\n"
        "<script>\n"
        'document.getElementById("Zigbee").src = "http://" + location.hostname + ":" + "9440" + "/z4d/";\n'
        "</script>\n"
    )


def test_hardware_name_is_escaped():
    name = 'Zig"bee</script><b>'
    page = custom_menu_html(name, "9440")
    assert 'id="Zig&quot;bee&lt;/script&gt;&lt;b&gt;"' in page
    assert 'getElementById("Zig\\"bee<\\/script><b>")' in page
    assert page.count("</script>") == 1
