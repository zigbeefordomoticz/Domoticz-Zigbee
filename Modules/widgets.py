#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author:  pipiche38
#   French translation: @martial83
#
"""
    Module: widget.py

    Description: Widget management

"""


SWITCH_LVL_MATRIX = {
    "Plug": { 

        "00": ( 0, "Off"), 
        "01": ( 1, "On") , 
        "ForceUpdate": False },

    "Door":  {
        "00": ( 0, "Closed"),
        "01": ( 1, "Open"),
        "ForceUpdate": False},

    "DoorLock":  {
        # Doorlock widget seems to behave inverted
        "01": ( 0, "Closed" ),
        "00": ( 1, "Open" ),
        "ForceUpdate": False },

    "LumiLock": {
        '1101':   ( 1,  "10"), # Unauthorized
        '1107':   ( 2,  "20"), # Bad Insert
        '1207':   ( 3,  "30"), # Unlock all to neutral
        '1601':   ( 4,  "40"), # All Key Removed
        '1311':   ( 5,  "50"), # New Key
        '120101': ( 6,  "60"), # Authorized #1
        '121101': ( 7,  "70"), # Key in Lock #1
        '120102': ( 8,  "80"), # Key 2
        '121102': ( 9,  "90"),
        '120103': (10, "100"), # Key 3
        '121103': (11, "110"),
        '120104': (12, "120"), # Key 4
        '121104': (13, "130"),
        '120105': (14, "140"), # Key 5
        '121105': (15, "150"),
        "ForceUpdate": True,
        "LevelNames": "Off|Unauthorized|Bad Insert|Unlock all to neutral|All Key Removed|New Key|Autorized Key #1|Key in lock #1|Autorized Key #2|Key in lock #2|Autorized Key #3|Key in lock #3|Autorized Key #4|Key in lock #4|Autorized Key #5|Key in lock #5",
        "Language": { 
            "fr-FR": {"Off|Unauthorized|Bad Insert|Unlock all to neutral|All Key Removed|New Key|Autorized Key #1|Key in lock #1|Autorized Key #2|Key in lock #2|Autorized Key #3|Key in lock #3|Autorized Key #4|Key in lock #4|Autorized Key #5|Key in lock #5"}
        }
    },

    "Smoke": { 
        "00": ( 0, "Off"), 
        "01": ( 1, "On"), 
        "ForceUpdate": False},

    "Water": { 
        "00": ( 0, "Off"), 
        "01": ( 1, "On"), 
        "ForceUpdate": False},

    "Switch": { 
        "00": ( 0,"Off"), 
        "01": ( 1,"On") , 
        "ForceUpdate": False},

    "SwitchButton": { 
        "00": ( 0,"Off"), 
        "01": ( 1,"On") , 
        "ForceUpdate": True},

    "Motion": { 
        "00": ( 0, "Off"), 
        "01": ( 1, "On") , 
        "ForceUpdate": True},

    "LivoloSWL": { 
        "00": ( 0, "Off"), 
        "01": ( 1, "On"), 
        "ForceUpdate": False },

    "LivoloSWR": { 
        "10": ( 0, "Off"), 
        "11": ( 1, "On"), 
        "ForceUpdate": False },

    "INNR_RC110_SCENE": {
        "00": (0, "00"), 
        "01": (1, "01"), 
        "ForceUpdate": False, 
        "LevelNames": "Off|On|+|-|Long +|Long -|Release|Scene1|Scene2|Scene3|Scene4|Scene5|Scene6",
        "Language": { 
            "fr-FR": { "LevelNames": "Arrêt|Marche|+|-|Long +|Long -|Rel.|Scène1|Scène2|Scène3|Scène4|Scène5|Scène6"}
            }
        },

    "INNR_RC110_LIGHT": {
        "00": (0,"00"), 
        "01": (1, "01"), 
        "ForceUpdate": False, 
        "LevelNames": "Off|On|+|-|Long +|Long -|Release",
        "Language": {
            "fr-FR": { "LevelNames": "Arrêt|Marche|+|-|Long +|Long -|Rel."}
            }
        },

    "Button": { 
        "01": (1,"On") , 
        "ForceUpdate": True},

    "Button_3": { 
        "00": (0, "00"), 
        1: (1, "10"),
        "1": (1, "10"),
        "01": (1, "10"), 
        2: (2, "20"),
        "2": (2, "20"),
        "02": (2, "20"), 
        3: (3, "30") , 
        "3": (3, "30") , 
        "03": (3, "30") , 
        "ForceUpdate": True, 
        "LevelNames": "Off|Click|Double Click|Long Click",
        "Language": {
            "fr-FR": { "LevelNames": "Arrêt|Click|Double Click|Long Click"}
            }
        },

    "Generic_5_buttons": { 
        "00": (0, "00"), 
        "01": (1, "10"), 
        "02": (2, "20"),
        "03": (3, "30"), 
        "04": (4, "40"), 
        "ForceUpdate": True, 
        "LevelNames": "button1|button2|button3|button4|button5",
        "Language": {
            "fr-FR": {"LevelNames": "Bouton1|Bouton2|Bouton3|Bouton4|Bouton5"}
            }
        },
        
    "AqaraOppleMiddleBulb": { 
        "00": (0, "00"), 
        "01": (1, "10"), 
        "02": (2, "20"),
        "03": (3, "30"), 
        "04": (4, "40"), 
        "ForceUpdate": True, 
        "LevelNames": "Off|On|-|+|Release",
        "Language": {
            "fr-FR": {"LevelNames": "Eteindre|Marche|-|+|Arrêt"}
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
        "LevelNames": "off|Click|Double click|Tripple click|Long click|Release",
        "Language": {
            "fr-FR": {"LevelNames": "off|Clic|Double clic|Triple clic|Long clic|Relacher"}
            }
        },

    "GenericLvlControl": { 
        "off": (1, "10"), 
        "on": (2, "20"), 
        "moveup": (3, "30"),
        "movedown": (4, "40"),
        "stop": ( 5, "50") ,
        "ForceUpdate": True, 
        "LevelNames": "Off|Off|On|Dim +|Dim -|Stop",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Eteindre|Marche|Monter|Descendre|Arrêt"}
            }
        },

    "LegrandSelector": { 
        "00": (0, "00"), 
        "01": (1, "10"), 
        "moveup": (2, "20"), 
        "movedown": (3, "30"), 
        "stop": (4,"40"), 
        "ForceUpdate": True, 
        "LevelNames": "Off|On|Dim +|Dim -|Stop",
        "Language": {
            "fr-FR": {"LevelNames": "Eteindre|Allumer|Monter|Descendre|Arrêt"}

            }
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
        "LevelNames": "One click|Two clicks|Tree clicks|Four+ clicks",
        "Language": {
            "fr-FR": {"LevelNames": "Simple click|Double click|Triple click|Quadruple+ click"}
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
        "LevelNames": "Click|Double click|Long click|Release click|Shake",
        "Language": {
            "fr-FR": {"LevelNames": "Click|Double click|Long click|Relacher click|Remuer"}
             }
        },

    "DSwitch": {
        "LevelNames": "Off|Left Click|Right Click|Both Click" ,
        "Language": {
            "fr-FR": {"LevelNames": "Off|Left Click|Right Click|Both Click" }
            }
        },

    "DButton": {
        "ForceUpdate": True, 
        "LevelNames": "Off|Switch 1|Switch 2|Both_Click",
        "Language": {
             "fr-FR": {"LevelNames": "Arrêt|Click Gauche|Click Droit|Click des 2" }
            }
        },

    "DButton_3": {
        "ForceUpdate": True, 
        "LevelNames": "Off|Left click|Left Double click|Left Long click|Right click|Right Double Click|Right Long click|Both click|Both Double click|Both Long click",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Click Gauche|Double click Gauche|Long Click Gauche|Click Droit|Double Click Droit|Long Click Droit|Click des 2|Double Click des 2|Long Click des 2"}
        }
    },

    "Toggle": {
        "ForceUpdate": True,
        "LevelNames": "Off|On|Toggle",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Marche|Bascule"}
        }
    },

    "Aqara": {
        "ForceUpdate": True,
        "LevelNames": "Off|Shake|Alert|Free_Fall|Flip_90|Flip_180|Move|Tap|Clock_Wise|Anti_Clock_Wise",
        "Language": {
             "fr-FR": {"LevelNames": "Arrêt|Agiter|Alerte|Chute libre|Retourner_90|Retourner_180|Bouger|Frapper|Rotation Horaire|Rotation Antihoraire"}
        }
    },

    "XCube": {
        "ForceUpdate": True, 
        "LevelNames": "Off|Shake|Alert|Free_Fall|Flip_90|Flip_180|Move|Tap|Clock_Wise|Anti_Clock_Wise",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Agiter|Alerte|Chute libre|Retourner_90|Retourner_180|Bouger|Frapper|Rotation Horaire|Rotation Antihoraire"}
        }
    },

    "Vibration": {
        "00": (0, "00"),
        "10": (1, "10"),
        "20": (2, "20"),
        "30": (3, "30"),
        "ForceUpdate": False,
        "LevelNames": "Off|Tilt|Vibrate|Free Fall",
        "Language": {
            "fr": {"LevelNames": "Arrêt|Incliner|Vibrer|Chute libre"}
        }
    },

    "SwitchIKEA": { 
        "00": (0,"Off"), 
        "01": (1,"On"), 
        "ForceUpdate": True , 
        "LevelNames": "Off|On|Push Up|Push Down|Release",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Marche|Appuyer Haut|Appuyer Bas|Relacher"}
        }
    },

    "Ikea_Round_OnOff": { 
        "00": "00", 
        "toggle": (1,"10"), 
        "ForceUpdate": True},
            
    "Ikea_Round_5b": { 
        "00": (0,"00"), 
        "toggle": (1, "10"),
        "left_click": ( 2, "20"),
        "right_click": ( 3, "30"),
        "click_up": ( 4, "40"),
        "hold_up": ( 5, "50"),
        "release_up": ( 6, "60"),
        "click_down": ( 7, "70"),
        "hold_down": ( 8, "80"),
        "release_down": ( 9, "90"),
        "right_hold": ( 10, "100"),
        "release_down": ( 11, "110"),
        "left_hold": ( 12, "120"),
        "release_down": ( 13, "130"),
        "ForceUpdate": True, 
        "LevelNames": "Off|ToggleOnOff|Left_click|Right_click|Up_click|Up_push|Up_release|Down_click|Down_push|Down_release|Right_push|Right_release|Left_push|Left_release",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Basculer|Click Gauche|Click Droit|Click Haut|Click Haut Long|Relacher Haut|Click Bas|Click Bas Long|Relacher Bas|Click Long Droit|Relacher Droit|Click Long Gauche|Relacher Gauche"}
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
        "LevelNames": "Off| Manual| Schedule| Manual Energy Saver| Schedule Energy Saver| Holiday| Holiday Frost Protection",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt| Manuel| Programmé| Mode Eco. manuel| Mode Eco. Programmé| Congés| Hors Gel"}
        }
    },

    "ThermoMode_2": {
       0: (0, "Off"), 
       1: (1, "10"), 
       2: (2, "20"),  
       "ForceUpdate": True,
       "LevelNames": "Off|Auto|Manual",
       "Language": {
           "fr-FR": {"LevelNames": "Arrêt|Auto|Manuel"}
       }
   },
   
    "ThermoMode": {
        0x00: (0, "Off"), # Off
        0x01: (1, "10"),  # Auto
        0x03: (2, "20"),  # Cool
        0x04: (3, "30"),  # Heat
        0x05: (4, "40"),  # Force heat
        0x08: (5, "50"),  # Dry
        0x07: (6, "60"),  # Fan
        "ForceUpdate": False,
        "LevelNames": "Off|Auto|Cool|Heat|Force Heat|Dry|Fan",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Auto|Froid|Chaud|Chaud Forcé|Déshumidicateur|Ventilateur"}
        }
    },

    "HACTMODE": {
        "00": ( 1, "10"),
        "03": ( 2, "20"),
        "ForceUpdate": False,
        "LevelNames": "Off|Conventional|Fil Pilote",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Normal|Fil Pilote"}
        }
    },

    'ContractPower': {
        "LevelNames": "Off|3KVA|6KVA|9KVA|12KVA|15KVA",
        "Language": {
            "fr-FR": {"LevelNames": "Off|3KVA|6KVA|9KVA|12KVA|15KVA"}
        }
    },

    "FIP": { 
        "LevelNames": "Off|Confort|Confort -1|Confort -2|Eco|Frost Protection|Off",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Confort|Confort -1|Confort -2|Eco|Hors Gel|Arrêt"}
        }
    },

    "LegranCableMode": {
        "0100": ( 1, "10"), # Normal
        "0200": ( 2, "20"), # FIP
        "ForceUpdate": False,
        "LevelNames": "Off|Conventional|Fil Pilote",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Normal|Fil Pilote"}
        }
    },

    "AlarmWD": { 
        "LevelNames": "Stop|Alarm|Siren|Strobe|Armed|Disarmed",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêter|Alarme|Sirène|Flash|Armer|Désarmer"}
        }
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
        "LevelNames": "Off|BT 1 Click|BT 1 Long|BT 1 Release|BT 2 Click|BT 2 Long|BT 2 Release|BT 3 Click|BT 3 Long|BT 3 Release|BT 4 Click|BT 4 Long|BT 4 Release",
        "Language": {
            "fr-FR": {"Off|BT 1 Click|BT 1 Long|BT 1 Release|BT 2 Click|BT 2 Long|BT 2 Release|BT 3 Click|BT 3 Long|BT 3 Release|BT 4 Click|BT 4 Long|BT 4 Release"}
        }
    },

    "Alarm": {
        '00': ( 0, "No Alert"),
        '01': ( 1, "Level 1"),
        '02': ( 2, "Level 2"),
        '03': ( 3, "Level 3"),
        '04': ( 4, "Critical"), 
        "ForceUpdate": True,
    },

    "BSO-Orientation": {
         0:  ( 0, "Off"), 
         10: ( 1,  "10"),
         20: ( 2,  "20"), 
         30: ( 3,  "30"), 
         40: ( 4,  "40"), 
         50: ( 5,  "50"),
         60: ( 6,  "60"),
         70: ( 7,  "70"),
         80: ( 8,  "80"),
         90: ( 9,  "90"),
        100: (10, "100"),
        "ForceUpdate": True,
        "LevelNames": "Off|0°|10°|20°|30°|40°|50°|60°|70°|80°|90°",
    },

    "IAS_ACE": { 
        "00": (0, "00"), 
        "01": (2, "20"), # Arm Day (Home Zones Only) - Command Arm 0x00 - Payload 0x01
        "02": (1, "10"), # Emergency - Command Emergency 0x02
        "03": (3, "30"), # Arm All Zones - Command Arm 0x00 - Payload Arm all Zone 0x03
        "04": (4, "40"), # Disarm - Command 0x00 - Payload Disarm 0x00
        "ForceUpdate": True, 
        "LevelNames": "Off|Emergency|Arm Day (Home Zones Only)|Arm All Zones|Disarm",
        "Language": {
            "fr-FR": {"LevelNames": "Off|Urgence|Armer (zone maison)|Armer (toutes zones)|Désarmer"}
            }
    },
    
    'FanControl': {
        "00": (0, "00"), # Off
        "05": (1, "10"), # Auto
        "01": (2, "20"), # Low
        "02": (3, "30"), # Moyen
        "03": (4, "40"), # Fort
        "ForceUpdate": True, 
        "LevelNames": "Off|Auto|Low|Medium|High",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Auto|Bas|Moyen|Fort"}
        }
    },
    
    "PAC-MODE": {
        "00": (0, "00"), # Off
        "03": (1, "10"),  # Cool
        "04": (2, "20"),  # Heat
        "08": (3, "30"),  # Dry
        "07": (4, "40"),  # Fan
        "ForceUpdate": True,
        "LevelNames": "Off|Cool|Heat|Dry|Fan",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Froid|Chaud|Déshumidicateur|Ventilateur"}
        }
    },

    'PAC-WING': {
        "ff": (0, "Off"), # Off - All wings stopped
        "00": (1, "10"), # Off Mode
        "01": (2, "20"), # Auto On
        "ForceUpdate": True, 
        "LevelNames": "Off|Off|Auto",
        "Language": {
            "fr-FR": {"LevelNames": "Arrêt|Off|Auto"}
        }
    },
    'KF204Switch': {
        "00": (0, "00"), # Off
        "01": (1, "10"), # Button 0 ( left)
        "02": (2, "20"), # Button X ( right)
        "03": (3, "30"), # Button - ( Down )
        "04": (4, "40"), # Button + ( Up )
        "ForceUpdate": True, 
        "LevelNames": "Off|0|X|+|-",
        "Language": {
            "fr-FR": {"LevelNames": "Off|0|X|+|-"}
        }
    },
}
