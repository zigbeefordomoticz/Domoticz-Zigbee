#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

from time import time

from Zigbee.zdpCommands import zdp_binding_device, zdp_unbinding_device

from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING
from Modules.tools import is_fake_ep
from Modules.zigateConsts import CLUSTERS_LIST


def bindGroup(self, ieee, ep, cluster, groupid):

    if ieee not in self.IEEE2NWK:
        self.log.logging(
            "Binding",
            "Debug",
            "bindGroup - Unknown ieee: %s, ep: %s, cluster: %s, groupId: %s" % (ieee, ep, cluster, groupid),
        )
        return

    nwkid = self.IEEE2NWK[ieee]
    if nwkid not in self.ListOfDevices:
        self.log.logging(
            "Binding",
            "Debug",
            "bindGroup - Unknown nwkid: %s from ieee: %s, ep: %s, cluster: %s, groupId: %s" % (nwkid, ieee, ep, cluster, groupid),
        )
        return

    if self.ControllerIEEE and ieee == self.ControllerIEEE:
        self.log.logging(
            "Binding",
            "Debug",
            "bindGroup - Cannot bind Coordinator from ieee: %s, ep: %s, cluster: %s, groupId: %s" % (ieee, ep, cluster, groupid),
        )
        # we have to bind the ZiGate to a group
        return

    self.log.logging(
        "Binding",
        "Debug",
        "bindGroup - ieee: %s, ep: %s, cluster: %s, groupId: %s" % (ieee, ep, cluster, groupid),
        nwkid=nwkid,
    )
    # Read to bind
    mode = "01"  # Addres Mode to use: group

    #datas = str(ieee) + str(ep) + str(cluster) + str(mode) + str(groupid)
    i_sqn = zdp_binding_device(self, ieee , ep , cluster , mode , groupid , "")
    #i_sqn = sendZigateCmd(self, "0030", datas)

def unbindGroup(self, ieee, ep, cluster, groupid):

    if ieee not in self.IEEE2NWK:
        self.log.logging(
            "Binding",
            "Debug",
            "unbindGroup - Unknown ieee: %s, ep: %s, cluster: %s, groupId: %s" % (ieee, ep, cluster, groupid),
        )
        return

    nwkid = self.IEEE2NWK[ieee]
    if nwkid not in self.ListOfDevices:
        self.log.logging(
            "Binding",
            "Debug",
            "unbindGroup - Unknown nwkid: %s from ieee: %s, ep: %s, cluster: %s, groupId: %s" % (nwkid, ieee, ep, cluster, groupid),
        )
        return

    if self.ControllerIEEE and ieee == self.ControllerIEEE:
        # we have to bind the ZiGate to a group
        self.log.logging(
            "Binding",
            "Debug",
            "unbindGroup - Cannot unbind Coordinator from ieee: %s, ep: %s, cluster: %s, groupId: %s" % (ieee, ep, cluster, groupid),
        )
        return

    self.log.logging(
        "Binding",
        "Log",
        "unbindGroup - ieee: %s, ep: %s, cluster: %s, groupId: %s" % (ieee, ep, cluster, groupid),
        nwkid=nwkid,
    )
    # Read to bind
    mode = "01"  # Addres Mode to use: group

    #datas = str(ieee) + str(ep) + str(cluster) + str(mode) + str(groupid)
    i_sqn = zdp_unbinding_device(self, ieee , ep , cluster , mode , groupid , "")
    #i_sqn = sendZigateCmd(self, "0031", datas)

