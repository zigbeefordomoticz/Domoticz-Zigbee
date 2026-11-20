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
Native Zigbee scenes: a named state stored on the devices of a group, through
the ZCL Scenes cluster (0x0005), and recalled with one group-cast frame.

A scene belongs to a group, and is identified on a device by (GroupId, SceneId).
A store record is one group, keyed by its GroupId:

    {"scenes": {SceneId: {"name", "comment", "transitionTime", "createdAt", "updatedAt",
                          "lastRecalled", "selectorLevel",
                          "members": {"<ieee>-<ep>": member}}}}

GroupId and SceneId are hex strings, as in ListOfGroups ("1001", "03"). A member
is keyed by IEEE, which survives a re-pairing, and by endpoint, as two endpoints
of a device can be in the same group. It is one of:

    native:   {"endpoint", "capability", "status", "lastCheck", "error", "snapshot"}
    fallback: {"endpoint", "capability", "status": "n/a", "snapshot"}

The snapshot is the on/off and level the plugin last saw at the capture. A fallback
member is sent it at a recall. On a native member it is only shown: the scene is what
the device stored, and a member a scan found has none.

The size of the scene table of a device is not in the ZCL: Get Scene Membership gives
what is left, so the total is that and the scenes the store has on the device, all
groups together, as the table is shared. It is kept on the device, in "SceneTable",
as {endpoint: total}: it stays when the store is lost. A device that cannot tell what
it has left, or holds scenes the plugin never scanned, only makes it less exact.

A comment is only known to the plugin, like the name: a device holds neither, so a
scan cannot bring it back after a store was lost.

A scan asks each member which scenes of the group it holds, with Get Scene
Membership. A scene the plugin does not know, set by a remote or another
controller, becomes a record with "discovered": True and a null transition time,
which only a capture gives it, so that a capture never reuses its ID. A scan cannot
say what a scene contains: a member reporting a scene ID is synced as far as
that ID goes, and a synced member that no longer holds it is failed as "absent".

A scene ID can be asked for. Add Scene replaces what a device holds under that ID,
and the store only knows the scenes of the plugin, so such a capture waits for a scan
and only starts once it is finished, if nothing holds the ID. It is kept in memory
with its scan: a restart costs that capture and nothing else. A member that did not
answer cannot be asked, and it is captured like any other.

Capture is sent to each member, not to the group: a scene command answers only
when it is unicast, and Get Scene Membership would report a Re-capture missed by
a device as synced, the scene ID being already there. Add Scene comes first, as
Store Scene cannot set the transition time, and Store Scene follows its response,
whatever the status: Add Scene is not the verdict, Store Scene is.

Add Scene replaces the entry and its state, so the transition time only changes
with a capture. It is in whole seconds, the unit a device stores.

Members in the store and in the group can differ. A member that left the group
through the plugin is dropped, after Remove All Scenes. Otherwise the store is
left alone: the views and Recall only use the members still in the group, so a
group list that could not be read costs no scene.

A scene is on all of its group or on part of it: the members of the record are that
part, chosen at the capture. A device of the group outside them is nothing more, be
it left out on purpose or come later, and a recall leaves it alone: the group-cast is
ignored by a device without the scene. So a capture stays on the members of the scene
unless it is told otherwise, or it would bring back one that was taken out. A member
taken out, by an edit or a capture, stays in the group and is sent Remove Scene, with
no wait for the response, as for a deleted scene: one that did not hear it still
answers a recall, and the next scan shows it in the scene again. At least one native
member stays, as a scene with none is not on any device.

Each group with scenes has a Selector Switch in Domoticz (Classes/SceneSelector.py),
a scene being a level, Off being the group switched off. A scene takes the lowest free
level and keeps it for life. The Selector is only touched from the Domoticz thread: a
change marks the group, and the heartbeat brings its Selector up to date. A group with
no scene left has no Selector. One the user deleted comes back with the next new scene
of the group, the next scan or the next start: as long as there are scenes it is
expected, and a scene scan rebuilds it after a store was lost. The members only leave
a group with the last of its two widgets (GrpServices.FullRemoveOfGroup).

A Selector showing a scene goes back to Off when the devices of that scene leave it.
As for the widget of a group, this comes from the state of its devices, recomputed at
each heartbeat, but device by device: a plug going off beside a lamp that stays on
does not change the status of a group. It is compared with the state once a recall
has settled, not with the snapshot, which a device may have stored differently.
A recall settles after its transition and SCENE_SETTLE_TIME, as the fade sends reports
of its own, and a level has to move by more than LEVEL_REPORT_CHANGE, as that is what
a dimmer holds back until its next periodic report. On/off and level only, like the
snapshot: a colour or a shutter leaving a scene is not seen. Going to Off is an event
with the action of the Off level, as Domoticz writes no value without its triggers, but
it does not reach onCommand: the group is not switched off.

