#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
from time import time
from Modules.output import sendZigateCmd
from Modules.logging import loggingOutput
from Modules.zigateConsts import CLUSTERS_LIST


def bindGroup( self, ieee, ep, cluster, groupid ):

    mode = "01"     # Group mode
    nwkid = 'ffff'
    if ieee in self.IEEE2NWK:
        nwkid = self.IEEE2NWK[ieee]

    loggingOutput( self, 'Debug', "bindGroup - ieee: %s, ep: %s, cluster: %s, Group: %s" %(ieee,ep,cluster,groupid) , nwkid=nwkid)
    datas =  ieee + ep + cluster + mode + groupid
    sendZigateCmd(self, "0030", datas )


def unbindGroup( self, ieee , ep, cluster, groupid):

    mode = "01"     # Group mode
    nwkid = 'ffff'
    if ieee in self.IEEE2NWK:
        nwkid = self.IEEE2NWK[ieee]

    loggingOutput( self, 'Debug', "unbindGroup - ieee: %s, ep: %s, cluster: %s, Group: %s" %(ieee,ep,cluster,groupid) , nwkid=nwkid)
    datas =  ieee + ep + cluster + mode + groupid
    sendZigateCmd(self, "0031", datas )



def bindDevice( self, ieee, ep, cluster, destaddr=None, destep="01"):
    '''
    Binding a device/cluster with ....
    if not destaddr and destep provided, we will assume that we bind this device with the Zigate coordinator

    ATTENTION:
    In case overwriteZigateEpBind is set, we will use that one instead of the despEp
    '''

    if not destaddr:
        #destaddr = self.ieee # Let's grab the IEEE of Zigate
        if self.ZigateIEEE is not None and self.ZigateIEEE != '':
            destaddr = self.ZigateIEEE
        else:
            loggingOutput( self, 'Debug', "bindDevice - self.ZigateIEEE not yet initialized")
            return

    if ieee in self.IEEE2NWK:
        nwkid = self.IEEE2NWK[ieee]
        if nwkid in self.ListOfDevices:

            # Very bad Hack, but at that stage, there is no other information we can Use. PROFALUX
            if (self.ListOfDevices[nwkid]['ProfileID'] == '0104' and self.ListOfDevices[nwkid]['ZDeviceID'] == '0201'):    # Remote
                # Do not bind Remote Command
                loggingOutput( self, 'Log',"----> Do not bind cluster %s for Profalux Remote command %s/%s" \
                    %(cluster, nwkid, ep), nwkid)
                return

            if ('Model' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]['Model'] != {}):
                _model = self.ListOfDevices[nwkid]['Model']
                if _model in self.DeviceConf:
                    # Bind and use Zigate Endpoint specified as overwriteZigateEpBind
                    if 'overwriteZigateEpBind' in self.DeviceConf[ _model ]:
                        destep = self.DeviceConf[ _model ]['overwriteZigateEpBind']
                        loggingOutput( self, 'Log',"----> %s/%s on %s overwrite Zigate Endpoint for bind and use %s" \
                                    %(nwkid, ep, cluster, destep))

                    # For to Bind only the Configured Clusters
                    if ('ClusterToBind' in self.DeviceConf[_model] and cluster not in self.DeviceConf[_model]['ClusterToBind']):
                        loggingOutput( self, 'Debug',"----> Do not bind cluster %s due to Certified Conf for %s/%s" \
                                %(cluster, nwkid, ep), nwkid)
                        return

                    # Bind only on those source Endpoint
                    if ('bindEp' in self.DeviceConf[_model] and ep not in self.DeviceConf[_model]['bindEp']):
                        loggingOutput( self, 'Debug',"Do not Bind %s to Zigate Ep %s Cluster %s" \
                                %(_model, ep, cluster), nwkid)
                        return

    nwkid = self.IEEE2NWK[ieee]
    if 'Bind' not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]['Bind'] = {}

    if ep not in self.ListOfDevices[nwkid]['Bind']:
        self.ListOfDevices[nwkid]['Bind'][ep] = {}

    if cluster not in self.ListOfDevices[nwkid]['Bind'][ep]:
        self.ListOfDevices[nwkid]['Bind'][ep][cluster] = {}
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Target'] = '0000' # Zigate
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Stamp'] = int(time())
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Phase'] = 'requested'
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Status'] = ''

        loggingOutput( self, 'Debug', "bindDevice - ieee: %s, ep: %s, cluster: %s, Zigate_ieee: %s, Zigate_ep: %s" \
                %(ieee,ep,cluster,destaddr,destep) , nwkid=nwkid)

        # Read to bind
        mode = "03"     # Addres Mode to use

        datas =  str(ieee)+str(ep)+str(cluster)+str(mode)+str(destaddr)+str(destep)
        sendZigateCmd(self, "0030", datas )

    return

