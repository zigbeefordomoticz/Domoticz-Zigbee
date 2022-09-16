# Zigbee for Domoticz Version 6.3


## Objective

The purpose is to document some of the features  of the plugin version 6.3
We will also document some pre-requisites


## Pre-requisities

In order to have a smooth transition when moving to version 6.3 and where there is no data migration, it would be good to take the following steps:

1. If you are running 6.1.5 , you can use the Plugin Update menu from the plugin Web interface ( Admin > Plugin ).
1. Stop the plugin by disabling from the Hardware Domoticz plugin list ( use the enable/disable button and press update).
2. Stop Domoticz as you will have to restart it in order to load a new plugin configuration item .
3. if you are not on 6.1.5 and you didn't use the WebAdmin Plugin Update menu, do the following
   1. `cd Domoticz-Zigbee` (or Domoticz-Zigate for the old installation)
   2. `git config --add submodule.recurse true`
   3. `git pull --recurse-submodules`    ( you might have to use the sudo command if you get access right issues)
   4. `sudo python3 -m pip --no-input install -r requirements.txt`
4. Restart Domoticz
5. Go to the Hardware menu , and select the ZigbeeforDomoticz plugin.
   1. Check that the __API bas url__ is correctly setup.
6. Enable the Plugin in order to start it.
7. Check Domoticz logs for any errors 
8. Check Plugin logs ( Domoticz-Zigbee/Logs/PluginZigbee_xx.log )


## Features

Most of the features added to the plugin are in relation with Texas Instrument deConz and Silicon Labs based Coordinators. The main reason is that we have access to latest firmwares on those coordinators, while it is not the case with ZiGate for which we are also suffering from bugs.


### Automatic Backup

At every plugin start, every plugin shutdown and on a regular time, the plugin create a coordinator backup, which can be restore  on any coordinators (except ZiGate).
The backup is save in a simple text file under the Data folder with a name "Coordinator-07.backup". Every time a new backup is done, a copy is created so we keep an historical list of backups.

### Network Topology ( TopologyV2 )

Starting this version the Network Topology is created by using the Routing Tables and the Neigbourgh tables, while it was based only on the Neighbourg tables. 
This feature is only available on Texas Instrument, deConz, Silicon Labs based coordinator, as there is a bug in the 321 Zigate firmware which prevent to access Routing Table

In case you are a ZiGate user and when requesting a Topology Report you don't get any result. Check the advanced settings and make sure that 'TopologyV2' is disable.


### Configure Reporting edition

Configure Reporting is a special Zigbee feature which allows to configure when, with which frequency, with which change sensor informations can be reported.
From the WebUI > Tools > Configure Reporting you will be able to edit/change the Configure Reporting settings like :
* Min ( the minimum time laps between 2 reports )
* Max ( the maximum time laps whithout any report )
* Change ( the minimum value change to trigger a report)

### Reverse proxy compatibility with Plugin WebUi

We have made the plugin and especially the WebUI compatible with reverse proxy. You can find several exemple in the wiki, on how to set it up.
* [Reverse Proxy with Apache 2](https://github.com/zigbeefordomoticz/wiki/blob/master/en-eng/How-To-Reverse-Proxy-with-Apache2.md)
* [Reverse Proxy with Caddy](https://github.com/zigbeefordomoticz/wiki/blob/master/en-eng/How-To-Reverse-Proxy-with-Caddy.md)
* [Reverse Proxy with Nginx](https://github.com/zigbeefordomoticz/wiki/blob/master/fr-fr/Tuto_Mettre-une-authentification-sur-interface-web.md)
