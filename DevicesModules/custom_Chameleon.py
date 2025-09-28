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
Chameleon Smart Metering (ERL Z3) Module
========================================

This module provides utilities to interact with and decode status registers (STGE) 
and attributes of ERL Z3-compatible smart meters over Zigbee. It supports parsing 
bitfield status values, mapping them to human-readable labels, and triggering 
attribute reads from relevant Zigbee clusters.

Key Features
------------
- Decode the STGE (Statuts / 0x0702 / 0x0200) register into meaningful fields:
  * Contact sec
  * Organe de coupure
  * État du cache-bornes
  * Surtension / Dépassement puissance
  * Mode fonctionnement (producteur/consommateur)
  * Sens énergie active
  * Tarifs fournisseur et distributeur
  * Horloge / Télé-information / Communication
  * CPL status & synchronization
  * Couleur du jour et du lendemain
  * Préavis et pointe mobile

- Store decoded attribute values with `checkAndStoreAttributeValue` for later use.

- Provide attribute constants and mappings for Zigbee clusters:
  * Smart Metering (0x0702, 0x070d)
  * Metering Identification (0x0b01)
  * Basic cluster (0x0000)

- Trigger reading of missing Zigbee attributes via `erl_z3_master_info`.

Dependencies
------------
- `Modules.basicOutputs.read_attribute` for Zigbee attribute reading
- `Modules.tools.checkAndStoreAttributeValue` for storing values
- `Modules.zigateConsts.ZIGATE_EP` endpoint constant

Main Functions
--------------
- chameleon_stge(self, nwkid, ep, cluster, attribut, stge)
    Decode the `stge` bitfield register and log/store all relevant attributes.

- erl_z3_master_info(self, nwkid)
    Trigger attribute reads for ERL Z3 devices, ensuring critical attributes 
    are retrieved and kept up to date.

Constants
---------
- CONTACT_SEC, ETAT_CACHE_BORNES, FONCTION_PROD_CONSO, SENS_ENERGIE,
  HORLOGE, SORTIE_TIC, SORTIE_EURIDIS, STATUT_CPL, SYNCHRO_CPL, COULEUR
    Dictionaries mapping raw register values to human-readable strings.

- SMART_METERING_CLUSTER, SMART_METERING_070D_CLUSTER, 
  METERING_IDENTIFICATION_CLUSTER
    Zigbee cluster identifiers.

- ERL_Z3_*_ATTRIBUTE
    Attribute identifiers for smart metering and identification clusters.

Usage
-----
Typical usage involves:
1. Receiving a `stge` register from the smart meter and decoding it:
   >>> chameleon_stge(self, nwkid, ep, cluster, attribut, stge)

2. Periodically triggering a refresh of ERL Z3 attributes:
   >>> erl_z3_master_info(self, nwkid)