def rebind_Clusters( self, NWKID):

    cluster_to_bind = CLUSTERS_LIST

    # Checking if anything must be done before Bindings, and if we have to take some specific bindings
    if 'Model' in self.ListOfDevices[NWKID]:
        _model = self.ListOfDevices[NWKID]['Model']
        if _model != {}:   
            if _model in self.DeviceConf:
                # Check if we have to unbind clusters
                if 'ClusterToUnbind' in self.DeviceConf[ _model ]:
                    for iterEp, iterUnBindCluster in self.DeviceConf[ _model ]['ClusterToUnbind']:
                        unbindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterUnBindCluster)

        # User Configuration if exists
            if self.ListOfDevices[NWKID]['Model'] in self.DeviceConf:
                if 'ClusterToBind' in self.DeviceConf[ _model ]:
                    cluster_to_bind = self.DeviceConf[ _model ]['ClusterToBind']

    # If Bind information, then remove it
    if 'Bind' in self.ListOfDevices[NWKID]:
        del self.ListOfDevices[NWKID]['Bind']

    # If allow Unbind before Bind, then Unbind
    if self.pluginconf.pluginConf['doUnbindBind']:
        for iterBindCluster in cluster_to_bind:
            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                if iterBindCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                    loggingOutput( self, 'Debug', 'Request an Unbind for %s/%s on Cluster %s' %(NWKID, iterEp, iterBindCluster), nwkid=NWKID)
                    unbindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)

    # Bind
    for iterBindCluster in cluster_to_bind:
        for iterEp in self.ListOfDevices[NWKID]['Ep']:
            if iterBindCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                loggingOutput( self, 'Debug', 'Request a Bind  for %s/%s on Cluster %s' %(NWKID, iterEp, iterBindCluster), nwkid=NWKID)
                bindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)

def unbindDevice( self, ieee, ep, cluster, destaddr=None, destep="01"):
    '''
    unbind
    '''

    mode = "03"     # IEEE
    if not destaddr:
        #destaddr = self.ieee # Let's grab the IEEE of Zigate
        if self.ZigateIEEE is not None and self.ZigateIEEE != '':
            destaddr = self.ZigateIEEE
            destep = "01"
        else:
            loggingOutput( self, 'Debug', "bindDevice - self.ZigateIEEE not yet initialized")
            return

    nwkid = self.IEEE2NWK[ieee]

    # If doing unbind, the Configure Reporting is lost
    if 'ConfigureReporting' in self.ListOfDevices[nwkid]:
        del  self.ListOfDevices[nwkid]['ConfigureReporting']

    # Remove the Bind
    if (
        'Bind' in self.ListOfDevices[nwkid]
        and ep in self.ListOfDevices[nwkid]['Bind']
        and cluster in self.ListOfDevices[nwkid]['Bind'][ep]
    ):
        del self.ListOfDevices[nwkid]['Bind'][ep][cluster]

    loggingOutput( self, 'Debug', "unbindDevice - ieee: %s, ep: %s, cluster: %s, Zigate_ieee: %s, Zigate_ep: %s" %(ieee,ep,cluster,destaddr,destep) , nwkid=nwkid)
    datas = str(ieee) + str(ep) + str(cluster) + str(mode) + str(destaddr) + str(destep)
    sendZigateCmd(self, "0031", datas )

    return

def webBind( self, sourceIeee, sourceEp, destIeee, destEp, Cluster):

    if sourceIeee not in self.IEEE2NWK:
        Domoticz.Error("---> unknown sourceIeee: %s" %sourceIeee)
        return

    if destIeee not in self.IEEE2NWK:
        Domoticz.Error("---> unknown destIeee: %s" %destIeee)
        return

    sourceNwkid = self.IEEE2NWK[sourceIeee]
    destNwkid = self.IEEE2NWK[destIeee]


    if sourceEp not in self.ListOfDevices[sourceNwkid]['Ep']:
        Domoticz.Error("---> unknown sourceEp: %s for sourceNwkid: %s" %(sourceEp, sourceNwkid))
        return
    loggingOutput( self, 'Debug', "Binding Device %s/%s with Device target %s/%s on Cluster: %s" %(sourceIeee, sourceEp, destIeee, destEp, Cluster), sourceNwkid)
    if Cluster not in self.ListOfDevices[sourceNwkid]['Ep'][sourceEp]:
        Domoticz.Error("---> Cluster %s not find in %s --> %s" %( Cluster, sourceNwkid, self.ListOfDevices[sourceNwkid]['Ep'][sourceEp].keys()))
        return
    loggingOutput( self, 'Debug', "Binding Device %s/%s with Device target %s/%s on Cluster: %s" %(sourceIeee, sourceEp, destIeee, destEp, Cluster), destNwkid)

    if destEp not in self.ListOfDevices[destNwkid]['Ep']:
        Domoticz.Error("---> unknown destEp: %s for destNwkid: %s" %(destEp, destNwkid))
        return

    mode = "03"     # IEEE
    datas =  str(sourceIeee)+str(sourceEp)+str(Cluster)+str(mode)+str(destIeee)+str(destEp)
    sendZigateCmd(self, "0030", datas )
    loggingOutput( self, 'Debug', "---> %s %s" %("0030", datas), sourceNwkid)

    if 'WebBind' not in self.ListOfDevices[sourceNwkid]:
        self.ListOfDevices[sourceNwkid]['WebBind'] = {}
    if sourceEp not in self.ListOfDevices[sourceNwkid]['WebBind']:
        self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp] = {}
    if Cluster not in self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp]:
        self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster] = {}
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster] = {}
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['SourceIEEE'] = sourceIeee
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['Target'] = destNwkid
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['TargetIEEE'] = destIeee
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['TargetEp'] = destEp
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['Stamp'] = int(time())
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['Phase'] = 'requested'
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['Status'] = ''


