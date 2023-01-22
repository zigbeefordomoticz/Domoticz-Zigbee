
import binascii
import json
import struct
from os import listdir
from os.path import isdir, isfile, join

from DevicesModules import FUNCTION_MODULE
from Modules.domoMaj import MajDomoDevice
from Modules.pluginModels import check_found_plugin_model
from Modules.tools import checkAndStoreAttributeValue, getAttributeValue

# "ActionList":
#   check_store_value - check the value and store in the corresponding data strcuture entry
#   upd_domo_device - trigger update request in domoticz
#   store_specif_attribute - Store the data value in self.ListOfDevices[ nwkid ][_storage_specificlvl1 ][_storage_specificlvl2][_storage_specificlvl3]

CHECK_AND_STORE = "check_store_value"
STORE_SPECIFIC_ATTRIBUTE = "store_specif_attribute"
BASIC_MODEL_NAME = "basic_model_name"
STORE_SPECIFIC_PLACE = "SpecifStoragelvl1"
STORE_SPECIFIC_PLACE = "SpecifStoragelvl2"
STORE_SPECIFIC_PLACE = "SpecifStoragelvl3"
UPDATE_DOMO_DEVICE = "upd_domo_device"

ACTIONS_TO_FUNCTIONS = {
    CHECK_AND_STORE: checkAndStoreAttributeValue,
    UPDATE_DOMO_DEVICE: MajDomoDevice
}

def process_cluster_attribute_response( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, ):
    

    self.log.logging("ZclClusters", "Debug", "Foundation Cluster - Nwkid: %s Ep: %s Cluster: %s Attribute: %s Data: %s Source: %s" %(
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData, Source))

    device_model = _get_model_name( self, MsgSrcAddr)
    _name = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "Name", model=device_model)
    _datatype = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "DataType", model=device_model)
    _ranges = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "Range", model=device_model )
    _special_values = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "SpecialValues", model=device_model)
    _eval_formula = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "EvalExp", model=device_model )
    _action_list = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ActionList", model=device_model )
    _storage_specificlvl1 = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "SpecifStoragelvl1", model=device_model )
    _storage_specificlvl2 = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "SpecifStoragelvl2", model=device_model )
    _storage_specificlvl3 = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "SpecifStoragelvl3", model=device_model )
    _eval_inputs = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "EvalExpCustomVariables", model=device_model)
    _function = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "EvalFunc", model=device_model)
    
    value = _decode_attribute_data( MsgAttType, MsgClusterData)
    
    if _datatype != MsgAttType:
        self.log.logging("ZclClusters", "Log", "process_cluster_attribute_response - %s/%s %s - %s DataType: %s miss-match with %s" %( 
            MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, _datatype ))
        
    _force_value = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ValueOverwrite", model=device_model)
    if _force_value is not None:
        value = _force_value
        
    if _special_values is not None:
        check_special_values( self, value, MsgAttType, _special_values )
        
    if _ranges is not None:
        checking_ranges = _check_range( self, value, MsgAttType, _ranges, )
        if checking_ranges is not None and not checking_ranges:
            self.log.logging("ZclClusters", "Error", " . value out of ranges : %s -> %s" %( value, str(_ranges) ))
            
    if _eval_formula is not None:
        value = compute_attribute_value( self, MsgSrcAddr, MsgSrcEp, value, _eval_inputs, _eval_formula, _function)

    formated_logging( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, device_model, _name, _datatype, _ranges, _special_values, _eval_formula, _action_list, _eval_inputs, _force_value, value)
    if value is None:
        return
    
    if _action_list is None:
        self.log.logging("ZclClusters", "Debug", "---> No Action")
        return
    
    for data_action in _action_list:
        if data_action == CHECK_AND_STORE:
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

        elif data_action == UPDATE_DOMO_DEVICE and majdomodevice_possiblevalues( self, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value ):
            action_majdomodevice( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value )
            
        elif data_action == STORE_SPECIFIC_ATTRIBUTE:
            store_value_in_specif_storage( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value, _storage_specificlvl1, _storage_specificlvl2, _storage_specificlvl3)
            
        elif data_action == BASIC_MODEL_NAME:
            _handle_model_name( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, device_model, MsgClusterData, value )
            

def _read_zcl_cluster( self, cluster_filename ):
    with open(cluster_filename, "rt") as handle:
        try:
            return json.load(handle)
        except ValueError as e:
            self.log.logging("ZclClusters", "Error", "--> JSON readZclClusters: %s load failed with error: %s" % (cluster_filename, str(e)))
            return None
            
        except Exception as e:
            self.log.logging("ZclClusters", "Error", "--> JSON readZclClusters: %s load general error: %s" % (cluster_filename, str(e)))
            return None
    return None

