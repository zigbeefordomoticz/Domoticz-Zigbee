



import Domoticz
import Modules.output
from Modules.domoticz import MajDomoDevice
from Modules.zigateConsts import ZIGATE_EP


def pollingOrvibo( self, key ):

    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """
    rescheduleAction= False

    return rescheduleAction


def callbackDeviceAwake_Orvibo(self, NwkId, EndPoint, cluster):

    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    #Domoticz.Log("callbackDeviceAwake_Orvibo - Nwkid: %s, EndPoint: %s cluster: %s" \
    #        %(NwkId, EndPoint, cluster))

    return


def orviboReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    #Domoticz.Log("OrviboReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
    #        %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload))

    BUTTON_MAP = {
        # d0d2422bbf3a4982b31ea843bfedb559
        'd0d2422bbf3a4982b31ea843bfedb559': {
            '01': 1, # Top
            '02': 2, # Middle
            '03': 3, # Bottom
            },
        # Interupteur Autocolalant / 
        '3c4e4fc81ed442efaf69353effcdfc5f': { 
            '03': 10, # Top Left,
            '0b': 20, # Middle Left
            '07': 30, # Top Right
            '0f': 40, # Mddle Right
            }
    }

    ACTIONS_MAP ={
        '00': 1, # Click
        '02': 2, # Long Click 
        '03': 3, # Release
    }

 
 
    if srcNWKID not in self.ListOfDevices:
        Domoticz.Error("%s not found in Database")
        return
    if 'Model' not in self.ListOfDevices[ srcNWKID]:
        return

    _Model = self.ListOfDevices[ srcNWKID]['Model']
    if ClusterID != '0017':
        Domoticz.Error("orviboReadRawAPS - unexpected ClusterId %s for NwkId: %s" %(ClusterID, srcNWKID))
        return

    FrameControlFiled = MsgPayload[0:2]

    if FrameControlFiled == '19':
        sqn = MsgPayload[2:4]
        cmd = MsgPayload[4:6]
        data = MsgPayload[6:]

    if cmd == '08':
        button = data[0:2]
        action = data[4:6]

        #Domoticz.Log("button: %s, action: %s" %(button, action))

        if action in ACTIONS_MAP and button in BUTTON_MAP[ _Model]:
           selector = BUTTON_MAP[ _Model][ button ] + ACTIONS_MAP[ action ]
           #Domoticz.Log("---> Selector: %s" %selector)
           MajDomoDevice(self, Devices, srcNWKID, '01', '0006', selector)


def OrviboRegistration( self, nwkid ):

    cluster = '0000'
    attribute = '0099'
    datatype = '20'
    value = '01'

    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "0000" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
           EPout= tmpEp

   # Set Commissioning as Done
    manuf_id = '0000'
    manuf_spec = '00'
    cluster_id = '0000'
    Hattribute = '0099'
    data_type = "20" # Bool
    data = '01'
   
    Domoticz.Log("Orvibo registration for %s" %nwkid)
    Modules.output.write_attribute( self, nwkid, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)    
