"""
Green Power frames (9exx), built by Classes/ZigpyTransport/plugin_encoders.py
from zigpy Green Power events (Classes/ZigpyTransport/greenPower.py).

    9e00  GPD commissioned   hex of a versioned JSON record (holds the GPD
                             security key: never log the record or MsgData)
    9e01  GPD command        ieee(16) nwk(4) endpoint(2) command(2)
                             frame counter(8) payload(rest)
    9e02  GPD removed        ieee(16) nwk(4)

Logging only for now: the GPDs are not yet stored in ListOfDevices.
"""

import json

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

    logged = {k: record.get(k) for k in GP_RECORD_LOGGED_FIELDS}
    action = "commissioned again" if record.get("recommissioned") else "commissioned"
    self.log.logging("GreenPower", "Status", "Green Power device %s: %s LQI: %s" % (action, logged, int(MsgLQI, 16)))


def Decode9E01(self, Devices, MsgData, MsgLQI):
    command = decode_gp_command(MsgData)
    self.log.logging("GreenPower", "Debug", "Decode9E01 - Green Power command %s LQI: %s" % (command, int(MsgLQI, 16)))


def Decode9E02(self, Devices, MsgData, MsgLQI):
    self.log.logging("GreenPower", "Status", "Green Power device removed: ieee %s nwk %s" % (MsgData[:16], MsgData[16:20]))
