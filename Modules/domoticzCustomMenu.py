#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""The page the plugin adds to the Domoticz custom menu (www/templates/<hardware name>.html).

The page is an iframe on the plugin WebUI. Where it points depends on the
*Plugin WebUI port* parameter (Mode4), which is either a port ("9440") or
an address and a port ("127.0.0.1:9440"):

* the WebUI listens on a loopback address: it can only be reached through a
  reverse proxy that serves it under /z4d/ next to Domoticz, so the iframe
  uses the relative /z4d/ of the page's own address;
* otherwise: <scheme>://<address the browser used for Domoticz>:<port>/z4d/,
  https when the WebUI has a usable certificate, http otherwise.

A browser does not show an http page inside an https one. When Domoticz is
opened over https and the WebUI is http, the page shows a link that opens the
WebUI in a new tab instead of a blank frame.

With the WebUI turned off (Mode4 neither a port nor address:port, e.g.
"None"), there is nothing to point to and no page is written.
"""

import html
import ipaddress
import json

LOOPBACK_NAMES = {"localhost", "ip6-localhost"}


def split_webui_port(webui_port):
    """Return (address, port) from the Plugin WebUI port parameter; address is None for a port alone."""
    webui_port = webui_port.strip()
    if ":" not in webui_port:
        return None, webui_port
    address, _, port = webui_port.rpartition(":")
    return address.strip().strip("[]"), port.strip()


def is_loopback(address):
    if not address:
        return False
    if address.lower() in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


def _js_string(value):
    """A JavaScript string literal that cannot close the <script> element."""
    return json.dumps(value).replace("</", "<\\/")


def webui_enabled(webui_port):
    """The Plugin WebUI port parameter starts the WebUI (same test as plugin.py onStart)."""
    return webui_port.isdigit() or ":" in webui_port


MIXED_CONTENT_NOTE = (
    "Domoticz is opened over https and the plugin WebUI is served over http: "
    "the browser does not show the WebUI inside this page. "
)
OPEN_WEBUI_LINK = "Open the Zigbee for Domoticz WebUI"


def custom_menu_html(hardware_name, webui_port, webui_tls=False):
    """The custom menu page for this hardware and Plugin WebUI port; webui_tls when the WebUI serves https."""
    address, port = split_webui_port(webui_port)
    if is_loopback(address):
        src = _js_string("/z4d/")
    else:
        scheme = "https://" if webui_tls else "http://"
        src = '%s + location.hostname + ":" + %s + "/z4d/"' % (_js_string(scheme), _js_string(port))

    return (
        '<iframe id="%(id)s" style="width:100%%;height:800px;overflow:scroll;">\n'
        "</iframe>\n"
        "\n"
        "<script>\n"
        "(function () {\n"
        "  var frame = document.getElementById(%(js_id)s);\n"
        "  var src = %(src)s;\n"
        '  if (location.protocol === "https:" && src.indexOf("http:") === 0) {\n'
        '    var note = document.createElement("p");\n'
        "    note.textContent = %(note)s;\n"
        '    var link = document.createElement("a");\n'
        "    link.href = src;\n"
        '    link.target = "_blank";\n'
        '    link.rel = "noopener";\n'
        "    link.textContent = %(link)s;\n"
        "    note.appendChild(link);\n"
        "    frame.parentNode.replaceChild(note, frame);\n"
        "  } else {\n"
        "    frame.src = src;\n"
        "  }\n"
        "})();\n"
        "</script>\n"
    ) % {
        "id": html.escape(hardware_name, quote=True),
        "js_id": _js_string(hardware_name),
        "src": src,
        "note": _js_string(MIXED_CONTENT_NOTE),
        "link": _js_string(OPEN_WEBUI_LINK),
    }
