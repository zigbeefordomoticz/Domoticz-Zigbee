import asyncio
import importlib
import logging
import sys
from threading import Thread
import Domoticz
from zigpy_zigate.api import ZiGate
from zigpy_znp.api import ZNP
from zigpy_zigate.config import CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA, SCHEMA_DEVICE


from typing import Any, Optional

import zigpy_zigate
import zigpy_zigate.zigbee.application 
import zigpy_znp.zigbee.application 
import zigpy.device
import zigpy.types as t

from typing import Any, Optional

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

    def add_device(self, ieee, nwk):
        Domoticz.Log("add_device %s" %str(nwk))
    def device_initialized(self, device):
        Domoticz.Log("device_initialized")
    async def remove(self, ieee: t.EUI64) -> None:
        Domoticz.Log("remove")
    def get_device(self, ieee=None, nwk=None):
        Domoticz.Log("get_device")
    def zigate_callback_handler(self, msg, response, lqi):
        Domoticz.Log("zigate_callback_handler %04x %s" %(msg, response))





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
        #Domoticz.Log("handle_message %s %d %d %d %d" %(str(profile),cluster,src_ep,dst_ep))
        Domoticz.Log("handle_message %s" %(str(profile)))
        return None

class App_znp(zigpy_znp.zigbee.application.ControllerApplication):
    pass

         
class ZigpyTransport(object):
    def __init__( self, hardwareid,radiomodule, serialPort):
        logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',datefmt='%Y-%m-%d:%H:%M:%S',level=logging.DEBUG)
        
        self.running = True
        self._serialPort = serialPort
        self._radiomodule = radiomodule
        self.hardwareid = hardwareid
        self.zigpy_thread = Thread(name="Zigpy_thread", target=ZigpyTransport.zigpy_thread, args=(self,))

    def start_zigpy_thread(self):

        self.zigpy_thread.start(  )   
        Domoticz.Log("--> Thread launched: %s" %self.zigpy_thread)

                
    def stop_zigpy_thread(self):
        Domoticz.Log("Shuting down co-routine")
        self.zigpy_running = False
        self.zigpy_thread.join()

    def zigpy_thread(self):
        logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',datefmt='%Y-%m-%d:%H:%M:%S',level=logging.DEBUG)

        Domoticz.Log("Starting zigpy thread")
        self.zigpy_running = True
        app = asyncio.run( radio_start (self, self._radiomodule, self._serialPort) )  
        
              
async def radio_start(self, radiomodule, serialPort, auto_form=False ):

    Domoticz.Log("In radio_start")
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',datefmt='%Y-%m-%d:%H:%M:%S',level=logging.DEBUG)
    
    # Import the radio library
    conf = {CONF_DEVICE: {"path": serialPort}}
    if radiomodule == 'zigate':
        app = App_zigate (conf) 
    elif radiomodule == 'znp':
        app = App_znp (conf) 

    await app.startup(True)  

    await app.permit_ncp(time_s=240)

    # Run forever
    Domoticz.Log("Starting work loop")

    while self.zigpy_running:
        Domoticz.Log("Continue loop %s" %self.zigpy_running)
        await asyncio.sleep(.5)

    Domoticz.Log("Exiting work loop")


    app.shutdown()
    Domoticz.Log("Exiting co-rounting radio_start")