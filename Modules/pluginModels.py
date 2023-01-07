

def check_found_plugin_model( model, manufacturer_name=None, manufacturer_code=None, device_id=None):
    
    for x in PLUGIN_MODELS_MATRIX:
        if "Model" in x and model != x["Model"]:
            continue
        if (
            manufacturer_name is not None and "Manufacturer" in x and manufacturer_name not in x["Manufacturer"]
            or manufacturer_code is not None and "ManufId" in x and manufacturer_code not in x["ManufId"]
        ):
            continue
        if device_id is not None and "DeviceID" in x and manufacturer_name not in x["DeviceID"]:
            continue
        
        if "PluginModelName" in x:
            return x["PluginModelName"]
    return model


PLUGIN_MODELS_MATRIX = [
    { "Model": "TS0207",
        "DeviceID": "0402",
        "PluginModelName": "TS0207-waterleak",},
    
    { "Model": "TS0207",
        "DeviceID": "0008",
        "PluginModelName": "TS0207-extender",},


    { "Model": "AC211",
        "PluginModelName": "AC221",},
    
    { "Model": "Thermostat",
        "Manufacturer": [ "Schneider Electric", ], 
        "ManufId": [ "105e",],
        "PluginModelName": "Wiser2-Thermostat",},
    
    { "Model": "lumi.sensor_swit",
        "PluginModelName": "lumi.sensor_switch.aq3t",},
    
    { "Model": "TS011F", 
        "Manufacturer": [ "_TZ3000_vzopcetz", ], 
        "PluginModelName": "TS011F-multiprise" },
    
    { "Model": "TS011F", 
        "Manufacturer": [ "_TZ3000_pmz6mjyu", ],
        "PluginModelName": "TS011F-2Gang-switches" },
       
    { "Model": "TS011F", 
        "Manufacturer": [ "_TZ3000_qeuvnohg", ],
        "ManufId": [],
        "PluginModelName": "TS011F-din" },
    
    { "Model": "TS011F", 
        "Manufacturer": [ 
            "_TZ3000_w0qqde0g", "_TZ3000_gjnozsaz", "_TZ3000_zloso4jk","_TZ3000_cphmq0q7", 
            "_TZ3000_ew3ldmgx", "_TZ3000_dpo1ysak", "_TZ3000_typdpbpg", "_TZ3000_ksw8qtmt",
            "_TZ3000_amdymr7l", "_TZ3000_2putqrmw",],
        "ManufId": [],
        "PluginModelName": "TS011F-plug" },
    
    { "Model": "TS0201", 
        "Manufacturer": [ "_TZ3000_qaaysllp", ], 
        "ManufId": [],
        "PluginModelName": "TS0201-_TZ3000_qaaysllp" },
    
    { "Model": "TS0202", 
        "Manufacturer": [ "_TZ3210_jijr1sss", ], 
        "ManufId": [],
        "PluginModelName": "TS0201-_TZ3210_jijr1sss" },
    
]