"""

from Modules.basicOutputs import read_attribute
from Modules.tools import checkAndStoreAttributeValue
from Modules.zigateConsts import ZIGATE_EP

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

def chameleon_stge(self, nwkid, ep, cluster, attribut, stge):

    # Registre de statuts / STG / 0x0702 / 0200
    
    self.log.logging( "Chameleon", "Debug", "chameleon_stge %s %s %s %s %s" %( 
        nwkid, ep, cluster, attribut, stge))

    contact_sec = ( stge & 0b00000000000000000000000000000001)
    organe_coupure = ( stge & 0b00000000000000000000000000001110) >> 1
    etat_cache_bornes = ( stge & 0b00000000000000000000000000010000) >> 4
    sur_tension = ( stge & 0b00000000000000000000000001000000) >> 6
    depassement_puissance = ( stge & 0b00000000000000000000000010000000) >> 7
    mode_fonctionnement =(stge & 0b00000000000000000000000100000000) >> 8
    sens_energie = ( stge & 0b00000000000000000000001000000000) >> 9
    tarif_fourniture = ( stge & 0b00000000000000000011110000000000) >> 10
    tarif_distributeur =( stge & 0b00000000000000001100000000000000) >> 14
    Mode_horloge = ( stge & 0b00000000000000010000000000000000) >> 16
    sortie_tic = ( stge & 0b00000000000000100000000000000000) >> 17
    sortie_euridis = ( stge & 0b00000000000110000000000000000000) >> 19
    status_cpl = ( stge & 0b00000000011000000000000000000000) >> 21
    synchro_cpl = ( stge & 0b00000000100000000000000000000000) >> 23
    couleur_jour = ( stge & 0b00000011000000000000000000000000) >> 24
    couleur_demain = ( stge & 0b00001100000000000000000000000000) >> 26
    preavis_point_mobile = ( stge & 0b00110000000000000000000000000000) >> 28
    pointe_mobile = ( stge & 0b11000000000000000000000000000000) >> 30

    if contact_sec in CONTACT_SEC:
        contact_sec = CONTACT_SEC[ contact_sec ]

    if etat_cache_bornes in ETAT_CACHE_BORNES:
        etat_cache_bornes = ETAT_CACHE_BORNES[ etat_cache_bornes ]  

    if mode_fonctionnement in FONCTION_PROD_CONSO:
        mode_fonctionnement = FONCTION_PROD_CONSO[ mode_fonctionnement ]

    if sens_energie in SENS_ENERGIE:
        sens_energie = SENS_ENERGIE[ sens_energie ]

    if Mode_horloge in HORLOGE:
        Mode_horloge = HORLOGE[ Mode_horloge]

    if sortie_tic in SORTIE_TIC:
        sortie_tic = SORTIE_TIC[ sortie_tic ]

    if sortie_euridis in SORTIE_EURIDIS:
        sortie_euridis = SORTIE_EURIDIS[ sortie_euridis ]

    if status_cpl in STATUT_CPL:
        status_cpl = STATUT_CPL[ status_cpl ]

    if synchro_cpl in SYNCHRO_CPL:
        synchro_cpl = SYNCHRO_CPL[ synchro_cpl ]

    if couleur_jour in COULEUR:
        couleur_jour = COULEUR[ couleur_jour]
        
    if couleur_demain in COULEUR:
        couleur_demain = COULEUR[ couleur_demain]
    
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Contact sec", contact_sec)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Organe de coupure", organe_coupure)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "État du cache-bornes distributeur", etat_cache_bornes)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Surtension sur une des phases", sur_tension)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Dépassement de la puissance de référence", depassement_puissance)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Fonctionnement producteur/consommateur", mode_fonctionnement)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Sens énergie active", sens_energie)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Tarif en cours sur le contrat fourniture", tarif_fourniture)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Tarif en cours sur le contrat distributeur", tarif_distributeur)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Mode dégradée horloge", Mode_horloge)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "État de la sortie télé-information", sortie_tic)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "État de la sortie communication", sortie_euridis)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Statut du CPL", status_cpl)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Synchronisation CPL", synchro_cpl)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Couleur du jour", couleur_jour)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Couleur du lendemain", couleur_demain)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Préavis pointes mobiles", preavis_point_mobile)
    checkAndStoreAttributeValue(self, nwkid, ep, cluster, "Pointe mobile", pointe_mobile)
    return stge

SMART_METERING_CLUSTER = "0702"
ERL_Z3_LINKY_MODE = "0209"
ERL_Z3_ADCO_ATTRIBUTE = "0308"
ERL_Z3_NGTF_OPTARIF_ATTRIBUTE = "030f"

SMART_METERING_070D_CLUSTER = "070d"
ERL_Z3_PTEC_LTARF_ATTRIBUTE = "0102"
ERL_Z3_STGE_DEMAIN_ATTRIBUTE = "0103"

METERING_IDENTIFICATION_CLUSTER = "0b01"
ERL_Z3_VERSION_TIC_ATTRIBUTE = "000a"
ERL_Z3_PRM_ATTRIBUTE = "000c"
ERL_Z3_PREF_ISOUSC_ATTRIBUTE = "000d"
ERL_Z3_PCOUP_ATTRIBUTE = "000e"

def erl_z3_master_info(self, nwkid):
    """
    Trigger reading attributes for ERL Z3.
    Optimized to reduce repetition and make attribute checks more declarative.
    """
    self.log.logging("Chameleon", "Debug", f"erl_z3_master_info {nwkid}")

    # Define attribute groups by cluster
    attr_groups = {
        "0000": [("4000", "firmware version")],  # Basic Cluster
        "0702": [  # Smart Metering Cluster
            (ERL_Z3_LINKY_MODE, "LINKY_MODE"),
            (ERL_Z3_ADCO_ATTRIBUTE, "ADCO"),
            (ERL_Z3_NGTF_OPTARIF_ATTRIBUTE, "NGTF/OPTARIF"),
        ],
        "070d": [  # Smart Metering 0x070d Cluster
            (ERL_Z3_PTEC_LTARF_ATTRIBUTE, "PTEC/LTARF"),
            (ERL_Z3_STGE_DEMAIN_ATTRIBUTE, "STGE/DEMAIN"),
        ],
        "0b01": [  # Metering Identification Cluster
            (ERL_Z3_VERSION_TIC_ATTRIBUTE, "VERSION_TIC"),
            (ERL_Z3_PRM_ATTRIBUTE, "PRM"),
            (ERL_Z3_PREF_ISOUSC_ATTRIBUTE, "PREF_ISOUSC"),
            (ERL_Z3_PCOUP_ATTRIBUTE, "PCOUP"),
        ],
    }

    # Map cluster IDs to constants
    cluster_map = {
        "0000": "0000",
        "0702": SMART_METERING_CLUSTER,
        "070d": SMART_METERING_070D_CLUSTER,
        "0b01": METERING_IDENTIFICATION_CLUSTER,
    }

    chameleon_tic_infos = self.ListOfDevices.get(nwkid, {})
    chameleon_tic_ep = chameleon_tic_infos.get("Ep", {}).get("01", {})

    # Iterate through clusters and attributes
    for cluster_id, attributes in attr_groups.items():
        cluster_data = chameleon_tic_ep.get(cluster_id, {})
        for attr_id, attr_name in attributes:
            if cluster_data is None or cluster_data.get(attr_id) is None:
                self.log.logging( "Chameleon", "Debug", f"erl_z3_master_info reading {attr_name} for {nwkid}" )
                read_attribute( self, nwkid, ZIGATE_EP, "01", cluster_map[cluster_id], "00", "00", "0000", 0x01, attr_id, ackIsDisabled=False, )
    