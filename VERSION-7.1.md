# Zigbee for Domoticz Version 7.1

## Objective

This documentation aims to provide an overview of the key features found in version 7.1 of the plugin. Additionally, it outlines the requirements for migrating to this version. Notably, as version 7.1 necessitates a minimum Python 3 version, automatic updates from the previous 6.3 version will not be available. Users will need to actively engage in the upgrade process to transition to the latest version.

## IMPORTANT

Once you have upgraded to version 7.1, please note that reverting to a previous version using a simple git checkout xxxx is not possible. In the event that you need to switch back to a previous version, it will be necessary to restore your backup and carefully reinstate both the Domoticz environment and the Plugin setup.

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

* Extensive Device Certification: The plugin boasts compatibility with approximately 500 certified devices. Each device has its dedicated configuration file, ensuring optimized integration. Moreover, the plugin has the capability to manage any Zigbee 3.0 compliant device without requiring a specific configuration file.

* Utilization of Latest Zigpy Radio Libraries: The plugin incorporates the use of cutting-edge Zigpy radio libraries, ensuring enhanced performance and reliability.

* Clear Separation of Device Configuration and Plugin Core Engine: The plugin's architecture distinguishes between device configuration files and the core engine. This separation allows for efficient management and scalability of certified devices, which are meticulously handled and maintained in the [ z4d-certified-devices repository](https://github.com/zigbeefordomoticz/z4d-certified-devices).

* Enhanced Flexibility for Non-Standard Zigbee Devices: The plugin provides an open and adaptable approach for configuring and integrating non-standard Zigbee devices. Detailed instructions and guidelines can be found in the [how-to](https://zigbeefordomoticz.github.io/wiki/en-eng/HowTo_Device-Customization.html) section, empowering users to customize their device integrations to meet specific requirements.
