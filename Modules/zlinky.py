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

import time

from Modules.pluginDbAttributes import (STORE_CONFIGURE_REPORTING,
                                        STORE_READ_CONFIGURE_REPORTING)

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
        "ZLinky_TIC-historique-mono",
        "ZLinky_TIC-historique-tri",
        "ZLinky_TIC-standard-mono",
        "ZLinky_TIC-standard-mono-prod", 
        "ZLinky_TIC-standard-tri",
        "ZLinky_TIC-standard-tri-prod" 
        ),
    "ZLinky_TIC-historique-mono": ( 
        "ZLinky_TIC-standard-mono",
        "ZLinky_TIC-standard-mono-prod",
        ),
    "ZLinky_TIC-historique-tri": ( 
        "ZLinky_TIC-standard-tri",
        "ZLinky_TIC-standard-tri-prod" 
        ),
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
    "0300": "PROTOCOL Linky"
}

def convert_kva_to_ampere( kva ):
    return ( kva * 1000) / 200

def zlinky_color_tarif(self, MsgSrcAddr, color):
    if "ZLinky" not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["ZLinky"] = {}
    self.ListOfDevices[MsgSrcAddr]["ZLinky"]["Color"] = color

def store_ZLinky_infos( self, nwkid, command_tic, value):

    if 'ZLinky' not in self.ListOfDevices[ nwkid ]:
        self.ListOfDevices[ nwkid ][ 'ZLinky' ] = {}
    self.ListOfDevices[ nwkid ][ 'ZLinky' ][ command_tic ] = value

def get_ISOUSC( self, nwkid ):

    if (
        "ZLinky" in self.ListOfDevices[nwkid] 
        and "ISOUSC" in self.ListOfDevices[nwkid]["ZLinky"]
    ):
        return self.ListOfDevices[nwkid]["ZLinky"]["ISOUSC"]

    ampere = False
    if (
        "ZLinky" in self.ListOfDevices[nwkid] 
        and "PROTOCOL Linky" in self.ListOfDevices[nwkid]["ZLinky"]
        and self.ListOfDevices[nwkid]["ZLinky"]["PROTOCOL Linky"] in (0, 2)
    ):
        # We are in Historique mode , so value is given in Ampere
        ampere = True

    # Let's check if we have in the Ep values
    if (
        "Ep" in self.ListOfDevices[nwkid]
        and "01" in self.ListOfDevices[nwkid]["Ep"]
        and "0b01" in self.ListOfDevices[nwkid]["Ep"]["01"]
        and "000d" in self.ListOfDevices[nwkid]["Ep"]["01"]["0b01"]
    ):

        if ampere:
            return self.ListOfDevices[nwkid]["Ep"]["01"]["0b01"]["000d"]

        return convert_kva_to_ampere( self.ListOfDevices[nwkid]["Ep"]["01"]["0b01"]["000d"] )

    return 0

def get_OPTARIF( self, nwkid):

    if (
        "ZLinky" in self.ListOfDevices[nwkid] 
        and "OPTARIF" in self.ListOfDevices[nwkid]["ZLinky"]
    ):
        return self.ListOfDevices[nwkid]["ZLinky"]["OPTARIF"]

    return "BASE"

def get_instant_power( self, nwkid ):
    return round(float(self.ListOfDevices[nwkid]["Ep"]["01"]["0b04"]["050f"]), 2) if "0b04" in self.ListOfDevices[nwkid]["Ep"]["01"] and "050f" in self.ListOfDevices[nwkid]["Ep"]["01"]["0b04"] else 0

def get_tarif_color( self, nwkid ):
    return self.ListOfDevices[nwkid]["ZLinky"]["Color"] if "ZLinky" in self.ListOfDevices[nwkid] and "Color" in self.ListOfDevices[nwkid]["ZLinky"] else None
   
    
