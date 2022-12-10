
import binascii
import json
import struct
from os import listdir
from os.path import isdir, isfile, join

from Modules.domoMaj import MajDomoDevice
from Modules.tools import checkAndStoreAttributeValue, getAttributeValue

ACTIONS_TO_FUNCTIONS = {
    "checkstore": checkAndStoreAttributeValue,
    "majdomodevice": MajDomoDevice
}

def _read_foundation_cluster( self, cluster_filename ):
    with open(cluster_filename, "rt") as handle:
        try:
            return json.load(handle)
        except ValueError as e:
            self.log.logging("FoundationCluster", "Error", "--> JSON FoundationCluster: %s load failed with error: %s" % (cluster_filename, str(e)))

            return None
        except Exception as e:
            self.log.logging("FoundationCluster", "Error", "--> JSON FoundationCluster: %s load general error: %s" % (cluster_filename, str(e)))
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
    self.log.logging("FoundationCluster", "Debug", " . _check_range %s %s %s" %(value, datatype, _range))
    
    if len(_range) != 2:
        self.log.logging("FoundationCluster", "Error", " . Incorrect range %s" %str(_range))
        return None
    
    _range1 = _decode_attribute_data( datatype, _range[0])
    _range2 = _decode_attribute_data( datatype, _range[1])
    
    self.log.logging("FoundationCluster", "Debug", " . _check_range range1: %s" %(_range1))
    self.log.logging("FoundationCluster", "Debug", " . _check_range range2: %s" %(_range2))
    
    if _range1 < _range2:
        return _range1 <= value <= _range2
    
    if _range1 > _range2:
        return _range1 >= value >= _range2

def _get_model_name( self, nwkid):

    if "Model" in self.ListOfDevices[ nwkid ] and self.ListOfDevices[ nwkid ]["Model"] not in ( '', {}):
        return self.ListOfDevices[ nwkid ]["Model"]
    return None

def _cluster_foundation_attribute_retreival( self, cluster, attribute, parameter ):
    self.log.logging("FoundationCluster", "Debug", " . _cluster_foundation_attribute_retreival %s %s %s" %( cluster, attribute, parameter))
    if (
        attribute in self.FoundationClusters[ cluster ]["Attributes"] 
        and parameter in self.FoundationClusters[ cluster ]["Attributes"][ attribute ]
    ):
        return self.FoundationClusters[ cluster ]["Attributes"][ attribute ][ parameter ]
    return None

def _cluster_specific_attribute_retreival( self, model, ep, cluster, attribute, parameter ):
    self.log.logging("FoundationCluster", "Debug", " . _cluster_specific_attribute_retreival %s %s %s %s %s" %( model, ep, cluster, attribute, parameter))
    if (
        attribute in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"] 
        and parameter in self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ]
    ):
        return self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ][ parameter ]
    return None

def _update_eval_formula( self, formula, input_variable, variable_name):
    self.log.logging("FoundationCluster", "Debug", " . _update_eval_formula( %s, %s, %s" %( formula, input_variable, variable_name))
    return formula.replace( input_variable, variable_name )

# methods used outside

def load_foundation_cluster(self):
    foundation_cluster_path = self.pluginconf.pluginConf["pluginConfig"] + "Foundation"
    if not isdir(foundation_cluster_path):
        return

    foundation_cluster_definition = [f for f in listdir(foundation_cluster_path) if isfile(join(foundation_cluster_path, f))]
    for cluster_definition in sorted(foundation_cluster_definition):
        cluster_filename = str(foundation_cluster_path + "/" + cluster_definition)
        cluster_definition = _read_foundation_cluster( self, cluster_filename )

        if (
            cluster_definition is None
            or "ClusterId" not in cluster_definition
            or "Enabled" not in cluster_definition or not cluster_definition["Enabled"]
            or cluster_definition[ "ClusterId"] in self.FoundationClusters
            or "Description" not in cluster_definition
        ):
            continue
        
        self.FoundationClusters[ cluster_definition[ "ClusterId"] ] = {
            "Version": cluster_definition[ "Version" ],
            "Attributes": dict( cluster_definition[ "Attributes" ] )
        }
        self.log.logging("FoundationCluster", "Status", " - Foundation Cluster %s - %s version %s loaded" %( 
            cluster_definition[ "ClusterId"], cluster_definition["Description"], cluster_definition[ "Version" ],))
    self.log.logging("FoundationCluster", "Debug", "--> Foundation Clusters loaded: %s" % self.FoundationClusters.keys())

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
    self.log.logging("FoundationCluster", "Debug", "is_cluster_specific_config %s/%s and definition %s" %( 
        cluster, attribute, self.DeviceConf[ model ]['Ep'][ ep ][ cluster ]["Attributes"][ attribute ] ))

    return True
    