def webUnBind( self, sourceIeee, sourceEp, destIeee, destEp, Cluster):

    if sourceIeee not in self.IEEE2NWK:
        Domoticz.Error("---> unknown sourceIeee: %s" %sourceIeee)
        return

    if destIeee not in self.IEEE2NWK:
        Domoticz.Error("---> unknown destIeee: %s" %destIeee)
        return

    sourceNwkid = self.IEEE2NWK[sourceIeee]
    destNwkid = self.IEEE2NWK[destIeee]

    if sourceEp not in self.ListOfDevices[sourceNwkid]['Ep']:
        Domoticz.Error("---> unknown sourceEp: %s for sourceNwkid: %s" %(sourceEp, sourceNwkid))
        return
    loggingOutput( self, 'Debug', "UnBinding Device %s/%s with Device target %s/%s on Cluster: %s" %(sourceIeee, sourceEp, destIeee, destEp, Cluster), sourceNwkid)
    if Cluster not in self.ListOfDevices[sourceNwkid]['Ep'][sourceEp]:
        Domoticz.Error("---> Cluster %s not find in %s --> %s" %( Cluster, sourceNwkid, self.ListOfDevices[sourceNwkid]['Ep'][sourceEp].keys()))
        return
    loggingOutput( self, 'Debug', "UnBinding Device %s/%s with Device target %s/%s on Cluster: %s" %(sourceIeee, sourceEp, destIeee, destEp, Cluster), destNwkid)

    if destEp not in self.ListOfDevices[destNwkid]['Ep']:
        Domoticz.Error("---> unknown destEp: %s for destNwkid: %s" %(destEp, destNwkid))
        return

    mode = "03"     # IEEE
    datas =  str(sourceIeee)+str(sourceEp)+str(Cluster)+str(mode)+str(destIeee)+str(destEp)
    sendZigateCmd(self, "0031", datas )
    loggingOutput( self, 'Debug', "---> %s %s" %("0031", datas), sourceNwkid)

    if (
        'WebBind' in self.ListOfDevices[sourceNwkid]
        and sourceEp in self.ListOfDevices[sourceNwkid]['WebBind']
        and Cluster in self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp]
    ):
        del self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]
        if len(self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp]) == 0:
            del self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp]
        if len(self.ListOfDevices[sourceNwkid]['WebBind']) == 0:
            del self.ListOfDevices[sourceNwkid]['WebBind']



def callBackForWebBindIfNeeded( self , srcNWKID ):

    """
    Check that WebBind are well set
    """

    if srcNWKID not in self.ListOfDevices:
        return
    if 'WebBind' not in self.ListOfDevices[srcNWKID]:
        return

    for Ep in list(self.ListOfDevices[srcNWKID]['WebBind']):
        for ClusterId in list(self.ListOfDevices[srcNWKID]['WebBind'][ Ep ]):
            if ('Phase' in self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId] and self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId]['Phase']== 'requested'):
                if ('Stamp' in self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId] and time() < self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId]['Stamp']+ 5):    # Let's wait 5s before trying again
                    continue
                loggingOutput( self, 'Log', "Redo a WebBind for device %s" %(srcNWKID))
                sourceIeee = self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId]['SourceIEEE']
                destIeee = self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId]['TargetIEEE']
                destEp = self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId]['TargetEp']
                # Perforning the bind
                webBind(self, sourceIeee, Ep, destIeee, destEp, ClusterId)

                self.ListOfDevices[srcNWKID]['WebBind'][Ep][ClusterId]['Stamp'] = int(time())
