#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_input.py

    Description: manage inputs from Zigate

"""

from Modules.basicOutputs import getListofAttribute
from Zigbee.decode8002 import decode8002_and_process


def ZigateRead(self, Devices, Data):
    
    DECODERS = {
        "004d": Decode004D,
        "0040": Decode0040,
        "0041": Decode0041,
        "0042": Decode0042,
        "0100": Decode0100,
        "0110": Decode0110,
        "0302": Decode0302,
        "0400": Decode0400,
        "8000": Decode8000_v2,
        "8002": Decode8002,
        "8003": Decode8003,
        "8004": Decode8004,
        "8005": Decode8005,
        "8006": Decode8006,
        "8007": Decode8007,
        "8008": Decode8008,
        "8009": Decode8009,
        "8010": Decode8010,
        # "8011": Decode8011,
        "8014": Decode8014,
        "8015": Decode8015,
        "8017": Decode8017,
        "8024": Decode8024,
        "8028": Decode8028,
        "802b": Decode802B,
        "802c": Decode802C,
        "8030": Decode8030,
        "8031": Decode8031,
        "8034": Decode8034,
        "8040": Decode8040,
        "8041": Decode8041,
        "8042": Decode8042,
        "8043": Decode8043,
        "8044": Decode8044,
        "8045": Decode8045,
        "8046": Decode8046,
        "8047": Decode8047,
        "8048": Decode8048,
        "8049": Decode8049,
        "804a": Decode804A,
        "804b": Decode804B,
        "804e": Decode804E,
        "8060": Decode8060,
        "8061": Decode8061,
        "8062": Decode8062,
        "8063": Decode8063,
        "8085": Decode8085,
        "8095": Decode8095,
        "80a5": Decode80A5,
        "80a6": Decode80A6,
        "80a7": Decode80A7,
        "8100": Decode8100,
        "8101": Decode8101,
        "8102": Decode8102,
        "8110": Decode8110,
        "8120": Decode8120,
        "8122": Decode8122,
        "8139": Decode8140,
        "8140": Decode8140,
        "8400": Decode8400,
        "8401": Decode8401,
        "8501": Decode8501,
        "8502": Decode8502,
        "8503": Decode8503,
        "8701": Decode8701,
        "8806": Decode8806,
        "8807": Decode8807,
        "7000": Decode7000,
    }
    # Not used
    # NOT_IMPLEMENTED = ("00d1", "8029", "80a0", "80a1", "80a2", "80a3", "80a4")

    # self.log.logging( "Input", 'Debug', "ZigateRead - decoded data: " + Data + " lenght: " + str(len(Data)) )

    if Data is None:
        return

    FrameStart = Data[:2]
    FrameStop = Data[len(Data) - 2 :]
    if FrameStart != "01" and FrameStop != "03":
        self.log.logging( "Input", "Error", "ZigateRead received a non-zigate frame Data: " + str(Data) + " FS/FS = " + str(FrameStart) + "/" + str(FrameStop) )
        return


    MsgType, MsgData, MsgLQI = extract_messge_infos( self, Data)
    self.Ping["Nb Ticks"] = 0  # We receive a valid packet 
    
    self.log.logging( "Input", "Debug", "ZigateRead - MsgType: %s,  Data: %s, LQI: %s" % (
        MsgType, MsgData, int(MsgLQI, 16)), )

    if MsgType == "8002":
        # Let's try to see if we can decode it, and then get a new MsgType
        decoded_frame = decode8002_and_process( self, Data)
        if decoded_frame is None:
            return
        MsgType, MsgData, MsgLQI = extract_messge_infos( self, decoded_frame)

    if MsgType in DECODERS:
        _decoding = DECODERS[MsgType]
        _decoding(self, Devices, MsgData, MsgLQI)
        
    elif MsgType == "8002":
        Decode8002(self, Devices, Data, MsgData, MsgLQI)
        
    elif MsgType == "8011":
        Decode8011(self, Devices, MsgData, MsgLQI)
        
    else:
        self.log.logging(
            "Input",
            "Error",
            "ZigateRead - Decoder not found for %s" % (MsgType),
        )


















def zigpy_Decode8140(self, Devices, MsgData, MsgLQI):
    
    MsgComplete = MsgData[:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgClusterID = MsgData[8:12]
    
    if "Attributes List" not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["Attributes List"] = {"Ep": {}}
        
    if "Ep" not in self.ListOfDevices[MsgSrcAddr]["Attributes List"]:
        self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"] = {}
        
    if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"]:
        self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp] = {}
        
    if MsgClusterID not in self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp]:
        self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp][MsgClusterID] = {}

    idx = 12
    while idx < len( MsgData ):
        Attribute = MsgData[idx : idx + 4]
        idx += 4
        Attribute_type = MsgData[idx : idx + 2]
        idx += 2
        self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp][MsgClusterID][Attribute] = Attribute_type

    if MsgComplete != "01":
        next_start = "%04x" % (int(Attribute, 16) + 1)
        getListofAttribute( self, MsgSrcAddr, MsgSrcEp, MsgClusterID, start_attribute=next_start, )


