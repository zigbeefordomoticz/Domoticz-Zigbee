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

The Selector is a second unit of the DeviceID of the group: unit 1 is the widget of the
group, unit 2 the Selector. GrpDomoticz owns these units, this only knows the levels.
The group loses its members with the last of the two, see GrpServices.FullRemoveOfGroup.

A level is a position in Domoticz: the name at index n is level n * 10. Scripts and
events hold a level, so a scene keeps its level for life, and a deleted one leaves a
free slot instead of moving the next ones. The actions of the levels are kept for the
same reason, and the other options are the user's. They must all be sent back, as
Domoticz replaces the options as a whole.
"""

from Modules.domoticzAbstractLayer import (domo_delete_widget,
                                           domo_read_nValue_sValue,
                                           domo_read_Options, domo_update_api)

SCENE_LOG = "Scene"

WIDGET_CREATION_FAILED = -1

LEVEL_STEP = 10
OFF_NAME = "Off"
# What a free slot shows: choosing it does nothing
FREE_LEVEL_NAME = "-"
# Buttons: a click always sends the command. A scene can be recalled again, once lamps
# have moved, and the dropdown (1) of the dashboard only sends one when the level changes
DEFAULT_OPTIONS = {"LevelOffHidden": "false", "SelectorStyle": "0"}


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

    @property
    def _groupmgt(self):
        return self.plugin.groupmgt

    def _unit(self, GroupId):
        return self._groupmgt.scene_selector_unit(GroupId)

    def sync(self, GroupId, group_name, levels):
        """Create the Selector of a group, or bring it to these {level: name}."""
        names = _level_names(levels)
        unit = self._unit(GroupId)
        if unit is None:
            self._create(GroupId, group_name, names)
            return

        current = domo_read_Options(self.plugin, self._devices, GroupId, unit) or {}
        options = _options(current, names)
        shown = self._shown_level(GroupId, unit)
        level = shown if shown in levels else 0
        if options != current or level != shown:
            # A list of names that changed is not an event: the triggers stay quiet
            self.logging("Debug", "sync - %s/%s levels %s, level %s" % (GroupId, unit, options["LevelNames"], level), GroupId)
            domo_update_api(self.plugin, self._devices, GroupId, unit, *_level_values(level), Options=options, SuppressTriggers=True)

    def _create(self, GroupId, group_name, names):
        self.logging("Debug", "create - %s levels %s" % (GroupId, names), GroupId)
        idx = self._groupmgt.create_scene_selector(GroupId, "%s - Scenes" % (group_name or GroupId), _options(DEFAULT_OPTIONS, names))
        if idx == WIDGET_CREATION_FAILED:
            self.logging("Log", "The Selector of the scenes of group %s was not created: scenes stay available from the WebUI" % GroupId, GroupId)

    def _shown_level(self, GroupId, unit):
        _, sValue = domo_read_nValue_sValue(self.plugin, self._devices, GroupId, unit)
        return int(sValue) if str(sValue).isdigit() else 0

    def show(self, GroupId, level):
        """Set the level, with the triggers: this is what events and scripts wait for."""
        unit = self._unit(GroupId)
        if unit is not None:
            domo_update_api(self.plugin, self._devices, GroupId, unit, *_level_values(level))

    def clear(self, GroupId):
        """The lights left the scene. Not an event: nobody chose Off, and it may carry actions."""
        unit = self._unit(GroupId)
        if unit is not None:
            domo_update_api(self.plugin, self._devices, GroupId, unit, *_level_values(0), SuppressTriggers=True)

    def level(self, GroupId):
        """The level shown, 0 without a Selector."""
        unit = self._unit(GroupId)
        return 0 if unit is None else self._shown_level(GroupId, unit)

    def remove(self, GroupId):
        """No scene left. When the widget of the group went first, this was what kept the group."""
        unit = self._unit(GroupId)
        if unit is None:
            return
        self.logging("Debug", "remove - %s/%s" % (GroupId, unit), GroupId)
        domo_delete_widget(self.plugin, self._devices, GroupId, unit)
        if self._groupmgt.group_widget_unit(GroupId) is None:
            self._groupmgt.FullRemoveOfGroup(None, GroupId)

    def group_off(self, GroupId):
        """The Off level: the group is switched off as from its own widget, which may be gone."""
        self._groupmgt.processCommand(self._groupmgt.group_widget_unit(GroupId), GroupId, "Off", 0, "")
