


SWITCH_LVL_MATRIX = {
    'Plug': { 
        '01': ( 1, 'On') , 
        '00': ( 0, 'Off'), 
        'ForceUpdate': False },

    'Door':  { 
        '00': ( 0, 'Closed'), 
        '01': ( 1,'Open'), 
        'ForceUpdate': False},

    'Smoke': { 
        '00': ( 0, 'Off'), 
        '01': ( 1,'On'), 
        'ForceUpdate': False},

    'Water': { 
        '00': ( 0, 'Off'), 
        '01': ( 1, 'On'), 
        'ForceUpdate': False},

    'Switch': { 
        '00': ( 0,'Off'), 
        '01': ( 1,'On') , 
        'ForceUpdate': False},

    'Motion': { 
        '00': ( 0, 'Off'), 
        '01': ( 1, 'On') , 
        'ForceUpdate': True},

    'LivoloSWL': { 
        '00': ( 0, 'Off'), 
        '01': ( 1, 'On'), 
        'ForceUpdate': False },

    'LivoloSWR': { 
        '00': ( 0, 'Off'), 
        '01': ( 1, 'On'), 
        'ForceUpdate': False },

    'INNR_RC110_SCENE': {
        '00': (0, '00'), 
        '01': (1, '01'), 
        'ForceUpdate': False, 
        "LevelNames": "Off|On|click_up|click_down|move_up|move_down|stop|scene1|scene2|scene3|scene4|scene5|scene6",
        "Language": { 
            "fr": { "LevelNames": "Off|On|click_up|click_down|move_up|move_down|stop|scene1|scene2|scene3|scene4|scene5|scene6"}
            }
        },

    'INNR_RC110_LIGHT': {
        '00': (0,'00'), 
        '01': (1, '01'), 
        'ForceUpdate': False, 
        "LevelNames": "Off|On|click_up|click_down|move_up|move_down|stop",
        "Language": {
            "fr": { "LevelNames": "Off|On|click_up|click_down|move_up|move_down|stop"}
            }
        },

    'Button': { 
        '01': (1,'On') , 
        'ForceUpdate': True},

    'Button_3': { 
        '00': (0, '00'), 
        '01': (1, '10'), 
        '02': (2, '20'), 
        '03': (3, '30') , 
        'ForceUpdate': True, 
        "LevelNames": "Off|Click|Double Click|Long Click",
        "Language": {
            "fr": { "LevelNames": "Off|Click|Double Click|Long Click"}
            }
        },

    'Generic_5_buttons': { 
        '00': (0, '00'), 
        '01': (1, '10'), 
        '02': (2, '20'),
        '03': (3, '30'), 
        '04': (4, '40'), 
        'ForceUpdate': True, 
        "LevelNames": "button1|button2|button3|button4|button5",
        "Language": {
            "fr": {"LevelNames": "button1|button2|button3|button4|button5"}
            }
        },

    'GenericLvlControl': { 
        'off': (1, '10'), 
        'on': (2, '20'), 
        'moveup': (3, '30'),
        'movedown': (4, '40'),
        'stop': ( 5, '50') ,
        'ForceUpdate': True, 
        "LevelNames": "Off|Off|On|Move Up|Move Down|Stop",
        "Language": {
            "fr": {"LevelNames": "Off|Off|On|Move Up|Move Down|Stop"}
            }
        },

    'LegrandSelector': { 
        '00': (0, '00'), 
        '01': (1, '10'), 
        'moveup': (2, '20'), 
        'movedown': (3, '30'), 
        'stop': (4,'40'), 
        'ForceUpdate': True, 
        'LevelNames': 'Off|On|Move Up|Move Down|Stop',
        "Language": {
            "fr": {'LevelNames': 'Off|On|Move Up|Move Down|Stop'}
            }
        },

    'SwitchAQ2': { 
        '1': (0, '00'),
        '2': (1, '10'),
        '3': (2, '20'),
        '4': (3, '30'),
        '01': (0, '00'), 
        '02': (1, '10'), 
        '03': (2, '20'), 
        '04': (3, '30'), 
        '80': (3, '30'), 
        '255': (3, '30'), 
        'ForceUpdate': True, 
        "LevelNames": "1 Click|2 Clicks|3 Clicks|4+ Clicks",
        "Language": {
            "fr": {"LevelNames": "1 Click|2 Clicks|3 Clicks|4+ Clicks"}
            }
        },

    'SwitchAQ3': { 
        '1': (0, '00'), 
        '2': (1, '10'), 
        '01': (0, '00'), 
        '02': (1, '10'), 
        '16': (2, '20'), 
        '17': (3, '30'), 
        '18': (4, '40'), 
        'ForceUpdate': True, 
        "LevelNames": "Click|Double Click|Long Click|Release Click|Shake",
        "Language": {
            "fr": {"LevelNames": "Click|Double Click|Long Click|Release Click|Shake"}
            }
        },

    'DSwitch': {
        "LevelNames": "Off|Left Click|Right Click|Both Click" ,
        "Language": {
            "fr": {"LevelNames": "Off|Left Click|Right Click|Both Click" }
            }
        },

    'DButton': {
        "LevelNames": "Off|Switch 1|Switch 2|Both_Click",
        "Language": {
            "fr": {"LevelNames": "Off|Switch 1|Switch 2|Both_Click"}
            }
        },

    "DButton_3": {
        "LevelNames": "Off|Left Click|Left Double Clink|Left Long Click|Right Click|Right Double Click|Right Long Click|Both Click|Both Double Click|Both Long Click",
        "Language": {
            "fr": {"LevelNames": "Off|Left Click|Left Double Clink|Left Long Click|Right Click|Right Double Click|Right Long Click|Both Click|Both Double Click|Both Long Click"}
        }
    },

    'Toggle': {
        "LevelNames": "Off|On|Toggle",
        "Language": {
            "fr": {"LevelNames": "Off|On|Toggle"}
        }
    },

    'Aqara': {
        "LevelNames": "Off|Shake|Alert|Free_Fall|Flip_90|Flip_180|Move|Tap|Clock_Wise|Anti_Clock_Wise",
        "Language": {
            "fr": {"LevelNames": "Off|Shake|Alert|Free_Fall|Flip_90|Flip_180|Move|Tap|Clock_Wise|Anti_Clock_Wise"}
        }
    },

    'XCube': {
        "LevelNames": "Off|Shake|Alert|Free_Fall|Flip_90|Flip_180|Move|Tap|Clock_Wise|Anti_Clock_Wise",
        "Language": {
            "fr": {"LevelNames": "Off|Shake|Alert|Free_Fall|Flip_90|Flip_180|Move|Tap|Clock_Wise|Anti_Clock_Wise"}
        }
    },

    'Vibration': {
        '00': (0, '00'),
        '10': (1, '10'),
        '20': (2, '20'),
        '30': (3, '30'),
        'ForceUpdate': False,
        "LevelNames": "Off|Tilt|Vibrate|Free Fall",
        "Language": {
            "fr": {"LevelNames": "Off|Tilt|Vibrate|Free Fall"}
        }}
    ,

    'SwitchIKEA': { 
        '00': (0,'Off'), 
        '01': (1,'On'), 
        'ForceUpdate': True , 
        "LevelNames": "Off|On|Push Up|Push Down|Release",
        "Language": {
            "fr": {"LevelNames": "Off|On|Push Up|Push Down|Release"}
        }
    },

    'Ikea_Round_OnOff': { 
        '00': '00', 
        'toggle': (1,'10'), 
        'ForceUpdate': True},
            
    'Ikea_Round_5b': { 
        '00': (0,'00'), 
        'toggle': (1, '10'),
        'left_click': ( 2, '20'),
        'right_click': ( 3, '30'),
        'click_up': ( 4, '40'),
        'hold_up': ( 5, '50'),
        'release_up': ( 6, '60'),
        'click_down': ( 7, '70'),
        'hold_down': ( 8, '80'),
        'release_down': ( 9, '90'),
        'right_hold': ( 10, '100'),
        'release_down': ( 11, '110'),
        'left_hold': ( 12, '120'),
        'release_down': ( 13, '130'),
        'ForceUpdate': True, 
        "LevelNames": "Off|ToggleOnOff|Left_click|Right_click|Up_click|Up_push|Up_release|Down_click|Down_push|Down_release|Right_push|Right_release|Left_push|Left_release",
        "Language": {
            "fr": {"LevelNames": "Off|ToggleOnOff|Left_click|Right_click|Up_click|Up_push|Up_release|Down_click|Down_push|Down_release|Right_push|Right_release|Left_push|Left_release"}
        }
    },

    'ThermoModeEHZBRTS': {
        '00': (0, 'Off'),
        '01': (1, '10'), 
        '02': (2, '20'), 
        '03': (3, '30'), 
        '04': (4, '40'),
        '05': (5, '50'), 
        '06': (6, '60'),
        'ForceUpdate': False,  
        "LevelNames": "Off| Manual| Schedule| Manual Energy Saver| Schedule Energy Saver| Holiday| Holiday Frost Protection",
        "Language": {
            "fr": {"LevelNames": "Off| Manual| Schedule| Manual Energy Saver| Schedule Energy Saver| Holiday| Holiday Frost Protection"}
        }
    },

    'ThermoMode': {
        0: (0, 'Off'), 
        1: (1, '10'), 
        2: (2, '20'), 
        3: (3, '30'), 
        4: (4, '40'),
        'ForceUpdate': False,
        "LevelNames": "Off|Auto|Cool|Heat|Force Heat",
        "Language": {
            "fr": {"LevelNames": "Off|Auto|Cool|Heat|Force Heat"}
        }
    },

    'HACTMODE': {
        '00': ( 1, '10'),
        '03': ( 2, '20'),
        'ForceUpdate': False,
        "LevelNames": "Off|Conventional|Set Point|Fil Pilote",
        "Language": {
            "fr": {"LevelNames": "Off|Conventional|Set Point|Fil Pilote"}
        }
    },

    'FIP': { 
        "LevelNames": "Off|Confort|Confort -1|Confort -2|Eco|Frost Protection|Off",
        "Language": {
            "fr": {"LevelNames": "Off|Confort|Confort -1|Confort -2|Eco|Frost Protection|Off"}
        }
    },

    'LegrandFilPilote': { 
        "LevelNames": "Off|Confort|Confort -1|Confort -2|Eco|Frost Protection|Off",
        "Language": {
            "fr": {"LevelNames": "Off|Confort|Confort -1|Confort -2|Eco|Frost Protection|Off"}
        }
    },

    'AlarmWD': { 
        "LevelNames": "Stop|Alarm|Siren|Strobe|Armed|Disarmed",
        "Language": {
            "fr": {"LevelNames": "Stop|Alarm|Siren|Strobe|Armed|Disarmed"}
        }
    },
}