def _decode_attribute_data( AttType, attribute_value, handleErrors=False):

    if len(attribute_value) == 0:
        return ""

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

def _check_range( self, value, datatype, _range):
    self.log.logging("ZclClusters", "Debug", " . _check_range %s %s %s" %(value, datatype, _range))
    
    if len(_range) != 2:
        self.log.logging("ZclClusters", "Error", " . Incorrect range %s" %str(_range))
        return None
    
    _range1 = _decode_attribute_data( datatype, _range[0])
    _range2 = _decode_attribute_data( datatype, _range[1])
    
    self.log.logging("ZclClusters", "Debug", " . _check_range range1: %s" %(_range1))
    self.log.logging("ZclClusters", "Debug", " . _check_range range2: %s" %(_range2))
    
    if _range1 < _range2:
        return _range1 <= value <= _range2
    
    if _range1 > _range2:
        return _range1 >= value >= _range2

def _get_model_name( self, nwkid):

    if "Model" in self.ListOfDevices[ nwkid ] and self.ListOfDevices[ nwkid ]["Model"] not in ( '', {}):
        return self.ListOfDevices[ nwkid ]["Model"]
    return None

def _cluster_zcl_attribute_retreival( self, cluster, attribute, parameter ):

    self.log.logging("ZclClusters", "Debug", " . _cluster_zcl_attribute_retreival %s %s %s" %( cluster, attribute, parameter))

    if (
        attribute in self.readZclClusters[ cluster ]["Attributes"] 
        and parameter in self.readZclClusters[ cluster ]["Attributes"][ attribute ]
    ):

        self.log.logging("ZclClusters", "Debug", " . %s %s %s --> %s" %(
            cluster, attribute, parameter, self.readZclClusters[ cluster ]["Attributes"][ attribute ][ parameter ])
        ) 
        return self.readZclClusters[ cluster ]["Attributes"][ attribute ][ parameter ]
    return None

def _cluster_specific_attribute_retreival( self, model, ep, cluster, attribute, parameter ):

    self.log.logging("ZclClusters", "Debug", " . _cluster_specific_attribute_retreival %s %s %s %s %s" %( model, ep, cluster, attribute, parameter))

    if (
        attribute in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"] 
        and parameter in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ]
    ):

        self.log.logging("ZclClusters", "Debug", " . %s %s %s --> %s" %(

            cluster, attribute, parameter, self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ][ parameter ])
        ) 

        return self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ][ parameter ]
    return None

def _update_eval_formula( self, formula, input_variable, variable_name):

    self.log.logging("ZclClusters", "Debug", " . _update_eval_formula( %s, %s, %s" %( formula, input_variable, variable_name))

    return formula.replace( input_variable, variable_name )


def _handle_model_name( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, device_model, rawvalue, value ):
    self.log.logging( "ZclClusters", "Debug", "_handle_model_name - %s / %s - %s %s %s %s %s - %s" % (
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, value, device_model), MsgSrcAddr, )
    
    modelName = _cleanup_model_name( self, MsgAttType, rawvalue)
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
     
    
    
def _cleanup_model_name( self, MsgAttType, value):
    # Stop at the first Null
    self.log.logging( "ZclClusters", "Error", "_cleanup_model_name - %s %s" % (MsgAttType, value),)
    
    idx = 0
    for _ in value:
        if value[idx : idx + 2] == "00":
            break
        idx += 2
    self.log.logging( "ZclClusters", "Error", "      [1] -  %s" % ( value[:idx]),)
    
    AttrModelName = _decode_attribute_data( MsgAttType, value[:idx], handleErrors=True) 
    self.log.logging( "ZclClusters", "Error", "      [2] -  %s" % ( AttrModelName),)
    modelName = AttrModelName.replace("/", "")
    self.log.logging( "ZclClusters", "Error", "      [3] -  %s" % ( modelName),)
    modelName = modelName.replace("  ", " ")
    self.log.logging( "ZclClusters", "Error", "      [4] -  %s" % ( modelName),)
    return modelName
   
    
