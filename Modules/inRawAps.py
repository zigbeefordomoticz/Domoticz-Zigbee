

from Modules.schneider_wiser import schneiderReadRawAPS


def inRawAps( self, srcnwkid, srcep, cluster, dstnwkid, dstep, payload):

    """
    This function is called by Decode8002
    """

    CALLBACK_TABLE = {
        # Manuf : ( callbackDeviceAwake_xxxxx function )
        '105e' : schneiderReadRawAPS ,
        }


    if key not in self.ListOfDevices:
        return
    if 'Manufacturer' not in self.ListOfDevices[key]:
        return

    if self.ListOfDevices[key]['Manufacturer'] in CALLBACK_TABLE:
        manuf = self.ListOfDevices[key]['Manufacturer']
        func = CALLBACK_TABLE[ manuf ]
        func( self, srcnwkid, srcep, cluster, dstnwkid, dstep, payload)


    return
