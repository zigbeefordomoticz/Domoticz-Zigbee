#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import json
from time import time

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.basicOutputs import (ZigatePermitToJoin, setExtendedPANID,
                                  start_Zigate, zigateBlueLed)
from Modules.domoticzAbstractLayer import (domoticz_error_api,
                                           domoticz_log_api,
                                           domoticz_status_api)
from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING
from Modules.sendZigateCommand import (raw_APS_request, send_zigatecmd_raw,
                                       send_zigatecmd_zcl_ack,
                                       send_zigatecmd_zcl_noack)
from Modules.zigateConsts import (PROFILE_ID, ZCL_CLUSTERS_LIST, ZHA_DEVICES,
                                  ZLL_DEVICES)


def rest_new_hrdwr(self, verb, data, parameters):

    """
    This is call to Enable/Disable a Provisioning process. As a toggle you will enable the provisioning or disable it
    it will return either Enable or Disable
    """
    _response = prepResponseMessage(self, setupHeadersResponse())

    if verb != "GET":
        return _response

    data = {}
    if len(parameters) != 1:
        domoticz_error_api("rest_new_hrdwr - unexpected parameter %s " % parameters)
        _response["Data"] = { "BE_Error": "unexpected parameter %s " % parameters}
        return _response

    if parameters[0] not in ("enable", "cancel", "disable"):
        domoticz_error_api("rest_new_hrdwr - unexpected parameter %s " % parameters[0])
        _response["Data"] = { "BE_Error": "unexpected parameter %s " % parameters[0]}
        return _response

    if parameters[0] == "enable":
        domoticz_log_api("Enable Assisted pairing")
        if len(self.DevicesInPairingMode):
            del self.DevicesInPairingMode
            self.DevicesInPairingMode = []
        if not self.ControllerData:
            # Seems we are in None mode - Testing for ben
            self.fakeDevicesInPairingMode = 0

        if self.permitTojoin["Duration"] != 255 and self.pluginParameters["Mode2"] != "None":
            ZigatePermitToJoin(self, (4 * 60))

        _response["Data"] = { "BE_Start": "start pairing mode at %s " % int(time())}
        return _response

    if parameters[0] in ("cancel", "disable"):
        domoticz_log_api("Disable Assisted pairing")
        if len(self.DevicesInPairingMode) != 0:
            del self.DevicesInPairingMode
            self.DevicesInPairingMode = []

        if not self.ControllerData:
            # Seems we are in None mode - Testing for ben
            self.fakeDevicesInPairingMode = 0

        if not (self.permitTojoin["Duration"] == 255 or self.pluginParameters["Mode2"] == "None"):
            ZigatePermitToJoin(self, 0)

        _response["Data"] = {"BE_Stop": "stop pairing mode at %s " % int(time())}
        return _response


