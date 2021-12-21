
from Classes.ZigpyTransport.apiZigate import (erase_persistent_data,
                                              get_firmware_version,
                                              get_time_server,
                                              management_network_request,
                                              set_certification, set_channel,
                                              set_extended_panid, set_led,
                                              set_time, set_tx_power,
                                              zigate_soft_reset)

NATIVE_COMMANDS_MAPPING = {
    "GET-FIRMWARE-VERSION": { 'Function': get_firmware_version, 'NumParams': 0},
    "SOFT-RESET": { 'Function': zigate_soft_reset, 'NumParams': 0},
    "ERASE-PDM": { 'Function': erase_persistent_data, 'NumParams': 0},
    "SET-TIME": { 'Function': set_time, 'NumParams': 1},
    "GET-TIME": { 'Function': get_time_server, 'NumParams': 0},
    "SET-LED": { 'Function': set_led, 'NumParams': 1},
    "SET-CERTIFICATION": { 'Function': set_certification, 'NumParams': 1},
    "SET-TX-POWER": { 'Function': set_tx_power, 'NumParams': 1},
    "SET-CHANNEL": { 'Function': set_channel, 'NumParams': 1},
    "SET-EXTPANID": { 'Function': set_extended_panid, 'NumParams': 1},
    }


async def native_commands( self, cmd, datas):
    self.log.logging("TransportWrter", "Debug","native_commands - cmd: %s datas: %s" %(cmd, datas))
    func = None
    if cmd in NATIVE_COMMANDS_MAPPING:
        func = NATIVE_COMMANDS_MAPPING[ cmd ]['Function']
    else:
        self.log.logging("TransportWrter", "Error","Unknown native function %s" %cmd)
    if func is None:
        self.log.logging("TransportWrter", "Error","Unknown native function %s" %cmd)

    if NATIVE_COMMANDS_MAPPING[ cmd ]['NumParams'] == 0:
        return await func(self)
    if NATIVE_COMMANDS_MAPPING[ cmd ]['NumParams'] == 1:
        self.log.logging("TransportWrter", "Debug","====> %s" %datas["Param1"])
        return await func(self, datas["Param1"] )

# ZIGPY - Mapping
#
# PERMIT-TO-JOIN -> self.app.permit_ncp(duration)
# RAW-COMMAND -> use request or mrequest