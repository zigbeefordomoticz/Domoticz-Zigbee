

from Modules.domoMaj import MajDomoDevice
from Modules.tools import updLQI, updSQN, timeStamped
from Modules.domoTools import lastSeenUpdate, timedOutDevice

def ikea_openclose_remote(self, Devices, NwkId, Ep, command, Data, Sqn):


    if self.ListOfDevices[NwkId]["Status"] != "inDB":
        return

    updSQN(self, NwkId, Sqn)
    lastSeenUpdate(self, Devices, NwkId=NwkId)

    if command == "00":  # Close/Down
        MajDomoDevice(self, Devices, NwkId, Ep, "0006", "00")
    elif command == "01":  # Open/Up
        MajDomoDevice(self, Devices, NwkId, Ep, "0006", "01")
    elif command == "02":  # Stop
        MajDomoDevice(self, Devices, NwkId, Ep, "0006", "02")
