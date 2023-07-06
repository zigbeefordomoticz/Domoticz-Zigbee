# Zigbee for Domoticz Version 7.1

## Objective

The purpose is to document key features of plugin version 7.1 and also the requirements to move to that version.
Because 7.1 requires a minimum version of python3, you won't have any automatic update from the latest 6.3 version, but you'll required to have an active action to upgrade.

## Pre-requisities

Python3.8 is required to run the plugin in version 7.1.
In case you are still on a PI with Buster, this is not compatible and you must move first to Bullseye prior planning to upgrade the plugin to 7.1

## How-to upgrade to 7.1

1. Make sure you run python3.8 or above. If you are on buster, you have to upgrade to Bullseye first

    `python3 --version`

1. Update the the repository, and switch to stable7
    from the plugin home directory `plugins/Domoticz-Zigbee`

    ```bash
    git pull
    git checkout stable7
    git pull
    ```

1. Install and update the required python3 modules

    from the plugin home directory `plugins/Domoticz-Zigbee`

    ```bash
    sudo python3 -m pip install -r requirements.txt --upgrade
    ```

    * `sudo` is required as usally domoticz runs under root user

## Features

* Use of latest zigpy radio libraries
* split between Device configuration files and plugin core engine
* More open way to configure/integrate non-standard Zigbee devices, [how-to](https://zigbeefordomoticz.github.io/wiki/en-eng/HowTo_Device-Customization.html).
