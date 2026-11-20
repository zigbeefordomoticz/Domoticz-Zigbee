#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Green Power device types (Conf/ZGPmodel/<model name>.json).

Most Green Power devices (GPD) tell nothing about themselves when they are
commissioned: no manufacturer, no model, no command list, only a GP Device
ID (0x02 "On/Off Switch" for a switch that also dims). The user picks the
type on the Green Power page of Admin > Provisionning before pairing, and the
GPD commissioned in that window gets it (store record "RequestedModel").

    {
        "Description": "On/Off switch with dimming",   shown in the WebUI
        "Order": 2,                                     list order in the WebUI
        "Ep": {"01": {"Type": "GenericLvlControl"}},    widgets, as a certified JSON
        "Commands": {"20": ["0008", "off"], ...}        GPD command id (2 hex) ->
                                                        [cluster, value] given to
                                                        maj_domo_widgets()
    }

A command key can also carry the command payload, "69/04": GPDs that send
the same command for every button tell the button in the payload (8-bit
vector press 0x69 of a 4-button switch: one bit per button). The key with
the payload wins over the bare command id. A target can name the endpoint of
the widget it updates, [cluster, value, ep] (an endpoint of "Ep"); without
it, every widget of the GPD is updated. The endpoints are the plugin's own
(f1, f2, ...): a GPD has none.

The file name, without .json, is the model name. Loaded once at startup into
self.GreenPowerModels; a file that does not follow this shape is logged as an
Error and left out.
"""

import json
import re
from pathlib import Path

GP_MODELS_FOLDER = "ZGPmodel"
GP_MODELS_ATTRIBUTE = "GreenPowerModels"

_HEX2 = re.compile(r"[0-9a-f]{2}")
_HEX4 = re.compile(r"[0-9a-f]{4}")
# GPD command id, optionally followed by its payload: "20", "69/04"
_COMMAND_KEY = re.compile(r"[0-9a-f]{2}(/([0-9a-f]{2})+)?")


def _model_error(conf):
    """Why a device type definition is not usable, or None."""
    if not isinstance(conf, dict):
        return "not a JSON object"
    ep = conf.get("Ep")
    if not isinstance(ep, dict) or not ep:
        return "no Ep"
    for ep_id, ep_conf in ep.items():
        if not _HEX2.fullmatch(str(ep_id)) or not isinstance(ep_conf, dict) or not ep_conf.get("Type"):
            return "Ep %s: needs a 2-hex endpoint and a Type" % ep_id
    commands = conf.get("Commands")
    if not isinstance(commands, dict) or not commands:
        return "no Commands"
    for command_id, target in commands.items():
        if not _COMMAND_KEY.fullmatch(str(command_id)):
            return "Commands: %s is not a 2-hex GPD command id, optionally /payload in hex" % command_id
        if not (isinstance(target, list) and len(target) in (2, 3) and _HEX4.fullmatch(str(target[0])) and isinstance(target[1], str)):
            return "Commands %s: needs [cluster (4 hex), value] or [cluster, value, ep]" % command_id
        if len(target) == 3 and target[2] not in ep:
            return "Commands %s: ep %s is not in Ep" % (command_id, target[2])
    return None


def load_gp_models(self, config_folder=None):
    """Load Conf/ZGPmodel/*.json into self.GreenPowerModels {model name: definition}."""
    models = {}
    setattr(self, GP_MODELS_ATTRIBUTE, models)
    folder = Path(config_folder if config_folder is not None else self.pluginconf.pluginConf["pluginConfig"]) / GP_MODELS_FOLDER
    if not folder.is_dir():
        return models

    for path in sorted(folder.glob("*.json")):
        try:
            conf = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            self.log.logging("GreenPower", "Error", "Green Power device type %s not loaded: %s" % (path.name, e), None, {"Error code": "GPMODEL-LOAD-01", "File": path.name})
            continue
        error = _model_error(conf)
        if error:
            self.log.logging("GreenPower", "Error", "Green Power device type %s not loaded: %s" % (path.name, error), None, {"Error code": "GPMODEL-LOAD-02", "File": path.name})
            continue
        models[path.stem] = conf

    self.log.logging("GreenPower", "Status", "Z4D loads %s Green Power device type(s)" % len(models))
    return models


def gp_models(self):
    return getattr(self, GP_MODELS_ATTRIBUTE, None) or {}


def gp_model_list(self):
    """The device types for the WebUI, in their Order."""
    return [
        {"Name": name, "Description": conf.get("Description", name), "Order": conf.get("Order", 99),
         "Widgets": [ep_conf["Type"] for ep_conf in conf["Ep"].values()]}
        for name, conf in sorted(gp_models(self).items(), key=lambda item: (item[1].get("Order", 99), item[0]))
    ]


def gp_model_command(self, model_name, command_id, payload=""):
    """
    (cluster, value, ep) for a GPD command under a device type, None when the
    type does not map it. ep is None when the target names no endpoint (every
    widget). The key with the payload ("69/04") wins over the bare command id.
    """
    conf = gp_models(self).get(model_name)
    if conf is None:
        return None
    commands = conf["Commands"]
    target = None
    if payload:
        target = commands.get("%02x/%s" % (command_id, payload.lower()))
    if target is None:
        target = commands.get("%02x" % command_id)
    if target is None:
        return None
    return target[0], target[1], (target[2] if len(target) == 3 else None)
