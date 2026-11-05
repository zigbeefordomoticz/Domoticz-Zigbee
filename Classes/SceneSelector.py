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
"""
The Domoticz side of the native Zigbee scenes: one Selector Switch per group with
scenes, a scene being a level. SceneManagement decides what the levels are, this only
talks to Domoticz, and only from the Domoticz thread.

The Selector has a DeviceID of its own, and is not a second unit of the group's:
onDeviceRemoved takes any unit of a group DeviceID for the group itself, so deleting
the Selector would empty the group.

A level is a position in Domoticz: the name at index n is level n * 10. Scripts and
events hold a level, so a scene keeps its level for life, and a deleted one leaves a
free slot instead of moving the next ones. The actions of the levels are kept for the
same reason, and the other options are the user's. They must all be sent back, as
Domoticz replaces the options as a whole.
"""

from Classes.AdminWidgets import Z4D_DEVICEID_SCENE_SELECTOR
from Modules.domoticzAbstractLayer import (
    domo_create_api, domo_delete_widget, domo_read_nValue_sValue,
    domo_read_Options, domo_update_api, find_first_unit_widget_from_deviceID)

SCENE_LOG = "Scene"

SELECTOR_UNIT = 1
SELECTOR_TYPE, SELECTOR_SUBTYPE, SELECTOR_SWITCHTYPE = 244, 62, 18
WIDGET_CREATION_FAILED = -1

LEVEL_STEP = 10
OFF_NAME = "Off"
# What a free slot shows: choosing it does nothing
FREE_LEVEL_NAME = "-"
DEFAULT_OPTIONS = {"LevelOffHidden": "false", "SelectorStyle": "1"}


def _level_names(levels):
    """The LevelNames entries, from {level: name}."""
    return [OFF_NAME] + [levels.get(level, FREE_LEVEL_NAME) for level in range(LEVEL_STEP, max(levels) + LEVEL_STEP, LEVEL_STEP)]


def _options(current, names):
    """The options of a Selector with these names, the rest as it is."""
    actions = current.get("LevelActions", "").split("|")
    actions = (actions + [""] * len(names))[:len(names)]
    return {**current, "LevelNames": "|".join(names), "LevelActions": "|".join(actions)}


def _level_values(level):
    """nValue and sValue of a level, as the Selectors of the plugin write them."""
    return level // LEVEL_STEP, str(level)


class SceneSelector:

    def __init__(self, plugin):
        self.plugin = plugin

    def logging(self, logType, message, GroupId):
        self.plugin.log.logging(SCENE_LOG, logType, message, GroupId)

    @property
    def _devices(self):
        return self.plugin.groupmgt.Devices

    @staticmethod
    def is_selector(DeviceID):
        return DeviceID.startswith(Z4D_DEVICEID_SCENE_SELECTOR)

    @staticmethod
    def group_of(DeviceID):
        return DeviceID[len(Z4D_DEVICEID_SCENE_SELECTOR):]

    @staticmethod
    def device_id(GroupId):
        return Z4D_DEVICEID_SCENE_SELECTOR + GroupId

    def _unit(self, GroupId):
        return find_first_unit_widget_from_deviceID(self.plugin, self._devices, self.device_id(GroupId))

    def sync(self, GroupId, group_name, levels):
        """Create the Selector of a group, or bring it to these {level: name}."""
        device_id = self.device_id(GroupId)
        names = _level_names(levels)
        unit = self._unit(GroupId)
        if unit is None:
            self._create(GroupId, group_name, names)
            return

        current = domo_read_Options(self.plugin, self._devices, device_id, unit) or {}
        options = _options(current, names)
        shown = self._shown_level(device_id, unit)
        level = shown if shown in levels else 0
        if options != current or level != shown:
            # A list of names that changed is not an event: the triggers stay quiet
            self.logging("Debug", "sync - %s levels %s, level %s" % (device_id, options["LevelNames"], level), GroupId)
            domo_update_api(self.plugin, self._devices, device_id, unit, *_level_values(level), Options=options, SuppressTriggers=True)

    def _create(self, GroupId, group_name, names):
        device_id = self.device_id(GroupId)
        self.logging("Debug", "create - %s levels %s" % (device_id, names), GroupId)
        idx = domo_create_api(
            self.plugin, self._devices, device_id, SELECTOR_UNIT, "%s - Scenes" % (group_name or GroupId),
            Type_=SELECTOR_TYPE, Subtype_=SELECTOR_SUBTYPE, Switchtype_=SELECTOR_SWITCHTYPE,
            widgetOptions=_options(DEFAULT_OPTIONS, names),
        )
        if idx == WIDGET_CREATION_FAILED:
            self.logging("Log", "The Selector of the scenes of group %s was not created: scenes stay available from the WebUI" % GroupId, GroupId)

    def _shown_level(self, device_id, unit):
        _, sValue = domo_read_nValue_sValue(self.plugin, self._devices, device_id, unit)
        return int(sValue) if str(sValue).isdigit() else 0

    def show(self, GroupId, level):
        """Set the level, with the triggers: this is what events and scripts wait for."""
        unit = self._unit(GroupId)
        if unit is not None:
            domo_update_api(self.plugin, self._devices, self.device_id(GroupId), unit, *_level_values(level))

    def remove(self, GroupId):
        unit = self._unit(GroupId)
        if unit is not None:
            self.logging("Debug", "remove - %s" % self.device_id(GroupId), GroupId)
            domo_delete_widget(self.plugin, self._devices, self.device_id(GroupId), unit)

    def group_off(self, GroupId):
        """The Off level: the group is switched off as from its own widget."""
        unit = find_first_unit_widget_from_deviceID(self.plugin, self._devices, GroupId)
        self.plugin.groupmgt.processCommand(unit, GroupId, "Off", 0, "")
