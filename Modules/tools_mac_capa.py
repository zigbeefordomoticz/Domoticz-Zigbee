#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""MAC capability helpers extracted from tools.py"""


def decodeMacCapa(inMacCapa):

    maccap = int(inMacCapa, 16)
    alternatePANCOORDInator = maccap & 0b00000001
    deviceType = (maccap & 0b00000010) >> 1
    powerSource = (maccap & 0b00000100) >> 2
    receiveOnIddle = (maccap & 0b00001000) >> 3
    securityCap = (maccap & 0b01000000) >> 6
    allocateAddress = (maccap & 0b10000000) >> 7

    MacCapa = []
    if alternatePANCOORDInator:
        MacCapa.append("Able to act Coordinator")
    if deviceType:
        MacCapa.append("Full-Function Device")
    else:
        MacCapa.append("Reduced-Function Device")
    if powerSource:
        MacCapa.append("Main Powered")
    if receiveOnIddle:
        MacCapa.append("Receiver during Idle")
    if securityCap:
        MacCapa.append("High security")
    else:
        MacCapa.append("Standard security")
    if allocateAddress:
        MacCapa.append("NwkAddr should be allocated")
    else:
        MacCapa.append("NwkAddr need to be allocated")
    return MacCapa


def ReArrangeMacCapaBasedOnModel(self, nwkid, inMacCapa):
    """
    Function to check if the MacCapa should not be updated based on Model.
    As they are some bogous Devices which tell they are Main Powered and they are not !

    Return the old or the revised MacCapa and eventually fix some Attributes
    """
    from Modules.tools_model import get_deviceconf_parameter_value

    if nwkid not in self.ListOfDevices:
        self.log.logging("PluginTools", "Error", "%s not known !!!" % nwkid)
        return inMacCapa

    if "Model" not in self.ListOfDevices[nwkid]:
        return inMacCapa

    # Convert battery annouced devices to main powered / Make sure that you do the reverse n NetworkMap
    if (
        get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "MainPoweredDevice")
        or self.ListOfDevices[nwkid]["Model"] in ("TI0001", "TS0011", "TS0013", "TS0601-switch", "TS0601-2Gangs-switch", )
    ):
        # Livol Switch, must be converted to Main Powered
        # Patch some status as Device Annouced doesn't provide much info
        self.ListOfDevices[nwkid]["LogicalType"] = "Router"
    # Not DevideType but DeviceType    
    #    self.ListOfDevices[nwkid]["DevideType"] = "FFD"
        self.ListOfDevices[nwkid]["DeviceType"] = "FFD"
        self.ListOfDevices[nwkid]["MacCapa"] = "8e"
        self.ListOfDevices[nwkid]["PowerSource"] = "Main"
        return "8e"

    # Convert Main Powered device to Battery
    if (
        get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "BatteryPoweredDevice")
        or self.ListOfDevices[nwkid]["Model"] in ( "lumi.remote.b686opcn01", "lumi.remote.b486opcn01", "lumi.remote.b286opcn01", "lumi.remote.b686opcn01-bulb", "lumi.remote.b486opcn01-bulb", "lumi.remote.b286opcn01-bulb", "lumi.remote.b686opcn01",)
    ):
        # Aqara Opple Switch, must be converted to Battery Devices
        self.ListOfDevices[nwkid]["MacCapa"] = "80"
        self.ListOfDevices[nwkid]["PowerSource"] = "Battery"
        if "Capability" in self.ListOfDevices[nwkid] and "Main Powered" in self.ListOfDevices[nwkid]["Capability"]:
            self.ListOfDevices[nwkid]["Capability"].remove("Main Powered")
        return "80"

    if "MacCapa" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["MacCapa"] == "80" and (
        self.ListOfDevices[nwkid]["PowerSource"] == "" or "PowerSource" not in self.ListOfDevices[nwkid]
    ):
        # This is needed for VOC_Sensor from Nextrum for instance. (Looks like the device do not provide Node Descriptor )
        self.ListOfDevices[nwkid]["PowerSource"] = "Battery"

    return inMacCapa


