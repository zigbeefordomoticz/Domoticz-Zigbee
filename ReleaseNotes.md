# Release Notes

Please use the Wiki <https://github.com/pipiche38/Domoticz-Zigate-Wiki> and feel free to contribute.
And if you have any questions, problem please use first the Domoticz forum.

- French channel : <https://easydomoticz.com/forum/viewtopic.php?f=8&t=7099>
- English channel : <https://www.domoticz.com/forum/viewtopic.php?f=28&t=24789>

If you want to contribue , please let us know , we are looking for help in various areas:

- certifying new ZigBee devices
- improving the plugin
- increasing the level of documentation for end user

## Attention

stable will remain on 4.11.17 and no further update will be done. This is the latest version supported with DomoticZ below 2020 ( 4.xxxx like )
stable-2020 is the new stable branche dedicated for DomoticZ equal and above 2020.1

Release Numbering

- Odd numbers --> Stable/6
- Even numbers  --> Beta/6

## 1 April 2022 - stable6.1.001 ( Zigate, Zigate+, TI CCxxxx ZNP, Silicon Labs EZSP)

- [Technical] - relying zigpy libraries for none Zigate Coordinators
- [Hardware] - Enable Texas Instrument Coordinator based on zigpy-znp library
- [Hardware] - Enable Silicon Labs Coordinator based on zigpy bellows library
- [Technical] - Enable analytics information from WebUI
- [Hardware] - Moes Curtain Switch calibration
- [Hardware] - Moes Siren without temp/humi sensors
- [Hardware] - New Lumi remote switch b28ac1
- [Hardware] - Tuya plug \_TS3000
- [Hardware] - Enable calibration for MOES Thermostat
- [WebUI] - API to getBattery device status
- [WebUI] - Refactoring of the Topology Report. Click on node to get more insights
- [Hardware] - Schneider Shutter/Dimmer NHPBSHUTTER1
- [Hardware] - Tuya garage door
- [Hardware] - Orvibo dry Contact Module CM10ZW

## 23 January 2022  - 5.1.18

- [Issue] - Fix several issues preventing good pairing
- [Hardware] - Orvibo dry Contact CM10ZW
- [Hardware] - Lidle Valve
- [Hardware] - TS004F Scene controller

## January 2022 - 5.1.17

- [Hardware] - New Profalux Blind MOCT-xxxx
- [Technocal] - Several fixes

## 27 December 2021 - 5.1.16

- [Hardware] - Scene controller Tuya TS004F
- [Hardware] - New Aqara Door sensor (Lumi.Magnet.acn001)
- [Hardware] - Tuya Smart all in One ( Lux, Motion, temp, Humi)
- [Hardware] - Config file for Casa.IA devices
- [Hardware] - Danfoss Ally Room Sensor 014G2480
- [Hardware] - Support of Firmware 321
- [Issue] - Fix Config Reporting issue with Frient Temp/Humi sensor
- [Hardware] - Aqara Vibration sensivity can be define on a per device.
- [Hardware] - Enable Wiser TRV to get temperature from external sensor

## 7 November 2021 - 5.1.15

- [Hardware] - Sunricher remote control ZG2858A
- [Technical] - Allow binding on cluster 0300
- [Technical] - Updating Meter when receving summation and not only on instant power
- [Technical] - Finishing TS011 Plug
- [Technical] - Provide REST API for Binding Table and Group binding
- [Technical] - KADRILJ roller blind
- [Technical] - Allow creating groups on battery based device.
- [Issue] - Fixing issues in ZLinky alarm
- [Hardware] - Additional Danfoss parameters for eTRV

## 1 November 2021 - 5.1.14

- [Web UI] - Finishing french translation
- [Hardware] - Additional Moes eTRV Tuya
- [Hardware] - Handling the IKEA TRadfri open/close remote

## 27 October 2021 - 5.1.13

- [Web UI] - Improve Franch translation
- [Hardware] - Support Casa.IA CPC321, 3 lignes monitoring
- [Hardware] - Support Tuya TS001F Plug with metering
- [Technical] - Fix issue preventing correct pairing of Mija Switch

## 25 October 2021 - 5.1.12

- [Technical] - After a Power Off/On make sure to retreive the current status of Switches, Plug, Led and Level Control

## 25 October 2021 - 5.1.12

- [Technical] - After a Power Off/On make sure to retreive the current status of Switches, Plug, Led and Level Control

## 24 October 2021 - 5.1.11

- [Technical] - After a Power Off/On make sure to retreive the current status of Switches, Plug, Led and Level Control

## 24 October 2021 - 5.1.10

