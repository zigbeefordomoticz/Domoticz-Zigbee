#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import json
import os
import os.path
import mimetypes

from time import time

from Modules.zigateConsts import  ZCL_CLUSTERS_LIST , CERTIFICATION_CODE,  ZIGATE_COMMANDS

from Modules.basicOutputs import ZigatePermitToJoin, sendZigateCmd, start_Zigate, setExtendedPANID, zigateBlueLed
from Modules.legrand_netatmo import legrand_ledInDark, legrand_ledIfOnOnOff, legrand_dimOnOff, legrand_ledShutter
from Modules.actuators import actuators
from Modules.tools import is_hex
from Classes.PluginConf import PluginConf,SETTINGS
from GroupMgt.GroupMgt import GroupsManagement
from Classes.DomoticzDB import DomoticzDB_Preferences

from WebServer.headerResponse import setupHeadersResponse, prepResponseMessage

MIMETYPES = { 
        "gif": "image/gif" ,
        "htm": "text/html" ,
        "html": "text/html" ,
        "jpg": "image/jpeg" ,
        "png": "image/png" ,
        "css": "text/css" ,
        "xml": "application/xml" ,
        "js": "application/javascript" ,
        "json": "application/json" ,
        "swf": "application/x-shockwave-flash" ,
        "manifest": "text/cache-manifest" ,
        "appcache": "text/cache-manifest" ,
        "xls": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ,
        "m3u": "audio/mpegurl" ,
        "mp3": "audio/mpeg" ,
        "ogg": "audio/ogg" ,
        "php": "text/html" ,
        "wav": "audio/x-wav" ,
        "svg": "image/svg+xml" ,
        "db": "application/octet-stream" ,
        "otf": "application/x-font-otf" ,
        "ttf": "application/x-font-ttf" ,
        "woff": "application/x-font-woff" 
   }

