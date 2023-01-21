
import binascii
import json
import struct
from os import listdir
from os.path import isdir, isfile, join

from Modules.domoMaj import MajDomoDevice
from Modules.tools import checkAndStoreAttributeValue, getAttributeValue

from DevicesModules import FUNCTION_MODULE

CHECK_AND_STORE = "check_store_value"
UPDATE_DOMO_DEVICE = "upd_domo_device"

ACTIONS_TO_FUNCTIONS = {
    CHECK_AND_STORE: checkAndStoreAttributeValue,
    UPDATE_DOMO_DEVICE: MajDomoDevice
}

def _read_zcl_cluster( self, cluster_filename ):
    with open(cluster_filename, "rt") as handle:
        try:
            return json.load(handle)
        except ValueError as e:
            self.log.logging("readZclClusters", "Error", "--> JSON readZclClusters: %s load failed with error: %s" % (cluster_filename, str(e)))

            return None
        except Exception as e:
            self.log.logging("readZclClusters", "Error", "--> JSON readZclClusters: %s load general error: %s" % (cluster_filename, str(e)))
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
        return _decode_caracter_string(attribute_value, handleErrors)
    return attribute_value

def _decode_caracter_string(attribute_value, handleErrors):
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
    self.log.logging("readZclClusters", "Debug", " . _check_range %s %s %s" %(value, datatype, _range))
    
    if len(_range) != 2:
        self.log.logging("readZclClusters", "Error", " . Incorrect range %s" %str(_range))
        return None
    
    _range1 = _decode_attribute_data( datatype, _range[0])
    _range2 = _decode_attribute_data( datatype, _range[1])
    
    self.log.logging("readZclClusters", "Debug", " . _check_range range1: %s" %(_range1))
    self.log.logging("readZclClusters", "Debug", " . _check_range range2: %s" %(_range2))
    
    if _range1 < _range2:
        return _range1 <= value <= _range2
    
    if _range1 > _range2:
        return _range1 >= value >= _range2

def _get_model_name( self, nwkid):

    if "Model" in self.ListOfDevices[ nwkid ] and self.ListOfDevices[ nwkid ]["Model"] not in ( '', {}):
        return self.ListOfDevices[ nwkid ]["Model"]
    return None

def _cluster_zcl_attribute_retreival( self, cluster, attribute, parameter ):
    self.log.logging("readZclClusters", "Debug", " . _cluster_zcl_attribute_retreival %s %s %s" %( cluster, attribute, parameter))
    if (
        attribute in self.readZclClusters[ cluster ]["Attributes"] 
        and parameter in self.readZclClusters[ cluster ]["Attributes"][ attribute ]
    ):
        self.log.logging("readZclClusters", "Debug", " . %s %s %s --> %s" %(
            cluster, attribute, parameter, self.readZclClusters[ cluster ]["Attributes"][ attribute ][ parameter ])
        ) 
        return self.readZclClusters[ cluster ]["Attributes"][ attribute ][ parameter ]
    return None

def _cluster_specific_attribute_retreival( self, model, ep, cluster, attribute, parameter ):
    self.log.logging("readZclClusters", "Debug", " . _cluster_specific_attribute_retreival %s %s %s %s %s" %( model, ep, cluster, attribute, parameter))
    if (
        attribute in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"] 
        and parameter in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ]
    ):
        self.log.logging("readZclClusters", "Debug", " . %s %s %s --> %s" %(
            cluster, attribute, parameter, self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ][ parameter ])
        ) 

        return self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ][ parameter ]
    return None

def _update_eval_formula( self, formula, input_variable, variable_name):
    self.log.logging("readZclClusters", "Debug", " . _update_eval_formula( %s, %s, %s" %( formula, input_variable, variable_name))
    return formula.replace( input_variable, variable_name )



def load_zcl_cluster(self):
    zcl_cluster_path = self.pluginconf.pluginConf["pluginConfig"] + "ZclDefinitions"
    if not isdir(zcl_cluster_path):
        return

    self.log.logging("readZclClusters", "Status", "Loading ZCL Cluster definitions")
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
        self.log.logging("readZclClusters", "Status", " - ZCL Cluster %s - %s (v%s) loaded" %( 
            cluster_definition[ "ClusterId"], cluster_definition["Description"], cluster_definition[ "Version" ],))

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
    self.log.logging("readZclClusters", "Debug", "is_cluster_specific_config %s/%s and definition %s" %( 
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
    self.log.logging("readZclClusters", "Debug", "is_cluster_zcl_config_available %s/%s and definition %s" %( 
        cluster, attribute, self.readZclClusters[ cluster ]["Attributes"][ attribute ] ))
    
    return True

def cluster_attribute_retreival(self, ep, cluster, attribute, parameter, model=None):
    if model and is_cluster_specific_config(self, model, ep, cluster, attribute=attribute):
        return _cluster_specific_attribute_retreival( self, model, ep, cluster, attribute, parameter )
    return _cluster_zcl_attribute_retreival( self, cluster, attribute, parameter )

def process_cluster_attribute_response( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, ):
    
    self.log.logging("readZclClusters", "Debug", "Foundation Cluster - Nwkid: %s Ep: %s Cluster: %s Attribute: %s Data: %s Source: %s" %(
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData, Source))

    device_model = _get_model_name( self, MsgSrcAddr)
    _name = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "Name", model=device_model)
    _datatype = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "DataType", model=device_model)
    _ranges = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "Range", model=device_model )
    _special_values = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "SpecialValues", model=device_model)
    _eval_formula = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "EvalExp", model=device_model )
    _action_list = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ActionList", model=device_model )
    _eval_inputs = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "EvalExpCustomVariables", model=device_model)
    _function = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "EvalFunc", model=device_model)
    
    value = _decode_attribute_data( MsgAttType, MsgClusterData)
    
    if _datatype != MsgAttType:
        self.log.logging("readZclClusters", "Error", "process_cluster_attribute_response - %s/%s %s - %s DataType: %s miss-match with %s" %( 
            MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, _datatype ))
        
    _force_value = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ValueOverwrite", model=device_model)
    if _force_value is not None:
        value = _force_value
        
    if _special_values is not None:
        check_special_values( self, value, MsgAttType, _special_values )
        
    if _ranges is not None:
        checking_ranges = _check_range( self, value, MsgAttType, _ranges, )
        if checking_ranges is not None and not checking_ranges:
            self.log.logging("readZclClusters", "Error", " . value out of ranges : %s -> %s" %( value, str(_ranges) ))
            
    if _eval_formula is not None:
        value = compute_attribute_value( self, MsgSrcAddr, MsgSrcEp, value, _eval_inputs, _eval_formula, _function)

    formated_logging( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, device_model, _name, _datatype, _ranges, _special_values, _eval_formula, _action_list, _eval_inputs, _force_value, value)
    if value is None:
        return
    
    if _action_list is None:
        self.log.logging("readZclClusters", "Debug", "---> No Action")
        return
    
    for data_action in _action_list:
        if data_action == CHECK_AND_STORE:
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

        elif data_action == UPDATE_DOMO_DEVICE and majdomodevice_possiblevalues( self, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value ):
            action_majdomodevice( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value )
            
