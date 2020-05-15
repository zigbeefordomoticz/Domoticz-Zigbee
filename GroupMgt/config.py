#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


import Domoticz
import json
import pickle
import os.path

def _write_GroupList(self):
    ' serialize pickle format the ListOfGrups '

    self.logging( 'Debug', "Write %s" %self.groupListFileName)
    self.logging( 'Debug', "Dumping: %s" %self.ListOfGroups)

    with open( self.groupListFileName , 'wb') as handle:
        pickle.dump( self.ListOfGroups, handle, protocol=pickle.HIGHEST_PROTOCOL)
    self.HBcount=0

def _load_GroupList(self):
    ' unserialized (load) ListOfGroup from file'

    self.tmpListOfGroups = {}
    if os.path.isfile( self.groupListFileName ):
        with open( self.groupListFileName , 'rb') as handle:
            self.tmpListOfGroups = pickle.load( handle )

    self.ListOfGroups = {}
    updateneeded = False
    for grpid in list(self.tmpListOfGroups):
        self.ListOfGroups[grpid] = {}
        for attribute in ( 'Name', 'WidgetStyle', 'Cluster'):
            self.ListOfGroups[grpid][ attribute ] = {}
            if attribute in self.tmpListOfGroups[grpid]:
                self.ListOfGroups[grpid][ attribute ] =  self.tmpListOfGroups[grpid][ attribute ]

        if 'Tradfri Remote' in self.tmpListOfGroups[grpid]:
            self.ListOfGroups[grpid]['Tradfri Remote'] = dict(self.tmpListOfGroups[grpid]['Tradfri Remote'])

        self.ListOfGroups[grpid]['Imported'] = []
        self.ListOfGroups[grpid]['Devices'] = []

        for item in self.tmpListOfGroups[grpid]['Devices']:
            if len(item) == 2:
                dev, ep = item
                if dev not in self.ListOfDevices:
                    Domoticz.Error("Loading groups - Looks like device %s do not exist anymore, please do a fullscan group" %dev)
                    continue
                ieee = self.ListOfDevices[ dev ] ['IEEE']

            elif len(item) == 3:
                dev, ep, ieee = item
                if dev not in self.ListOfDevices and ieee in self.IEEE2NWK:
                    dev = self.IEEE2NWK[ ieee ]
                    updateneeded = True

            self.ListOfGroups[grpid][ 'Devices' ].append( (dev, ep , ieee) )

    self.logging( 'Debug', "Loading ListOfGroups: %s" %self.ListOfGroups)
    self.logging( 'Debug', "Loading tmpListOfGroups: %s" %self.tmpListOfGroups)

    del self.tmpListOfGroups

    if updateneeded:
        self._write_GroupList()

def load_jsonZigateGroupConfig( self, load=True ):

    if self.json_groupsConfigFilename is None:
        return

    if not os.path.isfile( self.json_groupsConfigFilename ) :
        self.logging( 'Debug', "GroupMgt - Nothing to import from %s" %self.json_groupsConfigFilename)
        return
            
    with open( self.json_groupsConfigFilename, 'rt') as handle:
        ZigateGroupConfig = json.load( handle)

    if not load and len(self.targetDevices) == 0:
        for group_id in ZigateGroupConfig:
            if 'Imported' not in ZigateGroupConfig[group_id]:
                continue
            #Domoticz.Log(" --> Grp: %s --> %s" %(group_id, str(ZigateGroupConfig[group_id]['Imported'])))
            for iterTuple in list(ZigateGroupConfig[group_id]['Imported']):
                #Domoticz.Log("----> %s" %str(iterTuple))
                _ieee = iterTuple[0] 
                if _ieee in self.IEEE2NWK:
                    _nwkid = self.IEEE2NWK[ _ieee ]
                    if _nwkid not in self.targetDevices:
                        self.targetDevices.append( _nwkid )

        # Finaly add Zigate 0x0000 in the target
        if '0000' not in self.targetDevices:
            self.targetDevices.append( '0000' )
        self.logging( 'Debug', "load_ZigateGroupConfiguration - load: %s, targetDevices: %s" %(load, self.targetDevices))
        return

    for group_id in ZigateGroupConfig:
        self.logging( 'Debug', " )> Group ID: %s" %group_id)
        if group_id not in self.ListOfGroups:
            self.logging( 'Debug', "  - Init ListOfGroups")
            self.ListOfGroups[group_id] = {}
            self.ListOfGroups[group_id]['Name'] = ''
            self.ListOfGroups[group_id]['Devices'] = []
            self.ListOfGroups[group_id]['Imported'] = []

        if 'Imported' not in self.ListOfGroups[group_id]:
            self.ListOfGroups[group_id]['Imported'] = []

        if 'Devices' not in self.ListOfGroups[group_id]:
            self.ListOfGroups[group_id]['Devices'] = []

        if 'Name' not in self.ListOfGroups[group_id]:
            self.ListOfGroups[group_id]['Name'] = ZigateGroupConfig[group_id]['Name']

        else:
            if self.ListOfGroups[group_id]['Name'] == '':
                self.ListOfGroups[group_id]['Name'] = ZigateGroupConfig[group_id]['Name']

        self.logging( 'Debug', " )> Group Name: %s" %ZigateGroupConfig[group_id]['Name'])
        if 'Tradfri Remote' in ZigateGroupConfig[group_id]:
            self.ListOfGroups[group_id]['Tradfri Remote'] = ZigateGroupConfig[group_id]['Tradfri Remote']

        if 'Imported' in ZigateGroupConfig[group_id]:
            self.ListOfGroups[group_id]['Imported'] = list(ZigateGroupConfig[group_id]['Imported'])

        self.logging( 'Debug', "load_ZigateGroupConfiguration - Group[%s]: %s List of Devices: %s to be processed" 
            %( group_id, self.ListOfGroups[group_id]['Name'], str(self.ListOfGroups[group_id]['Imported'])))

