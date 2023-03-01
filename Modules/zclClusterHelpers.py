import binascii
import struct

from Modules.pluginModels import (check_found_plugin_model,
                                  plugin_self_identifier)
from Modules.readAttributes import ReadAttributeRequest_0702_multiplier_divisor
from Modules.tools import get_deviceconf_parameter_value

# Common/ helpers

def decoding_attribute_data( AttType, attribute_value, handleErrors=False):

    if len(attribute_value) == 0:
        return ""
    
    if int(AttType, 16) == 0x00:
        return attribute_value

    if int(AttType, 16) == 0x10:  # Boolean
        return attribute_value[:2]

    if int(AttType, 16) == 0x18:  # 8Bit bitmap
        return int(attribute_value[:8], 16)

    if int(AttType, 16) == 0x19:  # 16BitBitMap
        return int(attribute_value[:4], 16)

    if int(AttType, 16) == 0x20:  # Uint8 / unsigned char
        return int(attribute_value[:2], 16)

    if int(AttType, 16) == 0x21:  # 16BitUint
        return struct.unpack("H", struct.pack("H", int(attribute_value[:4], 16)))[0]

    if int(AttType, 16) == 0x22:  # ZigBee_24BitUint
        return struct.unpack("I", struct.pack("I", int("0" + attribute_value, 16)))[0]

    if int(AttType, 16) == 0x23:  # 32BitUint
        return struct.unpack("I", struct.pack("I", int(attribute_value[:8], 16)))[0]

    if int(AttType, 16) == 0x25:  # ZigBee_48BitUint
        return struct.unpack("Q", struct.pack("Q", int(attribute_value, 16)))[0]

    if int(AttType, 16) == 0x28:  # int8
        return int(attribute_value, 16)

    if int(AttType, 16) == 0x29:  # 16Bitint   -> tested on Measurement clusters
        return struct.unpack("h", struct.pack("H", int(attribute_value[:4], 16)))[0]

    if int(AttType, 16) == 0x2A:  # ZigBee_24BitInt
        return struct.unpack("i", struct.pack("I", int("0" + attribute_value, 16)))[0]

    if int(AttType, 16) == 0x2B:  # 32Bitint
        return struct.unpack("i", struct.pack("I", int(attribute_value[:8], 16)))[0]

    if int(AttType, 16) == 0x2D:  # ZigBee_48Bitint
        return struct.unpack("q", struct.pack("Q", int(attribute_value, 16)))[0]

    if int(AttType, 16) == 0x30:  # 8BitEnum
        return int(attribute_value[:2], 16)

    if int(AttType, 16) == 0x31:  # 16BitEnum
        return struct.unpack("h", struct.pack("H", int(attribute_value[:4], 16)))[0]

    if int(AttType, 16) == 0x39:  # Xiaomi Float
        return struct.unpack("f", struct.pack("I", int(attribute_value, 16)))[0]

    if int(AttType, 16) in {0x42, 0x43}:  # CharacterString
        return _decode_caracter_string( attribute_value, handleErrors)
    return attribute_value


def _decode_caracter_string( attribute_value, handleErrors):
    decode = ""

    try:
        decode = binascii.unhexlify(attribute_value).decode("utf-8")
        
    except Exception as e:
        if handleErrors:  # If there is an error we force the result to '' This is used for 0x0000/0x0005
            decode = ""
        else:
            decode = binascii.unhexlify(attribute_value).decode("utf-8", errors="ignore")
            decode = decode.replace("\x00", "")
            decode = decode.strip()

    # Cleaning
    decode = decode.strip("\x00")
    decode = decode.strip()
    if decode is None:
        decode = ""
    return decode


# Used by Cluster 0x0000

