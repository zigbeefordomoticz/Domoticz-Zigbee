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


from Modules.pluginDbAttributes import (STORE_CONFIGURE_REPORTING,
                                        STORE_READ_CONFIGURE_REPORTING)

ATTR_ZLINKY = "ZLinky"
ATTR_PROTO_LINKY = "PROTOCOL Linky"

ISOUSC_THRESHOLD_MAX = 98
ISOUSC_THRESHOLD_MED = 90

TENSION_NOMINAL = 230
KILO = 1000

ZLINK_CONF_MODEL = (
    "ZLinky_TIC",
    "ZLinky_TIC-historique-mono" , "ZLinky_TIC-historique-tri",
    "ZLinky_TIC-standard-mono", "ZLinky_TIC-standard-tri",
    "ZLinky_TIC-standard-mono-prod", "ZLinky_TIC-standard-tri-prod"
    )

ZLINKY_MODE = {
    0: { "Mode": ('historique', 'mono'), "Conf": "ZLinky_TIC-historique-mono" },
    1: { "Mode": ('standard', 'mono'), "Conf": "ZLinky_TIC-standard-mono" },
    2: { "Mode": ('historique', 'tri'), "Conf": "ZLinky_TIC-historique-tri" },
    3: { "Mode": ('standard', 'tri'), "Conf": "ZLinky_TIC-standard-tri" },
    5: { "Mode": ('standard', 'mono prod'), "Conf": "ZLinky_TIC-standard-mono-prod" },
    7: { "Mode": ('standard', 'tri prod'), "Conf": "ZLinky_TIC-standard-tri-prod" },
}

ZLINKY_UPGRADE_PATHS = { 
    "ZLinky_TIC": (
        "ZLinky_TIC-historique-mono", "ZLinky_TIC-historique-tri",
        "ZLinky_TIC-standard-mono", "ZLinky_TIC-standard-mono-prod",
        "ZLinky_TIC-standard-tri", "ZLinky_TIC-standard-tri-prod"),
    "ZLinky_TIC-historique-mono": ( "ZLinky_TIC-standard-mono", "ZLinky_TIC-standard-mono-prod"),
    "ZLinky_TIC-historique-tri": ( "ZLinky_TIC-standard-tri", "ZLinky_TIC-standard-tri-prod" ),
    "ZLinky_TIC-standard-mono-prod": (),
    "ZLinky_TIC-standard-tri": (),
    "ZLinky_TIC-standard-tri-prod": (),
}
ZLinky_TIC_COMMAND = {
    # Mode Historique
    "0000": "OPTARIF",
    "0001": "DEMAIN",
    "0002": "HHPHC",
    "0003": "PPOT",
    "0004": "PEJP",
    "0005": "ADPS",
    "0006": "ADIR1",
    "0007": "ADIR2",
    "0008": "ADIR3",
    "0009": "MOTDETAT",

    # Mode standard
    "0200": "LTARF",
    "0201": "NTARF",
    "0202": "DATE",
    "0203": "EASD01",
    "0204": "EASD02",
    "0205": "EASD03",
    "0206": "EASD04",
    "0207": "SINSTI",
    "0208": "SMAXIN",
    "0209": "SMAXIN-1",
    "0210": "CCAIN",
    "0211": "CCAIN-1",
    "0212": "SMAXN-1",
    "0400": "SMAXN-1",
    "0213": "SMAXN2-1",
    "0214": "SMAXN3-1",
    "0215": "MSG1",
    "0216": "MSG2",
    "0217": "STGE",
    "0218": "DPM1",
    "0219": "FPM1",
    "0220": "DPM2",
    "0221": "FPM2",
    "0222": "DPM3",
    "0223": "FPM3",
    "0224": "RELAIS",
    "0225": "NJOURF",
    "0226": "NJOURF+1",
    "0227": "PJOURF+1",
    "0228": "PPOINTE1",
    "0300": ATTR_PROTO_LINKY
}

OP_TARIFAIRE_MAP = {
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
    "HPJR": (4, "Rouge HP"),
   
}



def get_notification_day_color(value):
    """Determine the numeric and string representation of the day color and peak status for Domoticz UpdateDevice()"""

    # Check if value exists in color_map
    if value in OP_TARIFAIRE_MAP:
        return OP_TARIFAIRE_MAP[value]

    # Fallback for values starting with B/W/R
    color_prefix_map = {
        "B": [ 1, "Blue Hours"],
        "W": [ 2, "White Hours"],
        "R": [ 4, "Red Hours"]
    }

    return color_prefix_map.get(value[0], (3, "Unknown"))  # Default to (3, "Unknown") if no match


