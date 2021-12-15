
import asyncio
import binascii
import json
import logging
import queue
from typing import Any, Optional

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
from Classes.ZigpyTransport.nativeCommands import (NATIVE_COMMANDS_MAPPING,
                                                   native_commands)
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

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
        
    def get_zigpy_version(self):
        return self.version

    def add_device(self, ieee, nwk):
        Domoticz.Log("add_device %s" %str(nwk))
        
    def device_initialized(self, device):
        Domoticz.Log("device_initialized")
        
    async def remove(self, ieee: t.EUI64) -> None:
        Domoticz.Log("remove")
        
    def get_device(self, ieee=None, nwk=None):
        Domoticz.Log("get_device")
        return zigpy.device.Device(self, ieee, nwk)
        
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
        
        
        #Domoticz.Log("handle_message %s" %(str(profile)))
        if sender.nwk is not None or sender.ieee is not None:
            plugin_frame = build_plugin_frame_content( sender, profile, cluster, src_ep, dst_ep, message)
            Domoticz.Log("handle_message Sender: %s frame for plugin: %s" %(str(sender.nwk), plugin_frame))
            self.callBackFunction (plugin_frame)
        else:
            Domoticz.Log("handle_message Sender unkown device : %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" %
                     (str(sender), profile, cluster, src_ep, dst_ep, str(message)))

        return None

    def set_callback_message (self, callBackFunction):
        self.callBackFunction = callBackFunction

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
    Domoticz.Log("start_zigpy_thread - Starting zigpy thread")
    self.zigpy_thread.start()

def stop_zigpy_thread(self):
    Domoticz.Log("stop_zigpy_thread - Stopping zigpy thread")
    self.writer_queue.put( (0, "STOP") )
    self.zigpy_running = False
    
def zigpy_thread(self):
    Domoticz.Log("zigpy_thread - Starting zigpy thread")
    self.zigpy_running = True
    asyncio.run( radio_start (self, self._radiomodule, self._serialPort) )  

def build_plugin_frame_content(sender, profile, cluster, src_ep, dst_ep, message, receiver=0x0000, src_addrmode=0x02, dst_addrmode=0x02):
        payload = binascii.hexlify(message).decode('utf-8')
        ProfilID = "%04x" %profile
        ClusterID = "%04x" %cluster
        SourcePoint = "%02x" %src_ep
        DestPoint = "%02x" %dst_ep
        SourceAddressMode = "%02x" %src_addrmode
        SourceAddress = "%04x" %sender.nwk
        DestinationAddressMode = "%02x" %dst_addrmode   
        DestinationAddress = "%04x" %0x0000
        Payload = payload

        frame_payload = "00" + ProfilID + ClusterID + SourcePoint + DestPoint + SourceAddressMode + SourceAddress
        frame_payload += DestinationAddressMode + DestinationAddress + Payload
        
        plugin_frame = "01"                                  # 0:2
        plugin_frame += "8002"                               # 2:4 MsgType 0x8002
        plugin_frame += "%04x" % ((len(frame_payload)//2)+1) # 6:10 lenght
        plugin_frame += "%02x" % 0xff                        # 10:12 CRC set to ff but would be great to  compute it
        plugin_frame += frame_payload
        plugin_frame += "%02x" %sender.lqi
        plugin_frame += "03"
        
        return plugin_frame

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
    
    # Set Call_handler to send message back to F_OUT
    self.app.set_callback_message ( self.F_out )

    await worker_loop(self)

    Domoticz.Log("Exiting work loop")

    await self.app.shutdown()
    Domoticz.Log("Exiting co-rounting radio_start")

async def worker_loop(self):
    self.logging_writer("Status", "worker_loop - ZigyTransport: worker_loop start.")
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',datefmt='%Y-%m-%d:%H:%M:%S',level=logging.DEBUG)
    
    while self.zigpy_running:        
        # self.logging_writer( 'Debug', "Waiting for next command Qsize: %s" %self.writer_queue.qsize())
        if self.writer_queue is None:
            break
        try:
            prio, entry = self.writer_queue.get(False)
        except queue.Empty:
            await asyncio.sleep(.5)
            continue
            
        if entry == "STOP":
            break
    
        # message = {
        #      "cmd": cmd,
        #      "datas": datas,
        #      "NwkId": NwkId,
        #      "TimeStamp": time.time(),
        #      }
        data = json.loads(entry)
        
        try:
            if data["cmd"] == "PERMIT-TO-JOIN":
                duration = data["datas"]["Duration"] 
                if duration == 0xff:
                    duration = 0xfe
                await self.app.permit(time_s=duration)

            elif   data["cmd"] in NATIVE_COMMANDS_MAPPING:
                await native_commands(self, data["cmd"], data["datas"])

            elif data["cmd"] == "RAW-COMMAND":
                process_raw_command( self, data["datas"])

            if self.writer_queue.qsize() > self.statistics._MaxLoad:
                self.statistics._MaxLoad = self.writer_queue.qsize()

        except queue.Empty:
            # Empty Queue, timeout.
            pass

        except Exception as e:
            self.logging_writer("Error", "Error while receiving a ZiGate command: %s" % e)
            handle_thread_error(self, e, 0, 0, "None")
        await asyncio.sleep(.5)
        
    self.logging_writer("Status", "ZigyTransport: writer_thread Thread stop.")

def process_raw_command( self, data):
    #data = {
    #    'Profile': int(profileId, 16),
    #    'Cluster': int(cluster, 16),
    #    'TargetNwk': int(targetaddr, 16),
    #    'TargetEp': int(dest_ep, 16),
    #    'SrcEp': int(zigate_ep, 16),
    #    'Sqn': None,
    #    'payload': payload,
    #    }
    Profile = data["Profile"]
    Cluster = data["Cluster"]
    NwkId = data["TargetNwk"]
    dEp = data["TargetEp"]
    sEp = data["SrcEp"]
    payload = data["payload"]
    sequence = self.app.get_sequence()
    addressmode = data["AddressMode"]
    if addressmode == 0x01:
        self.app.mrequest(self, NwkId, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=True, use_ieee=False)
    elif addressmode == 0x02:
        destination = t.AddrModeAddress(mode=t.AddrMode.NWK, address=NwkId)
        self.app.request(self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=True, use_ieee=False)
    elif addressmode == 0x07:
        destination = t.AddrModeAddress(mode=0x07, address=NwkId)
        self.app.request(self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=True, use_ieee=False)

def handle_thread_error(self, e, nb_in, nb_out, data):
    trace = []
    tb = e.__traceback__
    self.logging_transport("Error","'%s' failed '%s'" % (tb.tb_frame.f_code.co_name, str(e)))
    while tb is not None:
        trace.append(
            {"Module": tb.tb_frame.f_code.co_filename, "Function": tb.tb_frame.f_code.co_name, "Line": tb.tb_lineno}
        )
        self.logging_transport("Error",
            "----> Line %s in '%s', function %s"
            % (
                tb.tb_lineno,
                tb.tb_frame.f_code.co_filename,
                tb.tb_frame.f_code.co_name,
            )
        )
        tb = tb.tb_next

    context = {
        "Error Code": "TRANS-THREADERROR-01",
        "Type:": str(type(e).__name__),
        "Message code:": str(e),
        "Stack Trace": str(trace),
        "nb_in": nb_in,
        "nb_out": nb_out,
        "Data": str(data),
    }
    self.logging_transport("Error", "handle_error_in_thread ", _context=context)

