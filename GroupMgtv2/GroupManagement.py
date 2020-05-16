#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""

This is the Version 2 of Zigate Plugin Group Management.

The aim of this Class is to be able to manage groups as they were in the previous version,
but also to have instant groupmembership provisioning instead of the batch approach of the previous version.

Important, the aim is not to break any upward compatibility

Group management rely on 2 files:

- ZigateGroupsConfig -xx.json which contains the Group configuration/definition
- GroupsList-xx.pck which contains somehow a cash of what is available on each devices 
                    (1) will be converted to a JSON format


DATA STRUCTURES

- Each device knowns its group membership. ( ListOfDevices)
  Today there is an attribut 'GroupMgt' which is a list of Group with a status
  V2 attribut 'GroupMembership' which is a list of Group the device is member of.
       - Status: TobeAdd, AddedReq, Ok, Error, ToBeRemoved, RemovedReq
       - TimeStamp (when the Status has been set)

- ListOfGroups is the Data structutre supporting Groups
  ListOfGroups[group id]['Name']            - Group Name as it will be created in Domoticz
  ListOfGroups[group id]['Devices']         - List of Devices associed to this group on Zigate
  ListOfGroups[group id]['Tradfri Remote']  - Manage the Tradfri Remote

  

SYNOPSIS

- At plugin start, if the group cash file exist, read and populate the data structutre.
                   if the cash doesn't exist, request to each Main Powered device tfor their existing group membership.
                   collect the information and populate the data structutre accoridngly.

- When the data strutcutre is fully loaded, the object will be full operational and able to handle the following request
    - adding group  membership to a specific device
    - removing group membership to a specific device
    - view group membership

    - actioning ( On, Off, LevelControl, ColorControl , WindowCovering )    

    - Managing device short address changes ( could be better to store the IEEE )         


      











""

