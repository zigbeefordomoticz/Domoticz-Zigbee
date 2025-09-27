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

import json
from datetime import timedelta

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.linky import LINKY_GRID, TIC_MODE, decode_registre_status
from Modules.tools import get_device_nickname

CHAMELEON_ERL = "Chameleon"


def _retreive_chameleon_nwkids(self):
    """Returns a list of network IDs that contain a mwa_tic."""
    return [nwid for nwid in self.ListOfDevices if CHAMELEON_ERL in self.ListOfDevices[nwid]]


def _retreive_ticmode_human_readable(mode_tic,):
    return 'Unknown' if mode_tic is None else TIC_MODE.get(mode_tic, 'Unknown')


def _retreive_mode_elec_human_readable(mode_elec):
    return 'Unknown' if mode_elec is None else LINKY_GRID.get(mode_elec, 'Unknown')


def rest_chameleon_tic(self, verb, data, parameters): 

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    _chameleon_tic_response = []
    self.logging( "Debug", "rest_mwa_tic - for %s %s %s" % (verb, data, parameters))

    # find if we have a MWA-TIC
    chameleon_tic_list = _retreive_chameleon_nwkids(self)
    self.logging( "Debug", f"rest_mwa_tic - identified {chameleon_tic_list}" )
    
    for chameleon_tic in chameleon_tic_list:
        self.logging( "Debug", f"rest_mwa_tic - processing {chameleon_tic}" )

        chameleon_tic_infos = self.ListOfDevices[ chameleon_tic ]
        chameleon_tic_attributes = chameleon_tic_infos.get(CHAMELEON_ERL)
        chameleon_tic_ep = chameleon_tic_infos.get("Ep",{}).get("01")
        chameleon_tic_0000 = chameleon_tic_ep.get("0000",{})
        chameleon_tic_0b01 = chameleon_tic_ep.get("0b01")
        
        if chameleon_tic_attributes is None:
            continue

        device = {
            'Nwkid': chameleon_tic,
            'ZDeviceName': get_device_nickname( self, NwkId=chameleon_tic),
            'Identifiant': chameleon_tic_attributes.get('ADCO','Unknown'),
            'Point de livraison (PDL, PRM)': chameleon_tic_attributes.get('PRM','Unknown'),
            'TICMode': _retreive_ticmode_human_readable(chameleon_tic_attributes.get('LINKY_MODE', 'Unknown')),
            'Type de contrat': chameleon_tic_attributes.get('NGTF/OPTARIF', 'Unknown'),
            'Période tarifaire en cours': chameleon_tic_attributes.get('PTEC/LTARF', 'Unknown'),
            'Période tarifaire demain': chameleon_tic_attributes.get('STGE/DEMAIN', 'Unknown'),
            'Puissance Max contrat': chameleon_tic_attributes.get('PREF/ISOUSC', 'Unknown'),
            'Parameters': []
        }

        device["Parameters"].append( { "Version Firmware": chameleon_tic_0000.get("4000") })
        
        for mwa_tic_param in chameleon_tic_attributes:
            if mwa_tic_param == 'MOTDETAT' and chameleon_tic_attributes[ mwa_tic_param ]:
                attr_value = decode_registre_status( chameleon_tic_attributes[ mwa_tic_param ])
            else:
                attr_value = chameleon_tic_attributes[ mwa_tic_param ]
            device["Parameters"].append( { mwa_tic_param: attr_value } )

        _chameleon_tic_response.append( device )
        
    if verb == "GET" and len(parameters) == 0:
        if self.fake_mode():
            _response["Data"] = json.dumps(fake_chameleon_tic(), sort_keys=False)
            return _response

        _response["Data"] = json.dumps(_chameleon_tic_response, sort_keys=False)
    return _response


def fake_chameleon_tic():

    return [
        {
            "Nwkid": "abcd",
            "ZDeviceName": "The Fake chameleon_tic",
            "Parameters": [
                { "ModeTIC": 0 },
                { "PTEC": "HEURES PLEINES" },
                { "HCHC": 1691584 },
                { "HCHP": 1920319 },
                { "Total": 3620688 },
                { "UpTime": 2869423},
                { "OPTARIF": "HCHP 22h-6h"},
                { "date_time": "0000000067e3d963"},
                { "ModeElec": 1}
            ],
        }
    ]