The decoders (forwarder thread), the REST calls (a thread per client) and the
heartbeat all change the records, hence the lock around each read-modify-write.
"""

import re
import threading
from itertools import count
from time import time

from Modules.tools import is_ack_tobe_disabled, is_hex
from Modules.zigateConsts import MAX_LOAD_ZIGATE, ZIGATE_EP
from Zigbee.zclCommands import (zcl_move_to_level_with_onoff,
                                zcl_onoff_off_noeffect, zcl_onoff_on)
from Zigbee.zclRawCommands import (zcl_raw_add_scene,
                                   zcl_raw_get_scene_membership,
                                   zcl_raw_recall_scene,
                                   zcl_raw_remove_all_scenes,
                                   zcl_raw_remove_scene, zcl_raw_store_scene)

SCENE_CLUSTER = "0005"
ONOFF_CLUSTER = "0006"
LEVEL_CLUSTER = "0008"

COORDINATOR_NWKID = "0000"
GROUP_NOT_FOR_SCENES = "0000"
# The endpoint of a group-cast is not used: the group is the address
GROUP_CAST_EP = "01"

MAX_SCENE_ID = 0xff
SCENE_ID_FORMAT = re.compile("[0-9a-fA-F]{2}")
MAX_NAME_LENGTH = 32
MAX_COMMENT_LENGTH = 200
# 0xffff means "no transition time" in the ZCL
MAX_TRANSITION_TIME = 0xfffe
DEFAULT_TRANSITION_TIME = 1

# Each response has this long to come back, in seconds
SCENE_RESPONSE_TIMEOUT = 30

# A recall settles this long after its transition, in seconds: reports are 5 s apart
SCENE_SETTLE_TIME = 10
# The Change of the default reporting of the level (0x0008/0x0000, Modules/zigateConsts.py)
LEVEL_REPORT_CHANGE = 5

STEP_ADD = "Add"
STEP_STORE = "Store"

STATUS_PENDING = "pending"
STATUS_SYNCED = "synced"
STATUS_FAILED = "failed"
STATUS_NOT_APPLICABLE = "n/a"

SELECTOR_LEVEL_STEP = 10

CAPABILITY_NATIVE = "native"
CAPABILITY_FALLBACK = "fallback"

# Capacity of Get Scene Membership: 0xfe is "at least one more", 0xff is unknown
CAPACITY_NOT_A_COUNT = 0xfe

ERROR_TIMEOUT = "timeout"
ERROR_INTERRUPTED = "interrupted"
ERROR_ABSENT = "absent"

CAPTURE_WAITING = "waiting"
CAPTURE_STARTED = "started"
CAPTURE_REFUSED = "refused"

SUCCESS = "00"

SCENE_LOG = "Scene"
# Where a scene follows a group change
GROUP_SCENE_LOG = ["Groups", "Scene"]


class SceneError(Exception):
    """A request that cannot be served. code is what REST returns (issue 2194, section 8)."""

    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code = code


def _cached_value(raw):
    """A cached attribute is an int or a hex string, or nothing yet."""
    if raw is None or raw == "" or raw == {}:
        return None
    if isinstance(raw, int):
        return raw
    return int(str(raw), 16) if is_hex(str(raw)) else None


def _member_moved(before, now):
    """Has a member left the state it had? A value the plugin never saw says nothing."""
    if None not in (before["onOff"], now["onOff"]) and before["onOff"] != now["onOff"]:
        return True
    if now["onOff"] == 0 or None in (before["level"], now["level"]):
        return False
    return abs(before["level"] - now["level"]) > LEVEL_REPORT_CHANGE


class SceneManagement:

    def __init__(self, plugin, store, selector=None):
        self.plugin = plugin
        self.store = store
        self.selector = selector
        self._lock = threading.RLock()
        # (GroupId, SceneId, member key) -> {"step", "nwkid", "deadline"}
        self._waiting = {}
        # GroupId -> the last scan of this group, kept for the views until the next one
        self._scans = {}
        # The groups whose Selector is behind, and the scene each last recalled
        self._selector_behind = set(store.keys()) if selector else set()
        self._selector_recalled = {}
        # GroupId -> the scene its Selector shows: {"sceneId", "settled", "state"}
        self._selector_shown = {}
        # The Selectors the user deleted, until the next start, scan or new scene
        self._selector_removed = set()
        self._fail_interrupted_captures()

    def logging(self, logType, message, nwkid=None, module=SCENE_LOG):
        self.plugin.log.logging(module, logType, message, nwkid)

    @property
    def _groups(self):
        return self.plugin.groupmgt.ListOfGroups

    # ── Group members ───────────────────────────────────────────────────────

    def _capability(self, nwkid, ep):
        """
        How a scene reaches this endpoint, None when it cannot.

        Epv2 and not Ep: Ep mixes input and output clusters, and a remote has the
        Scenes cluster as output.
        """
        cluster_in = self.plugin.ListOfDevices.get(nwkid, {}).get("Epv2", {}).get(ep, {}).get("ClusterIn", {})
        if SCENE_CLUSTER in cluster_in:
            return CAPABILITY_NATIVE
        if ONOFF_CLUSTER in cluster_in or LEVEL_CLUSTER in cluster_in:
            return CAPABILITY_FALLBACK
        return None

    def _group_members(self, GroupId):
        """The members a scene can reach, keyed as in the store."""
        members = {}
        for nwkid, ep, ieee in self._groups[GroupId].get("Devices", []):
            nwkid = self.plugin.IEEE2NWK.get(ieee, nwkid)
            capability = None if nwkid == COORDINATOR_NWKID else self._capability(nwkid, ep)
            if capability:
                members["%s-%s" % (ieee, ep)] = {"nwkid": nwkid, "ep": ep, "ieee": ieee, "capability": capability}
        return members

    def _snapshot(self, nwkid, ep):
        """On/off and level as the plugin last saw them."""
        ep_data = self.plugin.ListOfDevices.get(nwkid, {}).get("Ep", {}).get(ep, {})
        on_off = _cached_value(ep_data.get(ONOFF_CLUSTER, {}).get("0000"))
        return {
            "onOff": None if on_off is None else int(on_off != 0),
            "level": _cached_value(ep_data.get(LEVEL_CLUSTER, {}).get("0000")),
        }

    # ── Checks ──────────────────────────────────────────────────────────────

    def _check_group(self, GroupId):
        if GroupId not in self._groups:
            raise SceneError("GROUP_NOT_FOUND")

    def _check_group_for_capture(self, GroupId):
        self._check_group(GroupId)
        if GroupId == GROUP_NOT_FOR_SCENES:
            raise SceneError("GROUP_NOT_ALLOWED")
        members = self._group_members(GroupId)
        if not any(member["capability"] == CAPABILITY_NATIVE for member in members.values()):
            raise SceneError("NO_CAPABLE_MEMBER")
        return members

    def _chosen_members(self, available, keys):
        """The members of this list, as keyed in the store, out of those available."""
        if not isinstance(keys, list) or not all(isinstance(key, str) and key in available for key in keys):
            raise SceneError("MEMBERS_INVALID")
        chosen = {key: available[key] for key in keys}
        if not any(member["capability"] == CAPABILITY_NATIVE for member in chosen.values()):
            raise SceneError("MEMBERS_INVALID")
        return chosen

    def _check_load(self):
        if self.plugin.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
            raise SceneError("COORDINATOR_BUSY")

    def _check_name(self, record, name, SceneId=None):
        if not isinstance(name, str) or not name.strip():
            raise SceneError("NAME_REQUIRED")
        name = name.strip()
        # "|" separates the levels of a Selector
        if "|" in name or len(name) > MAX_NAME_LENGTH:
            raise SceneError("NAME_INVALID")
        for other_id, other in record["scenes"].items():
            if other_id != SceneId and other["name"].casefold() == name.casefold():
                raise SceneError("NAME_DUPLICATE")
        return name

    def _check_comment(self, comment):
        if comment is None:
            return ""
        if not isinstance(comment, str) or len(comment.strip()) > MAX_COMMENT_LENGTH:
            raise SceneError("COMMENT_INVALID")
        return comment.strip()

    def _check_transition(self, transition_time):
        if isinstance(transition_time, bool) or not isinstance(transition_time, int) or not 0 <= transition_time <= MAX_TRANSITION_TIME:
            raise SceneError("TRANSITION_INVALID")
        return transition_time

    def _scene_record(self, GroupId, SceneId):
        self._check_group(GroupId)
        record = self.store.get(GroupId)
        if record is None or SceneId not in record["scenes"]:
            raise SceneError("SCENE_NOT_FOUND")
        return record

    def _allocate_scene_id(self, record):
        for scene_id in range(1, MAX_SCENE_ID + 1):
            if "%02x" % scene_id not in record["scenes"]:
                return "%02x" % scene_id
        raise SceneError("SCENE_ID_EXHAUSTED")

    def _check_scene_id(self, record, SceneId):
        if not isinstance(SceneId, str) or not SCENE_ID_FORMAT.fullmatch(SceneId):
            raise SceneError("SCENE_ID_INVALID")
        SceneId = SceneId.lower()
        if SceneId in record["scenes"]:
            raise SceneError("SCENE_ID_IN_USE")
        return SceneId

    def _capture_waiting(self, GroupId):
        capture = self._scans.get(GroupId, {}).get("capture")
        return capture is not None and capture["state"] == CAPTURE_WAITING

    # ── Requests ────────────────────────────────────────────────────────────

    def create_scene(self, GroupId, name, transition_time=DEFAULT_TRANSITION_TIME, SceneId=None, comment=None, members=None):
        """
        Capture the current state of a group as a new scene, or of these members of it.
        With a SceneId, the capture only starts after a scan: the answer is then the view
        of the group, not a scene. The scan is on the whole group: a member left out still
        answers a recall of an ID it holds.
        """
        with self._lock:
            group = self._check_group_for_capture(GroupId)
            record = self.store.get(GroupId, {"scenes": {}})
            name = self._check_name(record, name)
            self._check_transition(transition_time)
            comment = self._check_comment(comment)
            chosen = group if members is None else self._chosen_members(group, members)
            if SceneId is not None:
                SceneId = self._check_scene_id(record, SceneId)
            if self._capture_waiting(GroupId):
                raise SceneError("SCENE_ID_CHECK_RUNNING")
            self._check_load()

            if SceneId is not None:
                return self._capture_after_scan(GroupId, SceneId, name, transition_time, group, chosen, comment)

            SceneId = self._allocate_scene_id(record)
            self._add_scene(GroupId, record, SceneId, name, transition_time, chosen, comment)
            return self._scene_view(GroupId, SceneId, record["scenes"][SceneId])

    def _add_scene(self, GroupId, record, SceneId, name, transition_time, members, comment=""):
        self.logging("Debug", "create_scene - group %s scene %s %s, transition %ss" % (GroupId, SceneId, name, transition_time))
        now = int(time())
        self._selector_removed.discard(GroupId)
        record["scenes"][SceneId] = {
            "name": name,
            "transitionTime": transition_time,
            "comment": comment,
            "createdAt": now,
            "updatedAt": now,
            "lastRecalled": None,
            "members": {},
        }
        self._capture(GroupId, SceneId, record, members)
        self._selector_changed(GroupId)

    def _capture_after_scan(self, GroupId, SceneId, name, transition_time, group, chosen, comment=""):
        self.logging("Debug", "create_scene - group %s scene %s %s: scan first" % (GroupId, SceneId, name))
        capture = {
            "sceneId": SceneId, "name": name, "transitionTime": transition_time, "comment": comment,
            "members": list(chosen), "state": CAPTURE_WAITING, "error": None,
        }
        if self._scan_running(GroupId):
            self._scans[GroupId]["capture"] = capture
        else:
            self._start_scan(GroupId, group, capture)
        return self.group_view(GroupId)

    def capture_scene(self, GroupId, SceneId, transition_time=None, members=None):
        """
        Overwrite a scene with the current state of its members, or of these members of
        the group: a device comes in or goes out this way.
        """
        with self._lock:
            record = self._scene_record(GroupId, SceneId)
            group = self._check_group_for_capture(GroupId)
            scene = record["scenes"][SceneId]
            chosen = self._chosen_members(group, [key for key in scene["members"] if key in group] if members is None else members)
            self._check_load()
            if transition_time is not None:
                scene["transitionTime"] = self._check_transition(transition_time)
            elif scene["transitionTime"] is None:
                scene["transitionTime"] = DEFAULT_TRANSITION_TIME
            scene.pop("discovered", None)
            scene["updatedAt"] = int(time())
            self.logging("Debug", "capture_scene - group %s scene %s %s, transition %ss" % (GroupId, SceneId, scene["name"], scene["transitionTime"]))
            self._drop_members(GroupId, SceneId, scene, group, self._leaving(scene, group, chosen))
            self._capture(GroupId, SceneId, record, chosen)
            return self._scene_view(GroupId, SceneId, scene)

    def retry_scene(self, GroupId, SceneId):
        """Capture again on the failed members. Each stores the state it is in now."""
        with self._lock:
            record = self._scene_record(GroupId, SceneId)
            self._check_load()
            scene = record["scenes"][SceneId]
            members = self._group_members(GroupId)
            failed = [key for key, member in scene["members"].items() if member["status"] == STATUS_FAILED and key in members]
            self.logging("Debug", "retry_scene - group %s scene %s, failed members %s" % (GroupId, SceneId, failed))
            for key in failed:
                scene["members"][key].update({
                    "status": STATUS_PENDING, "error": None, "snapshot": self._snapshot(members[key]["nwkid"], members[key]["ep"]),
                })
            self.store.set(GroupId, record)
            for key in failed:
                self._send_add(GroupId, SceneId, key, members[key], scene["transitionTime"])
            return self._scene_view(GroupId, SceneId, scene)

    def edit_scene(self, GroupId, SceneId, name, comment=None, members=None):
        """
        The name, the comment and the members a scene keeps: a list can only take some
        out, as a device coming in has to capture. Without a comment or a list, what the
        scene has stays, and only a member taken out sends anything to the devices.
        """
        with self._lock:
            record = self._scene_record(GroupId, SceneId)
            scene = record["scenes"][SceneId]
            new_name = self._check_name(record, name, SceneId)
            new_comment = scene.get("comment", "") if comment is None else self._check_comment(comment)
            group = self._group_members(GroupId)
            leaving = []
            if members is not None:
                held = {key: group[key] for key in scene["members"] if key in group}
                leaving = self._leaving(scene, group, self._chosen_members(held, members))
            if leaving:
                self._check_load()
            self.logging("Debug", "edit_scene - group %s scene %s from %s to %s, leaving %s" % (GroupId, SceneId, scene["name"], new_name, leaving))
            self._drop_members(GroupId, SceneId, scene, group, leaving)
            scene["name"] = new_name
            scene["comment"] = new_comment
            scene["updatedAt"] = int(time())
            self.store.set(GroupId, record)
            self._selector_changed(GroupId)
            return self._scene_view(GroupId, SceneId, scene)

    def recall_scene(self, GroupId, SceneId):
        """One group-cast Recall Scene, and direct commands to the fallback members."""
        with self._lock:
            record = self._scene_record(GroupId, SceneId)
            scene = record["scenes"][SceneId]
            members = self._group_members(GroupId)
            held = {key: scene["members"][key] for key in scene["members"] if key in members}
            self.logging("Debug", "recall_scene - group %s scene %s %s, members %s" % (
                GroupId, SceneId, scene["name"], {key: member["capability"] for key, member in held.items()}))

            if any(member["capability"] == CAPABILITY_NATIVE for member in held.values()):
                zcl_raw_recall_scene(self.plugin, GroupId, ZIGATE_EP, GROUP_CAST_EP, GroupId, SceneId, groupaddrmode=True)

            for key, member in held.items():
                if member["capability"] == CAPABILITY_FALLBACK:
                    self._replay_snapshot(members[key], member["snapshot"], scene["transitionTime"])

            scene["lastRecalled"] = int(time())
            self.store.set(GroupId, record)
            self._selector_recalled[GroupId] = SceneId
            self._selector_changed(GroupId)
            self.logging("Log", "Scene %s recalled on group %s" % (scene["name"], GroupId))
            return self._scene_view(GroupId, SceneId, scene)

    def delete_scene(self, GroupId, SceneId):
        with self._lock:
            record = self._scene_record(GroupId, SceneId)
            scene = record["scenes"].pop(SceneId)
            self.logging("Debug", "delete_scene - group %s scene %s %s" % (GroupId, SceneId, scene["name"]))
            self._drop_members(GroupId, SceneId, scene, self._group_members(GroupId), list(scene["members"]))
            self._save(GroupId, record)

    def scan_group(self, GroupId):
        """Ask each member which scenes of the group it holds. The answers come through the views."""
        with self._lock:
            members = self._check_group_for_capture(GroupId)
            self.plugin.groupmgt.request_widgets_restore()
            if self._scan_running(GroupId):
                return self.group_view(GroupId)
            self._check_load()
            self._start_scan(GroupId, members)
            return self.group_view(GroupId)

    def _start_scan(self, GroupId, members, capture=None):
        native = {key: member for key, member in members.items() if member["capability"] == CAPABILITY_NATIVE}
        self.logging("Debug", "scan_group - group %s, members %s" % (GroupId, list(native)))
        self._scans[GroupId] = {
            "at": int(time()),
            "deadline": time() + SCENE_RESPONSE_TIMEOUT,
            "members": len(native),
            "waiting": {key: member["nwkid"] for key, member in native.items()},
            "noAnswer": [],
            "found": [],
            # Before the first frame: the last answer is what starts it
            "capture": capture,
        }
        for member in native.values():
            nwkid, ep = member["nwkid"], member["ep"]
            zcl_raw_get_scene_membership(self.plugin, nwkid, ZIGATE_EP, ep, GroupId, ackIsDisabled=is_ack_tobe_disabled(self.plugin, nwkid))

    def member_removed(self, GroupId, NwkId, Ep, ieee):
        """
        To call before Remove Group is sent: a device drops the scenes of a group
        it leaves, or should, and a scene command is refused for a group it has left.
        """
        with self._lock:
            record = self.store.get(GroupId)
            if record is None:
                return
            key = "%s-%s" % (ieee, Ep)
            held = [SceneId for SceneId, scene in record["scenes"].items() if key in scene["members"]]
            if not held:
                return
            self.logging("Debug", "member_removed - group %s %s/%s leaves scenes %s" % (GroupId, NwkId, Ep, held), NwkId, GROUP_SCENE_LOG)
            if any(record["scenes"][SceneId]["members"][key]["capability"] == CAPABILITY_NATIVE for SceneId in held):
                zcl_raw_remove_all_scenes(self.plugin, NwkId, ZIGATE_EP, Ep, GroupId, ackIsDisabled=is_ack_tobe_disabled(self.plugin, NwkId))
            for SceneId in held:
                self._waiting.pop((GroupId, SceneId, key), None)
                del record["scenes"][SceneId]["members"][key]
                if not record["scenes"][SceneId]["members"]:
                    del record["scenes"][SceneId]
            self._save(GroupId, record)

    # ── Device exchanges ────────────────────────────────────────────────────

    def _leaving(self, scene, group, kept):
        """The members of a scene to take out. One no longer in the group stays: it may be the list that is wrong."""
        return [key for key in scene["members"] if key in group and key not in kept]

    def _drop_members(self, GroupId, SceneId, scene, group, keys):
        """Out of the scene. Only a member still in the group can be told: a scene command is refused otherwise."""
        for key in keys:
            self._waiting.pop((GroupId, SceneId, key), None)
            if scene["members"].pop(key)["capability"] == CAPABILITY_NATIVE and key in group:
                nwkid, ep = group[key]["nwkid"], group[key]["ep"]
                zcl_raw_remove_scene(self.plugin, nwkid, ZIGATE_EP, ep, GroupId, SceneId, ackIsDisabled=is_ack_tobe_disabled(self.plugin, nwkid))

    def _capture(self, GroupId, SceneId, record, members):
        """Rebuild the members of a scene and start the capture of the native ones."""
        scene = record["scenes"][SceneId]
        self.logging("Debug", "_capture - group %s scene %s, members %s" % (
            GroupId, SceneId, {key: member["capability"] for key, member in members.items()}))
        scene["members"] = {}
        for key, member in members.items():
            if member["capability"] == CAPABILITY_NATIVE:
                scene["members"][key] = {
                    "endpoint": member["ep"], "capability": CAPABILITY_NATIVE,
                    "status": STATUS_PENDING, "lastCheck": None, "error": None,
                    "snapshot": self._snapshot(member["nwkid"], member["ep"]),
                }
            else:
                scene["members"][key] = {
                    "endpoint": member["ep"], "capability": CAPABILITY_FALLBACK,
                    "status": STATUS_NOT_APPLICABLE, "snapshot": self._snapshot(member["nwkid"], member["ep"]),
                }

        # Saved before sending, for a response to find its member
        self.store.set(GroupId, record)
        for key, member in members.items():
            if member["capability"] == CAPABILITY_NATIVE:
                self._send_add(GroupId, SceneId, key, member, scene["transitionTime"])

    def _send_add(self, GroupId, SceneId, key, member, transition_time):
        nwkid, ep = member["nwkid"], member["ep"]
        self._wait(GroupId, SceneId, key, STEP_ADD, nwkid)
        # A retry on a scene found by a scan: its transition time is not known
        transition_time = DEFAULT_TRANSITION_TIME if transition_time is None else transition_time
        zcl_raw_add_scene(self.plugin, nwkid, ZIGATE_EP, ep, GroupId, SceneId, transition_time, ackIsDisabled=is_ack_tobe_disabled(self.plugin, nwkid))

    def _wait(self, GroupId, SceneId, key, step, nwkid):
        self._waiting[(GroupId, SceneId, key)] = {"step": step, "nwkid": nwkid, "deadline": time() + SCENE_RESPONSE_TIMEOUT}

    def scene_response(self, step, nwkid, ep, status, GroupId, SceneId):
        """An Add Scene or Store Scene response, from the decoders."""
        with self._lock:
            ieee = self.plugin.ListOfDevices.get(nwkid, {}).get("IEEE")
            key = "%s-%s" % (ieee, ep)
            waiting = self._waiting.get((GroupId, SceneId, key))
            if waiting is None or waiting["step"] != step:
                self.logging("Debug", "scene_response - %s from %s/%s, group %s scene %s: not waited for, ignored" % (step, nwkid, ep, GroupId, SceneId), nwkid)
                return

            if step == STEP_ADD:
                self.logging("Debug", "scene_response - Add from %s/%s status %s, group %s scene %s: sending Store" % (nwkid, ep, status, GroupId, SceneId), nwkid)
                self._wait(GroupId, SceneId, key, STEP_STORE, nwkid)
                zcl_raw_store_scene(self.plugin, nwkid, ZIGATE_EP, ep, GroupId, SceneId, ackIsDisabled=is_ack_tobe_disabled(self.plugin, nwkid))
                return

            del self._waiting[(GroupId, SceneId, key)]
            if status == SUCCESS:
                self.logging("Debug", "scene_response - Store from %s/%s, group %s scene %s: synced" % (nwkid, ep, GroupId, SceneId), nwkid)
                self._set_member_status(GroupId, SceneId, key, STATUS_SYNCED)
            else:
                self.logging("Log", "Scene %s of group %s not stored on %s/%s: status %s" % (SceneId, GroupId, nwkid, ep, status), nwkid)
                self._set_member_status(GroupId, SceneId, key, STATUS_FAILED, status)

    def membership_response(self, nwkid, ep, status, GroupId, scenes, capacity=None):
        """
        A Get Scene Membership response, from the decoders. scenes is a list of SceneId,
        capacity what the device has left, None on a refusal.
        """
        with self._lock:
            key = "%s-%s" % (self.plugin.ListOfDevices.get(nwkid, {}).get("IEEE"), ep)
            scan = self._scans.get(GroupId)
            if scan is None or key not in scan["waiting"]:
                self.logging("Debug", "membership_response - %s/%s, group %s: not waited for, ignored" % (nwkid, ep, GroupId), nwkid)
                return

            del scan["waiting"][key]
            if status == SUCCESS:
                self.logging("Debug", "membership_response - %s/%s, group %s holds %s" % (nwkid, ep, GroupId, scenes), nwkid)
                self._apply_membership(GroupId, key, ep, scenes, scan)
                self._note_scene_table(nwkid, ep, key, capacity)
            else:
                scan["noAnswer"].append(nwkid)
            if not scan["waiting"]:
                self._scan_finished(GroupId, scan)

    def _scenes_held(self, key):
        """What the store has on a member, in all its groups: they share one table."""
        records = (self.store.get(GroupId) for GroupId in list(self.store.keys()))
        return sum(scene["members"].get(key, {}).get("status") == STATUS_SYNCED for record in records for scene in record["scenes"].values())

    def _note_scene_table(self, nwkid, ep, key, capacity):
        device = self.plugin.ListOfDevices[nwkid]
        table = dict(device.get("SceneTable", {}))
        if capacity is None or capacity >= CAPACITY_NOT_A_COUNT:
            table.pop(ep, None)
        else:
            table[ep] = self._scenes_held(key) + capacity
        self.logging("Debug", "_note_scene_table - %s/%s capacity %s, table %s" % (nwkid, ep, capacity, table), nwkid)
        device["SceneTable"] = table

    def _apply_membership(self, GroupId, key, ep, scenes, scan):
        record = self.store.get(GroupId, {"scenes": {}})
        now = int(time())
        for SceneId in scenes:
            if SceneId not in record["scenes"]:
                record["scenes"][SceneId] = self._discovered_scene(record, SceneId, now)
                scan["found"].append(SceneId)
            members = record["scenes"][SceneId]["members"]
            held = members.setdefault(key, {
                "endpoint": ep, "capability": CAPABILITY_NATIVE, "status": STATUS_SYNCED, "lastCheck": now, "error": None,
            })
            if held["capability"] != CAPABILITY_NATIVE:
                continue
            if held["status"] == STATUS_SYNCED or held["error"] == ERROR_ABSENT:
                held.update({"status": STATUS_SYNCED, "lastCheck": now, "error": None})

        for SceneId, scene in record["scenes"].items():
            held = scene["members"].get(key)
            if SceneId not in scenes and held and held["status"] == STATUS_SYNCED:
                held.update({"status": STATUS_FAILED, "error": ERROR_ABSENT, "lastCheck": now})
        self._save(GroupId, record)

    def _scan_finished(self, GroupId, scan):
        """The capture a scan was holding: the checks are made again, things may have moved."""
        capture = scan["capture"]
        if capture is None or capture["state"] != CAPTURE_WAITING:
            return
        try:
            members = self._chosen_members(self._check_group_for_capture(GroupId), capture["members"])
            record = self.store.get(GroupId, {"scenes": {}})
            self._check_name(record, capture["name"])
            self._check_scene_id(record, capture["sceneId"])
            self._check_load()
        except SceneError as e:
            self.logging("Log", "Scene %s not captured on group %s as ID %s: %s" % (capture["name"], GroupId, capture["sceneId"], e.code))
            capture.update({"state": CAPTURE_REFUSED, "error": e.code})
            return
        capture["state"] = CAPTURE_STARTED
        self._add_scene(GroupId, record, capture["sceneId"], capture["name"], capture["transitionTime"], members, capture["comment"])

    def _discovered_scene(self, record, SceneId, now):
        """Named so that it can be told apart, recalled and renamed like any scene."""
        base = name = "Scene %s" % SceneId
        taken = {scene["name"].casefold() for scene in record["scenes"].values()}
        suffix = 2
        while name.casefold() in taken:
            name = "%s (%s)" % (base, suffix)
            suffix += 1
        return {
            "name": name, "transitionTime": None, "discovered": True,
            "createdAt": now, "updatedAt": now, "lastRecalled": None, "members": {},
        }

    def _scan_running(self, GroupId):
        return bool(self._scans.get(GroupId, {}).get("waiting"))

    def _set_member_status(self, GroupId, SceneId, key, status, error=None):
        record = self.store.get(GroupId)
        member = record["scenes"].get(SceneId, {}).get("members", {}).get(key) if record else None
        if member is None:
            return
        member.update({"status": status, "error": error, "lastCheck": int(time())})
        self.store.set(GroupId, record)

    def _replay_snapshot(self, member, snapshot, transition_time):
        nwkid, ep = member["nwkid"], member["ep"]
        ack_disabled = is_ack_tobe_disabled(self.plugin, nwkid)
        self.logging("Debug", "_replay_snapshot - %s/%s %s, transition %ss" % (nwkid, ep, snapshot, transition_time), nwkid)
        if snapshot["onOff"] == 0:
            zcl_onoff_off_noeffect(self.plugin, nwkid, ep, ackIsDisabled=ack_disabled)
        elif snapshot["level"] is not None:
            # Scene transitions are in seconds, a level transition in 1/10 s
            transition = "%04x" % min(transition_time * 10, MAX_TRANSITION_TIME)
            zcl_move_to_level_with_onoff(self.plugin, nwkid, ep, "01", "%02x" % snapshot["level"], transition=transition, ackIsDisabled=ack_disabled)
        elif snapshot["onOff"] == 1:
            zcl_onoff_on(self.plugin, nwkid, ep, ackIsDisabled=ack_disabled)

    def heartbeat(self):
        with self._lock:
            now = time()
            for (GroupId, SceneId, key), waiting in list(self._waiting.items()):
                if now >= waiting["deadline"]:
                    del self._waiting[(GroupId, SceneId, key)]
                    self.logging("Log", "Scene %s of group %s: no %s Scene response from %s" % (SceneId, GroupId, waiting["step"], waiting["nwkid"]), waiting["nwkid"])
                    self._set_member_status(GroupId, SceneId, key, STATUS_FAILED, ERROR_TIMEOUT)
            for GroupId, scan in self._scans.items():
                if scan["waiting"] and now >= scan["deadline"]:
                    self.logging("Log", "Scan of the scenes of group %s: no response from %s" % (GroupId, list(scan["waiting"].values())))
                    scan["noAnswer"].extend(scan["waiting"].values())
                    scan["waiting"] = {}
                    self._scan_finished(GroupId, scan)
            for GroupId in list(self._selector_behind):
                self._sync_selector(GroupId)
            for GroupId in list(self._selector_shown):
                self._check_shown_scene(GroupId)
        self.store.flush(self.plugin)

    def _fail_interrupted_captures(self):
        """A capture does not survive a restart: nothing is waiting for its responses."""
        for GroupId in self.store.keys():
            record = self.store.get(GroupId)
            changed = False
            for scene in record["scenes"].values():
                for member in scene["members"].values():
                    if member["status"] == STATUS_PENDING:
                        member.update({"status": STATUS_FAILED, "error": ERROR_INTERRUPTED})
                        changed = True
            if changed:
                self.logging("Debug", "_fail_interrupted_captures - group %s" % GroupId)
                self.store.set(GroupId, record)

    def _save(self, GroupId, record):
        """A group without a scene has no record."""
        if record["scenes"]:
            self.store.set(GroupId, record)
        else:
            self.store.delete(GroupId)
        self._selector_changed(GroupId)

    # ── Selector widget ─────────────────────────────────────────────────────

    def _selector_changed(self, GroupId):
        if self.selector:
            self._selector_behind.add(GroupId)

    def _assign_levels(self, record):
        """Each scene without a level takes the lowest free one. Returns True when one did."""
        taken = {scene["selectorLevel"] for scene in record["scenes"].values() if "selectorLevel" in scene}
        free = (level for level in count(SELECTOR_LEVEL_STEP, SELECTOR_LEVEL_STEP) if level not in taken)
        waiting = [scene for _, scene in sorted(record["scenes"].items()) if "selectorLevel" not in scene]
        for scene in waiting:
            scene["selectorLevel"] = next(free)
        return bool(waiting)

    def _sync_selector(self, GroupId):
        self._selector_behind.discard(GroupId)
        recalled = self._selector_recalled.pop(GroupId, None)
        record = self.store.get(GroupId)
        if record is None:
            self.selector.remove(GroupId)
            return
        if GroupId not in self._groups:
            # As for the store: a group list that could not be read costs nothing
            return
        if self._assign_levels(record):
            self.store.set(GroupId, record)
        if GroupId in self._selector_removed:
            return
        scenes = record["scenes"]
        self.selector.sync(GroupId, self._groups[GroupId].get("Name", ""), {scene["selectorLevel"]: scene["name"] for scene in scenes.values()})
        if recalled in scenes:
            self.selector.show(GroupId, scenes[recalled]["selectorLevel"])
            self._watch_shown_scene(GroupId, recalled, time() + (scenes[recalled]["transitionTime"] or 0) + SCENE_SETTLE_TIME)
        elif GroupId not in self._selector_shown:
            # After a restart: the Selector is what still knows the scene
            level = self.selector.level(GroupId)
            shown = next((SceneId for SceneId, scene in scenes.items() if scene["selectorLevel"] == level), None)
            if shown:
                self._watch_shown_scene(GroupId, shown, time())

    def _watch_shown_scene(self, GroupId, SceneId, settled):
        self._selector_shown[GroupId] = {"sceneId": SceneId, "settled": settled, "state": None}

    def _scene_state(self, GroupId, scene):
        """Where the devices of a scene are now, by member: the group has others, which it does not hold."""
        members = self._group_members(GroupId)
        return {key: self._snapshot(members[key]["nwkid"], members[key]["ep"]) for key in scene["members"] if key in members}

    def _check_shown_scene(self, GroupId):
        shown = self._selector_shown[GroupId]
        if time() < shown["settled"]:
            return
        scene = self.store.get(GroupId, {"scenes": {}})["scenes"].get(shown["sceneId"])
        if scene is None:
            del self._selector_shown[GroupId]
            return
        state = self._scene_state(GroupId, scene)
        if shown["state"] is None:
            shown["state"] = state
            return
        moved = [key for key in shown["state"] if key in state and _member_moved(shown["state"][key], state[key])]
        if moved:
            self.logging("Debug", "Scene %s of group %s left by %s: Selector to Off" % (shown["sceneId"], GroupId, moved), GroupId)
            del self._selector_shown[GroupId]
            self.selector.show(GroupId, 0)

    def selector_command(self, GroupId, Command, Level):
        """A level chosen on a Selector, from onCommand."""
        with self._lock:
            if GroupId not in self._groups:
                self.logging("Log", "Selector of group %s: the group is not known" % GroupId, GroupId)
            elif Command == "Off":
                self._selector_shown.pop(GroupId, None)
                self.selector.group_off(GroupId)
                self.selector.show(GroupId, 0)
            elif Command == "Set Level":
                self._selector_recall(GroupId, Level)
            else:
                self.logging("Debug", "selector_command - group %s: %s ignored" % (GroupId, Command), GroupId)

    def _selector_recall(self, GroupId, Level):
        scenes = self.store.get(GroupId, {"scenes": {}})["scenes"]
        SceneId = next((SceneId for SceneId, scene in scenes.items() if scene.get("selectorLevel") == Level), None)
        if SceneId is None:
            self.logging("Log", "Selector of group %s: no scene at level %s" % (GroupId, Level), GroupId)
            return
        self.recall_scene(GroupId, SceneId)
        self._sync_selector(GroupId)

    def selector_removed(self, GroupId):
        """The user deleted the Selector. The scenes are still there, on the devices and in the WebUI."""
        with self._lock:
            record = self.store.get(GroupId)
            if record is not None:
                self.logging("Log", "Selector of group %s removed: it comes back with the next new scene, scan or start" % GroupId, GroupId)
                self._selector_removed.add(GroupId)
                self._selector_shown.pop(GroupId, None)

    def restore_selectors(self):
        """From GrpDomoticz.restore_group_widgets, on the Domoticz thread."""
        with self._lock:
            self._selector_removed.clear()
            if self.selector:
                self._selector_behind.update(self.store.keys())

    def group_removed(self, GroupId):
        """The group is gone, and no member was there to take its scenes with it."""
        with self._lock:
            self.store.delete(GroupId)
            self._selector_changed(GroupId)

    # ── Views, for REST ─────────────────────────────────────────────────────

    def _device_name(self, nwkid):
        return self.plugin.ListOfDevices.get(nwkid, {}).get("ZDeviceName", "")

    def _scene_slots(self, key, member):
        """The scenes on a member of the group and its table, None when it has no table."""
        if member["capability"] != CAPABILITY_NATIVE:
            return None
        table = self.plugin.ListOfDevices.get(member["nwkid"], {}).get("SceneTable", {})
        return {"used": self._scenes_held(key), "total": table.get(member["ep"])}

    def _scene_view(self, GroupId, SceneId, scene):
        members = self._group_members(GroupId)
        held = {key: member for key, member in scene["members"].items() if key in members}
        views = []
        for key, member in held.items():
            view = {"ieee": members[key]["ieee"], "nwkId": members[key]["nwkid"], "name": self._device_name(members[key]["nwkid"])}
            view.update(member)
            view["sceneSlots"] = self._scene_slots(key, members[key])
            views.append(view)

        native = [member for member in held.values() if member["capability"] == CAPABILITY_NATIVE]
        return {
            "groupId": GroupId,
            "sceneId": SceneId,
            "name": scene["name"],
            "comment": scene.get("comment", ""),
            "transitionTime": scene["transitionTime"],
            "discovered": scene.get("discovered", False),
            "createdAt": scene["createdAt"],
            "updatedAt": scene["updatedAt"],
            "lastRecalled": scene["lastRecalled"],
            "members": views,
            # In the group but not in the scene: left out, or come since. A capture can take them
            "missing": [
                {"ieee": member["ieee"], "endpoint": member["ep"], "name": self._device_name(member["nwkid"]), "capability": member["capability"]}
                for key, member in members.items() if key not in held
            ],
            "synced": sum(member["status"] == STATUS_SYNCED for member in native),
            "native": len(native),
        }

    def _scan_view(self, GroupId):
        scan = self._scans.get(GroupId)
        if scan is None:
            return None
        capture = scan["capture"]
        return {
            "capture": capture and {key: capture[key] for key in ("sceneId", "name", "state", "error")},
            "running": bool(scan["waiting"]),
            "at": scan["at"],
            "members": scan["members"],
            "found": len(scan["found"]),
            "noAnswer": [self._device_name(nwkid) or nwkid for nwkid in scan["noAnswer"]],
        }

    def group_view(self, GroupId):
        with self._lock:
            self._check_group(GroupId)
            record = self.store.get(GroupId, {"scenes": {}})
            members = self._group_members(GroupId)
            return {
                "groupId": GroupId,
                "groupName": self._groups[GroupId].get("Name", ""),
                "capable": GroupId != GROUP_NOT_FOR_SCENES and any(member["capability"] == CAPABILITY_NATIVE for member in members.values()),
                "members": [
                    {"ieee": member["ieee"], "nwkId": member["nwkid"], "endpoint": member["ep"],
                     "name": self._device_name(member["nwkid"]), "capability": member["capability"],
                     "sceneSlots": self._scene_slots(key, member)}
                    for key, member in members.items()
                ],
                "scenes": [self._scene_view(GroupId, SceneId, scene) for SceneId, scene in sorted(record["scenes"].items())],
                "scan": self._scan_view(GroupId),
            }

    def groups_view(self):
        return [self.group_view(GroupId) for GroupId in list(self._groups)]