def handle_model_name( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, device_model, rawvalue, value ):
    self.log.logging( "ZclClusters", "Debug", "_handle_model_name - %s / %s - %s %s %s %s %s - %s" % (
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, value, device_model), MsgSrcAddr, )
    
    modelName = _cleanup_model_name( MsgAttType, rawvalue)
    self.log.logging( "ZclClusters", "Debug", "_handle_model_name - modelName after cleanup %s" % modelName)
    
    modelName = _build_model_name( self, MsgSrcAddr, modelName)
    self.log.logging( "ZclClusters", "Debug", "_handle_model_name - modelName after build model name %s" % modelName)
    
    # Here the Device is not yet provisioned
    if "Model" not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["Model"] = {}

    self.log.logging( "ZclClusters", "Debug", "_handle_model_name - %s / %s - Recepion Model: >%s<" % (
        MsgClusterId, MsgAttrID, modelName), MsgSrcAddr, )
    if modelName == "":
        return

    if _is_device_already_provisionned( self, MsgSrcAddr, modelName):
        return

    if self.ListOfDevices[MsgSrcAddr]["Model"] == modelName and self.ListOfDevices[MsgSrcAddr]["Model"] in self.DeviceConf:
        # This looks like a Duplicate, just drop
        self.log.logging("ZclClusters", "Debug", "_handle_model_name - %s / %s - no action" % (
            MsgClusterId, MsgAttrID), MsgSrcAddr)
        return

    if self.ListOfDevices[MsgSrcAddr]["Model"] != modelName and self.ListOfDevices[MsgSrcAddr]["Model"] in self.DeviceConf:
        # We ae getting a different Model Name, let's log an drop
        self.log.logging( "ZclClusters", "Error", "_handle_model_name - %s / %s - no action as it is a different Model Name than registered %s" % (
            MsgClusterId, MsgAttrID, modelName), MsgSrcAddr, )
        return

    if self.ListOfDevices[MsgSrcAddr]["Model"] in ( "", {}):
        self.ListOfDevices[MsgSrcAddr]["Model"] = modelName
        
    elif self.ListOfDevices[MsgSrcAddr]["Model"] in self.DeviceConf:
        modelName = self.ListOfDevices[MsgSrcAddr]["Model"]
        
    elif modelName in self.DeviceConf:
        self.ListOfDevices[MsgSrcAddr]["Model"] = modelName

    if _update_data_structutre_based_on_model_name( self, MsgSrcAddr, modelName) and self.iaszonemgt:
        self.iaszonemgt.force_IAS_registration_if_needed(MsgSrcAddr)


def _update_data_structutre_based_on_model_name( self, MsgSrcAddr, modelName):
    # Let's see if this model is known in DeviceConf. If so then we will retreive already the Eps
    if self.ListOfDevices[MsgSrcAddr]["Model"] not in self.DeviceConf: 
        return False

    modelName = self.ListOfDevices[MsgSrcAddr]["Model"]
    self.log.logging("ZclClusters", "Debug", "_handle_model_name Extract all info from Model : %s" % self.DeviceConf[modelName], MsgSrcAddr)

    if "ConfigSource" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["ConfigSource"] == "DeviceConf":
        self.log.logging("ZclClusters", "Debug", "_handle_model_name Not redoing the DeviceConf enrollement", MsgSrcAddr)
        return True

    if "Param" in self.DeviceConf[modelName]:
        self.ListOfDevices[MsgSrcAddr]["Param"] = dict(self.DeviceConf[modelName]["Param"])

    _BackupEp = None
    if "Type" in self.DeviceConf[modelName]:  # If type exist at top level : copy it
        if "ConfigSource" not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]["ConfigSource"] = "DeviceConf"

        self.ListOfDevices[MsgSrcAddr]["Type"] = self.DeviceConf[modelName]["Type"]

        if "Ep" in self.ListOfDevices[MsgSrcAddr]:
            self.log.logging("ZclClusters", "Debug", "_handle_model_name Removing existing received Ep", MsgSrcAddr)
            _BackupEp = dict(self.ListOfDevices[MsgSrcAddr]["Ep"])
            del self.ListOfDevices[MsgSrcAddr]["Ep"]  # It has been prepopulated by some 0x8043 message, let's remove them.
            self.ListOfDevices[MsgSrcAddr]["Ep"] = {}  # It has been prepopulated by some 0x8043 message, let's remove them.
            self.log.logging("ZclClusters", "Debug", "-- Record removed 'Ep' %s" % (self.ListOfDevices[MsgSrcAddr]), MsgSrcAddr)
            
    _upd_data_strut_based_on_model(self, MsgSrcAddr, modelName, _BackupEp)


