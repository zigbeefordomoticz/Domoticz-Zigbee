import struct
from Modules.sendZigateCommand import (raw_APS_request)
from Modules.tools import get_and_inc_SQN

# General Command Frame

# Read Attributes Command
def rawaps_read_attribute_req( self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr, ackIsDisabled=True ):
    self.log.logging( "zclCommand", "Debug", "rawaps_read_attribute_req %s %s %s %s %s %s %s %s" %(
        nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr) )
    
    cmd = "00"  # Read Attribute Command Identifier

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x00)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #

    cluster_frame = 0b00010000
    if manufacturer_spec == "01":
        cluster_frame += 0b00000100
        
    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_SQN(self, nwkid)
    payload = fcf
    if manufacturer_spec == "01":
        payload += manufacturer_spec + manufacturer[4:2] + manufacturer[0:2]
    payload += sqn + cmd
    idx = 0
    while idx < len(Attr):
        attribute = Attr[idx : idx + 4]
        idx += 4
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(attribute, 16)))[0]
    return raw_APS_request(self, nwkid, EpOut, Cluster, "0104", payload, zigate_ep=EpIn, ackIsDisabled=ackIsDisabled)

# Write Attributes
def rawaps_write_attribute_req( self, nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=True ):
    self.log.logging("zclCommand", "Debug", "rawaps_write_attribute_req %s %s %s %s %s %s %s %s %s" %(
        nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data))
    cmd = "02" 
    cluster_frame = 0b00010000
    if manuf_spec == "01":
        cluster_frame += 0b00000100
    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_SQN(self, nwkid)
    payload = fcf
    if manuf_spec == "01":
        payload += manuf_spec + "%04x" % struct.unpack(">H", struct.pack("H", int(manuf_id, 16)))[0]
    payload += sqn + cmd
    payload += "%04x" % struct.unpack(">H", struct.pack("H", int(attribute, 16)))[0]
    payload += data_type
    if data_type in ("10", "18", "20", "28", "30"):
        payload += data
    elif data_type in ("09", "16", "21", "29", "31"):
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(data, 16)))[0]
    elif data_type in ("22", "2a"):
        payload += "%06x" % struct.unpack(">i", struct.pack("I", int(data, 16)))[0]
    elif data_type in ("23", "2b", "39"):
        payload += "%08x" % struct.unpack(">f", struct.pack("I", int(data, 16)))[0]
    else:
        payload += data
    return raw_APS_request(self, nwkid, EPout, cluster, "0104", payload, zigate_ep=EPin, ackIsDisabled=ackIsDisabled)


# Write Attributes No Response 

# Configure Reporting 
def rawaps_configure_reporting_req( self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, attributelist, ackIsDisabled=True ):
    self.log.logging( "zclCommand", "Debug", "rawaps_read_attribute_req %s %s %s %s %s %s %s %s" %(
        nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, attributelist) )
    
    cmd = "06"  # Configure Reporting Command Identifier

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x00)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #

    cluster_frame = 0b00010000
    if manufacturer_spec == "01":
        cluster_frame += 0b00000100
        
    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_SQN(self, nwkid)
    payload = fcf
    if manufacturer_spec == "01":
        payload += manufacturer_spec + manufacturer[4:2] + manufacturer[0:2]
    payload += sqn + cmd
    payload += build_payload_for_configure_reporting( attributelist )
    return raw_APS_request(self, nwkid, EpOut, Cluster, "0104", payload, zigate_ep=EpIn, ackIsDisabled=ackIsDisabled)

        
def build_payload_for_configure_reporting( attributelist ):
    # Zigate Configure Reporting expect attrubuterecord as: attrdirection + attrType + attr + minInter + maxInter + timeOut + chgFlag
    # So we need to reorder as per Zigbee standard and also handle the Endian
    # https://zigbeealliance.org/wp-content/uploads/2019/12/07-5123-06-zigbee-cluster-library-specification.pdf 2.5.7.1 
    idx = 0
    payload = ""
    while idx < len(attributelist):
        attribute_direction = attributelist[idx : idx + 2]
        attribute_identifier = "%04x" % struct.unpack(">H", struct.pack("H", int(attributelist[idx + 4 : idx + 8], 16)))[0]
        attribute_datatype = attributelist[idx + 2 : idx + 4]
        min_reporting = "%04x" % struct.unpack(">H", struct.pack("H", int(attributelist[idx + 8 : idx + 12], 16)))[0]
        max_reporting = "%04x" % struct.unpack(">H", struct.pack("H", int(attributelist[idx + 12 : idx + 16], 16)))[0]
        idx += 16
        reporting_change = get_change_flag( attribute_datatype, attributelist[idx:] )
        idx += len(reporting_change)
        timeout_period = "%04x" % struct.unpack(">H", struct.pack("H", int(attributelist[idx : idx + 4], 16)))[0]
        idx += 4

        payload += attribute_identifier + attribute_datatype + min_reporting + max_reporting
        if reporting_change != "":
            payload += reporting_change
        payload += timeout_period
    return payload


