async def get_firmware_version(self):
    version_str = await self.app._api.version_str()


async def zigate_soft_reset(self):
    await self.app._api.reset()


async def erase_persistent_data(self):
    await self.app._api.erase_persistent_data()


async def set_time(self, dt=None):
    await self.app._api.set_time(dt)


async def get_time_server(self):
    await self.app._api.get_time_server()


async def set_led(self, enable=True):
    await self.app._api.set_led(enable)


async def set_certification(self, typ="CE"):
    await self.app._api.set_certification(typ)


async def management_network_request(self):
    await self.app._api.management_network_request()


async def set_tx_power(self, power=63):
    await self.app._api.set_tx_power(power)


async def set_channel(self, channels=None):
    await self.app._api.set_channel(channels=None)


async def set_extended_panid(self, extended_pan_id):
    await self.app._api.set_extended_panid(extended_pan_id)


NATIVE_COMMANDS_MAPPING = {
    "GET-FIRMWARE-VERSION": {"Function": get_firmware_version, "NumParams": 0},
    "SOFT-RESET": {"Function": zigate_soft_reset, "NumParams": 0},
    "ERASE-PDM": {"Function": erase_persistent_data, "NumParams": 0},
    "SET-TIME": {"Function": set_time, "NumParams": 1},
    "GET-TIME": {"Function": get_time_server, "NumParams": 0},
    "SET-LED": {"Function": set_led, "NumParams": 1},
    "SET-CERTIFICATION": {"Function": set_certification, "NumParams": 1},
    "SET-TX-POWER": {"Function": set_tx_power, "NumParams": 1},
    "SET-CHANNEL": {"Function": set_channel, "NumParams": 1},
    "SET-EXTPANID": {"Function": set_extended_panid, "NumParams": 1},
}


async def native_commands(self, cmd, datas):
    self.log.logging("TransportZigpy", "Debug", "native_commands - cmd: %s datas: %s" % (cmd, datas))
    func = None
    if cmd in NATIVE_COMMANDS_MAPPING:
        func = NATIVE_COMMANDS_MAPPING[cmd]["Function"]
    else:
        self.log.logging("TransportZigpy", "Error", "Unknown native function %s" % cmd)
    if func is None:
        self.log.logging("TransportZigpy", "Error", "Unknown native function %s" % cmd)

    if NATIVE_COMMANDS_MAPPING[cmd]["NumParams"] == 0:
        return await func(self)
    if NATIVE_COMMANDS_MAPPING[cmd]["NumParams"] == 1:
        self.log.logging("TransportZigpy", "Debug", "====> %s" % datas["Param1"])
        return await func(self, datas["Param1"])


# ZIGPY - Mapping
#
# PERMIT-TO-JOIN -> self.app.permit_ncp(duration)
# RAW-COMMAND -> use request or mrequest
