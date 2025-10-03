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
Zigbee Linky (TIC Meter) Support Module for Domoticz
====================================================

This module provides helpers and utilities for handling **Linky smart meters** 
via the Zigbee protocol in the Domoticz plugin. It focuses on interpreting, 
decoding, and collecting data from the TIC (Télé-Information Client) interface 
of ERL Z3 Linky devices.

Main Features
-------------
- **Tariff Handling**:
  - `LINKY_TARIF_MATRIX`: Maps raw PTEC values (e.g., HC, HP, EJPHN, EJPHPM) 
    to Domoticz-compatible numeric and string values for display.
  - `linky_tarif_color()`: Converts tariff codes into (nValue, sValue) pairs.

- **Mode Handling**:
  - `LINKY_MODEL_NAME`: Maps numeric values into TIC modes (historique, standard, mono, tri).
  - `linky_mode_tic()`: Returns the configuration dictionary for the Linky TIC mode.

- **Register Decoding**:
  - `decode_registre_status()`: Decodes Linky "registre de statuts" frames into a 
    dictionary of attributes (contact, cutoff organ, overvoltage, energy direction, etc.).

- **Data Collection**:
  - `collect_ticmeter_linky()`: Ensures essential TIC meter fields are present 
    for a given device. If missing, it triggers Zigbee attribute reads with 
    a 5-minute throttle.

Constants
---------
- `LINKY_TARIF_MATRIX` : Maps tariff labels to (nValue, description).
- `LINKY_MODEL_NAME`   : Maps mode values to TIC mode/configuration.
- `TIC_MODE`           : Maps mode IDs to "historique" or "standard".
- `LINKY_GRID`         : Maps grid type IDs to mono/tri.

Functions
---------
- `linky_tarif_color(self, value)`
    Translate Linky PTEC tariff values into Domoticz-compatible values.
- `linky_mode_tic(self, value)`
    Translate Linky TIC mode into mode/configuration.
- `decode_registre_status(registre_status)`
    Decode a raw Linky registre status frame into a structured dictionary.
- `collect_ticmeter_linky(self, nwkid)`
    Collect and update TIC meter attributes if missing, with throttled polling.

Notes
-----
- This module integrates with the Domoticz Zigbee plugin framework and relies 
  on `Modules.readAttributes` to perform actual Zigbee attribute reads.
- Logging is performed through the plugin's `self.log` object.
- The code is specific to ERL Z3 Linky-compatible devices but may be extended 
  for other TIC-based meters.