def is_cluster_foundation_config_available( self, cluster, attribute=None):
    if cluster not in self.FoundationClusters:
        return False
    if (
        attribute is None 
        or attribute not in self.FoundationClusters[ cluster ]["Attributes"] 
        or "Enabled" not in self.FoundationClusters[ cluster ]["Attributes"][ attribute ]
        or not self.FoundationClusters[ cluster ]["Attributes"][ attribute ]["Enabled"]
    ):
        return False
    self.log.logging("FoundationCluster", "Debug", "is_cluster_foundation_config_available %s/%s and definition %s" %( 
        cluster, attribute, self.FoundationClusters[ cluster ]["Attributes"][ attribute ] ))
    
    return True

def cluster_attribute_retreival(self, ep, cluster, attribute, parameter, model=None):
    if model and is_cluster_specific_config(self, model, ep, cluster, attribute=attribute):
        return _cluster_specific_attribute_retreival( self, model, ep, cluster, attribute, parameter )
    return _cluster_foundation_attribute_retreival( self, cluster, attribute, parameter )

def process_cluster_attribute_response( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, ):
    
    self.log.logging("FoundationCluster", "Debug", "Foundation Cluster - Nwkid: %s Ep: %s Cluster: %s Attribute: %s Data: %s Source: %s" %(
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData, Source))

    device_model = _get_model_name( self, MsgSrcAddr)
    _name = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "Name", model=device_model)
    _datatype = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "DataType", model=device_model)
    _ranges = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "Range", model=device_model )
    _special_values = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "SpecialValues", model=device_model)
    _eval_formula = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "eval", model=device_model )
    _action_list = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "action", model=device_model )
    _eval_inputs = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "evalInputs", model=device_model)
    _force_value = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "overwrite", model=device_model)
    _majdomo_formater = cluster_attribute_retreival( self, MsgSrcEp, MsgClusterId, MsgAttrID, "majdomoformat", model=device_model)
    value = _decode_attribute_data( _datatype, MsgClusterData)
    
    if _force_value is not None:
        value = _force_value
        
    if _special_values is not None:
        check_special_values( self, value, _datatype, _special_values )
        
    if _ranges is not None:
        checking_ranges = _check_range( self, value, _datatype, _ranges, )
        if checking_ranges is not None and not checking_ranges:
            self.log.logging("FoundationCluster", "Error", " . value out of ranges : %s -> %s" %( value, str(_ranges) ))
            
    if _eval_formula is not None:
        value = compute_attribute_value( self, MsgSrcAddr, MsgSrcEp, value, _eval_inputs, _eval_formula)

    formated_logging( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, device_model, _name, _datatype, _ranges, _special_values, _eval_formula, _action_list, _eval_inputs, _force_value, value)
    
    for data_action in _action_list:
        if data_action == "checkstore":
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

        elif data_action == "majdomodevice":
            if _majdomo_formater and _majdomo_formater == "str":
                majValue = str( value )
            else:
                majValue = value
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, majValue )


def check_special_values( self, value, data_type, _special_values ):
    flag = False
    for x in _special_values:
        if value == _decode_attribute_data( data_type, x):
            self.log.logging("FoundationCluster", "Log", " . found %s as %s" %( value, _special_values[ x ] ))
            flag = True
    return flag
        
        
def compute_attribute_value( self, nwkid, ep, value, _eval_inputs, _eval_formula):

    evaluation_result = value
    custom_variable = {}
    if _eval_inputs is not None:
        for idx, x in enumerate(_eval_inputs):
            if "Cluster" in _eval_inputs[x] and "Attribute" in _eval_inputs[x]:
                cluster = _eval_inputs[x][ "Cluster" ]
                attribute = _eval_inputs[x][ "Attribute" ]
                custom_value = getAttributeValue(self, nwkid, ep, cluster, attribute)
                self.log.logging("FoundationCluster", "Debug", " . %s/%s = %s" %( cluster, attribute, custom_value ))
                if custom_value is None:
                    self.log.logging("FoundationCluster", "Error", "process_cluster_attribute_response - unable to found Input variable: %s Cluster: %s Attribute: %s" %(
                        x, cluster, attribute))
                    continue
                custom_variable[ idx ] = custom_value
                _eval_formula = _update_eval_formula( self, _eval_formula, x, "custom_variable[ %s ]" % idx)
                self.log.logging("FoundationCluster", "Debug", " . Updated formula: %s" %_eval_formula)

        for x in custom_variable:
            self.log.logging("FoundationCluster", "Debug", " . custom_variable[ %s ] = %s" %( idx, custom_variable[ idx ]))
        
    if _eval_formula is not None and _eval_formula != "":
        evaluation_result = eval( _eval_formula )
    self.log.logging("FoundationCluster", "Debug", " . after evaluation value: %s -> %s" %( value, evaluation_result))
    return evaluation_result


def formated_logging( self, nwkid, ep, cluster, attribute, dt, dz, d, Source, device_model, attr_name, exp_dt, _ranges, _special_values, eval_formula, action_list, eval_inputs, force_value, value):
    self.log.logging( "FoundationCluster",  "Log", "Attribute Report | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s" %(
        nwkid, ep, cluster, attribute, attr_name,  dt, dz, device_model, eval_formula, eval_inputs, action_list, force_value, value ))        