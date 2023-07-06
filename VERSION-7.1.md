# Zigbee for Domoticz Version 7.1

## Objective

The purpose is to document key features of plugin version 7.1 and also the requirements to move to that version.
Because 7.1 requires a minimum version of python3, you won't have any automatic update from the latest 6.3 version, but you'll required to have an active action to upgrade.

## IMPORTANT

Once move to 7.1, you cannot fall back to a previous version. If you still need to do, you have to use your backup, and restore Domoticz and the Plugin environment

## Pre-requisities

Python3.8 is required to run the plugin in version 7.1.
In case you are still on a PI with Buster, this is not compatible and you must move first to Bullseye prior planning to upgrade the plugin to 7.1

## How-to upgrade to 7.1

1. Make the necessary backup before doing any update. This could save you a lot of time, headaches.

   * To backup the plugin refer to the [wiki](https://github.com/zigbeefordomoticz/wiki/blob/master/en-eng/Plugin_Backup.md), and don't forget that you should backup Domoticz and the plugin in the same time window to prevent any miss-match.

1. Make sure you run python3.8 or above. If you are on buster, you have to upgrade to Bullseye first

    `python3 --version`

1. Update the the repository, and switch to stable7
    from the plugin home directory `plugins/Domoticz-Zigbee`

    ```bash
    git pull
    git checkout stable7
    git pull
    ```

    you might have to use `sudo`in order to execure the above commands with the root privileges.

1. Install and update the required python3 modules

    from the plugin home directory `plugins/Domoticz-Zigbee`

    ```bash
    sudo python3 -m pip install -r requirements.txt --upgrade
    ```

    * `sudo` is required as usally domoticz runs under root user

## Features

* Around of 500 devices certified with the plugin. This means that we have a dedicated configuration file for each of them, so their integration is optimized. However the plugin is capable to manage any Zigbee 3.0 which comply with the standard without any specific configuration file.
* Use of latest zigpy radio libraries
* split between Device configuration files and plugin core engine. The certified devices are know handle on [z4d-certified-devices repository](https://github.com/zigbeefordomoticz/z4d-certified-devices)
* More open way to configure/integrate non-standard Zigbee devices, [how-to](https://zigbeefordomoticz.github.io/wiki/en-eng/HowTo_Device-Customization.html).