"""

import time

import Modules.readAttributes

LINKY_TARIF_MATRIX = {
    "BASE": (0, "All Hours"),
    "TH..": (0, "All Hours"),
    
    "HC..": (1, "Off-peak Hours"),
    "HP..": (2, "Peak Hours"),
    "HEURE CREUSE": (1, "Off-peak Hours"),
    "HEURES PLEINES": (2, "Peak Hours"),
    "HEURE CREUSE": (1, "Off-peak Hours"),
    "HEURES PLEINES": (2, "Peak Hours"),

    "00": (1, "Off-peak Hours"),
    "01": (2, "Peak Hours"),

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

LINKY_NTARF_TARIF_MATRIX = {
    0: (0, "All Hours"),
    1: (1, "Off-peak Hours"),
    2: (2, "Peak Hours"),
}

LINKY_MODEL_NAME = {
    0: { "Mode": ('historique', 'mono'), "Conf": "TICMeter-mono" },
    1: { "Mode": ('standard', 'mono'), "Conf": "TICMeter-mono" },
    2: { "Mode": ('historique', 'tri'), "Conf": "TICMeter-tri" },
    3: { "Mode": ('standard', 'tri'), "Conf": "TICMeter-tri" },
    5: { "Mode": ('standard', 'mono prod'), "Conf": "TICMeter-mono-prod" },
    7: { "Mode": ('standard', 'tri prod'), "Conf": "TICMeter-tri-prod" },
}

TIC_MODE = {
    0: "historique",
    1: "standard",
}

LINKY_GRID = {
    0: "mono",
    1: "Triphasé",
}


def linky_tarif_color( self, value ):
    """ Translate the Linky PTEC value to a tuple of nValues and sValues for Domoticz """
    self.log.logging( ["GammaTroniques", "Chameleon"], "Log", f"linky_tarif_color Tarif Color >{value}<")
    return LINKY_TARIF_MATRIX.get(value, (3, f"PTEC: {value} Unknown Tarif"))

def linky_tarif_color_ntarf( self, value ):
    """ Translate the Linky NTARF value to a tuple of nValues and sValues for Domoticz """
    self.log.logging( ["GammaTroniques", "Chameleon"], "Log", f"linky_tarif_color_ntarf Tarif Color >{value}<")
    return LINKY_NTARF_TARIF_MATRIX.get(value, (3, f"NTARF: {value} Unknown Tarif"))

def linky_mode_tic( self, value ):
    """ Translate the Linky TIC Mode value to a dict of Mode and Config file to be used """
    self.log.logging( ["GammaTroniques", "Chameleon"], "Log", f"linky_mode_tic Mode >{value}<")
    return LINKY_MODEL_NAME.get(value, { "Mode": ('unknown', 'unknown'), "Conf": "TICMeter-unknown" })


def decode_registre_status( registre_status):
    """ Decoding of Registre status Linky frame and return a dictionnary of values """

    # Attempt to convert the input into an integer, return an empty dictionary on failure.
    try:
        registre_status = int(registre_status, 16)
    except ValueError:
        return {}

    # Define bit masks and corresponding shifts for each attribute
    ATTRIBUTE_DEFINITIONS = [
        ('contact_sec', 0x00000001, 0),                     # bit 0
        ('organe_coupure', 0x0000000E, 1),                  # bits 1-3
        ('etat_cache_bornes', 0x00000010, 4),               # bit 4
        ('sur_tension', 0x00000040, 6),                     # bit 6
        ('depassement_puissance', 0x00000080, 7),           # bit 7
        ('mode_fonctionnement', 0x00000100, 8),             # bit 8
        ('sens_energie', 0x00000200, 9),                    # bit 9

        ('tarif_fourniture', 0x00003C00, 10),               # bits 10-13
        ('tarif_distributeur', 0x0000C000, 14),             # bits 14-15

        ('mode_horloge', 0x00010000, 16),                   # bit 16
        ('sortie_tic', 0x00020000, 17),                     # bit 17
        ('sortie_euridis', 0x000C0000, 19),                 # bits 19-20

        ('status_cpl', 0x00300000, 21),                     # bits 21-22
        ('synchro_cpl', 0x00800000, 23),                    # bit 23

        ('couleur_jour', 0x03000000, 24),                   # bits 24-25
        ('couleur_demain', 0x0C000000, 26),                 # bits 26-27

        ('preavis_pointe_mobile', 0x30000000, 28),          # bits 28-29
        ('pointe_mobile', 0xC0000000, 30),                  # bits 30-31
    ]

    # Define the mappings for each attribute
    MAPPINGS = {
        'contact_sec': {
            0: "fermé", 1: "ouvert"},
        'etat_cache_bornes': {
            0: "fermé", 1: "ouvert"},
        'mode_fonctionnement': {
            0: "consommateur", 1: "producteur"},
        'sens_energie': {
            0: "énergie active positive", 1: "énergie active négative"},
        'tarif_fourniture': {
            0: "énergie ventilée sur Index 1", 1: "énergie ventilée sur Index 2", 2: "énergie ventilée sur Index 3",
            3: "énergie ventilée sur Index 4", 4: "énergie ventilée sur Index 5", 5: "énergie ventilée sur Index 6",
            6: "énergie ventilée sur Index 7", 7: "énergie ventilée sur Index 8", 8: "énergie ventilée sur Index 9",
            9: "énergie ventilée sur Index 1"},
        'tarif_distributeur': {
            0: "énergie ventilée sur Index 1",
            1: "énergie ventilée sur Index 2",
            2: "énergie ventilée sur Index 3",
            3: "énergie ventilée sur Index 4",
        },
        'Mode_horloge': {
            0: "horloge correcte", 1: "horloge en mode dégradée"},
        'sortie_tic': {
            0: "mode historique", 1: "mode standard"},
        'sortie_euridis': {
            0: "désactivée", 1: "activée sans sécurité", 3: "activée avec sécurité"},
        'status_cpl': {
            0: "New/Unlock", 1: "New/Lock", 2: "Registered"},
        'synchro_cpl': {
            0: "compteur non synchronisé", 1: "compteur synchronisé"},
        'couleur_jour': {
            0: "Pas d'annonce", 1: "Bleu", 2: "Blanc", 3: "Rouge"},
        'couleur_demain': {
            0: "Pas d'annonce", 1: "Bleu", 2: "Blanc", 3: "Rouge"},
        'preavis_pointe_mobile': {
            0: "Pas de pointe mobile", 1: "PM 1 en cours",
            2: "PM 2 en cours", 3: "PM 3 en cours"},
        'pointe_mobile': {
            0: "Pas de pointe mobile", 1: "PM 1 en cours",
            2: "PM 2 en cours", 3: "PM 3 en cours"}
    }

    # Initialize the result dictionary
    result = {}

    # Extract and map each attribute based on the definitions
    for attr, mask, shift in ATTRIBUTE_DEFINITIONS:
        # Extract the value by applying the mask and shifting
        value = (registre_status & mask) >> shift

        # Apply mapping if it exists, otherwise keep the raw value
        result[attr] = MAPPINGS.get(attr, {}).get(value, value)

    return result


def collect_ticmeter_linky(self, nwkid):
    """
    Collects TIC meter data for a given device if essential fields are missing.

    This method checks the current health and status of the TIC meter associated
    with the given network ID (`nwkid`). If the device is live but key data
    (such as TIC mode, tariff, power status, etc.) is missing, it triggers a
    read of all relevant attributes using appropriate modules.

    To avoid excessive polling, a throttle of 5 minutes is applied between
    read attempts using the "GlobalReadInProgress" timestamp.

    Parameters:
        nwkid (str): The network ID of the device to be checked and updated.

    Returns:
        None
    """
    device = self.ListOfDevices.get(nwkid)
    if not device:
        return

    if device.get("Health") != "Live":
        return

    ticmeter_data = device.setdefault("GammaTroniques", {})

    tic_mode = ticmeter_data.get("ModeTIC")
    elec_mode = ticmeter_data.get("ModeElec")
    tarif = ticmeter_data.get("OPTARIF") or ticmeter_data.get("NGTF")
    ptec = ticmeter_data.get("PTEC") or ticmeter_data.get("LTARF")
    pref = ticmeter_data.get("pref") or ticmeter_data.get("PREF")
    uptime = ticmeter_data.get("UpTime")

    if any(x is None for x in (tic_mode, elec_mode, tarif, ptec, pref, uptime)):
        last_read_time = ticmeter_data.get("GlobalReadInProgress")
        now = time.time()

        if last_read_time is not None and last_read_time > now - 300:
            # Avoid repeated reads within 5 minutes
            return

        self.log.logging("Pairing", "Status", "Reading TICMeter and collecting all data, as key data are missing")

        Modules.readAttributes.read_attributes_gammatroniques_tic_meter(self, nwkid)
        Modules.readAttributes.read_attributes_ticmeter_tarif(self, nwkid)
        Modules.readAttributes.read_attributes_ticmeter_details(self, nwkid)

        ticmeter_data["GlobalReadInProgress"] = now
