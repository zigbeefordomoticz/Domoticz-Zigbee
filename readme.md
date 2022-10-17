# Zigbee for Domoticz plugin: Connect all your Zigbee devices to Domoticz

![Zigbee for Domoticz](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/blob/beta6/images/Z4D-200.png )

[![Percentage of issues still open](http://isitmaintained.com/badge/open/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Percentage of issues still open")
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Average time to resolve an issue")
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/pipiche "Donate via PayPal")
[![CodeFactor](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/badge/beta6)](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/overview/beta6)

## Zigbee for Domoticz

Zigbee for Domoticz a plugin for [Domoticz home automation software](https://www.domoticz.com/) to connect Zigbee devices through Zigbee coordinator (Zigbee controllers), like [ZiGate](https://zigate.fr), as well as Texas Instruments CC253x/CC13x2/CC26x2 Zigbee adapters/dongles/sticks/keys like [zzh](https://electrolama.com/projects/zig-a-zig-ah/), as well as Silicon Labs Zigbee adapters/dongles/sticks/keys like [elelabs](https://elelabs.com/)

This plugin is an evolution of the mature Zigate plugin for Domoticz, which will continue to manage and handle Zigate in native mode, while Texas Instruments's will be handle through unified communication libraries from the [zigpy](https://github.com/zigpy/zigpy) project. Please acknowledge that we are not developping nor maintaining zigpy project, and we rely on the zigpy community for zigpy related issues. If you want to get more insight here are the list of [open issue on zigpy related modules](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/issues/1235)

For __Windows users__, please check the [Plugin V6 running on Windows](https://zigbeefordomoticz.github.io/wiki/en-eng/Plugin_Version6_on_Windows.html) V6 running on Windows

## Pre requisities

* Domoticz 2021.1 or above
* You need Python 3.8 at least
* Zigpy layers will requires additional python3 modules to be install:

  Go to the plugin Home directory ( domoticz/plugins/Domoticz-Zigate or Domoticz-Zigbee)

  `sudo pip3 install -r requirements.txt`

## Plugin first installation or first time on release 6.xxx (stable6)

1. Make sure the pre-requisities steps (here above) have been executed

2. Go in your Domoticz directory using a command line and open the plugins directory.
  Usually you should be under domoticz/plugins

3. Run: `git clone https://github.com/zigbeefordomoticz/Domoticz-Zigbee.git`
  It will create a folder 'Domoticz-Zigbee'

4. Go in the Zigbee for Domoticz folder ( Domoticz-Zigbee ).
  Usally you should be under domoticz/plugins/Domoticz-Zigbee
  
5. run: `sudo pip3 install -r requirements.txt`

6. run: `git config --add submodule.recurse true`

7. run: `git submodule update --init --recursive`
  Finally, make the plugin.py file executable `chmod +x Domoticz-Zigbee/plugin.py`

8. Restart Domoticz.

## Plugin first time on release 6 (stable6 or beta6)

This is the case where you have move from the stable5 branch to stable6/beta6.

1. Make sure the pre-requisites steps (here above) have been executed

2. Go in the Zigbee for Domoticz folder ( Domoticz-Zigbee ).
  Usally you should be under domoticz/plugins/Domoticz-Zigbee

3. run: `git config --add submodule.recurse true`

4. run: `git submodule update --init --recursive`
  Finally, make the plugin.py file executable `chmod +x Domoticz-Zigbee/plugin.py`
  
5. run: `sudo pip3 install -r requirements.txt`

6. Restart Domoticz. (you need a FULL restart of Domotciz)

[More information available here](https://zigbeefordomoticz.github.io/wiki/en-eng/Plugin_Version-6.html)

## Regular Plugin update (when already on stable6)

1. Go in the Zigbee for Domoticz plugin directory
  Usally you should be under domoticz/plugins/Domoticz-Zigbee
  
2. run: `git pull --recurse-submodules`

3. run: `sudo pip3 install -r requirements.txt`

4. Restart Domoticz or plugin.

## Tested Hardware Zigbee adapters/dongles/sticks/keys

The plugin was originally developed for the [Zigate](https://zigate.fr) Coordinators in close relationship with [Zigate](https://zigate.fr) manufactuer.
In case you are looking to use non-ZiGate coordinators, please see here the [list of open issues](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/issues/1235) against the Zigpy libraries and its radio modules

Our main developement platforms is now using Texas Instruments or Silicon Labs Zigbee Coordinator adapters with Domoticz on Raspberry Pi. Those TI and Silabs based are Zigbee coordinators now provide much more functionnalities than ZiGate Zigbee coordinators, and so most of the newest and upcoming features are not available with ZiGate,  (features like example; real-time backup, Topology Report based on routing tables, and on-demand Over The Air device OTA firmware upgrades).

Note that regardless of model of Zigbee Coordinator it is generally recommended that users both initially and then relativly regularly upgrade the firmware on your Zigbee Coordinator adapter to try keeping it at least the latest known stable version, this is able one of the first steps before starting troubleshooting any issues.

### Texas Instrument Zigbee Coordinators

Since late 2021 where we have started opening the plugin to further brands of Zigbee Coordinators and begun focusing on compatibility with the [zzh](https://electrolama.com/projects/zig-a-zig-ah/) from [Electrolama](https://electrolama.com), thanks to their sponsorship.

Any Texas Instruments CC253x, CC13x2, CC26x2 adapters based on the [Zigbee Network Processors](http://dev.ti.com/tirex/content/simplelink_zigbee_sdk_plugin_2_20_00_06/docs/zigbee_user_guide/html/zigbee/introduction.html ) should be supported, more information could be found on [zigpy-znp](https://github.com/zigpy/zigpy-znp) which provided the layer to interface with the coordinator. Note however that CC2530 and CC2531 are no longer recommended as they use obsolete hardware chips and do not officially support Zigbee 3.0 capable firmware.

You can also find a list of [Texas Instruments supported adapters](https://www.zigbee2mqtt.io/guide/adapters/#recommended) which also works with [zigpy-znp](https://github.com/zigpy/zigpy-znp) and as such should also work with this plugin

### Silicon Labs Zigbee Coordinators

A big thanks to [Elelabs](https://elelabs.com/) sponsorship and whom have help us to ensure full compatibility with their Zigbee Coordinator ELU013 and ELR023.

We rely on [zigpy-bellows](https://github.com/zigpy/bellows) for the Silicon Labs compatibility. A list of compatible hardware is available [here](https://github.com/zigpy/bellows#hardware-requirement)

### dresden elektronik ConBee and RaspBee Zigbee Coordinators

Thanks goes to [dresden elektronik](https://github.com/dresden-elektronik/) / [Phoscon](https://phoscon.de/) for sponsorship and help in adding initial suppport with their ConBee and RaspBee (deCONZ firmware based) Zigbee Coordinators.

ConBee and RaspBee support is only in the beta6 branch for now as still experimental, however deconz support can otherwise be considered ready with only the minor limitations that Zigbee channel change is not yet possible, and there is currently no support for Wiser/Livolo devices (but a dresden elektronik / Phoscon developer is working on a new deCONZ firmware update for ConBee and RaspBee adapters that should sort out Wiser/Livolo device support).

deCONZ firmware based adapters depends on [zigpy-deconz](https://github.com/zigpy/zigpy-deconz) for ConBee/RaspBee compatibility.

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

* __beta6__: Current developement branch adds [ConBee/RaspBee (deconz) compatibility](https://github.com/zigpy/zigpy-deconz) on top of ZiGate/TI/Silabs support in stable branch.
* __stable6__: default branch provides stable support for these types of Zigbee Coordinator adapters/dongles/sticks/modules:
  * [ZiGate](https://zigate.fr) models known today,
  * [Electrolama zzh/zoe](https://electrolama.com/) models as well as [other Texas Instruments CC26x2/CC13x2 based adapters](https://github.com/zigpy/bellows/blob/dev/README.md#hardware-requirement) with newer [Z-Stack_3.x.0 firmware](https://github.com/Koenkk/Z-Stack-firmware/tree/master/coordinator/Z-Stack_3.x.0/bin),
  * [Elelabs](https://elelabs.com/shop/)/[Popp](https://popp.eu/zb-stick/) models as well as [other Silicon Labs EFR32MG1x/EFR32MG2x based adapters](https://github.com/zigpy/zigpy-znp/blob/dev/README.md#hardware-requirements) with newer [EZSP v8 firmware](https://github.com/grobasoz/zigbee-firmware/).

* Not supported
  * __stable5__: Support ALL ZiGate models known today and requires Domoticz 2020.x at minima (not supported anymore)
  * *__beta__*: lastest version 6.0.15 - February 2022
  * *__stable__*: latest version 4.11. - Feb. 2021) deprecated
  * *__master__*: latest version 3.0. - Sept. 2018) deprecated

## How to switch from one channel to the other

`git pull --recurse-submodules`
`git checkout stable6  // will move you to the stable6 channel`

`git checkout beta6    // will move you to the beta channel`
`git pull --recurse-submodules`

## Donations

Donations are more than welcome and will be used to buy new hard, devices, sensors and in such testing and making them working with the Zigate plugin. Please feel free to use the current link :

* <img src="https://www.pipiche.fr//pp.svg" width="24" height="24" alt="Donate via Paypal"/> <a href="https://paypal.me/pipiche">Donate via PayPal</a><br/>
