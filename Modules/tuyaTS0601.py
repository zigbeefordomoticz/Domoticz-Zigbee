
from Modules.domoMaj import MajDomoDevice
from Modules.tuyaTools import store_tuya_attribute
from Modules.tools import checkAndStoreAttributeValue
from Modules.domoTools import Update_Battery_Device


# Generic functions

def ts0601_response(self, Devices, model_name, NwkId, Ep, dp, datatype, data):
    self.log.logging("Tuya", "Debug", "ts0601_response - %s %s %s %s %s" % (NwkId, model_name, dp, datatype, data), NwkId)
    
    dps_mapping = ts0601_extract_data_point_infos( self, model_name) 
    if dps_mapping is None:
        return False
    
    str_dp = "%02x" %dp
    if str_dp not in dps_mapping:
        self.log.logging("Tuya", "Log", "ts0601_response - unknow dp %s %s %s %s %s" % (NwkId, str_dp, datatype, data, str(dps_mapping)), NwkId)
        store_tuya_attribute(self, NwkId, "UnknowDp_0x%02x_Dt_0x%02x" % (dp, datatype) , data)
        return False
    
    value = int(data, 16)
    if "EvalExp" in dps_mapping[ str_dp ]:
        value = evaluate_expression_with_data(self, dps_mapping[ str_dp ][ "EvalExp"], value)

    if "store_tuya_attribute" in dps_mapping[ str_dp ]:
        store_tuya_attribute(self, NwkId, dps_mapping[ str_dp ]["store_tuya_attribute"], data)
    
    if "sensor_type" not in dps_mapping[ str_dp ]:
        if "store_tuya_attribute" not in dps_mapping[ str_dp ]:
            store_tuya_attribute(self, NwkId, "UnknowDp_0x%02x_Dt_0x%02x" % (dp, datatype) , data)
        return True
    
    sensor_type = dps_mapping[ str_dp ][ "sensor_type"]
    if sensor_type not in DP_SENSOR_FUNCTION:
        self.log.logging("Tuya", "Error", "ts0601_response - no sensor function found for %s %s %s %s %s" % (
            NwkId, sensor_type, dp, datatype, data), NwkId)
        return True
    
    value = check_domo_format_req( self, dps_mapping[ str_dp ], value)
    
    func = DP_SENSOR_FUNCTION[ sensor_type ]
    func(self, Devices, NwkId, Ep, value )
    return True
        
        
# Helpers        

def evaluate_expression_with_data(self, expression, value):
    try:
        return eval( expression )
        
    except NameError as e:
        self.log.logging("ZclClusters", "Error", "Undefined variable, please check the formula %s" %expression)
    
    except SyntaxError as e:
        self.log.logging("ZclClusters", "Error", "Syntax error, please check the formula %s" %expression)

    except ValueError as e:
        self.log.logging("ZclClusters", "Error", "Value Error, please check the formula %s %s" %(expression, e))
        
    return value

def check_domo_format_req( self, dp_informations, value):
    
    if "DomoDeviceFormat" not in dp_informations:
        return value
    return str(value) if dp_informations[ "DomoDeviceFormat" ] == "str" else value

def ts0601_extract_data_point_infos( self, model_name):
    
    if model_name not in self.DeviceConf:
        return None
    if "TS0601_DP" not in self.DeviceConf[model_name ]:
        return None
    return self.DeviceConf[model_name ][ "TS0601_DP" ]



# Sensors responses

def ts0601_motion(self, Devices, nwkid, ep, value):
    # Occupancy
    self.log.logging("Tuya", "Debug", "ts0601_motion - Occupancy %s %s %s" % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Occupancy", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0406", value )
    checkAndStoreAttributeValue(self, nwkid, "01", "0406", "0000", value)


def ts0601_illuminance(self, Devices, nwkid, ep, value):
    # Illuminance
    self.log.logging("Tuya", "Debug", "ts0601_illuminance - Illuminance %s %s %s" % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Illuminance", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0400", value)
    checkAndStoreAttributeValue(self, nwkid, "01", "0400", "0000", value)