class WebServer(object):

    from WebServer.com import startWebServer, onStop, onConnect, onDisconnect
    from WebServer.dispatcher import do_rest  
    from WebServer.logging import logging
    from WebServer.onMessage import onMessage
    from WebServer.rest_Bindings import rest_bindLSTcluster, rest_bindLSTdevice, rest_binding, rest_unbinding
    from WebServer.rest_Energy import rest_req_nwk_full, rest_req_nwk_inter
    from WebServer.rest_Groups import rest_zGroup, rest_zGroup_lst_avlble_dev
    from WebServer.rest_Provisioning import rest_new_hrdwr, rest_rcv_nw_hrdwr
    from WebServer.rest_Topology import rest_netTopologie, rest_req_topologie
    from WebServer.sendresponse import sendResponse
    from WebServer.tools import keepConnectionAlive, DumpHTTPResponseToLog          

    hearbeats = 0 

    def __init__( self, networkenergy, networkmap, ZigateData, PluginParameters, PluginConf, Statistics, adminWidgets, ZigateComm, HomeDirectory, hardwareID, DevicesInPairingMode, groupManagement, Devices, ListOfDevices, IEEE2NWK , permitTojoin, WebUserName, WebPassword, PluginHealth, httpPort, loggingFileHandle):

        self.httpServerConn = None
        self.httpClientConn = None
        self.httpServerConns = {}
        self.httpPort = httpPort
        self.loggingFileHandle = loggingFileHandle

        self.httpsServerConn = None
        self.httpsClientConn = None
        self.httpsServerConns = {}
        self.httpsPort = None

        self.PluginHealth = PluginHealth
        self.WebUsername = WebUserName
        self.WebPassword = WebPassword
        self.pluginconf = PluginConf
        self.zigatedata = ZigateData
        self.adminWidget = adminWidgets
        self.ZigateComm = ZigateComm
        self.statistics = Statistics
        self.pluginparameters = PluginParameters
        self.networkmap = networkmap
        self.networkenergy = networkenergy

        self.permitTojoin = permitTojoin

        self.groupmgt = groupManagement if groupManagement else None
        self.ListOfDevices = ListOfDevices
        self.DevicesInPairingMode = DevicesInPairingMode
        self.fakeDevicesInPairingMode = 0
        self.IEEE2NWK = IEEE2NWK
        self.Devices = Devices

        self.restart_needed = {'RestartNeeded': False}
        self.homedirectory = HomeDirectory
        self.hardwareID = hardwareID
        mimetypes.init()
        # Start the WebServer
        self.startWebServer( )                    

    def rest_plugin_health( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())
        if self.pluginconf.pluginConf['enableKeepalive']:
            _response["Headers"]["Connection"] = "Keep-alive"
        else:
            _response["Headers"]["Connection"] = "Close"
        if not self.pluginconf.pluginConf['enableCache']:
            _response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
            _response["Headers"]["Pragma"] = "no-cache"
            _response["Headers"]["Expires"] = "0"
            _response["Headers"]["Accept"] = "*/*"

        _response["Status"] = "200 OK"
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            health = {
                'HealthFlag': self.PluginHealth['Flag'],
                'HealthTxt': self.PluginHealth['Txt'], }

            if 'Firmware Update' in self.PluginHealth:
                health['OTAupdateProgress'] = self.PluginHealth['Firmware Update']['Progress']
                health['OTAupdateDevice'] = self.PluginHealth['Firmware Update']['Device']

            if self.groupmgt:
                health['GroupStatus'] = self.groupmgt.StartupPhase

            _response["Data"] = json.dumps( health, sort_keys=True )

        return _response
                    
    def rest_zigate_erase_PDM( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())





        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            self.logging( 'Status', "Erase Zigate PDM")
            Domoticz.Error("Erase Zigate PDM non implémenté pour l'instant")
            if self.pluginconf.pluginConf['eraseZigatePDM']:
                if self.pluginparameters['Mode1'] != 'None':
                    sendZigateCmd(self, "0012", "")
                self.pluginconf.pluginConf['eraseZigatePDM'] = 0

            if self.pluginconf.pluginConf['extendedPANID'] is not None:
                self.logging( 'Status', "ZigateConf - Setting extPANID : 0x%016x" %( self.pluginconf.pluginConf['extendedPANID'] ))
                if self.pluginparameters['Mode1'] != 'None':
                    setExtendedPANID(self, self.pluginconf.pluginConf['extendedPANID'])
            action = {'Description': 'Erase Zigate PDM - Non Implemente'}
                #if self.pluginparameters['Mode1'] != 'None':
                #    start_Zigate( self )
        return _response

    def rest_rescan_group( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())
 
 
 
 
 
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        action = {}
        if verb == 'GET':
            self.groupListFileName = self.pluginconf.pluginConf['pluginData'] + "/GroupsList-%02d.pck" %self.hardwareID
            JsonGroupConfigFileName = self.pluginconf.pluginConf['pluginData'] + "/ZigateGroupsConfig-%02d.json" %self.hardwareID
            TxtGroupConfigFileName = self.pluginconf.pluginConf['pluginConfig'] + "/ZigateGroupsConfig-%02d.txt" %self.hardwareID
            for filename in ( TxtGroupConfigFileName, JsonGroupConfigFileName, self.groupListFileName ):
                if os.path.isfile( filename ):
                    self.logging( 'Debug', "rest_rescan_group - Removing file: %s" %filename )
                    os.remove( filename )
                    self.restart_needed['RestartNeeded'] = True
            action['Name'] = 'Groups file removed.'
            action['TimeStamp'] = int(time())

        _response["Data"] = json.dumps( action , sort_keys=True )

        return _response

    def rest_reset_zigate( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())
        if verb == 'GET':
            if self.pluginparameters['Mode1'] != 'None':
                self.zigatedata['startZigateNeeded'] = True
                #start_Zigate( self )
                sendZigateCmd(self, "0011", "" ) # Software Reset
            action = {'Name': 'Software reboot of Zigate', 'TimeStamp': int(time())}
        _response["Data"] = json.dumps( action , sort_keys=True )
        return _response

    def rest_zigate( self, verb, data, parameters):

        _response = setupHeadersResponse()
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            if self.zigatedata:
                _response["Data"] = json.dumps( self.zigatedata, sort_keys=True )
            else:
                fake_zigate = {
                    'Firmware Version': 'fake - 0310',
                    'IEEE': '00158d0001ededde',
                    'Short Address': '0000',
                    'Channel': '0b',
                    'PANID': '51cf',
                    'Extended PANID': 'bd1247ec9d358634',
                }

                _response["Data"] = json.dumps( fake_zigate , sort_keys=True )
        return _response

    def rest_domoticz_env( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
                
                dzenv = {}
                #dzenv['proto'] = self.pluginconf.pluginConf['proto']
                #dzenv['host'] = self.pluginconf.pluginConf['host']
                dzenv['port'] = self.pluginconf.pluginConf['port']

                dzenv['WebUserName'] = self.WebUsername
                dzenv['WebPassword'] = self.WebPassword

                _response["Data"] = json.dumps( dzenv, sort_keys=True )
        return _response

    def rest_PluginEnv( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())     
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
                _response["Data"] = json.dumps( self.pluginparameters, sort_keys=True )
        return _response

    def rest_nwk_stat( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())

        _filename = self.pluginconf.pluginConf['pluginReports'] + 'NetworkEnergy-v3-' + '%02d' %self.hardwareID + '.json'

        _timestamps_lst = [] # Just the list of Timestamps
        _scan = {}
        if os.path.isfile( _filename ):
            self.logging( 'Debug', "Opening file: %s" %_filename)
            with open( _filename , 'rt') as handle:
                for line in handle:
                    if not (line[0] == '{' or line[-1] == '}'):
                        continue

                    entry = json.loads( line, encoding=dict )
                    for _ts in entry:
                        _timestamps_lst.append( _ts )
                        _scan[_ts] = entry[ _ts ]

        if verb == 'DELETE':
            if len(parameters) == 0:
                #os.remove( _filename )
                action = {'Name': 'File-Removed', 'FileName': _filename}
                _response['Data'] = json.dumps( action , sort_keys=True)

            elif len(parameters) == 1:
                timestamp = parameters[0]
                if timestamp in _timestamps_lst:
                    self.logging( 'Debug', "Removing Report: %s from %s records" %(timestamp, len(_timestamps_lst)))
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

                    action = {'Name': 'Report %s removed' % timestamp}
                    _response['Data'] = json.dumps( action , sort_keys=True)
                else:
                    Domoticz.Error("Removing Nwk-Energy %s not found" %timestamp )
                    _response['Data'] = json.dumps( [] , sort_keys=True)
            return _response

        elif verb == 'GET':
            if len(parameters) == 0:
                _response['Data'] = json.dumps( _timestamps_lst , sort_keys=True)

            elif len(parameters) == 1:
                timestamp = parameters[0]
                if timestamp in _scan:
                    for r in _scan[timestamp]:
                        self.logging( "Debug", "report: %s" %r)
                        if r['_NwkId'] == '0000':
                            _response['Data'] = json.dumps( r['MeshRouters'], sort_keys=True )
                else:
                    _response['Data'] = json.dumps( [] , sort_keys=True)
        return _response

    def rest_plugin_restart( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == 'GET':
            if self.WebUsername and self.WebPassword:
                url = 'http://%s:%s@127.0.0.1:%s' %(self.WebUsername, self.WebPassword, self.pluginconf.pluginConf['port'])
            else:
                url = 'http://127.0.0.1:%s' %self.pluginconf.pluginConf['port']
            url += '/json.htm?type=command&param=updatehardware&htype=94'
            url += '&idx=%s' %self.pluginparameters['HardwareID']

            url += '&name=%s' %self.pluginparameters['Name']
            url += '&address=%s' %self.pluginparameters['Address']
            url += '&port=%s' %self.pluginparameters['Port']
            url += '&serialport=%s' %self.pluginparameters['SerialPort']
            url += '&Mode1=%s' %self.pluginparameters['Mode1']
            url += '&Mode2=%s' %self.pluginparameters['Mode2']
            url += '&Mode3=%s' %self.pluginparameters['Mode3']
            url += '&Mode4=%s' %self.pluginparameters['Mode4']
            url += '&Mode5=%s' %self.pluginparameters['Mode5']
            url += '&Mode6=%s' %self.pluginparameters['Mode6']
            url += '&extra=%s' %self.pluginparameters['Key']
            url += '&enabled=true'
            url += '&datatimeout=0'

            info = {'Text': 'Plugin restarted', 'TimeStamp': int(time())}
            _response["Data"] = json.dumps( info, sort_keys=True )

            Domoticz.Log("Plugin Restart command : %s" %url)
            _cmd = "/usr/bin/curl '%s' &" %url
            try:
                os.system( _cmd )  # nosec
            except:
                Domoticz.Error("Error while trying to restart plugin %s" %_cmd)

        return _response
        
    def rest_restart_needed( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())

        if verb == 'GET':
            _response["Data"] = json.dumps( self.restart_needed, sort_keys=True )
        return _response

    def rest_plugin_stat( self, verb, data, parameters):

        Statistics = {}
        self.logging( 'Debug', "self.statistics: %s" %self.statistics)
        self.logging( 'Debug', " --> Type: %s" %type(self.statistics))

        Statistics['Trend'] = [ ]
        if self.pluginparameters['Mode1'] == 'None':
            Statistics['CRC'] = 1
            Statistics['FrameErrors'] = 1
            Statistics['Sent'] = 5
            Statistics['Received'] = 10
            Statistics['Cluster'] = 268
            Statistics['ReTx'] = 3
            Statistics['CurrentLoad'] = 1
            Statistics['MaxLoad'] = 7
            Statistics['APSAck'] = 100
            Statistics['APSNck'] =  0
            Statistics['StartTime'] = int(time()) - 120
        else:
            Statistics['CRC'] =self.statistics._crcErrors
            Statistics['FrameErrors'] =self.statistics._frameErrors
            Statistics['Sent'] =self.statistics._sent
            Statistics['Received'] =self.statistics._received
            Statistics['Cluster'] =self.statistics._clusterOK
            Statistics['ReTx'] =self.statistics._reTx
            Statistics['APSFailure'] =self.statistics._APSFailure
            Statistics['APSAck'] =self.statistics._APSAck
            Statistics['APSNck'] =self.statistics._APSNck
            Statistics['CurrentLoad'] = len(self.ZigateComm.zigateSendingFIFO)
            Statistics['MaxLoad'] = self.statistics._MaxLoad
            Statistics['StartTime'] =self.statistics._start

            _nbitems = len(self.statistics.TrendStats)

            minTS = 0
            if  len(self.statistics.TrendStats) == 120:
                # Identify the smallest TS (we cannot assumed the list is sorted)
                minTS = 120
                for item in self.statistics.TrendStats:
                    if item['_TS'] < minTS:
                        minTS = item['_TS']
                minTS -= 1 # To correct as the dataset start at 1 (and not 0)

            # Renum
            for item in self.statistics.TrendStats:
                _TS = item['_TS'] 
                if _nbitems >= 120:
                    # Rolling window in progress
                    _TS -= minTS

                Statistics['Trend'].append( {"_TS":_TS, "Rxps": item['Rxps'],"Txps": item['Txps'], "Load": item['Load']} )

        Statistics['Uptime'] = int(time() - Statistics['StartTime'])
        Statistics['Txps'] = round(Statistics['Sent'] / Statistics['Uptime'], 2)
        Statistics['Txpm'] = round(Statistics['Sent'] / Statistics['Uptime'] * 60, 2)
        Statistics['Txph'] = round(Statistics['Sent'] / Statistics['Uptime'] * 3600, 2)
        Statistics['Rxps'] = round(Statistics['Received'] / Statistics['Uptime'], 2)
        Statistics['Rxpm'] = round(Statistics['Received'] / Statistics['Uptime'] * 60, 2)
        Statistics['Rxph'] = round(Statistics['Received'] / Statistics['Uptime'] * 3600, 2)

        _response = prepResponseMessage( self ,setupHeadersResponse())
        if verb == 'GET':
                _response["Data"] = json.dumps( Statistics, sort_keys=True )
        return _response

    def rest_Settings( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())

        if verb == 'GET':
            if len(parameters) == 0:
                setting_lst = []
                for _theme in SETTINGS:
                    if _theme in ( 'PluginTransport'): 
                        continue

                    theme = {
                        '_Order': SETTINGS[_theme]['Order'],
                        '_Theme': _theme,
                        'ListOfSettings': [],
                    }

                    for param in self.pluginconf.pluginConf:
                        if param not in SETTINGS[_theme]['param']: 
                            continue

                        if not SETTINGS[_theme]['param'][param]['hidden']:
                            setting = {
                                'Name': param,
                                'default_value': SETTINGS[_theme]['param'][param][
                                    'default'
                                ],
                                'DataType': SETTINGS[_theme]['param'][param][
                                    'type'
                                ],
                                'restart_need': SETTINGS[_theme]['param'][param][
                                    'restart'
                                ],
                                'Advanced': SETTINGS[_theme]['param'][param][
                                    'Advanced'
                                ],
                            }

                            if SETTINGS[_theme]['param'][param]['type'] == 'hex':
                                Domoticz.Debug("--> %s: %s - %s" %(param, self.pluginconf.pluginConf[param], type(self.pluginconf.pluginConf[param])))
                                if isinstance( self.pluginconf.pluginConf[param], int):
                                    setting['current_value'] = '%x' %self.pluginconf.pluginConf[param] 
                                else:
                                    setting['current_value'] = '%x' %int(self.pluginconf.pluginConf[param] ,16)
                            else:
                                setting['current_value'] = self.pluginconf.pluginConf[param]
                            theme['ListOfSettings'].append ( setting )
                    setting_lst.append( theme )
                _response["Data"] = json.dumps( setting_lst, sort_keys=True )

        elif verb == 'PUT':
            _response["Data"] = None
            data = data.decode('utf8')
            self.logging( 'Debug', "Data: %s" %data)
            data = data.replace('true','1')     # UI is coming with true and not True
            data = data.replace('false','0')   # UI is coming with false and not False

            setting_lst = eval(data)
            upd = False
            for setting in setting_lst:
                found = False
                self.logging( 'Debug', "setting: %s = %s" %(setting, setting_lst[setting]['current']))

                # Do we have to update ?
                for _theme in SETTINGS:
                    for param in SETTINGS[_theme]['param']:
                        if param != setting: 
                            continue

                        found = True
                        upd = True
                        if str(setting_lst[setting]['current']) == str(self.pluginconf.pluginConf[param]):
                            #Nothing to do
                            continue

                        self.logging( 'Debug', "Updating %s from %s to %s" %( param, self.pluginconf.pluginConf[param], setting_lst[setting]['current']))
                        if SETTINGS[_theme]['param'][param]['restart']:
                            self.restart_needed['RestartNeeded'] = True

                        if param == 'Certification':
                            if setting_lst[setting]['current'] in CERTIFICATION_CODE:
                                self.pluginconf.pluginConf['Certification'] = setting_lst[setting]['current']
                                self.pluginconf.pluginConf['CertificationCode'] = CERTIFICATION_CODE[setting_lst[setting]['current']]
                            else:
                                Domoticz.Error("Unknown Certification code %s (allow are CE and FCC)" %(setting_lst[setting]['current']))
                                continue

                        elif param == 'blueLedOnOff':
                            if self.pluginconf.pluginConf[param] != setting_lst[setting]['current']:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                                if self.pluginconf.pluginConf[param]:
                                    zigateBlueLed( self, True)
                                else:
                                    zigateBlueLed( self, False)

                        elif param == 'EnableLedShutter':
                            if self.pluginconf.pluginConf[param] != setting_lst[setting]['current']:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                                if setting_lst[setting]['current']:
                                    legrand_ledShutter( self, 'On')
                                else:
                                    legrand_ledShutter( self, 'Off')


                        elif param == 'EnableLedInDark':
                            if self.pluginconf.pluginConf[param] != setting_lst[setting]['current']:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                                if setting_lst[setting]['current']:
                                    legrand_ledInDark( self, 'On')
                                else:
                                    legrand_ledInDark( self, 'Off')

                        elif param == 'EnableDimmer':
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                                if setting_lst[setting]['current']:
                                    legrand_dimOnOff( self, 'On')
                                else:
                                    legrand_dimOnOff( self, 'Off')

                        elif param == 'EnableLedIfOn':
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                                if setting_lst[setting]['current']:
                                    legrand_ledIfOnOnOff( self, 'On')
                                else:
                                    legrand_ledIfOnOnOff( self, 'Off')

                        elif param == 'debugMatchId':
                            if setting_lst[setting]['current'] == 'ffff':
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']
                            else:
                                self.pluginconf.pluginConf['debugMatchId'] = ""
                                matchID = setting_lst[setting]['current'].lower().split(',')
                                for key in matchID:
                                    if len(key) == 4:
                                        if key not in self.ListOfDevices:
                                            continue

                                        self.pluginconf.pluginConf['debugMatchId'] += key + ","
                                    if len(key) == 16:
                                        # Expect an IEEE
                                        if key not in self.IEEE2NWK:
                                            continue

                                        self.pluginconf.pluginConf['debugMatchId'] += self.IEEE2NWK[key] + ","
                                self.pluginconf.pluginConf['debugMatchId'] = self.pluginconf.pluginConf['debugMatchId'][:-1] # Remove the last ,
                        else:
                            if SETTINGS[_theme]['param'][param]['type'] == 'hex':
                                #Domoticz.Log("--> %s: %s - %s" %(param, self.pluginconf.pluginConf[param], type(self.pluginconf.pluginConf[param])))
                                self.pluginconf.pluginConf[param] = int(setting_lst[setting]['current'],16)
                            else:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]['current']


                if not found:
                    Domoticz.Error("Unexpected parameter: %s" %setting)
                    _response["Data"] = { 'unexpected parameters %s' %setting }

                if upd:
                    # We need to write done the new version of PluginConf
                    self.pluginconf.write_Settings()

        return _response

    def rest_PermitToJoin( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())


        if verb == 'GET':
            duration = self.permitTojoin['Duration']
            timestamp = self.permitTojoin['Starttime']
            info = {}
            if duration == 255:
                info['PermitToJoin'] = 255
            elif duration == 0:
                info['PermitToJoin'] = 0
            elif int(time()) >= timestamp + duration:
                info['PermitToJoin'] = 0
            else:
                rest = (
                    self.permitTojoin['Starttime']
                    + self.permitTojoin['Duration']
                    - int(time())
                )

                self.logging('Debug', 'remain %s s' % rest)
                info['PermitToJoin'] = rest
            _response["Data"] = json.dumps( info, sort_keys=True )

        elif verb == 'PUT':
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode('utf8')
                data = json.loads(data)
                self.logging( 'Debug', "parameters: %s value = %s" %( 'PermitToJoin', data['PermitToJoin']))
                if 'Router' in data:
                    duration = int( data['PermitToJoin'])
                    router = data['Router']
                    if router in self.ListOfDevices:
                        # Allow Permit to join from this specific router    
                        self.logging( 'Log', "Requesting router: %s to switch into Permit to join" %router)             
                        sendZigateCmd( self, "0049", router + '%02x' %duration + '00') 

                else:                   
                    if self.pluginparameters['Mode1'] != 'None':
                        ZigatePermitToJoin(self, int( data['PermitToJoin']))
        return _response

    def rest_Device( self, verb, data, parameters):

        _dictDevices = {}
        _response = prepResponseMessage( self ,setupHeadersResponse())

        if verb == 'GET':
            if self.Devices is None or len(self.Devices) == 0:
                return _response

            if len(parameters) == 0:
                # Return the Full List of ZIgate Domoticz Widget
                device_lst = []
                for x in self.Devices:
                    if len(self.Devices[x].DeviceID)  != 16:
                        continue

                    device_info = {
                        '_DeviceID': self.Devices[x].DeviceID,
                        'Name': self.Devices[x].Name,
                        'ID': self.Devices[x].ID,
                        'sValue': self.Devices[x].sValue,
                        'nValue': self.Devices[x].nValue,
                        'SignaleLevel': self.Devices[x].SignalLevel,
                        'BatteryLevel': self.Devices[x].BatteryLevel,
                        'TimedOut': self.Devices[x].TimedOut,
                    }

                    #device_info['Type'] = self.Devices[x].Type
                    #device_info['SwitchType'] = self.Devices[x].SwitchType
                    device_lst.append( device_info )
                _response["Data"] = json.dumps( device_lst, sort_keys=True )

            elif len(parameters) == 1:
                for x in self.Devices:
                    if len(self.Devices[x].DeviceID)  != 16:
                        continue

                    if parameters[0] == self.Devices[x].DeviceID:
                        _dictDevices = {
                            '_DeviceID': self.Devices[x].DeviceID,
                            'Name': self.Devices[x].Name,
                            'ID': self.Devices[x].ID,
                            'sValue': self.Devices[x].sValue,
                            'nValue': self.Devices[x].nValue,
                            'SignaleLevel': self.Devices[x].SignalLevel,
                            'BatteryLevel': self.Devices[x].BatteryLevel,
                            'TimedOut': self.Devices[x].TimedOut,
                        }

                        #_dictDevices['Type'] = self.Devices[x].Type
                        #_dictDevices['SwitchType'] = self.Devices[x].SwitchType
                        _response["Data"] = json.dumps( _dictDevices, sort_keys=True )
                        break

            else:
                device_lst = []
                for parm in parameters:
                    device_info = {}
                    for x in self.Devices:
                        if len(self.Devices[x].DeviceID)  != 16:
                            continue

                        if parm == self.Devices[x].DeviceID:
                            device_info = {
                                '_DeviceID': self.Devices[x].DeviceID,
                                'Name': self.Devices[x].Name,
                                'ID': self.Devices[x].ID,
                                'sValue': self.Devices[x].sValue,
                                'nValue': self.Devices[x].nValue,
                                'SignaleLevel': self.Devices[x].SignalLevel,
                                'BatteryLevel': self.Devices[x].BatteryLevel,
                                'TimedOut': self.Devices[x].TimedOut,
                            }

                            #device_info['Type'] = self.Devices[x].Type
                            #device_info['SwitchType'] = self.Devices[x].SwitchType
                            device_lst.append( device_info )
                _response["Data"] = json.dumps( device_lst, sort_keys=True )
        return _response

    def rest_zDevice_name( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())

        if verb == 'DELETE':
            if len(parameters) == 1:
                ieee = nwkid = None
                deviceId = parameters[0]
                if len( deviceId ) == 4: # Short Network Addr
                    if deviceId not in self.ListOfDevices:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown LOD" %(deviceId))
                        Domoticz.Error("Device %s to be removed unknown" %deviceId )
                        _response['Data'] = json.dumps( [] , sort_keys=True)
                        return _response
                    nwkid = deviceId
                    ieee = self.ListOfDevices[deviceId]['IEEE']
                else:
                    if deviceId not in self.IEEE2NWK:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown in IEEE22NWK" %(deviceId))
                        Domoticz.Error("Device %s to be removed unknown" %deviceId )
                        _response['Data'] = json.dumps( [] , sort_keys=True)
                        return _response
                    ieee = deviceId
                    nwkid = self.IEEE2NWK[ ieee ]
                if nwkid:
                    del self.ListOfDevices[ nwkid ]
                if ieee:
                    del self.IEEE2NWK[ ieee ]

                # for a remove in case device didn't send the leave
                if 'IEEE' in self.zigatedata and ieee:
                    # uParrentAddress + uChildAddress (uint64)
                    sendZigateCmd(self, "0026", self.zigatedata['IEEE'] + ieee )

                action = {'Name': 'Device %s/%s removed' % (nwkid, ieee)}
                _response['Data'] = json.dumps( action , sort_keys=True)

        elif verb == 'GET':
            _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
            device_lst = []
            for x in self.ListOfDevices:
                if x == '0000': 
                    continue

                device = {'_NwkId': x}
                for item in ( 'ZDeviceName', 'IEEE', 'Model', 'MacCapa', 'Status', 'ConsistencyCheck', 'Health', 'RSSI', 'Battery'):
                    if item in self.ListOfDevices[x]:
                        if item == 'MacCapa':
                            device['MacCapa'] = []
                            mac_capability = int(self.ListOfDevices[x][item],16)
                            AltPAN      =   ( mac_capability & 0x00000001 )
                            DeviceType  =   ( mac_capability >> 1 ) & 1
                            PowerSource =   ( mac_capability >> 2 ) & 1
                            ReceiveonIdle = ( mac_capability >> 3 ) & 1
                            if DeviceType == 1 :
                                device['MacCapa'].append("FFD")
                            else :
                                device['MacCapa'].append("RFD")
                            if ReceiveonIdle == 1 :
                                device['MacCapa'].append("RxonIdle")
                            if PowerSource == 1 :
                                device['MacCapa'].append("MainPower")
                            else :
                                device['MacCapa'].append("Battery")
                            self.logging( 'Debug', "decoded MacCapa from: %s to %s" %(self.ListOfDevices[x][item], str(device['MacCapa'])))
                        else:
                            if self.ListOfDevices[x][item] == {}:
                                device[item] = ''
                            else:
                                device[item] = self.ListOfDevices[x][item]
                    else:
                        device[item] = ''

                device['WidgetList'] = []
                for ep in self.ListOfDevices[x]['Ep']:
                    if 'ClusterType' in self.ListOfDevices[x]['Ep'][ep]:
                        clusterType= self.ListOfDevices[x]['Ep'][ep]['ClusterType']
                        for widgetID in clusterType:
                            for widget in self.Devices:
                                if self.Devices[widget].ID == int(widgetID):
                                    self.logging( 'Debug', "Widget Name: %s %s" %(widgetID, self.Devices[widget].Name))
                                    if self.Devices[widget].Name not in device['WidgetList']:
                                        device['WidgetList'].append( self.Devices[widget].Name )

                    elif 'ClusterType' in self.ListOfDevices[x]:
                        clusterType = self.ListOfDevices[x]['ClusterType']
                        for widgetID in clusterType:
                            for widget in self.Devices:
                                if self.Devices[widget].ID == int(widgetID):
                                    self.logging( 'Debug', "Widget Name: %s %s" %(widgetID, self.Devices[widget].Name))
                                    if self.Devices[widget].Name not in device['WidgetList']:
                                        device['WidgetList'].append( self.Devices[widget].Name )

                if device not in device_lst:
                    device_lst.append( device )
            #_response["Data"] = json.dumps( device_lst, sort_keys=True )
            self.logging( 'Debug', "zDevice_name - sending %s" %device_lst)
            _response["Data"] = json.dumps( device_lst, sort_keys=True )

        elif verb == 'PUT':
            _response["Data"] = None
            data = data.decode('utf8')
            self.logging( 'Debug', "Data: %s" %data)
            data = eval(data)
            for x in data:
                if 'ZDeviceName' in x and 'IEEE' in x:
                    for dev in self.ListOfDevices:
                        if self.ListOfDevices[dev]['IEEE'] == x['IEEE'] and \
                                self.ListOfDevices[dev]['ZDeviceName'] != x['ZDeviceName']:
                            self.ListOfDevices[dev]['ZDeviceName'] = x['ZDeviceName']
                            self.logging( 'Debug', "Updating ZDeviceName to %s for IEEE: %s NWKID: %s" \
                                    %(self.ListOfDevices[dev]['ZDeviceName'], self.ListOfDevices[dev]['IEEE'], dev))
                else:
                    Domoticz.Error("wrong data received: %s" %data)

        return _response

    def rest_zDevice( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())

        if verb == 'DELETE':
            if len(parameters) == 1:
                deviceId = parameters[0]
                if len( deviceId ) == 4: # Short Network Addr
                    if deviceId not in self.ListOfDevices:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown LOD" %(deviceId))
                        Domoticz.Error("Device %s to be removed unknown" %deviceId )
                        _response['Data'] = json.dumps( [] , sort_keys=True)
                        return _response
                    nwkid = deviceId
                    ieee = self.ListOfDevice[deviceId]['IEEE']
                else:
                    if deviceId not in self.IEEE2NWK:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown in IEEE22NWK" %(deviceId))
                        Domoticz.Error("Device %s to be removed unknown" %deviceId )
                        _response['Data'] = json.dumps( [] , sort_keys=True)
                        return _response
                    ieee = deviceId
                    nwkid = self.IEEE2NWK[ ieee ]

                del self.ListOfDevice[ nwkid ]
                del self.IEEE2NWK[ ieee ]
                action = {'Name': 'Device %s/%s removed' % (nwkid, ieee)}
                _response['Data'] = json.dumps( action , sort_keys=True)
            return _response

        elif verb == 'GET':
            if self.Devices is None or len(self.Devices) == 0:
                return _response
            if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
                return _response
            if len(parameters) == 0:
                zdev_lst = []
                for item in self.ListOfDevices:
                    if item == '0000': 
                        continue
                    device = {'_NwkId': item}
                    # Main Attributes
                    for attribut in ( 'ZDeviceName', 'ConsistencyCheck', 'Stamp', 'Health', 'Status', 'Battery', 'RSSI', 'Model', 'IEEE', 'ProfileID', 'ZDeviceID', 'Manufacturer', 'DeviceType', 'LogicalType', 'PowerSource', 'ReceiveOnIdle', 'App Version', 'Stack Version', 'HW Version' ):

                        if attribut in self.ListOfDevices[item]:
                            if self.ListOfDevices[item][attribut] == {}:
                                device[attribut] = ''
                            elif self.ListOfDevices[item][attribut] == '' and self.ListOfDevices[item]['MacCapa'] == '8e':
                                if attribut == 'DeviceType':
                                    device[attribut] = 'FFD'
                                elif attribut == 'LogicalType':
                                    device[attribut] = 'Router'
                                elif attribut == 'PowerSource':
                                    device[attribut] = 'Main'
                            else:
                                device[attribut] = self.ListOfDevices[item][attribut]
                        else:
                            device[attribut] = ''

                    # Last Seen Information
                    device['LastSeen'] = ''
                    if (
                        'Stamp' in self.ListOfDevices[item]
                        and 'LastSeen' in self.ListOfDevices[item]['Stamp']
                    ):
                        device['LastSeen'] = self.ListOfDevices[item]['Stamp']['LastSeen']

                    # ClusterType
                    _widget_lst = []
                    if 'ClusterType' in self.ListOfDevices[item]:
                        for widgetId in self.ListOfDevices[item]['ClusterType']:
                            widget = {'_WidgetID': widgetId, 'WidgetName': ''}
                            for x in self.Devices:
                                if self.Devices[x].ID == int(widgetId):
                                    widget['WidgetName'] = self.Devices[x].Name
                                    break

                            widget['WidgetType'] = self.ListOfDevices[item]['ClusterType'][widgetId]
                            _widget_lst.append( widget )

                    # Ep informations
                    ep_lst = []
                    if 'Ep' in self.ListOfDevices[item]:
                        for epId in self.ListOfDevices[item]['Ep']:
                            _ep = {'Ep': epId, 'ClusterList': []}
                            for cluster in self.ListOfDevices[item]['Ep'][epId]:
                                if cluster == 'ColorMode': 
                                    continue

                                if cluster == 'ClusterType':
                                    for widgetId in self.ListOfDevices[item]['Ep'][epId]['ClusterType']:
                                        widget = {'_WidgetID': widgetId, 'WidgetName': ''}
                                        for x in self.Devices:
                                            if self.Devices[x].ID == int(widgetId):
                                                widget['WidgetName'] = self.Devices[x].Name
                                                break

                                        widget['WidgetType'] = self.ListOfDevices[item]['Ep'][epId]['ClusterType'][widgetId]
                                        _widget_lst.append( widget )
                                    continue

                                elif cluster == 'Type':
                                    device['Type'] = self.ListOfDevices[item]['Ep'][epId]['Type']
                                    continue

                                _cluster = {}
                                if cluster in ZCL_CLUSTERS_LIST:
                                    _cluster[cluster] = ZCL_CLUSTERS_LIST[cluster]

                                else:
                                    _cluster[cluster] = "Unknown"
                                _ep['ClusterList'].append( _cluster )

                            ep_lst.append ( _ep )
                    device['Ep'] = ep_lst
                    device['WidgetList'] = _widget_lst

                    # Last Commands
                    lastcmd_lst = []
                    if 'Last Cmds' in self.ListOfDevices[item]:
                        for lastCmd in self.ListOfDevices[item]['Last Cmds']:
                            timestamp = lastCmd[0]
                            cmd = lastCmd[1]
                            #payload = lastCmd[2]
                            _cmd = {'CmdCode': cmd, 'TimeStamps': timestamp}
                            lastcmd_lst.append( _cmd )
                    device['LastCmds'] = lastcmd_lst
                    zdev_lst.append( device )

                _response["Data"] = json.dumps( zdev_lst, sort_keys=True )
        return _response

    def rest_zDevice_raw( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())
 
        if verb == 'GET':
            if self.Devices is None or len(self.Devices) == 0:
                return _response
            if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
                return _response
            if len(parameters) == 0:
                zdev_lst = []
                for item in self.ListOfDevices:
                    entry = dict(self.ListOfDevices[item])
                    entry['NwkID'] = item
                    zdev_lst.append(entry)
                _response["Data"] = json.dumps( zdev_lst, sort_keys=False )
            elif len(parameters) == 1:
                if parameters[0] in self.ListOfDevices:
                    _response["Data"] =  json.dumps( self.ListOfDevices[parameters[0]], sort_keys=False ) 
                elif parameters[0] in self.IEEE2NWK:
                    _response["Data"] =  json.dumps( self.ListOfDevices[self.IEEE2NWK[parameters[0]]], sort_keys=False ) 

        return _response

    def rest_raw_command( self, verb, data, parameters):

        Domoticz.Log("raw_command - %s %s" %(verb, data))
        _response = prepResponseMessage( self ,setupHeadersResponse())

        if verb == 'PUT':
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode('utf8')
                data = json.loads(data)
                Domoticz.Log("---> Data: %s" %str(data))
                if 'Command' not in data and 'payload' not in data:
                    Domoticz.Error("Unexpected request: %s" %data)
                    _response["Data"] = json.dumps( "Executing %s on %s" %(data['Command'], data['payload']) )
                    return _response
                msgtype = int( data['Command'] , 16 )
                if msgtype not in ZIGATE_COMMANDS:
                    Domoticz.Error("raw_command - Unknown MessageType received %s" %msgtype)
                    _response["Data"] = json.dumps( "Unknown MessageType received %s" %msgtype)
                    return _response
                
                cmd = data['Command']
                payload = data['payload']
                if payload is None:
                    payload = ""
                sendZigateCmd( self, data['Command'], data['payload'])
                self.logging( 'Log', "rest_dev_command - Command: %s payload %s" %(data['Command'], data['payload']))
                _response["Data"] = json.dumps( "Executing %s on %s" %(data['Command'], data['payload']) ) 

        return _response

    def rest_dev_command( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())

        if verb == 'PUT':
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode('utf8')
                data = json.loads(data)
                Domoticz.Log("---> Data: %s" %str(data))
                self.logging( 'Log', "rest_dev_command - Command: %s on object: %s with extra %s %s" %(data['Command'], data['NwkId'], data['Value'],  data['Color']))
                _response["Data"] = json.dumps( "Executing %s on %s" %(data['Command'], data['NwkId']) ) 
                if 'Command' not in data:
                    return _response
                if data['Command'] == '':
                    return _response
                if data['Value'] == '' or data['Value'] is None:
                    Level = 0
                else:
                    if is_hex(str(data['Value'])):
                        Level = int(str(data['Value']),16)
                    else:
                        Level = int(str(data['Value']))
                ColorMode = ColorValue = ''
                color = ''
                if data['Color'] == '' or data['Color'] is None:
                    Hue_List = {}
                    Color = json.dumps( Hue_List )
                else:
                    # Decoding RGB
                    # rgb(30,96,239)
                    ColorMode = data['Color'].split('(')[0]
                    ColorValue = data['Color'].split('(')[1].split(')')[0]
                    if ColorMode == 'rgb':
                        Hue_List = {}
                        Hue_List['m'] = 3
                        Hue_List['r'], Hue_List['g'], Hue_List['b'] = ColorValue.split(',') 
                    self.logging( 'Log', "rest_dev_command -        Color decoding m: %s r:%s g: %s b: %s"  %(Hue_List['m'], Hue_List['r'], Hue_List['g'], Hue_List['b']))
                    Color = json.dumps( Hue_List )



                epout = '01'
                if 'Type' not in data:
                    actuators( self,  data['Command'], data['NwkId'], epout , 'Switch')
                else:
                    SWITCH_2_CLUSTER = { 'Switch':'0006',
                        'LivoloSWL':'0006',
                        'LivoloSWR':'0006',
                        'LvlControl':'0008',
                        'WindowCovering':'0102',
                        'ThermoSetpoint':'0201',
                        'ColorControlRGBWW':'0300',
                        'ColorControlWW':'0300',
                        'ColorControlRGB':'0300'}

                    key = data['NwkId']
                    if data['Type'] is None:
                        clusterCode = '0003'
                    else:
                        clusterCode = SWITCH_2_CLUSTER[ data['Type'] ]

                    for tmpEp in self.ListOfDevices[data['NwkId']]['Ep']:
                        if clusterCode  in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                            epout=tmpEp
                    actuators( self,  data['Command'], key, epout , data['Type'], value=Level, color=Color)

        return _response

    def rest_dev_capabilities( self, verb, data, parameters):

        _response = prepResponseMessage( self ,setupHeadersResponse())

        if verb != 'GET':
            return _response

        if self.Devices is None or len(self.Devices) == 0:
            return _response

        if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
            return _response

        if len(parameters) == 0:
            Domoticz.Error("rest_dev_capabilities - expecting a device id! %s" %(parameters))
            return _response

        if len(parameters) != 1:
            return

        if not ( parameters[0] in self.ListOfDevices or parameters[0] in self.IEEE2NWK ):
            Domoticz.Error("rest_dev_capabilities - Device %s doesn't exist" %(parameters[0]))
            return _response

        # Check Capabilities
        CLUSTER_INFOS = {
                '0003': [ 
                    { 'actuator': 'Identify', 'Value': '', 'Type': ( ) },
                    { 'actuator': 'IdentifyEffect', 'Value': 'hex', 'Type': ( ) },
                ],
                '0006': [
                    { 'actuator': 'On', 'Value':'', 'Type': ( 'Switch',) },
                    { 'actuator': 'Off', 'Value':'', 'Type': ( 'Switch', ) },
                    { 'actuator': 'Toggle', 'Value':'', 'Type': ( 'Switch', ) },
                ],
                '0008': [
                    { 'actuator': 'SetLevel', 'Value':'int', 'Type': ( 'LvlControl',) },
                ],
                '0102': [
                    { 'actuator': 'On', 'Value':'', 'Type': ( 'WindowCovering',) },
                    { 'actuator': 'Off', 'Value':'', 'Type': ( 'WindowCovering',) },
                    { 'actuator': 'Stop', 'Value':'', 'Type': ( 'WindowCovering',) },
                    { 'actuator': 'SetLevel', 'Value':'hex', 'Type': ( 'WindowCovering',) },
                ],
                '0201': [
                    { 'actuator': 'SetPoint', 'Value':'hex', 'Type': ( 'ThermoSetpoint',) },
                ],
                '0300': [
                    { 'actuator': 'SetColor', 'Value':'rgbww', 'Type': ( 'ColorControlRGBWW', 'ColorControlWW', 'ColorControlRGB') },
                ]

            }
        dev_capabilities = {'NwkId': {}, 'Capabilities': [], 'Types': []}
        if  parameters[0] in self.ListOfDevices:
            _nwkid = parameters[0]
        elif parameters[0] in self.IEEE2NWK:
            _nwkid = self.IEEE2NWK[parameters[0]]
        dev_capabilities['NwkId'] = _nwkid

        for ep in self.ListOfDevices[ _nwkid ]['Ep']:
            for cluster in self.ListOfDevices[ _nwkid ]['Ep'][ ep ]:
                if cluster not in CLUSTER_INFOS:
                    continue
                for action in CLUSTER_INFOS[cluster]:
                    _capabilitie = {
                        'actuator': action['actuator'],
                        'Value': False if action['Value'] == '' else action['Value'],
                        'Type': True if len(action['Type']) != 0 else False,
                        }

                    dev_capabilities['Capabilities'].append( _capabilitie )

                    for cap in action['Type']:
                        if cap not in dev_capabilities['Types']:
                            dev_capabilities['Types'].append( cap )

                    # Adding non generic Capabilities
                    if (
                        'Model' in self.ListOfDevices[_nwkid]
                        and self.ListOfDevices[_nwkid]['Model'] != {}
                        and self.ListOfDevices[_nwkid]['Model'] == 'TI0001'
                    ):
                        if 'LivoloSWL' not in dev_capabilities['Types']:
                            dev_capabilities['Types'].append( 'LivoloSWL' )
                        if 'LivoloSWR' not in dev_capabilities['Types']:
                            dev_capabilities['Types'].append( 'LivoloSWR' )

        _response["Data"] = json.dumps( dev_capabilities )
        return _response