

from Modules.schneider_wiser import callbackDeviceAwake_Schneider


def callbackDeviceAwake(self, key, cluster):

    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part

    and will call the manufacturer specific one if needed and if existing
    """

    CALLBACK_TABLE = {
        # Manuf : ( callbackDeviceAwake_xxxxx function )
        '105e' : callbackDeviceAwake_Schneider ,
        }


    if key not in self.ListOfDevices:
        return
    if 'Manufacturer' not in self.ListOfDevices[key]:
        return

    if self.ListOfDevices[key]['Manufacturer'] in CALLBACK_TABLE:
        manuf = self.ListOfDevices[key]['Manufacturer']
        func = CALLBACK_TABLE[ manuf ]
        func( self, key, cluster)


    return
