
from Classes.ZigpyTransport.apiZigate import (erase_persistent_data,
                                              get_firmware_version,
                                              get_time_server,
                                              management_network_request,
                                              set_certification, set_channel,
                                              set_extended_panid, set_led,
                                              set_time, set_tx_power,
                                              zigate_soft_reset)

NATIVE_COMMANDS_MAPPING = {
    "GET-FIRMWARE-VERSION": get_firmware_version,
    "SOFT-RESET": zigate_soft_reset,
    "ERASE-PDM": erase_persistent_data,
    "SET-TIME": set_time,
    "GET-TIME": get_time_server,
    "SET-LED": set_led,
    "SET-CERTIFICATION": set_certification,
    "SET-TX-POWER": set_tx_power,
    "SET-CHANNEL": set_channel,
    "SET-EXTPANID":set_extended_panid
    }


def native_commands( self, cmd, datas):
    pass

# ZIGPY - Mapping
#
# PERMIT-TO-JOIN -> self.app.permit_ncp(duration)
# RAW-COMMAND -> use request or mrequest