def rest_rcv_nw_hrdwr(self, verb, data, parameters):

    """
    Will return a status on the provisioning process. Either Enable or Disable and in case there is a new device provisionned
    during the period, it will return the information captured.
    """

    _response = prepResponseMessage(self, setupHeadersResponse())

    if verb != "GET":
        return _response

    data = {}
    data["NewDevices"] = []

    if not self.ControllerData:
        # Seems we are in None mode - Testing for ben
        if self.fakeDevicesInPairingMode in (0, 1):
            # Do nothing just wait the next pool
            self.fakeDevicesInPairingMode += 1
            _response["Data"] = json.dumps(data)
            return _response

        if self.fakeDevicesInPairingMode in (2, 3):
            self.fakeDevicesInPairingMode += 1
            newdev = {}
            newdev["NwkId"] = list(self.ListOfDevices.keys())[0]
            data["NewDevices"].append(newdev)
            _response["Data"] = json.dumps(data)
            return _response

        if self.fakeDevicesInPairingMode in (4, 5):
            self.fakeDevicesInPairingMode += 1
            newdev = {}
            newdev["NwkId"] = list(self.ListOfDevices.keys())[0]
            data["NewDevices"].append(newdev)
            newdev = {}
            newdev["NwkId"] = list(self.ListOfDevices.keys())[1]
            data["NewDevices"].append(newdev)
            _response["Data"] = json.dumps(data)
            return _response

        if self.fakeDevicesInPairingMode in (6, 7):
            self.fakeDevicesInPairingMode += 1
            self.DevicesInPairingMode.append(list(self.ListOfDevices.keys())[0])
            self.DevicesInPairingMode.append(list(self.ListOfDevices.keys())[1])
            self.DevicesInPairingMode.append(list(self.ListOfDevices.keys())[2])

    domoticz_log_api("Assisted Pairing: Polling: %s" % str(self.DevicesInPairingMode))
    if len(self.DevicesInPairingMode) == 0:
        domoticz_log_api("--> Empty queue")
        _response["Data"] = json.dumps(data)
        return _response

    listOfPairedDevices = list(self.DevicesInPairingMode)
    _fake = 0
    for nwkid in listOfPairedDevices:
        if not self.ControllerData:
            _fake += 1
        if nwkid not in self.ListOfDevices:
            continue
        newdev = {}
        newdev["NwkId"] = nwkid

        domoticz_log_api("--> New device: %s" % nwkid)
        if "Status" not in self.ListOfDevices[nwkid]:
            domoticz_error_api("Something went wrong as the device seems not be created")
            data["NewDevices"].append(newdev)
            continue

        if self.ListOfDevices[nwkid]["Status"] in ("004d", "0045", "0043", "8045", "8043") or (_fake == 1):
            # Pairing in progress, just return the Nwkid
            data["NewDevices"].append(newdev)
            continue

        elif self.ListOfDevices[nwkid]["Status"] == "UNKNOW" or (_fake == 2):
            domoticz_log_api("--> UNKNOW , removed %s from List" % nwkid)
            self.DevicesInPairingMode.remove(nwkid)
            newdev["ProvisionStatus"] = "Failed"
            newdev["ProvisionStatusDesc"] = "Failed"

        elif self.ListOfDevices[nwkid]["Status"] == "inDB":
            domoticz_log_api("--> inDB , removed %s from List" % nwkid)
            self.DevicesInPairingMode.remove(nwkid)
            newdev["ProvisionStatus"] = "inDB"
            newdev["ProvisionStatusDesc"] = "inDB"
        else:
            domoticz_log_api("--> Unexpected , removed %s from List" % nwkid)
            self.DevicesInPairingMode.remove(nwkid)
            newdev["ProvisionStatus"] = "Unexpected"
            newdev["ProvisionStatusDesc"] = "Unexpected"
            domoticz_error_api("Unexpected")
            continue

        newdev["IEEE"] = "Unknown"
        if "IEEE" in self.ListOfDevices[nwkid]:
            newdev["IEEE"] = self.ListOfDevices[nwkid]["IEEE"]

        newdev["ProfileId"] = ""
        newdev["ProfileIdDesc"] = "Unknow"
        if "ProfileID" in self.ListOfDevices[nwkid]:
            if self.ListOfDevices[nwkid]["ProfileID"] != {}:
                newdev["ProfileId"] = self.ListOfDevices[nwkid]["ProfileID"]
                if int(newdev["ProfileId"], 16) in PROFILE_ID:
                    newdev["ProfileIdDesc"] = PROFILE_ID[int(newdev["ProfileId"], 16)]

        newdev["ZDeviceID"] = ""
        newdev["ZDeviceIDDesc"] = "Unknow"
        if "ZDeviceID" in self.ListOfDevices[nwkid]:
            if self.ListOfDevices[nwkid]["ZDeviceID"] != {}:
                newdev["ZDeviceID"] = self.ListOfDevices[nwkid]["ZDeviceID"]
                if int(newdev["ProfileId"], 16) == 0x0104:  # ZHA
                    if int(newdev["ZDeviceID"], 16) in ZHA_DEVICES:
                        newdev["ZDeviceIDDesc"] = ZHA_DEVICES[int(newdev["ZDeviceID"], 16)]
                    else:
                        newdev["ZDeviceIDDesc"] = "Unknow"
                elif int(newdev["ProfileId"], 16) == 0xC05E:  # ZLL
                    if int(newdev["ZDeviceID"], 16) in ZLL_DEVICES:
                        newdev["ZDeviceIDDesc"] = ZLL_DEVICES[int(newdev["ZDeviceID"], 16)]

        if "Model" in self.ListOfDevices[nwkid]:
            newdev["Model"] = self.ListOfDevices[nwkid]["Model"]

        newdev["PluginCertified"] = "Unknow"
        if "ConfigSource" in self.ListOfDevices[nwkid]:
            if self.ListOfDevices[nwkid]["ConfigSource"] == "DeviceConf":
                newdev["PluginCertified"] = "yes"
            else:
                newdev["PluginCertified"] = "no"

        newdev["Ep"] = []
        if "Ep" in self.ListOfDevices[nwkid]:
            for iterEp in self.ListOfDevices[nwkid]["Ep"]:
                ep = {}
                ep["Ep"] = iterEp
                ep["Clusters"] = []
                for clusterId in self.ListOfDevices[nwkid]["Ep"][iterEp]:
                    if clusterId in ("ClusterType", "Type", "ColorControl"):
                        continue

                    cluster = {}
                    cluster["ClusterId"] = clusterId
                    if clusterId in ZCL_CLUSTERS_LIST:
                        cluster["ClusterDesc"] = ZCL_CLUSTERS_LIST[clusterId]
                    else:
                        cluster["ClusterDesc"] = "Unknown"
                    ep["Clusters"].append(cluster)
                    domoticz_log_api("------> New Cluster: %s" % str(cluster))
                newdev["Ep"].append(ep)
                domoticz_log_api("----> New Ep: %s" % str(ep))
        data["NewDevices"].append(newdev)
        domoticz_log_api(" --> New Device: %s" % str(newdev))
    # for nwkid in listOfPairedDevices:

    _response["Data"] = json.dumps(data)
    return _response


