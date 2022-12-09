
import json
from os import listdir
from os.path import isdir, isfile, join
import struct
import binascii
from Modules.domoMaj import MajDomoDevice
from Modules.tools import (DeviceExist, checkAndStoreAttributeValue,
                           checkAttribute, checkValidValue,
                           get_deviceconf_parameter_value, getEPforClusterType,
                           is_hex, set_status_datastruct,
                           set_timestamp_datastruct)


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


def load_foundation_cluster(self):

    foundation_cluster_path = self.pluginconf.pluginConf["pluginConfig"] + "Foundation"

    if not isdir(foundation_cluster_path):
        return

    foundation_cluster_definition = [f for f in listdir(foundation_cluster_path) if isfile(join(foundation_cluster_path, f))]

    for cluster_definition in foundation_cluster_definition:
        cluster_filename = str(foundation_cluster_path + "/" + cluster_definition)
        cluster_definition = _read_foundation_cluster( self, cluster_filename )
        
        if cluster_definition is None:
            continue
        
        if "ClusterId" not in cluster_definition:
            continue
        if "Enabled" not in cluster_definition or not cluster_definition["Enabled"]:
            continue
        if cluster_definition[ "ClusterId"] in self.FoundationClusters:
            continue
        
        self.FoundationClusters[ cluster_definition[ "ClusterId"] ] = {
            "Version": cluster_definition[ "Version" ],
            "Attributes": dict( cluster_definition[ "Attributes" ] )
        }
        self.log.logging("FoundationCluster", "Status", " .  Foundation Cluster %s version %s loaded" %( 
            cluster_definition[ "ClusterId"], cluster_definition[ "Version" ]))

    self.log.logging("FoundationCluster", "Debug", "--> Foundation Clusters loaded: %s" % self.FoundationClusters.keys())
    

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

def cluster_foundation_attribute_retreival( self, cluster, attribute, parameter ):
    
    if parameter in self.FoundationClusters[ cluster ]["Attributes"][ attribute ]:
        return self.FoundationClusters[ cluster ]["Attributes"][ attribute ][ parameter ]
    return ""

def process_cluster_attribute_response( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, ):
    
    self.log.logging("FoundationCluster", "Debug", "Foundation Cluster - Nwkid: %s Ep: %s Cluster: %s Attribute: %s Data: %s Source: %s" %(
        MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData, Source)
    )

    _name = cluster_foundation_attribute_retreival( self, MsgClusterId, MsgAttrID, "Name" )
    _datatype = cluster_foundation_attribute_retreival( self, MsgClusterId, MsgAttrID, "DataType" )
    _range = cluster_foundation_attribute_retreival( self, MsgClusterId, MsgAttrID, "Range" )
    _special_values = cluster_foundation_attribute_retreival( self, MsgClusterId, MsgAttrID, "SpecialValues")
    _eval_formula = cluster_foundation_attribute_retreival( self, MsgClusterId, MsgAttrID, "eval" ) 
    _action_list = cluster_foundation_attribute_retreival( self, MsgClusterId, MsgAttrID, "action" ) 
 
    
    self.log.logging("FoundationCluster", "Debug", " . Name:    %s" %_name )
    self.log.logging("FoundationCluster", "Debug", " . DT:      %s versus received %s" %( _datatype, MsgAttType ))
    self.log.logging("FoundationCluster", "Debug", " . range    %s" %( _range ))
    self.log.logging("FoundationCluster", "Debug", " . formula  %s" %( _eval_formula ))
    self.log.logging("FoundationCluster", "Debug", " . actions  %s" %( _action_list ))
    self.log.logging("FoundationCluster", "Debug", " . special values %s" %( _special_values ))
    
    value = decode_attribute_data( _datatype, MsgClusterData)
    self.log.logging("FoundationCluster", "Debug", " . decode value: %s -> %s" %( MsgClusterData, value))
    
    evaluation_result = value
    if _eval_formula != "":
        evaluation_result = eval( _eval_formula )
    self.log.logging("FoundationCluster", "Debug", " . after evaluation value: %s -> %s" %( value, evaluation_result))
    value = evaluation_result
    
    for data_action in _action_list:
        if data_action == "checkstore":
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)
            
        elif data_action == "majdomodevice":
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value )
    

def decode_attribute_data( AttType, attribute_value, handleErrors=False):

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
        return decode_caracter_string(attribute_value, handleErrors)
    return attribute_value


def decode_caracter_string(attribute_value, handleErrors):
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


def check_range( value, _range):
    
    if len(_range) != 2:
        return None
    if int( _range[0],15) < int(_range[1],16):
        return int( _range[0],15) <= value <= int(_range[1],16)
    
    if int( _range[0],15) > int(_range[1],16):
        return int( _range[0],15) >= value >= int(_range[1],16)
        