def _upd_data_strut_based_on_model(self, MsgSrcAddr, modelName, inital_ep):
    for Ep in self.DeviceConf[modelName]["Ep"]:  # For each Ep in DeviceConf.txt
        if Ep not in self.ListOfDevices[MsgSrcAddr]["Ep"]:  # If this EP doesn't exist in database
            self.ListOfDevices[MsgSrcAddr]["Ep"][Ep] = {}  # create it.
            self.log.logging( "ZclClusters", "Debug", "-- Create Endpoint %s in record %s" % (
                Ep, self.ListOfDevices[MsgSrcAddr]["Ep"]), MsgSrcAddr, )

        for cluster in self.DeviceConf[modelName]["Ep"][Ep]:  # For each cluster discribe in DeviceConf.txt
            if cluster in self.ListOfDevices[MsgSrcAddr]["Ep"][Ep]:
                # If this cluster doesn't exist in database
                continue

            self.log.logging("ZclClusters", "Debug", "----> Cluster: %s" % cluster, MsgSrcAddr)
            self.ListOfDevices[MsgSrcAddr]["Ep"][Ep][cluster] = {}  # create it.
            if inital_ep and Ep in inital_ep:
                # In case we had data, let's retreive it
                if cluster not in inital_ep[Ep]:
                    continue
                for attr in inital_ep[Ep][cluster]:
                    if attr in self.ListOfDevices[MsgSrcAddr]["Ep"][Ep][cluster]:
                        if self.ListOfDevices[MsgSrcAddr]["Ep"][Ep][cluster][ attr ] in ["", {}]:
                            self.ListOfDevices[MsgSrcAddr]["Ep"][Ep][cluster][attr] = inital_ep[Ep][cluster][attr]
                    else:
                        self.ListOfDevices[MsgSrcAddr]["Ep"][Ep][cluster][attr] = inital_ep[Ep][cluster][attr]

                    self.log.logging( "ZclClusters", "Debug", "------> Cluster %s set with Attribute %s" % (
                        cluster, attr), MsgSrcAddr, )

        if "Type" in self.DeviceConf[modelName]["Ep"][Ep]:  # If type exist at EP level : copy it
            self.ListOfDevices[MsgSrcAddr]["Ep"][Ep]["Type"] = self.DeviceConf[modelName]["Ep"][Ep]["Type"]
        if ( "ColorMode" in self.DeviceConf[modelName]["Ep"][Ep] and "ColorInfos" not in self.ListOfDevices[MsgSrcAddr] ):
            self.ListOfDevices[MsgSrcAddr]["ColorInfos"] = {}
        if "ColorMode" in self.DeviceConf[modelName]["Ep"][Ep]:
            self.ListOfDevices[MsgSrcAddr]["ColorInfos"]["ColorMode"] = int(self.DeviceConf[modelName]["Ep"][Ep]["ColorMode"])

    self.log.logging( "ZclClusters", "Debug", "_handle_model_name Result based on DeviceConf is: %s" % str(self.ListOfDevices[MsgSrcAddr]), MsgSrcAddr, )
    return True


