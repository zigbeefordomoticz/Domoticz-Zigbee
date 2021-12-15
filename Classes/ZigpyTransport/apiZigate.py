




async def get_firmware_version(self):
    version_str = await self.app._api.version_str()
    
async def zigate_soft_reset(self):
    await self.app._api.reset()
    
async def erase_persistent_data(self):
    await  self.app._api.erase_persistent_data()
    
async def set_time(self, dt=None):
    await self.app._api.set_time( dt=None)
    
async def get_time_server(self):
    await self.app._api.get_time_server()
    
async def set_led(self, enable=True):
    await self.app._api.set_led( enable=True)
    
async def set_certification(self, typ='CE'):
    await self.app._api.set_certification( typ)
    
async def management_network_request(self):
    await self.app._api.management_network_request()
    
async def set_tx_power(self, power=63):
    await self.app._api.set_tx_power(power)
    
async def set_channel(self, channels=None):
    await self.app._api.set_channel( channels=None)
    
    
async def set_extended_panid(self, extended_pan_id):
    await self.app._api.set_extended_panid( extended_pan_id)
    
