

import Domoticz

from Modules.domoticz import MajDomoDevice
from Modules.output import write_attribute
from Modules.zigateConsts import ZIGATE_EP

def enableOppleSwitch( self, nwkid ):

    if nwkid not in self.ListOfDevices:
        return

    manuf_id = '115F'
    manuf_spec = "01"
    cluster_id = 'FCC0'
    Hattribute = '0009'
    data_type = '20'
    Hdata = '01'

    Domoticz.Log( "Write Attributes LUMI Magic Word Nwkid: %s" %nwkid)
    write_attribute( self, nwkid, ZIGATE_EP, '01', cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)


def AqaraOppleDecoding( self, Devices, nwkid, Ep, ClusterId, ModelName, payload):

    if ClusterId == '0006': # On OFF
        Command =  payload[14:16]    

        Domoticz.Log("AqaraOppleDecoding - Nwkid: %s, Ep: %s,  ON/OFF, Cmd: %s" \
            %(nwkid, Ep, Command))
        MajDomoDevice( self, Devices, nwkid, '01', "0006", Command)

    elif ClusterId == '0008': # Level Control
        StepMode = payload[14:16]
        StepSize = payload[16:18]
        TransitionTime = payload[18:22]
        unknown = payload[22:26]

        Domoticz.Log("AqaraOppleDecoding - Nwkid: %s, Ep: %s, LvlControl, StepMode: %s, StepSize: %s, TransitionTime: %s, unknown: %s" \
            %(nwkid, Ep,StepMode,StepSize,TransitionTime,unknown))

        MajDomoDevice( self, Devices, nwkid, '03', "0006", StepSize)

    elif ClusterId == '0300': # Step Color Temperature
        StepMode = payload[14:16]
        EnhancedStepSize = payload[16:20]
        TransitionTime = payload[20:24]
        ColorTempMinimumMired = payload[24:28]
        ColorTempMaximumMired = payload[28:32]
        unknown = payload[32:36]

        Domoticz.Log("AqaraOppleDecoding - Nwkid: %s, Ep: %s, ColorControl , StepMode: %s, EnhancedStepSize: %s, TransitionTime: %s, ColorTempMinimumMired: %s, ColorTempMaximumMired: %s" \
            %(nwkid, Ep,StepMode,EnhancedStepSize,TransitionTime,ColorTempMinimumMired, ColorTempMaximumMired))
 
 
 

    return