def bindDevice(self, ieee, ep, cluster, destaddr=None, destep="01"):
    """
    Binding a device/cluster with ....
    if not destaddr and destep provided, we will assume that we bind this device with the Zigate coordinator

    ATTENTION:
    In case overwriteZigateEpBind is set, we will use that one instead of the despEp
    """

    if not destaddr:
        # destaddr = self.ieee # Let's grab the IEEE of Zigate
        if self.ControllerIEEE is not None and self.ControllerIEEE != "":
            destaddr = self.ControllerIEEE
        else:
            self.log.logging("Binding", "Debug", "bindDevice - self.ControllerIEEE not yet initialized")
            return

    if ieee in self.IEEE2NWK:
        nwkid = self.IEEE2NWK[ieee]
        if nwkid in self.ListOfDevices:

            # Very bad Hack, but at that stage, there is no other information we can Use. PROFALUX
            if self.ListOfDevices[nwkid]["ProfileID"] == "0104" and self.ListOfDevices[nwkid]["ZDeviceID"] == "0201":  # Remote
                # Do not bind Remote Command
                self.log.logging(
                    "Binding",
                    "Debug",
                    "----> Do not bind cluster %s for Profalux Remote command %s/%s" % (cluster, nwkid, ep),
                    nwkid,
                )
                return

            if "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] != {}:
                _model = self.ListOfDevices[nwkid]["Model"]
                if _model in self.DeviceConf:
                    # Bind and use Zigate Endpoint specified as overwriteZigateEpBind
                    if "overwriteZigateEpBind" in self.DeviceConf[_model]:
                        destep = self.DeviceConf[_model]["overwriteZigateEpBind"]
                        self.log.logging(
                            "Binding",
                            "Debug",
                            "----> %s/%s on %s overwrite Coordinator Endpoint for bind and use %s" % (nwkid, ep, cluster, destep),
                            nwkid,
                        )

                    # For to Bind only the Configured Clusters
                    if "ClusterToBind" in self.DeviceConf[_model] and cluster not in self.DeviceConf[_model]["ClusterToBind"]:
                        self.log.logging(
                            "Binding",
                            "Debug",
                            "----> Do not bind cluster %s due to Certified Conf for %s/%s" % (cluster, nwkid, ep),
                            nwkid,
                        )
                        return

                    # Bind only on those source Endpoint
                    if "bindEp" in self.DeviceConf[_model] and ep not in self.DeviceConf[_model]["bindEp"]:
                        self.log.logging(
                            "Binding",
                            "Debug",
                            "Do not Bind %s to Coordinator Ep %s Cluster %s" % (_model, ep, cluster),
                            nwkid,
                        )
                        return

    nwkid = self.IEEE2NWK[ieee]

    if is_fake_ep(self, nwkid, ep):
        return
            
    self.log.logging(
        "Binding",
        "Debug",
        "bindDevice - ieee: %s, ep: %s, cluster: %s, Zigate_ieee: %s, Zigate_ep: %s" % (ieee, ep, cluster, destaddr, destep),
        nwkid=nwkid,
    )

    # Read to bind
    mode = "03"  # Addres Mode to use

    #datas = str(ieee) + str(ep) + str(cluster) + str(mode) + str(destaddr) + str(destep)
    i_sqn = zdp_binding_device(self, ieee , ep , cluster , mode , destaddr , destep)
    #i_sqn = sendZigateCmd(self, "0030", datas)

    if "Bind" not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]["Bind"] = {}

    if ep not in self.ListOfDevices[nwkid]["Bind"]:
        self.ListOfDevices[nwkid]["Bind"][ep] = {}

    if cluster not in self.ListOfDevices[nwkid]["Bind"][ep]:
        self.ListOfDevices[nwkid]["Bind"][ep][cluster] = {'Target': '0000'}
        self.ListOfDevices[nwkid]["Bind"][ep][cluster]["Stamp"] = int(time())
        self.ListOfDevices[nwkid]["Bind"][ep][cluster]["Phase"] = "requested"
        self.ListOfDevices[nwkid]["Bind"][ep][cluster]["Status"] = ""
        self.ListOfDevices[nwkid]["Bind"][ep][cluster]["i_sqn"] = i_sqn


