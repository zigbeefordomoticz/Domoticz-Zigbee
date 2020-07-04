
import Domoticz
from time import time

from Modules.tools import loggingMessages, decodeMacCapa, ReArrangeMacCapaBasedOnModel, timeStamped, IEEEExist, DeviceExist, initDeviceInList
from Modules.logging import loggingInput, loggingPairing
from Modules.domoTools import lastSeenUpdate, timedOutDevice
from Modules.readAttributes import ReadAttributeRequest_0000, ReadAttributeRequest_0001
from Modules.bindings import rebind_Clusters, reWebBind_Clusters
from Modules.schneider_wiser import schneider_wiser_registration, schneiderReadRawAPS
from Modules.basicOutputs import sendZigateCmd
from Modules.livolo import livolo_bind
from Modules.configureReporting import processConfigureReporting
from Modules.legrand_netatmo import legrand_refresh_battery_remote
from Modules.lumi import  enableOppleSwitch



# When receiving a Device Annoucement the Rejoin Flag can give us some information
# 0x00 The device was not on the network. 
#      Most-likely it has been reset, and all Unbind, Bind , Report, must be redone
# 0x01 The device was on the Network, but change its route
#      the devie was not reset
# 0x02, 0x03 The device was on the network and coming back. 
#       Here we can assumed the device was not reset.


REJOIN_NETWORK = {
    '00': '0x00 - join a network through association',
    '01': '0x01 - joining directly or rejoining the network using the orphaning procedure',
    '02': '0x02 - joining the network using the NWK rejoining procedure.',
    '03': '0x03 - change the operational network channel to that identified in the ScanChannels parameter.',
    }

def device_annoucementv1( self, Devices, MsgData, MsgRSSI  ):

    MsgSrcAddr = MsgData[0:4]
    MsgIEEE = MsgData[4:20]
    MsgMacCapa = MsgData[20:22]
    MsgRejoinFlag = None
    newShortId = False

    if len(MsgData) > 22: # Firmware 3.1b 
        MsgRejoinFlag = MsgData[22:24]

    loggingInput( self, 'Debug', "Decode004D - Device Annoucement: NwkId: %s Ieee: %s MacCap: %s ReJoin: %s LQI: %s" 
        %( MsgSrcAddr,MsgIEEE, MsgMacCapa, MsgRejoinFlag, MsgRSSI ), MsgSrcAddr)


    if is_device_exist_in_db( self, MsgIEEE):
        # This device is known
        newShortId = ( self.IEEE2NWK[ MsgIEEE ] != MsgSrcAddr )
        loggingInput( self, 'Debug', "------>  Known device: NwkId: %s Ieee: %s MacCap: %s ReJoin: %s LQI: %s newShortId: %s" 
            %( MsgSrcAddr,MsgIEEE, MsgMacCapa, MsgRejoinFlag, MsgRSSI, newShortId ), MsgSrcAddr)

        if self.FirmwareVersion and int(self.FirmwareVersion,16) > 0x031b and MsgRejoinFlag is None:
            # Device does exist, we will rely on ZPS_EVENT_NWK_NEW_NODE_HAS_JOINED in order to have the JoinFlag
            loggingInput( self, 'Debug', "------> Droping no rejoin flag! %s %s )" %(MsgSrcAddr, MsgIEEE), MsgSrcAddr)
            timeStamped( self, MsgSrcAddr , 0x004d)
            lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
            return

        if MsgSrcAddr in self.ListOfDevices and self.ListOfDevices[MsgSrcAddr]['Status'] in ( '004d', '0045', '0043', '8045', '8043'):
            # In case we receive a Device Annoucement we are alreday doing the provisioning.
            # Same IEEE and same Short Address.
            # We will drop the message, as there is no reason to process it.
            loggingInput( self, 'Debug', "------> Droping (provisioning in progress) Status: %s" %self.ListOfDevices[MsgSrcAddr]['Status'], MsgSrcAddr)
            return

    now = time()
    loggingMessages( self, '004D', MsgSrcAddr, MsgIEEE, int(MsgRSSI,16), None)

    # Test if Device Exist, if Left then we can reconnect, otherwise initialize the ListOfDevice for this entry
    if DeviceExist(self, Devices, MsgSrcAddr, MsgIEEE):
        decode004d_existing_device( self, Devices, MsgSrcAddr, MsgIEEE , MsgMacCapa, MsgRejoinFlag, newShortId, MsgRSSI, now )
    else:
        loggingPairing( self, 'Status', "Device Announcement Addr: %s, IEEE: %s LQI: %s" \
                %( MsgSrcAddr, MsgIEEE, int(MsgRSSI,16) ) )
        decode004d_new_device( self, Devices, MsgSrcAddr, MsgIEEE , MsgMacCapa, MsgRejoinFlag, MsgData, MsgRSSI, now )


