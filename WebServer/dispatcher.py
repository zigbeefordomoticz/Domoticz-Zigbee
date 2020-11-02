#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz

from WebServer.headerResponse import setupHeadersResponse, prepResponseMessage
from WebServer.rest_Bindings import rest_bindLSTcluster, rest_bindLSTdevice, rest_binding, rest_unbinding
from WebServer.rest_Topology import rest_netTopologie, rest_req_topologie
from WebServer.rest_Energy import rest_req_nwk_full, rest_req_nwk_inter
from WebServer.rest_Groups import rest_zGroup, rest_rescan_group, rest_zGroup_lst_avlble_dev,rest_scan_devices_for_group
from WebServer.rest_Provisioning import rest_new_hrdwr, rest_rcv_nw_hrdwr

def do_rest( self, Connection, verb, data, version, command, parameters):

    REST_COMMANDS = { 
        'unbinding':     {'Name':'unbinding',          'Verbs':{'PUT'},          'function':self.rest_unbinding},
        'binding':       {'Name':'binding',            'Verbs':{'PUT'},          'function':self.rest_binding},
        'bind-lst-cluster':{'Name':'bind-lst-cluster', 'Verbs':{'GET'},          'function':self.rest_bindLSTcluster},
        'bind-lst-device': {'Name':'bind-lst-device',  'Verbs':{'GET'},          'function':self.rest_bindLSTdevice},
        'new-hrdwr':     {'Name':'new-hrdwr',          'Verbs':{'GET'},          'function':self.rest_new_hrdwr},
        'rcv-nw-hrdwr':  {'Name':'rcv-nw-hrdwr',       'Verbs':{'GET'},          'function':self.rest_rcv_nw_hrdwr},
        'device':        {'Name':'device',             'Verbs':{'GET'},          'function':self.rest_Device},
        'dev-cap':       {'Name':'dev-cap',            'Verbs':{'GET'},          'function':self.rest_dev_capabilities},
        'dev-command':   {'Name':'dev-command',        'Verbs':{'PUT'},          'function':self.rest_dev_command},
        'raw-command':   {'Name':'raw-command',        'Verbs':{'PUT'},          'function':self.rest_raw_command},
        'domoticz-env':  {'Name':'domoticz-env',       'Verbs':{'GET'},          'function':self.rest_domoticz_env},
        'plugin-health': {'Name':'plugin-health',      'Verbs':{'GET'},          'function':self.rest_plugin_health},
        'nwk-stat':      {'Name':'nwk_stat',           'Verbs':{'GET','DELETE'}, 'function':self.rest_nwk_stat},
        'permit-to-join':{'Name':'permit-to-join',     'Verbs':{'GET','PUT'},    'function':self.rest_PermitToJoin},
        'plugin':        {'Name':'plugin',             'Verbs':{'GET'},          'function':self.rest_PluginEnv},
        'plugin-stat':   {'Name':'plugin-stat',        'Verbs':{'GET'},          'function':self.rest_plugin_stat},
        'plugin-restart':   {'Name':'plugin-restart',  'Verbs':{'GET'},          'function':self.rest_plugin_restart},

        'restart-needed':{'Name':'restart-needed',     'Verbs':{'GET'},          'function':self.rest_restart_needed},
        'req-nwk-inter': {'Name':'req-nwk-inter',      'Verbs':{'GET'},          'function':self.rest_req_nwk_inter},
        'req-nwk-full':  {'Name':'req-nwk-full',       'Verbs':{'GET'},          'function':self.rest_req_nwk_full},
        'req-topologie': {'Name':'req-topologie',      'Verbs':{'GET'},          'function':self.rest_req_topologie},
        'sw-reset-zigate':  {'Name':'sw-reset-zigate', 'Verbs':{'GET'},          'function':self.rest_reset_zigate},
        'setting':       {'Name':'setting',            'Verbs':{'GET','PUT'},    'function':self.rest_Settings_wo_debug},
        'setting-debug': {'Name':'setting',            'Verbs':{'GET','PUT'},    'function':self.rest_Settings_with_debug},
        'topologie':     {'Name':'topologie',          'Verbs':{'GET','DELETE'}, 'function':self.rest_netTopologie},
        'zdevice':       {'Name':'zdevice',            'Verbs':{'GET','DELETE'}, 'function':self.rest_zDevice},
        'zdevice-name':  {'Name':'zdevice-name',       'Verbs':{'GET','PUT','DELETE'}, 'function':self.rest_zDevice_name},
        'zdevice-raw':   {'Name':'zdevice-raw',        'Verbs':{'GET','PUT'},    'function':self.rest_zDevice_raw},
        'zgroup':        {'Name':'device',             'Verbs':{'GET','PUT'},    'function':self.rest_zGroup},
        'zgroup-list-available-device':   
                         {'Name':'zgroup-list-available-device','Verbs':{'GET'}, 'function':self.rest_zGroup_lst_avlble_dev},
        'zigate':        {'Name':'zigate',             'Verbs':{'GET'},          'function':self.rest_zigate},
        'log-error-history':{'Name':'log-error-history','Verbs':{'GET'},         'function':self.rest_logErrorHistory},
        'clear-error-history':{'Name':'clear-error-history','Verbs':{'GET'},         'function':self.rest_logErrorHistoryClear},
        'zigate-erase-PDM':{'Name':'zigate-erase-PDM', 'Verbs':{'GET'},          'function':self.rest_zigate_erase_PDM},
        'zigate-mode':   {'Name':'zigate-mode',        'Verbs':{'GET'},          'function': self.rest_zigate_mode},
        'rescan-groups': {'Name':'rescan-groups',      'Verbs':{'GET'},          'function':self.rest_rescan_group},
        'scan-device-for-grp': {'Name':'ScanDevscan-device-for-grpiceForGrp',  'Verbs':{'PUT'}, 'function':self.rest_scan_devices_for_group},
        'ota-firmware-update': {'Name':'ota-firmware-update',   'Verbs':{'PUT'}, 'function':self.rest_ota_firmware_update},
        'ota-firmware-list': {'Name':'ota-firmware-list',       'Verbs':{'GET'}, 'function':self.rest_ota_firmware_list},
        'ota-firmware-device-list': {'Name':'ota-firmware-list','Verbs':{'GET'}, 'function':self.rest_ota_devices_for_manufcode}
        

        }

    self.logging( 'Debug', "do_rest - Verb: %s, Command: %s, Param: %s" %(verb, command, parameters))

    HTTPresponse = {}

    if command in REST_COMMANDS and verb in REST_COMMANDS[command]['Verbs']:
        HTTPresponse = setupHeadersResponse()
        if self.pluginconf.pluginConf['enableKeepalive']:
            HTTPresponse["Headers"]["Connection"] = "Keep-alive"
        else:
            HTTPresponse["Headers"]["Connection"] = "Close"
        HTTPresponse["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
        HTTPresponse["Headers"]["Pragma"] = "no-cache"
        HTTPresponse["Headers"]["Expires"] = "0"
        HTTPresponse["Headers"]["Accept"] = "*/*"
        if version == '1':
            HTTPresponse = REST_COMMANDS[command]['function']( verb, data, parameters)
        elif version == '2':
            HTTPresponse = REST_COMMANDS[command]['functionv2']( verb, data, parameters)

    self.logging( 'Debug', "==> return HTTPresponse: %s" %(HTTPresponse))
    if HTTPresponse == {} or HTTPresponse is None:
        # We reach here due to failure !
        HTTPresponse = prepResponseMessage( self ,setupHeadersResponse())
        HTTPresponse["Status"] = "400 BAD REQUEST"
        HTTPresponse["Data"] = 'Unknown REST command: %s' %command
        HTTPresponse["Headers"]["Content-Type"] = "text/plain; charset=utf-8"

    self.logging( 'Debug', "==> sending HTTPresponse: %s to %s" %(HTTPresponse, Connection))
    self.sendResponse( Connection, HTTPresponse )
