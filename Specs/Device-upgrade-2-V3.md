# Upgrade of Device Structure to V3

## Purpose

Purpose is mainly to shift from storing sAddr in Domoticz DeviceID to IEEE, in order to have a uniq reference.
In order to keep the mapping between IEEE and the sAddr which is used for communication with the Zigate, we will store the sAddr the Zigate field under the entry DomoID


## Upgrade mechanism

While the Domoticz database can be updated through .Update() call, there is no possibility to update DeviceID. A Pull Request has been submitted , but it looks that the Domoticz owner @gizmocuz is not willing to release it.

The suggested alternative is then :
* for oldDeviceID in Devices :
  * Create a new Device and use IEEE has the DeviceID
  * Rename the old Device by changing the name into 'V2 <prev name>'

* Impacts
  * lost of historical data for all devices. In order to compensate the oldDevice is not removed and it will be the responsability of the user to remove (or not) those oldDevices.

## Implementations

* As the IEEE will be used only to interact with the Domoticz Database, the changes will be limited to the domoticz database interactions.

  * plugin.py
    * Initialisation of ListOfDevices {} structure. At loading time, the entry key must be initialised with Options.Zigate.DomoID -instead of DeviceID -

  * z_database.py

| function | description |
| -------- | ----------- |
| loadLOD( self, Devices ) | Load the Domoticz Devices into ListOfDevices |

  * z_domoticz.py
    * CreateDomoDevice()
    * MajDomoDevice()
    * UpdateDevice(): prior calling .Update() retreive sAddr from DomoID

  * z_tools.py
    * initDeviceInList
      * From V2 to V3