def action_majdomodevice( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value ):
    self.log.logging( "readZclClusters", "Debug", "action_majdomodevice - %s/%s %s %s %s %s" %(
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, device_model, value ))    
    _majdomo_formater = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "DomoDeviceFormat", model=device_model)
    self.log.logging( "readZclClusters", "Debug", "     _majdomo_formater: %s" %_majdomo_formater)
    
    majValue = value
    if _majdomo_formater and _majdomo_formater == "str":
        majValue = str( value )
    
    _majdomo_cluster = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "UpdDomoDeviceWithCluster", model=device_model)
    self.log.logging( "readZclClusters", "Debug", "     _majdomo_cluster: %s" %_majdomo_cluster)
    
    majCluster = _majdomo_cluster if _majdomo_cluster is not None else MsgClusterId

    _majdomo_attribute = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "UpdDomoDeviceWithAttibute", model=device_model)
    self.log.logging( "readZclClusters", "Debug", "     _majdomo_attribute: %s" %_majdomo_attribute)
    
    majAttribute = _majdomo_attribute if _majdomo_attribute is not None else ""
    
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, majCluster, majValue, Attribute_=majAttribute)
    

def majdomodevice_possiblevalues( self, MsgSrcEp, MsgClusterId, MsgAttrID, model, value):

    _majdomodeviceValidValues = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "ValidValuesDomoDevices", model=model)
    if _majdomodeviceValidValues is None:
        return True
    eval_result = eval( _majdomodeviceValidValues )
    self.log.logging("readZclClusters", "Debug", " . majdomodevice_possiblevalues: %s -> %s" %( eval_result, _majdomodeviceValidValues))
    return eval_result

def check_special_values( self, value, data_type, _special_values ):
    flag = False
    for x in _special_values:
        if value == _decode_attribute_data( data_type, x):
            self.log.logging("readZclClusters", "Log", " . found %s as %s" %( value, _special_values[ x ] ))
            flag = True
    return flag
        
        
def compute_attribute_value( self, nwkid, ep, value, _eval_inputs, _eval_formula, _function):

    self.log.logging("readZclClusters", "Log", "compute_attribute_value - _function: %s FUNCTION_MODULE: %s" %( _function, str(FUNCTION_MODULE) ))
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
                self.log.logging("readZclClusters", "Debug", " . %s/%s = %s" %( cluster, attribute, custom_value ))
                if custom_value is None:
                    self.log.logging("readZclClusters", "Error", "process_cluster_attribute_response - unable to found Input variable: %s Cluster: %s Attribute: %s" %(
                        x, cluster, attribute))
                    continue
                custom_variable[ idx ] = custom_value
                _eval_formula = _update_eval_formula( self, _eval_formula, x, "custom_variable[ %s ]" % idx)
                self.log.logging("readZclClusters", "Debug", " . Updated formula: %s" %_eval_formula)

        for x in custom_variable:
            self.log.logging("readZclClusters", "Debug", " . custom_variable[ %s ] = %s" %( idx, custom_variable[ idx ]))
        
    if _eval_formula is not None and _eval_formula != "":
        evaluation_result = eval( _eval_formula )
    self.log.logging("readZclClusters", "Debug", " . after evaluation value: %s -> %s" %( value, evaluation_result))
    return evaluation_result


def formated_logging( self, nwkid, ep, cluster, attribute, dt, dz, d, Source, device_model, attr_name, exp_dt, _ranges, _special_values, eval_formula, action_list, eval_inputs, force_value, value):

    cluster_description = self.readZclClusters[ cluster ]["Description"]
    self.log.logging( "readZclClusters", "Log", "Attribute Report | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s" %(
        nwkid, ep, cluster, cluster_description, attribute, attr_name, dt, dz, device_model, eval_formula, eval_inputs, action_list, force_value, value ))        