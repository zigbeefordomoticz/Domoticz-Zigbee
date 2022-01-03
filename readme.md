# Zigbee for Domoticz a Zigbee for Domoticz

![Zigbee for Domoticz](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/blob/zigpy/images/Z4D-200.png )

[![Percentage of issues still open](http://isitmaintained.com/badge/open/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Percentage of issues still open")
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Average time to resolve an issue")
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/pipiche "Donate via PayPal")

[![CodeFactor](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/badge/beta)](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/overview/beta)

## Zigbee for Domoticz

Zigbee for Domoticz a plugin for [Domoticz home automation software](https://www.domoticz.com/) to connect Zigbee devices through Zigbee cooridnators (Zigbee controllers), like [ZiGate](https://zigate.fr), as well as Texas Instruments CC253x/CC13x2/CC26x2 Zigbee adapters/dongles/sticks/keys via [zigpy](https://github.com/zigpy) library.

This plugin is an evolution of the mature Zigate plugin for Domoticz, which will continue to manage and handle Zigate in native mode, while Texas Instruments's and other future Zigbee stacks will be handle through unified communication libraries from the [zigpy](https://github.com/zigpy/zigpy) project.

## Compatibility WARNINGS

### REQUIRES Domoticz 2020 or above

The plugin requires Domoticz 2020 or above. We strongly recommend 2021.1 or above
If you cannot be on Domoticz 2020.x or above, please use the 'stable' branch which is the only one compatible with the oldest Domoticz version

### Tested Zigbee Coordinator hardware

The plugin was originally developed for the [Zigate](https://zigate.fr) controller in close relationship with the [Zigate](https://zigate.fr) manufactuer.
Since late 2021 where we have stated opening the plugin to further brands of Zigbee Coordinators and begun focusing on compatibility with the [zzh](https://electrolama.com/projects/zig-a-zig-ah/) from [Electrolama](https://electrolama.com), thanks to their sponsorship. And a big thanks to @puddly and @Adminiuga from the zigpy team.

All Texas Instruments CC253x/CC13x2/CC26x2 ZNP (Zigbee Network Processors) adapter using standard Z-Stack 3 (TI  SimpleLink Zigbee stack) firmware should be supported, (e.g. [zzh USB adapter by Electrolama](https://electrolama.com/projects/zig-a-zig-ah/)), more information could be found on [zigpy-znp](https://github.com/zigpy/zigpy-znp) which provides the layer to interface with the Zigbee coordinator.

You can also find a list of Texas Instruments in [Supported Adapters](https://www.zigbee2mqtt.io/guide/adapters/#recommended) which also works with [zigpy-znp](https://github.com/zigpy/zigpy-znp) and as such should also work with this plugin

## LIMITATIONS

* Please do consider that the current plugin is limited to create a maximum of 255 "Widgets" (Domoticz devices).  This will still give you the possibility to integrate a large number of Zigbee devices, but not an unlimited number.

## Documentation

Documentation are available on the GitHub [Wiki](https://github.com/zigbeefordomoticz/Domoticz-Zigate-Wiki "Wiki")

## Support

Your first place to get support is via the Forums.

* English channel : <https://www.domoticz.com/forum/viewforum.php?f=68>
* French Channel : <https://easydomoticz.com/forum/viewforum.php?f=28>

## About release channels

In order to provide stability and also provide more recent development, Zigbee for Domoticz plugin has the following channels

* **stable6**: Support the up coming evolutions and the non-ZiGate controllers via the zigpy layer.
* **beta**: We can open the beta channel to provide early version and to stabilize the version priori to be move to the stable channel
* **stable5**: Support ALL ZiGate models known today and requires Domoticz 2020.x at minima
* ***stable***: latest version 4.11. - Feb. 2021) deprecated
* ***master***: latest version 3.0. - Sept. 2018) deprecated

## How to switch from one channel to the other

`git pull --recurse-submodules`

`git checkout stable5  // will move you to the stable5 channel`

`git checkout beta    // will move you to the beta channel`

`git pull --recurse-submodules` // Might be required

In case you need to be on stable instead of stable5

`git checkout stable  // will move you to the stable channel`

## Donations

Donations are more than welcome and will be used to buy new hard, devices, sensors and in such testing and making them working with the Zigate plugin. Please feel free to use the current link :

* <img src="https://www.pipiche.fr//pp.svg" width="24" height="24" alt="Donate via Paypal"/> <a href="https://paypal.me/pipiche">Donate via PayPal</a><br/>
