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
    Module: widget.py

    Description: Widget management

"""



SWITCH_SELECTORS = {
    "ACMode": {
        "00": (0, "00"),
        "03": (1, "10"),
        "04": (2, "20"),
        "08": (3, "30"),
        "07": (4, "40"),
        "ForceUpdate": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|Cool|Heat|Dry|Fan",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Froid|Chaud|Déshumidicateur|Ventilateur"
            },
            "es-ES": {
                "LevelNames": "Off|Frío||Calefacción|Deshumidificador|Ventilador"
            }
        }
    },
    "ACMode_2": {
        "00": (0, "00"),
        "03": (1, "10"),
        "04": (2, "20"),
        "08": (3, "30"),
        "07": (4, "40"),
        "ForceUpdate": True,
        "OffHidden": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|Cool|Heat|Dry|Fan",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Froid|Chaud|Déshumidicateur|Ventilateur"
            },
            "es-ES": {
                "LevelNames": "Off|Frío||Calefacción|Deshumidificador|Ventilador"
            }
        }
    },
    "ACSwing": {
        "00": (0, "00"),
        "01": (1, "10"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|On",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Allumé"
            }
        }
    },
    "AirPurifierMode": {
        "00": (0, "00"),
        "01": (1, "10"),
        "02": (2, "20"),
        "03": (2, "30"),
        "04": (2, "40"),
        "05": (2, "50"),
        "06": (2, "60"),
        "ForceUpdate": True,
        "SelectorStyle": 0,
        "LevelNames": "Off|Auto|Spd1|Spd2|Spd3|Spd4|Spd5",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Auto|Vit1|Vit2|Vit3|Vit4|V5"
            }
        }
    },
    "Alarm": {
        "00": (0, "No Alert"),
        "01": (1, "Level 1"),
        "02": (2, "Level 2"),
        "03": (3, "Level 3"),
        "04": (4, "Critical"),
        "ForceUpdate": True
    },
    "AlarmWD": {
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Stop|Alarm|Siren|Strobe|Armed|Disarmed",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêter|Alarme|Sirène|Flash|Armer|Désarmer"
            }
        }
    },
    "Aqara": {
        "ForceUpdate": True,
        "LevelNames": "Off|Shake|Alert|Free_Fall|Flip_90|Flip_180|Move|Tap|Clock_Wise|Anti_Clock_Wise",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Agiter|Alerte|Chute libre|Retourner_90|Retourner_180|Bouger|Frapper|Rotation Horaire|Rotation Antihoraire"
            }
        }
    },
    "AqaraOppleMiddle": {
        "00": (0, "00"),
        "01": (1, "10"),
        "02": (2, "20"),
        "03": (3, "30"),
        "04": (4, "40"),
        "05": (5, "50"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "off|Click|Double click|Tripple click|Long click|Release",
        "Language": {
            "fr-FR": {
                "LevelNames": "off|Clic|Double clic|Triple clic|Long clic|Relacher"
            }
        }
    },
    "AqaraOppleMiddleBulb": {
        "00": (0, "00"),
        "01": (1, "10"),
        "02": (2, "20"),
        "03": (3, "30"),
        "04": (4, "40"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|On|-|+|Release",
        "Language": {
            "fr-FR": {
                "LevelNames": "Eteindre|Marche|-|+|Arrêt"
            }
        }
    },
    "BSO-Orientation": {
        0: (0, "00"),
        10: (1, "10"),
        20: (2, "20"),
        30: (3, "30"),
        40: (4, "40"),
        50: (5, "50"),
        60: (6, "60"),
        70: (7, "70"),
        80: (8, "80"),
        90: (9, "90"),
        100: (10, "100"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|0°|10°|20°|30°|40°|50°|60°|70°|80°|90°"
    },
    "Button": {
        "01": (1, "On"),
        "ForceUpdate": True
    },
    "Button_3": {
        "00": (0, "00"),
        1: (1, "10"),
        "1": (1, "10"),
        "01": (1, "10"),
        2: (2, "20"),
        "2": (2, "20"),
        "02": (2, "20"),
        3: (3, "30"),
        "3": (3, "30"),
        "03": (3, "30"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Click|Double Click|Long Click",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Click|Double Click|Long Click"
            }
        }
    },
    "CAC221ACMode": {
        "00": (0, "00"),
        "01": (1, "10"),
        "03": (2, "20"),
        "04": (2, "30"),
        "08": (3, "40"),
        "07": (4, "50"),
        "ForceUpdate": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|Auto|Cool|Heat|Dry|Fan",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Auto|Froid|Chaud|Déshumidicateur|Ventilateur"
            },
            "es-ES": {
                "LevelNames": "Off|Auto|Frío||Calefacción|Deshumidificador|Ventilador"
            }
        }
    },
    "ContractPower": {
        "ForceUpdate": False,
        "OffHidden": True,
        "SelectorStyle": 0,
        "LevelNames": "Off|3KVA|6KVA|9KVA|12KVA|15KVA",
        "Language": {
            "fr-FR": {
                "LevelNames": "Off|3KVA|6KVA|9KVA|12KVA|15KVA"
            }
        }
    },
    "DButton": {
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Switch 1|Switch 2|Both_Click",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Click Gauche|Click Droit|Click des 2"
            }
        }
    },
    "DButton_3": {
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Left click|Left Double click|Left Long click|Right click|Right Double Click|Right Long click|Both click|Both Double click|Both Long click",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Click Gauche|Double click Gauche|Long Click Gauche|Click Droit|Double Click Droit|Long Click Droit|Click des 2|Double Click des 2|Long Click des 2"
            }
        }
    },
    "DSwitch": {
        "LevelNames": "Off|Left Click|Right Click|Both Click",
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 0,
        "Language": {
            "fr-FR": {
                "LevelNames": "Off|Left Click|Right Click|Both Click"
            }
        }
    },
    "Door": {
        "00": (0, "Closed"),
        "01": (1, "Open"),
        "ForceUpdate": False
    },
    "DoorLock": {
        "01": (0, "Closed"),
        "00": (1, "Open"),
        "ForceUpdate": False
    },
    "FIP": {
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Confort|Confort -1|Confort -2|Eco|Frost Protection|Off",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Confort|Confort -1|Confort -2|Eco|Hors Gel|Arrêt"
            }
        }
    },
    "FanControl": {
        "00": (0, "00"),
        "05": (1, "10"),
        "01": (2, "20"),
        "02": (3, "30"),
        "03": (4, "40"),
        "ForceUpdate": True,
        "OffHidden": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|Auto|Low|Medium|High",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Auto|Bas|Moyen|Fort"
            }
        }
    },
    "GenericLvlControl": {
        "off": (1, "10"),
        "on": (2, "20"),
        "moveup": (3, "30"),
        "movedown": (4, "40"),
        "stop": (5, "50"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Off|On|Dim +|Dim -|Stop",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Eteindre|Marche|Monter|Descendre|Arrêt"
            }
        }
    },
    "Generic_5_buttons": {
        "00": (0, "00"),
        "01": (1, "10"),
        "02": (2, "20"),
        "03": (3, "30"),
        "04": (4, "40"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "button1|button2|button3|button4|button5",
        "Language": {
            "fr-FR": {
                "LevelNames": "Bouton1|Bouton2|Bouton3|Bouton4|Bouton5"
            }
        }
    },
    "HACTMODE": {
        "00": (1, "10"),
        "03": (2, "20"),
        "ForceUpdate": False,
        "OffHidden": True,
        "SelectorStyle": 0,
        "LevelNames": "Off|Conventional|Fil Pilote",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Normal|Fil Pilote"
            }
        }
    },
    "HeatingStatus": {
        0: (0, "Off"),
        1: (1, "10"),
        2: (2, "20"),
        "ForceUpdate": True,
        "LevelNames": "Off|Heating|Not Heating",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Allumer|Eteind"
            }
        }
    },
    "HeimanSceneSwitch": {
        0: (0, "Off"),
        240: (1, "10"),
        241: (2, "20"),
        242: (3, "30"),
        243: (4, "40"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Movie|At Home|Sleep|Go Out",
        "Language": {
            "fr-FR": {
                "Off|Movie|At Home|Sleep|Go Out"
            }
        }
    },
    "HueSmartButton": {
        "toggle": (1, "10"),
        "move": (3, "30"),
        "SelectorStyle": 1,
        "LevelNames": "Off|toggle|move",
        "Language": {}
    },
    "IAS_ACE": {
        "00": (0, "00"),
        "01": (2, "20"),
        "02": (1, "10"),
        "03": (3, "30"),
        "04": (4, "40"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Emergency|Arm Day (Home Zones Only)|Arm All Zones|Disarm",
        "Language": {
            "fr-FR": {
                "LevelNames": "Off|Urgence|Armer (zone maison)|Armer (toutes zones)|Désarmer"
            }
        }
    },
    "INNR_RC110_LIGHT": {
        "00": (0, "00"),
        "01": (1, "01"),
        "ForceUpdate": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|On|+|-|Long +|Long -|Release",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Marche|+|-|Long +|Long -|Rel."
            }
        }
    },
    "INNR_RC110_SCENE": {
        "00": (0, "00"),
        "01": (1, "01"),
        "ForceUpdate": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|On|+|-|Long +|Long -|Release|Scene1|Scene2|Scene3|Scene4|Scene5|Scene6",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Marche|+|-|Long +|Long -|Rel.|Scène1|Scène2|Scène3|Scène4|Scène5|Scène6"
            }
        }
    },
    "Ikea_Remote_2N": {
        "00": (0, "00"),
        "toggle": (1, "10"),
        "left_click": (2, "20"),
        "right_click": (3, "30"),
        "click_up": (4, "40"),
        "hold_up": (5, "50"),
        "release_up": (6, "60"),
        "click_down": (7, "70"),
        "hold_down": (8, "80"),
        "release_down": (9, "90"),
        "right_hold": (10, "100"),
        "right_release": (11, "110"),
        "left_hold": (12, "120"),
        "left_release": (13, "130"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|ToggleOnOff|Left_click|Right_click|Up_click|Up_push|Up_release|Down_click|Down_push|Down_release|Right_push|Right_release|Left_push|Left_release",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Basculer|Click Gauche|Click Droit|Click Haut|Click Haut Long|Relacher Haut|Click Bas|Click Bas Long|Relacher Bas|Click Long Droit|Relacher Droit|Click Long Gauche|Relacher Gauche"
            }
        }
    },
    "Ikea_Round_5b": {
        "00": (0, "00"),
        "toggle": (1, "10"),
        "left_click": (2, "20"),
        "right_click": (3, "30"),
        "click_up": (4, "40"),
        "hold_up": (5, "50"),
        "release_up": (6, "60"),
        "click_down": (7, "70"),
        "hold_down": (8, "80"),
        "release_down": (9, "90"),
        "right_hold": (10, "100"),
        "left_hold": (12, "120"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|ToggleOnOff|Left_click|Right_click|Up_click|Up_push|Up_release|Down_click|Down_push|Down_release|Right_push|Right_release|Left_push|Left_release",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Basculer|Click Gauche|Click Droit|Click Haut|Click Haut Long|Relacher Haut|Click Bas|Click Bas Long|Relacher Bas|Click Long Droit|Relacher Droit|Click Long Gauche|Relacher Gauche"
            }
        }
    },
    "Ikea_Round_OnOff": {
        "00": "00",
        "toggle": (1, "10"),
        "ForceUpdate": True
    },
    "KF204Switch": {
        "00": (0, "00"),
        "01": (1, "10"),
        "02": (2, "20"),
        "03": (3, "30"),
        "04": (4, "40"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 0,
        "LevelNames": "Off|0|X|+|-",
        "Language": {
            "fr-FR": {
                "LevelNames": "Off|0|X|+|-"
            }
        }
    },
    "LegranCableMode": {
        "0100": (1, "10"),
        "0200": (2, "20"),
        "ForceUpdate": False,
        "OffHidden": True,
        "SelectorStyle": 0,
        "LevelNames": "Off|Conventional|Fil Pilote",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Normal|Fil Pilote"
            }
        }
    },
    "LegrandSelector": {
        "00": (0, "00"),
        "01": (1, "10"),
        "moveup": (2, "20"),
        "movedown": (3, "30"),
        "stop": (4, "40"),
        "02": (5, "50"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|On|Dim +|Dim -|Stop|Toggle",
        "Language": {
            "fr-FR": {
                "LevelNames": "Eteindre|Allumer|Monter|Descendre|Arrêt|Toggle"
            }
        }
    },
    "LegrandSleepWakeupSelector": {
        "": (0, "00"),
        "00": (1, "10"),
        "01": (2, "20"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Sleep|WakeUp",
        "Language": {
            "fr-FR": {
                "LevelNames": "Off|Coucher|Lever"
            }
        }
    },
    "LivoloSWL": {
        "00": (0, "Off"),
        "01": (1, "On"),
        "ForceUpdate": False
    },
    "LivoloSWR": {
        "10": (0, "Off"),
        "11": (1, "On"),
        "ForceUpdate": False
    },
    "LumiLock": {
        "1101": (1, "10"),
        "1107": (2, "20"),
        "1207": (3, "30"),
        "1601": (4, "40"),
        "1311": (5, "50"),
        "120101": (6, "60"),
        "121101": (7, "70"),
        "120102": (8, "80"),
        "121102": (9, "90"),
        "120103": (10, "100"),
        "121103": (11, "110"),
        "120104": (12, "120"),
        "121104": (13, "130"),
        "120105": (14, "140"),
        "121105": (15, "150"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Unauthorized|Bad Insert|Unlock all to neutral|All Key Removed|New Key|Autorized Key #1|Key in lock #1|Autorized Key #2|Key in lock #2|Autorized Key #3|Key in lock #3|Autorized Key #4|Key in lock #4|Autorized Key #5|Key in lock #5",
        "Language": {
            "fr-FR": {
                "Off|Unauthorized|Bad Insert|Unlock all to neutral|All Key Removed|New Key|Autorized Key #1|Key in lock #1|Autorized Key #2|Key in lock #2|Autorized Key #3|Key in lock #3|Autorized Key #4|Key in lock #4|Autorized Key #5|Key in lock #5"
            }
        }
    },
    "Motionac01": {
        "0": (0, "00"),
        "10": (1, "10"),
        "20": (2, "20"),
        "30": (3, "30"),
        "40": (4, "40"),
        "50": (5, "50"),
        "60": (6, "60"),
        "70": (7, "70"),
        "80": (8, "80"),
        "ForceUpdate": True,
        "OffHidden": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|Enter|Leave|Left_enter|Right_leave|Right_enter|Left_leave|Approach|Away"
    },
    "OrviboRemoteSquare": {
        0: (0, "Off"),
        11: (1, "10"),
        12: (2, "20"),
        13: (3, "30"),
        21: (4, "40"),
        22: (5, "50"),
        23: (6, "60"),
        31: (7, "70"),
        32: (8, "80"),
        33: (9, "90"),
        41: (10, "100"),
        42: (11, "110"),
        43: (12, "120"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|BT 1 Click|BT 1 Long|BT 1 Release|BT 2 Click|BT 2 Long|BT 2 Release|BT 3 Click|BT 3 Long|BT 3 Release|BT 4 Click|BT 4 Long|BT 4 Release",
        "Language": {
            "fr-FR": {
                "Off|BT 1 Click|BT 1 Long|BT 1 Release|BT 2 Click|BT 2 Long|BT 2 Release|BT 3 Click|BT 3 Long|BT 3 Release|BT 4 Click|BT 4 Long|BT 4 Release"
            }
        }
    },
    "Plug": {
        "00": (0, "Off"),
        "01": (1, "On"),
        "ForceUpdate": False
    },
    "PollingControl": {
        "00": (0, "00"),
        "01": (1, "10"),
        "02": (2, "20"),
        "ForceUpdate": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|Slow Polling|Fast Polling",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Mesures normale|Mesures rapides"
            }
        }
    },
    "PollingControlV2": {
        "00": (0, "00"),   # Off
        "01": (3, "10"),   # "2/day" -> 43200 secondes ( 12 heures)
        "02": (4, "20"),   # "20/day" ->  4320 secondes ( 1h 12 minutes)
        "03": (5, "30"),   # "96/day" ->   900 secondes ( 15 minutes)
        "05": (2, "40"),   # Fast Polling, Force polling to every 15s
        "ForceUpdate": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|2x/day|20x/day|96x/day|Fast Polling",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|2x/day|20x/day|96x/day|Mesures rapides"
            }
        }
    },
    "SOS": {
        "01": (1, "On"),
        "ForceUpdate": True
    },
    "Smoke": {
        "00": (0, "Off"),
        "01": (1, "On"),
        "02": (1, "On"),
        "ForceUpdate": False
    },
    "Switch": {
        "00": (0, "Off"),
        0: (0, "Off"),
        "01": (1, "On"),
        1: (1, "On"),
        "ForceUpdate": False
    },
    "SwitchAQ2": {
        "1": (0, "00"),
        "2": (1, "10"),
        "3": (2, "20"),
        "4": (3, "30"),
        "01": (0, "00"),
        "02": (1, "10"),
        "03": (2, "20"),
        "04": (3, "30"),
        "80": (3, "30"),
        "255": (3, "30"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "One click|Two clicks|Tree clicks|Four+ clicks",
        "Language": {
            "fr-FR": {
                "LevelNames": "Simple click|Double click|Triple click|Quadruple+ click"
            }
        }
    },
    "SwitchAQ2WithOff": {
        "0": (0, "00"),
        "1": (1, "10"),
        "2": (2, "20"),
        "3": (3, "30"),
        "4": (4, "40"),
        "01": (1, "10"),
        "02": (2, "20"),
        "03": (3, "30"),
        "04": (4, "40"),
        "80": (5, "50"),
        "255": (4, "40"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off | One click|Two clicks|Tree clicks|Four+ clicks",
        "Language": {
            "fr-FR": {
                "LevelNames": "Off | Simple click|Double click|Triple click|Quadruple+ click"
            }
        }
    },
    "SwitchAQ3": {
        "1": (0, "00"),
        "2": (1, "10"),
        "01": (0, "00"),
        "02": (1, "10"),
        "16": (2, "20"),
        "17": (3, "30"),
        "18": (4, "40"),
        "00": (0, "00"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Click|Double click|Long click|Release click|Shake",
        "Language": {
            "fr-FR": {
                "LevelNames": "Click|Double click|Long click|Relacher click|Remuer"
            }
        }
    },
    "SwitchAQ3WithOff": {
        "0": (0, "00"),
        "1": (1, "10"),
        "2": (2, "20"),
        "01": (1, "10"),
        "02": (2, "20"),
        "16": (3, "30"),
        "17": (4, "40"),
        "18": (5, "50"),
        "00": (0, "00"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Click|Double click|Long click|Release click|Shake",
        "Language": {
            "fr-FR": {
                "LevelNames": "Off|Click|Double click|Long click|Relacher click|Remuer"
            }
        }
    },
    "SwitchButton": {
        "00": (0, "Off"),
        "01": (1, "On"),
        "ForceUpdate": True
    },
    "SwitchIKEA": {
        "00": (0, "Off"),
        "01": (1, "10"),
        "02": (2, "20"),
        "03": (3, "30"),
        "04": (4, "40"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|On|Push Up|Push Down|Release",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Marche|Appuyer Haut|Appuyer Bas|Relacher"
            }
        }
    },
    "TINT_REMOTE_WHITE": {
        "00": (0, "00"),
        "01": (1, "10"),
        "02": (2, "20"),
        "03": (3, "30"),
        "04": (4, "40"),
        "05": (5, "50"),
        "06": (6, "60"),
        "07": (7, "70"),
        "08": (8, "80"),
        "09": (9, "90"),
        "10": (10, "100"),
        "11": (11, "110"),
        "12": (12, "120"),
        "13": (13, "130"),
        "14": (14, "140"),
        "15": (15, "150"),
        "16": (16, "160"),
        "17": (17, "170"),
        "18": (18, "180"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|On|Color -|Color +|Dim -| Dim+|Long Dim-|Long Dim+|Stop|Scene1|Scene2|Scene3|Scene4|Scene5|Scene6|Scene7|Color Up|Color Down|Color Stop",
        "Language": {
            "fr-FR": {
                "LevelNames": "Off|On|Color -|Color +|Dim -| Dim+|Long Dim-|Long Dim+|Stop|Scene1|Scene2|Scene3|Scene4|Scene5|Scene6|Scene7|Color Up|Color Down|Color Stop"
            }
        }
    },
    "Tamper": {
        "00": (0, "No Alert"),
        "01": (1, "Tamper "),
        "ForceUpdate": False
    },
    "ThermoMode": {
        "00": (0, "00"),
        "01": (1, "10"),
        "03": (2, "20"),
        "04": (3, "30"),
        "08": (4, "40"),
        "07": (5, "50"),
        "ForceUpdate": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|Auto|Cool|Heat|Dry|Fan",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Auto|Froid|Chaud|Déshumidicateur|Ventilateur"
            }
        }
    },
    "ThermoModeEHZBRTS": {
        "00": (0, "Off"),
        "01": (1, "10"),
        "02": (2, "20"),
        "03": (3, "30"),
        "04": (4, "40"),
        "05": (5, "50"),
        "06": (6, "60"),
        "ForceUpdate": False,
        "SelectorStyle": 1,
        "LevelNames": "Off| Manual| Schedule| Manual Energy Saver| Schedule Energy Saver| Holiday| Holiday Frost Protection",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt| Manuel| Programmé| Mode Eco. manuel| Mode Eco. Programmé| Congés| Hors Gel"
            }
        }
    },
    "ThermoMode_2": {
        0: (0, "Off"),
        1: (1, "10"),
        2: (2, "20"),
        "ForceUpdate": True,
        "SelectorStyle": 0,
        "LevelNames": "Off|Auto|Manual",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Auto|Manuel"
            }
        }
    },
    "ThermoMode_3": {
        0: (0, "Off"),
        1: (1, "10"),
        2: (2, "20"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Comfort|No-Freeze",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Confort|hors-gel"
            }
        }
    },
    "ThermoMode_4": {
        0: (0, "Off"),
        1: (1, "Auto"),
        2: (2, "10"),
        3: (3, "20"),
        4: (4, "30"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Auto|Manual|Temp Hand|Holidays",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Auto|Manuel|Temp Hand|Vacances"
            }
        }
    },
    "ThermoMode_5": {
        0: (0, "Off"),
        1: (1, "10"),
        2: (2, "20"),
        3: (3, "30"),
        "ForceUpdate": True,
        "OffHidden": False,
        "SelectorStyle": 0,
        "LevelNames": "Off|Auto|Manual|Away",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Auto|Manual|Away"
            }
        }
    },
    "ThermoMode_6": {
        0: (0, "00"),
        1: (1, "10"),
        2: (2, "20"),
        3: (3, "30"),
        "ForceUpdate": False,
        "OffHidden": True,
        "SelectorStyle": 0,
        "LevelNames": "Off|Cool|Heat|Fan",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Froid|Chaud|Ventilateur"
            }
        }
    },
    "ThermoMode_7": {
        2: (0, "00"),
        1: (1, "10"),
        0: (2, "20"),
        "ForceUpdate": False,
        "OffHidden": False,
        "SelectorStyle": 0,
        "LevelNames": "Off|Manual|Auto",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Manuel|Auto"
            }
        }
    },
    "ThermoMode_8": {
        0: (0, "Off"),
        1: (1, "10"),
        2: (2, "20"),
        3: (3, "30"),
        4: (4, "40"),
        5: (5, "50"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Manual|Auto|Eco|Confort|Holidays",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Manuel|Auto|Eco|Confort|Vacances"
            }
        }
    },

    "ThermoOnOff": {
        0: (0, "Off"),
        1: (1, "On"),
        "ForceUpdate": False
    },
    "Toggle": {
        "ForceUpdate": True,
        "SelectorStyle": 0,
        "LevelNames": "Off|On|Toggle",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Marche|Bascule"
            }
        }
    },
    "TuyaRadarSensor": {
        0: (0, "Off"),
        1: (1, "10"),
        2: (2, "20"),
        "ForceUpdate": True,
        "OffHidden": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|Presence|Moving",
        "Language": {
            "fr-FR": {
                "Off|Presence|Deplacement"
            }
        }
    },
    "TuyaSiren": {
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "00": (0, "00"),
        "01": (1, "10"),
        "02": (2, "20"),
        "03": (3, "30"),
        "04": (4, "40"),
        "05": (5, "50"),
        "LevelNames": "Off|Alarm 1|Alarm 2|Alarm 3|Alarm 4|Alarm 5",
        "Languages": {
            "fr-FR": {
                "LevelNames": "Off|Alarm 1|Alarm 2|Alarm 3|Alarm 4|Alarm 5"
            }
        }
    },
    "TuyaSirenHumi": {
        "00": (0, "00"),
        "01": (1, "10"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Alarm Humidity",
        "Languages": {
            "fr-FR": {
                "LevelNames": "Off|Alarm Humidité"
            }
        }
    },
    "TuyaSirenTemp": {
        "00": (0, "00"),
        "01": (1, "10"),
        "ForceUpdate": True,
        "SelectorStyle": 1,
        "LevelNames": "Off|Alarm Temperature",
        "Languages": {
            "fr-FR": {
                "LevelNames": "Off|Alarm Température"
            }
        }
    },
    "Vibration": {
        "00": (0, "00"),
        "10": (1, "10"),
        "20": (2, "20"),
        "30": (3, "30"),
        "ForceUpdate": False,
        "SelectorStyle": 1,
        "LevelNames": "Off|Tilt|Vibrate|Free Fall",
        "Language": {
            "fr": {
                "LevelNames": "Arrêt|Incliner|Vibrer|Chute libre"
            }
        }
    },
    "Water": {
        "00": (0, "Off"),
        "01": (1, "On"),
        "ForceUpdate": False
    },
    "XCube": {
        "ForceUpdate": True,
        "LevelNames": "Off|Shake|Alert|Free_Fall|Flip_90|Flip_180|Move|Tap|Clock_Wise|Anti_Clock_Wise",
        "Language": {
            "fr-FR": {
                "LevelNames": "Arrêt|Agiter|Alerte|Chute libre|Retourner_90|Retourner_180|Bouger|Frapper|Rotation Horaire|Rotation Antihoraire"
            }
        }
    },
    "blindIKEA": {
        "00": (1, "10"),
        "01": (2, "20"),
        "02": (3, "30"),
        "ForceUpdate": True,
        "OffHidden": True,
        "SelectorStyle": 0,
        "LevelNames": "Off|Open|Close|Stop",
        "Language": {
            "fr-FR": {
                "LevelNames": "Off|Ouvrir|Fermer|Arreter"
            }
        }
    }
}


def get_force_update_value_mapping(widget_name, value):
    """
    Extract the nValue, sValue tuple and provide the ForceUpdate for any value provided.
    Return None if not found.

    Args:
        widget_name: The name of the widget.
        value: The value to be mapped.

    Returns:
        The nValue, sValue tuple along with the ForceUpdate value, or None if not found.
    """

    sub_dict = SWITCH_SELECTORS.get(widget_name, {})
    value = sub_dict.get(value, None)
    force_update_value = sub_dict.get("ForceUpdate", False)

    return value + (force_update_value,) if value is not None else None