def _build_model_name( self, nwkid, modelName):
    
    manufacturer_name = self.ListOfDevices[nwkid]["Manufacturer Name"] if "Manufacturer Name" in self.ListOfDevices[nwkid] else ""
    manuf_code = self.ListOfDevices[nwkid]["Manufacturer"] if "Manufacturer" in self.ListOfDevices[nwkid] else ""


    # Try to check if the Model name is in the DeviceConf list ( optimised devices)
    if modelName + '-' + manufacturer_name in self.DeviceConf:
        return modelName + '-' + manufacturer_name
        
    if modelName + manufacturer_name in self.DeviceConf:
        return modelName + manufacturer_name
    
    # If not found, let see if the model name can be extracted from the (ModelName, ManufacturerName) tuple set in the Conf file as Identifier
    plugin_identifier = plugin_self_identifier( self, modelName, manufacturer_name)
    if plugin_identifier:
        return plugin_identifier

    zdevice_id = self.ListOfDevices[nwkid]["ZDeviceID"] if "ZDeviceID" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["ZDeviceID"] else None

    return check_found_plugin_model( self, modelName, manufacturer_name=manufacturer_name, manufacturer_code=manuf_code, device_id=zdevice_id)


def _is_device_already_provisionned( self, nwkid, modelName):

    if "Ep" not in self.ListOfDevices[nwkid]:
        return False
    for iterEp in list(self.ListOfDevices[nwkid]["Ep"]):
        if "ClusterType" in list(self.ListOfDevices[nwkid]["Ep"][iterEp]):
            self.log.logging( "ZclClusters", "Debug", "_is_device_already_provisionned - %s / %s - %s is already provisioned in Domoticz" % (
                nwkid, iterEp, modelName), nwkid, )

            # However if Model is not correctly set, let's take the opportunity to correct
            if self.ListOfDevices[nwkid]["Model"] != modelName:
                self.log.logging( "ZclClusters", "Debug", "_is_device_already_provisionned - %s / %s - Update Model Name %s" % (
                    nwkid, iterEp, modelName), nwkid, )
                self.ListOfDevices[nwkid]["Model"] = modelName
            return True
    return False
     

def _cleanup_model_name( MsgAttType, value):
    # Stop at the first Null
    idx = 0
    for _ in value:
        if value[idx : idx + 2] == "00":
            break
        idx += 2
    AttrModelName = decoding_attribute_data( MsgAttType, value[:idx], handleErrors=True) 
    modelName = AttrModelName.replace("/", "")
    modelName = modelName.replace("  ", " ")
    return modelName


# Used by Cluster 0x0702
def compute_metering_conso(self, NwkId, MsgSrcEp, MsgClusterId, MsgAttrID, raw_value):
    # For Instant Power
    # Device Configuration PowerMeteringMultiplier can overwrite the Multiplier
    # Device Configuration PowerMeteringDivisor can overwrite the Divisor
    # For Summation 
    # Device Configuration SummationMeteringMultiplier can overwrite the Multiplier
    # Device Configuration SummationMeteringDivisor can overwrite the Divisor

    if isinstance(raw_value, str):
        raw_value = int(raw_value,16)

    # Get the Unit, to see if we have Kilo, so then multiply by 1000.
    unit = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "MeteringUnit")
    if unit is None:
        unit = ( self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId]["0300"] if ( MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] and "0300" in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] ) else "kW" )
    if unit == "kW":
        # Domoticz expect in Watts
        conso = raw_value * 1000
    elif unit == "Unitless":
        conso = raw_value
    else:
        # We assumed default as kW
        self.log.logging("ZclClusters", "Log", "compute_metering_conso - Unknown %s/%s assuming kW" %( 
            NwkId, MsgSrcEp ), NwkId)
        conso = raw_value * 1000
        
    multiplier = None
    divisor = None
    modelName = self.ListOfDevices[NwkId]["Model"] if "Model" in self.ListOfDevices[NwkId] else None
    # Check if we have a Device configuration overwrite
    if modelName and modelName not in ( '', {} ):
        if MsgAttrID == "0400":
            # Instant Power
            multiplier = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "PowerMeteringMultiplier")
            divisor = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "PowerMeteringDivisor")
        elif MsgAttrID == "0000":
            # Summation
            multiplier = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "SummationMeteringMultiplier")
            divisor = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], "SummationMeteringDivisor")

    if multiplier is None:
        # By default Multiplier is assumed to be 1
        multiplier = int( self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId]["0301"] if ( MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] and "0301" in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] ) else 1 )
    if divisor is None:
        # By default Multiplier is assumed to be 1
        divisor = int( self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId]["0302"] if ( MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] and "0302" in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] ) else 1 )
 
    conso = round( (( conso * multiplier ) / divisor ), 3)
    self.log.logging("ZclClusters", "Debug", "compute_metering_conso - %s/%s Unit: %s Multiplier: %s , Divisor: %s , raw: %s result: %s" % (
        NwkId, MsgSrcEp, unit, multiplier, divisor, raw_value, conso), NwkId)
    if ( 
        MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] 
        and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] 
        and ("0301" not in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] or "0302" not in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId]
             or "0300" not in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId])
    ):
        ReadAttributeRequest_0702_multiplier_divisor(self,NwkId )
    return conso


