import struct
from Modules.sendZigateCommand import (raw_APS_request)
from Modules.tools import get_and_inc_SQN
import Domoticz

DEFAULT_ACK_MODE = False

# General Command Frame

# Read Attributes Command
def rawaps_read_attribute_req( self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr, ackIsDisabled=DEFAULT_ACK_MODE ):
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
        payload += manufacturer[4:2] + manufacturer[:2]
    payload += sqn + cmd
    idx = 0
    while idx < len(Attr):
        attribute = Attr[idx : idx + 4]
        idx += 4
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(attribute, 16)))[0]
    return raw_APS_request(self, nwkid, EpOut, Cluster, "0104", payload, zigate_ep=EpIn, ackIsDisabled=ackIsDisabled)

# Write Attributes
def rawaps_write_attribute_req( self, nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=DEFAULT_ACK_MODE ):
    self.log.logging("zclCommand", "Debug", "rawaps_write_attribute_req %s %s %s %s %s %s %s %s %s" %(
        nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data))
    cmd = "02" 
    
    cluster_frame = 0b00010000                                                          # The frame type sub-field SHALL be set to indicate a global command (0b00)
    if manuf_spec == "01":                                                              # The manufacturer specific sub-field SHALL be set to 0 if this command is being used to Write Attributes defined for any cluster in the ZCL or 1 if this command is being used to write manufacturer specific attributes
        cluster_frame += 0b00000100
    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_SQN(self, nwkid)
    payload = fcf
    if manuf_spec == "01":
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(manuf_id, 16)))[0]
    payload += sqn + cmd
    payload += "%04x" % struct.unpack(">H", struct.pack("H", int(attribute, 16)))[0]    # Attribute Id
    payload += data_type                                                                # Attribute Data Type
    if data_type in ("10", "18", "20", "28", "30"):                                     # Attribute Data
        payload += data
    elif data_type in ("09", "16", "21", "29", "31"):
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(data, 16)))[0]
    elif data_type in ("22", "2a"):
        payload += "%06x" % struct.unpack(">i", struct.pack("I", int(data, 16)))[0]
    elif data_type in ("23", "2b", "39"):
        payload += "%08x" % struct.unpack(">f", struct.pack("I", int(data, 16)))[0]
    else:
        payload += data
    self.log.logging("zclCommand", "Debug", "rawaps_write_attribute_req ==== payload: %s" %(payload))

    return raw_APS_request(self, nwkid, EPout, cluster, "0104", payload, zigate_ep=EPin, ackIsDisabled=ackIsDisabled)


# Write Attributes No Response 

# Configure Reporting 
def rawaps_configure_reporting_req( self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, attributelist, ackIsDisabled=DEFAULT_ACK_MODE ):
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
        payload += manufacturer[4:2] + manufacturer[:2]
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
    if data_type_id in {0x08, 0x10, 0x18, 0x20, 0x28, 0x30}:
        # 1 byte - 8b
        return data[:2]
    if data_type_id in {0x09, 0x19, 0x21, 0x29, 0x31, 0x38}:
        # 2 bytes - 16b
        return "%04x" % struct.unpack(">H", struct.pack("H", int(data[:4], 16)))[0]
    if data_type_id in {0x0A, 0x1A, 0x22, 0x2a}:
        # 3 bytes - 24b
        return (
            "%08x"
            % struct.unpack(">I", struct.pack("I", int("0" + data[:6], 16)))[0]
        )[:6]

    if data_type_id in {0x0B, 0x1B, 0x23, 0x2b, 0x39}:
        # 4 bytes - 32b
        return "%08x" % struct.unpack(">I", struct.pack("I", int(data[:8], 16)))[0]
    if data_type_id in {0x0C, 0x1C, 0x24, 0x2c }:
        # 5 bytes - 40b
        return (
            "%010x"
            % struct.unpack(">Q", struct.pack("Q", int("0" + data[:10], 16)))[
                0
            ]
        )[:10]

    if data_type_id in {0x0D, 0x1D, 0x25, 0x2d}:
        # 6 bytes - 48b
        return (
            "%012x"
            % struct.unpack(">Q", struct.pack("Q", int(data[:12], 16)))[0]
        )[:12]

    if data_type_id in {0x0E, 0x1E, 0x26, 0x2e}:
        # 7 bytes - 56b
        return (
            "%014x"
            % (
                "%014x"
                % struct.unpack(
                    ">Q", struct.pack("Q", int("00" + data[:14], 16))
                )[0]
            )[:14]
        )

    if data_type_id in {0x0F, 0x1F, 0x27, 0x2f, 0x3a}:
        # 8 bytes - 64b
        return "%016x" % struct.unpack(">Q", struct.pack("Q", int(data[:16], 16)))[0]
    if data_type_id in { 0x41, 0x42 }:
        return data[2:int(data[:2], 16)]