def device_annoucementv2( self, Devices, MsgData, MsgRSSI ):

    # There are 2 types of Device Annoucement the plugin can received from firmware >= 31a
    # (1) Device Annoucement with a JoinFlags and LQI. This one could be issued from:
    #     - device association (but transaction key not yet exchanged)

    MsgSrcAddr = MsgData[0:4]
    MsgIEEE = MsgData[4:20]
    MsgMacCapa = MsgData[20:22]
    MsgRejoinFlag = None
    newShortId = False

    if len(MsgData) > 22: # Firmware 3.1b 
        MsgRejoinFlag = MsgData[22:24]



def is_device_exist_in_db( self, ieee):
    return ieee in self.IEEE2NWK

        
def decode004d_existing_device( self, Devices, MsgSrcAddr, MsgIEEE , MsgMacCapa, MsgRejoinFlag, newShortId, MsgRSSI, now ):
    # ############
    # Device exist, Reconnection has been done by DeviceExist()
    #

    # If needed fix MacCapa
    deviceMacCapa = list(decodeMacCapa( ReArrangeMacCapaBasedOnModel( self, MsgSrcAddr, MsgMacCapa ) ))

    loggingInput( self, 'Debug', "Decode004D - Already known device %s infos: %s, Change ShortID: %s " %( MsgSrcAddr, self.ListOfDevices[MsgSrcAddr], newShortId), MsgSrcAddr)
    if 'Announced' not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['Announced'] = {}
    if not isinstance( self.ListOfDevices[MsgSrcAddr]['Announced'] , dict):
        self.ListOfDevices[MsgSrcAddr]['Announced'] = {}

    self.ListOfDevices[MsgSrcAddr]['Announced']['Rejoin'] = str(MsgRejoinFlag)
    self.ListOfDevices[MsgSrcAddr]['Announced']['newShortId'] = newShortId

    if MsgRejoinFlag in ( '01', '02' ) and self.ListOfDevices[MsgSrcAddr]['Status'] != 'Left':
        loggingInput( self, 'Debug', "--> drop packet for %s due to  Rejoining network as %s, LQI: %s" \
            %(MsgSrcAddr, MsgRejoinFlag, int(MsgRSSI,16)), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Announced']['TimeStamp'] = now
        timeStamped( self, MsgSrcAddr , 0x004d)
        lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)
        legrand_refresh_battery_remote( self, MsgSrcAddr)
        return

    # If we got a recent Annoucement in the last 15 secondes, then we drop the new one
    if 'Announced' in  self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Status'] != 'Left':
        if 'TimeStamp' in self.ListOfDevices[MsgSrcAddr]['Announced']:
            if  now < self.ListOfDevices[MsgSrcAddr]['Announced']['TimeStamp'] + 15:
                # Looks like we have a duplicate Device Announced in less than 15s
                loggingInput( self, 'Debug', "Decode004D - Duplicate Device Annoucement for %s -> Drop" %( MsgSrcAddr), MsgSrcAddr)
                return

    if MsgSrcAddr in self.ListOfDevices:
        if 'ZDeviceName' in self.ListOfDevices[MsgSrcAddr]:
            loggingPairing( self, 'Status', "Device Announcement: %s(%s, %s) Join Flag: %s LQI: %s ChangeShortID: %s " \
                    %( self.ListOfDevices[MsgSrcAddr]['ZDeviceName'], MsgSrcAddr, MsgIEEE, MsgRejoinFlag, int(MsgRSSI,16), newShortId ))
        else:
            loggingPairing( self, 'Status', "Device Announcement Addr: %s, IEEE: %s Join Flag: %s LQI: %s ChangeShortID: %s" \
                    %( MsgSrcAddr, MsgIEEE, MsgRejoinFlag, int(MsgRSSI,16), newShortId))


    self.ListOfDevices[MsgSrcAddr]['Announced']['TimeStamp'] = now
    # If this is a rejoin after a leave, let's update the Status

    if self.ListOfDevices[MsgSrcAddr]['Status'] == 'Left':
        loggingInput( self, 'Debug', "Decode004D -  %s Status from Left to inDB" %( MsgSrcAddr), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['Status'] = 'inDB'

    timeStamped( self, MsgSrcAddr , 0x004d)
    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)

    # If we reach this stage we are in a case of a Device Reset, or
    # we have no evidence and so will do the same
    # Reset the device Hearbeat, This should allow to trigger Read Request
    self.ListOfDevices[MsgSrcAddr]['Heartbeat'] = 0

    for tmpep in self.ListOfDevices[MsgSrcAddr]['Ep']:
        if '0500' in self.ListOfDevices[MsgSrcAddr]['Ep'][tmpep]:
            # We found a Cluster 0x0500 IAS. May be time to start the IAS Zone process
            loggingInput( self, 'Debug', "Decode004D - IAS Zone controler setting %s" \
                    %( MsgSrcAddr), MsgSrcAddr)
            self.iaszonemgt.IASZone_triggerenrollement( MsgSrcAddr, tmpep)
            if '0502'  in self.ListOfDevices[MsgSrcAddr]['Ep'][tmpep]:
                loggingInput( self, 'Debug', "Decode004D - IAS WD enrolment %s" \

                    %( MsgSrcAddr), MsgSrcAddr)
                self.iaszonemgt.IASWD_enroll( MsgSrcAddr, tmpep)
            break
        
    if self.pluginconf.pluginConf['allowReBindingClusters']:
        loggingInput( self, 'Debug', "Decode004D - Request rebind clusters for %s" %( MsgSrcAddr), MsgSrcAddr)
        rebind_Clusters( self, MsgSrcAddr)
        reWebBind_Clusters( self, MsgSrcAddr)

    if  self.ListOfDevices[MsgSrcAddr]['Model'] in ('lumi.remote.b686opcn01', 'lumi.remote.b486opcn01', 'lumi.remote.b286opcn01',
                                    'lumi.remote.b686opcn01-bulb', 'lumi.remote.b486opcn01-bulb', 'lumi.remote.b286opcn01-bulb'):
        loggingInput( self, 'Log', "---> Calling enableOppleSwitch %s" %MsgSrcAddr, MsgSrcAddr)
        enableOppleSwitch( self, MsgSrcAddr)

    # As we are redo bind, we need to redo the Configure Reporting
    if 'ConfigureReporting' in self.ListOfDevices[MsgSrcAddr]:
        del self.ListOfDevices[MsgSrcAddr]['ConfigureReporting']

    processConfigureReporting( self, NWKID=MsgSrcAddr )

    # Let's take the opportunity to trigger some request/adjustement / NOT SURE IF THIS IS GOOD/IMPORTANT/NEEDED
    loggingInput( self, 'Debug', "Decode004D - Request attribute 0x0000 %s" %( MsgSrcAddr), MsgSrcAddr)
    ReadAttributeRequest_0000( self,  MsgSrcAddr)
    sendZigateCmd(self,"0042", str(MsgSrcAddr), ackIsDisabled = True ) 

    # Let's check if this is a Schneider Wiser
    if 'Manufacturer' in self.ListOfDevices[MsgSrcAddr]:
        if self.ListOfDevices[MsgSrcAddr]['Manufacturer'] == '105e':
            schneider_wiser_registration( self, Devices, MsgSrcAddr )



