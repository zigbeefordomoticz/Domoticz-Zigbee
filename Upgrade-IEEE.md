# Upgrade IEEE ( upgrade de la base Domoticz et de la base Plugin Zigate 

## Introduction
The purpose of this upgrade is to comply with the Domoticz database and to get all Zigate plugin related information inside the plugin Database ( DeviceList.txt )

## Upgrade steps

1. Stop domoticz ( e.g. sudo service domoticz stop )
1. Do a proper backup of domoticz.db and DeviceList.txt , so you are safe to go backward in case of issue

1. Make sure that you are on the latest plugin version
``` git checkout dev-IEEE ```
1. Edit the file Tools/UprageDB-2-IEEE.py in order to reference the right DB and file
   * Update DomoDB parameter => put the Full path to the sqlite domoticz database
   * Update PluginHomeDirectory => put the full path to the plugin ( .../plugin/Domoticz-Zigate/

1. You are ready to start the upgrade

```  python3 Tools/UpgradeDB-2-IEEE.py ```

## Starting now :
* There is no more Zigate information in the Domoticz database. The file DeviceList is becoming curcial to your system.
* You can also observe in the List of Devices (on the Domoticz Dashboard ) that all Zigate devices have now a new DeviceID instead of a previously 4 digits code. That is refered as the IEEE or Mac address
* DevciceList.txt has been renamed into DeviceList-#.txt . This digit corresponds to the HardwareID of the Zigate plugin instance. In case your run 2 instances of the plugin (because 2 USB Sigate), then you will have 2 DeviceList-#.txt : one for each.

