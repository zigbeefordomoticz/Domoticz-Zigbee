#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import json
import os
import os.path
from time import time
from datetime import datetime

from WebServer.headerResponse import setupHeadersResponse, prepResponseMessage


def rest_req_topologie( self, verb, data, parameters):

    _response = prepResponseMessage( self ,setupHeadersResponse(  ))

    if verb == 'GET':
        action = {'Name': 'Req-Topology', 'TimeStamp': int(time())}
        _response["Data"] = json.dumps( action, sort_keys=True )

        self.logging( 'Log', "Request a Start of Network Topology scan")
        if self.networkmap:
            if not self.networkmap.NetworkMapPhase():
                self.networkmap.start_scan()
            else:
                self.logging( 'Log', "Cannot start Network Topology as one is in progress...")
                
    return _response
      
def rest_netTopologie( self, verb, data, parameters):

    _response = prepResponseMessage( self ,setupHeadersResponse(  ))

    _filename = self.pluginconf.pluginConf['pluginReports'] + 'NetworkTopology-v3-' + '%02d' %self.hardwareID + '.json'
    self.logging( 'Debug', "Filename: %s" %_filename)

    if not os.path.isfile( _filename ) :
        _response['Data'] = json.dumps( {} , sort_keys=True ) 
        return _response

    # Read the file, as we have anyway to do it
    _topo = {}           # All Topo reports
    _timestamps_lst = [] # Just the list of Timestamps
    with open( _filename , 'rt') as handle:
        for line in handle:
            if line[0] != '{' and line[-1] != '}': 
                continue
            
            entry = json.loads( line, encoding=dict )
            for _ts in entry:
                _timestamps_lst.append( int(_ts) )
                _topo[_ts] = [] # List of Father -> Child relation for one TimeStamp
                _check_duplicate = []
                _nwkid_list = []
                reportLQI = entry[_ts]

                for item in reportLQI:
                    self.logging( 'Debug', "Node: %s" %item)
                    if item != '0000' and item not in self.ListOfDevices:
                        continue

                    if item not in _nwkid_list:
                        _nwkid_list.append( item )
                    for x in  reportLQI[item]['Neighbours']:
                        self.logging( 'Debug', "---> %s" %x)
                        # Report only Child relationship
                        if x != '0000' and x not in self.ListOfDevices: 
                            continue

                        if item == x: 
                            continue

                        if 'Neighbours' not in reportLQI[item]:
                            Domoticz.Error("Missing attribute :%s for (%s,%s)" %('Neighbours', item, x))
                            continue

                        for attribute in ( '_relationshp', '_lnkqty', '_devicetype', '_depth' ):
                            if attribute not in reportLQI[item]['Neighbours'][x]:
                                Domoticz.Error("Missing attribute :%s for (%s,%s)" %(attribute, item, x))
                                continue

                        if x not in _nwkid_list:
                            _nwkid_list.append( x )
                        
                        # We need to reorganise in Father/Child relationship.
                        if reportLQI[item]['Neighbours'][x]['_relationshp'] == 'Parent':
                            _father = item
                            _child  = x

                        elif reportLQI[item]['Neighbours'][x]['_relationshp'] == 'Child':
                            _father = x
                            _child = item

                        elif reportLQI[item]['Neighbours'][x]['_relationshp'] == 'Sibling':
                            _father = item
                            _child  = x

                        elif reportLQI[item]['Neighbours'][x]['_relationshp'] == 'Former Child':
                            # Not a Parent, not a Child, not a Sibbling
                            #_father = item
                            #_child  = x
                            continue

                        elif reportLQI[item]['Neighbours'][x]['_relationshp'] == 'None':
                            # Not a Parent, not a Child, not a Sibbling
                            #_father = item
                            #_child  = x
                            continue
                    
                        _relation = {}
                        _relation['Father'] = _father
                        _relation['Child'] = _child
                        _relation["_lnkqty"] = int(reportLQI[item]['Neighbours'][x]['_lnkqty'], 16)
                        _relation["DeviceType"] = reportLQI[item]['Neighbours'][x]['_devicetype']

                        if _father != "0000":
                            if 'ZDeviceName' in self.ListOfDevices[_father]:
                                if self.ListOfDevices[_father]['ZDeviceName'] != "" and self.ListOfDevices[_father]['ZDeviceName'] != {}:
                                    #_relation[master] = self.ListOfDevices[_father]['ZDeviceName']
                                    _relation['Father'] = self.ListOfDevices[_father]['ZDeviceName']
                        else:
                            _relation['Father'] = "Zigate"

                        if _child != "0000":
                            if 'ZDeviceName' in self.ListOfDevices[_child]:
                                if self.ListOfDevices[_child]['ZDeviceName'] != "" and self.ListOfDevices[_child]['ZDeviceName'] != {}:
                                    #_relation[slave] = self.ListOfDevices[_child]['ZDeviceName']
                                    _relation['Child'] = self.ListOfDevices[_child]['ZDeviceName']
                        else:
                            _relation['Child'] = "Zigate"

                        # Sanity check, remove the direct loop
                        if ( _relation['Child'], _relation['Father'] ) in _check_duplicate:
                            self.logging( 'Debug', "Skip (%s,%s) as there is already ( %s, %s)" %(_relation['Father'], _relation['Child'], _relation['Child'], _relation['Father']))
                            continue

                        _check_duplicate.append( ( _relation['Father'], _relation['Child']))
                        self.logging( 'Debug', "%10s Relationship - %15.15s - %15.15s %3s %2s" \
                            %( _ts, _relation['Father'], _relation['Child'], _relation["_lnkqty"],
                                    reportLQI[item]['Neighbours'][x]['_depth']))
                        _topo[_ts].append( _relation )
                    #end for x
                #end for item

                # Sanity check, to see if all devices are part of the report.
                # for iterDev in self.ListOfDevices:
                #     if iterDev in _nwkid_list: continue
                #     if 'Status' not in self.ListOfDevices[iterDev]: continue
                #     if self.ListOfDevices[iterDev]['Status'] != 'inDB': continue
                #    self.logging( 'Debug', "Nwkid %s has not been reported by this scan" %iterDev)
                #    _relation = {}
                #    _relation['Father'] = _relation['Child'] = iterDev
                #    _relation['_lnkqty'] = 0
                #    _relation['DeviceType'] = ''
                #    if 'ZDeviceName' in self.ListOfDevices[iterDev]:
                #        if self.ListOfDevices[iterDev]['ZDeviceName'] != "" and self.ListOfDevices[iterDev]['ZDeviceName'] != {}:
                #            _relation['Father'] = _relation['Child'] = self.ListOfDevices[iterDev]['ZDeviceName']
                #    _topo[_ts].append( _relation )

            #end for _st

    if verb == 'DELETE':
        if len(parameters) == 0:
            os.remove( _filename )
            action = {}
            action['Name'] = 'File-Removed'
            action['FileName'] = _filename
            _response['Data'] = json.dumps( action , sort_keys=True)

        elif len(parameters) == 1:
            timestamp = parameters[0]
            if timestamp in _topo:
                self.logging( 'Debug', "Removing Report: %s from %s records" %(timestamp, len(_topo)))
                with open( _filename, 'r+') as handle:
                    d = handle.readlines()
                    handle.seek(0)
                    for line in d:
                        if line[0] != '{' and line[-1] != '}':
                            handle.write( line )
                            continue
                        entry = json.loads( line, encoding=dict )
                        entry_ts = entry.keys()
                        if len( entry_ts ) == 1:
                            if timestamp in entry_ts:
                                self.logging( 'Debug', "--------> Skiping %s" %timestamp)
                                continue
                        else:
                            continue
                        handle.write( line )
                    handle.truncate()

                action = {}
                action['Name'] = 'Report %s removed' %timestamp
                _response['Data'] = json.dumps( action , sort_keys=True)
            else:
                Domoticz.Error("Removing Topo Report %s not found" %timestamp )
                _response['Data'] = json.dumps( [] , sort_keys=True)
        return _response

    if verb == 'GET':
        if len(parameters) == 0:
            # Send list of Time Stamps
            _response['Data'] = json.dumps( _timestamps_lst , sort_keys=True)

        elif len(parameters) == 1:
            timestamp = parameters[0]
            if timestamp in _topo:
                self.logging( 'Debug', "Topologie sent: %s" %_topo[timestamp])
                _response['Data'] = json.dumps( _topo[timestamp] , sort_keys=True)
            else:
                _response['Data'] = json.dumps( [] , sort_keys=True)

    return _response
