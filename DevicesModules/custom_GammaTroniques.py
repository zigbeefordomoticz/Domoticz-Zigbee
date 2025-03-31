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

STRING = "String"
HA_NUMBER = "??"
UINT8 = "uint8"
UINT16 = "uint16"
UINT32 = "uint32"
UINT32_TIME = "uint32_time"
UINT64 = "uint64"

C_ANY = "C_ANY"  # Contrat
C_HC = "HCHP"
C_EJP = "EJP"
C_TEMPO = "TEMPO"

G_ANY = "G_ANY"  # Grid
G_MONO = "Monophasé"
G_TRI = "Tri-Phasé"
STATIC_VALUE = "Static"
REAL_TIME = "Real Time"
NONE_CLASS = "None"
ZB_RO = "RO"  # Read Only
ZB_RP = "RP"  # Reporting
ZB_RW = "RW"  # Read/Write
ZB_UINT16 = "uint16"
ZB_UINT48 = "uint48"
ZB_UINT8 = "uint8"
ZB_UINT16 = "uint16"
ZB_UINT32 = "uint32"
ZB_UINT32_TIME = "uint32_time"
ZB_UINT64 = "uint64"
ZB_OCTSTR = "String"
ZB_CHARSTR = "String"
ZB_NO = "Null"
ZB_INT16 = "int16"

CURRENT = "Current"  # Ampere
POWER_kVA = "Power"  # Watt/KVA
ENERGY = "Energy"    # Usage/Summation
CLASS_BOOL = "Boolean"
POWER_VA = "Power"
POWER_W = "Power"
ENERGY_Q = "Energy"
CURRENT = "Current"
TENSION = "Tension"
TIMESTAMP = "Timestamp"
ANY = "Any"
TIME = "Time"   
NONE_CLASS = "None"
TIME_M = "Time"

# flake8: noqa

