#!/usr/bin/env python3
# coding: utf-8 -*-
"""
	Module: z_var.py

	Description: All global variables

"""
FirmwareVersion = ''		# Firmware version , initialized at start by requesting the firmware version of Ziate
HeartbeatCount = 0		
transport = 'unknow'
ReqRcv = ''
ZigateConn = ''
CrcCheck = 1				# Enable of not the CrcCheck when receiving messages
cmdInProgress = ''
sendDelay = 0				# Enable or not a delay in send command 0- no delay -1 a delay of n seconds ( n is based on the number of commands in the ques
liveSendDelay = 0
enableDeviceList = 1		# Enable or Disable the backup of ListOfDevices in DeviceLIst.txt
storeDiscoveryFrames = 1	# Enable tracking of Discovery process, and finaly store the outcome in DeviceDiscovery-[IEEE].txt file
homedirectory =''			# Home directory where file would be created/store ( DeviceList.txt , DeviceDiscovery-xxx.txt
