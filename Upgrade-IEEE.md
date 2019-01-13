# Upgrade IEEE ( upgrade de la base Domoticz et de la base Plugin Zigate  )

## Introduction
The purpose of this upgrade is to comply with the Domoticz database and to get all Zigate plugin related information inside the plugin Database ( DeviceList.txt )

## Upgrade steps

1. Stop domoticz ( e.g. sudo service domoticz stop )
1. Do a proper backup of domoticz.db and DeviceList.txt , so you are safe to go backward in case of issue

1. Make sure that you are on the latest plugin version
``` git checkout stable ```
1. Edit the file ```Tools/UprageDB-2-IEEE.py``` in order to reference the right DB and file
   * Update DomoDB parameter => put the Full path to the sqlite domoticz database
   * Update PluginHomeDirectory => put the full path to the plugin ( .../plugin/Domoticz-Zigate/

1. You are ready to start the upgrade

```python3 Tools/UpgradeDB-2-IEEE.py ```

1. Take attention to any error messages during that stage.
   * Here are the potential error messages : 
   1. ```----===>Cannot migrate this Domoticz DB device, you'll have to remove from Domotciz ```
      * This entry doesn't have an IEEE address ( a physical address) . This is somehow suspcious
   1. ```---===> This DeviceList entry doesn't have an IEEE  ```
      * This entry doesn't have an IEEE address ( a physical address) . This is somehow suspcious
   1. ```---===> This DeviceList entry doesn't match IEEE ```
      * We didn't find any matching Devices in the Domoticz Database. In such there is adisconnect between DeviceList.txt and Domoticz Devices. 


1. You can now restart Domoticz
```sudo service domoticz restart```

1. Please cross check Domoticz Logs in order to validate that every is running fine.

## Starting now :
* There is no more Zigate information in the Domoticz database. The file DeviceList is becoming curcial to your system.
* You can also observe in the List of Devices (on the Domoticz Dashboard ) that all Zigate devices have now a new DeviceID instead of a previously 4 digits code. That is refered as the IEEE or Mac address
* DevciceList.txt has been renamed into DeviceList-#.txt . This digit corresponds to the HardwareID of the Zigate plugin instance. In case your run 2 instances of the plugin (because 2 USB Sigate), then you will have 2 DeviceList-#.txt : one for each.

