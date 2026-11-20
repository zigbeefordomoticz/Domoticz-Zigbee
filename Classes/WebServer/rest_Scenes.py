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
REST API of the native Zigbee scenes, on /rest-z4d/1/scenes:

    GET     /scenes                         every group, with its scenes
    GET     /scenes/<group>                 one group
    PUT     /scenes/<group>                 create    {"name", "transitionTime", "sceneId", "comment"}
    PUT     /scenes/<group>/scan            ask the members which scenes they hold
    PUT     /scenes/<group>/<scene>         rename    {"name", "comment"}
    DELETE  /scenes/<group>/<scene>         remove from the devices and the store
    PUT     /scenes/<group>/<scene>/capture {"transitionTime"}, optional
    PUT     /scenes/<group>/<scene>/recall
    PUT     /scenes/<group>/<scene>/retry

Every change is a PUT, as on the rest of this server, and not a POST. Nothing here
checks where a request comes from: what stops another web page from sending one
is the preflight of a PUT, as no CORS header is ever sent. A POST with a text/plain
body has no preflight.

"sceneId" is optional, two hex digits. With it the capture only starts after a scan of
the group: the answer is the view of the group, and its "scan" gives the outcome in
"capture", {"sceneId", "name", "state": "waiting" | "started" | "refused", "error"}.

A refused request answers with {"error": <code>}, the code of the SceneError.
"""

import json

from Classes.SceneManagement import SceneError
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)

SCENE_LOG = ["WebServer", "Scene"]

ERROR_STATUS = {
    "BAD_REQUEST": "400 BAD REQUEST",
    "NAME_REQUIRED": "400 BAD REQUEST",
    "NAME_INVALID": "400 BAD REQUEST",
    "NAME_DUPLICATE": "400 BAD REQUEST",
    "TRANSITION_INVALID": "400 BAD REQUEST",
    "COMMENT_INVALID": "400 BAD REQUEST",
    "SCENE_ID_INVALID": "400 BAD REQUEST",
    "GROUP_NOT_FOUND": "404 NOT FOUND",
    "SCENE_NOT_FOUND": "404 NOT FOUND",
    "GROUP_NOT_ALLOWED": "409 CONFLICT",
    "NO_CAPABLE_MEMBER": "409 CONFLICT",
    "SCENE_ID_EXHAUSTED": "409 CONFLICT",
    "SCENE_ID_IN_USE": "409 CONFLICT",
    "SCENE_ID_CHECK_RUNNING": "409 CONFLICT",
    "SCENES_DISABLED": "409 CONFLICT",
    "COORDINATOR_BUSY": "503 SERVICE UNAVAILABLE",
}


def _body(data):
    """The JSON object of a request, which can come without a body."""
    if not data:
        return {}
    try:
        body = json.loads(data.decode("utf8") if isinstance(data, bytes) else data)
    except ValueError as e:
        raise SceneError("BAD_REQUEST") from e
    if not isinstance(body, dict):
        raise SceneError("BAD_REQUEST")
    return body


def _serve(scenemgt, verb, data, parameters):
    if verb == "GET" and len(parameters) == 0:
        return scenemgt.groups_view()
    if verb == "GET" and len(parameters) == 1:
        return scenemgt.group_view(parameters[0])

    if verb == "PUT" and len(parameters) == 1:
        body = _body(data)
        return scenemgt.create_scene(parameters[0], body.get("name"), body.get("transitionTime", 1), body.get("sceneId"), body.get("comment"))

    # Not a scene ID, which is two hex digits
    if verb == "PUT" and len(parameters) == 2 and parameters[1] == "scan":
        return scenemgt.scan_group(parameters[0])

    if verb == "PUT" and len(parameters) == 2:
        body = _body(data)
        return scenemgt.rename_scene(parameters[0], parameters[1], body.get("name"), body.get("comment"))

    if verb == "DELETE" and len(parameters) == 2:
        scenemgt.delete_scene(parameters[0], parameters[1])
        return {}

    if verb == "PUT" and len(parameters) == 3:
        group_id, scene_id, action = parameters
        if action == "capture":
            return scenemgt.capture_scene(group_id, scene_id, _body(data).get("transitionTime"))
        if action == "recall":
            return scenemgt.recall_scene(group_id, scene_id)
        if action == "retry":
            return scenemgt.retry_scene(group_id, scene_id)

    raise SceneError("BAD_REQUEST")


def rest_scenes(self, verb, data, parameters):
    _response = prepResponseMessage(self, setupHeadersResponse())

    try:
        if self.scenemgt is None:
            raise SceneError("SCENES_DISABLED")
        _response["Data"] = json.dumps(_serve(self.scenemgt, verb, data, parameters))

    except SceneError as e:
        if self.log:
            self.log.logging(SCENE_LOG, "Debug", f"rest_scenes {verb} {parameters}: {e.code}")
        _response["Status"] = ERROR_STATUS[e.code]
        _response["Data"] = json.dumps({"error": e.code})

    return _response
