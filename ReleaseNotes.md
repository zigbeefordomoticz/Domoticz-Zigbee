# Release Notes 
## xx November 2018 - beta-3.3
- [Technical] New Zigate Transport layer  ( ZigBee compliant with retransmission in case of missing data, bit also a agressive algorithm.)
- [Technical] Creation of PluginConf class to manage the PluginConf.txt file

## xx November  2018 - beta-3.2
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
- [Enhacement] Configure Reporting enabled by default on Clsuter 0x0006 , 0x0008, 0x0702
- [Technical] Implementation of Send Signal to get the Device visible. (if available)
- [Enhacement] Implement Software Reset of Zigate - Called at startup if enable in the Plugin menu

## xx mmmmmmmm  2018 - beta-3.1.0

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



## 12 September 2018 - 3.0.0 
Mainly a technical version in order to split the code in pieces.

- Code split
- Bug fixing


## 8 September 2018 - 2.4.0
We are keen to release this version off the Zigate Plugin, which include a set of update, enhacement and bugfixing.

- Configuration file to enable further configuration parameters
- New data capture from the zigate hardware. It involved also on the fly lenght and checksum validation, in order to ensure proper data transmitted to the plugin feature.
- Reporting device signal quality to Domoticz through RSSI.
- Reporting in the log at plugin start, the Zigate firmware version. We recommend using 03.0d
- Reporting in the log at plugin start and if the firmware version is greater than 03.0b
- We have onboarded a number of new devices ( Xcube Aqara,  TRADFRI LED LED1624G9, ...) all of them are now documented in a file name : Compatible-Hardware.md . Feel free to let us know if you are using a device not listed there and working properly.
- Implementation of polling of Profalux shutter state, in order to update Domoticz devices in case of direct radio-command
- a number of bug fixes.

Please feel free to report issue through github: https://github.com/sasu-drooz/Domoticz-Zigate/issues
And if you have any questions, problem please use first the Domoticz forum.
- French channel : https://easydomoticz.com/forum/viewtopic.php?f=8&t=7099
- English channel : https://www.domoticz.com/forum/viewtopic.php?f=28&t=24789

If you want to contribue , please let us know , we are looking for help in various areas:
- certifying new ZigBee devices
- improving the plugin
- increasing the level of documentation for end user

Thanks to : zaraki673, pipiche38, smanar, thiklop, dennoo, lboue, cldfr, sbhc68 
