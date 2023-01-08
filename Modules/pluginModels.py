
from Modules.tuyaConst import (TUYA_2GANGS_DIMMER_MANUFACTURER,
                               TUYA_2GANGS_SWITCH_MANUFACTURER,
                               TUYA_CURTAIN_MAUFACTURER,
                               TUYA_DIMMER_MANUFACTURER,
                               TUYA_ENERGY_MANUFACTURER, TUYA_MOTION,
                               TUYA_SIREN_MANUFACTURER,
                               TUYA_SMARTAIR_MANUFACTURER,
                               TUYA_SMOKE_MANUFACTURER,
                               TUYA_SWITCH_MANUFACTURER, TUYA_TEMP_HUMI,
                               TUYA_THERMOSTAT_MANUFACTURER,
                               TUYA_TS0601_MODEL_NAME, TUYA_WATER_TIMER,
                               TUYA_eTRV1_MANUFACTURER,
                               TUYA_eTRV2_MANUFACTURER,
                               TUYA_eTRV3_MANUFACTURER,
                               TUYA_eTRV4_MANUFACTURER,
                               TUYA_GARAGE_DOOR,
                               TUYA_eTRV5_MANUFACTURER)

def check_found_plugin_model( self, model, manufacturer_name=None, manufacturer_code=None, device_id=None):
    self.log.logging( "Pairing", "Log", "check_found_plugin_model - %s %s %s %s" % (
        model, manufacturer_name, manufacturer_code, device_id))

    for x in PLUGIN_MODELS_MATRIX:
        if "Model" in x and model not in x["Model"]:
            continue
        if (
            "Manufacturer" in x and x["Manufacturer"] and manufacturer_name not in x["Manufacturer"]
            or "ManufId" in x and x["ManufId"] and manufacturer_code not in x["ManufId"]
        ):
            continue
        if "DeviceID" in x and x["DeviceID"] and device_id not in x["DeviceID"]:
            continue
        
        self.log.logging( "Pairing", "Log", "check_found_plugin_model - Found %s" % x)
        
        if "PluginModelName" in x:
            self.log.logging( "Pairing", "Log", "check_found_plugin_model - return %s" % (
                x["PluginModelName"]))

            return x["PluginModelName"]
        
    return model