TICMETER_LABELS = { 
    "TICMETER_LABELS": {
        #     ID  Name                                 Label         Type        Size  Contract Grid    UpdateType     HA Class      CLUSTER ATTRIB   ACCESS  ZB_TYPE
        #  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        "Historique" : [
            {  1, "Identifiant",                        "ADCO",        STRING,      12, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0x0702, 0x0308,  ZB_RO, ZB_OCTSTR,   },  
            {  2, "Type de contrat",                    "OPTARIF",     STRING,       4, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0000,  ZB_RO, ZB_CHARSTR,  },  
            {  3, "Intensité souscrite",                "ISOUSC",      UINT32,       0, C_ANY,   G_ANY,  STATIC_VALUE,  CURRENT,      0x0000, 0x0000,  ZB_NO, ZB_NO,       },  # TODO: zigbee: when  Meter Identification cluster
            {  4, "Puissance Max contrat",              "pref",        UINT32,       0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_kVA,    0xFF42, 0x002b,  ZB_RO, ZB_UINT16,   },  # TODO: zigbee: when  Meter Identification cluster  0x0B01, 0x000D, 
            {  5, "Index Total",                        "total",       UINT64,       0,  C_ANY,  G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0000,  ZB_RP, ZB_UINT48,   },  
            {  6, "Index Base",                         "BASE",        UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0100,  ZB_RP, ZB_UINT48,   },  
            {  7, "Index Heures Creuses",               "HCHC",        UINT64,       0, C_HC,    G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0100,  ZB_RP, ZB_UINT48,   },  
            {  8, "Index Heures Pleines",               "HCHP",        UINT64,       0, C_HC,    G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0102,  ZB_RP, ZB_UINT48,   },  
            {  9, "Index Heures Normales",              "EJPHN",       UINT64,       0, C_EJP,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0100,  ZB_RP, ZB_UINT48,   },  
            { 10, "Index Heures de Pointe Mobile",      "EJPHPM",      UINT64,       0, C_EJP,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0102,  ZB_RP, ZB_UINT48,   },  
            { 11, "Préavis Début EJP",                  "PEJP",        UINT16,       0, C_EJP,   G_ANY,  STATIC_VALUE,  CLASS_BOOL,   0xFF42, 0x0001,  ZB_RP, ZB_UINT16,   },  
            { 12, "Heures Creuses Jours Bleus",         "BBRHCJB",     UINT64,       0, C_TEMPO, G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0100,  ZB_RP, ZB_UINT48,   },  
            { 13, "Heures Pleines Jours Bleus",         "BBRHPJB",     UINT64,       0, C_TEMPO, G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0102,  ZB_RP, ZB_UINT48,   },  
            { 14, "Heures Creuses Jours Blancs",        "BBRHCJW",     UINT64,       0, C_TEMPO, G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0104,  ZB_RP, ZB_UINT48,   },  
            { 15, "Heures Pleines Jours Blancs",        "BBRHPJW",     UINT64,       0, C_TEMPO, G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0106,  ZB_RP, ZB_UINT48,   },  
            { 16, "Heures Creuses Jours Rouges",        "BBRHCJR",     UINT64,       0, C_TEMPO, G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0108,  ZB_RP, ZB_UINT48,   },  
            { 17, "Heures Pleines Jours Rouges",        "BBRHPJR",     UINT64,       0, C_TEMPO, G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x010A,  ZB_RP, ZB_UINT48,   },  
            { 18, "Période tarifaire en cours",         "PTEC",        STRING,       4, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0039,  ZB_RP, ZB_CHARSTR,  },  # 0x0702, 0x0020
            { 19, "Couleur aujourd'hui",                "aujour",      STRING,       9, C_TEMPO, G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x003A,  ZB_RP, ZB_OCTSTR,   },  
            { 20, "Couleur du lendemain",               "DEMAIN",      STRING,       9, C_TEMPO, G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0003,  ZB_RP, ZB_OCTSTR,   },  
            { 21, "Intensité instantanée",              "IINST",       UINT16,       0, C_ANY,   G_MONO, REAL_TIME,     CURRENT,      0x0B04, 0x0508,  ZB_RP, ZB_UINT16,   },  
            { 22, "Intensité instantanée Phase 1",      "IINST1",      UINT16,       0, C_ANY,   G_TRI,  REAL_TIME,     CURRENT,      0x0B04, 0x0508,  ZB_RP, ZB_UINT16,   },  
            { 23, "Intensité instantanée Phase 2",      "IINST2",      UINT16,       0, C_ANY,   G_TRI,  REAL_TIME,     CURRENT,      0x0B04, 0x0908,  ZB_RP, ZB_UINT16,   },  
            { 24, "Intensité instantanée Phase 3",      "IINST3",      UINT16,       0, C_ANY,   G_TRI,  REAL_TIME,     CURRENT,      0x0B04, 0x0A08,  ZB_RP, ZB_UINT16,   },  
            { 25, "Intensité maximale",                 "IMAX",        UINT16,       0, C_ANY,   G_MONO, STATIC_VALUE,  CURRENT,      0x0B04, 0x050A,  ZB_RO, ZB_UINT16,   },  
            { 26, "Intensité maximale Phase 1",         "IMAX1",       UINT16,       0, C_ANY,   G_TRI,  STATIC_VALUE,  CURRENT,      0x0B04, 0x050A,  ZB_RO, ZB_UINT16,   },  
            { 27, "Intensité maximale Phase 2",         "IMAX2",       UINT16,       0, C_ANY,   G_TRI,  STATIC_VALUE,  CURRENT,      0x0B04, 0x090A,  ZB_RO, ZB_UINT16,   },  
            { 28, "Intensité maximale Phase 3",         "IMAX3",       UINT16,       0, C_ANY,   G_TRI,  STATIC_VALUE,  CURRENT,      0x0B04, 0x0A0A,  ZB_RO, ZB_UINT16,   },  
            { 29, "Dépassement Puissance",              "ADPS",        UINT16,       0, C_ANY,   G_MONO, STATIC_VALUE,  CURRENT,      0xFF42, 0x0004,  ZB_RP, ZB_UINT16,   },  
            { 30, "Dépassement Intensité Phase 1",      "ADIR1",       UINT16,       0, C_ANY,   G_TRI,  STATIC_VALUE,  CURRENT,      0xFF42, 0x0005,  ZB_RP, ZB_UINT16,   },  
            { 31, "Dépassement Intensité Phase 2",      "ADIR2",       UINT16,       0, C_ANY,   G_TRI,  STATIC_VALUE,  CURRENT,      0xFF42, 0x0006,  ZB_RP, ZB_UINT16,   },  
            { 32, "Dépassement Intensité Phase 3",      "ADIR3",       UINT16,       0, C_ANY,   G_TRI,  STATIC_VALUE,  CURRENT,      0xFF42, 0x0007,  ZB_RP, ZB_UINT16,   },  
            { 33, "Puissance apparente",                "PAPP",        UINT32,       0, C_ANY,   G_ANY,  REAL_TIME,     POWER_VA,     0x0B04, 0x050F,  ZB_RP, ZB_UINT16,   },  
            { 34, "Puissance maximale triphasée",       "PMAX",        UINT32,       0, C_ANY,   G_TRI,  STATIC_VALUE,  POWER_W,      0x0B04, 0x050D,  ZB_RO, ZB_INT16,    },  
            { 35, "Présence des potentiels",            "PPOT",        UINT32,       0, C_ANY,   G_TRI,  REAL_TIME,     NONE_CLASS,   0xFF42, 0x0008,  ZB_RO, ZB_UINT32,   },  
            { 36, "Horaire Heures Creuses",             "HHPHC",       STRING,       3, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0009,  ZB_RP, ZB_OCTSTR,   },  
            { 37, "Mot d'état du compteur",             "MOTDETAT",    STRING,       6, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x000A,  ZB_RO, ZB_OCTSTR,   },  
        ],
        "Standard": [
            { 38, "Identifiant",                        "ADSC",        STRING,      12, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0x0702, 0x0308,  ZB_RO, ZB_OCTSTR,   },  
            { 39, "Version de la TIC",                  "VTIC",        STRING,       2, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x002e,  ZB_RO, ZB_CHARSTR,  },  # TODO: zigbee: when  Meter Identification cluster 0x0B01, 0x000A,  
            { 40, "Date",                               "DATE",        UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0x0000, 0x0000,  ZB_NO, ZB_NO,       },  
            { 41, "Date et heure Compteur",             "date_time",   UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x000B,  ZB_RO, ZB_UINT64,   },  
            { 42, "Nom du calendrier tarifaire",        "NGTF",        STRING,      16, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0000,  ZB_RO, ZB_OCTSTR,   },  
            { 43, "Libellé tarif en cours",             "LTARF",       STRING,      16, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0039,  ZB_RP, ZB_CHARSTR,  },  
            { 43, "Index Total Energie soutirée",       "EAST",        UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0000,  ZB_RP, ZB_UINT48,   },  
            { 44, "Index 1 Energie soutirée",           "EASF01",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0100,  ZB_RP, ZB_UINT48,   },  
            { 45, "Index 2 Energie soutirée",           "EASF02",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0102,  ZB_RP, ZB_UINT48,   },  
            { 46, "Index 3 Energie soutirée",           "EASF03",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0104,  ZB_RP, ZB_UINT48,   },  
            { 47, "Index 4 Energie soutirée",           "EASF04",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0106,  ZB_RP, ZB_UINT48,   },  
            { 48, "Index 5 Energie soutirée",           "EASF05",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0108,  ZB_RP, ZB_UINT48,   },  
            { 49, "Index 6 Energie soutirée",           "EASF06",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x010A,  ZB_RP, ZB_UINT48,   },  
            { 50, "Index 7 Energie soutirée",           "EASF07",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x010C,  ZB_RP, ZB_UINT48,   },  
            { 51, "Index 8 Energie soutirée",           "EASF08",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x010E,  ZB_RP, ZB_UINT48,   },  
            { 52, "Index 9 Energie soutirée",           "EASF09",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0110,  ZB_RP, ZB_UINT48,   },  
            { 53, "Index 10 Energie soutirée",          "EASF10",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0112,  ZB_RP, ZB_UINT48,   },  
            { 54, "Index 1 Energie soutirée Distr",     "EASD01",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0xFF42, 0x000E,  ZB_RP, ZB_UINT48,   },  
            { 55, "Index 2 Energie soutirée Distr",     "EASD02",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0xFF42, 0x000F,  ZB_RP, ZB_UINT48,   },  
            { 56, "Index 3 Energie soutirée Distr",     "EASD03",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0xFF42, 0x0010,  ZB_RP, ZB_UINT48,   },  
            { 57, "Index 4 Energie soutirée Distr",     "EASD04",      UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0xFF42, 0x0011,  ZB_RP, ZB_UINT48,   },  
            { 58, "Energie injectée totale",            "EAIT",        UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY,       0x0702, 0x0001,  ZB_RP, ZB_UINT48,   },  
            { 59, "Energie réactive Q1 totale",         "ERQ1",        UINT32,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY_Q,     0x0B04, 0x0305,  ZB_RP, ZB_INT16,    },  
            { 60, "Energie réactive Q2 totale",         "ERQ2",        UINT32,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY_Q,     0x0B04, 0x050E,  ZB_RP, ZB_INT16,    },  
            { 61, "Energie réactive Q3 totale",         "ERQ3",        UINT32,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY_Q,     0x0B04, 0x090E,  ZB_RP, ZB_INT16,    },  
            { 62, "Energie réactive Q4 totale",         "ERQ4",        UINT32,       0, C_ANY,   G_ANY,  STATIC_VALUE,  ENERGY_Q,     0x0B04, 0x0A0E,  ZB_RP, ZB_INT16,    },  
            { 63, "Courant efficace Phase 1",           "IRMS1",       UINT16,       0, C_ANY,   G_ANY,  STATIC_VALUE,  CURRENT,      0x0B04, 0x0508,  ZB_RP, ZB_UINT16,   },  
            { 64, "Courant efficace Phase 2",           "IRMS2",       UINT16,       0, C_ANY,   G_ANY,  STATIC_VALUE,  CURRENT,      0x0B04, 0x0908,  ZB_RP, ZB_UINT16,   },  
            { 65, "Courant efficace Phase 3",           "IRMS3",       UINT16,       0, C_ANY,   G_ANY,  STATIC_VALUE,  CURRENT,      0x0B04, 0x0A08,  ZB_RP, ZB_UINT16,   },  
            { 66, "Tension efficace Phase 1",           "URMS1",       UINT16,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TENSION,      0x0B04, 0x0505,  ZB_RP, ZB_UINT16,   },  
            { 67, "Tension efficace Phase 2",           "URMS2",       UINT16,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TENSION,      0x0B04, 0x0905,  ZB_RP, ZB_UINT16,   },  
            { 68, "Tension efficace Phase 3",           "URMS3",       UINT16,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TENSION,      0x0B04, 0x0A05,  ZB_RP, ZB_UINT16,   },  
            { 69, "Puissance app. de référence",        "PREF",        UINT16,       0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_kVA,    0xFF42, 0x002B,  ZB_RO, ZB_UINT16,   },  # TODO: zigbee: when  Meter Identification cluster 0x0B01, 0x000D
            { 70, "Puissance app. de coupure",          "PCOUP",       UINT8,        0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_kVA,    0x0B01, 0x000E,  ZB_NO, ZB_UINT8,    },  # TODO: zigbee: when  Meter Identification cluster
            { 71, "Puissance soutirée",                 "SINSTS",      UINT32,       0, C_ANY,   G_MONO,  STATIC_VALUE, POWER_VA,     0x0B04, 0x050F,  ZB_RP, ZB_INT16,    },  
            { 72, "Puissance soutirée Phase 1",         "SINSTS1",     UINT32,       0, C_ANY,   G_TRI,  STATIC_VALUE,  POWER_VA,     0x0B04, 0x050F,  ZB_RP, ZB_INT16,    },  
            { 73, "Puissance soutirée Phase 2",         "SINSTS2",     UINT32,       0, C_ANY,   G_TRI,  STATIC_VALUE,  POWER_VA,     0x0B04, 0x090F,  ZB_RP, ZB_INT16,    },  
            { 74, "Puissance soutirée Phase 3",         "SINSTS3",     UINT32,       0, C_ANY,   G_TRI,  STATIC_VALUE,  POWER_VA,     0x0B04, 0x0A0F,  ZB_RP, ZB_INT16,    },  
            { 75, "Puissance max soutirée Auj.",        "SMAXSN",      UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0x0B04, 0x050D,  ZB_RO, ZB_INT16,    },  
            { 76, "Puissance max soutirée Auj. 1",      "SMAXSN1",     UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0x0B04, 0x050D,  ZB_RO, ZB_INT16,    },  
            { 77, "Puissance max soutirée Auj. 2",      "SMAXSN2",     UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0x0B04, 0x090D,  ZB_RO, ZB_INT16,    },  
            { 78, "Puissance max soutirée Auj. 3",      "SMAXSN3",     UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0x0B04, 0x0A0D,  ZB_RO, ZB_INT16,    },  
            { 79, "Heure Puissance max soutirée Auj",   "smaxsn_time", UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TIMESTAMP,     0xFF42, 0x002F,  ZB_RO, ZB_UINT64,  },  
            { 80, "Heure Puissance max soutirée Auj. 1","smaxsn1_time",UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TIMESTAMP,     0xFF42, 0x0030,  ZB_RO, ZB_UINT64,  },  
            { 81, "Heure Puissance max soutirée Auj. 2","smaxsn2_time",UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TIMESTAMP,     0xFF42, 0x0031,  ZB_RO, ZB_UINT64,  },  
            { 82, "Heure Puissance max soutirée Auj. 3","smaxsn3_time",UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TIMESTAMP,     0xFF42, 0x0032,  ZB_RO, ZB_UINT64,  },  
            { 83, "Puissance max soutirée Hier",        "SMAXSN-1",    UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0xFF42, 0x0012,  ZB_RO, ZB_INT16,    },  
            { 84, "Puissance max soutirée Hier 1",      "SMAXSN1-1",   UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0xFF42, 0x0013,  ZB_RO, ZB_INT16,    },  
            { 85, "Puissance max soutirée Hier 2",      "SMAXSN2-1",   UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0xFF42, 0x0014,  ZB_RO, ZB_INT16,    },  
            { 86, "Puissance max soutirée Hier 3",      "SMAXSN3-1",   UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0xFF42, 0x0015,  ZB_RO, ZB_INT16,    },  
            { 87, "Heure Puissance max soutirée Hier",  "maxs-1_time", UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TIMESTAMP,     0xFF42, 0x0033,  ZB_RO, ZB_UINT64,  },  
            { 88, "Heure Puissance max soutirée Hier 1","maxs1-1_time",UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TIMESTAMP,     0xFF42, 0x0034,  ZB_RO, ZB_UINT64,  },  
            { 89, "Heure Puissance max soutirée Hier 2","maxs2-1_time",UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TIMESTAMP,     0xFF42, 0x0035,  ZB_RO, ZB_UINT64,  },  
            { 90, "Heure Puissance max soutirée Hier 3","maxs3-1_time",UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  TIMESTAMP,     0xFF42, 0x0036,  ZB_RO, ZB_UINT64,  },  
            { 91, "Puissance injectée",                 "SINSTI",      UINT32,       0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0xFF42, 0x0016,  ZB_RP, ZB_UINT32,   },  
            { 92, "Puissance max injectée Auj.",        "SMAXIN",      UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0xFF42, 0x0017,  ZB_RO, ZB_UINT32,   },  
            { 93, "Puissance max injectée Hier",        "SMAXIN-1",    UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0xFF42, 0x0018,  ZB_RO, ZB_UINT32,   },  
            { 94, "Heure Puissance max injectée Auj.",  "smaxin_time", UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0xFF42, 0x0037,  ZB_RO, ZB_UINT64,   },  
            { 95, "Heure Puissance max injectée Hier",  "maxin-1_time",UINT64,       0, C_ANY,   G_ANY,  STATIC_VALUE,  POWER_VA,     0xFF42, 0x0038,  ZB_RO, ZB_UINT64,   },  
            { 96, "Point n courbe soutirée",            "CCASN",       UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0x0B04, 0x050B,  ZB_RO, ZB_INT16,    },  
            { 97, "Point n-1 courbe soutirée",          "CCASN-1",     UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0x0B04, 0x090B,  ZB_RO, ZB_INT16,    },  
            { 98, "Point n courbe injectée",            "CCAIN",       UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0019,  ZB_RO, ZB_INT16,    },  
            { 99, "Point n-1 courbe injectée",          "CCAIN-1",     UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x001a,  ZB_RO, ZB_INT16,    },  
            {100, "Tension moyenne Phase 1",            "UMOY1",       UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  TENSION,      0x0B04, 0x0511,  ZB_RO, ZB_UINT16,   },  
            {101, "Tension moyenne Phase 2",            "UMOY2",       UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  TENSION,      0x0B04, 0x0911,  ZB_RO, ZB_UINT16,   },  
            {102, "Tension moyenne Phase 3",            "UMOY3",       UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  TENSION,      0x0B04, 0x0A11,  ZB_RO, ZB_UINT16,   },  
            {103, "Registre de Statuts",                "STGE",        STRING,       8, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x000A,  ZB_RO, ZB_OCTSTR,   },  
            {104, "Couleur aujourd'hui",                "aujour",      STRING,       9, C_TEMPO, G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x003A,  ZB_RP, ZB_OCTSTR,   },  
            {105, "Couleur du lendemain",               "demain",      STRING,       9, C_TEMPO, G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0003,  ZB_RP, ZB_OCTSTR,   },  # TODO: Enedis-NOI-CPT_54E p25 Couleur du lendemain --> tuya 109
            {106, "Début Pointe Mobile 1",              "DPM1",        UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x001c,  ZB_RO, ZB_UINT64,   },  
            {107, "Fin Pointe Mobile 1",                "FPM1",        UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x001d,  ZB_RO, ZB_UINT64,   },  
            {108, "Début Pointe Mobile 2",              "DPM2",        UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x001e,  ZB_RO, ZB_UINT64,   },  
            {109, "Fin Pointe Mobile 2",                "FPM2",        UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x001f,  ZB_RO, ZB_UINT64,   },  
            {110, "Début Pointe Mobile 3",              "DPM3",        UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0020,  ZB_RO, ZB_UINT64,   },  
            {111, "Fin Pointe Mobile 3",                "FPM3",        UINT32_TIME,  0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0021,  ZB_RO, ZB_UINT64,   },  
            {112, "Message court",                      "MSG1",        STRING,      32, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0022,  ZB_RO, ZB_CHARSTR,  },  
            {113, "Message Ultra court",                "MSG2",        STRING,      16, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0023,  ZB_RO, ZB_CHARSTR,  },  
            {114, "Point Référence Mesure",             "PRM",         STRING,      14, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0x0702, 0x0307,  ZB_RO, ZB_CHARSTR,  },  
            {115, "Relais",                             "RELAIS",      STRING,       3, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0024,  ZB_RO, ZB_CHARSTR,  },  
            {116, "Index tarifaire en cours",           "NTARF",       UINT16,       0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0025,  ZB_RO, ZB_UINT16,   },  
            {117, "N° jours en cours fournisseur",      "NJOURF",      UINT16,       0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0026,  ZB_RO, ZB_UINT16    },  
            {118, "N° prochain jour fournisseur",       "NJOURF+1",    UINT16,       0, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0027,  ZB_RO, ZB_UINT16    },  
            {119, "Profil du prochain jour",            "PJOURF+1",    STRING,      16, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0028,  ZB_RO, ZB_CHARSTR   },  
            {120, "Profil du prochain jour pointe",     "PPOINTE",     STRING,      58, C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,   0xFF42, 0x0029,  ZB_RO, ZB_CHARSTR   },  
        ],
        "Admin": [
            {121, "Temps d'actualisation",              "now-refresh", UINT16,       0,      ANY,  C_ANY,   G_ANY,  STATIC_VALUE,  TIME,        "mdi:refresh",                         0xFF42, 0x0002,  ZB_RW, ZB_UINT16    },  
            {122, "Temps d'actualisation",              "set-refresh", HA_NUMBER,    0,      ANY,  C_ANY,   G_ANY,  STATIC_VALUE,  TIME,        "mdi:refresh",                         0x0000, 0x0000,  ZB_NO, ZB_NO        },  
            {123, "Mode TIC",                           "mode-tic",    UINT16,       0,      ANY,  C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,  "mdi:translate",                       0xFF42, 0x002c,  ZB_RO, ZB_UINT8     },  
            {124, "Mode Electrique",                    "mode-elec",   UINT16,       0,      ANY,  C_ANY,   G_ANY,  STATIC_VALUE,  NONE_CLASS,  "mdi:power-plug-outline",              0xFF42, 0x002a,  ZB_RO, ZB_UINT8     },  
            {125, "Temps de fonctionnement",            "uptime",      UINT64,       0,      ANY,  C_ANY,   G_ANY,  REAL_TIME,     TIME_M,      "mdi:clock-time-eight-outline",        0xFF42, 0x002d,  ZB_RO, ZB_UINT48    },  
            {126, "Mise à jour disponible",             "update",      UINT8,        0,      ANY,  C_ANY,   G_ANY,  STATIC_VALUE,  CLASS_BOOL,  "mdi:download",                        0x0000, 0x0000,  ZB_NO, ZB_NO        },  
            #  {127, "Dernière actualisation",             "timestamp",   UINT64,       0,      ANY,  C_ANY,   G_ANY,  STATIC_VALUE,  TIMESTAMP,   "",                                    0x0000, 0x0000,  ZB_NO, ZB_NO        },
            #  {128, "Free RAM",                           "free-ram",    UINT32,       0,      ANY,  C_ANY,   G_ANY,  REAL_TIME,     BYTES,       "",                                    0x0000, 0x0000,  ZB_NO, ZB_NO        },
        ]
    }  
} 

TICMETER_CLUSTER = "ff42"