def write_jsonZigateGroupConfig( self ):

    self.logging( 'Debug', "ListOfGroups: %s" %self.ListOfGroups)
    zigateGroupConfig = {}
    for group_id in self.ListOfGroups:
        zigateGroupConfig[group_id] = {}
        zigateGroupConfig[group_id]['Name'] =  self.ListOfGroups[group_id]['Name']

        if 'Imported' in self.ListOfGroups[group_id]:
            zigateGroupConfig[group_id]['Imported'] = list(self.ListOfGroups[group_id]['Imported'])

        if 'Tradfri Remote' in self.ListOfGroups[group_id]:
            zigateGroupConfig[group_id]['Tradfri Remote'] = self.ListOfGroups[group_id]['Tradfri Remote'] 

    self.logging( 'Debug', "Dumping: %s" %zigateGroupConfig)
    self.logging( 'Debug', "Write to : %s" %self.json_groupsConfigFilename)

    with open( self.json_groupsConfigFilename , 'wt') as handle:
        json.dump( zigateGroupConfig, handle, sort_keys=True, indent=2)

def load_ZigateGroupConfiguration(self):
    """ This is to import User Defined/Modified Groups of Devices for processing in the hearbeatGroupMgt
    Syntax is : <groupid>,<group name>,<list of device IEEE
    """

    if self.groupsConfigFilename is None:
        return
    if not os.path.isfile( self.groupsConfigFilename ) :
        self.logging( 'Debug', "GroupMgt - Nothing to import")
        return

    myfile = open( self.groupsConfigFilename, 'r')
    self.logging( 'Debug', "load_ZigateGroupConfiguration. Reading the file")
    while True:
        tmpread = myfile.readline().replace('\n', '')
        self.logging( 'Debug', "line: %s" %tmpread )
        if not tmpread:
            break

        if tmpread[0] == '#':
            continue

        group_id = group_name = None
        for token in tmpread.split(','):
            if group_id is None:
                # 1st item: group id
                group_id = str(token).strip(' ')

                if group_id not in self.ListOfGroups:
                    self.logging( 'Debug', "  - Init ListOfGroups")
                    self.ListOfGroups[group_id] = {}
                    self.ListOfGroups[group_id]['Name'] = ''
                    self.ListOfGroups[group_id]['Devices'] = []
                    self.ListOfGroups[group_id]['Imported'] = []

                if 'Imported' not in self.ListOfGroups[group_id]:
                    self.ListOfGroups[group_id]['Imported'] = []

                if 'Devices' not in self.ListOfGroups[group_id]:
                    self.ListOfGroups[group_id]['Devices'] = []

                self.logging( 'Debug', " )> Group ID: %s" %group_id)
                continue

            elif group_id and group_name is None:
                # 2nd item: group name
                group_name = str(token)
                if 'Name' not in self.ListOfGroups[group_id]:
                    self.ListOfGroups[group_id]['Name'] = group_name
                else:
                    if self.ListOfGroups[group_id]['Name'] == '':
                        self.ListOfGroups[group_id]['Name'] = group_name

                self.logging( 'Debug', " )> Group Name: %s" %group_name)
                continue

            else:
                # Last part, list of IEEE
                if group_id and group_name and token.strip() != '':
                    _ieeetoken = token.strip()
                    if  len(_ieeetoken.split('/')) == 1 :
                        _ieee = _ieeetoken
                        _ieeeEp = None

                    elif len(_ieeetoken.split('/')) == 2:
                        _ieee, _ieeeEp = _ieeetoken.split('/')

                    else:
                        Domoticz.Error("load_ZigateGroupConfiguration - Error in ZigateGroupConfig: %s" %( _ieeetoken))
                        continue

                    if _ieee not in self.IEEE2NWK:
                        # Check if this is not the Zigate itself
                        Domoticz.Error("load_ZigateGroupConfiguration - Unknown address %s to be imported" %_ieee )
                        continue

                    # Finaly, let's check if this is not an IKEA Tradfri Remote
                    nwkid = self.IEEE2NWK[_ieee]
                    _tradfri_remote = False
                    if ( 'Ep' in self.ListOfDevices[nwkid] and '01' in self.ListOfDevices[nwkid]['Ep']
                            and 'ClusterType' in self.ListOfDevices[nwkid]['Ep']['01'] ):

                        for iterDev in self.ListOfDevices[nwkid]['Ep']['01']['ClusterType']:

                            if self.ListOfDevices[nwkid]['Ep']['01']['ClusterType'][iterDev] == 'Ikea_Round_5b':
                                # We should not process it through the group.
                                self.logging( 'Log', "Not processing Ikea Tradfri as part of Group. Will enable the Left/Right actions")
                                self.ListOfGroups[group_id]['Tradfri Remote'] = {}
                                self.ListOfGroups[group_id]['Tradfri Remote']['Device Addr'] = nwkid
                                self.ListOfGroups[group_id]['Tradfri Remote']['Device Id'] = iterDev
                                _tradfri_remote = True

                    if not _tradfri_remote:
                        # Let's check if we don't have the EP included as well
                        self.ListOfGroups[group_id]['Imported'].append( (_ieee, _ieeeEp) )

                self.logging( 'Debug', " )> Group Imported: %s" %group_name)

        if group_id :
            self.logging( 'Debug', "load_ZigateGroupConfiguration - Group[%s]: %s List of Devices: %s to be processed" 
                %( group_id, self.ListOfGroups[group_id]['Name'], str(self.ListOfGroups[group_id]['Imported'])))

    myfile.close()