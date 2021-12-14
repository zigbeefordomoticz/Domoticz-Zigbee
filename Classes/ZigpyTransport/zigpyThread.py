
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
        self.udpate_network_info (network_state)
        
    def get_zigate_version(self):
        return self.version

    def add_device(self, ieee, nwk):
        Domoticz.Log("add_device %s" %str(nwk))
        
    def device_initialized(self, device):
        Domoticz.Log("device_initialized")
        
    async def remove(self, ieee: t.EUI64) -> None:
        Domoticz.Log("remove")
        
    def get_device(self, ieee=None, nwk=None):
        Domoticz.Log("get_device")
        dev = zigpy.device.Device(self, ieee, nwk)
        return dev
        
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

    def udpate_network_info (self,network_state):
        self.state.network_information = zigpy.state.NetworkInformation(
            extended_pan_id=network_state[3],
            pan_id=network_state[2],
            nwk_update_id=None,
            nwk_manager_id=0x0000,
            channel=network_state[4],
            channel_mask=None,
            security_level=5,
            network_key=None,
            tc_link_key=None,
            children=[],
            key_table=[],
            nwk_addresses={},
            stack_specific=None,
        )
        self.state.node_information= zigpy.state.NodeInfo (
            nwk = network_state[0],
            ieee = network_state[1],
            logical_type = None
        )

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
    self.running = True
    
    Domoticz.Log("PAN ID:               0x%04x" %self.app.pan_id)
    Domoticz.Log("Extended PAN ID:      0x%08x" %self.app.extended_pan_id)
    Domoticz.Log("Channel:              %d" %self.app.channel)
    Domoticz.Log("Device IEEE:          %s" %self.app.ieee)
    Domoticz.Log("Device NWK:           0x%04x" %self.app.nwk)

    #await self.app.permit_ncp(time_s=240)

    # Run forever
    Domoticz.Log("Starting work loop")

    while self.zigpy_running:
        #Domoticz.Log("Continue loop %s" %self.zigpy_running)
        await asyncio.sleep(.5)

    Domoticz.Log("Exiting work loop")


    await self.app.shutdown()
    Domoticz.Log("Exiting co-rounting radio_start")
