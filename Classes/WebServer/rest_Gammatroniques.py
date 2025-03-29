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

GAMMATRONIQUES = "GammaTroniques"



def format_uptime(milliseconds):
    seconds = milliseconds // 1000 
    td = timedelta(seconds=seconds)
    days, remainder = divmod(td.total_seconds(), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return f"{int(days)}d {int(hours):02}:{int(minutes):02}:{int(seconds):02}"


def _retreive_ticmeter_nwkids(self):
    """Returns a list of network IDs that contain a TICMeter."""
    return [nwid for nwid in self.ListOfDevices if GAMMATRONIQUES in self.ListOfDevices[nwid]]


def _retreive_ticmode_human_readable(mode_tic,):
    return 'Unknown' if mode_tic is None else TIC_MODE.get(mode_tic, 'Unknown')


def _retreive_mode_elec_human_readable(mode_elec):
    return 'Unknown' if mode_elec is None else LINKY_GRID.get(mode_elec, 'Unknown')


def rest_TICMeter(self, verb, data, parameters): 

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    _ticmeter_response = []
    self.logging( "Debug", "rest_TICMeter - for %s %s %s" % (verb, data, parameters))
    # find if we have a ZLinky
    tic_meters_list = _retreive_ticmeter_nwkids(self)
    self.logging( "Debug", f"rest_TICMeter - identified {tic_meters_list}" )
    
    for ticmeter in tic_meters_list:
        self.logging( "Debug", f"rest_TICMeter - processing {ticmeter}" )

        ticmeter_infos = self.ListOfDevices[ ticmeter ]
        ticmeter_gamma = ticmeter_infos.get(GAMMATRONIQUES)
        ticmeter_ep = ticmeter_infos.get("Ep",{}).get("01")
        ticmeter_0000 = ticmeter_ep.get("0000",{})
        #ticmeter_0702 = ticmeter_ep.get("0702")
        #ticmeter_0b04 = ticmeter_ep.get("0b04")
        #ticmeter_0b01 = ticmeter_ep.get("0b01")
        
        if ticmeter_gamma is None:
            continue

        device = {
            'Nwkid': ticmeter,
            'ZDeviceName': get_device_nickname( self, NwkId=ticmeter),
            'Identifiant': f"{int( ticmeter_gamma['Identifiant'])}" if "Identifiant" in ticmeter_gamma else "Unknown",
            'TICMode': _retreive_ticmode_human_readable(ticmeter_gamma.get('ModeTIC')),
            'Mode Electrique': _retreive_mode_elec_human_readable( ticmeter_gamma.get('ModeElec') ),
            'Type de contrat': ticmeter_gamma.get('OPTARIF') or ticmeter_gamma.get('NGTF', 'Unknown'),
            'Période tarifaire en cours': ticmeter_gamma.get('PTEC') or ticmeter_gamma.get('LTARF', 'Unknown'),
            'Puissance Max contrat': ticmeter_gamma.get('pref') or ticmeter_gamma.get('PREF', 'Unknown'),
            'UpTime': format_uptime(ticmeter_gamma.get('UpTime', 0)),
            'Parameters': []
        }

        device["Parameters"].append( { "Code date": ticmeter_0000.get("0006") })
        
        for ticmeter_param in ticmeter_gamma:
            if ticmeter_param == 'MOTDETAT' and ticmeter_gamma[ ticmeter_param ]:
                attr_value = decode_registre_status( ticmeter_gamma[ ticmeter_param ])
            elif ticmeter_param == 'UpTime':
                attr_value = format_uptime(ticmeter_gamma.get('UpTime', 0)),
            else:
                attr_value = ticmeter_gamma[ ticmeter_param ]
            device["Parameters"].append( { ticmeter_param: attr_value } )

        _ticmeter_response.append( device )
        
    if verb == "GET" and len(parameters) == 0:
        if self.fake_mode():
            _response["Data"] = json.dumps(fake_ticmeter(), sort_keys=False)
            return _response

        _response["Data"] = json.dumps(_ticmeter_response, sort_keys=False)
    return _response


def fake_ticmeter():

    return [
        {
            "Nwkid": "abcd",
            "ZDeviceName": "The Fake TICMeter",
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