def convert_kva_to_ampere( kva ):
    return ( kva * KILO) / TENSION_NOMINAL


def zlinky_color_tarif(self, nwkid, color):
    self.ListOfDevices.setdefault(nwkid, {}).setdefault(ATTR_ZLINKY, {})["Color"] = color


def store_ZLinky_infos(self, nwkid, command_tic, value):
    zlinky_dict = self.ListOfDevices[nwkid].setdefault('ZLinky', {})
    zlinky_dict[command_tic] = value


def get_ISOUSC(self, nwkid):
    # Retrieve 'ISOUSC' if it exists
    if 'ISOUSC' in self.ListOfDevices[nwkid]:
        return self.ListOfDevices[nwkid]['ISOUSC']

    # Retrieve 'PROTOCOL Linky' from 'ZLinky' if it exists
    protocol_linky = self.ListOfDevices[nwkid].get('ZLinky', {}).get('PROTOCOL Linky')

    # Retrieve '000d' from nested dictionaries in 'Ep'
    isousc_from_cluster_0b01 = self.ListOfDevices[nwkid].get('Ep', {}).get('01', {}).get('0b01', {}).get('000d', 0)

    if isousc_from_cluster_0b01:
        # Check protocol and convert if necessary
        if protocol_linky in (0, 2):
            return isousc_from_cluster_0b01
        return convert_kva_to_ampere(isousc_from_cluster_0b01)

    return 0


def get_OPTARIF(self, nwkid):
    """
    Retrieves the 'OPTARIF' value for a given network ID (nwkid) from the 'ZLinky' device data.

    If the 'OPTARIF' value is found and is a byte string, it decodes it to a regular string
    and removes any null byte characters. If 'OPTARIF' is not found or if it's not a byte
    string, the method returns the default value "BASE".

    Args:
        nwkid (str): The network ID used to access the device data in ListOfDevices.

    Returns:
        str: The cleaned 'OPTARIF' value, or "BASE" if not found.
    """
    def _normalize_tarif(op_tarifaire):
        """ Normalize Op Tarif """
        if op_tarifaire.startswith("BBR"):
            base_tarifaire = "TEMPO"  # Treat any BBRx as TEMPO
        elif op_tarifaire.startswith("EJP"):
            base_tarifaire = "EJP"  # Treat any EJPx as EJP
        else:
            base_tarifaire = op_tarifaire
        return base_tarifaire

    zlinky = self.ListOfDevices.get(nwkid, {}).get(ATTR_ZLINKY, {})

    # Get the raw value of "OPTARIF", or default to "BASE"
    optarif_value = zlinky.get("OPTARIF")
    
    if optarif_value is None:
        return None

    # If the value is a byte string, decode and clean up
    if isinstance(optarif_value, bytes):
        # Decode the byte string to UTF-8, ignoring errors, and remove null bytes
        optarif_value = optarif_value.decode('utf-8', errors='ignore').strip('\x00')

    # Remove null characters and strip whitespace
    if isinstance(optarif_value, str):
        optarif_value = optarif_value.replace('\u0000', '').replace('\x00', '').strip()

    return _normalize_tarif(optarif_value)


def get_instant_power(self, nwkid):
    try:
        device = self.ListOfDevices.get(nwkid, {})
        ep = device.get("Ep", {}).get("01", {})
        cluster = ep.get("0b04", {})
        power = cluster.get("050f")
        return round(float(power), 2) if power is not None else 0
    except (ValueError, TypeError):
        return 0


def get_tarif_color(self, nwkid):
    return self.ListOfDevices.get(nwkid, {}).get(ATTR_ZLINKY, {}).get("Color")


def get_ptec(self, nwkid):
    """ Retreive Current Tarif. (Historic)"""
    return self.ListOfDevices.get(nwkid, {}).get(ATTR_ZLINKY, {}).get("PTEC")