def ts0601_temperature(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya", "Debug", "ts0601_temperature - Temperature %s %s %s " % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Temp", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0402", value)
    
    
def ts0601_humidity(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya", "Debug", "ts0601_humidity - humidity %s %s %s " % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Humi", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0405", value)


def ts0601_distance(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya", "Debug", "ts0601_distance - Distance %s %s %s " % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Distance", value)
    MajDomoDevice(self, Devices, nwkid, ep, "Distance", value)


def ts0601_battery(self, Devices, nwkid, ep, value ):
    self.log.logging("Tuya", "Debug", "ts0601_battery - Battery %s %s %s" % (nwkid, ep, value), nwkid)
        
    store_tuya_attribute(self, nwkid, "Battery", value)
    checkAndStoreAttributeValue(self, nwkid, "01", "0001", "0000", value)
    self.ListOfDevices[nwkid]["Battery"] = value
    Update_Battery_Device(self, Devices, nwkid, value)
    store_tuya_attribute(self, nwkid, "BatteryStatus", value)


def ts0601_tamper(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya", "Debug", "ts0601_tamper - Tamper %s %s %s" % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "SmokeTamper", value)
    state = "01" if value != 0 else "00"
    MajDomoDevice(self, Devices, nwkid, ep, "0009", state)


def ts0601_switch(self, Devices, nwkid, ep, value):
    self.log.logging("Tuya", "Debug", "ts0601_switch - Switch%s %s %s" % (nwkid, ep, value), nwkid)
    store_tuya_attribute(self, nwkid, "Switch", value)
    state = "01" if value != 0 else "00"
    MajDomoDevice(self, Devices, nwkid, ep, "0006", state)


def ts0601_level_percentage(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya", "Debug", "ts0601_level_percentage - Percentage%s %s %s" % (nwkid, ep, value), nwkid, )
    store_tuya_attribute(self, nwkid, "PercentState", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0008", "%02x" %value)


def ts0601_door(self, Devices, nwkid, ep, value):
    # Door Contact: 0x00 => Closed, 0x01 => Open
    self.log.logging( "Tuya", "Debug", "ts0601_door - Door Contact%s %s %s" % (nwkid, ep, value), nwkid, )
    MajDomoDevice(self, Devices, nwkid, "01", "0500", "%02x" %value )
    store_tuya_attribute(self, nwkid, "DoorContact", value)


def ts0601_co2ppm(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya", "Debug", "ts0601_co2ppm - CO2 ppm %s %s %s" % (nwkid, ep, value), nwkid, )
    store_tuya_attribute( self, nwkid, "CO2 ppm", value, )
    MajDomoDevice(self, Devices, nwkid, ep, "0402", value, Attribute_="0005")


def ts0601_voc(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya", "Debug", "ts0601_voc - VOC ppm %s %s %s" % (nwkid, ep, value), nwkid, )
    store_tuya_attribute(self, nwkid, "VOC ppm", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0402", value, Attribute_="0003")


def ts0601_ch20(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya", "Debug", "ts0601_ch20 - CH2O ppm %s %s %s" % (nwkid, ep, value), nwkid, )
    store_tuya_attribute(self, nwkid, "CH2O ppm", value)
    MajDomoDevice(self, Devices, nwkid, ep, "0402", value, Attribute_="0004")


def ts0601_summation_energy(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya", "Debug", "ts0601_summation_energy - Summation %s %s %s" % (nwkid, ep, value), nwkid, )
    MajDomoDevice(self, Devices, nwkid, ep, "0702", str(value), Attribute_="0000")
    checkAndStoreAttributeValue(self, nwkid, ep, "0702", "0000", value)  # Store int
    store_tuya_attribute(self, nwkid, "Energy", str(value))


def ts0601_instant_power(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya", "Debug", "ts0601_instant_power - Instant Power %s %s %s" % (nwkid, ep, value), nwkid, )
    checkAndStoreAttributeValue(self, nwkid, ep, "0702", "0400", str(value))
    MajDomoDevice(self, Devices, nwkid, ep, "0702", str(value))
    store_tuya_attribute(self, nwkid, "InstantPower", str(value))  # Store str


def ts0601_voltage(self, Devices, nwkid, ep, value):
    self.log.logging( "Tuya", "Debug", "ts0601_voltage - Voltage %s %s %s" % (nwkid, ep, value), nwkid, )
    MajDomoDevice(self, Devices, nwkid, ep, "0001", str(value))
    store_tuya_attribute(self, nwkid, "Voltage", str(value))



DP_SENSOR_FUNCTION = {
    "motion": ts0601_motion,
    "illuminance": ts0601_illuminance,
    "temperature": ts0601_temperature,
    "humidity": ts0601_humidity,
    "distance": ts0601_distance,
    "battery": ts0601_battery,
    "tamper": ts0601_tamper,
    "switch": ts0601_switch,
    "door": ts0601_door,
    "lvl_percentage": ts0601_level_percentage,
    "co2": ts0601_co2ppm,
    "voc": ts0601_voc,
    "ch20": ts0601_ch20,
    "metering": ts0601_summation_energy,
    "power": ts0601_instant_power,
    "voltage": ts0601_voltage
}