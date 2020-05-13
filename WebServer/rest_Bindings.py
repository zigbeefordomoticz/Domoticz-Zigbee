#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz
import json

from Modules.zigateConsts import ZCL_CLUSTERS_ACT
from Modules.bindings import webBind, webUnBind
from WebServer.headerResponse import setupHeadersResponse


def rest_bindLSTcluster( self, verb, data, parameters):
    _response = setupHeadersResponse()
    if self.pluginconf.pluginConf['enableKeepalive']:
        _response["Headers"]["Connection"] = "Keep-alive"
    else:
        _response["Headers"]["Connection"] = "Close"
    _response["Status"] = "200 OK"
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

    bindCluster = []
    for key in self.ListOfDevices:
        if key == '0000': 
            continue

        for ep in self.ListOfDevices[key]['Ep']:
            for cluster in self.ListOfDevices[key]['Ep'][ep]:
                if cluster in ZCL_CLUSTERS_ACT and cluster not in bindCluster:
                    bindCluster.append( cluster )
    _response["Data"] = json.dumps( bindCluster )
    return _response

def rest_bindLSTdevice( self, verb, data, parameters):

    _response = setupHeadersResponse()
    if self.pluginconf.pluginConf['enableKeepalive']:
        _response["Headers"]["Connection"] = "Keep-alive"
    else:
        _response["Headers"]["Connection"] = "Close"
    _response["Status"] = "200 OK"
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
    if len(parameters) == 1:
        listofdevices = []
        clustertobind = parameters[0]
        for key in self.ListOfDevices:
            if key == '0000': 
                continue

            for ep in self.ListOfDevices[key]['Ep']:
                if clustertobind in self.ListOfDevices[key]['Ep'][ep]:
                    dev = {
                        'IEEE': self.ListOfDevices[key]['IEEE'],
                        'NwkId': key,
                        'Ep': ep,
                        'ZDeviceName': self.ListOfDevices[key]['ZDeviceName'],
                    }

                    if dev not in listofdevices:
                        listofdevices.append( dev )
        _response["Data"] = json.dumps( listofdevices )
    else:
        Domoticz.Error("Must have 1 argument. %s" %parameters)
    return _response

def rest_binding( self, verb, data, parameters):
    _response = setupHeadersResponse()
    if self.pluginconf.pluginConf['enableKeepalive']:
        _response["Headers"]["Connection"] = "Keep-alive"
    else:
        _response["Headers"]["Connection"] = "Close"
    _response["Status"] = "200 OK"
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

    if verb == 'PUT':
        _response["Data"] = None
        if len(parameters) == 0:
            data = data.decode('utf8')
            data = json.loads(data)

            if 'sourceIeee' not in data and \
                    'sourceEp' not in data and \
                    'destIeee' not in data and \
                    'destEp' not in data and \
                    'cluster' not in data:
                Domoticz.Log("-----> uncomplet json %s" %data)
                _response["Data"] = json.dumps("uncomplet json %s" %data)
                return _response

            self.logging( 'Log', "rest_binding - Source: %s/%s Dest: %s/%s Cluster: %s" %(data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp'], data['cluster']))
            webBind( self, data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp'], data['cluster'] )
            _response["Data"] = json.dumps( "Binding cluster %s between %s/%s and %s/%s" %(data['cluster'], data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp']))
            return _response

def rest_unbinding( self, verb, data, parameters):
    _response = setupHeadersResponse()
    if self.pluginconf.pluginConf['enableKeepalive']:
        _response["Headers"]["Connection"] = "Keep-alive"
    else:
        _response["Headers"]["Connection"] = "Close"
    _response["Status"] = "200 OK"
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

    if verb == 'PUT':
        _response["Data"] = None
        if len(parameters) == 0:
            data = data.decode('utf8')
            data = json.loads(data)

            if 'sourceIeee' not in data and \
                    'sourceEp' not in data and \
                    'destIeee' not in data and \
                    'destEp' not in data and \
                    'cluster' not in data:
                Domoticz.Log("-----> uncomplet json %s" %data)
                _response["Data"] = json.dumps("uncomplet json %s" %data)
                return _response

            self.logging( 'Log', "rest_unbinding - Source: %s/%s Dest: %s/%s Cluster: %s" %(data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp'], data['cluster']))
            webUnBind( self, data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp'], data['cluster'] )
            _response["Data"] = json.dumps( "Binding cluster %s between %s/%s and %s/%s" %(data['cluster'], data['sourceIeee'], data['sourceEp'], data['destIeee'], data['destEp']))
            return _response