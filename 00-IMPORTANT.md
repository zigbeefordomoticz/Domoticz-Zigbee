# IMPORTANT - 

## New Directory Structutre
after the update , you have a new directory structure 
https://github.com/sasu-drooz/Domoticz-Zigate/wiki/Plugin-directory-structure :

 - Classes     
 - Conf
 - Data
 - images
 - Modules
 - Tools
 - www
 - Zdatas

* you MUST move your plugin database ( file DeviceList-xx.txt ) to the Data directory, otherwise when you'll start the plugin it will start with an empty plugin database
* if you want to ustomize the PluginConf.txt, it is now available on Conf/PluginConf.txt. We also recommend to avoid any further overwrite to create a PluginCon-xx.txt (where xx is equal to the same number as DeviceList-xx.txt )
* The ZigateGroupsConfig-xx.txt or ZigateGroupsConfig.txt you might have created MUST be move to Conf

## Group Management
If you plan to use Group Management, you MUST have flashed the latest Zigate firmware 3.0f