def rest_full_reprovisionning(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

    domoticz_log_api("rest_full_reprovisionning -->Verb: %s Data: %s Parameters: %s" % (verb, data, parameters))

    if verb != "PUT":
        return _response

    data = data.decode("utf8")
    data = eval(data)
    self.logging("Log", "Data: %s" % data)

    if "IEEE" not in data and "NWKID" not in data:
        domoticz_error_api("rest_full_reprovisionning - unexpected parameter %s " % parameters)
        _response["Data"] = { "BE_status": "unexpected parameter %s " % parameters}
        return _response

    if "IEEE" in data:
        key = data["IEEE"]
        if key not in self.IEEE2NWK:
            domoticz_error_api("rest_full_reprovisionning - Unknown device %s " % key)
            return _response
        nwkid = self.IEEE2NWK[key]
        _response["Data"] = { "BE_status": "IEEE %s set to Provisioning Requested at %s" % (key, int(time()))}
    else:
        nwkid = data["NWKID"]
        if nwkid not in self.ListOfDevices:
            domoticz_error_api("rest_full_reprovisionning - Unknown device %s " % nwkid)
            return _response
        _response["Data"] = {"BE_status": "NwkId %s set to Provisioning Requested at %s" % (nwkid, int(time()))}

    if "Bind" in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid]["Bind"]
    if STORE_CONFIGURE_REPORTING in self.ListOfDevices[nwkid]:
        del self.ListOfDevices[nwkid][STORE_CONFIGURE_REPORTING]
    if "ReadAttributes" in self.ListOfDevices[nwkid]:
        del self.ListOfDevices[nwkid]["ReadAttributes"]
    if "Neighbours" in self.ListOfDevices[nwkid]:
        del self.ListOfDevices[nwkid]["Neighbours"]
    if "IAS" in self.ListOfDevices[nwkid]:
        del self.ListOfDevices[nwkid]["IAS"]
        for x in self.ListOfDevices[nwkid]["Ep"]:
            if "0500" in self.ListOfDevices[nwkid]["Ep"][ x ]:
                del self.ListOfDevices[nwkid]["Ep"][ x ]["0500"]
                self.ListOfDevices[nwkid]["Ep"][ x ]["0500"] = {}
            if "0502" in self.ListOfDevices[nwkid]["Ep"][ x ]:
                del self.ListOfDevices[nwkid]["Ep"][ x ]["0502"]
                self.ListOfDevices[nwkid]["Ep"][ x ]["0502"] = {}

    if "WriteAttributes" in self.ListOfDevices[nwkid]:
        del self.ListOfDevices[nwkid]["WriteAttributes"]
    
    self.ListOfDevices[nwkid]["Status"] = "provREQ"

    return _response
