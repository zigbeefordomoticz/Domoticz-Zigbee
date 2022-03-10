# Zigbee for Domoticz a Zigbee for Domoticz

![Zigbee for Domoticz](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/blob/beta6/images/Z4D-200.png )

[![Percentage of issues still open](http://isitmaintained.com/badge/open/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Percentage of issues still open")
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Average time to resolve an issue")
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/pipiche "Donate via PayPal")

[![CodeFactor](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/badge/beta6)](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/overview/beta6)

## Zigbee for Domoticz

Zigbee for Domoticz a plugin for [Domoticz home automation software](https://www.domoticz.com/) to connect Zigbee devices through Zigbee coordinator (Zigbee controllers), like [ZiGate](https://zigate.fr), as well as Texas Instruments CC253x/CC13x2/CC26x2 Zigbee adapters/dongles/sticks/keys like [zzh](https://electrolama.com/projects/zig-a-zig-ah/).

This plugin is an evolution of the mature Zigate plugin for Domoticz, which will continue to manage and handle Zigate in native mode, while Texas Instruments's will be handle through unified communication libraries from the [zigpy](https://github.com/zigpy/zigpy) project.

## Pre requisities

* Domoticz 2021.1 or above
* You need Python 3.7 at least
* Zigpy layers will requires additional python3 modules to be install:

  `sudo pip3 install voluptuous pycrypto aiosqlite crccheck pyusb attr attrs aiohttp pyserial-asyncio`

## Plugin first installation or first time on release 6.xxx (for now beta6)

The first time you have to install the plugin via the `git clone` command, or you have been move to the release 6.x.

* Go in your Domoticz directory using a command line and open the plugins directory.
  Usually you should be under domoticz/plugins

* Run: `git clone https://github.com/zigbeefordomoticz/Domoticz-Zigbee.git`
  It will create a folder 'Domoticz-Zigbee'

* Go in the Zigbee for Domoticz folder ( Domoticz-Zigbee ).
  Usally you should be under domoticz/plugins/Domoticz-Zigbee

* run: `git config --add submodule.recurse true`

* run: `git submodule update --init --recursive`
  Finally, make the plugin.py file executable `chmod +x Domoticz-Zigbee/plugin.py`

* Restart Domoticz.

[More information available here](https://github.com/zigbeefordomoticz/wiki/blob/master/fr-fr/Plugin_Version-6.md)

## Plugin update

* Go in the Zigbee for Domoticz plugin directory
  Usally you should be under domoticz/plugins/Domoticz-Zigbee
  
* run: `git pull --recurse-submodules`

### Tested Hardware Zigbee adapters/dongles/sticks/keys

The plugin was originally developed for the [Zigate](https://zigate.fr) Coordinators in close relationship with [Zigate](https://zigate.fr) manufactuer.

#### Texas Instrument Zigbee Coordinators
Since late 2021 where we have started opening the plugin to further brands of Zigbee Coordinators and begun focusing on compatibility with the [zzh](https://electrolama.com/projects/zig-a-zig-ah/) from [Electrolama](https://electrolama.com), thanks to their sponsorship.

Any Texas Instruments CC2531, CC13x2, CC26x2 adapters based on the [Zigbee Network Processors](http://dev.ti.com/tirex/content/simplelink_zigbee_sdk_plugin_2_20_00_06/docs/zigbee_user_guide/html/zigbee/introduction.html ) should be supported, more information could be found on [zigpy-znp](https://github.com/zigpy/zigpy-znp) which provided the layer to interface with the coordinator.

You can also find a list of [Texas Instruments supported adapters](https://www.zigbee2mqtt.io/guide/adapters/#recommended) which also works with [zigpy-znp](https://github.com/zigpy/zigpy-znp) and as such should also work with this plugin


#### Silicon Labs Zigbee Coordinators

A big thanks to [Elelabs](https://elelabs.com/) sponsorship and whom have help us to ensure full compatibility with their Zigbee Coordinator ELU013 and ELR023.

As for TI coordinator, we rely on [zigpy-bellows](https://github.com/zigpy/bellows) for the Silicon Labs compatibility . A list of compatible hardware is available [here](https://github.com/zigpy/bellows#hardware-requirement)

## LIMITATIONS

* Please do consider that the current plugin is limited to create a maximum of 255 "Widgets" (Domoticz devices).  This will still give you the possibility to integrate a large number of Zigbee devices , but not an unlimited number.

## Documentation

Documentation are available on the GitHub [Wiki](https://github.com/zigbeefordomoticz/Domoticz-Zigate-Wiki "Wiki")

## Support

Your first place to get support is via the Forums.

* English channel : <https://www.domoticz.com/forum/viewforum.php?f=68>
* French Channel : <https://easydomoticz.com/forum/viewforum.php?f=28>

## About release channels

In order to provide stability and also provide more recent development, Zigbee for Domoticz plugin has the following channels

* **beta6**: Current developpement branch integrates zigpy library and allow TI CCxxxx coordinators on top of ZiGate coordinators. Requires Domoticz 2021.1 at minima
* **stable5**: Support ALL ZiGate models known today and requires Domoticz 2020.x at minima


* Not supported
  * ***beta***: lastest version 6.0.15 deprecated (will be remove end of February 2022)
  * ***stable***: latest version 4.11. - Feb. 2021) deprecated
  * ***master***: latest version 3.0. - Sept. 2018) deprecated


## How to switch from one channel to the other

`git pull --recurse-submodules`

`git checkout stable5  // will move you to the stable5 channel`

`git checkout beta6    // will move you to the beta channel`

`git pull --recurse-submodules` // Might be required


## Donations

Donations are more than welcome and will be used to buy new hard, devices, sensors and in such testing and making them working with the Zigate plugin. Please feel free to use the current link :

* <img src="https://www.pipiche.fr//pp.svg" width="24" height="24" alt="Donate via Paypal"/> <a href="https://paypal.me/pipiche">Donate via PayPal</a><br/>
