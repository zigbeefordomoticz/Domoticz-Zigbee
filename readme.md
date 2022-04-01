# Zigbee for Domoticz a Zigbee for Domoticz

![Zigbee for Domoticz](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/blob/beta6/images/Z4D-200.png )

[![Percentage of issues still open](http://isitmaintained.com/badge/open/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Percentage of issues still open")
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Average time to resolve an issue")
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/pipiche "Donate via PayPal")
[![CodeFactor](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/badge/beta6)](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/overview/beta6)

## Zigbee for Domoticz

Zigbee for Domoticz a plugin for [Domoticz home automation software](https://www.domoticz.com/) to connect Zigbee devices through Zigbee coordinator (Zigbee controllers), like [ZiGate](https://zigate.fr), as well as Texas Instruments CC253x/CC13x2/CC26x2 Zigbee adapters/dongles/sticks/keys like [zzh](https://electrolama.com/projects/zig-a-zig-ah/), as well as Silicon Labs Zigbee adapters/dongles/sticks/keys like [elelabs](https://elelabs.com/)

This plugin is an evolution of the mature Zigate plugin for Domoticz, which will continue to manage and handle Zigate in native mode, while Texas Instruments's will be handle through unified communication libraries from the [zigpy](https://github.com/zigpy/zigpy) project.

## Pre requisities

* Domoticz 2021.1 or above
* You need Python 3.7 at least
* Zigpy layers will requires additional python3 modules to be install:

  `sudo pip3 install voluptuous pycrypto aiosqlite crccheck pyusb attrs aiohttp pyserial-asyncio`

## Plugin first installation or first time on release 6.xxx (stable6)

1. Make sure the pre-requisites steps (here above) have been executed

2. Go in your Domoticz directory using a command line and open the plugins directory.
  Usually you should be under domoticz/plugins

3. Run: `git clone https://github.com/zigbeefordomoticz/Domoticz-Zigbee.git`
  It will create a folder 'Domoticz-Zigbee'

4. Go in the Zigbee for Domoticz folder ( Domoticz-Zigbee ).
  Usally you should be under domoticz/plugins/Domoticz-Zigbee

5. run: `git config --add submodule.recurse true`

6. run: `git submodule update --init --recursive`
  Finally, make the plugin.py file executable `chmod +x Domoticz-Zigbee/plugin.py`

7. Restart Domoticz.

## Plugin first time on release 6 (stable6 or beta6)

This is the case where you have move from the stable5 branch to stable6/beta6.

1. Make sure the pre-requisites steps (here above) have been executed

2. Go in the Zigbee for Domoticz folder ( Domoticz-Zigbee ).
  Usally you should be under domoticz/plugins/Domoticz-Zigbee

3. run: `git config --add submodule.recurse true`

4. run: `git submodule update --init --recursive`
  Finally, make the plugin.py file executable `chmod +x Domoticz-Zigbee/plugin.py`

5. Restart Domoticz. (you need a FULL restart of Domotciz)

[More information available here](https://zigbeefordomoticz.github.io/wiki/en-eng/Plugin_Version-6.html)

## Regular Plugin update (when already on stable6)

1. Go in the Zigbee for Domoticz plugin directory
  Usally you should be under domoticz/plugins/Domoticz-Zigbee
  
2. run: `git pull --recurse-submodules`

3. Restart Domoticz or plugin.

## Tested Hardware Zigbee adapters/dongles/sticks/keys

The plugin was originally developed for the [Zigate](https://zigate.fr) Coordinators in close relationship with [Zigate](https://zigate.fr) manufactuer.

### Texas Instrument Zigbee Coordinators

Since late 2021 where we have started opening the plugin to further brands of Zigbee Coordinators and begun focusing on compatibility with the [zzh](https://electrolama.com/projects/zig-a-zig-ah/) from [Electrolama](https://electrolama.com), thanks to their sponsorship.

Any Texas Instruments CC2531, CC13x2, CC26x2 adapters based on the [Zigbee Network Processors](http://dev.ti.com/tirex/content/simplelink_zigbee_sdk_plugin_2_20_00_06/docs/zigbee_user_guide/html/zigbee/introduction.html ) should be supported, more information could be found on [zigpy-znp](https://github.com/zigpy/zigpy-znp) which provided the layer to interface with the coordinator.

You can also find a list of [Texas Instruments supported adapters](https://www.zigbee2mqtt.io/guide/adapters/#recommended) which also works with [zigpy-znp](https://github.com/zigpy/zigpy-znp) and as such should also work with this plugin

### Silicon Labs Zigbee Coordinators

A big thanks to [Elelabs](https://elelabs.com/) sponsorship and whom have help us to ensure full compatibility with their Zigbee Coordinator ELU013 and ELR023.

As for TI coordinator, we rely on [zigpy-bellows](https://github.com/zigpy/bellows) for the Silicon Labs compatibility . A list of compatible hardware is available [here](https://github.com/zigpy/bellows#hardware-requirement)

## LIMITATIONS

* Please do consider that the current plugin is limited to create a maximum of 255 "Widgets" (Domoticz devices).  This will still give you the possibility to integrate a large number of Zigbee devices , but not an unlimited number.

  * Note that as with all Zigbee hubs/gateways/bridges you will need to add several "Zigbee Router" devices in order to increase the size of your Zigbee network mesh to reach that maximum number of devices, as the Zigbee Coordinator adapter will only support a smaller number of direct connected devices. See documentation troubleshooting section for best practices.

* Currently there is a limitation with the non-ZiGate coordinator to have only 1 coordinator instance.

## Documentation

Documentation are available on the [Wiki](https://zigbeefordomoticz.github.io/wiki)

## Support

Your first place to get support is via the Forums.

* English channel : <https://www.domoticz.com/forum/viewforum.php?f=68>
* French Channel : <https://easydomoticz.com/forum/viewforum.php?f=28>

## About release channels

In order to provide stability and also provide more recent development, Zigbee for Domoticz plugin has the following channels

* **beta6**: Current developpement branch and allow TI CCxxxx , Silicon Labs and deConz coordinators on top of ZiGate coordinators.
* **stable6**: default branch for
  * [ZiGate](https://zigate.fr) models knwon today,
  * [Electrolama](https://electrolama.com/) models as well as the Texas Instrument CCxxx based coordinators,
  * [Elelabs](https://elelabs.com/products/elelabs-usb-adapter.html) as well as the Silicon Labs based coordinators.

* Not supported
  * **stable5**: Support ALL ZiGate models known today and requires Domoticz 2020.x at minima (not supported anymore)
  * ***beta***: lastest version 6.0.15 - February 2022
  * ***stable***: latest version 4.11. - Feb. 2021) deprecated
  * ***master***: latest version 3.0. - Sept. 2018) deprecated

## How to switch from one channel to the other

`git pull --recurse-submodules`
`git checkout stable6  // will move you to the stable5 channel`

`git checkout beta6    // will move you to the beta channel`
`git pull --recurse-submodules`

## Donations

Donations are more than welcome and will be used to buy new hard, devices, sensors and in such testing and making them working with the Zigate plugin. Please feel free to use the current link :

* <img src="https://www.pipiche.fr//pp.svg" width="24" height="24" alt="Donate via Paypal"/> <a href="https://paypal.me/pipiche">Donate via PayPal</a><br/>
