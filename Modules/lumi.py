

import Domoticz

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