- [Hardware] - Supporting Ikea Tradfri SHORTCUT and Remote N2
- [Hardware] - Danfoss heating TRV. ( Zone and danfoss setpoint)
- [Hardware] - Enabling Legrand emulation mode
- [Hardware] - Supporting ZLinky device
- [Hardware] - Correct calculation of Wiser eTRV valve %
- [WebUI] - New functionalities: Re-creation of Widgets, Reset Mode setting
- [Hardware] - SMaBiT av2019/29Q support ( Siren )
- [Technical] - Fix Metering calculation for Meter widget
- [Hardware] - First support of Accova Taffetas2
- [Technical] - Pairing enhacements

## 05 September 2021 - 5.1.09

- [WebAdmin] - Update of WebAdmin

## 02 September 2021 - 5.1.08

- [Hardware] - Tuya TS0202 PIR Motion Sensor
- [Technical] - Revert changes for reverse-proxy of WebUI on /zigate

## 27 August 2021 - 5.1.07

- [Hardware] - Compatible with ZiGate-Ethernet
- [Hardware] - Fix potential issue with ZiGateWifi
- [Technical] - Speed up the launch of plugin WebUI
- [Hardware] - Certified SonOff TH01 Temp+Humi sensor
- [Technical] - Support up coming Firmware 320
- [Hardware] - Support a new model of CO Heiman Sensor
- [Technical] - get update from pyseria module
- [Technical] - depending on Domoticz version, update immediatly the battery level of all widgets
- [Hardware] - support the Schneider Wiser Thermostat and Thermostat Valve
- [Hardware] - Support Frient Motion sensor
- [Technical] - All setup of Reverse Proxy for the Plugin WebUI
- [Hardware] - Manage Ballast configuration for Legrand Dimmer
- [Technical] Use of logging python module for plugin logs and debug
- [Hardware] New Tuya devices ( Door Sensor, Parkside water timer)
- [Technical] - Move a number of global settings to device specific by using the 'Paramater'

## 23 June 2021   - 5.1.06

- [Technical] - Update of Readme.md to better indicate the way to move from one branch to an other
- [Issue] - ZiGate+ Wifi not starting
- [Hardware] - Tuya DIN Energy counter certfied
- [Hardware] - Tuya/Parkside Smart Water Timer (Lidl), first phase.
- [Hardware] - Gledopto GL-C-007-1ID
- [Hardware] - Tuya Door Sensor TS0203

## 19 June 2021   - 5.1.04

- [Hardware] - Philips Hue Hue White Ambiance GU10
- [Technical] - various fixes

## 31st May 2021  -  5.1.03

- [Technical] - Better management of ZiGate V1 and V2
- [Technical] - Revert Config.Reporting of End Device to a proprer rate

## 26th May 2021  -  5.1.02

- [Technical] - Update the plugin version number
- [Technical] - Enable hw flow control for ZiGate+ ( USB, DIN)

## 24th May 2021  -  5.1.01  (NOT COMPATIBLE with Domoticz 4.xxxx)

- [Hardware] - Update of Danalock configuration
- [Technical] - handling (but not full support) ZiGate+ (V2)
- [Technical] - handling the new OptiPDM firmware for ZiGate
- [Technical] - Handling Extended Error code from NXP stack
- [Hardware] - Partialy support Wiser Thermostat (new generation). Temp and Humi reported. Thermostat setpoint not supported yet.
- [Tool] - Update JennicModuleProgrammer to support Erase EEPROM feature.
- [Hardware] - Support of Tuya SMart Touch 1,2 Gang support
- [Hardware] - Support of Tuya/Moes ZTZ-EU Switch
- [Hardware] - Support TS0042 remote
- [Technical] - Update pyserial embedded module
- [Hardware] - Handle the new Netatmo-Legrand Remote switch with Toggle mode instead of Off/On
- [Hardware] - Manage native Netatmo-Legrand Group Management with Remote Switch
- [Technical] - refactor Network Topology (simply version by default), required siblingDisplay to get full network
- [Hardware] - Integrate Hue Smart Button ( ROM001 )
- [Hardware] - Integrate DYI sensor ( Binary analog cluster)
- [Technical] - Refactor device parameter and make then device specific (instead of global).
- [Hardware] - Integrate Tuya TS0601 Thermostat
- [Technical] - Enable saving plugin databases into Domoticz Database
- [WebAdmin] - Enhancements of the Web User Interface.
- [Hardware] - Add Lora Tap Switch
- [Hardware] - Add Tuya eTRV

#### end of Domoticz 4.xxxx support. For above version it is required to have a minimum of 2020.1

## 23 Feb. 2021   - 4.11.17

- [Hardware] - Module AIr Co CAC221

## 03 Feb. 2021   - 4.11.16

- [Hardware] - Lumi Plug MAEU01
- [Hardware] - Lidl led
- [Hardware] - Update of Danalock configuration

## 19 Jan. 2021   - 4.11.15