def rebind_Clusters(self, NWKID):

    cluster_to_bind = CLUSTERS_LIST

    # Checking if anything must be done before Bindings, and if we have to take some specific bindings
    if "Model" in self.ListOfDevices[NWKID]:
        _model = self.ListOfDevices[NWKID]["Model"]
        if _model != {}:
            if _model in self.DeviceConf and "ClusterToUnbind" in self.DeviceConf[_model]:
                # Check if we have to unbind clusters
                for iterEp, iterUnBindCluster in self.DeviceConf[_model]["ClusterToUnbind"]:
                    unbindDevice(self, self.ListOfDevices[NWKID]["IEEE"], iterEp, iterUnBindCluster)

            # User Configuration if exists
            if self.ListOfDevices[NWKID]["Model"] in self.DeviceConf and "ClusterToBind" in self.DeviceConf[_model]:
                cluster_to_bind = self.DeviceConf[_model]["ClusterToBind"]

    # If Bind information, then remove it
    if "Bind" in self.ListOfDevices[NWKID]:
        del self.ListOfDevices[NWKID]["Bind"]

    # If allow Unbind before Bind, then Unbind
    if self.pluginconf.pluginConf["doUnbindBind"]:
        for iterBindCluster in cluster_to_bind:
            for iterEp in self.ListOfDevices[NWKID]["Ep"]:
                if iterBindCluster in self.ListOfDevices[NWKID]["Ep"][iterEp]:
                    self.log.logging(
                        "Binding",
                        "Debug",
                        "Request an Unbind for %s/%s on Cluster %s" % (NWKID, iterEp, iterBindCluster),
                        nwkid=NWKID,
                    )
                    unbindDevice(self, self.ListOfDevices[NWKID]["IEEE"], iterEp, iterBindCluster)

    # Bind
    for iterBindCluster in cluster_to_bind:
        for iterEp in self.ListOfDevices[NWKID]["Ep"]:
            if iterBindCluster in self.ListOfDevices[NWKID]["Ep"][iterEp]:
                self.log.logging(
                    "Binding",
                    "Debug",
                    "Request a rebind for %s/%s on Cluster %s" % (NWKID, iterEp, iterBindCluster),
                    nwkid=NWKID,
                )
                bindDevice(self, self.ListOfDevices[NWKID]["IEEE"], iterEp, iterBindCluster)


def reWebBind_Clusters(self, NWKID):

    if "WebBind" not in self.ListOfDevices[NWKID]:
        return
    for Ep in list(self.ListOfDevices[NWKID]["WebBind"]):
        for cluster in list(self.ListOfDevices[NWKID]["WebBind"][Ep]):
            for destNwkid in list(self.ListOfDevices[NWKID]["WebBind"][Ep][cluster]):
                if destNwkid in (
                    "Stamp",
                    "Target",
                    "TargetIEEE",
                    "SourceIEEE",
                    "TargetEp",
                    "Phase",
                    "Status",
                ):  # delete old mechanism
                    self.log.logging(
                        "Binding",
                        "Error",
                        "---> delete  destNwkid: %s" % (destNwkid),
                        NWKID,
                        {"Error code": "BINDINGS-REWEBCLS-01"},
                    )
                    del self.ListOfDevices[NWKID]["WebBind"][Ep][cluster][destNwkid]
                if self.ListOfDevices[NWKID]["WebBind"][Ep][cluster][destNwkid]["Phase"] == "binded":
                    self.log.logging(
                        "Binding",
                        "Debug",
                        "Request a rewebbind for : nwkid %s ep: %s cluster: %s destNwkid: %s" % (NWKID, Ep, cluster, destNwkid),
                        nwkid=NWKID,
                    )
                    self.ListOfDevices[NWKID]["WebBind"][Ep][cluster][destNwkid]["Stamp"] = int(time())
                    self.ListOfDevices[NWKID]["WebBind"][Ep][cluster][destNwkid]["Phase"] = "requested"
                    return


def unbindDevice(self, ieee, ep, cluster, destaddr=None, destep="01"):
    """
    unbind
    """

    mode = "03"  # IEEE
    if not destaddr:
        # destaddr = self.ieee # Let's grab the IEEE of Zigate
        if self.ControllerIEEE is not None and self.ControllerIEEE != "":
            destaddr = self.ControllerIEEE
            destep = "01"
        else:
            self.log.logging("Binding", "Debug", "bindDevice - self.ControllerIEEE not yet initialized")
            return

    nwkid = self.IEEE2NWK[ieee]

    # If doing unbind, the Configure Reporting is lost
    if STORE_CONFIGURE_REPORTING in self.ListOfDevices[nwkid]:
        del self.ListOfDevices[nwkid][STORE_CONFIGURE_REPORTING]

    # Remove the Bind
    if "Bind" in self.ListOfDevices[nwkid] and ep in self.ListOfDevices[nwkid]["Bind"] and cluster in self.ListOfDevices[nwkid]["Bind"][ep]:
        del self.ListOfDevices[nwkid]["Bind"][ep][cluster]

    self.log.logging(
        "Binding",
        "Debug",
        "unbindDevice - ieee: %s, ep: %s, cluster: %s, Zigate_ieee: %s, Zigate_ep: %s" % (ieee, ep, cluster, destaddr, destep),
        nwkid=nwkid,
    )
    #datas = str(ieee) + str(ep) + str(cluster) + str(mode) + str(destaddr) + str(destep)
    zdp_unbinding_device(self, ieee , ep , cluster , mode , destaddr , destep)
    #sendZigateCmd(self, "0031", datas)