def get_change_flag( attrType, data):
    # https://zigbeealliance.org/wp-content/uploads/2019/12/07-5123-06-zigbee-cluster-library-specification.pdf Table 2-10 (page 2-41)
    
    data_type_id = int(attrType,16)
    if data_type_id == 0x00:
        return ""
    if data_type_id in {0x08, 0x10, 0x18, 0x20}:
        # 1 byte
        return data[0:2]
    if data_type_id in {0x09, 0x19}:
        # 2 bytes
        return "%04x" % struct.unpack(">H", struct.pack("H", int(data[0:4], 16)))[0]
    if data_type_id in {0x0A, 0x1A}:
        # 3 bytes
        return data[6:4] + data[4:2] + data[0:2]
    if data_type_id in {0x0B, 0x1B}:
        # 4 bytes
        return data[8:6] + data[6:4] + data[4:2] + data[2:0]
    if data_type_id in {0x0C, 0x1C}:
        # 5 bytes
        return data[10:8] + data[8:6] + data[6:4] + data[4:2] + data[2:0]
    if data_type_id in {0x0D, 0x1D}:
        # 6 bytes
        return data[12:10] + data[10:8] + data[8:6] + data[6:4] + data[4:2] + data[2:0]
    if data_type_id in {0x0E, 0x1E}:
        # 7 bytes
        return data[14:12] + data[12:10] + data[10:8] + data[8:6] + data[6:4] + data[4:2] + data[2:0]
    if data_type_id in {0x0F, 0x1F}:
        # 8 bytes
        return data[16:14] + data[14:12] + data[12:10] + data[10:8] + data[8:6] + data[6:4] + data[4:2] + data[2:0]


# Discover Attributes 


# Cluster 0006: On/Off
######################
def raw_zcl_zcl_onoff(self, nwkid, EPIn, EpOut, command, effect="", groupaddrmode=False, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Log","raw_zcl_zcl_onoff %s %s %s %s %s %s" %(nwkid, EPIn, EpOut, command, effect, groupaddrmode ))
    
    Cluster = "0006"
    ONOFF_COMMANDS = {
        "Off": 0x00,
        "On": 0x01,
        "Toggle": 0x02,
        "OffWithEffect": 0x40,
        "OnWithRecallGlobalScene": 0x41,
        "OnWithTimedOff": 0x42,
    }
    if command not in ONOFF_COMMANDS:
        return
    
    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x01)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #
    cluster_frame = 0b00010001

    sqn = get_and_inc_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + "%02x" %ONOFF_COMMANDS[ command ] + effect

    return raw_APS_request(self, nwkid, EpOut, Cluster, "0104", payload, zigate_ep=EPIn, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)


# Cluster 0008: Level Control
#############################
    
def zcl_raw_level_move_to_level( self, nwkid, EPIn, EPout, command, level="00", move_mode="00", rate="FF", step_mode="00", step_size="01", transition="0010", groupaddrmode=False, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_raw_level_move_to_level %s %s %s %s %s %s %s %s %s %s" %(
        nwkid, EPIn, EPout, command, level, move_mode, rate, step_mode, step_size, transition ))
    
    Cluster = "0008"
    LEVEL_COMMANDS = {
        "MovetoLevel": 0x00,
        "Move": 0x01,
        "Step": 0x02,
        "Stop": 0x03,
        "MovetoLevelWithOnOff": 0x04,
        "MoveWithOnOff": 0x05,
        "StepWithOnOff": 0x06,
        "Stop2": 0x07
    }
    if command not in LEVEL_COMMANDS:
        return
    
    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x01)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #
    cluster_frame = 0b00010001

    sqn = get_and_inc_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + "%02x" %LEVEL_COMMANDS[ command ] 
    if command in ("MovetoLevel", "MovetoLevelWithOnOff"):
        payload += level + "%04x" % (struct.unpack(">H", struct.pack("H", int(transition, 16)))[0])
    elif command == ("Move", "MoveWithOnOff"):
        payload += move_mode + rate 
    elif command == ("Step", "StepWithOnOff"):
        payload += step_mode + step_size + "%04x" % (struct.unpack(">H", struct.pack("H", int(transition, 16)))[0])
 
    return raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigate_ep=EPIn, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)

    
# Cluster 0102: Window Covering
################################ 

def zcl_raw_window_covering(self, nwkid, EPIn, EPout, command, level="00", percentage="00", groupaddrmode=False, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_raw_window_covering %s %s %s %s %s" %(nwkid, EPout, command, level , percentage))
    
    Cluster = "0102"
    WINDOW_COVERING_COMMANDS = {
        "Up": 0x00,
        "Down": 0x01,
        "Stop": 0x02,
        "GoToLiftValue": 0x04,
        "GoToLiftPercentage": 0x05,
        "GoToTiltValue": 0x07,
        "GoToTiltPercentage": 0x08
    }
    if command not in WINDOW_COVERING_COMMANDS:
        return
    
    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x01)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #
    cluster_frame = 0b00010001

    sqn = get_and_inc_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + "%02x" %WINDOW_COVERING_COMMANDS[ command ] 
    if command in ("MovetoLevel", "MovetoLevelWithOnOff"):
        payload += level 
    elif command == ("GoToLiftValue", "GoToTiltValue"):
        payload += percentage 
 
    return raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigate_ep=EPIn, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
