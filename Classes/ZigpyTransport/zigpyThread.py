
from typing import Any, Optional
import logging
import asyncio

import Domoticz
import zigpy.appdb
import zigpy.config
import zigpy.device
import zigpy.exceptions
import zigpy.group
import zigpy.ota
import zigpy.quirks
import zigpy.state
import zigpy.topology
import zigpy.types as t
import zigpy.util
import zigpy.zcl
import zigpy.zdo
import zigpy.zdo.types as zdo_types
import zigpy_zigate
import zigpy_zigate.zigbee.application
import zigpy_znp.zigbee.application
from zigpy_zigate.config import CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA, SCHEMA_DEVICE

LOGGER = logging.getLogger(__name__)
    
def dump_app_info(app):
    
    nwk = app[0]
    ieee = app[1]
    pan_id = app[2]
    extended_pan_id = app[3]
    channel = app[4]
    
    Domoticz.Log("PAN ID:               0x%04x" %pan_id)
    Domoticz.Log("Extended PAN ID:      0x%08x" %extended_pan_id)
    Domoticz.Log("Channel:              0x%d" %channel)
    Domoticz.Log("Device IEEE:          %s" %ieee)
    Domoticz.Log("Device NWK:           0x%04x" %nwk)

class App_zigate(zigpy_zigate.zigbee.application.ControllerApplication):
    
        
    async def new(
    cls, config: dict, auto_form: bool = False, start_radio: bool = True
    ) -> zigpy.application.ControllerApplication:
        Domoticz.Log("new" )

    async def _load_db(self) -> None:
        Domoticz.Log("_load_db" )
        
    async def startup(self, auto_form=False):
        await super().startup(auto_form)
        network_state, lqi = await self._api.get_network_state()
        dump_app_info( network_state )
        
    def get_zigate_version(self):
        return  self.version

    def get_zigate_ieee(self):
        return self.ZigateIEEE
    
    def get_zigate_nwkid(self):
        return self.ZigateNWKID
    
    def get_zigate_panid(self):
        return self.ZigatePANId
    
    def get_zigate_extendedpanid(self):
        return self.ZigateExtendedPanId
    
    def get_zigate_channel(self):
        return self.ZigateChannel

    def add_device(self, ieee, nwk):
        Domoticz.Log("add_device %s" %str(nwk))
        
    def device_initialized(self, device):
        Domoticz.Log("device_initialized")
        
    async def remove(self, ieee: t.EUI64) -> None:
        Domoticz.Log("remove")
        
    def get_device(self, ieee=None, nwk=None):
        Domoticz.Log("get_device")
        
    #def zigate_callback_handler(self, msg, response, lqi):
    #    Domoticz.Log("zigate_callback_handler %04x %s" %(msg, response))

    def handle_leave(self, nwk, ieee):
        #super().handle_leave(nwk,ieee) 
        Domoticz.Log("handle_leave %s" %str(nwk))

    def handle_join(self, nwk, ieee):
        #super().handle_join(nwk,ieee) 
        Domoticz.Log("handle_join %s" %str(nwk))

    def handle_message(
        self,
        sender: zigpy.device.Device,
        profile: int,
        cluster: int,
        src_ep: int,
        dst_ep: int,
        message: bytes,
    ) -> None:
        Domoticz.Log("handle_message Sender: %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" %
                     (str(sender), profile, cluster, src_ep, dst_ep, str(message)))
        #Domoticz.Log("handle_message %s" %(str(profile)))
        return None

class App_znp(zigpy_znp.zigbee.application.ControllerApplication):
    pass


def start_zigpy_thread(self):
    self.zigpy_thread.start()

def stop_zigpy_thread(self):
    self.zigpy_running = False
    
def zigpy_thread(self):
    Domoticz.Log("Starting zigpy thread")
    self.zigpy_running = True
    asyncio.run( radio_start (self, self._radiomodule, self._serialPort) )  



async def radio_start(self, radiomodule, serialPort, auto_form=False ):

    Domoticz.Log("In radio_start")
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',datefmt='%Y-%m-%d:%H:%M:%S',level=logging.DEBUG)
    
    # Import the radio library
    conf = {CONF_DEVICE: {"path": serialPort}}
    if radiomodule == 'zigate':
        self.app = App_zigate (conf) 
        
    elif radiomodule == 'znp':
        self.app = App_znp (conf) 

    await self.app.startup(True)  
    self.version = None

    self.FirmwareBranch = "00"  # 00 Production, 01 Development 
    self.FirmwareMajorVersion = "04" # 03 PDM Legcay, 04 PDM Opti, 05 PDM V2
    self.FirmwareVersion = "0320"
    
    self.ZigateIEEE = "%s" %self.app.ieee
    self.ZigateNWKID = "%04x" %self.app.nwk
    self.ZigateExtendedPanId = "%08x" %self.app.extended_pan_id
    self.ZigatePANId = "%04x" %self.app.pan_id
    self.ZigateChannel = "%d" %self.app.channel
    self.running = True
    

    #await self.app.permit_ncp(time_s=240)

    # Run forever
    Domoticz.Log("Starting work loop")

    while self.zigpy_running:
        #Domoticz.Log("Continue loop %s" %self.zigpy_running)
        await asyncio.sleep(.5)

    Domoticz.Log("Exiting work loop")


    await self.app.shutdown()
    Domoticz.Log("Exiting co-rounting radio_start")