def webBind(self, sourceIeee, sourceEp, destIeee, destEp, Cluster):

    if sourceIeee not in self.IEEE2NWK:
        self.log.logging("Binding", "Error", "---> unknown sourceIeee: %s" % sourceIeee, None, {"Error code": "BINDINGS-WEBBIND-01"})
        return

    if destIeee not in self.IEEE2NWK:
        self.log.logging("Binding", "Error", "---> unknown destIeee: %s" % destIeee, None, {"Error code": "BINDINGS-WEBBIND-02"})
        return

    sourceNwkid = self.IEEE2NWK[sourceIeee]
    destNwkid = self.IEEE2NWK[destIeee]

    if sourceEp not in self.ListOfDevices[sourceNwkid]["Ep"]:
        self.log.logging(
            "Binding",
            "Error",
            "---> unknown sourceEp: %s for sourceNwkid: %s" % (sourceEp, sourceNwkid),
            None,
            {"Error code": "BINDINGS-WEBBIND-03", "sourceEp": sourceEp, "sourceNwkid": sourceNwkid},
        )
        return
    self.log.logging(
        "Binding",
        "Debug",
        "Binding Device %s/%s with Device target %s/%s on Cluster: %s" % (sourceIeee, sourceEp, destIeee, destEp, Cluster),
        sourceNwkid,
    )
    if Cluster not in self.ListOfDevices[sourceNwkid]["Ep"][sourceEp]:
        self.log.logging(
            "Binding",
            "Error",
            "---> Cluster %s not find in %s --> %s" % (Cluster, sourceNwkid, self.ListOfDevices[sourceNwkid]["Ep"][sourceEp].keys()),
            None,
            {"Error code": "BINDINGS-WEBBIND-04", "sourceEp": sourceEp, "sourceNwkid": sourceNwkid, "Cluster": Cluster},
        )
        return
    self.log.logging(
        "Binding",
        "Debug",
        "Binding Device %s/%s with Device target %s/%s on Cluster: %s" % (sourceIeee, sourceEp, destIeee, destEp, Cluster),
        destNwkid,
    )

    if destEp not in self.ListOfDevices[destNwkid]["Ep"]:
        self.log.logging(
            "Binding",
            "Error",
            "---> unknown destEp: %s for destNwkid: %s" % (destEp, destNwkid),
            None,
            {"Error code": "BINDINGS-WEBBIND-05", "sourceEp": sourceEp, "sourceNwkid": sourceNwkid, "destEp": destEp},
        )
        return

    mode = "03"  # IEEE
    #datas = str(sourceIeee) + str(sourceEp) + str(Cluster) + str(mode) + str(destIeee) + str(destEp)
    i_sqn = zdp_binding_device(self, sourceIeee , sourceEp , Cluster , mode , destIeee , destEp)
    #i_sqn = sendZigateCmd(self, "0030", datas)
    #self.log.logging("Binding", "Debug", "---> %s %s i_sqn: %s" % ("0030", datas, i_sqn), sourceNwkid)

    if "WebBind" not in self.ListOfDevices[sourceNwkid]:
        self.ListOfDevices[sourceNwkid]["WebBind"] = {}
    if sourceEp not in self.ListOfDevices[sourceNwkid]["WebBind"]:
        self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp] = {}
    if Cluster not in self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp]:
        self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster] = {}
    if destNwkid not in self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster]:
        self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid] = {}
    self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid] = {}
    self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]["SourceIEEE"] = sourceIeee
    self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]["Target"] = destNwkid
    self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]["TargetIEEE"] = destIeee
    self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]["TargetEp"] = destEp
    self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]["Stamp"] = int(time())
    self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]["Phase"] = "requested"
    self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]["i_sqn"] = i_sqn
    self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]["Status"] = ""