def load_zcl_cluster(self):
    zcl_cluster_path = self.pluginconf.pluginConf["pluginConfig"] + "ZclDefinitions"
    if not isdir(zcl_cluster_path):
        return

    self.log.logging("ZclClusters", "Status", "Loading ZCL Cluster definitions")

    zcl_cluster_definition = [f for f in listdir(zcl_cluster_path) if isfile(join(zcl_cluster_path, f))]
    for cluster_definition in sorted(zcl_cluster_definition):
        cluster_filename = str(zcl_cluster_path + "/" + cluster_definition)
        cluster_definition = _read_zcl_cluster( self, cluster_filename )

        if (
            cluster_definition is None
            or "ClusterId" not in cluster_definition
            or "Enabled" not in cluster_definition or not cluster_definition["Enabled"]
            or cluster_definition[ "ClusterId"] in self.readZclClusters
            or "Description" not in cluster_definition
        ):
            continue
        
        self.readZclClusters[ cluster_definition[ "ClusterId"] ] = {
            "Description": cluster_definition[ "Description" ],
            "Version": cluster_definition[ "Version" ],
            "Attributes": dict( cluster_definition[ "Attributes" ] )
        }

        self.log.logging("ZclClusters", "Status", " - ZCL Cluster %s - (V%s) %s loaded" %( 
            cluster_definition[ "ClusterId"], cluster_definition[ "Version" ], cluster_definition["Description"],))

def is_cluster_specific_config(self, model, ep, cluster, attribute=None):
    if model not in self.DeviceConf:
        return False
    if 'Ep' not in self.DeviceConf[ model ]:
        return False
    if ep not in self.DeviceConf[ model ]['Ep']:
        return False
    if cluster not in self.DeviceConf[ model ]['Ep'][ ep ]:
        return False
    if self.DeviceConf[ model ]['Ep'][ ep ][ cluster ] in ( '', {} ):
        return False
    if "Attributes" not in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]:
        return False
    if attribute not in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"]:
        return False

    self.log.logging("ZclClusters", "Debug", "is_cluster_specific_config %s/%s and definition %s" %( 
        cluster, attribute, self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ] ))

    return True
    
def is_cluster_zcl_config_available( self, cluster, attribute=None):
    if cluster not in self.readZclClusters:
        return False
    if (
        attribute is None 
        or attribute not in self.readZclClusters[ cluster ]["Attributes"] 
        or "Enabled" not in self.readZclClusters[ cluster ]["Attributes"][ attribute ]
        or not self.readZclClusters[ cluster ]["Attributes"][ attribute ]["Enabled"]
    ):
        return False

    self.log.logging("ZclClusters", "Debug", "is_cluster_zcl_config_available %s/%s and definition %s" %( 
        cluster, attribute, self.readZclClusters[ cluster ]["Attributes"][ attribute ] ))
    
    return True

def cluster_attribute_retreival(self, ep, cluster, attribute, parameter, model=None):
    if model and is_cluster_specific_config(self, model, ep, cluster, attribute=attribute):
        return _cluster_specific_attribute_retreival( self, model, ep, cluster, attribute, parameter )
    return _cluster_zcl_attribute_retreival( self, cluster, attribute, parameter )
    
def action_majdomodevice( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value ):
    self.log.logging( "ZclClusters", "Debug", "action_majdomodevice - %s/%s %s %s %s %s" %(
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value ))    
    _majdomo_formater = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "DomoDeviceFormat", model=device_model)
    self.log.logging( "ZclClusters", "Debug", "     _majdomo_formater: %s" %_majdomo_formater)
    
    majValue = value
    if _majdomo_formater and _majdomo_formater == "str":
        majValue = str( value )
    
    _majdomo_cluster = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "UpdDomoDeviceWithCluster", model=device_model)
    self.log.logging( "ZclClusters", "Debug", "     _majdomo_cluster: %s" %_majdomo_cluster)
    
    majCluster = _majdomo_cluster if _majdomo_cluster is not None else MsgClusterId

    _majdomo_attribute = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "UpdDomoDeviceWithAttibute", model=device_model)
    self.log.logging( "ZclClusters", "Debug", "     _majdomo_attribute: %s" %_majdomo_attribute)
    
    majAttribute = _majdomo_attribute if _majdomo_attribute is not None else ""
    
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, majCluster, majValue, Attribute_=majAttribute)
    
def majdomodevice_possiblevalues( self, MsgSrcEp, MsgClusterId, MsgAttrID, model, value):

    _majdomodeviceValidValues = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ValidValuesDomoDevices", model=model)
    if _majdomodeviceValidValues is None:
        return True
    eval_result = eval( _majdomodeviceValidValues )

    self.log.logging("ZclClusters", "Debug", " . majdomodevice_possiblevalues: %s -> %s" %( eval_result, _majdomodeviceValidValues))
    return eval_result

