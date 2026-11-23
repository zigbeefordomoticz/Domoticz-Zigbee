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
* otherwise: http://<address the browser used for Domoticz>:<port>/z4d/.
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


def custom_menu_html(hardware_name, webui_port):
    """The custom menu page for this hardware and Plugin WebUI port."""
    address, port = split_webui_port(webui_port)
    if is_loopback(address):
        src = _js_string("/z4d/")
    else:
        src = '"http://" + location.hostname + ":" + %s + "/z4d/"' % _js_string(port)

    return (
        '<iframe id="%s" style="width:100%%;height:800px;overflow:scroll;">\n'
        "</iframe>\n"
        "\n"
        "<script>\n"
        "document.getElementById(%s).src = %s;\n"
        "</script>\n"
    ) % (html.escape(hardware_name, quote=True), _js_string(hardware_name), src)
