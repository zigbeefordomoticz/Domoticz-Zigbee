#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: badz & pipiche38
#
import asyncio
import logging

import Classes.ZigpyTransport.AppGeneric
import zigpy.config as zigpy_conf
import zigpy.device
import zigpy.types as t
import zigpy.zcl
import zigpy.zdo
import zigpy.zdo.types as zdo_types
import zigpy_deconz
import zigpy_deconz.zigbee.application
from Classes.ZigpyTransport.plugin_encoders import \
    build_plugin_8010_frame_content

LOGGER = logging.getLogger(__name__)

class App_deconz(zigpy_deconz.zigbee.application.ControllerApplication):
    @classmethod
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        LOGGER.debug("new")

    async def _load_db(self) -> None:
        await Classes.ZigpyTransport.AppGeneric._load_db(self)
        LOGGER.debug("_load_db")

    async def initialize(self, *, auto_form: bool = False, force_form: bool = False):
        await Classes.ZigpyTransport.AppGeneric.initialize(self, auto_form=auto_form, force_form=force_form)
        LOGGER.info("deCONZ Configuration: %s", self.config)

    async def startup(self, HardwareID, pluginconf, callBackHandleMessage, callBackUpdDevice=None, callBackGetDevice=None, callBackBackup=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
        self.log = log
        self.pluginconf = pluginconf
        self.permit_to_join_timer = permit_to_join_timer
        self.callBackFunction = callBackHandleMessage
        self.callBackGetDevice = callBackGetDevice
        self.callBackUpdDevice = callBackUpdDevice
        self.callBackBackup = callBackBackup
        self.HardwareID = HardwareID

        await asyncio.sleep( 3 )

        try:
            await self.connect()
            await asyncio.sleep( 1 )
            await self.initialize(auto_form=True, force_form=force_form)
        except Exception as e:
            LOGGER.error("Couldn't start application", exc_info=e)
            await self.shutdown()
            raise

        # Populate and get the list of active devices.
        # This will allow the plugin if needed to update the IEEE -> NwkId
        await self.load_network_info( load_devices=True )
        network_info = self.state.network_info

        # deConz doesn't have such capabilities to provided list of paired devices.
        # LOGGER.debug("startup Network Info: %s" %str(network_info))
        # self.callBackFunction(build_plugin_8015_frame_content( self, network_info))

        # Trigger Version payload to plugin
        deconz_model = self.get_device(nwk=t.NWK(0x0000)).model
        deconz_manuf = self.get_device(nwk=t.NWK(0x0000)).manufacturer
        LOGGER.debug("startup in AppDeconz - Model: %s Manuf: %s" %(
            deconz_model, deconz_manuf))
        
        deconz_version = "%08x" %self.version
        deconz_major = deconz_version[:4]
        deconz_minor = deconz_version[4:8]
        LOGGER.debug("startup in AppDeconz - build 8010 %s %08x %s" %(
            deconz_version, self.version, deconz_major + deconz_minor))
        
        if deconz_model == "ConBee II":
            self.callBackFunction(build_plugin_8010_frame_content("40", deconz_major, deconz_minor))
        elif deconz_model == "RaspBee II":
            self.callBackFunction(build_plugin_8010_frame_content("41", deconz_major, deconz_minor))
        elif deconz_model == "RaspBee":
            self.callBackFunction(build_plugin_8010_frame_content("42", deconz_major, deconz_minor))
        elif deconz_model == "ConBee":
            self.callBackFunction(build_plugin_8010_frame_content("43", deconz_major, deconz_minor))
        else:
            LOGGER.info("Unknow Zigbee CIE from %s %s" %( deconz_manuf, deconz_model))
            self.callBackFunction(build_plugin_8010_frame_content("99", deconz_major, deconz_minor))
            
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup( await self.backups.create_backup(load_devices=self.pluginconf.pluginConf["BackupFullDevices"]))


    async def shutdown(self) -> None:
        """Shutdown controller."""
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup(await self.backups.create_backup(load_devices=True))
        await self.disconnect()

    async def register_endpoints(self):
        await self._register_endpoints()  

    async def _register_endpoints(self):
        """
        Registers all necessary endpoints.
        The exact order in which this method is called depends on the radio module.
        """

        LOGGER.info("Adding Endpoint 0x%x" %0x01)
        await self.add_endpoint(
            zdo_types.SimpleDescriptor(
                endpoint=1,
                profile=zigpy.profiles.zha.PROFILE_ID,
                device_type=zigpy.profiles.zha.DeviceType.IAS_CONTROL,
                device_version=0b0000,
                input_clusters=[
                    zigpy.zcl.clusters.general.Basic.cluster_id,
                    zigpy.zcl.clusters.general.OnOff.cluster_id,
                    zigpy.zcl.clusters.general.Time.cluster_id,
                    zigpy.zcl.clusters.general.Ota.cluster_id,
                    zigpy.zcl.clusters.security.IasAce.cluster_id,
                ],
                output_clusters=[
                    zigpy.zcl.clusters.general.PowerConfiguration.cluster_id,
                    zigpy.zcl.clusters.general.PollControl.cluster_id,
                    zigpy.zcl.clusters.security.IasZone.cluster_id,
                    zigpy.zcl.clusters.security.IasWd.cluster_id,
                ],
            )
        )

        LOGGER.info("Adding Endpoint 0x%x" %0x02)
        await self.add_endpoint(
            zdo_types.SimpleDescriptor(
                endpoint=2,
                profile=zigpy.profiles.zll.PROFILE_ID,
                device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                device_version=0b0000,
                input_clusters=[zigpy.zcl.clusters.general.Basic.cluster_id],
                output_clusters=[],
            )
        )

        # Livolo Switch 0x08
        if "Livolo" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Livolo"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x08)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x08,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        zigpy.zcl.clusters.general.OnOff.cluster_id,
                        ],
                    output_clusters=[
                        zigpy.zcl.clusters.security.IasZone.cluster_id,
                        ],
                )
            )

        # Wiser Legacy 0x0b
        if "Wiser" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Wiser"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x0b)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x0b,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        ],
                    output_clusters=[
                        ],
                )
            )

        # Orvibo 0x0a
        if "Orvibo" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Orvibo"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x0a)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x0a,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        ],
                    output_clusters=[
                        ],
                )
            )

        # Terncy 0x6e
        if "Terncy" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Terncy"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x6e)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x6e,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        ],
                    output_clusters=[
                        ],
                )
            )

        # Konke 0x15
        if "Konke" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Konke"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x15)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x15,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        zigpy.zcl.clusters.general.OnOff.cluster_id,
                        ],
                    output_clusters=[
                        zigpy.zcl.clusters.security.IasZone.cluster_id,
                        ],
                )
            )

        # Wiser2 (new generation 0x03)
        if "Wiser2" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Wiser2"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x03)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x03,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        ],
                    output_clusters=[
                        ],
                )
            )
        
    def get_device(self, ieee=None, nwk=None):
        return Classes.ZigpyTransport.AppGeneric.get_device(self, ieee, nwk)

    def handle_join(self, nwk: t.NWK, ieee: t.EUI64, parent_nwk: t.NWK) -> None:
        return Classes.ZigpyTransport.AppGeneric.handle_join(self, nwk, ieee, parent_nwk)
            
    def get_device_ieee(self, nwk):
        return Classes.ZigpyTransport.AppGeneric.get_device_ieee(self, nwk)

    def handle_leave(self, nwk, ieee):
        Classes.ZigpyTransport.AppGeneric.handle_leave(self, nwk, ieee)

    def handle_message(
        self,
        sender: zigpy.device.Device,
        profile: int,
        cluster: int,
        src_ep: int,
        dst_ep: int,
        message: bytes,
    ) -> None:
        return Classes.ZigpyTransport.AppGeneric.handle_message(self,sender,profile,cluster,src_ep,dst_ep,message)                

    async def set_zigpy_tx_power(self, power):
        pass
        #await self._api.set_tx_power(power)

    async def set_led(self, mode):
        pass
        #await self._api.set_led(mode)

    async def set_certification(self, mode):
        pass
        #await self._api.set_certification(mode)

    async def get_time_server(self):
        pass
        #await self._api.get_time_server()

    async def set_time_server(self, newtime):
        pass
        #await self._api.set_time()

    async def get_firmware_version(self):
        pass

    async def erase_pdm(self):
        pass

    async def soft_reset(self):
        pass

    async def set_extended_pan_id(self, extended_pan_ip): 
        pass 

    async def set_channel(self):
        pass        

    async def remove_ieee(self, ieee):
        pass

    async def coordinator_backup( self ):
        if self.config[zigpy_conf.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup(await self.backups.create_backup(load_devices=self.pluginconf.pluginConf["BackupFullDevices"]))

    def is_bellows(self):
        return False
    def is_znp(self):
        return False
    def is_deconz(self):
        return True