def check_special_values( self, value, data_type, _special_values ):
    flag = False
    for x in _special_values:
        if value == _decode_attribute_data( data_type, x):
            self.log.logging("ZclClusters", "Debug", " . found %s as %s" %( value, _special_values[ x ] ))
            flag = True
    return flag
    
def compute_attribute_value( self, nwkid, ep, value, _eval_inputs, _eval_formula, _function):

    self.log.logging("ZclClusters", "Debug", "compute_attribute_value - _function: %s FUNCTION_MODULE: %s" %( _function, str(FUNCTION_MODULE) ))

    if _function and _function in dict(FUNCTION_MODULE):
        return FUNCTION_MODULE[ _function ]
        
    evaluation_result = value
    custom_variable = {}
    if _eval_inputs is not None:
        for idx, x in enumerate(_eval_inputs):
            if "Cluster" in _eval_inputs[x] and "Attribute" in _eval_inputs[x]:
                cluster = _eval_inputs[x][ "ClusterId" ]
                attribute = _eval_inputs[x][ "AttributeId" ]
                custom_value = getAttributeValue(self, nwkid, ep, cluster, attribute)

                self.log.logging("ZclClusters", "Debug", " . %s/%s = %s" %( cluster, attribute, custom_value ))
                if custom_value is None:
                    self.log.logging("ZclClusters", "Error", "process_cluster_attribute_response - unable to found Input variable: %s Cluster: %s Attribute: %s" %(
                        x, cluster, attribute))
                    continue
                custom_variable[ idx ] = custom_value
                _eval_formula = _update_eval_formula( self, _eval_formula, x, "custom_variable[ %s ]" % idx)
                self.log.logging("ZclClusters", "Debug", " . Updated formula: %s" %_eval_formula)

        for x in custom_variable:
            self.log.logging("ZclClusters", "Debug", " . custom_variable[ %s ] = %s" %( idx, custom_variable[ idx ]))
        
    if _eval_formula is not None and _eval_formula != "":
        evaluation_result = eval( _eval_formula )
    self.log.logging("ZclClusters", "Debug", " . after evaluation value: %s -> %s" %( value, evaluation_result))
    return evaluation_result

def store_value_in_specif_storage( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value, _storage_specificlvl1, _storage_specificlvl2, _storage_specificlvl3):
    
    self.log.logging( "ZclClusters", "Debug", "store_value_in_specif_storage - %s/%s %s %s %s %s" %(
        MsgSrcAddr, MsgSrcEp, _storage_specificlvl1, _storage_specificlvl2, _storage_specificlvl3, value))
    if _storage_specificlvl1 is None:
        return
    if _storage_specificlvl1 not in self.ListOfDevices[ MsgSrcAddr ]:
        self.ListOfDevices[ MsgSrcAddr ][ _storage_specificlvl1 ] = {}
    if _storage_specificlvl2 is None:
        self.ListOfDevices[ MsgSrcAddr ][ _storage_specificlvl1 ] = value
        return
    if _storage_specificlvl2 not in self.ListOfDevices[ MsgSrcAddr ][ _storage_specificlvl1 ]:
        self.ListOfDevices[ MsgSrcAddr ][ _storage_specificlvl1 ][ _storage_specificlvl2 ] = {}
    if _storage_specificlvl3 is None:
        self.ListOfDevices[ MsgSrcAddr ][ _storage_specificlvl1 ][ _storage_specificlvl2 ] = value
        return
    if _storage_specificlvl3 not in self.ListOfDevices[ MsgSrcAddr ][ _storage_specificlvl1 ][ _storage_specificlvl2 ]:
        self.ListOfDevices[ MsgSrcAddr ][ _storage_specificlvl1 ][ _storage_specificlvl2 ][ _storage_specificlvl3 ] = {}    
    self.ListOfDevices[ MsgSrcAddr ][ _storage_specificlvl1 ][ _storage_specificlvl2 ][ _storage_specificlvl3 ] = value
    
def formated_logging( self, nwkid, ep, cluster, attribute, dt, dz, d, Source, device_model, attr_name, exp_dt, _ranges, _special_values, eval_formula, action_list, eval_inputs, force_value, value):

    if not self.pluginconf.pluginConf["trackZclClusters"]:
        return
    cluster_description = self.readZclClusters[ cluster ]["Description"]
    self.log.logging( "ZclClusters", "Log", "Attribute Report | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s" %(
        nwkid, ep, cluster, cluster_description, attribute, attr_name, dt, dz, device_model, eval_formula, eval_inputs, action_list, force_value, value ))        