def zlinky_check_alarm(self, Devices, MsgSrcAddr, MsgSrcEp, value):

    if value == 0:
        return "00|Normal"

    Isousc = get_ISOUSC( self, MsgSrcAddr )

    if Isousc == 0:
        return "00|Normal"

    flevel = (value * 100) / Isousc
    self.log.logging( "Cluster", "Debug", "zlinky_check_alarm - %s/%s flevel- %s %s %s" % (MsgSrcAddr, MsgSrcEp, value, Isousc, flevel), MsgSrcAddr, )

    if flevel > 98:
        self.log.logging( "Cluster", "Debug", "zlinky_check_alarm - %s/%s Alarm-01" % (MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
        return "03|Reach >98 %% of Max subscribe %s" % (Isousc)

       
    elif flevel > 90:
        self.log.logging( "Cluster", "Debug", "zlinky_check_alarm - %s/%s Alarm-02" % (MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
        return "02|Reach >90 %% of Max subscribe %s" % (Isousc)

        
    self.log.logging( "Cluster", "Debug", "zlinky_check_alarm - %s/%s Alarm-03" % (MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
    return "00|Normal"
        


def linky_mode( self, nwkid , protocol=False):
    
    if 'ZLinky' not in self.ListOfDevices[ nwkid ]:
        return None
    
    if 'PROTOCOL Linky' not in self.ListOfDevices[ nwkid ]['ZLinky']:
        return get_linky_mode_from_ep(self, nwkid )
    
    if self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] in ZLINKY_MODE and not protocol:
        return ZLINKY_MODE[ self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] ]["Mode"]
    elif protocol:
        return self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky']

    return None


def get_linky_mode_from_ep(self, nwkid):
    ep = self.ListOfDevices.get(nwkid, {}).get("Ep", {}).get("01", {}).get("ff66", {}).get("0300")
    return ep if ep in ZLINKY_MODE else None


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

def update_zlinky_device_model_if_needed( self, nwkid ):
    
    if "Model" not in self.ListOfDevices[ nwkid ]:
        return

    zlinky_conf = linky_device_conf(self, nwkid)

    if self.ListOfDevices[ nwkid ]["Model"] != zlinky_conf:
        if not linky_upgrade_authorized( self.ListOfDevices[ nwkid ]["Model"], zlinky_conf ):
            self.log.logging( "ZLinky", "Log", "Not authorized adjustement ZLinky model from %s to %s" %( 
                self.ListOfDevices[ nwkid ]["Model"], zlinky_conf  ))
            return

        self.log.logging( "ZLinky", "Status", "Adjusting ZLinky model from %s to %s" %( 
            self.ListOfDevices[ nwkid ]["Model"], zlinky_conf  ))
        
        # Looks like we have to update the Model in order to use the right attributes
        self.ListOfDevices[ nwkid ]["Model"] = zlinky_conf

        # Read Attribute has to be redone from scratch
        if "ReadAttributes" in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid]["ReadAttributes"]

        if 'ZLinky' in self.ListOfDevices[ nwkid ]:
            del self.ListOfDevices[ nwkid ]['ZLinky']

        # Configure Reporting to be done
        if STORE_CONFIGURE_REPORTING in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid][STORE_CONFIGURE_REPORTING]

        if STORE_READ_CONFIGURE_REPORTING in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid][STORE_READ_CONFIGURE_REPORTING]
            
        if self.configureReporting:
            self.configureReporting.check_configuration_reporting_for_device( nwkid, force=True)
            
        if "Heartbeat" in self.ListOfDevices[nwkid]:
            self.ListOfDevices[nwkid]["Heartbeat"] = "-1"

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
    """ decoding of STGE Linky frame"""
    # Contact Sec : bit 0
    # Organe de coupure: bits 1 à 3
    # Etat du cache-bornes distributeur: bit 4
    # Surtension sur une des phases: bit 6
    # Dépassement de la puissance de référence bit 7
    # Fonctionnement produ/conso: bit 8
    # Sens de l'énégerie active: bit 9
    # Tarif en cours contrat fourniture: bit 10 à 13
    # Tarif en cours contrat distributeur: bit 14 et 15
    # Mode dégradée de l'horloge: bit 16
    # Etat de sortie tic: bit 17
    # Etat de sortie Euridis: bit 19 et 20
    # Statut du CPL: bit 21 et 22
    # Synchro CPL: bit 23
    # Couleur du jour: bit 24 et 25
    # Couleur du lendemain: bit 26 et 27
    # Préavis points mobiles: bit 28 à 29
    # Pointe mobile: bit 30 et 31

    try:
        stge = int(stge, 16)
    except ValueError:
        return {}

    STEG_ATTRIBUTES = {
        'contact_sec': stge & 0x00000001,
        'organe_coupure': (stge & 0x0000000E) >> 1,
        'etat_cache_bornes': (stge & 0x00000010) >> 4,
        'sur_tension': (stge & 0x00000040) >> 6,
        'depassement_puissance': (stge & 0x00000080) >> 7,
        'mode_fonctionnement': (stge & 0x00000100) >> 8,
        'sens_energie': (stge & 0x00000200) >> 9,
        'tarif_fourniture': (stge & 0x0001F000) >> 12,
        'tarif_distributeur': (stge & 0x00060000) >> 14,
        'Mode_horloge': (stge & 0x00100000) >> 16,
        'sortie_tic': (stge & 0x00200000) >> 17,
        'sortie_euridis': (stge & 0x00C00000) >> 19,
        'status_cpl': (stge & 0x03000000) >> 21,
        'synchro_cpl': (stge & 0x08000000) >> 23,
        'couleur_jour': (stge & 0x30000000) >> 24,
        'couleur_demain': (stge & 0xC0000000) >> 26,
        'preavis_point_mobile': (stge & 0x30000000) >> 28,
        'pointe_mobile': (stge & 0xC0000000) >> 30,
    }

    # Decode mapped values
    STEG_ATTRIBUTES_MAPPING = {
        'contact_sec': CONTACT_SEC,
        'etat_cache_bornes': ETAT_CACHE_BORNES,
        'mode_fonctionnement': FONCTION_PROD_CONSO,
        'sens_energie': SENS_ENERGIE,
        'Mode_horloge': HORLOGE,
        'sortie_tic': SORTIE_TIC,
        'sortie_euridis': SORTIE_EURIDIS,
        'status_cpl': STATUT_CPL,
        'synchro_cpl': SYNCHRO_CPL,
        'couleur_jour': COULEUR,
        'couleur_demain': COULEUR,
    }

    # Decode mapped values for applicable attributes
    for attr, mapping in STEG_ATTRIBUTES_MAPPING.items():
        if attr in STEG_ATTRIBUTES and STEG_ATTRIBUTES[attr] in mapping:
            STEG_ATTRIBUTES[attr] = mapping[STEG_ATTRIBUTES[attr]]

    return STEG_ATTRIBUTES


def zlinky_sum_all_indexes(self, nwkid):
    zlinky_info = self.ListOfDevices.get(nwkid, {}).get("ZLinky", {})
    index_mid_info = zlinky_info.get("INDEX_MID", {})

    return index_mid_info.get("CompteurTotalisateur", 0)


def zlinky_totalisateur(self, nwkid, attribute, value):
    zlinky_info = self.ListOfDevices.setdefault(nwkid, {}).setdefault("ZLinky", {})
    index_mid_info = zlinky_info.setdefault("INDEX_MID", {"CompteurTotalisateur": 0})

    previous_index = index_mid_info.get(attribute, {}).get("Compteur", 0)
    increment = value - previous_index

    index_mid_info["CompteurTotalisateur"] += increment
    index_mid_info[attribute] = {"TimeStamp": time.time(), "Compteur": value}