def mainPoweredDevice(self, nwkid):
    """
    return True is it is Main Powered device
    return False if it is not Main Powered
    """
    from Modules.tools_model import get_deviceconf_parameter_value

    if nwkid not in self.ListOfDevices:
        self.log.logging("PluginTools", "Debug", "mainPoweredDevice - Unknown Device: %s" % nwkid)
        return False

    model_name = ""
    if "Model" in self.ListOfDevices[nwkid]:
        model_name = self.ListOfDevices[nwkid]["Model"]

    mainPower = False
    if "MacCapa" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["MacCapa"] != {}:
        mainPower = self.ListOfDevices[nwkid]["MacCapa"] in ["8e", "84"]

    # These are Model annouced as Main Power and are not
    if (
        get_deviceconf_parameter_value(self, model_name, "BatteryPoweredDevice")
        or model_name in (
            "lumi.remote.b686opcn01",
            "lumi.remote.b486opcn01",
            "lumi.remote.b286opcn01",
            "lumi.remote.b686opcn01-bulb",
            "lumi.remote.b486opcn01-bulb",
            "lumi.remote.b286opcn01-bulb",
        )
    ):
        mainPower = False

    # These are device annouced as Battery, but are Main Powered ( some time without neutral)
    if (
        get_deviceconf_parameter_value(self, model_name, "MainPoweredDevice")
        or model_name in ("TI0001", "TS0011", "TS0601-switch", "TS0601-2Gangs-switch", "ZBMINI-L",)
    ):
        mainPower = True
        self.ListOfDevices[nwkid]["LogicalType"] = "End Device"
    # Not DevideType but DeviceType    
    #    self.ListOfDevices[nwkid]["DevideType"] = "RFD"
        self.ListOfDevices[nwkid]["DeviceType"] = "RFD"

    if not mainPower and "PowerSource" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["PowerSource"] != {}:
        mainPower = self.ListOfDevices[nwkid]["PowerSource"] == "Main"

    # We need to take in consideration that Livolo is reporting a MacCapa of 0x80
    # That Aqara Opple are reporting MacCap 0x84 while they are Battery devices

    return mainPower


def full_function_device(self, nwkid):
    from Modules.tools_model import get_deviceconf_parameter_value
    
    if nwkid not in self.ListOfDevices:
        return True
    
    # Zigpy is considering end devices as reduced function devices and that are Receiving on idle
    main_powered_device = bool( get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid].get("Model", ""), "MainPowered") )
    is_full_function_device = main_powered_device or "Full-Function Device" in self.ListOfDevices[nwkid].get("Capability", [])
    
    self.log.logging( "outRawAPS", "Debug", "Device %s is reduced function device: %s" % (nwkid, is_full_function_device), nwkid)
    
    return is_full_function_device

def device_listening_on_iddle(self, nwkid):

    from Modules.tools_model import get_deviceconf_parameter_value

    if nwkid not in self.ListOfDevices:
        return True

    # Zigpy is considering end devices as reduced function devices and that are Receiving on idle
    received_when_idle = bool( get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid].get("Model", ""), "ReceiveOnIdle") )
    reduced_function_device = received_when_idle or "Reduced-Function Device" in self.ListOfDevices[nwkid].get("Capability", [])

    self.log.logging( "outRawAPS", "Debug", "Device %s is reduced function device: %s" % (nwkid, reduced_function_device), nwkid)

    return reduced_function_device


def is_ack_tobe_disabled(self, nwkid):
    """Determine if ACK should be disabled for the given device."""
    
    device = self.ListOfDevices.get(nwkid)
    if not device:
        return False

    # or if it's not listening while idle.
    if device_listening_on_iddle(self, nwkid):
        return False

    # Keep ACK if pairing is in progress, 
    if device.get("PairingInProgress"):
        return False
    
    if full_function_device(self, nwkid):
        return True

    # if it's a battery-powered device,
    if device.get("PowerSource") == "Battery" or device.get("MacCapa") == "80":
        return False

    return False

# Node descriptor material handed to zigpy for a pre-loaded device.
#
# zigpy fills Device.node_desc only for a device it interviewed itself, and the
# plugin registers its own devices with add_device(), which leaves it None. A
# device with no node_desc is skipped by zigpy's topology scan before any
# request is sent, so on an existing install a scan reaches almost nothing.
# See issue #2110.

COORDINATOR_NWKID = "0000"

CAPABILITY_FULL_FUNCTION_DEVICE = "Full-Function Device"
CAPABILITY_REDUCED_FUNCTION_DEVICE = "Reduced-Function Device"

NODE_DESCRIPTOR_LOGICAL_TYPES = {
    "coordinator": "coordinator",
    "router": "router",
    "end device": "end_device",
    "end_device": "end_device",
}

NODE_DESCRIPTOR_DEVICE_TYPES = {"FFD": "router", "RFD": "end_device"}

# decodeMacCapa()'s bit positions, so a Capability list can be turned back into
# the MAC capability byte it was decoded from
CAPABILITY_TO_MAC_CAPABILITY_BIT = {
    "Able to act Coordinator": 0b00000001,
    CAPABILITY_FULL_FUNCTION_DEVICE: 0b00000010,
    "Main Powered": 0b00000100,
    "Receiver during Idle": 0b00001000,
    "High security": 0b01000000,
    "NwkAddr should be allocated": 0b10000000,
}

MAC_CAPABILITY_FULL_FUNCTION_DEVICE = 0b00000010