- [Hardware] - Add Gledopto GL-C-007 as a RGB W
- [Issue] - Fix Gledopto GL-C-009 definition as a Level Control

## 4 Jan. 2021   - 4.11.14

- [Hardware] - Correct the right widget Color Control Widget fo CLA60 RW OSRAM

## 1 Jan.  2021  - 4.11.13

- [Hardware] - Support Tuya Water leak sensor
- [Hardware] - Support of Legrand Teleruptor
- [Hardware] - Support of Sonoff ZB Mini switch
- [Hardware] - Support Idinio foor dimmer

## 18 Dec. 2020   - 4.11.12

- [Hardware] - New eTRV Tuya
- [Hardware] - Better management of Battery level for SonOff devices ( NX-4911 Manufacturerd by Revolt )
- [Hardware] - Fix some issues related to the FIP mode of Schneider Wiser HACT

## 27 Nov.  2020  - 4.11.11

- [Hardware] - Handle the behaviour of the Legrand shutter when firmware above 0x1a

## 5 Nov.  2020  - 4.11.9

- [Hardware] - Add Heiman RC-EF-3.0 remote.

## 24 Oct.  2020  - 4.11.8

- [Hardware] - ENKI-LEXMAN Bulb ( Leroy Merlin)
- [Hardware] - INNR SP 120 Plug ( Instant Power, Voltage, Current reporting)
- [Hardware] - Schneider 1 Gang Shutter

# 15 Oct.   2020  - 4.11.7

- [Hardware] - Various fixed for Heiman remote device.

## 29 Sept. 2020  - 4.11.2

