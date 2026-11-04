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

# Error codes put in the context of every Group Management Error log ({"Error code": "GRPxxyy", ...}).
# xx is the area, yy the number within it. Never reuse or renumber a code: users quote them.
GRP_ERROR_CODES = {
    # 00 - Domoticz widget of a group
    "GRP0001": "Group widget not created: group name or id is empty",
    "GRP0002": "Domoticz refused to create the group widget",
    "GRP0003": "Group widget not renamed: group name or id is empty",
    "GRP0004": "Group widget not updated: group id is empty",
    # 01 - group members and state
    "GRP0101": "Group to update is not in ListOfGroups",
    "GRP0102": "Group member is not in ListOfDevices and could not be found by its IEEE",
    "GRP0103": "Group member without IEEE is not in ListOfDevices",
    "GRP0104": "Group member is not in ListOfDevices and could not be found by its IEEE",
    "GRP0105": "Group member endpoint does not exist on the device",
    "GRP0106": "Group member has no widget",
    "GRP0107": "Group member is neither in ListOfDevices nor in IEEE2NWK",
    # 02 - membership responses from the devices
    "GRP0201": "Add Group response of an unexpected length",
    "GRP0202": "Add Group response from an unknown device",
    "GRP0203": "View Group response from an unknown device",
    "GRP0204": "Get Group Membership response from an unknown device",
    "GRP0205": "Remove Group response of an unexpected length",
    "GRP0206": "Remove Group response from an unknown device",
    # 03 - IKEA Tradfri 5 buttons remote
    "GRP0301": "Remote of a group is no longer known",
    "GRP0302": "Remote is not associated to any group",
    "GRP0303": "Group has no Tradfri Remote entry",
    "GRP0304": "Tradfri Remote entry of the group has no Color Mode",
    "GRP0305": "Color Mode of the Tradfri Remote is not defined",
    # 04 - migration of the groups list
    "GRP0401": "Tradfri Remote not migrated: device and IEEE unknown, removed from the group",
    "GRP0402": "Group device dropped at migration: unexpected format",
    "GRP0403": "Group device dropped at migration: device or IEEE unknown",
    "GRP0404": "Group device at migration is not in ListOfDevices",
    # 05 - WebUI / REST API
    "GRP0501": "Group not created: no group id available",
}


class GroupRequestError(Exception):
    """A request refused before anything changes. code is what REST returns, not one of the codes above."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code
