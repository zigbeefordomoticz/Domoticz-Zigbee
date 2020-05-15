#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import subprocess

def restartPluginViaDomoticzJsonApi( self ):
    
    if self.WebUsername and self.WebPassword:
        url = 'http://%s:%s@127.0.0.1:%s' %(self.WebUsername, self.WebPassword, self.pluginconf.pluginConf['port'])
    else:
        url = 'http://127.0.0.1:%s' %self.pluginconf.pluginConf['port']


    url += '/json.htm?type=command&param=updatehardware&htype=94'
    url += '&idx=%s'     %self.pluginparameters['HardwareID']
    url += '&name=%s'    %self.pluginparameters['Name']
    url += '&address=%s' %self.pluginparameters['Address']
    url += '&port=%s'    %self.pluginparameters['Port']
    url += '&serialport=%s' %self.pluginparameters['SerialPort']
    url += '&Mode1=%s'   %self.pluginparameters['Mode1']
    url += '&Mode2=%s'   %self.pluginparameters['Mode2']
    url += '&Mode3=%s'   %self.pluginparameters['Mode3']
    url += '&Mode4=%s'   %self.pluginparameters['Mode4']
    url += '&Mode5=%s'   %self.pluginparameters['Mode5']
    url += '&Mode6=%s'   %self.pluginparameters['Mode6']
    url += '&extra=%s'   %self.pluginparameters['Key']
    url += '&enabled=true'
    url += '&datatimeout=0'

    Domoticz.Status( "Plugin Restart command : %s" %url)
    _cmd = "/usr/bin/curl '%s' &" %url

    subprocess.Popen([ _cmd ], shell=False)
