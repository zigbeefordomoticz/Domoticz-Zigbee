"""
Green Power frames (9exx), built by Classes/ZigpyTransport/plugin_encoders.py
from zigpy Green Power events (Classes/ZigpyTransport/greenPower.py).

    9e00  GPD commissioned   hex of a versioned JSON record (holds the GPD
                             security key: never log the record or MsgData)
    9e01  GPD command        ieee(16) nwk(4) endpoint(2) command(2)
                             frame counter(8) payload(rest)
    9e02  GPD removed        ieee(16) nwk(4)
    9e03  GPDF heard         ieee(16) command(2) flags(2) proxy nwk(4)
                             rssi(2), for the pairing feed
    9e04  GP window          state(2) seconds(4), for the pairing feed

The pairing feed (Modules/greenPowerFeed.py) shows these steps on Admin →
Provisioning.

The GPDs are kept in the Green Power device store (Modules/greenPowerStore.py),
not in ListOfDevices. Their widgets: Modules/greenPowerWidgets.py.
"""

import json
import time

from Modules.greenPowerFeed import WINDOW_STATES, gp_feed, gp_src_id
from Modules.greenPowerStore import (gp_command_fields, gp_device_record,
                                     gp_store, request_gp_store_flush,
                                     request_gp_widget_creation)

GP_FRAME_VERSION = 1

# Record fields that may be logged
GP_RECORD_LOGGED_FIELDS = ("ieee", "nwk", "src_id", "device_id", "manufacturer_id", "model_id", "commands", "security_level", "frame_counter")


def decode_gp_record(MsgData):
    return json.loads(bytes.fromhex(MsgData).decode("utf-8"))


def decode_gp_command(MsgData):
    return {
        "ieee": MsgData[:16],
        "nwk": MsgData[16:20],
        "endpoint": MsgData[20:22],
        "command_id": MsgData[22:24],
        "frame_counter": int(MsgData[24:32], 16),
        "payload": MsgData[32:],
    }


def Decode9E00(self, Devices, MsgData, MsgLQI):
    record = decode_gp_record(MsgData)
    if record.get("v") != GP_FRAME_VERSION:
        self.log.logging("GreenPower", "Error", "Decode9E00 - unsupported Green Power record version %s" % record.get("v"))
        return

    lqi = int(MsgLQI, 16)
    logged = {k: record.get(k) for k in GP_RECORD_LOGGED_FIELDS}
    action = "commissioned again" if record.get("recommissioned") else "commissioned"
    self.log.logging("GreenPower", "Status", "Green Power device %s: %s LQI: %s" % (action, logged, lqi), record.get("nwk"))

    store = gp_store(self)
    if store is None:
        self.log.logging("GreenPower", "Error", "Decode9E00 - Green Power device store not loaded, %s not recorded" % record.get("ieee"), record.get("nwk"), {"Error code": "GPSTORE-9E00-01"})
        return

    ieee = record["ieee"]
    previous = store.get(ieee)
    stored = gp_device_record(record, int(time.time()), lqi, previous=previous)
    if previous:
        # Commissioned again: the GPD keeps its widgets, and the type they were made from
        for key in ("Model", "Ep", "RequestedModel"):
            if key in previous:
                stored[key] = previous[key]
    # The device type picked on the Green Power page for this window (Conf/ZGPmodel),
    # for a GPD that has no widget yet
    requested = gp_feed(self).pairing_model()
    if requested and not any(ep.get("ClusterType") for ep in (stored.get("Ep") or {}).values()):
        stored["RequestedModel"] = requested
    store.set(ieee, stored)
    # Written at the next heartbeat, not at the periodic flush
    request_gp_store_flush(self)
    # Created from the heartbeat (Domoticz thread)
    request_gp_widget_creation(self, ieee)
    # Shown on Admin → Provisioning (/rcv-nw-hrdwr)
    webserver = getattr(self, "webserver", None)
    if webserver:
        webserver.add_green_power_device_in_pairing_mode(ieee, record.get("nwk"))
    # A unidirectional GPD gets no answer: the user takes it out of its commissioning mode
    gp_feed(self).add("commissioned", IEEE=ieee, SrcId=gp_src_id(ieee), NwkId=record.get("nwk"),
                      DeviceId=record.get("device_id"), Again=bool(record.get("recommissioned")), Hint="leave-pairing")


def Decode9E01(self, Devices, MsgData, MsgLQI):
    command = decode_gp_command(MsgData)
    lqi = int(MsgLQI, 16)
    self.log.logging("GreenPower", "Debug", "Decode9E01 - Green Power command %s LQI: %s" % (command, lqi), command["nwk"])

    store = gp_store(self)
    # Frame counter written at the periodic flush
    if store is None or not store.update(command["ieee"], gp_command_fields(command["frame_counter"], int(time.time()), lqi)):
        self.log.logging("GreenPower", "Log", "Decode9E01 - command from Green Power device %s, not in the Green Power device store" % command["ieee"], command["nwk"])
        return

    # Imported here: the widget layer pulls in most of Modules/
    from Modules.greenPowerWidgets import update_gp_widgets
    update_gp_widgets(self, Devices, command["ieee"], int(command["command_id"], 16))


def Decode9E02(self, Devices, MsgData, MsgLQI):
    ieee = MsgData[:16]
    self.log.logging("GreenPower", "Status", "Green Power device removed: ieee %s nwk %s" % (ieee, MsgData[16:20]), MsgData[16:20])

    store = gp_store(self)
    if store is None or ieee not in store:
        return

    store.delete(ieee)
    request_gp_store_flush(self)
    gp_feed(self).add("removed", IEEE=ieee, SrcId=gp_src_id(ieee), NwkId=MsgData[16:20])


def Decode9E03(self, Devices, MsgData, MsgLQI):
    ieee = MsgData[:16]
    command_id = int(MsgData[16:18], 16)
    flags = int(MsgData[18:20], 16)
    proxy = MsgData[20:24]
    rssi = int(MsgData[24:26], 16)
    rssi = rssi - 256 if rssi > 127 else rssi
    entry = gp_feed(self).heard(ieee, command_id, flags, None if proxy == "ffff" else proxy, rssi, int(MsgLQI, 16))
    self.log.logging("GreenPower", "Debug", "Decode9E03 - Green Power frame heard %s" % entry)


def Decode9E04(self, Devices, MsgData, MsgLQI):
    state = WINDOW_STATES.get(int(MsgData[:2], 16))
    if state is None:
        self.log.logging("GreenPower", "Error", "Decode9E04 - unknown Green Power window state %s" % MsgData[:2])
        return
    gp_feed(self).window(state, int(MsgData[2:6], 16))