def node_descriptor_fields(nwkid, device_record):
    """What the plugin knows of a device's node descriptor, as plain data.

    Plain data rather than a zigpy NodeDescriptor, so that plugin.py and this
    module stay free of zigpy imports: the transport builds the real struct.

    "raw" is the node descriptor the plugin captured off the wire and never
    rewrites, which the transport parses in preference to everything else here --
    it is the very thing being reconstructed, and it is the only source that can
    tell a coordinator from a router. It is kept across restarts
    (MANDATORY_ATTRIBUTES in Modules/database.py). The remaining keys are the
    fallback for a device that never answered a Node Descriptor request.

    Returns None when neither a raw descriptor nor a device type is known, so
    that the caller registers the device the way it does today -- without a
    descriptor -- rather than with a guessed one. Guessing matters here: a device
    wrongly presented as a router is one zigpy will interrogate on every single
    scan.
    """
    if not device_record:
        return None

    raw = device_record.get("_rawNodeDescriptor")
    raw = raw.strip() if isinstance(raw, str) and raw.strip() else None

    logical_type = _node_descriptor_logical_type(nwkid, device_record)
    if logical_type is None and raw is None:
        return None

    return {
        "raw": raw,
        "logical_type": logical_type,
        "mac_capability": _node_descriptor_mac_capability(device_record),
        # "Manufacturer" usually holds the 4-hex manufacturer code, but some
        # device modules put a name in it ("Legrand"), hence the range check
        "manufacturer_code": _node_descriptor_int(device_record.get("Manufacturer"), 0xFFFF),
        "maximum_buffer_size": _node_descriptor_int(device_record.get("Max Buffer Size"), 0xFF),
        "maximum_incoming_transfer_size": _node_descriptor_int(device_record.get("Max Rx"), 0xFFFF),
        "maximum_outgoing_transfer_size": _node_descriptor_int(device_record.get("Max Tx"), 0xFFFF),
        "server_mask": _node_descriptor_int(device_record.get("server_mask"), 0xFFFF),
        "descriptor_capability_field": _node_descriptor_int(device_record.get("descriptor_capability"), 0xFF),
    }


def _node_descriptor_logical_type(nwkid, device_record):
    """Router, end device or coordinator, read from the least-rewritten source.

    "Capability" is preferred over LogicalType, DeviceType and MacCapa because it
    holds what the device announced: it is written once at pairing from
    decodeMacCapa(), and the only later change to it is "Main Powered" being
    dropped for a device known to misreport its power source. The other three
    are rewritten per model afterwards, and in opposite directions for the same
    models -- ReArrangeMacCapaBasedOnModel() marks TI0001 and the TS06xx
    switches Router/FFD while mainPoweredDevice() marks the very same models
    End Device/RFD, so whichever ran last is what LogicalType holds.

    Reading the announced capability also lands on the right answer for the two
    device families that correction exists for, without needing to know their
    model names: Livolo announces 0x80 and Aqara Opple 0x84, and neither has the
    full-function bit set, so both come out as end devices -- which is what
    NetworkMap.is_a_router() concluded too, there by excluding them by name.
    """
    if nwkid == COORDINATOR_NWKID:
        return "coordinator"

    capability = device_record.get("Capability")
    if isinstance(capability, (list, tuple, set)):
        if CAPABILITY_FULL_FUNCTION_DEVICE in capability:
            return "router"
        if CAPABILITY_REDUCED_FUNCTION_DEVICE in capability:
            return "end_device"

    # Nothing was announced, or the record predates it being kept: fall back to
    # whatever is left, corrections and all.
    logical_type = NODE_DESCRIPTOR_LOGICAL_TYPES.get(
        str(device_record.get("LogicalType") or "").strip().lower()
    )
    if logical_type:
        return logical_type

    device_type = NODE_DESCRIPTOR_DEVICE_TYPES.get(device_record.get("DeviceType"))
    if device_type:
        return device_type

    mac_capability = _node_descriptor_int(device_record.get("MacCapa"), 0xFF)
    if mac_capability:
        return "router" if mac_capability & MAC_CAPABILITY_FULL_FUNCTION_DEVICE else "end_device"

    return None


def _node_descriptor_mac_capability(device_record):
    """The MAC capability byte, re-encoded from the announced Capability.

    Same reason as the logical type: MacCapa itself is rewritten per model, and
    Capability is what the device said.
    """
    capability = device_record.get("Capability")
    if isinstance(capability, (list, tuple, set)) and capability:
        flags = 0
        for name, bit in CAPABILITY_TO_MAC_CAPABILITY_BIT.items():
            if name in capability:
                flags |= bit
        return flags

    return _node_descriptor_int(device_record.get("MacCapa"), 0xFF)


def _node_descriptor_int(value, maximum):
    """A node descriptor field as an int, or 0 when the record holds no usable value."""
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value if 0 <= value <= maximum else 0
    if not isinstance(value, str) or not value.strip():
        return 0
    try:
        number = int(value.strip(), 16)
    except ValueError:
        return 0
    return number if 0 <= number <= maximum else 0
