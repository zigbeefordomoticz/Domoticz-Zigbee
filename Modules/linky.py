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


LINKY_TARIF_MATRIX = {
    "BASE": (0, "All Hours"),
    "TH..": (0, "All Hours"),
    "HC..": (1, "Off-peak Hours"),
    "HP..": (2, "Peak Hours"),

    "HEURES CREUSES": (1, "Off-peak Hours"),
    "HEURES PLEINES": (2, "Peak Hours"),
    
    "HN..": (1, "Normal Hours"),
    "EJPHN": (1, "Normal Hours"),
    "PM..": (4, "Mobile Peak Hours"),
    "EJPHPM": (4, "Mobile Peak Hours"),

    "BHC": (1, "Bleu HC"),
    "BHP": (1, "Bleu HP"),
    "HCJB": (1, "Bleu HC"),
    "HPJB": (1, "Bleu HP"),          

    "WHC": (2, "Blanc HC"),
    "WHP": (2, "Blanc HP"),
    "HCJW": (2, "Blanc HC"),
    "HPJW": (2, "Blanc HP"),

    "RHC": (4, "Rouge HC"),
    "RHP": (4, "Rouge HP"),
    "HCJR": (4, "Rouge HC"),
    "HPJR": (4, "Rouge HP")
}


LINKY_MODE = {
    0: { "Mode": ('historique', 'mono'), "Conf": "TICMeter-mono" },
    1: { "Mode": ('standard', 'mono'), "Conf": "TICMeter-mono" },
    2: { "Mode": ('historique', 'tri'), "Conf": "TICMeter-tri" },
    3: { "Mode": ('standard', 'tri'), "Conf": "TICMeter-tri" },
    5: { "Mode": ('standard', 'mono prod'), "Conf": "TICMeter-mono-prod" },
    7: { "Mode": ('standard', 'tri prod'), "Conf": "TICMeter-tri-prod" },
}


def linky_tarif_color( value ):
    """ Translate the Linky PTEC value to a tuple of nValues and sValues for Domoticz """

    return LINKY_TARIF_MATRIX.get(value, (3, "Unknown Tarif"))
   
def linky_mode_tic( value ):
    """ Translate the Linky TIC Mode value to a dict of Mode and Config file to be used """

    return LINKY_MODE.get(value, { "Mode": ('unknown', 'unknown'), "Conf": "TICMeter-unknown" })
        
        