def decode004d_new_device( self, Devices, MsgSrcAddr, MsgIEEE , MsgMacCapa, MsgRejoinFlag, MsgData, MsgRSSI, now ):
    # New Device coming for provisioning
    # Decode Device Capabiities
    deviceMacCapa = list(decodeMacCapa( MsgMacCapa ))

    # There is a dilem here as Livolo and Schneider Wiser share the same IEEE prefix.
    if self.pluginconf.pluginConf['Livolo']:
        PREFIX_MACADDR_LIVOLO = '00124b00'
        if MsgIEEE[0:len(PREFIX_MACADDR_LIVOLO)] == PREFIX_MACADDR_LIVOLO:
            livolo_bind( self, MsgSrcAddr, '06')

    # New device comming. The IEEE is not known
    loggingInput( self, 'Debug', "Decode004D - New Device %s %s" %(MsgSrcAddr, MsgIEEE), MsgSrcAddr)

    # I wonder if this code makes sense ? ( PP 02/05/2020 ), This should not happen!
    if MsgIEEE in self.IEEE2NWK :
        Domoticz.Error("Decode004d - New Device %s %s already exist in IEEE2NWK" %(MsgSrcAddr, MsgIEEE))
        loggingPairing( self, 'Debug', "Decode004d - self.IEEE2NWK[MsgIEEE] = %s with Status: %s" 
                %(self.IEEE2NWK[MsgIEEE], self.ListOfDevices[self.IEEE2NWK[MsgIEEE]]['Status']) )
        if self.ListOfDevices[self.IEEE2NWK[MsgIEEE]]['Status'] != 'inDB':
            loggingInput( self, 'Debug', "Decode004d - receiving a new Device Announced for a device in processing, drop it",MsgSrcAddr)
        return

    # 1- Create the entry in IEEE - 
    self.IEEE2NWK[MsgIEEE] = MsgSrcAddr

    # This code should not happen !( PP 02/05/2020 )
    if IEEEExist( self, MsgIEEE ):
        # we are getting a dupplicate. Most-likely the Device is existing and we have to reconnect.
        if not DeviceExist(self, Devices, MsgSrcAddr,MsgIEEE):
            loggingPairing( self, 'Error', "Decode004d - Paranoia .... NwkID: %s, IEEE: %s -> %s " 
                    %(MsgSrcAddr, MsgIEEE, str(self.ListOfDevices[MsgSrcAddr])))
            return

    # 2- Create the Data Structutre
    initDeviceInList(self, MsgSrcAddr)
    loggingPairing( self, 'Debug',"Decode004d - Looks like it is a new device sent by Zigate")
    self.CommiSSionning = True
    self.ListOfDevices[MsgSrcAddr]['MacCapa'] = MsgMacCapa
    self.ListOfDevices[MsgSrcAddr]['Capability'] = deviceMacCapa
    self.ListOfDevices[MsgSrcAddr]['IEEE'] = MsgIEEE
    self.ListOfDevices[MsgSrcAddr]['Announced'] = now

    if 'Main Powered' in self.ListOfDevices[MsgSrcAddr]['Capability']:
        self.ListOfDevices[MsgSrcAddr]['PowerSource'] = 'Main'
    if 'Full-Function Device' in self.ListOfDevices[MsgSrcAddr]['Capability']:
            self.ListOfDevices[MsgSrcAddr]['LogicalType'] = 'Router'
            self.ListOfDevices[MsgSrcAddr]['DeviceType'] = 'FFD'
    if 'Reduced-Function Device' in self.ListOfDevices[MsgSrcAddr]['Capability']:
            self.ListOfDevices[MsgSrcAddr]['LogicalType'] = 'End Device'
            self.ListOfDevices[MsgSrcAddr]['DeviceType'] = 'RFD'

    loggingPairing( self, 'Log', "--> Adding device %s in self.DevicesInPairingMode" %MsgSrcAddr)
    if MsgSrcAddr not in self.DevicesInPairingMode:
        self.DevicesInPairingMode.append( MsgSrcAddr )
    loggingPairing( self, 'Log',"--> %s" %str(self.DevicesInPairingMode))

    # 3- Store the Pairing info if needed
    if self.pluginconf.pluginConf['capturePairingInfos']:
        if MsgSrcAddr not in self.DiscoveryDevices:
            self.DiscoveryDevices[MsgSrcAddr] = {}
            self.DiscoveryDevices[MsgSrcAddr]['Ep']={}
        self.DiscoveryDevices[MsgSrcAddr]['004D'] = MsgData
        self.DiscoveryDevices[MsgSrcAddr]['NWKID'] = MsgSrcAddr
        self.DiscoveryDevices[MsgSrcAddr]['IEEE'] = MsgIEEE
        self.DiscoveryDevices[MsgSrcAddr]['MacCapa'] = MsgMacCapa
        self.DiscoveryDevices[MsgSrcAddr]['Decode-MacCapa'] = deviceMacCapa

    # 4- We will request immediatly the List of EndPoints
    PREFIX_IEEE_XIAOMI = '00158d000'
    if MsgIEEE[0:len(PREFIX_IEEE_XIAOMI)] == PREFIX_IEEE_XIAOMI:
        ReadAttributeRequest_0000(self, MsgSrcAddr, fullScope=False ) # In order to request Model Name
    if self.pluginconf.pluginConf['enableSchneiderWiser']:
        ReadAttributeRequest_0000(self, MsgSrcAddr, fullScope=False ) # In order to request Model Name

    loggingPairing( self, 'Debug', "Decode004d - Request End Point List ( 0x0045 )")
    self.ListOfDevices[MsgSrcAddr]['Heartbeat'] = "0"
    self.ListOfDevices[MsgSrcAddr]['Status'] = "0045"

    sendZigateCmd(self,"0045", str(MsgSrcAddr))             # Request list of EPs
    loggingInput( self, 'Debug', "Decode004D - %s Infos: %s" %( MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]), MsgSrcAddr)

    timeStamped( self, MsgSrcAddr , 0x004d)
    lastSeenUpdate( self, Devices, NwkId=MsgSrcAddr)