- [Issue] - Spelling mistake for lumi.sensor_switch label in French
- [Issue] - Comply with Zigbee standard as regards to configure reporting of Data type >= 0x30 ( #697 )
- [Technical] - Re-factor the Read attribute loop in pairingProcess
- [Issue] - fix potential issues of unbound local variables
- [Technical] - add decoding attributes for cluster 0x0204
- [Issue] - fix issue in ReadAttribute preventing to read all attributes, and using manufacture code.
- [Issue] - revert black formatting of Transport
- [Improvement] - send a notification to Domoticz Notification widget when a device announcement is received.

## 27 Sept. 2020  - 4.11.1 (Supporting Firmware 3.1d)

- [Technical] - Implement a full SQN management and Synchro based on firmware 31d
- [Technical] - By default use NOACK ZCL command if response is expected. Other commands are send with ACK
- [Technical] - Bind and ConfigureReporting based on SQN
- [Hardware] - SonOff devicess
- [Technical] - Disable automatic start of Network Topology and Interferences reports
- [Technical] - Follow Device Annoucement protocol (Rejoin)
- [Technical] - Replace RSSI related label to LQI
- [Hardware] - Integrate new Heiman Sensors ( Smoke and CO)
- [Issue] - Fix an issue related to pairing of IAS devices
- [Hardware] - Suport of Wiser Thermostat + HACT + VACT eco-system (simulating Wiser Hub)
- [Hardware] - Support Danalock device
- [Technical] - Support Zigbee Polling Control
- [Technical] - Measure Reacting time and Processing time
- [Hardware] - Support Legrand Manufacturer Specific Cluster 0xfc01 (firm 31d)
- [Technical] - Support the Firm 31d Hybrid mode
- [Technical] - Support sending Read Attribute and Write Attribute in Raw mode
- [Technical] - Full review of use of ACK or not when sending command
- [Technical] - Firm 31d - implement 0x8110 accordingly to the new change
- [Technical] - Implement Multi-Threading capabilities (not enabled on 4.11 )
- [Hardware] - Danfoss eTRV
- [Hardware] - Tuya
- [Hardware] - ZigLight
- [Hardware] - LUMI WXKG06LM and WXKG07LM b186acn02/ b286acn02
- [Technical] - Web UI enhancement ( Bind/Unbind, Enable PowerOn after Off/On)
- [Technical] - Handle for LUMI tag and so decode more informations
- [Hardware] - SmartThings outlet
- [Hardware] - SONOFF Switch
- [Hardware] - Integration of the Heiman Remote Control RC-EM ( firm 31d)
- [Hardware] - Heiman Remote Control RC-EM ( 4 buttons )

## 24 Aug 2020 - 4.9.5

- [Technical] - Don't warn in case of Firmware 31d

## 21 June 2020 - 4.9.4

- [Hardware] - Certified Xiaomi Smart Socket EU Plug ZCZ04LM

## 14 June 2020 - 4.9.3

- [Technical] - Livolo parameter
- [Technical] - Improvement Schneider

## 8 June 2020 - 4.9.2

- [Technical] - Smooth pairing for Schneider devices
- [Issue] - Do not poll battery based devices
- [Issue] - Require plugin restart after enabling Reset Read Attribute or Group Management
- [WebAdmin] - Security fixes

## 5 June 2020 - 4.9.1 (Last release supporting Firmware below 3.1c)

- [Technical] - Ready for PDM on host.
- [Technical] - Scrip for PiZiGate on Fedora distribution
- [Technical] - Provide Firmware
- [WebAdmin] - User Interface Optimisation
- [Hardware] - Support Schneider Wiser Thermostatic Valve
- [Technical] - Allo device to device bindings via Web Admin Interface
- [Technical] - Revise Strategy for OTA device firmware update. Provides only way to retreive/pull the firmware
- [Technical] - Handle OTA Firmware update for LEDVANCE, Philips, Legrand ( would require 3.1d Zigate)
- [Technical] - Log mecanishm for the plugin (all Logs save under Logs folder)
- [Technical] - Refactor a number of Modules
- [Hardware] - Provides a number of additionnal Devices
- [Hardware] - Implementation of BSO profalux
- [WebAdmin] - Update Translation for French and Dutch
- [Technical] - Implement a Reset after delay of the Switch Selector (push button)
- [Hardware] - Support of Schneider sWiser, HACT and Thermostat.
- [WebAdmin] - Debug menu move to Tools
- [WebAdmin] - Allow to enable pairing on one specific router
- [Technical] - Full rework/refactor of Group Management. Allow real time Group creation/edition/removal

## 22 February 2020 - 4.7.5

- [Hardware] - More Device Configuration

## 18 February 2020 - 4.7.4

- [Hardware] - Update a number of device configuration

## 14 February 2020 - 4.7.3

- [Issue] - Fix issue when Window Covering device exist
- [Issue] - Re-enable configureReporting split Atrribute by attribute
- [Issue] - Check the validity of Temp and Humidity

## 12 February 2020 - 4.7.1

- [Issue] - Using wrong ClusterId for 0201 read attribute
- [Issue] - Fixing binding information

## 8 February 2020 - 4.7.0

- [Hardware] - Update of IKEA Tradfri firmware
- [Technical] - better management of APS Failure, network transmission
- [Technical] - speedup the process to get Powered Devices with a correct Health state
- [Technical] - Consider Health 'Non rechable' as a dead device, and do not process them anymore.
- [Technical] - Implement the possibility to setup the PowerOn after device PowerOff/Off (supported by Philips)
- [Technical] - Handle ZHA1.2/Pluzzy Firmware
- [Technical] - Handle Pluzzy devices - Temp/Humi is working for now.
- [Technical] - Transfert of GitHub repository
- [Hardware] - Certify Tuya Door contact
- [Hardware] - Certify Konke KIT Pro ( Multi Function switch, Door contact, Temp/Humi Sensor, Motion sensor)
- [Technical] - New way to restart plugin.
- [Hardware] - BITRON Home devices ( Door sensor )
- [Hardware] - BITRON Home devices ( Motion sensor )
- [Hardware] - BITRON Home devices ( Plug )
- [Hardware] - Centralite Door Sensor
- [Hardware] - Zemismart Blind and Shade. New way of handling widget creation (used ProfileID/DeviceID)
- [Technical] - Using command 0x47 to remove device
- [Hardware] - Livolo Switch
- [Hardware] - Manage Legrand devices. Use Legrand cluster to enable features.
- [Web Admin] - Possibility to delete unconsitent devices ( in Device Management)
- [Web Admin] - On demand command (adHoc) offer the possibility to send Zigate command to paired devices
- [Hardware] - INNR RC 110 remote command - Phase 2 ( widget creations for Scenes and Lights mode.
- [Technical] - Allo input of port number of Web Admin, will allow multiple zigate on 1 Domoticz instance
- [Hardware] - Tuya Temp/Humidity sensor
- [Technical] - Force polling after a Group update
- [Technical] - Improve group scan when Adding/Updating/Removing a group device
- [Technical] - Report Battery voltage if any to Voltage widget
- [Hardware] - TRADFRI bulb E27 WW clear 250lm
- [Technical] - Reduce priority of Topology and Energy scanner
- [Technical] - Speedup the Xiaomi pairing/provisioing process
- [Technical] - Able to set PowerOn after a powerOff ( 0 for Off, 1 for On, 255, for previous state), Works for devices able to handle it. (Legrand, Philips)
- [Technical] - Friendly Provisionning
- [Technical] - Management of Zigate Blue Led. No need to restart plugin. Action taken immediatly from settings
- [Technical] - Implement pingDevice policy (parameters pingDevices, pingDevicesFeq) . Ping every 3600s and once at plugin startup. The ping is much lighter than using the polling
- [Technical] - Implement a way to force device status after command initiated. ( forcePollingAfterAction )
- [Technical] - New way to manage Certified devices and make custom way to Bind and configure reporting
- [Technical] - When Device in Left status, then Timeout
- [Hardware] - LEDVANCE SMART+ INDOOR PLUG
- [Hardware] - Schneider Wiser S-Meter, Plug, Actionneur
- [Technical] - Split code and extract Legrand and Schneider to dedicate module
- [Technical] - Makes configure reporting (with multiple attribute)
- [Technical] - Manage Meter when not Current Summation, and makes Current Summation works for Salus, Legrand
- [Technical] - Refactor the way Device configrations are managed, and dedicate one json per Model
- [Technical] - Introduce ClusterToBind, ConfigureReportig and ReadAttributes pragma to configuration model
- [Technical] - Fully compliant with firmware 3.1c

## 31 July 2019  - 4.5.0 ( Web User Interface ) <https://github.com/sasu-drooz/Domoticz-Zigate/releases/tag/4.5.0>

- [Technical] - Web Server Class
- [Technical] - New way of managing PluginConf/Parameters, in order to be managed from UI.
- [Technical] - Full re-factory of Network Toplogy scanner
- [Technical] - Full re-factory of Network Energy Level scanner
- [technical] - Topology and Energy Level scan are now automaticlay started a launch of plugn + 120s, and then will be trogger manually by Web Interface
- [Technical] - enable live debug switch (with nwkid filtering) from the Web Admin Interface
- [Technical] - Refactor the Read Attribute mechanism. Enable Polling parameters for ON/OFF and LvlControl from the User Interface or Configuration file
- [Technical] - Implement ReJoin capabilities. When a device is sending a un-expected Leave (not following a remove).
- [Technical] - Refactor logFORMAT
- [Hardware] - Certify WXKG11LM (up to 4 clicks), Warning Device HEIMAN
- [Technical] - Refactor the PiZigate setup
- [Technical] - Tools to get PiZigate running on Fedora distribution
- [Technical] - Plugin version and Firmware Version check. Will required Internet access (which is currently enable by default in PluginConf)
- [Technical] - Allow debug Match with several device address
- [Technical] - decode more Attribute for Cluster 0x0006
- [Hardware] - Support of INNR RC110 remote command (required 3.1a firmware) - Phase 1
- [Technical] - Admin Interface in French ( Thanks to @martial83 )
- [Technical] - Admin Interface in Dutch ( Thanks to @gemies )
- [Hardware] - Certified Müller-Licht 44062 Bulb
- [Hardware] - Certified Philips LTW013 bulb
- [Hardware) - Make the Ikea Tradfri Switch ( On/Off ) capable to send multiple On
- [Hardware] - Certified CC2531 (lumi.router ) router
- [Technical] - Introduce auto-check of firmware/plugin version
- [Technical] - Enhance piZigate support
- [Technical] - Full compliance with firmware 3.1a

## 27 May 2019 - 4.3.0 <https://github.com/sasu-drooz/Domoticz-Zigate/releases/tag/4.3.0>

- [Enhancement] #419 Better versioning of DeviceList (restricted to 12 versions by default)
- [Hardware] #421 - Integrate the new Aqara switch with gyroscope
- [Hardware] - Add group management (cluster 0x0004) to Aqara Switch with Neutral
- [Hardware] - Add Aqara Switch with Neutral (one button)
- [Technical] - Make a configure reporting on Main powered devices on a daily basis
- [Technical] - Ping enhacement
- [Hardware] - Xiaomi relay ( lumi.relay.c3acn01 )
- [Technical] - Simplify ConfigureReporting
- [Technical] - Do ReadAttributes only for supported attributes.
- [Hardware] - Xiaomi Aqara Switch ( lumi.ctrl_86plug.aq1)
- [Technical] - Fancy log of Cluster during inclusion of new device
- [Technical] - History of DeviceList limited to 12 version by default
- [Issue] - Fix an issue with lumi.ctrl_neutral1
- [Hardware] - Make the Ikea ON/OFF switch able to send multiple Off/On, require a new pairing
- [Technical] - Better presentation of Cluster when doing a pairing
- [Technical] - Do ConfigureReporting on daily basis
- [Technical] - use the result of Attribute List from the end device
- [Technical] - Fix issue in Topology/LQI report
- [Technical] - Create a Report folder to store reporting ( LQI, Nwk Interference) reports.
- [Technical] - APS Failure management + reporting

## 19 May 2019 - 4.2.3 <https://github.com/sasu-drooz/Domoticz-Zigate/releases/tag/4.2.3>

- [Issue] Wrong battery calculation for Xiaomi devices.

## 05 May 2019 - 4.2.2

- [Issue] Fix a problem when creating a device and there is no Model associated.

## 30 April 2019 - 4.2.1

- [Technical] Disable APS failure reporting. If still want to use it, you can enable it enableAPSFailurereporting in PluginConf.txt

## 24 April 2019 - 4.2.0 <https://github.com/sasu-drooz/Domoticz-Zigate/releases/tag/4.2>

- [Enhancement] Over-The-Air firmware upgrade of main powered Ikea/Tradfri devices (so far only firmware publicaly available)
- [Enhancement] In case of communication failure between Zigate -> Device, triggering TimeOut flag on Domoticz Device widget.
- [Enhancement] Update device only in case of batterly level changes and not SignalLevel in order to reduce the notification system.
- [Technical] Start using 0x8702 messages
- [Hardware] #392 - Handle long press release on Aqara remote switch (Small square one with one round button)
- [Technical] 0xffff reserved short address
- [Technical] refactor ZigateRead code.
- [Technical] Add few more attributes for cluster 0x0000 (read attribute)
- [Enhacement] Allow Domoticz device update for Motion sensor if motion is detected.
- [Issue] Correct Group Level calculation for shutter/blinds
- [Issue] #383 - fixing and allowing index on one digit.
- [Issue] #384 - Handling 0xff02 Xiaomi attribute for cluster 0x0000 and decoding what is inside.
- [Technical] Refactor readClusters dispatch
- [Technical] New parameter Extended PANID . After an Erase PDM, the Zigate can start on a specific Extended PANID
- [Issue] #402 - Transport resilience, make sure that \_sendData is processing only Hexa Bytes.
- [Issue] #408 - If the Domoticz version is not at the right level, still update lastseen information in Plugin Database.
- [Issue] #410 - Transport resilience, make sure that we get at least 6 bytes when processing an incoming message.
- [Hardware] #406 - add Xiaomi lumi.ctrl_ln2.aq1
- [Issue] #405 - On a long run it might happen that device git a new ShortId, in such case, the Group table must be updated consequently.
- [Technical] - Review the Debuging mode at plugin start, so they are only relevant.
- [Technical] - Review and improve APS Data Failure handling (Decode8702).
- [Hardware] - Ikea Tradfri remote Switch On/Off
- [Hardware] - Ikea Tradfri Motion sensor
- [Technical] - Fix several issues in group Management, when you trigger a full group scan and some devices have been removed .
- [Issue] #318 - Use Model name or Nickname when creating a Domoticz widget.
- [Hardware] - Handle lumi.ctrl_neutral1 / QBKG04LM device
- [Issue] #414 - Plugin will switch GPIO to RUN mode at plugin start

## 05 April 2019 - 4.1.4 <https://github.com/sasu-drooz/Domoticz-Zigate/releases/tag/4.1.4>

- [Issue] #395 - PI doesn't stay as Model .

## 04 April 2019 - 4.1.3

- [Issue] Strange error in heartbeat self.self ...

## 30 Mars 2019 - 4.1.2

- [Issue] #390 and #389 - Integrate those 2 Pull Requests

## Mars 2019 - 4.1.1

- [Issue] #383 - fixing and allowing index on one digit.
- [Issue] #384 - Handling 0xff02 Xiaomi attribute for cluster 0x0000 and decoding what is inside.

## 12 Mars 2019 - 4.1.0 <https://github.com/sasu-drooz/Domoticz-Zigate/releases/tag/4.1.0>

- [Technical] Full refactor of Discovery and Enrolement process
- [Issue] Make the possibility to use a PluginConf per HardwareID #271
- [Issue] Make Motion Resetdevice customizable via a PluginConf parameter #270
- [Enhancement] Add Clock and Anti-clokc rotation tabs for XCube. This will require a remove and re-inclusion of the device #282, #281
- [Enhancement] Discover group membership from each main powered devices which also have cluster 0x0004
- [Hardware] NEXBANG Wireless Door Windows sensor Alarm Home WIFI Security Door (#287)
- [Hardware] ZIPATO smoke detector
- [Hardware] IAS Zone enrollement
- [Enhacement] Group Management (auto-discovery of existing group set via remote controller)
- [Enhacement] Zigate Status Widget (Measure section) ( Ready, Enrollement, Busy )
- [Technical] At startup when loading the ListOfDevice, do not load UNKNOW devices.
- [Enhacement] Zigate Notification Widget (measures section) to display plugin notification
- [Technical] Configurable plugin folders ( Data, Zdata, reports, www/templates )
- [Technical] Configure by default the ZigBee Channels (recommended for Europe
- [Hardware] Improve 2018 Xiaomi wireless sitches with 3 states per button ( lumi.remote.b286acn01, lumi.remote.b186acn01)
- [Technical] Remove the use of random
- [Technical] Ping <-> Zigate. In case of connectivity failure, reConnect
- [Technical] re-factor the ReadAttributes request in Hearbeat in order to avoid peak of load.
- [Technical] Restructure python modules and classes, in order to have a much cleaner plugin home directory
- [Technical] re-factor the ConfigureReporting in order to avoid peak of laod
- [Technical] Profile the possibility to configure the location of Data, Config and Report files. See PluginConf Documentation on Wiki
- [Hardware] Implementation of Thermostat in order to handle Eurotronic Spirit Zigbee ( Temp sensor, Setpoint )
- [Enhacement] Aqara Cube will get 2 Widgets , one Switch selector and one Text widget. The Text widget will get the Cube rotation Angle notification.
- [Enhacement] Aqara Cube improvement in terms of responsivness
- [Technical] Implement TX Power feature from firmware 3.0f.
- [Technical] Implement the possibility to switch off the Blue led from firmware 3.0f.
- [Hardware] Manage IKEA Tradfri Remote controller. Create a selector switch for the device and then capture remote event (if Zigate associated to the group)
- [Technical] Move config file to Conf directory
- [Technical] Live data as DeviceList and GroupList will be in Data folder
- [Enhacement] Workaround the domoticz issue as regards to Temperature and Baro sensor adjustement and make it happen (only for Domoticz version > 10355)
- [Issue] - #348 Status of Tradfri/Hue bulbs after Main power Off/on
- [Technical] - Allow the possibility to set the Certification compliance between CE and FCC
- [Issue] - #275 User Domoticz Accept New Hardware to set Zigate in Permit to join or not (only for Domoticz version > 10355)
- [Technical] - Make DeviceConf json compliant
- [Hardware] - Accept Philips Motion sensor (indoor and outdoor models)
- [Technical] - Make 4.1 compatible with Stable 4.9700 and Beta > 10355. This makes 4.9700 got some limitations. ( No Temp/Baro adjustement, old fashon Permit To Join)
- [Enhacement] - Use the Domoticz device Off Delay for motion sensor.
- [Enhacement] - Allow from the plugin menu to force a Group scan/discovery
- [Enhacement] - Disable by default the polling information. You need to set enableReadAttributes to 1 in PluginConf.txt to for the polling.
- [Technical] - Rename forceReadAttributes and forceConfigureReporting into resetReadAttributes and resetConfigureReporting
- [Hardware] - Certify the OSRAM SMart Plug device
- [Hardware] - Able to recognize Livolo double switch and be able to command it. (more test to be done on the state reporting). Also firmware must handle the Livolo Zigbee implementation to get stability.
- [Hardware] - Implementation of Legrand shutter/Window covering. ( On and Off command works).
- [Technical] - Lux calculation for non-Xiaomi devices.
- [Technical] - Transport statistics are now stored on a reporting file, for further analysis.
- [Technical] - When groups are ready report into GroupList-xx.json
- [Technical] - if allowed rebind_clusters when receiving a Device Annoucement
- [Technical] - #347 If you add the Tradfri remote 5 buttons (which was previously paired with Touchlink) to the group, the Left and Right buttons will then be activated.
- [Technical] - Use the new Domoticz API requested by us, to update on every incoming message the Device Last Seen in Domoticz.
- [Technical] - Reduce the LastSeen update to every 5' in order to avoid too much load on the IO

## 14 January 2019 - Version 4.0.7

- [Issue] Fix #322 / Power/Meter reporting not working for Xiaomi Smart Plug

## 03 January 2019 - Version 4.0.6

- [Isssue] Remove usage of random

## 27 December 2018 - Version 4.0.5

- [Issue] Negative temperature not correctly reported for Xiaomi Sensor

## 15 December 2018 - Version 4.0.4

- [Issue] #291 , wrong decoding of Cluster Out frame in 0x8043

## 13 December 2018 - Version 4.0.3

- [Hardware] Handle new Aqara switches WXKG03LM and WXKG02LM

## 09 December 2018 - Version 4.0.2

- [Issue] #278 , make the plugin windows compatible
- [Issue] #279 , test if ZDeviceID before trying o convert it to an int

## 08 December 2018 - Version 4.0.1

- [Issue] #272
- [Issue] Correct the Selector tab label for the Double Button swicth
- [Issue] When receiving a leave message , if the object is not 'removed' then request a rejoin

## 02 Decembre 2018 - Version 4.0.0 <https://github.com/sasu-drooz/Domoticz-Zigate/releases/tag/4.0.0>

- [Technical] New Zigate Transport layer  ( ZigBee compliant with retransmission in case of missing data, bit also a agressive algorithm.)
- [Technical] Creation of PluginConf class to manage the PluginConf.txt file
- [Technical] Refactor the inclusion/discovery and domoticz widget creation
- [Enhancement] Automaticaly handle Bulbe ColorMode in order to create the corresponding Widget WW, RGB or LED
- [Technical] Manage ConfigureReporting and ReadAttributes errors in the way that we do not ask anymore.
- [Hardware] Salus SP600 plug (power reporting will required a firmware update of Zigate)
- [Hardware] WXKG03LM Aqara wireles switch single button (using Cluster 0x0012)
- [Enhancement] Improve stats report at plugin exit
- [Hardware] Adding more IKEA Tradfri bulbes
- [Enhancement] Adding one more parameter in DeviceConf 'ColorMode' to define the type of Bulbe colormode.
- [Enhancement] When commissioning is over and the Domoticz device is created, ZLL device will blink
- [Issue] In case the Domoticz widget creation failed, plugin test the return of the Create() and in case of error report in the log
- [Issue] Fix some potential problem when receiveing and empty EP
- [Issue] Fix a potential issue when requetsing a Configure reporting on an non-ready cluster
- [Enhancement] Introducing a PluginConf parameter for tracking readCluster incoming message
- [Technical] reducing log level, and reducing Debug level
- [Enhancement] Elaborate the correct Color widget based on Color Mode and ProfileID/ZDeviceID
- [Technical] Filtering out Commissiong ProfileID/ZDeviceID
- [Hardware] Certification (@d2e2n2o) of XCube, lumi.sensor_switch.aq2, lumi.sensor_86sw1, lumi.sensor_86sw2, lumi.ctrl_ln2, TRADFRI bulb E27 WS opal 950lm, TRADFRI control outlet
- [Technical] Set the frequency of Network test to hourly
- [Enhancement] When stoping the Plugin , Transmission statistics will be print out
- [Technical] Introduce a Constants file.
- [Enhancement] #266 send identify message when completing the commissioning and get devices created.
- [Enhancement] Get async status of switches and plug
- [Enhancement] Get async Level of Level Control devices
- [Technical] Use IEEE instead of Network addresses in Domoticz
- [Technical] Don't store any plugin informations in Domoticz. All plugin infos are now in DeviceList
- [Issues] Able to manage 2 Zigates on the same Domoticz instance. The DeviceList file will be identified by the HardwareID (plugin instance in Domoticz)
- [Technical] Decode Device node descriptors information like Manufacturer, Power Source, Response When Idle ....
- [Technical] Manage Leave message from device
- [Hardware] Aqara Wall Switch LN (Double) Aqara 230 double switch, double fire switch (QBKG12LM))
- [Hardware] Aqara Motion sensor / Vibration sensor
- [Technical] Network Topology report based on LQI request.
- [Technical] Better management of Temp/Hum/Baro sensor with very basic forcast and Air quality
- [Technical] Randomize the time when Read Attribute Req will be sent. This will distribute the load of those recurring tasks.
- [Technical] Implementation of Configure Reporting
- [Technical] Implementation of bind and unbind commands ( needed for Configure reporting)
- [Enhancement] Configure Reporting enabled by default on Clsuter 0x0006 , 0x0008, 0x0702
- [Technical] Implementation of Send Signal to get the Device visible. (if available)
- [Enhancement] Implement Software Reset of Zigate - Called at startup if enable in the Plugin menu
- [Hardware] Xiaomi Plug - enabling power and meter reporting
- [Technical] control of Command versus status response
- [Technical] control of SQN on messages from battery powered devices. In case of out of sequence a message is logged
- [Technical] improving loading of Domoticz devices into self.ListOfDevices
- [Technical] implementing DomoID to track the deviceID at creation time (which is the reference in Domoticz DB. This is in planning of managing devices coming with a new saddr
- [Issue] fix problem created during #78
- [Hardware] enable plug-switch update when receiving 0x000/ff01 cluster
- [Technical] Upgrade to Zigate V2 data structure and store in domoticz.db ( would required latest Domoticz Beta version to work )
- [Technical] Change TypeName to ClusterType in the Zigate structure.
- [Technical] Serialisation of zigate cmd based on sendDelay paramater available on PluinConf.txt - set by default to 1s
- [Technical] Remove unecessary charaters sent in case of Wifi transport
- [Technical] Enable/Disable login Discovery Process information. The purpose is to keep in a dedicated file all informations captures during the discovery phase. This will allow us to work on new -un certified - devices.
- [Issue] - Handle Leave message
- [Issue] - When you remove a device in Domoticz, we remove the entry in the Plugin, but we don't remove the device in Zigate, yet.

## 12 September 2018 - 3.0.0 <https://github.com/sasu-drooz/Domoticz-Zigate/releases/tag/3.0.0>

Mainly a technical version in order to split the code in pieces.

- Code split
- Bug fixing

## 8 September 2018 - 2.4.0 <https://github.com/sasu-drooz/Domoticz-Zigate/releases/tag/2.4.0>

Thanks to : zaraki673, pipiche38, badz, smanar, thiklop, dennoo, lboue, cldfr, sbhc68
