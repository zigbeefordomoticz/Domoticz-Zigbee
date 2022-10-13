#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: ConfigureReporting.py

    Description: Configure Reporting of all connected object, based on their corresponding cluster

"""


import time

from Modules.bindings import bindDevice, unbindDevice
from Modules.paramDevice import get_device_config_param
from Modules.pluginDbAttributes import (STORE_CONFIGURE_REPORTING,
                                        STORE_CUSTOM_CONFIGURE_REPORTING,
                                        STORE_READ_CONFIGURE_REPORTING)
from Modules.tools import (deviceconf_device, get_isqn_datastruct,
                           get_list_isqn_attr_datastruct,
                           get_list_isqn_int_attr_datastruct,
                           getClusterListforEP, is_ack_tobe_disabled,
                           is_attr_unvalid_datastruct, is_bind_ep, is_fake_ep,
                           is_time_to_perform_work, mainPoweredDevice,
                           reset_attr_datastruct, set_isqn_datastruct,
                           set_status_datastruct, set_timestamp_datastruct)
from Modules.zigateConsts import (MAX_LOAD_ZIGATE, SIZE_DATA_TYPE, ZIGATE_EP,
                                  CFG_RPT_ATTRIBUTESbyCLUSTERS, analog_value,
                                  composite_value, discrete_value)
from Zigbee.zclCommands import (zcl_configure_reporting_requestv2,
                                zcl_read_report_config_request)

from Classes.ZigateTransport.sqnMgmt import (TYPE_APP_ZCL,
                                             sqn_get_internal_sqn_from_app_sqn)

CONFIGURE_REPORT_PERFORM_TIME = 21  # Reenforce will be done each xx hours


def get_max_cfg_rpt_attribute_value( self, nwkid=None):
    
    # This is about Read Configuration Reporting from a device
    if nwkid:  
        read_configuration_report_chunk = get_device_config_param( self, nwkid, "ConfigurationReportChunk")
    
    if read_configuration_report_chunk:
        return get_device_config_param( self, nwkid, "ConfigurationReportChunk")
    return self.pluginconf.pluginConf["ConfigureReportingChunk"]


class ConfigureReporting:
    def __init__(
        self,
        zigbee_communitation,
        PluginConf,
        DeviceConf,
        ZigateComm,
        ListOfDevices,
        Devices,
        log,
        busy,
        FirmwareVersion,
        IEEE2NWK,
        ZigateIEEE,
    ):

        self.zigbee_communication = zigbee_communitation
        self.pluginconf = PluginConf
        self.DeviceConf = DeviceConf
        self.ControllerLink = ZigateComm
        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.log = log
        self.busy = busy
        self.FirmwareVersion = FirmwareVersion

        # Needed for bind
        self.IEEE2NWK = IEEE2NWK
        self.ControllerIEEE = ZigateIEEE

        # Local
        self.target = []

    def logging(self, logType, message, nwkid=None, context=None):
        self.log.logging("ConfigureReporting", logType, message, nwkid, context)

    # Commands
    
    def processConfigureReporting(self, NwkId=None, batch=False):

        if NwkId:
            configure_reporting_for_one_device( self, NwkId, batch, )
            return
        
        for key in list(self.ListOfDevices.keys()):
            if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
                self.logging(
                    "Debug",
                    f"configureReporting - skip configureReporting for now ... system too busy ({self.busy}/{self.ControllerLink.loadTransmit()}) for {NwkId}",
                    nwkid=NwkId,
                )
                return  # Will do at the next round
            configure_reporting_for_one_device(self, key, True)

    def cfg_reporting_on_demand(self, nwkid):
        # Remove Cfg Rpt tracking attributes
        if STORE_CONFIGURE_REPORTING in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid][STORE_CONFIGURE_REPORTING]
        configure_reporting_for_one_device(self, nwkid, False)

    def prepare_and_send_configure_reporting( self, key, Ep, cluster_configuration, cluster, direction, manufacturer_spec, manufacturer, ListOfAttributesToConfigure ):

        # Create the list of Attribute reporting configuration for a specific cluster
        # Finally send the command
        self.logging("Debug", f"------ prepare_and_send_configure_reporting - key: {key} ep: {Ep} cluster: {cluster} Cfg: {cluster_configuration}", nwkid=key)

        maxAttributesPerRequest = get_max_cfg_rpt_attribute_value( self, nwkid=key)

        attribute_reporting_configuration = []
        for attr in ListOfAttributesToConfigure:
            attrType = cluster_configuration[attr]["DataType"]
            #minInter = cluster_configuration[attr]["MinInterval"]
            #maxInter = cluster_configuration[attr]["MaxInterval"]
            #timeOut = cluster_configuration[attr]["TimeOut"]
            #chgFlag = cluster_configuration[attr]["Change"]

            if analog_value(int(attrType, 16)):
                # Analog values: For attributes with 'analog' data type (see 2.6.2), 
                # the "rptChg" has the same data type as the attribute. 
                # The sign (if any) of the reportable change field is ignored.
                attribute_reporting_record = {
                    "Attribute": attr,
                    "DataType": attrType,
                    "minInter": cluster_configuration[attr]["MinInterval"],
                    "maxInter": cluster_configuration[attr]["MaxInterval"],
                    "rptChg": cluster_configuration[attr]["Change"],
                    "timeOut": cluster_configuration[attr]["TimeOut"],
                }
            elif discrete_value(int(attrType, 16)):
                # Discrete value: For attributes of 'discrete' data type (see 2.6.2),
                # "rptChg" field is omitted.
                attribute_reporting_record = {
                    "Attribute": attr,
                    "DataType": attrType,
                    "minInter": cluster_configuration[attr]["MinInterval"],
                    "maxInter": cluster_configuration[attr]["MaxInterval"],
                    "timeOut": cluster_configuration[attr]["TimeOut"],
                }
            elif composite_value(int(attrType, 16)):
                # Composite value: assumed "rptChg" is omitted
                attribute_reporting_record = {
                    "Attribute": attr,
                    "DataType": attrType,
                    "minInter": cluster_configuration[attr]["MinInterval"],
                    "maxInter": cluster_configuration[attr]["MaxInterval"],
                    "timeOut": cluster_configuration[attr]["TimeOut"],
                }
            else:
                self.logging(
                    "Error",
                    f"--------> prepare_and_send_configure_reporting - Unexpected Data Type: Cluster: {cluster} Attribut: {attr} DataType: {attrType}",
                )
                continue

            attribute_reporting_configuration.append(attribute_reporting_record)

            if len(attribute_reporting_configuration) == maxAttributesPerRequest:
                self.send_configure_reporting_attributes_set( key, ZIGATE_EP, Ep, cluster, direction, manufacturer_spec, manufacturer, attribute_reporting_configuration, )
                # Reset the Lenght to 0
                attribute_reporting_configuration = []

        # Send remaining records
        if attribute_reporting_configuration:
            self.send_configure_reporting_attributes_set( key, ZIGATE_EP, Ep, cluster, direction, manufacturer_spec, manufacturer, attribute_reporting_configuration, )

    def send_configure_reporting_attributes_set(
        self,
        key,
        ZIGATE_EP,
        Ep,
        cluster,
        direction,
        manufacturer_spec,
        manufacturer,
        attribute_reporting_configuration,
    ):
        self.logging(
            "Debug",
            f"----------> send_configure_reporting_attributes_set Reporting {key}/{Ep} on cluster {cluster} Len: {len(attribute_reporting_configuration)} Attribute List: {str(attribute_reporting_configuration)}",
            nwkid=key,
        )

        i_sqn = zcl_configure_reporting_requestv2(
            self,
            key,
            ZIGATE_EP,
            Ep,
            cluster,
            direction,
            manufacturer_spec,
            manufacturer,
            attribute_reporting_configuration,
            is_ack_tobe_disabled(self, key),
        )
        for x in attribute_reporting_configuration:
            set_isqn_datastruct(self, STORE_CONFIGURE_REPORTING, key, Ep, cluster, x["Attribute"], i_sqn)

    def read_configure_reporting_response(self, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus):
        # This is the response receive after a Configuration Reporting request
        self.logging( "Debug", "read_configure_reporting_response %s %s %s %s %s" %(MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus))
        
        if MsgAttributeId:
            set_status_datastruct( self, STORE_CONFIGURE_REPORTING, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus, )
            if MsgStatus == "00":
                self.read_report_configure_request( MsgSrcAddr , MsgSrcEp, MsgClusterId, list(get_list_isqn_int_attr_datastruct(self, STORE_CONFIGURE_REPORTING, MsgSrcAddr, MsgSrcEp, MsgClusterId)) )
            else:        
                self.logging(
                    "Debug",
                    f"Configure Reporting response - ClusterID: {MsgClusterId}/{MsgAttributeId}, MsgSrcAddr: {MsgSrcAddr}, MsgSrcEp:{MsgSrcEp} , Status: {MsgStatus}",
                    nwkid=MsgSrcAddr,
                )
            return
                
        # We got a global status for all attributes requested in this command
        # We need to find the Attributes related to the i_sqn
        i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
        self.logging("Debug", "------- - i_sqn: %0s e_sqn: %s" % (i_sqn, MsgSQN),nwkid=MsgSrcAddr )
        for matchAttributeId in list(get_list_isqn_attr_datastruct(self, STORE_CONFIGURE_REPORTING, MsgSrcAddr, MsgSrcEp, MsgClusterId)):
            if ( get_isqn_datastruct( self, STORE_CONFIGURE_REPORTING, MsgSrcAddr, MsgSrcEp, MsgClusterId, matchAttributeId, ) != i_sqn ):
                continue
            self.logging("Debug", f"------- - Sqn matches for Attribute: {matchAttributeId}",nwkid=MsgSrcAddr)
            set_status_datastruct( self, STORE_CONFIGURE_REPORTING, MsgSrcAddr, MsgSrcEp, MsgClusterId, matchAttributeId, MsgStatus, )
            if MsgStatus != "00":
                self.logging(
                    "Debug",
                    f"Configure Reporting response - ClusterID: {MsgClusterId}/{matchAttributeId}, MsgSrcAddr: {MsgSrcAddr}, MsgSrcEp:{MsgSrcEp} , Status: {MsgStatus}",
                    nwkid=MsgSrcAddr,
                )
        # As we receive the result of a Configure Reporting, lets do a read               
        self.read_report_configure_request( MsgSrcAddr , MsgSrcEp, MsgClusterId, list(get_list_isqn_int_attr_datastruct(self, STORE_CONFIGURE_REPORTING, MsgSrcAddr, MsgSrcEp, MsgClusterId)) )

    def check_configure_reporting(self, checking_period):
        # This is call on a regular basic, and will trigger a Read Configuration reporting if needed.
        for nwkid in list(self.ListOfDevices.keys()):
            if deviceconf_device(self, nwkid):
                return self.check_configuration_reporting_for_device( nwkid, checking_period=checking_period)
                
    def check_configuration_reporting_for_device( self, NwkId, checking_period=None, force=False):
        # If return True an action has been performed
        # If return False no action performed
        
        self.logging("Debug", f"check_configuration_reporting_for_device - {NwkId} Period: {checking_period} force: {force}", nwkid=NwkId)
        
        if force:
            return self.read_reporting_configuration_request(NwkId, force=force)

        if not deviceconf_device(self, NwkId):
            self.logging("Debug", "     Not a plugin certified device", nwkid=NwkId)
            return False
        
        if not mainPoweredDevice(self, NwkId):
            self.logging("Debug", "     Not a main powered device", nwkid=NwkId)
            return False    # Not Main Powered

        if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
            self.logging("Debug", "     System busy", nwkid=NwkId)
            return False    # Will do at the next round

        if STORE_READ_CONFIGURE_REPORTING not in self.ListOfDevices[ NwkId ]:
            self.logging("Debug", "     STORE_READ_CONFIGURE_REPORTING not available", nwkid=NwkId)
            return self.read_reporting_configuration_request(NwkId)

        if "TimeStamp" not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]:
            self.logging("Debug", "     TimeStamp not available", nwkid=NwkId)
            return self.read_reporting_configuration_request(NwkId)

        if time.time() > (self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["TimeStamp"] + checking_period):
            self.logging("Debug", "     Requesting a read_reporting_configuration_request due to TimeStamp", nwkid=NwkId)
            return self.read_reporting_configuration_request(NwkId)
        
        #self.logging("Log", "     nocriteria matches %s %s" %(
        #    time.time(), (self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["TimeStamp"] + checking_period)))
        return False
        
    def read_reporting_configuration_request(self, Nwkid, force=False ):
        self.logging("Debug", "read_reporting_configuration_request %s %s" %(Nwkid, force), nwkid=Nwkid)
        
        if Nwkid == "0000":
            return False
        if Nwkid not in self.ListOfDevices:
            self.logging("Debug", f"read_reporting_configuration_request - Unknown key: {Nwkid}", nwkid=Nwkid)
            return False
        if "Status" not in self.ListOfDevices[Nwkid]:
            self.logging("Debug", "read_reporting_configuration_request - no 'Status' flag for device %s !!!" % Nwkid, nwkid=Nwkid)
            return False
        if self.ListOfDevices[Nwkid]["Status"] != "inDB":
            self.logging("Debug", "read_reporting_configuration_request - 'Status' flag for device %s is %s" % (Nwkid,self.ListOfDevices[Nwkid]["Status"]), nwkid=Nwkid)
            return False
        if "Health" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Health"] == "Not Reachable":
            self.logging("Debug", "read_reporting_configuration_request - %s is Not Reachable !!" % (Nwkid), nwkid=Nwkid)
            return False
        if STORE_CONFIGURE_REPORTING not in self.ListOfDevices[ Nwkid ]:
            self.logging("Debug", "read_reporting_configuration_request - %s has no %s record!!" % (Nwkid, STORE_CONFIGURE_REPORTING), nwkid=Nwkid)
            return False
        if "Ep" not in self.ListOfDevices[ Nwkid ][STORE_CONFIGURE_REPORTING]:
            # Most likely the record has been removed. So let do nothing here
            self.logging("Debug", "read_reporting_configuration_request - %s  %s as no Ep entry!!" % (Nwkid, STORE_CONFIGURE_REPORTING), nwkid=Nwkid)
            return False

        if (
            STORE_READ_CONFIGURE_REPORTING not in self.ListOfDevices[ Nwkid ]
            or "Ep" not in self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING]
        ):       
            self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING] = { 
                "Ep": {},
                "Request" : {
                    "Status": "Requested",
                    "Retry": 0,
                    "TimeStamp": 0
                }}

        if "Request" not in self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING]: 
            self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING]["Request"] = {
                "Status": "Requested",
                "Retry": 0,
                "TimeStamp": 0
            }

        if ( 
            not force 
            and (
                time.time() < (self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING]["Request"]["TimeStamp"] + 60)
                or self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING]["Request"]["Retry"] > 3
            )
        ):
            # Too early, already a request in progress
            self.logging("Debug", "read_reporting_configuration_request     Too early .... %s" %(self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING]["Request"]["Retry"]), nwkid=Nwkid)
            return False
        
        wip_flag = False
        for epout in self.ListOfDevices[ Nwkid ][STORE_CONFIGURE_REPORTING]["Ep"]:
            if is_fake_ep(self, Nwkid, epout):
                continue
            
            for cluster_id in self.ListOfDevices[ Nwkid ][STORE_CONFIGURE_REPORTING]["Ep"][ epout ]:
                attribute_lst = []
                for attribute in list(self.ListOfDevices[Nwkid][STORE_CONFIGURE_REPORTING]["Ep"][epout][cluster_id]["Attributes"]):
                    if attribute is None:
                        self.logging("Debug", "read_reporting_configuration_request attribute %s ================================== is None !!!" %cluster_id)
                        continue
                    attribute_lst.append( int(attribute, 16) )
                if attribute_lst:
                    zcl_read_report_config_request( self, Nwkid, ZIGATE_EP, epout, cluster_id, "00", "0000", attribute_lst, is_ack_tobe_disabled(self, Nwkid),)
                    wip_flag = True
                else:
                    continue
                    # We do not find any atrributes for the cluster !!!

        if wip_flag:
            self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING]["Request"]["Retry"] += 1
            self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING]["Request"]["TimeStamp"] = time.time()

        return wip_flag

    def read_report_configure_request(self, nwkid, epout, cluster_id, attribute_list, manuf_specific="00", manuf_code="0000"):

        maxAttributesPerRequest = get_max_cfg_rpt_attribute_value( self, nwkid=nwkid)

        if attribute_list and len( attribute_list ) <= maxAttributesPerRequest:
            zcl_read_report_config_request( self, nwkid, ZIGATE_EP, epout, cluster_id, manuf_specific, manuf_code, attribute_list, is_ack_tobe_disabled(self, nwkid),)
            return
        
        self.logging("Debug", "read_report_configure_request %s/%s need to break attribute list into chunk %s" %( nwkid, epout, str(attribute_list)))
        idx = 0
        while idx < len(attribute_list):
            end = idx + maxAttributesPerRequest
            if idx + maxAttributesPerRequest > len(attribute_list):
                end = len(attribute_list)
            self.logging("Debug", "      chunk %s" %str( attribute_list[ idx : end ]))
            if attribute_list[ idx : end ]:
                zcl_read_report_config_request( self, nwkid, ZIGATE_EP, epout, cluster_id, manuf_specific, manuf_code, attribute_list[ idx : end ], is_ack_tobe_disabled(self, nwkid),)
            idx = end

    def read_report_configure_response(self, MsgData, MsgLQI):
        
        if self.zigbee_communication == "zigpy":
            return read_report_configure_response_zigpy(self, MsgData, MsgLQI)
        return read_report_configure_response_zigate(self, MsgData, MsgLQI)
    
    def retreive_configuration_reporting_definition(self, NwkId):
    
        if STORE_CUSTOM_CONFIGURE_REPORTING in self.ListOfDevices[NwkId]:
            self.logging("Debug", f"retreive_configuration_reporting_definition - returning {self.ListOfDevices[NwkId][ STORE_CUSTOM_CONFIGURE_REPORTING ]}", nwkid=NwkId)
            return self.ListOfDevices[NwkId][ STORE_CUSTOM_CONFIGURE_REPORTING ]

        if (
            "Model" in self.ListOfDevices[NwkId]
            and self.ListOfDevices[NwkId]["Model"] != {}
            and self.ListOfDevices[NwkId]["Model"] in self.DeviceConf
            and STORE_CONFIGURE_REPORTING in self.DeviceConf[self.ListOfDevices[NwkId]["Model"]]
        ):
            self.logging("Debug", f"retreive_configuration_reporting_definition - returning {self.DeviceConf[self.ListOfDevices[NwkId]['Model']][STORE_CONFIGURE_REPORTING]}", nwkid=NwkId)
            
            return self.DeviceConf[self.ListOfDevices[NwkId]["Model"]][STORE_CONFIGURE_REPORTING]

        self.logging("Debug", f"retreive_configuration_reporting_definition - returning {CFG_RPT_ATTRIBUTESbyCLUSTERS}", nwkid=NwkId)
        
        return CFG_RPT_ATTRIBUTESbyCLUSTERS

    def check_and_redo_configure_reporting_if_needed( self, Nwkid):
        self.logging("Debug", f"check_and_redo_configure_reporting_if_needed - NwkId: {Nwkid} ", nwkid=Nwkid)

        if not deviceconf_device(self, Nwkid):
            return False
        
        if STORE_CONFIGURE_REPORTING not in self.ListOfDevices[ Nwkid ] or self.ListOfDevices[ Nwkid ][STORE_CONFIGURE_REPORTING] in ( '', {}): 
            # we should redo the configure reporting as we don't have the Configuration Reporting 
            self.logging("Debug", f"check_and_redo_configure_reporting_if_needed - NwkId: {Nwkid} not found {STORE_CONFIGURE_REPORTING} ", nwkid=Nwkid)
            configure_reporting_for_one_device( self, Nwkid, batchMode=True)    
            return True

        if ( 
            STORE_READ_CONFIGURE_REPORTING not in self.ListOfDevices[ Nwkid ] 
            or self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING] in ( '', {})
            or "Request" in self.ListOfDevices[ Nwkid ][STORE_READ_CONFIGURE_REPORTING] 
        ):
            # we should do a read as it looks missing
            self.logging("Debug", f"check_and_redo_configure_reporting_if_needed - NwkId: {Nwkid} not found {STORE_READ_CONFIGURE_REPORTING} ", nwkid=Nwkid)
            self.read_reporting_configuration_request( Nwkid )
            return True

        configuration_reporting = self.retreive_configuration_reporting_definition( Nwkid)
        wip_flap = False
        for _ep in self.ListOfDevices[ Nwkid ]["Ep"]:
            self.logging("Debug", f"-- check_and_redo_configure_reporting_if_needed - NwkId: {Nwkid} {_ep}", nwkid=Nwkid)

            if is_fake_ep(self, Nwkid, _ep):
                continue

            for _cluster in self.ListOfDevices[ Nwkid ]["Ep"][ _ep ]:
                if _cluster not in configuration_reporting:
                    continue
                if "Attributes" not in configuration_reporting[ _cluster ]:
                    continue

                self.logging("Debug", f"---- check_and_redo_configure_reporting_if_needed - NwkId: {Nwkid} {_ep} {_cluster}", nwkid=Nwkid)
                cluster_configuration = configuration_reporting[ _cluster ]["Attributes"]
                self.logging("Debug", f"---- check_and_redo_configure_reporting_if_needed - NwkId: {Nwkid} {_ep} {_cluster} ==> {cluster_configuration}", nwkid=Nwkid)
                for attribut in cluster_configuration:
                    self.logging("Debug", f"------ check_and_redo_configure_reporting_if_needed - NwkId: {Nwkid} {_ep} {_cluster} {attribut}", nwkid=Nwkid)
                    attribute_current_configuration = retreive_read_configure_reporting_record(self, Nwkid, Ep=_ep, ClusterId=_cluster, AttributeId=attribut)
                    if attribute_current_configuration is None:
                        self.logging("Debug", f"-------- check_and_redo_configure_reporting_if_needed - NwkId: {Nwkid} {_ep} {_cluster} {attribut} return None !", nwkid=Nwkid)
                        # Better to check if we didn't have an error before
                        if is_valid_cluster_attribute( self, Nwkid, _ep, _cluster, attribut):
                            configure_reporting_for_one_cluster(self, Nwkid, _ep, _cluster, True, cluster_configuration)
                        continue
                    self.logging("Debug", f"-------- check_and_redo_configure_reporting_if_needed - NwkId: {Nwkid} {_ep} {_cluster} {attribut} ==> {attribute_current_configuration}", nwkid=Nwkid)

                    if "Status" in attribute_current_configuration and attribute_current_configuration["Status"] != "00":
                        if attribute_current_configuration["Status"] == '8b':
                            configure_reporting_for_one_cluster(self, Nwkid, _ep, _cluster, True, cluster_configuration)
                            # There is no need to continue as we have requested a Cluster
                            wip_flap = True
                            cluster_update = True
                            break
 
                        self.logging("Debug", f"------ check_and_redo_configure_reporting_if_needed invalid status {attribute_current_configuration['Status']}", nwkid=Nwkid)
                        continue
                        
                    self.logging("Debug", f"------ check_and_redo_configure_reporting_if_needed - {Nwkid} {_cluster} {attribut} Checking {attribute_current_configuration} versus {cluster_configuration[attribut]} " , nwkid=Nwkid)
                    cluster_update = False
                    for x in ( "Change", "MinInterval", "MaxInterval"):
                        if x not in attribute_current_configuration:
                            continue
                        if x == "Change" and not analog_value(int(attribute_current_configuration['DataType'], 16)):
                            continue
                        if (
                            attribute_current_configuration[x] != '' 
                            and cluster_configuration[attribut][x] != ''
                            and int(attribute_current_configuration[x],16) == int(cluster_configuration[attribut][x],16)
                        ):
                            continue
                        
                        if not wip_flap:
                            self.logging( "Status", f"------ We have detected a miss configuration reports for device {Nwkid} on ep {_ep} and cluster {_cluster}" ,nwkid=Nwkid)
                        
                        self.logging( "Status", f" - Attribut {attribut} request to force a Configure Reporting due to field {x} '{attribute_current_configuration[ x ]}' != '{cluster_configuration[ attribut ][ x]}'", nwkid=Nwkid)
                        configure_reporting_for_one_cluster(self, Nwkid, _ep, _cluster, True, cluster_configuration)
                        wip_flap = True
                        cluster_update = True
                        break   # No need to check for an other difference
                    if cluster_update:
                        # We need to move to the next cluster, as we have requested
                        # a cluster cfg reporting update
                        break
        return wip_flap
           
####

def is_valid_cluster_attribute( self, Nwkid, _ep, _cluster, attribut):
    
    if Nwkid not in self.ListOfDevices:
        return False

    if _ep in self.ListOfDevices[Nwkid]["Ep"] and _cluster in self.ListOfDevices[Nwkid]["Ep"][ _ep ] and "ClusterType" not in self.ListOfDevices[Nwkid]["Ep"][ _ep ]:
        # Check if we are expecting 
        return False

    if STORE_READ_CONFIGURE_REPORTING in self.ListOfDevices[Nwkid]:
        return True
    if "Ep" not in self.ListOfDevices[Nwkid][STORE_READ_CONFIGURE_REPORTING]:
        return True
    if _ep not in self.ListOfDevices[Nwkid][STORE_READ_CONFIGURE_REPORTING]["Ep"]:
        return True
    if _cluster not in self.ListOfDevices[Nwkid][STORE_READ_CONFIGURE_REPORTING]["Ep"][_ep]:
        return True
    if attribut not in self.ListOfDevices[Nwkid][STORE_READ_CONFIGURE_REPORTING]["Ep"][_ep][_cluster]:
        return True
    if "Status" not in self.ListOfDevices[Nwkid][STORE_READ_CONFIGURE_REPORTING]["Ep"][_ep][_cluster][attribut]:
        return True
    
    if self.ListOfDevices[Nwkid][STORE_READ_CONFIGURE_REPORTING]["Ep"][_ep][_cluster][attribut]["Status"] == '8b':
        # No configuration report setup
        return True
    
    elif self.ListOfDevices[Nwkid][STORE_READ_CONFIGURE_REPORTING]["Ep"][_ep][_cluster][attribut]["Status"] != '00': 
        self.logging( "Log", "is_valid_cluster_attribute - %s/%s Unvalid Cluster/attribut %s/%s %s" %(
            Nwkid, _ep, _cluster, attribut, self.ListOfDevices[Nwkid][STORE_READ_CONFIGURE_REPORTING]["Ep"][_ep][_cluster][attribut]["Status"]))
        return False
    
    return True

 
def configure_reporting_for_one_device(self, key, batchMode):
    self.logging("Debug", f"configure_reporting_for_one_device - key: {key} batchMode: {batchMode}", nwkid=key)
    # Let's check that we can do a Configure Reporting. Only during the pairing process (NWKID is provided) or we are on the Main Power
    if key == "0000":
        return
    if key not in self.ListOfDevices:
        self.logging("Debug", f"processConfigureReporting - Unknown key: {key}", nwkid=key)
        return
    if "Status" not in self.ListOfDevices[key]:
        self.logging("Debug", "processConfigureReporting - no 'Status' flag for device %s !!!" % key, nwkid=key)
        return
    if self.ListOfDevices[key]["Status"] != "inDB":
        return

    if batchMode and not mainPoweredDevice(self, key):
        return  # Not Main Powered!

    if batchMode and "Health" in self.ListOfDevices[key] and self.ListOfDevices[key]["Health"] == "Not Reachable":
        return

    cfgrpt_configuration = self.retreive_configuration_reporting_definition( key)

    self.logging("Debug", f"configure_reporting_for_one_device - processing {key} with {cfgrpt_configuration}", nwkid=key)
    
    for Ep in self.ListOfDevices[key]["Ep"]:
        configure_reporting_for_one_endpoint(self, key, Ep, batchMode, cfgrpt_configuration)


def configure_reporting_for_one_endpoint(self, key, Ep, batchMode, cfgrpt_configuration):
    self.logging("Debug", f"-- configure_reporting_for_one_endpoint - key: {key} ep: {Ep} batchMode: {batchMode} Cfg: {cfgrpt_configuration}", nwkid=key)
    
    if is_fake_ep(self, key, Ep):
        self.logging("Debug", f"--> configure_reporting_for_one_endpoint - Fake Ep {key}/{Ep} skiping", nwkid=key)
        return

    if not is_bind_ep(self, key, Ep):
        self.logging("Debug", f"--> configure_reporting_for_one_endpoint - Not Binding ep {key}/{Ep} skiping", nwkid=key)
        return

    if cfgrpt_configuration == {}:
        self.logging("Debug", f"--> configure_reporting_for_one_endpoint - {key}/{Ep} Empty cfgrt_configuration record", nwkid=key)
        return
    
    clusterList = getClusterListforEP(self, key, Ep)
    self.logging("Debug", f"--> configure_reporting_for_one_endpoint - processing {key}/{Ep} ClusterList: {clusterList}", nwkid=key)

    now = time.time()
    for cluster in clusterList:
        if cluster not in cfgrpt_configuration:
            self.logging("Debug", f"----> configure_reporting_for_one_endpoint - processing {key}/{Ep} {cluster} not in {cfgrpt_configuration}", nwkid=key)
            continue

        if not do_we_have_to_do_the_work(self, key, Ep, cluster):
            self.logging("Debug", f"----> configure_reporting_for_one_endpoint - Not Binding ep {key}/{Ep} skiping", nwkid=key)
            continue

        # Configure Reporting must be done because:
        # (1) 'ConfigureReporting' do not exist
        # (2) 'ConfigureReporting' is empty
        # (3) if checkConfigurationReporting is enabled and it is time to do the work
        if (
            batchMode 
            and STORE_CONFIGURE_REPORTING in self.ListOfDevices[key] 
            and len(self.ListOfDevices[key][STORE_CONFIGURE_REPORTING]) != 0
            and Ep in self.ListOfDevices[key][STORE_CONFIGURE_REPORTING]["Ep"]
            and cluster in self.ListOfDevices[key][STORE_CONFIGURE_REPORTING]["Ep"][Ep]
        ):
            if self.pluginconf.pluginConf["checkConfigurationReporting"]:
                if not is_time_to_perform_work( self, STORE_CONFIGURE_REPORTING, key, Ep, cluster, now, (CONFIGURE_REPORT_PERFORM_TIME * 3600), ):
                    self.logging("Debug", f"----> configure_reporting_for_one_endpoint Not time to perform  {key}/{Ep} - {cluster}", nwkid=key)
                    continue
                self.logging("Debug", f"----> configure_reporting_for_one_endpoint it is time to work  {key}/{Ep} - {cluster}", nwkid=key) 
            
            else:
                self.logging(
                    "Debug",
                    "----> configure_reporting_for_one_endpoint ['checkConfigurationReporting']: %s then skip" % self.pluginconf.pluginConf["checkConfigurationReporting"],
                    nwkid=key
                )
                continue
            
        self.logging("Debug", f"----> configure_reporting_for_one_endpoint it is time to work .....  {key}/{Ep} - {cluster}", nwkid=key) 

        if batchMode and (self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE):
            self.logging(
                "Debug",
                f"----> configure_reporting_for_one_endpoint - {key} skip configureReporting for now ... system too busy ({self.busy}/{self.ControllerLink.loadTransmit()}) for {key}",
                nwkid=key,
            )
            return  # Will do at the next round

        self.logging("Debug", f"----> configure_reporting_for_one_endpoint - requested for device: {key} on Cluster: {cluster}", nwkid=key)

        # If NWKID is not None, it means that we are asking a ConfigureReporting for a specific device
        # Which happens on the case of New pairing, or a re-join
        

        if "Attributes" not in cfgrpt_configuration[ cluster ]:
            self.logging("Debug", f"----> configure_reporting_for_one_endpoint - for device: {key} on Cluster: {cluster} no Attributes key on {cfgrpt_configuration[ cluster ]}", nwkid=key)
            continue
        
        set_timestamp_datastruct(self, STORE_CONFIGURE_REPORTING, key, Ep, cluster, time.time())
        configure_reporting_for_one_cluster(self, key, Ep, cluster, batchMode, cfgrpt_configuration[cluster]["Attributes"])


def configure_reporting_for_one_cluster(self, key, Ep, cluster, batchMode, cluster_configuration):
    self.logging("Debug", f"---- configure_reporting_for_one_cluster - key: {key} ep: {Ep} cluster: {cluster} Cfg: {cluster_configuration}", nwkid=key)

    manufacturer = "0000"
    manufacturer_spec = "00"
    direction = "00"

    do_rebind_if_needed(self, key, Ep, batchMode, cluster)
    
    ListOfAttributesToConfigure = []
    for attr in cluster_configuration:
        # Check if the Attribute is listed in the Attributes List (provided by the Device
        # In case Attributes List exists, we have give the list of reported attribute.
        if cluster == "0300":
            # We need to evaluate the Attribute on ZDevice basis
            if self.ListOfDevices[key]["ZDeviceID"] == {}:
                continue

            ZDeviceID = self.ListOfDevices[key]["ZDeviceID"]
            if "ZDeviceID" in cluster_configuration[attr] and (
                ZDeviceID not in cluster_configuration[attr]["ZDeviceID"] and len(cluster_configuration[attr]["ZDeviceID"]) != 0
            ):
                self.logging( "Debug", f"------> configure_reporting_for_one_cluster - {key}/{Ep} skip Attribute {attr} for Cluster {cluster} due to ZDeviceID {ZDeviceID}", nwkid=key, )
                continue

        # Check against Attribute List only if the Model is not defined in the Certified Conf.
        if not is_valid_attribute(self, key, Ep, cluster, attr):
            continue

        if is_tobe_skip(self, key, Ep, cluster, attr):
            continue

        # Check if we have a Manufacturer Specific Cluster/Attribute. If that is the case, we need to send what we have ,
        # and then send the Manufacturer attribute, and finaly continue the job
        manufacturer_code = manufacturer_specific_attribute(self, key, cluster, attr, cluster_configuration[attr])
        if manufacturer_code:
            # Send what we have
            if ListOfAttributesToConfigure:
                self.prepare_and_send_configure_reporting( key, Ep, cluster_configuration, cluster, direction, manufacturer_spec, manufacturer, ListOfAttributesToConfigure, )

            self.logging("Debug", f"------> configure_reporting_for_one_cluster Reporting: Manuf Specific Attribute {attr}", nwkid=key)

            # Process the Attribute
            ListOfAttributesToConfigure = []
            ListOfAttributesToConfigure.append(attr)
            
            manufacturer_spec = "01"

            self.prepare_and_send_configure_reporting( key, Ep, cluster_configuration, cluster, direction, manufacturer_spec, manufacturer_code, ListOfAttributesToConfigure, )

            # Look for the next attribute and do not assume it is Manuf Specif
            ListOfAttributesToConfigure = []
            manufacturer_spec = "00"
            manufacturer = "0000"

            continue  # Next Attribute

        ListOfAttributesToConfigure.append(attr)
        self.logging("Debug", f"------> configure_reporting_for_one_cluster  {key}/{Ep} Cluster {cluster} Adding attr: {attr} ", nwkid=key)

    self.logging("Debug", f"------> configure_reporting_for_one_cluster  {key}/{Ep} Cluster {cluster} ready with: {ListOfAttributesToConfigure} ", nwkid=key)
    self.prepare_and_send_configure_reporting( key, Ep, cluster_configuration, cluster, direction, manufacturer_spec, manufacturer, ListOfAttributesToConfigure, )


def do_rebind_if_needed(self, nwkid, Ep, batchMode, cluster):
    
    # To be done ony in batchMode, as otherwise it has already been done (pairing time)
    if batchMode and self.pluginconf.pluginConf["allowReBindingClusters"]:
        # Correctif 22 Novembre. Delete only for the specific cluster and not the all Set
        if (
            "Bind" in self.ListOfDevices[nwkid]
            and Ep in self.ListOfDevices[nwkid]["Bind"]
            and cluster in self.ListOfDevices[nwkid]["Bind"][Ep]
        ):
            del self.ListOfDevices[nwkid]["Bind"][Ep][cluster]
        if "IEEE" in self.ListOfDevices[nwkid]:
            self.logging("Debug", f"---> configureReporting - requested Bind for {nwkid} on Cluster: {cluster}", nwkid=nwkid)
            if self.pluginconf.pluginConf["doUnbindBind"]:
                unbindDevice(self, self.ListOfDevices[nwkid]["IEEE"], Ep, cluster)
            bindDevice(self, self.ListOfDevices[nwkid]["IEEE"], Ep, cluster)
        else:
            self.logging("Error", f"configureReporting - inconsitency on {nwkid} no IEEE found : {str(self.ListOfDevices[nwkid])} ")

def read_report_configure_response_zigpy(self, MsgData, MsgLQI):  # Read Configure Report response
    self.logging( "Debug", f"Read Configure Reporting response - {MsgData}", )
    
    NwkId = MsgData[2:6]
    Ep = MsgData[6:8]
    ClusterId = MsgData[8:12]
    self.logging( "Debug", f" - NwkId: {NwkId} Ep: {Ep} ClusterId: {ClusterId} ",nwkid=NwkId )
    idx = 12
    while idx < len(MsgData):
        status = MsgData[idx:idx + 2]
        idx += 2
        direction = MsgData[idx:idx + 2]
        idx += 2
        attribute = MsgData[idx:idx + 4]
        idx += 4
        self.logging( "Debug", f" - status: {status} direction: {direction} attribute: {attribute} restofdata: {MsgData[idx:]}",nwkid=NwkId )
        DataType = MinInterval = MaxInterval = Change = timeout = None
        if status != "00" and self.zigbee_communication == "native":   # native == zigate
            # Looks like Zigate send some padding data when Status different that 0x00 and there is 
            # only one attribut send a time. #1226
            break
        elif status == "00":
            DataType = MsgData[idx:idx + 2]
            idx += 2
            self.logging( "Debug", f" - DataType: {DataType}  restofdata: {MsgData[idx:]}",nwkid=NwkId )
            MinInterval = MsgData[idx:idx + 4]
            idx += 4
            self.logging( "Debug", f" - MinInterval: {MinInterval}  restofdata: {MsgData[idx:]}",nwkid=NwkId )
            MaxInterval = MsgData[idx:idx + 4]
            idx += 4
            self.logging( "Debug", f" - MaxInterval: {MaxInterval}  restofdata: {MsgData[idx:]}",nwkid=NwkId)
            
            if analog_value(int(DataType,16)) and DataType in SIZE_DATA_TYPE:
                size = SIZE_DATA_TYPE[DataType] * 2
                Change = MsgData[idx : idx + size]
                idx += size             
                self.logging( "Debug", f" - Change: {Change}  restofdata: {MsgData[idx:]}", nwkid=NwkId)               

            if direction == "01":
                timeout = MsgData[idx : idx + 4]
                idx += 4
                self.logging( "Debug", f" - timeout: {timeout}  restofdata: {MsgData[idx:]}", nwkid=NwkId )  

        store_read_configure_reporting_record( self, NwkId, Ep, ClusterId, status, attribute, DataType, MinInterval, MaxInterval, Change, timeout )
        self.logging(
            "Debug",
            f"Read Configure Reporting response - Status: {status} NwkId: {NwkId} Ep: {Ep} Cluster: {ClusterId} Attribute: {attribute} DataType: {DataType} Min: {MinInterval} Max: {MaxInterval} Change: {Change}",
            nwkid=NwkId,
        )
    if STORE_READ_CONFIGURE_REPORTING in self.ListOfDevices[NwkId] and "Request" in self.ListOfDevices[NwkId][STORE_READ_CONFIGURE_REPORTING]:
        self.logging( "Debug", f"       Remove self.ListOfDevices[ {NwkId} ][{STORE_READ_CONFIGURE_REPORTING}]['Request']", nwkid=NwkId, )
        del self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Request"]


def read_report_configure_response_zigate(self, MsgData, MsgLQI):  # Read Configure Report response
    self.logging( "Debug", f"Read Configure Reporting response - {MsgData}", )
    # 03 1ed5 01 0006 
    # 00 10 0000 012c 0001

    # 04 4ac5 01 0702 00 2a 0400 012c 0005
    NwkId = MsgData[2:6]
    Ep = MsgData[6:8]
    ClusterId = MsgData[8:12]
    self.logging( "Debug", f" - NwkId: {NwkId} Ep: {Ep} ClusterId: {ClusterId} ",nwkid=NwkId )
    idx = 12
    direction = "00"
    while idx < len(MsgData):
        status = MsgData[idx:idx + 2]
        idx += 2
        DataType = MsgData[idx:idx + 2]
        idx += 2
        attribute = MsgData[idx:idx + 4]
        idx += 4
        self.logging( "Debug", f" - status: {status} direction: {direction} attribute: {attribute} DataType: {DataType} restofdata: {MsgData[idx:]}",nwkid=NwkId )
        MinInterval = MaxInterval = Change = timeout = None
        if status != "00":   # native == zigate
            # Looks like Zigate send some padding data when Status different that 0x00 and there is 
            # only one attribut send a time. #1226
            break

        MaxInterval = MsgData[idx:idx + 4]
        idx += 4
        self.logging( "Debug", f" - MaxInterval: {MaxInterval}  restofdata: {MsgData[idx:]}", nwkid=NwkId)
            
        MinInterval = MsgData[idx:idx + 4]
        idx += 4
        self.logging( "Debug", f" - MinInterval: {MinInterval}  restofdata: {MsgData[idx:]}",nwkid=NwkId )
        
        try:
            int_datatype = int(DataType,16)
        except Exception as e:
            self.logging( "Error", f" - unable to convert datatype {DataType} into int. NwkId: {NwkId} Ep: {Ep} ClusterId: {ClusterId} {MsgData}", nwkid=NwkId)
            return 

        if composite_value( int_datatype ) or discrete_value( int_datatype ):
            pass

        elif DataType in SIZE_DATA_TYPE:
            size = SIZE_DATA_TYPE[DataType] * 2
            Change = MsgData[idx : idx + size]
            idx += size             
            self.logging( "Debug", f" - Change: {Change}  restofdata: {MsgData[idx:]}", nwkid=NwkId)               

        if direction == "01":
            timeout = MsgData[idx : idx + 4]
            idx += 4
            self.logging( "Debug", f" - timeout: {timeout}  restofdata: {MsgData[idx:]}", nwkid=NwkId)  

        store_read_configure_reporting_record( self, NwkId, Ep, ClusterId, status, attribute, DataType, MinInterval, MaxInterval, Change, timeout )
        self.logging(
            "Debug",
            f"Read Configure Reporting response - Status: {status} NwkId: {NwkId} Ep: {Ep} Cluster: {ClusterId} Attribute: {attribute} DataType: {DataType} Min: {MinInterval} Max: {MaxInterval} Change: {Change}",
            nwkid=NwkId,
        )
    if STORE_READ_CONFIGURE_REPORTING in self.ListOfDevices[NwkId] and "Request" in self.ListOfDevices[NwkId][STORE_READ_CONFIGURE_REPORTING]:
        self.logging( "Debug", f"       Remove self.ListOfDevices[ {NwkId} ][{STORE_READ_CONFIGURE_REPORTING}]['Request']", nwkid=NwkId, )
        del self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Request"]

def do_we_have_to_do_the_work(self, NwkId, Ep, cluster):

    if cluster in ("Type", "ColorMode", "ClusterType"):
        return False
    
    if "Model" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Model"] != {}:
        if self.ListOfDevices[NwkId]["Model"] == "lumi.light.aqcn02" and cluster in (
            "0402",
            "0403",
            "0405",
            "0406",
        ):
            return False

        if self.ListOfDevices[NwkId]["Model"] == "lumi.remote.b686opcn01" and Ep != "01":
            # We bind only on EP 01
            self.logging("Debug", f"Do not Configure Reporting lumi.remote.b686opcn01 to Zigate Ep {Ep} Cluster {cluster}", nwkid=NwkId)

            return False

    # Bad Hack for now. FOR PROFALUX
    if self.ListOfDevices[NwkId]["ProfileID"] == "0104" and self.ListOfDevices[NwkId]["ZDeviceID"] == "0201":  # Remote
        # Do not Configure Reports Remote Command
        self.logging("Debug", f"----> Do not Configure Reports cluster {cluster} for Profalux Remote command {NwkId}/{Ep}", nwkid=NwkId)

        return False
    return True


def is_valid_attribute(self, nwkid, Ep, cluster, attr):
    if (
        (
            "Model" in self.ListOfDevices[nwkid]
            and self.ListOfDevices[nwkid]["Model"] != {}
            and self.ListOfDevices[nwkid]["Model"] not in self.DeviceConf
            and "Attributes List" in self.ListOfDevices[nwkid]
        )
        and "Ep" in self.ListOfDevices[nwkid]["Attributes List"]
        and Ep in self.ListOfDevices[nwkid]["Attributes List"]["Ep"]
        and cluster in self.ListOfDevices[nwkid]["Attributes List"]["Ep"][Ep]
        and attr not in self.ListOfDevices[nwkid]["Attributes List"]["Ep"][Ep][cluster]
    ):
        self.logging("Debug", f"configureReporting: drop attribute {attr}", nwkid=nwkid)
        return False
    return True


def is_tobe_skip(self, nwkid, Ep, Cluster, attr):
    
    if self.zigbee_communication == "native" and self.FirmwareVersion and int(self.FirmwareVersion, 16) <= int("31c", 16):
        if is_attr_unvalid_datastruct(self, STORE_CONFIGURE_REPORTING, nwkid, Ep, Cluster, "0000"):
            return True
        reset_attr_datastruct(self, STORE_CONFIGURE_REPORTING, nwkid, Ep, Cluster, "0000")

    if self.zigbee_communication == "native" and self.FirmwareVersion and int(self.FirmwareVersion, 16) > int("31c", 16):
        if is_attr_unvalid_datastruct(self, STORE_CONFIGURE_REPORTING, nwkid, Ep, Cluster, attr):
            return True
        reset_attr_datastruct(self, STORE_CONFIGURE_REPORTING, nwkid, Ep, Cluster, attr)
    return False


def manufacturer_specific_attribute(self, key, cluster, attr, cfg_attribute):

    # Return False if the attribute is not a manuf specific, otherwise return the Manufacturer code
    if "ManufSpecific" in cfg_attribute:
        self.logging(
            "Log",
            f'manufacturer_specific_attribute - NwkId: {key} found attribute: {attr} Manuf Specific, return ManufCode: {cfg_attribute["ManufSpecific"]}',
            nwkid=key
        )

        return cfg_attribute["ManufSpecific"]

    if (
        attr
        in (
            "4000",
            "4012",
        )
        and cluster == "0201"
        and "Model" in self.ListOfDevices[key]
        and self.ListOfDevices[key]["Model"] in ("eT093WRO", "eTRV0100")
    ):
        return "1246"

    if (
        attr in ("fd00",)
        and cluster == "0201"
        and "Model" in self.ListOfDevices[key]
        and self.ListOfDevices[key]["Model"] in ("AC221", "AC211")
    ):
        return "113c"

    if cluster == "fc21" and "Manufacturer" in self.ListOfDevices[key] and self.ListOfDevices[key]["Manufacturer"] == "1110":
        return "1110"

    if (
        attr
        in (
            "0030",
            "0031",
        )
        and cluster == "0406"
        and "Manufacturer" in self.ListOfDevices[key]
        and self.ListOfDevices[key]["Manufacturer"] == "100b"
    ):
        return "100b"


def store_read_configure_reporting_record( self, NwkId, Ep, ClusterId, status, attribute, DataType, MinInterval, MaxInterval, Change, timeout ):
    
    if STORE_READ_CONFIGURE_REPORTING not in self.ListOfDevices[ NwkId ]:
        self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING] = { "Ep": {} }
    if "Ep" not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]:
        self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING] = { "Ep": {} }
    self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["TimeStamp"] = time.time()   
    if Ep not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"]:
        self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ] = {}
    if ClusterId not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ]:
        self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ] = {}
    if status == "00":
        self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][ attribute ] = {
            "TimeStamp": time.time(),
            "Status": status,
            "DataType": DataType,
            "MinInterval": MinInterval,
            "MaxInterval": MaxInterval,
        }
        if Change:
            self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][ attribute ][ "Change" ] = Change
        if timeout:
            self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][ attribute ][ "TimeOut" ] = timeout  
    else:
        self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][ attribute ] = { 
            "TimeStamp": time.time(),
            'Status': status }


def retreive_read_configure_reporting_record(self, NwkId, Ep=None, ClusterId=None, AttributeId=None):
    
    if STORE_READ_CONFIGURE_REPORTING not in self.ListOfDevices[ NwkId ]:
        return None

    if Ep is None and ClusterId is None:
        # We want the all structure
        return self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"]
        
    if ( 
        Ep is None 
        and "Ep" in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING] 
        and Ep in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"]
        and ClusterId in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ]
    ):
        # We want only the Ep
        return self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ]
        
    if (
        AttributeId is None 
        and "Ep" in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING] 
        and Ep in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"]
        and ClusterId in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ]
    ):
        # We want a specific Cluster is a Specific Ep
        return self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ]

    if ( 
        "Ep" not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING] 
        or Ep not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"]
        or ClusterId not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ]
        or AttributeId not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ]
    ):
        return None

    if ( 
        "Status" in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId] 
        and self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId]["Status"] != "00"
    ):
        self.logging("Debug", f"retreive_read_configure_reporting_record {NwkId}/{Ep} Cluster {ClusterId} Status != 0x00", nwkid=NwkId)
        return { "Status": self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId]["Status"] }
        
    if (
        "DataType" not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId]
        or "MinInterval" not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId]
        or "MaxInterval" not in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId]
    ):
        self.logging("Debug", f"retreive_read_configure_reporting_record {NwkId}/{Ep} Cluster {ClusterId} No DataType, Min and Max !!", nwkid=NwkId)
        return None
        
    return_data = {
        "DataType": self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId][ "DataType" ],
        "MinInterval": self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId][ "MinInterval" ],
        "MaxInterval": self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId][ "MaxInterval" ],
    }
    if "Change" in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId]:
        return_data[ "Change" ] = self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId][ "Change" ]
            
    if "TimeOut" in self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId]:
        return_data[ "TimeOut" ] = self.ListOfDevices[ NwkId ][STORE_READ_CONFIGURE_REPORTING]["Ep"][ Ep ][ ClusterId ][AttributeId][ "TimeOut" ]
    return return_data