def get_ltarf(self, nwkid):
    """ Retreive Current Tarif. (Standard)"""

    _ltarf = self.ListOfDevices.get(nwkid, {}).get(ATTR_ZLINKY, {}).get("LTARF")
    # If the value is a byte string, decode and clean up
    if isinstance(_ltarf, bytes):
        # Decode the byte string to UTF-8, ignoring errors, and remove null bytes
        _ltarf = _ltarf.decode('utf-8', errors='ignore').strip('\x00')

    # Remove null characters and strip whitespace
    if isinstance(_ltarf, str):
        _ltarf = _ltarf.replace('\u0000', '').replace('\x00', '').strip()

    return _ltarf


def zlinky_check_alarm(self, Devices, MsgSrcAddr, MsgSrcEp, value):

    if value == 0:
        return "00|Normal"

    isousc = get_ISOUSC( self, MsgSrcAddr )

    if isousc == 0:
        return "00|Normal"

    flevel = (value * 100) / isousc
    self.log.logging( "Cluster", "Debug", "zlinky_check_alarm - %s/%s flevel- %s %s %s" % (MsgSrcAddr, MsgSrcEp, value, isousc, flevel), MsgSrcAddr, )

    if flevel > ISOUSC_THRESHOLD_MAX:
        self.log.logging( "Cluster", "Debug", "zlinky_check_alarm - %s/%s Alarm-01" % (MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
        return "03|Reach >98 %% of Max subscribe %s" % (isousc)

       
    elif flevel > ISOUSC_THRESHOLD_MED:
        self.log.logging( "Cluster", "Debug", "zlinky_check_alarm - %s/%s Alarm-02" % (MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
        return "02|Reach >90 %% of Max subscribe %s" % (isousc)

        
    self.log.logging( "Cluster", "Debug", "zlinky_check_alarm - %s/%s Alarm-03" % (MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
    return "00|Normal"


def linky_mode(self, nwkid, protocol=False):
    """Retrieve the Linky mode for a given device."""

    # Get or set "PROTOCOL Linky" only if it hasn't been set
    zlinky_data = self.ListOfDevices.setdefault(nwkid, {}).setdefault(ATTR_ZLINKY, {})

    if ATTR_PROTO_LINKY not in zlinky_data:
        protocol_linky = get_linky_mode_from_ep(self, nwkid)
        if protocol_linky is None:
            return None  # Do nothing if get_linky_mode_from_ep returns None
        zlinky_data[ATTR_PROTO_LINKY] = protocol_linky
    else:
        protocol_linky = zlinky_data[ATTR_PROTO_LINKY]

    if protocol:
        return protocol_linky  # Return protocol name if requested

    return ZLINKY_MODE.get(protocol_linky, {}).get("Mode")


def get_linky_mode_from_ep(self, nwkid):
    """Retrieve the Linky protocol mode from endpoint data."""

    protocol_linky = (
        self.ListOfDevices
        .get(nwkid, {})
        .get("Ep", {})
        .get("01", {})
        .get("ff66", {})
        .get("0300")
    )

    return protocol_linky if protocol_linky in ZLINKY_MODE else None


def linky_device_conf(self, nwkid):
    device = self.ListOfDevices.get(nwkid, {})
    zlinky_info = device.get('ZLinky', {})
    protocol_linky = zlinky_info.get('PROTOCOL Linky')

    if not protocol_linky:
        mode = get_linky_mode_from_ep(self, nwkid)
        if mode:
            self.log.logging("Cluster", "Status", f"linky_device_conf {nwkid} found 0xff66/0x0300: {mode}")
            zlinky_info['PROTOCOL Linky'] = mode
            return ZLINKY_MODE[mode]["Conf"]
        else:
            return "ZLinky_TIC"

    if protocol_linky not in ZLINKY_MODE:
        return "ZLinky_TIC"
    
    self.log.logging("Cluster", "Debug", f"linky_device_conf {nwkid} found Protocol Linky: {protocol_linky}")
    return ZLINKY_MODE[protocol_linky]["Conf"]

 
def linky_upgrade_authorized( current_model, new_model ):

    return (
        current_model in ZLINKY_UPGRADE_PATHS
        and new_model in ZLINKY_UPGRADE_PATHS[current_model]
    )


def update_zlinky_device_model_if_needed(self, nwkid):
    """Update ZLinky device model if an upgrade is authorized and necessary."""

    device_info = self.ListOfDevices.get(nwkid, {})
    model_name = device_info.get("Model")

    if not model_name:
        return

    zlinky_conf = linky_device_conf(self, nwkid)

    if not linky_upgrade_authorized(model_name, zlinky_conf):
        self.log.logging("ZLinky", "Log", f"Not authorized to adjust ZLinky model from {model_name} to {zlinky_conf}")
        return

    self.log.logging("ZLinky", "Status", f"Adjusting ZLinky model from {model_name} to {zlinky_conf}")

    # Update the model name
    device_info["Model"] = zlinky_conf

    # Remove outdated attributes to trigger a fresh read
    for key in ["ReadAttributes", ATTR_ZLINKY, STORE_CONFIGURE_REPORTING, STORE_READ_CONFIGURE_REPORTING]:
        device_info.pop(key, None)

    # Force configuration reporting if enabled
    if self.configureReporting:
        self.configureReporting.check_configuration_reporting_for_device(nwkid, force=True)

    # Reset heartbeat status
    device_info["Heartbeat"] = "-1"


CONTACT_SEC = {
    0: "fermé",
    1: "ouvert"
}
ETAT_CACHE_BORNES = {
    0: "fermé",
    1: "ouvert"
}
FONCTION_PROD_CONSO = {
    0: "consommateur",
    1: "producteur"
}
SENS_ENERGIE = {
    0: "énergie active positive",
    1: "énergie active négative"
}
HORLOGE = {
    0: "horloge correcte",
    1: "horloge en mode dégradée"
}
SORTIE_TIC = {
    0: "mode historique",
    1: "mode standard"
}
SORTIE_EURIDIS = {
    0: "désactivée",
    1: "activée sans sécurité",
    3: "activée avec sécurité"
}
STATUT_CPL = {
    0: "New/Unlock",
    1: "New/Lock",
    3: "Registered"
}
SYNCHRO_CPL = {
    0: "compteur non synchronisé",
    1: "compteur synchronisé"
}
COULEUR = {
    0: "néant",
    1: "Bleu",
    2: "Blanc",
    3: "Rouge"
}


def decode_STEG(stge):
    """ Decoding of STGE Linky frame """

    # Attempt to convert the input into an integer, return an empty dictionary on failure.
    try:
        stge = int(stge, 16)
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
        value = (stge & mask) >> shift

        # Apply mapping if it exists, otherwise keep the raw value
        result[attr] = MAPPINGS.get(attr, {}).get(value, value)

    return result


def zlinky_sum_all_indexes(self, nwkid):
    zlinky_info = self.ListOfDevices.get(nwkid, {}).get(ATTR_ZLINKY, {})
    return zlinky_info.get("INDEX_MID", {}).get("CompteurTotalisateur", 0)



def zlinky_totalisateur(self, nwkid, attribute, value):
    """
    Updates the total energy consumption index ('CompteurTotalisateur') for a ZLinky device.

    This method computes the sum of specific measurement indexes from the ZLinky 0702 cluster
    and updates the stored total under the device's `INDEX_MID` dictionary.

    Parameters:
        nwkid (str): The network ID of the device.
        attribute (str): The attribute name triggering the update (unused in this function).
        value (Any): The new value received (unused in this function).

    Notes:
        - If the required 0702 cluster is not found under endpoint "01", an error is logged and the method exits.
        - Only specific attribute keys are summed, as defined in `ZLINKY_INDEX_KEYS`.
    """
    ZLINKY_INDEX_KEYS = {"0100", "0102", "0104", "0106", "0108", "010a"}
    ENDPOINT = "01"
    CLUSTER_ID = "0702"

    # Get device info or initialize structure
    zlinky_info = self.ListOfDevices.setdefault(nwkid, {}).setdefault(ATTR_ZLINKY, {})
    index_mid_info = zlinky_info.setdefault("INDEX_MID", {"CompteurTotalisateur": 0})
    prev_total = index_mid_info["CompteurTotalisateur"]
    
    # Access the cluster
    ep = self.ListOfDevices[nwkid].get("Ep", {})
    cluster = ep.get(ENDPOINT, {}).get(CLUSTER_ID)

    if cluster is None:
        self.log.logging("ZLinky", "Error", f"zlinky_totalisateur: {nwkid} has no cluster {CLUSTER_ID}")
        return

    # Compute the total
    total = sum(cluster.get(key, 0) for key in ZLINKY_INDEX_KEYS)

    # Update and log
    
    index_mid_info["CompteurTotalisateur"] = total
    self.log.logging("ZLinky", "Debug", f"zlinky_totalisateur from: {prev_total} to {total}")