PLUGIN_MODELS_MATRIX = [
    # CASA.ia
    { "Model": ["AC211",],
        "PluginModelName": "AC221",},
    
    # Wiser2
    { "Model": ["Thermostat",],
        "Manufacturer": [ "Schneider Electric", ], 
        "ManufId": [ "105e",],
        "PluginModelName": "Wiser2-Thermostat",},

    # LUMI
    { "Model": ["lumi.sensor_swit",],
        "PluginModelName": "lumi.sensor_switch.aq3t",},

    # TUYA
    { "Model": ["TS0003",],
        "Manufacturer": [ "_TYZB01_ncutbjdi", ],
        "PluginModelName": "TS0003-QS-Zigbee-S05-LN",},

    { "Model": ["TS0207",],
        "DeviceID": "0402",
        "PluginModelName": "TS0207-waterleak",},
    
    { "Model": ["TS0207",],
        "DeviceID": "0008",
        "PluginModelName": "TS0207-extender",},

    { "Model": ["TS011F",],
        "Manufacturer": [ "_TZ3000_vzopcetz", ], 
        "PluginModelName": "TS011F-multiprise" },
    
    { "Model": ["TS011F",],
        "Manufacturer": [ "_TZ3000_pmz6mjyu", ],
        "PluginModelName": "TS011F-2Gang-switches" },
       
    { "Model": ["TS011F",],
        "Manufacturer": [ "_TZ3000_qeuvnohg", ],
        "ManufId": [],
        "PluginModelName": "TS011F-din" },
    
    { "Model": ["TS011F",],
        "Manufacturer": [ 
            "_TZ3000_w0qqde0g", "_TZ3000_gjnozsaz", "_TZ3000_zloso4jk","_TZ3000_cphmq0q7", 
            "_TZ3000_ew3ldmgx", "_TZ3000_dpo1ysak", "_TZ3000_typdpbpg", "_TZ3000_ksw8qtmt",
            "_TZ3000_amdymr7l", "_TZ3000_2putqrmw",],
        "ManufId": [],
        "PluginModelName": "TS011F-plug" },
    
    { "Model": ["TS0201",], 
        "Manufacturer": [ "_TZ3000_qaaysllp", ], 
        "ManufId": [],
        "PluginModelName": "TS0201-_TZ3000_qaaysllp" },
    
    { "Model": ["TS0202", ], 
        "Manufacturer": [ "_TZ3210_jijr1sss", ], 
        "ManufId": [],
        "PluginModelName": "TS0201-_TZ3210_jijr1sss" },
 
    # TS601 - SIRENE
    { "Model": [ "0yu2xgi", ],
        "PluginModelName": "TS0601-sirene",},

    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_SIREN_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-sirene",},

    # TS601 -TEMP/HUMI
    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_TEMP_HUMI, 
        "ManufId": [],
        "PluginModelName": "TS0601-temphumi",},

    # TS601 -MOTION
    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_MOTION, 
        "ManufId": [],
        "PluginModelName": "TS0601-motion",},

    # TS601 -SMOKE
    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_SMOKE_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-smoke",},

    # TS601 -DIMMER
    { "Model": TUYA_TS0601_MODEL_NAME, 
        "Manufacturer": TUYA_DIMMER_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-sirene",},
  
    # TS601 - 2 Gangs Dimmer
    { "Model":TUYA_TS0601_MODEL_NAME, 
        "Manufacturer": TUYA_2GANGS_DIMMER_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-2Gangs-dimmer",},

    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_SWITCH_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-switch",},

    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_2GANGS_SWITCH_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-2Gangs-switch",},
  
    { "Model": TUYA_TS0601_MODEL_NAME, 
        "Manufacturer": TUYA_CURTAIN_MAUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-curtain",},
  
    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_THERMOSTAT_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-thermostat",},
  
    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_eTRV1_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-eTRV1",},
  
    { "Model": TUYA_TS0601_MODEL_NAME, 
        "Manufacturer": TUYA_eTRV2_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-eTRV2",},
  
    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_eTRV3_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-eTRV3",},

    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_eTRV4_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-_TZE200_b6wax7g0",},

    { "Model": TUYA_TS0601_MODEL_NAME,  
        "Manufacturer": TUYA_eTRV5_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-eTRV5",},

    { "Model": TUYA_TS0601_MODEL_NAME, 
        "Manufacturer": TUYA_SMARTAIR_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-SmartAir",},

    { "Model": TUYA_TS0601_MODEL_NAME, 
        "Manufacturer": TUYA_ENERGY_MANUFACTURER, 
        "ManufId": [],
        "PluginModelName": "TS0601-Energy",},

    { "Model": TUYA_TS0601_MODEL_NAME, 
        "Manufacturer": TUYA_WATER_TIMER, 
        "ManufId": [],
        "PluginModelName": "TS0601-Parkside-Watering-Timer",},
    
    # Garage Door
    { "Model": ["TS0601",], 
        "Manufacturer": TUYA_GARAGE_DOOR, 
        "ManufId": [],
        "PluginModelName": "TS0601-_TZE200_nklqjk62",},

    { "Model": ["TS0601",],
        "Manufacturer": [ "_TZE200_chyvmhay",],
        "ManufId": [],
        "PluginModelName": "TS0601-_TZE200_nklqjk62",},

    # Thermostat with Cooling
    { "Model": ["TS0601",],  
        "Manufacturer": [ "_TZE200_dzuqwsyg",],
        "ManufId": [],
        "PluginModelName": "TS0601-_TZE200_dzuqwsyg",},


]