# Discover Attributes 


# Cluster 0006: On/Off
######################
def raw_zcl_zcl_onoff(self, nwkid, EPIn, EpOut, command, effect="", groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
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
    
def zcl_raw_level_move_to_level( self, nwkid, EPIn, EPout, command, level="00", move_mode="00", rate="FF", step_mode="00", step_size="01", transition="0010", groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
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

def zcl_raw_window_covering(self, nwkid, EPIn, EPout, command, level="00", percentage="00", groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
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

# Cluster 0300: Color

def zcl_raw_move_color( self, nwkid, EPIn, EPout, command, temperature=None,  hue=None, saturation=None, colorX=None, colorY=None, transition="0010", groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):

    self.log.logging( "zclCommand", "Debug", "zcl_raw_move_color %s %s %s %s %s %s %s %s %s %s %s" %( 
                    nwkid, EPIn, EPout, command, temperature,  hue, saturation, colorX, colorY, transition, ackIsDisabled))

    COLOR_COMMANDS = {
        #"MovetoHue": 0x00,
        #"MoveHue": 0x01,
        #"StepHue": 0x02,
        #"MovetoSaturation": 0x03,
        #"MoveSaturation": 0x04,
        #"StepSaturation": 0x05,
        "MovetoHueandSaturation": 0x06,      # zcl_move_hue_and_saturation(self, nwkid, EPout, hue, saturation, transition="0010", ackIsDisabled=DEFAULT_ACK_MODE)
        "MovetoColor": 0x07,                # zcl_move_to_colour(self, nwkid, EPout, colorX, colorY, transition="0010", ackIsDisabled=DEFAULT_ACK_MODE)
        #"MoveColor": 0x08,
        #"StepColor": 0x09,
        "MovetoColorTemperature": 0x0a,     # zcl_move_to_colour_temperature( self, nwkid, EPout, temperature, transition="0010", ackIsDisabled=DEFAULT_ACK_MODE)
        #"EnhancedMovetoHue": 0x40,
        #"EnhancedMoveHue": 0x41,
        #"EnhancedStepHue": 0x42,
        #"EnhancedMovetoHueandSaturation": 0x43,
        #"ColorLoopSet": 0x44,
        #"StopMoveStep": 0x47,
        #"MoveCOlorTemperature": 0x4b,
        #"StepColorTemperature": 0x4c
    }


    Cluster = "0300"
    if command not in COLOR_COMMANDS:
        self.log.logging( "zclCommand", "Debug", "zcl_raw_move_color command %s not implemented yet!!" %command)
        return

    
    cluster_frame = 0b00010001
    sqn = get_and_inc_SQN(self, nwkid)
    
    payload = "%02x" % cluster_frame + sqn + "%02x" %COLOR_COMMANDS[ command ] 
     
    if command == "MovetoHueandSaturation" and hue and saturation:
        payload += hue 
        payload += saturation 
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(transition, 16)))[0])
        
    elif command == "MovetoColor" and colorX and colorY:
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(colorX, 16)))[0])  
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(colorY, 16)))[0])  
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(transition, 16)))[0])
        
    elif command == "MovetoColorTemperature" and temperature:
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(temperature, 16)))[0])  
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(transition, 16)))[0])
        
    return raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigate_ep=EPIn, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)



    