def webUnBind(self, sourceIeee, sourceEp, destIeee, destEp, Cluster):

    if sourceIeee not in self.IEEE2NWK:
        self.log.logging(
            "Binding",
            "Error",
            "---> unknown sourceIeee: %s" % sourceIeee,
            None,
            {"Error code": "BINDINGS-WEBUNBIND-01", "sourceIeee": sourceIeee, "IEEE2NWK": self.IEEE2NWK},
        )
        return

    if destIeee not in self.IEEE2NWK:
        self.log.logging(
            "Binding",
            "Error",
            "---> unknown destIeee: %s" % destIeee,
            None,
            {"Error code": "BINDINGS-WEBUNBIND-02", "destIeee": destIeee, "IEEE2NWK": self.IEEE2NWK},
        )
        return

    sourceNwkid = self.IEEE2NWK[sourceIeee]
    destNwkid = self.IEEE2NWK[destIeee]

    if sourceEp not in self.ListOfDevices[sourceNwkid]["Ep"]:
        self.log.logging(
            "Binding",
            "Error",
            "---> unknown sourceEp: %s for sourceNwkid: %s" % (sourceEp, sourceNwkid),
            sourceNwkid,
            {"Error code": "BINDINGS-WEBUNBIND-03", "sourceEp": sourceEp},
        )
        return
    self.log.logging(
        "Binding",
        "Debug",
        "UnBinding Device %s/%s with Device target %s/%s on Cluster: %s" % (sourceIeee, sourceEp, destIeee, destEp, Cluster),
        sourceNwkid,
    )
    if Cluster not in self.ListOfDevices[sourceNwkid]["Ep"][sourceEp]:
        self.log.logging(
            "Binding",
            "Error",
            "---> Cluster %s not find in %s --> %s" % (Cluster, sourceNwkid, self.ListOfDevices[sourceNwkid]["Ep"][sourceEp].keys()),
            sourceNwkid,
            {"Error code": "BINDINGS-WEBUNBIND-04", "Cluster": Cluster},
        )
        return
    self.log.logging(
        "Binding",
        "Debug",
        "UnBinding Device %s/%s with Device target %s/%s on Cluster: %s" % (sourceIeee, sourceEp, destIeee, destEp, Cluster),
        destNwkid,
    )

    if destEp not in self.ListOfDevices[destNwkid]["Ep"]:
        self.log.logging(
            "Binding",
            "Error",
            "---> unknown destEp: %s for destNwkid: %s" % (destEp, destNwkid),
            destNwkid,
            {"Error code": "BINDINGS-WEBUNBIND-05", "destEp": destEp, "destNwkid": destNwkid},
        )
        return

    mode = "03"  # IEEE
    #datas = str(sourceIeee) + str(sourceEp) + str(Cluster) + str(mode) + str(destIeee) + str(destEp)
    zdp_unbinding_device(self, sourceIeee , sourceEp , Cluster , mode , destIeee , destEp)
    #sendZigateCmd(self, "0031", datas)
    #self.log.logging("Binding", "Debug", "---> %s %s" % ("0031", datas), sourceNwkid)

    if (
        "WebBind" in self.ListOfDevices[sourceNwkid]
        and sourceEp in self.ListOfDevices[sourceNwkid]["WebBind"]
        and Cluster in self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp]
        and destNwkid in self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster]
    ):
        del self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]
        if len(self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster]) == 0:
            del self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster]
        if len(self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp]) == 0:
            del self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp]
        if len(self.ListOfDevices[sourceNwkid]["WebBind"]) == 0:
            del self.ListOfDevices[sourceNwkid]["WebBind"]

def WebBindStatus(self, sourceIeee, sourceEp, destIeee, destEp, Cluster):

    if sourceIeee not in self.IEEE2NWK:
        self.log.logging(
            "Binding",
            "Error",
            "---> unknown sourceIeee: %s" % sourceIeee,
            None,
            {"Error code": "BINDINGS-WEBBINDST-01", "sourceIeee": sourceIeee, "IEEE2NWK": self.IEEE2NWK},
        )
        return

    if destIeee not in self.IEEE2NWK:
        self.log.logging(
            "Binding",
            "Error",
            "---> unknown destIeee: %s" % destIeee,
            None,
            {"Error code": "BINDINGS-WEBBINDST-02", "destIeee": destIeee, "IEEE2NWK": self.IEEE2NWK},
        )
        return

    sourceNwkid = self.IEEE2NWK[sourceIeee]
    if "WebBind" in self.ListOfDevices[sourceNwkid] and sourceEp in self.ListOfDevices[sourceNwkid]["WebBind"] and Cluster in self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp]:
        destNwkid = self.IEEE2NWK[destIeee]

        if destNwkid in self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster] and "Phase" in self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]:
            return self.ListOfDevices[sourceNwkid]["WebBind"][sourceEp][Cluster][destNwkid]["Phase"]
    return None


