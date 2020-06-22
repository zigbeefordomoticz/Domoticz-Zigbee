#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: basicOutputs

    Description: All direct communications towards Zigate

"""
import Domoticz
import binascii
import struct
import json

from datetime import datetime
from time import time

from Modules.zigateConsts import ZIGATE_EP, ADDRESS_MODE, ZLL_DEVICES, ZIGATE_COMMANDS
from Modules.tools import mainPoweredDevice
from Modules.logging import loggingBasicOutput

def send_zigatecmd_zcl_ack( self, address, cmd, datas ):
    # Send a ZCL command with ack
    # address can be a shortId or an IEEE
    ackIsDisabled = False
    if len(address) == 4:
        # Short address
        address_mode = '%02x' %ADDRESS_MODE['short']
        if self.pluginconf.pluginConf['disableAckOnZCL']:
            address_mode = '%02x' %ADDRESS_MODE['shortnoack']
            ackIsDisabled = True
    else:
        address_mode = '%02x' %ADDRESS_MODE['ieee']
        if self.pluginconf.pluginConf['disableAckOnZCL']:
            address_mode = '%02x' %ADDRESS_MODE['ieeenoack']
            ackIsDisabled = True
    return send_zigatecmd_raw( self, cmd, address_mode + address + datas, ackIsDisabled = ackIsDisabled )

def send_zigatecmd_zcl_noack( self, address, cmd, datas):
    # Send a ZCL command with ack
    # address can be a shortId or an IEEE
    disableAck = True
    if len(address) == 4:
        # Short address
        address_mode = '%02x' %ADDRESS_MODE['shortnoack']
        if self.pluginconf.pluginConf['forceAckOnZCL']:
            Domoticz.Log("Force Ack")
            address_mode = '%02x' %ADDRESS_MODE['short']
            disableAck = False
    else:
        address_mode = '%02x' %ADDRESS_MODE['ieeenoack']
        if self.pluginconf.pluginConf['forceAckOnZCL']:
            address_mode = '%02x' %ADDRESS_MODE['ieee']
            Domoticz.Log("Force Ack")
            disableAck = False 
    return send_zigatecmd_raw( self, cmd, address_mode + address + datas, ackIsDisabled = disableAck )

def send_zigatecmd_raw( self, cmd, datas, ackIsDisabled = False ):
    #
    # Send the cmd directly to ZiGate

   if self.ZigateComm is None:
       Domoticz.Error("Zigate Communication error.")
       return

   i_sqn = self.ZigateComm.sendData( cmd, datas , ackIsDisabled )
   if self.pluginconf.pluginConf['debugzigateCmd']:
       loggingBasicOutput( self, 'Log', "send_zigatecmd_raw - [%s] %s %s Queue Length: %s" %(i_sqn, cmd, datas, self.ZigateComm.loadTransmit()))
   else:
       loggingBasicOutput( self, 'Debug', "=====> send_zigatecmd_raw - [%s] %s %s Queue Length: %s" %(i_sqn,cmd, datas, self.ZigateComm.loadTransmit()))
   if self.ZigateComm.loadTransmit() > 15:
       loggingBasicOutput( self, 'Log', "WARNING - send_zigatecmd_raw: [%s] %s %18s ZigateQueue: %s" %(i_sqn,cmd, datas, self.ZigateComm.loadTransmit()))

   return i_sqn

def sendZigateCmd(self, cmd, datas , ackIsDisabled = False):
    """
    sendZigateCmd will send command to Zigate by using the SendData method
    cmd : 4 hex (str) which correspond to the Zigate command
    datas : string of hex char 
    ackIsDisabled : If True, it means that usally a Ack is expected ( ZIGATE_COMMANDS), but here it has been disabled via Address Mode

    """
    if int(cmd,16) not in ZIGATE_COMMANDS:
        Domoticz.Error("Unexpected command: %s %s" %(cmd, datas))
        return None
    
    if ZIGATE_COMMANDS[ int(cmd,16)]['Layer'] == 'ZCL':
        loggingBasicOutput( self, 'Debug', "sendZigateCmd - ZCL layer %s %s" %(cmd, datas))

        AddrMod = datas[0:2]
        NwkId = datas[2:6]
        if NwkId not in self.ListOfDevices:
            Domoticz.Error("sendZigateCmd - Decoding error %s %s" %(cmd, datas))
            return None
        if AddrMod == '01':
            # Group With Ack
            return send_zigatecmd_raw( self, cmd, datas ) 

        if AddrMod == '02':
            # Short with Ack
            return send_zigatecmd_zcl_ack( self,NwkId, cmd, datas[6:] )   

        if AddrMod == '07':
            # Short No Ack
            return send_zigatecmd_zcl_noack( self,NwkId, cmd, datas[6:] )

    return send_zigatecmd_raw( self, cmd, datas, ackIsDisabled )

def ZigatePermitToJoin( self, permit ):
    """
    ZigatePermitToJoin will switch the Zigate in the Pairing mode or not based on the permit flag

    permit : 0 - disable Permit to Join
             1 - 254 - enable Permit to join from 1s to 254s
             255 - enable Permit to join (unlimited)
    """

    if permit:
        # Enable Permit to join
        if self.permitTojoin['Duration'] != 255:
            if permit != 255:
                loggingBasicOutput( self, "Status", "Request Accepting new Hardware for %s seconds " %permit)
            else:
                loggingBasicOutput( self, "Status", "Request Accepting new Hardware for ever ")

            self.permitTojoin['Starttime'] = int(time())
            self.permitTojoin['Duration'] = 0 if permit <= 5 else permit
    else:
        self.permitTojoin['Starttime'] = int(time())
        self.permitTojoin['Duration'] = 0
        loggingBasicOutput( self, "Status", "Request Disabling Accepting new Hardware")

    PermitToJoin( self, '%02x' %permit )

    loggingBasicOutput( self, 'Debug', "Permit Join set :" )
    loggingBasicOutput( self, 'Debug', "---> self.permitTojoin['Starttime']: %s" %self.permitTojoin['Starttime'] )
    loggingBasicOutput( self, 'Debug', "---> self.permitTojoin['Duration'] : %s" %self.permitTojoin['Duration'] )

def PermitToJoin( self, Interval, TargetAddress='FFFC'):
    
    send_zigatecmd_raw(self, "0049", TargetAddress + Interval + '00' )
    if TargetAddress == 'FFFC':
        # Request a Status to update the various permitTojoin structure
        send_zigatecmd_raw( self, "0014", "" ) # Request status
 
def start_Zigate(self, Mode='Controller'):
    """
    Purpose is to run the start sequence for the Zigate
    it is call when Network is not started.

    """

    ZIGATE_MODE = ( 'Controller', 'Router' )

    if Mode not in ZIGATE_MODE:
        Domoticz.Error("start_Zigate - Unknown mode: %s" %Mode)
        return

    loggingBasicOutput( self, "Status", "ZigateConf setting Channel(s) to: %s" \
            %self.pluginconf.pluginConf['channel'])
    setChannel(self, str(self.pluginconf.pluginConf['channel']))
    
    if Mode == 'Controller':
        loggingBasicOutput( self, "Status", "Set Zigate as a Coordinator" )
        send_zigatecmd_raw(self, "0023","00")

        loggingBasicOutput( self, "Status", "Set Zigate as a TimeServer" )
        setTimeServer( self)

        loggingBasicOutput( self, "Status", "Start network" )
        send_zigatecmd_raw(self, "0024", "" )   # Start Network
    
        loggingBasicOutput( self, 'Debug', "Request network Status" )
        send_zigatecmd_raw( self, "0014", "" ) # Request status
        send_zigatecmd_raw( self, "0009", "" ) # Request status

        # Request a Status to update the various permitTojoin structure
        send_zigatecmd_raw( self, "0014", "" ) # Request status

def setTimeServer( self ):

    EPOCTime = datetime(2000,1,1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())
    #loggingBasicOutput( self, "Status", "setTimeServer - Setting UTC Time to : %s" %( UTCTime) )
    data = "%08x" %UTCTime
    send_zigatecmd_raw(self, "0016", data  )
    #Request Time
    send_zigatecmd_raw(self, "0017", "")

def zigateBlueLed( self, OnOff):

    if OnOff:
        loggingBasicOutput( self, 'Log', "Switch Blue Led On" )
        send_zigatecmd_raw(self, "0018","01")
    else:
        loggingBasicOutput( self, 'Log', "Switch Blue Led off" )
        send_zigatecmd_raw(self, "0018","00")

def getListofAttribute(self, nwkid, EpOut, cluster):
    
    #datas = "{:02n}".format(2) + nwkid + ZIGATE_EP + EpOut + cluster + "0000" + "00" + "00" + "0000" + "FF"
    datas = ZIGATE_EP + EpOut + cluster + "0000" + "00" + "00" + "0000" + "FF"
    loggingBasicOutput( self, 'Debug', "attribute_discovery_request - " +str(datas) )
    send_zigatecmd_zcl_noack(self, nwkid, "0140", datas )

def initiateTouchLink( self):

    loggingBasicOutput( self, "Status", "initiate Touch Link")
    send_zigatecmd_raw(self, "00D0", '' )

def factoryresetTouchLink( self):

    loggingBasicOutput( self, "Status", "Factory Reset Touch Link Over The Air")
    send_zigatecmd_raw(self, "00D2", '' )

def identifySend( self, nwkid, ep, duration=0, withAck = False):

    #datas = "02" + "%s"%(nwkid) + ZIGATE_EP + ep + "%04x"%(duration) 
    datas = ZIGATE_EP + ep + "%04x"%(duration) 
    loggingBasicOutput( self, 'Debug', "identifySend - send an Identify Message to: %s for %04x seconds Ack: %s" %( nwkid, duration, withAck))
    loggingBasicOutput( self, 'Debug', "identifySend - data sent >%s< " %(datas))
    if withAck:
        send_zigatecmd_zcl_ack(self, nwkid, "0070", datas )
    else:
        send_zigatecmd_zcl_noack(self, nwkid, "0070", datas )

def maskChannel( channel ):

    CHANNELS = { 0: 0x00000000, # Scan for all channels
            11: 0x00000800,
            12: 0x00001000, 
            13: 0x00002000, 
            14: 0x00004000, 
            15: 0x00008000,
            16: 0x00010000, 
            17: 0x00020000, 
            18: 0x00040000, 
            19: 0x00080000,
            20: 0x00100000,
            21: 0x00200000, 
            22: 0x00400000, 
            23: 0x00800000, 
            24: 0x01000000, 
            25: 0x02000000,
            26: 0x04000000 }

    mask = 0x00000000

    if isinstance(channel, list):
        for c in channel:
            if c.isdigit():
                if int(c) in CHANNELS:
                    mask += CHANNELS[int(c)]
            else:
                Domoticz.Error("maskChannel - invalid channel %s" %c)

    elif isinstance(channel, int):
        if channel in CHANNELS:
            mask = CHANNELS[ channel ]
        else:
            Domoticz.Error("Requested channel not supported by Zigate: %s" %channel)

    elif isinstance(channel, str):
        lstOfChannels = channel.strip().split(',')
        for channel in lstOfChannels:
            if channel.isdigit():
                if int(channel) in CHANNELS:
                    mask += CHANNELS[int(channel)]
                else:
                    Domoticz.Error("Requested channel not supported by Zigate: %s" %channel)
            else:
                Domoticz.Error("maskChannel - invalid channel %s" %c)
    else:
        Domoticz.Errors("Requested channel is invalid: %s" %channel)

    return mask

def setChannel( self, channel):
    '''
    The channel list
    is a bitmap, where each bit describes a channel (for example bit 12
    corresponds to channel 12). Any combination of channels can be included.
    ZigBee supports channels 11-26.
    '''
    mask = maskChannel( channel )
    loggingBasicOutput( self, "Status", "setChannel - Channel set to : %08.x " %(mask))

    send_zigatecmd_raw(self, "0021", "%08.x" %(mask))

def channelChangeInitiate( self, channel ):

    loggingBasicOutput( self, "Status", "Change channel from [%s] to [%s] with nwkUpdateReq" %(self.currentChannel, channel))
    Domoticz.Log("Not Implemented")
    #NwkMgtUpdReq( self, channel, 'change')

def channelChangeContinue( self ):

    loggingBasicOutput( self, "Status", "Restart network")
    send_zigatecmd_raw(self, "0024", "" )   # Start Network
    send_zigatecmd_raw(self, "0009", "")     # In order to get Zigate IEEE and NetworkID

def setExtendedPANID(self, extPANID):
    '''
    setExtendedPANID MUST be call after an erase PDM. If you change it 
    after having paired some devices, they won't be able to reach you anymore
    Extended PAN IDs (EPIDs) are 64-bit numbers that uniquely identify a PAN. 
    ZigBee communicates using the shorter 16-bit PAN ID for all communication except one.
    '''

    datas = "%016x" %extPANID
    loggingBasicOutput( self, 'Debug', "set ExtendedPANID - %016x "\
            %( extPANID) )
    send_zigatecmd_raw(self, "0020", datas )

def leaveMgtReJoin( self, saddr, ieee, rejoin=True):
    """
    E_SL_MSG_MANAGEMENT_LEAVE_REQUEST / 0x47 


    This function requests a remote node to leave the network. The request also
    indicates whether the children of the leaving node should also be requested to leave
    and whether the leaving node(s) should subsequently attempt to rejoin the network.

    This function is provided in the ZDP API for the reason
    of interoperability with nodes running non-NXP ZigBee PRO
    stacks that support the generated request. On receiving a
    request from this function, the NXP ZigBee PRO stack will
    return the status ZPS_ZDP_NOT_SUPPORTED.

    """

    loggingBasicOutput( self, 'Log', "leaveMgtReJoin - sAddr: %s , ieee: %s, [%s/%s]" %( saddr, ieee,  self.pluginconf.pluginConf['allowAutoPairing'], rejoin))
    if not self.pluginconf.pluginConf['allowAutoPairing']:
        loggingBasicOutput( self, 'Log', "leaveMgtReJoin - no action taken as 'allowAutoPairing' is %s" %self.pluginconf.pluginConf['allowAutoPairing'])
        return

    if rejoin:
        loggingBasicOutput( self, "Status", "Switching Zigate in pairing mode to allow %s (%s) coming back" %(saddr, ieee))

        # If Zigate not in Permit to Join, let's switch it to Permit to Join for 60'
        duration = self.permitTojoin['Duration']
        stamp = self.permitTojoin['Starttime']
        if duration == 0:
            dur_req = 60
            self.permitTojoin['Duration'] = 60
            self.permitTojoin['Starttime'] = int(time())
            loggingBasicOutput( self, 'Debug', "leaveMgtReJoin - switching Zigate in Pairing for %s sec" % dur_req)
            send_zigatecmd_raw(self, "0049","FFFC" + '%02x' %dur_req + "00")
            loggingBasicOutput( self, 'Debug', "leaveMgtReJoin - Request Pairing Status")
            send_zigatecmd_raw( self, "0014", "" ) # Request status
        elif duration != 255:
            if  int(time()) >= ( self.permitTojoin['Starttime'] + 60):
                dur_req = 60
                self.permitTojoin['Duration'] = 60
                self.permitTojoin['Starttime'] = int(time())
                loggingBasicOutput( self, 'Debug', "leaveMgtReJoin - switching Zigate in Pairing for %s sec" % dur_req)
                send_zigatecmd_raw(self, "0049","FFFC" + '%02x' %dur_req + "00")
                loggingBasicOutput( self, 'Debug', "leaveMgtReJoin - Request Pairing Status")
                send_zigatecmd_raw( self, "0014", "" ) # Request status

        #Request a Re-Join and Do not remove children
        _leave = '01'
        _rejoin = '01'
        _rmv_children = '01'
        _dnt_rmv_children = '00'

        datas = saddr + ieee + _rejoin + _dnt_rmv_children
        loggingBasicOutput( self, "Status", "Request a rejoin of (%s/%s)" %(saddr, ieee))
        send_zigatecmd_raw(self, "0047", datas )

def leaveRequest( self, ShortAddr=None, IEEE= None, RemoveChild=0x00, Rejoin=0x00 ):
    """
    E_SL_MSG_LEAVE_REQUEST / 0x004C / ZPS_eAplZdoLeaveNetwork
    If you wish to move a whole network branch from under
    the requesting node to a different parent node, set
    bRemoveChildren to FALSE and bRejoin to TRUE.
    """

    _ieee = None

    if IEEE:
        _ieee = IEEE
    else:
        if ( ShortAddr and ShortAddr in self.ListOfDevices and 'IEEE' in self.ListOfDevices[ShortAddr] ):
            _ieee = self.ListOfDevices[ShortAddr]['IEEE']
        else:
            Domoticz.Error("leaveRequest - Unable to determine IEEE address for %s %s" %(ShortAddr, IEEE))
            return

    _rmv_children = '%02X' %RemoveChild
    _rejoin = '%02X' %Rejoin

    datas = _ieee + _rmv_children + _rejoin
    #loggingBasicOutput( self, "Status", "Sending a leaveRequest - %s %s" %( '0047', datas))
    loggingBasicOutput( self, 'Debug', "---------> Sending a leaveRequest - NwkId: %s, IEEE: %s, RemoveChild: %s, Rejoin: %s" %( ShortAddr, IEEE, RemoveChild, Rejoin))
    send_zigatecmd_raw(self, "0047", datas )

def removeZigateDevice( self, IEEE ):
    """
    E_SL_MSG_NETWORK_REMOVE_DEVICE / 0x0026 / ZPS_teStatus ZPS_eAplZdoRemoveDeviceReq

    This function can be used (normally by the Co-ordinator/Trust Centre) to request
    another node (such as a Router) to remove one of its children from the network (for
    example, if the child node does not satisfy security requirements).

    The Router receiving this request will ignore the request unless it has originated from
    the Trust Centre or is a request to remove itself. If the request was sent without APS
    layer encryption, the device will ignore the request. If APS layer security is not in use,
    the alternative function ZPS_eAplZdoLeaveNetwork() should be used.


    u64ParentAddr 64-bit IEEE/MAC address of parent to be instructed
    u64ChildAddr 64-bit IEEE/MAC address of child node to be removed
    """

    if IEEE not in self.IEEE2NWK:
        return

    nwkid = self.IEEE2NWK[ IEEE ]
    loggingBasicOutput( self, "Status", "Remove from Zigate Device = " + " IEEE = " +str(IEEE) )

    # Do we have to remove a Router or End Device ?
    if mainPoweredDevice( self, nwkid):
        ParentAddr = IEEE
    else:
        if self.ZigateIEEE is None:
            Domoticz.Error("Zigae IEEE unknown: %s" %self.ZigateIEEE)
            return
        ParentAddr = self.ZigateIEEE

    ChildAddr = IEEE
    send_zigatecmd_raw(self, "0026", ParentAddr + ChildAddr )

def raw_APS_request( self, targetaddr, dest_ep, cluster, profileId, payload, zigate_ep=ZIGATE_EP):

    """" Command
    This function submits a request to send data to a remote node, with no restrictions
    on the type of transmission, destination address, destination application profile,
    destination cluster and destination endpoint number - these destination parameters
    do not need to be known to the stack or defined in the ZPS configuration. In this
    sense, this is most general of the Data Transfer functions.

    The data is sent in an Application Protocol Data Unit (APDU) instance,

    Command 0x0530
    address mode
    target short address 4
    source endpoint 2
    destination endpoint 2
    clusterId 4
    profileId 4
    security mode 2
    radius 2
    data length 2
    data Array of 2

    eSecurityMode is the security mode for the data transfer, one of:
            0x00 : ZPS_E_APL_AF_UNSECURE (no security enabled)
            0x01 : ZPS_E_APL_AF_SECURE Application-level security using link key and network key)
            0x02 : ZPS_E_APL_AF_SECURE_NWK (Network-level security using network key)
            0x10 : ZPS_E_APL_AF_SECURE | ZPS_E_APL_AF_EXT_NONCE (Application-level security using link key and network key with the extended NONCE included in the frame)
            0x20 : ZPS_E_APL_AF_WILD_PROFILE (May be combined with above flags using OR operator. Sends the message using the wild card profile (0xFFFF) instead of the profile in the associated Simple descriptor)
    u8Radius is the maximum number of hops permitted to the destination node (zero value specifies that default maximum is to be used)

    """
    """ APS request command Payload

    target addr ( IEEE )
    target ep
    clusterID
    dest addr mode
    dest addr
    dest ep

    """

    #SECURITY = 0x33
    SECURITY = 0x30
    RADIUS = 0x00

    addr_mode ='%02X' % ADDRESS_MODE['short']
    security = '%02X' %SECURITY
    radius = '%02X' %RADIUS

    len_payload = (len(payload)) // 2
    len_payload = '%02x' %len_payload

    loggingBasicOutput( self, 'Debug', "raw_APS_request - Addr: %s Ep: %s Cluster: %s ProfileId: %s Payload: %s" %(targetaddr, dest_ep, cluster, profileId, payload))

    send_zigatecmd_raw(self, "0530", addr_mode + targetaddr + zigate_ep + dest_ep + cluster + profileId + security + radius + len_payload + payload)


def read_attribute( self, addr ,EpIn , EpOut ,Cluster ,direction , manufacturer_spec , manufacturer , lenAttr, Attr, ackToBeEnabled = False):
    
    if ackToBeEnabled:
        send_zigatecmd_zcl_ack( self, addr, '0100', EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + '%02x' %lenAttr + Attr )
    else:
        send_zigatecmd_zcl_noack( self, addr, '0100', EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + '%02x' %lenAttr + Attr )

def write_attribute( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackToBeEnabled = False):
    
    direction = "00"
    if data_type == '42': # String  
        # In case of Data Type 0x42 ( String ), we have to add the length of string before the string.
        data = '%02x' %(len(data)//2) + data

    lenght = "01" # Only 1 attribute

    datas = ZIGATE_EP + EPout + clusterID
    datas += direction + manuf_spec + manuf_id
    datas += lenght +attribute + data_type + data
    loggingBasicOutput( self, 'Debug', "write_attribute for %s/%s - >%s<" %(key, EPout, datas) )

    # ATTENTION "0110" with firmware 31c are always call with Ack (overwriten by firmware)
    if ackToBeEnabled:
        return send_zigatecmd_zcl_ack(self, key, "0110", str(datas))
    else:
        return send_zigatecmd_zcl_ack(self, key, "0110", str(datas))


def write_attributeNoResponse( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackToBeDisabled = False ):
    
    if key == 'ffff':
        addr_mode = '04'
    direction = "00"

    if data_type == '42': # String
        # In case of Data Type 0x42 ( String ), we have to add the length of string before the string.
        data = '%02x' %(len(data)//2) + data

    lenght = "01" # Only 1 attribute

    datas = ZIGATE_EP + EPout + clusterID
    datas += direction + manuf_spec + manuf_id
    datas += lenght +attribute + data_type + data
    loggingBasicOutput( self, 'Log', "write_attribute No Reponse for %s/%s - >%s<" %(key, EPout, datas), key)

    # Firmware <= 31c are in fact with ACK
    return send_zigatecmd_zcl_noack(self, key, "0113", str(datas))

## Scene
def scene_membership_request( self, nwkid, ep, groupid='0000'):

    datas = ZIGATE_EP + ep +  groupid
    send_zigatecmd_zcl_noack(self, nwkid, "00A6", datas )

def identifyEffect( self, nwkid, ep, effect='Blink' ):

    """
        Blink   / Light is switched on and then off (once)
        Breathe / Light is switched on and off by smoothly increasing and 
                  then decreasing its brightness over a one-second period, 
                  and then this is repeated 15 times
        Okay    / •  Colour light goes green for one second
                  •  Monochrome light flashes twice in one second
        Channel change / •  Colour light goes orange for 8 seconds
                         •  Monochrome light switches to
                            maximum brightness for 0.5 s and then to
                            minimum brightness for 7.5 s
        Finish effect  /  Current stage of effect is completed and then identification mode is
                          terminated (e.g. for the Breathe effect, only the current one-second
                          cycle will be completed)
        Stop effect    /  Current effect and id


        A variant of the selected effect can also be specified, but currently only the default
        (as described above) is available.
    """

    effect_command = { 'Blink': 0x00 ,
            'Breathe': 0x01,
            'Okay': 0x02,
            'ChannelChange': 0x0b,
            'FinishEffect': 0xfe,
            'StopEffect': 0xff }


    identify = any( '0300' in self.ListOfDevices[nwkid]['Ep'][iterEp] for iterEp in self.ListOfDevices[nwkid]['Ep'] )


    if ( 'ZDeviceID' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]['ZDeviceID'] != {} and \
        self.ListOfDevices[nwkid]['ZDeviceID'] != '' and int(self.ListOfDevices[nwkid]['ZDeviceID'], 16) in ZLL_DEVICES ):
        identify = True

    if not identify:
        return

    if effect not in effect_command:
        effect = 'Blink'

    #datas = "02" + "%s"%(nwkid) + ZIGATE_EP + ep + "%02x"%(effect_command[effect])  + "%02x" %0
    datas = ZIGATE_EP + ep + "%02x"%(effect_command[effect])  + "%02x" %0
    send_zigatecmd_zcl_noack(self, nwkid, "00E0", datas )