#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import json

import os.path

from time import time

from Modules.zigateConsts import ADDRESS_MODE, MAX_LOAD_ZIGATE, ZIGATE_EP

from GroupMgt.tool import TIMEOUT, MAX_CYCLE


def modification_date( filename ):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    return os.path.getmtime( filename )


def hearbeatGroupMgt( self ):
    ' hearbeat to process Group Management actions '
    # Groups Management


    def _start( self ):
             # Check if there is an existing Pickle file. If this file is newer than ZigateConf, we can simply load it and finish the Group startup.
            # In case the file is older, this means that ZigateGroupConf is newer and has some changes, do the full process.

        # Check if the DeviceList file exist.
        self.logging( 'Log', "Group Management - Init phase")
        self.StartupPhase = 'scan'
        last_update_GroupList = 0
        if os.path.isfile( self.groupListFileName ) :
            self.logging( 'Debug', "--->GroupList.pck exists")
            last_update_GroupList = modification_date( self.groupListFileName )
            self.logging( 'Debug', "--->Last Update of GroupList: %s" %last_update_GroupList)
        else:
            self.logging( 'Debug', "--->GroupList.pck doesn't exist")

        if self.groupsConfigFilename or self.json_groupsConfigFilename:
            if self.groupsConfigFilename and os.path.isfile( self.groupsConfigFilename ):
                self.logging( 'Debug', "------------>Config file exists %s" %self.groupsConfigFilename)
                self.txt_last_update_ConfigFile = modification_date( self.groupsConfigFilename )
                self.logging( 'Debug', "------------>Last Update of TXT Config File: %s" %self.txt_last_update_ConfigFile)
                self.load_jsonZigateGroupConfig( load=False ) # Just to load the targetDevices if applicable
                self.fullScan = False

            if self.json_groupsConfigFilename and os.path.isfile( self.json_groupsConfigFilename ):
                self.logging( 'Debug', "------------>Json Config file exists")
                self.json_last_update_ConfigFile = modification_date( self.json_groupsConfigFilename )
                self.logging( 'Debug', "------------>Last Update of JSON Config File: %s" %self.json_last_update_ConfigFile)
                self.load_jsonZigateGroupConfig( load=False ) # Just to load the targetDevices if applicable
                self.fullScan = False

            if last_update_GroupList > self.txt_last_update_ConfigFile and last_update_GroupList > self.json_last_update_ConfigFile:
                # GroupList is newer , just reload the file and exit
                self.logging( 'Status', "--------->No update of Groups needed")
                self.StartupPhase = 'completion'
                self._load_GroupList()

        else:    # No config file, so let's move on
            self.logging( 'Debug', "------>No Config file, let's use the GroupList")
            self.logging( 'Debug', "------>switch to end of Group Startup")
            self._load_GroupList()
            self.StartupPhase = 'completion'

    def _scan( self ):
        if self.HB <= 12:
            # Tempo 1' before starting Group
            self.HB += 1
            return
        # We will send a Request for Group memebership to each active device
        # In case a device doesn't belo,ng to any group, no response is provided.
        self.logging( 'Log', "Group Management - Discovery mode - Searching for Group Membership (or continue)")
        self.stillWIP = True
        _workcompleted = True

        if self.fullScan:
            listofdevices = list(self.ListOfDevices.keys())

        else:
            listofdevices = self.targetDevices

        self.logging( 'Log', "Group Management - Discovery mode - Devices to be queried: %s" %str(listofdevices))
        for iterDev in listofdevices:
            _mainPowered = False
            if iterDev not in self.ListOfDevices:
                # Most likely this device has been removed
                continue

            if ( 'MacCapa' in self.ListOfDevices[iterDev] and self.ListOfDevices[iterDev]['MacCapa'] == '8e' ):
                _mainPowered = True

            if ( 'PowerSource' in self.ListOfDevices[iterDev] and self.ListOfDevices[iterDev]['PowerSource'] == 'Main' ):
                _mainPowered = True

            if not _mainPowered:
                self.logging( 'Debug', " - %s not main Powered" %(iterDev))
                continue

            if ( 'Health' in self.ListOfDevices[iterDev] and self.ListOfDevices[iterDev]['Health'] == 'Not Reachable' ):
                self.logging( 'Debug', "Group Management - Discovery mode - skiping device %s which is Not Reachable" %iterDev)
                continue

            if 'Ep' in self.ListOfDevices[iterDev]:
                for iterEp in self.ListOfDevices[iterDev]['Ep']:
                    if iterEp == 'ClusterType': continue
                    if ( iterDev == '0000' or \
                            ( 'ClusterType' in self.ListOfDevices[iterDev] or 'ClusterType' in self.ListOfDevices[iterDev]['Ep'][iterEp] )) and \
                            '0004' in self.ListOfDevices[iterDev]['Ep'][iterEp] and \
                            ( '0006' in self.ListOfDevices[iterDev]['Ep'][iterEp] or '0008' in self.ListOfDevices[iterDev]['Ep'][iterEp] or \
                            '0102' in self.ListOfDevices[iterDev]['Ep'][iterEp] ):
                        # As we are looking for Group Membership, we don't know to which Group it could belongs.
                        # XXXX is a special group in the code to be used in that case.
                        if 'GroupMgt' not in  self.ListOfDevices[iterDev]:
                            self.ListOfDevices[iterDev]['GroupMgt'] = {}

                        if iterEp not in  self.ListOfDevices[iterDev]['GroupMgt']:
                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp] = {}

                        if 'XXXX' not in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX'] = {}
                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase'] = {}
                            self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase-Stamp'] = {}

                        if ( 'Phase' in self.ListOfDevices[iterDev]['GroupMgt'][iterEp][ 'XXXX' ] and \
                                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][ 'XXXX' ]['Phase'] == 'REQ-Membership' ):
                            continue

                        if  len(self.ZigateComm.zigateSendingFIFO) >= MAX_LOAD_ZIGATE:
                            self.logging( 'Debug', "normalQueue: %s" %len(self.ZigateComm.zigateSendingFIFO))
                            self.logging( 'Debug', "normalQueue: %s" %(str(self.ZigateComm.zigateSendingFIFO)))
                            self.logging( 'Debug', "too busy, will try again ...%s" %len(self.ZigateComm.zigateSendingFIFO))
                            _workcompleted = False
                            break # will continue in the next cycle

                        self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase'] = 'REQ-Membership'
                        self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase-Stamp'] = int(time())
                        self._getGroupMembership(iterDev, iterEp)   # We request MemberShip List
                        self.logging( 'Debug', " - request group membership for %s/%s" %(iterDev, iterEp))
        else:
            if _workcompleted:
                self.logging( 'Log', "hearbeatGroupMgt - Finish Discovery Phase" )
                self.StartupPhase = 'finish scan'

    def _finishing_scan( self ):
        # Check for completness or Timeout
        if self.StartupPhase ==  'finish scan':
            self.logging( 'Log', "Group Management - Membership gathering")

        self.StartupPhase = 'finish scan continue'
        now = time()
        self.stillWIP = True
        _completed = True
        for iterDev in self.ListOfDevices:
            if 'GroupMgt' in self.ListOfDevices[iterDev]:       # We select only the Device for which we have requested Group membership
                for iterEp in self.ListOfDevices[iterDev]['GroupMgt']:
                    for iterGrp in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                        if iterGrp == 'XXXX': 
                            continue

                        if 'Phase' not in self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]:
                            continue

                        self.logging( 'Debug', 'Checking if process is done for %s/%s - %s -> %s' 
                                %(iterDev,iterEp,iterGrp,str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp])))

                        if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] == 'OK-Membership':
                            continue

                        if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] + TIMEOUT > now:
                            _completed = False
                            break # Need to wait a couple of sec.

                        self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'TimeOut'
                        self.logging( 'Debug', " - No response receive for %s/%s - assuming no group membership for %s " %(iterDev,iterEp, iterGrp))

                    else:
                        if 'XXXX' in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                            self.logging( 'Debug', 'Checking if process is done for %s/%s - XXXX -> %s' 
                                %(iterDev,iterEp,str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX'])))
                            if self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']['Phase-Stamp'] + TIMEOUT > now:
                                _completed = False
                                break
                            del  self.ListOfDevices[iterDev]['GroupMgt'][iterEp]['XXXX']

        if _completed:
            for iterGrp in self.ListOfGroups:
                self.logging( 'Status', "Group: %s - %s" %(iterGrp, self.ListOfGroups[iterGrp]['Name']))
                self.logging( 'Debug', "Group: %s - %s" %(iterGrp, str(self.ListOfGroups[iterGrp]['Devices'])))
                for iterDev, iterEp, iterIEEE in self.ListOfGroups[iterGrp]['Devices']:
                    if iterDev not in self.ListOfDevices:
                        Domoticz.Error("Group Management - seems that Group %s is refering to a non-existing device %s/%s" \
                                %(self.ListOfGroups[iterGrp]['Name'], iterDev, iterEp))
                        continue

                    if 'IEEE' not in self.ListOfDevices[iterDev]:
                        Domoticz.Error("Group Management - seems that Group %s is refering to a device %s/%s with an unknown IEEE" \
                                %(self.ListOfGroups[iterGrp]['Name'], iterDev, iterEp))
                        continue

                    self.logging( 'Status', "  - device: %s/%s %s" %( iterDev, iterEp, self.ListOfDevices[iterDev]['IEEE']))
            self.logging( 'Status', "Group Management - Discovery Completed" )
            self.StartupPhase = 'load config'

    def _load_config( self):
        
        # Which config file is the newest
        self.logging( 'Debug', "Group Management - Loading Zigate Group Configuration file")
        if self.json_last_update_ConfigFile >= self.txt_last_update_ConfigFile:
            # Take JSON
            self.logging( 'Debug', "Group Management - Loading Zigate Group Configuration file JSON")
            self.load_jsonZigateGroupConfig()

        else:
            #Take TXT
            self.logging( 'Debug', "Group Management - Loading Zigate Group Configuration file TXT")
            self.load_ZigateGroupConfiguration()

        self.TobeAdded = []
        self.TobeRemoved = []
        self.StartupPhase = 'process config'

    def _process_config( self ):
            self.stillWIP = True
            for iterGrp in self.ListOfGroups:
                if 'Imported' not in self.ListOfGroups[iterGrp]:
                    self.logging( 'Debug', "Nothing to import ...")
                    continue

                if len(self.ListOfGroups[iterGrp]['Imported']) == 0 and len(self.ListOfGroups[iterGrp]['Devices']) == 0 :
                    self.logging( 'Debug', "Nothing to import and no Devices ...")
                    continue

                self.logging( 'Debug', "Processing Group: %s - Checking Removal" %iterGrp)
                # Remove group membership
                self.logging( 'Debug', " - %s" %self.ListOfGroups[iterGrp]['Devices'])
                self.logging( 'Debug', " - %s" %self.ListOfGroups[iterGrp]['Imported'])

                for iterDev, iterEp, iterIEEE in self.ListOfGroups[iterGrp]['Devices']:
                    if iterDev not in self.ListOfDevices:
                        Domoticz.Error("hearbeat Group - Most likely, device %s is not paired anymore ..." %iterDev)
                        continue

                    if 'IEEE' not in self.ListOfDevices[iterDev]:
                        break

                    iterIEEE = self.ListOfDevices[iterDev]['IEEE']

                    self.logging( 'Debug', "    - checking device: %s / %s to be removed " %(iterDev, iterEp))
                    self.logging( 'Debug', "    - checking device: %s " %self.ListOfGroups[iterGrp]['Imported'])
                    self.logging( 'Debug', "    - checking device: IEEE: %s " %iterIEEE)

                    _found = False
                    for iterTuple in self.ListOfGroups[iterGrp]['Imported']:
                        if iterIEEE == iterTuple[0]:
                            if iterTuple[1]: 
                                if iterEp == iterTuple[1]:
                                    _found = True
                                    break
                            else:
                                _found = True
                                break

                    if _found:
                        continue

                    removeIEEE = iterIEEE
                    if iterIEEE not in self.IEEE2NWK:
                        Domoticz.Error("Unknown IEEE to be removed %s" %iterIEEE)
                        continue

                    removeNKWID = self.IEEE2NWK[iterIEEE]
                    if removeNKWID not in self.ListOfDevices:
                        Domoticz.Error("Unknown IEEE to be removed %s" %removeNKWID)
                        continue

                    self.logging( 'Debug', " %s/%s to be removed from %s" 
                            %(removeNKWID, iterEp, iterGrp))
                    self.TobeRemoved.append( ( removeNKWID, iterEp, iterGrp ) )

                self.logging( 'Debug', "Processing Group: %s - Checking Adding" %iterGrp)
                # Add group membership
                for iterIEEE, import_iterEp in self.ListOfGroups[iterGrp]['Imported']:
                    if iterIEEE not in self.IEEE2NWK:
                        Domoticz.Error("heartbeat Group - Unknown IEEE %s" %iterIEEE)
                        continue

                    iterDev = self.IEEE2NWK[iterIEEE]
                    self.logging( 'Debug', "    - checking device: %s to be added " %iterDev)
                    if iterDev in self.ListOfGroups[iterGrp]['Devices']:
                        self.logging( 'Debug', "%s already in group %s" %(iterDev, iterGrp))
                        continue

                    self.logging( 'Debug', "       - checking device: %s " %iterDev)
                    if 'Ep' in self.ListOfDevices[iterDev]:
                        _listDevEp = []
                        if import_iterEp:
                            _listDevEp.append(import_iterEp)

                        else:
                            _listDevEp = list(self.ListOfDevices[iterDev]['Ep'])
                        self.logging( 'Debug', 'List of Ep: %s' %_listDevEp)

                        for iterEp in _listDevEp:
                            self.logging( 'Debug', "       - Check existing Membership %s/%s" %(iterDev,iterEp))

                            if ('GroupMgt' in self.ListOfDevices[iterDev] and \
                                    iterEp in self. ListOfDevices[iterDev]['GroupMgt'] and \
                                    iterGrp in self.ListOfDevices[ iterDev]['GroupMgt'][iterEp] and \
                                    self.ListOfDevices[iterDev] ['GroupMgt'][iterEp][iterGrp] ['Phase'] == 'OK-Membership'): 
                                self.logging( 'Debug', "       - %s/%s already in group %s" %(iterDev, iterEp, iterGrp)) 
                                continue

                            if iterEp not in self.ListOfDevices[iterDev]['Ep']:
                                Domoticz.Error("whearbeatGroupMgt - unknown EP %s for %s against (%s)" %(iterEp, iterDev, self.ListOfDevices[iterDev]['Ep']))
                                continue

                            if  ( iterDev == '0000' or \
                                    ( 'ClusterType' in self.ListOfDevices[iterDev] or 'ClusterType' in self.ListOfDevices[iterDev]['Ep'][iterEp] )) and \
                                    '0004' in self.ListOfDevices[iterDev]['Ep'][iterEp] and \
                                    ( '0006' in self.ListOfDevices[iterDev]['Ep'][iterEp] or '0008' in self.ListOfDevices[iterDev]['Ep'][iterEp] or \
                                        '0102' in self.ListOfDevices[iterDev]['Ep'][iterEp] ):
                                self.logging( 'Debug', " %s/%s to be added to %s"
                                        %( iterDev, iterEp, iterGrp))
                                self.TobeAdded.append( ( iterIEEE, iterDev, iterEp, iterGrp ) )

            self.logging( 'Log', "Group Management - End of Configuration processing" )
            self.logging( 'Log', "  - To be removed : %s" %self.TobeRemoved)
            self.logging( 'Log', "  - To be added : %s" %self.TobeAdded)
            if len(self.TobeAdded) == 0 and len(self.TobeRemoved) == 0:
                self.StartupPhase = 'check group list'
                self._SaveGroupFile = True
                self.logging( 'Debug', "Updated Groups are : %s" %self.UpdatedGroups)
                self._write_GroupList()
                for iterGroup in self.UpdatedGroups:
                    self._identifyEffect( iterGroup, '01', effect='Okay' )
                    self.adminWidgets.updateNotificationWidget( self.Devices, 'Groups %s operational' %iterGroup)

            else:
                self.StartupPhase = 'processing'

    def _processing( self ):
            
        self.stillWIP = True
        _completed = True
        self.logging( 'Debug', "hearbeatGroupMgt - Perform Zigate commands")
        self.logging( 'Debug', " - Removal to be performed: %s" %str(self.TobeRemoved))
        for iterDev, iterEp, iterGrp in list(self.TobeRemoved):
            if iterDev not in self.ListOfDevices and iterDev != '0000':
                Domoticz.Error("hearbeatGroupMgt - unconsistency found. %s not found in ListOfDevices." %iterDev)
                continue

            if iterEp not in self.ListOfDevices[iterDev]['GroupMgt']:
                Domoticz.Error("hearbeatGroupMgt - unconsistency found. %s/%s not found in ListOfDevices." %(iterDev,iterEp))
                continue

            if iterGrp not in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                Domoticz.Error("hearbeatGroupMgt - unconsistency found. Group: %s for %s/%s not found in ListOfDevices." \
                        %(iterGrp, iterDev,iterEp))
                continue

            if  len(self.ZigateComm.zigateSendingFIFO) >= MAX_LOAD_ZIGATE:
                self.logging( 'Debug', "normalQueue: %s" %len(self.ZigateComm.zigateSendingFIFO))
                self.logging( 'Debug', "normalQueue: %s" %(str(self.ZigateComm.zigateSendingFIFO)))
                _completed = False
                self.logging( 'Debug', "Too busy, will come back later")
                break # will continue in the next cycle

            self._removeGroup( iterDev, iterEp, iterGrp )
            self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'DEL-Membership'
            self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = int(time())
            self.TobeRemoved.remove( (iterDev, iterEp, iterGrp) )

        self.logging( 'Debug', " - Add to be performed: %s" %str(self.TobeAdded))
        for iterIEEE, iterDev, iterEp, iterGrp in list(self.TobeAdded):
            if  len(self.ZigateComm.zigateSendingFIFO) >= MAX_LOAD_ZIGATE:
                self.logging( 'Debug', "normalQueue: %s" %len(self.ZigateComm.zigateSendingFIFO))
                self.logging( 'Debug', "normalQueue: %s" %(str(self.ZigateComm.zigateSendingFIFO)))
                _completed = False
                self.logging( 'Debug', "Too busy, will come back later")
                break # will continue in the next cycle

            if iterDev not in self.ListOfDevices and iterDev != '0000':
                Domoticz.Error("hearbeatGroupMgt - unconsitecy found. %s not for found in ListOfDevices." %iterDev)
                continue

            if 'GroupMgt' not in self.ListOfDevices[iterDev]:
                self.ListOfDevices[iterDev]['GroupMgt'] = {}
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp] = {}
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp] = {}
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = {}
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = {}

            if iterGrp not in self.ListOfDevices[iterDev]['GroupMgt']:
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp] = {}
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = {}
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = {}

            if 'Phase' not in self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]:
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = {}
                self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = {}

            self._addGroup( iterIEEE, iterDev, iterEp, iterGrp )
            self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'ADD-Membership'
            self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] = int(time())
            self.TobeAdded.remove( (iterIEEE, iterDev, iterEp, iterGrp) )

        if _completed:
            self.StartupPhase = 'finish configuration'               
 
    def _finish_config( self):
        
        # Check for completness or Timeout
        self.logging( 'Log', "Group Management - Finishing configuration mode")
        self.stillWIP = True
        now = time()
        _completed = True
        for iterDev in self.ListOfDevices:
            if 'GroupMgt' not in self.ListOfDevices[iterDev]:
                continue

            if 'Ep' in self.ListOfDevices[iterDev]:
                for iterEp in self.ListOfDevices[iterDev]['GroupMgt']:
                    for iterGrp in self.ListOfDevices[iterDev]['GroupMgt'][iterEp]:
                        #if iterDev == '0000' and iterGrp in ( '0000' ):
                            #Adding Zigate to group 0x0000 or 0xffff
                            # We do not get any response
                        #    self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'OK-Membership'

                        if iterGrp == 'XXXX': 
                            continue

                        if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] in ( 'OK-Membership', 'TimmeOut'):
                            continue

                        if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] not in ( 'DEL-Membership' ,'ADD-Membership' ):
                            self.logging( 'Debug', "Unexpected phase for %s/%s in group %s : phase!: %s"
                            %( iterDev, iterEp, iterGrp,  str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp])))
                            continue

                        if self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase-Stamp'] + TIMEOUT > now:
                            _completed = False
                            break # Wait a couple of Sec

                        self.logging( 'Debug', 'Checking if process is done for %s/%s - %s -> %s' 
                                %(iterDev,iterEp,iterGrp,str(self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp])))

                        self.ListOfDevices[iterDev]['GroupMgt'][iterEp][iterGrp]['Phase'] = 'TimeOut'
                        self.logging( 'Debug', " - No response receive for %s/%s - assuming no group membership to %s" %(iterDev,iterEp, iterGrp))

        if _completed:
            self.logging( 'Log', "hearbeatGroupMgt - Configuration mode completed" )
            self.Cycle += 1
            if self.Cycle > MAX_CYCLE:
                Domoticz.Error("We reach the max number of Cycle and didn't succeed in the Group Creation")
                self._SaveGroupFile = False
                self.StartupPhase = 'check group list'

            else:
                self.StartupPhase = 'scan'
                for iterDev in self.ListOfDevices:
                    if 'GroupMgt' in self.ListOfDevices[iterDev]:
                        del self.ListOfDevices[iterDev]['GroupMgt']

                for iterGrp in list(self.ListOfGroups):
                    del self.ListOfGroups[iterGrp] 
 
    def _checking_group_list( self ):
        
        # GroupList is build in the germembership response
        self.logging( 'Log', "Group Management - Checking Group list")
        self.stillWIP = True
        for iterGrp in list(self.ListOfGroups):
            self.logging( 'Debug', "Checking %s " %iterGrp)
            self.logging( 'Debug', "  - Devices: %s" %len(self.ListOfGroups[iterGrp]['Devices']))
            for x in self.Devices:
                if self.Devices[x].DeviceID == iterGrp:
                    if len(self.ListOfGroups[iterGrp]['Devices']) == 0:
                        self.logging( 'Log', "hearbeatGroupMgt - Remove Domotticz Device : %s for Group: %s " %(self.Devices[x].Name, iterGrp))
                        self._removeDomoGroupDevice( iterGrp)
                        del self.ListOfGroups[iterGrp] 

                    else:
                        self.ListOfGroups[iterGrp]['Name'] = self.Devices[x].Name
                        # Check if we need to update the Widget
                        self._updateDomoGroupDeviceWidget(self.ListOfGroups[iterGrp]['Name'], iterGrp)
                        self.logging( 'Log', "hearbeatGroupMgt - _updateDomoGroup done")
                    break

            else:
                # Unknown group in Domoticz. Create it
                if len(self.ListOfGroups[iterGrp]['Devices']) == 0:
                    del self.ListOfGroups[iterGrp] 
                    continue

                if self.ListOfGroups[iterGrp]['Name'] == '':
                    self.ListOfGroups[iterGrp]['Name'] = "Zigate Group %s" %iterGrp
                self.logging( 'Log', "hearbeatGroupMgt - create Domotciz Widget for %s " %self.ListOfGroups[iterGrp]['Name'])
                self._createDomoGroupDevice( self.ListOfGroups[iterGrp]['Name'], iterGrp)

        self.StartupPhase = 'completion'
        # We write GroupList to cash only if in case of success.
        if self._SaveGroupFile:
            self._write_GroupList()
            self.logging( 'Status', "Group Management - startup done")
            self.adminWidgets.updateNotificationWidget( self.Devices, 'Groups management startup completed') 
 
    def _completion( self):
        for iterGrp in self.ListOfGroups:
            self.logging( 'Status', "Group: %s - %s" %(iterGrp, self.ListOfGroups[iterGrp]['Name']))
            self.logging( 'Debug', "Group: %s - %s" %(iterGrp, str(self.ListOfGroups[iterGrp]['Devices'])))
            for iterDev, iterEp , iterIEEE in self.ListOfGroups[iterGrp]['Devices']:
                if iterDev in self.ListOfDevices:
                    self.logging( 'Status', "  - device: %s/%s %s" %( iterDev, iterEp, self.ListOfDevices[iterDev]['IEEE']))

        # Store Group in report under json format (Debuging purpose)
        json_filename = self.groupListReport
        with open( json_filename, 'wt') as json_file:
            json_file.write('\n')
            json.dump( self.ListOfGroups, json_file, indent=4, sort_keys=True)

        self.StartupPhase = 'ready'
        self.stillWIP = False 
 

    if self.StartupPhase == 'ready':
        for group_nwkid in self.ListOfGroups:
            self.updateDomoGroupDevice( group_nwkid)

    elif self.StartupPhase == 'start':

        _start( self )

    elif self.StartupPhase == 'scan':

        _scan( self )

    elif self.StartupPhase in ( 'finish scan', 'finish scan continue') :

        _finishing_scan( self )

    elif  self.StartupPhase == 'load config':

        _load_config( self )

    elif self.StartupPhase == 'process config':

        _process_config( self )

    elif self.StartupPhase == 'processing':

        _processing( self )

    elif self.StartupPhase == 'finish configuration':

        _finish_config( self )

    elif self.StartupPhase == 'check group list':

        _checking_group_list( self )

    elif self.StartupPhase == 'completion':

        _completion( self )