def compute_electrical_measurement_conso(self, NwkId, MsgSrcEp, MsgClusterId, MsgAttrID, raw_value):
    # ActivePowerDivisor 	
    # RMSVoltageDivisor
    # RMSCurrentDivisor
    self.log.logging("Cluster", "Debug", "compute_electrical_measurement_conso - %s/%s %s %s %s %s" % (
        NwkId, MsgSrcEp, MsgClusterId, MsgAttrID, raw_value, type(raw_value)), NwkId)

    MULTIPLIER_DIVISOR_MATRIX = {
        '0505': { 'multiplier': '0600', 'divisor': '0601', 'custom': 'RMSVoltageDivisor'},    # RMSVoltage
        '0508': { 'multiplier': '0602', 'divisor': '0603', 'custom': 'RMSCurrentDivisor'},    # RMSCurrent
        '050b': { 'multiplier': '0604', 'divisor': '0605', 'custom': 'ActivePowerDivisor'},   # ActivePower
    }
    if isinstance( raw_value, str):
        raw_value = int(raw_value,16)

    conso = raw_value
    multiplier = None
    divisor = None

    if MsgAttrID not in MULTIPLIER_DIVISOR_MATRIX:
        return
    
    # Check if we have a Custom divisor, we assumed multiplier = 1
    custom = MULTIPLIER_DIVISOR_MATRIX[ MsgAttrID ]['custom']
    divisor = get_deviceconf_parameter_value(self, self.ListOfDevices[NwkId]["Model"], custom)
    if divisor is not None:
        divisor = int(divisor )
        self.log.logging("ZclClusters", "Debug", "compute_electrical_measurement_conso - %s/%s Custom Divisor: %s , raw: %s result: %s" % (
            NwkId, MsgSrcEp, divisor, raw_value, conso), NwkId)
        return round( (( conso ) / divisor ), 3)
        
    multiplier_attribute = MULTIPLIER_DIVISOR_MATRIX[ MsgAttrID ]['multiplier']
    divisor_attribute = MULTIPLIER_DIVISOR_MATRIX[ MsgAttrID ]['divisor']
        
    # By default Multiplier is assumed to be 1
    multiplier = int( self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId][ multiplier_attribute ] if ( MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] and multiplier_attribute in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] ) else 1 )
    # By default Multiplier is assumed to be 1
    divisor = int( self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId][ divisor_attribute ] if ( MsgSrcEp in self.ListOfDevices[NwkId]["Ep"] and MsgClusterId in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp] and divisor_attribute in self.ListOfDevices[NwkId]["Ep"][MsgSrcEp][MsgClusterId] ) else 1 )
 
    conso = round( (( conso * multiplier ) / divisor ), 3)
    self.log.logging("ZclClusters", "Debug", "compute_electrical_measurement_conso - %s/%s Multiplier: %s , Divisor: %s , raw: %s result: %s" % (
        NwkId, MsgSrcEp, multiplier, divisor, raw_value, conso), NwkId)

    return conso
