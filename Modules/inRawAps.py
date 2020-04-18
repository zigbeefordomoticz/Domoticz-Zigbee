
import Domoticz

from Modules.schneider_wiser import schneiderReadRawAPS
from Modules.legrand_netatmo import legrandReadRawAPS


def inRawAps( self, srcnwkid, srcep, cluster, dstnwkid, dstep, payload):

    """
    This function is called by Decode8002
    """

    CALLBACK_TABLE = {
        # Manuf : ( callbackDeviceAwake_xxxxx function )
        '105e' : schneiderReadRawAPS ,
        '1021' : legrandReadRawAPS ,
        }

    Domoticz.Log("inRawAps - NwkId: %s Ep: %s, Cluster: %s, dstNwkId: %s, dstEp: %s, Payload: %s" \
            %(srcnwkid, srcep, cluster, dstnwkid, dstep, payload))

    if srcnwkid not in self.ListOfDevices:
        return
    if 'Manufacturer' not in self.ListOfDevices[srcnwkid]:
        return

    manuf = self.ListOfDevices[srcnwkid]['Manufacturer']
    Domoticz.Log("  - Manuf: %s" %manuf)

    if manuf in CALLBACK_TABLE:
        func = CALLBACK_TABLE[ manuf ]
        func( self, srcnwkid, srcep, cluster, dstnwkid, dstep, payload)


    return
