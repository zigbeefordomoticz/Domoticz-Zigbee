#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""
    Module: manufacturer_code.py
 
    Description: 

"""

MANUFACTURER_NAME_TO_CODE = {
    "EMBER": "1002",
    "PHILIPS": "100b",
    "frient A/S": "1015",
    "LEGRAND": "1021",
    "VANTAGE": "1021",
    "LUMI": "1037",
    "SCHNEIDER ELECTRIC": "105e",
    "COMPUTIME": "1078",
    "PROFALUX": "1110",
    "DANALOCK": "115c",
    "OSRAM": "110c",
    "OWON": "113c",
    "XIAOMI": "115f",
    "INNR": "1166",
    "IKEA OF SWEDEN": "117c",
    "LEDVANCE": "1189",
    "HEIMAN": "120b",
    "DANFOSS": "1246",
    "KONKE": "1268",
    "OSRAM-2": "bbaa",
    "Develco": "1015",
}

TUYA_PREFIX = (
    "_TZ",
    "_TY",
)
TUYA_MANUF_CODE = 1002


def check_and_update_manufcode(self):

    for nwkid in list(self.ListOfDevices):
        if "Manufacturer Name" in self.ListOfDevices[nwkid]:
            if str(self.ListOfDevices[nwkid]["Manufacturer Name"]).upper() in MANUFACTURER_NAME_TO_CODE:
                if (
                    self.ListOfDevices[nwkid]["Manufacturer"]
                    != MANUFACTURER_NAME_TO_CODE[str(self.ListOfDevices[nwkid]["Manufacturer Name"]).upper()]
                ):
                    self.ListOfDevices[nwkid]["Manufacturer"] = MANUFACTURER_NAME_TO_CODE[
                        str(self.ListOfDevices[nwkid]["Manufacturer Name"]).upper()
                    ]

            elif self.ListOfDevices[nwkid]["Manufacturer Name"][:3] in TUYA_PREFIX:
                # Tuya
                if self.ListOfDevices[nwkid]["Manufacturer"] != TUYA_MANUF_CODE:
                    self.ListOfDevices[nwkid]["Manufacturer"] = TUYA_MANUF_CODE

PREFIX_MAC_LEN = 6
PREFIX_MACADDR_IKEA_TRADFRI = ( "000d6f", "14b457")
PREFIX_MACADDR_DEVELCO = ( "0015bc", )
PREFIX_MACADDR_TUYA = ( "842e14", "847127", "84fd27", "588e81", "60a423", "a4c138", "b4e3f9", "bc33ac", )
PREFIX_MACADDR_LEGRAND = ( "000474", )
PREFIX_MACADDR_PROFALUX = ( "20918a", )
PREFIX_MACADDR_WIZER_LEGACY = ( "00124b", )
PREFIX_MACADDR_WIZER_HOME = ( "588E81", )
PREFIX_MACADDR_LIVOLO = ( "00124b", )
PREFIX_MACADDR_XIAOMI = ( "00158d", )  # Seems to be also INR
PREFIX_MACADDR_OPPLE = ( "04cf8c", )
PREFIX_MACADDR_CASAIA = ( "90fd9f", "3c6a2c")