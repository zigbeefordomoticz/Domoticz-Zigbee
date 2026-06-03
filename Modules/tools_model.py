#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""Device model/config helpers extracted from tools.py"""

import time

from Modules.zigateConsts import HEARTBEAT


def deviceconf_device(self, nwkid):
    """
    Retrieve the DeviceConf entry for a given device based on its model.

    Args:
        nwkid (str): The network ID of the device.

    Returns:
        dict: The corresponding configuration from DeviceConf if found,
              otherwise an empty dictionary.
    """
    device = self.ListOfDevices.get(nwkid, {})
    model = device.get("Model")

    return self.DeviceConf[model] if model and model in self.DeviceConf else {}


def getListofClusterbyModel(self, Model, InOut):
    """
    Provide the list of clusters attached to Ep In
    """
    listofCluster = []
    if InOut == "" or InOut is None:
        return listofCluster
    if InOut not in ["Epin", "Epout"]:
        self.log.logging("PluginTools", "Error", "getListofClusterbyModel - Argument error : " + Model + " " + InOut)
        return ""

    if Model in self.DeviceConf and InOut in self.DeviceConf[Model]:
        for ep in list(self.DeviceConf[Model][InOut].keys()):
            seen = ""
            for cluster in sorted(self.DeviceConf[Model][InOut][ep]):
                if cluster in ("ClusterType", "Type", "ColorMode", seen):
                    continue
                listofCluster.append(cluster)
                seen = cluster
    return listofCluster


def getListofInClusterbyModel(self, Model):
    return getListofClusterbyModel(self, Model, "Epin")


def getListofOutClusterbyModel(self, Model):
    return getListofClusterbyModel(self, Model, "Epout")


def getListofType(self, widget_type):
    """
    Splits a slash-separated device widget_type string into a list of individual widget_type.

    Args:
        Type (str): A slash-separated string like "Plug/Power/Meters".

    Returns:
        list[str]: A list of widget_type, e.g., ['Plug', 'Power', 'Meters'].
                   Returns an empty list if input is empty or None.
    """
    return widget_type.split('/') if widget_type else []


def get_deviceconf_parameter_value(self, model, attribute, return_default=None):
    """ Retrieve Configuration Attribute from Config file"""
    
    return self.DeviceConf.get(model, {}).get(attribute, return_default)


def build_list_of_device_model(self, force=False):
    
    if not force and ( self.internalHB % (23 * 3600 // HEARTBEAT) != 0):
        return

    self.pluginParameters["NetworkDevices"] = {}
    for x in self.ListOfDevices:
        if x == "0000":
            continue

        manufcode = manufname = modelname = None
        if "Model" in self.ListOfDevices[x]:
            modelname = self.ListOfDevices[x]["Model"]

        self.ListOfDevices[ x ]["CertifiedDevice"] = modelname in self.DeviceConf

        if "Manufacturer" in self.ListOfDevices[x]:
            manufcode = self.ListOfDevices[x]["Manufacturer"]
            if manufcode in ( "", {}):
                continue
            if manufcode not in self.pluginParameters["NetworkDevices"]:
                self.pluginParameters["NetworkDevices"][ manufcode ] = {}

        if manufcode and "Manufacturer Name" in self.ListOfDevices[x]:
            manufname = self.ListOfDevices[x]["Manufacturer Name"]
            if manufname in ( "", {} ):
                manufname = "unknown"
                
            if manufname not in self.pluginParameters["NetworkDevices"][ manufcode ]:
                self.pluginParameters["NetworkDevices"][ manufcode ][ manufname ] = []

        if manufcode and manufname and modelname:
            if modelname in ( "", {} ):
                continue
            if modelname not in self.pluginParameters["NetworkDevices"][ manufcode ][ manufname ]:
                self.pluginParameters["NetworkDevices"][ manufcode ][ manufname ].append( modelname )
                if modelname not in self.DeviceConf:
                    unknown_device_model(self, x, modelname,manufcode, manufname )


def unknown_device_model(self, NwkId, Model, ManufCode, ManufName ):
    
    self.log.logging("Plugin", "Debug", "unknown_device_model NwkId: %s Model: %s ManufCode: %s ManufName: %s" %(
        NwkId, Model, ManufCode, ManufName))
    
    if 'logUnknownDeviceModel' not in self.pluginconf.pluginConf or not self.pluginconf.pluginConf["logUnknownDeviceModel"]:
        return
    
    if 'Log_UnknowDeviceFlag' in self.ListOfDevices[ NwkId ] and (self.ListOfDevices[ NwkId ]['Log_UnknowDeviceFlag'] + ( 24 * 3600)) > time.time() :
        return
    
    if 'Status' in self.ListOfDevices[ NwkId ] and self.ListOfDevices[ NwkId ]['Status'] == 'notDB':
        return
           
    device_name = get_device_nickname( self, NwkId=NwkId)

    self.log.logging("Plugin", "Log", "We have detected a working device %s (%s) Model: %s not optimized with the plugin. " %( 
        get_device_nickname( self, NwkId=NwkId), NwkId, Model, ))
    self.log.logging("Plugin", "Log", "")
    self.log.logging("Plugin", "Log", " --- Please follow the link https://zigbeefordomoticz.github.io/wiki/en-eng/Problem_Dealing-with-none-optimized-device.html")         
    self.log.logging("Plugin", "Log", " --- Thanks the Zigbee for Domoticz plugin team")
    self.log.logging("Plugin", "Log", "")
    
    self.ListOfDevices[ NwkId ]['Log_UnknowDeviceFlag'] = time.time()


def get_device_nickname(self, NwkId=None, Ieee=None):
    if Ieee:
        NwkId = self.IEEE2NWK.get(Ieee, NwkId)
    nickname = self.ListOfDevices.get(NwkId, {}).get('ZDeviceName', "")
    return "0x%s" %NwkId if nickname == "" else nickname