def callBackForBindIfNeeded(self, srcNWKID):

    """
    Check that all Bind are well set
    """

    if srcNWKID not in self.ListOfDevices:
        return
    if "IEEE" not in self.ListOfDevices[srcNWKID]:
        return
    if "Bind" not in self.ListOfDevices[srcNWKID]:
        return

    sourceIeee = self.ListOfDevices[srcNWKID]["IEEE"]

    for Ep in list(self.ListOfDevices[srcNWKID]["Bind"]):
        for ClusterId in list(self.ListOfDevices[srcNWKID]["Bind"][Ep]):
            if "Phase" in self.ListOfDevices[srcNWKID]["Bind"][Ep][ClusterId] and self.ListOfDevices[srcNWKID]["Bind"][Ep][ClusterId]["Phase"] == "requested":

                if "Stamp" in self.ListOfDevices[srcNWKID]["Bind"][Ep][ClusterId] and time() < self.ListOfDevices[srcNWKID]["Bind"][Ep][ClusterId]["Stamp"] + 5:  # Let's wait 5s before trying again
                    continue

                self.log.logging(
                    "Binding",
                    "Debug",
                    "Redo a Bind for device that was in requested phase %s ClusterId %s" % (srcNWKID, ClusterId),
                    srcNWKID,
                )
                # Perforning the bind
                bindDevice(self, sourceIeee, Ep, ClusterId)

            elif ("Phase" in self.ListOfDevices[srcNWKID]["Bind"][Ep][ClusterId] and self.ListOfDevices[srcNWKID]["Bind"][Ep][ClusterId]["Phase"] == "binded") and ("i_sqn" not in self.ListOfDevices[srcNWKID]["Bind"][Ep][ClusterId]):
                # bind was done with i_sqn, we cant trust it, lets redo it
                self.log.logging(
                    "Binding",
                    "Debug",
                    "Redo a WebBind with sqn for device %s that was already binded" % (srcNWKID),
                    srcNWKID,
                )
                # Perforning the bind
                bindDevice(self, sourceIeee, Ep, ClusterId)


def callBackForWebBindIfNeeded(self, srcNWKID):

    """
    Check that WebBind are well set
    """

    if srcNWKID not in self.ListOfDevices:
        return
    if "WebBind" not in self.ListOfDevices[srcNWKID]:
        return

    for Ep in list(self.ListOfDevices[srcNWKID]["WebBind"]):
        for ClusterId in list(self.ListOfDevices[srcNWKID]["WebBind"][Ep]):
            for destNwkid in list(self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId]):
                if destNwkid not in self.ListOfDevices:
                    del self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]
                elif destNwkid in ("Stamp", "Target", "TargetIEEE", "SourceIEEE", "TargetEp", "Phase", "Status"):
                    self.log.logging(
                        "Binding",
                        "Error",
                        "---> delete  destNwkid: %s" % (destNwkid),
                        destNwkid,
                        {"Error code": "BINDINGS-CALLBACK-01"},
                    )
                    del self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]
                elif "Phase" in self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid] and self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]["Phase"] == "requested":

                    if "Stamp" in self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid] and time() < self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]["Stamp"] + 5:  # Let's wait 5s before trying again
                        continue

                    self.log.logging("Binding", "Debug", "Redo a WebBind for device %s" % (srcNWKID), srcNWKID)
                    sourceIeee = self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]["SourceIEEE"]
                    destIeee = self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]["TargetIEEE"]
                    destEp = self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]["TargetEp"]
                    # Perforning the bind
                    webBind(self, sourceIeee, Ep, destIeee, destEp, ClusterId)

                elif ("Phase" in self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid] and self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]["Phase"] == "binded") and (
                    "i_sqn" not in self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]
                ):
                    # bind was done with i_sqn, we cant trust it, lets redo it
                    self.log.logging("Binding", "Debug", "Redo a WebBind with sqn for device %s" % (srcNWKID), srcNWKID)
                    sourceIeee = self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]["SourceIEEE"]
                    destIeee = self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]["TargetIEEE"]
                    destEp = self.ListOfDevices[srcNWKID]["WebBind"][Ep][ClusterId][destNwkid]["TargetEp"]
                    # Perforning the bind
                    webBind(self, sourceIeee, Ep, destIeee, destEp, ClusterId)
