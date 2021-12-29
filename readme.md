# Zigbee for Domoticz a Zigbee for Domoticz

![Zigbee for Domoticz](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/blob/zigpy/images/Z4D-200.png )

[![Percentage of issues still open](http://isitmaintained.com/badge/open/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Percentage of issues still open")
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Average time to resolve an issue")
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/pipiche "Donate via PayPal")

[![CodeFactor](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/badge/beta)](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/overview/beta)

## Zigbee for Domoticz

Is a domoticz plugin to connect Zigbee devices through Zigbee controllers like [Zigate](https://zigate.fr) , Texas Instruments CC2531, CC13x2, CC26x2 adapters (via Zigpy library) like [zzh](https://electrolama.com/projects/zig-a-zig-ah/) .

This plugin is an evolution of the mature Zigate plugin, which will continue to manage and handle Zigate in native mode, while other coordinator will be handle through a unified communication library named [zigpy](https://github.com/zigpy/zigpy).

## Compatibility WARNINGS

### REQUIRES Domoticz 2020 or above

The plugin requires Domoticz 2020 or above. We strongly recommend 2021.1 or above
If you cannot be on Domoticz 2020.x or above, please use the 'stable' branch which is the only one compatible with the oldest Domoticz version

### Tested Hardware Coordinatoros

The plugin has been full developpped on [Zigate](https://zigate.fr) controller and in closed relationship with the [Zigate](https://zigate.fr) manufactuer.
Since late 2021 where we have stated opening the plugin to further brands of Coordinators and we have focussed on the [zzh](https://electrolama.com/projects/zig-a-zig-ah/) from [Electrolama](https://electrolama.com), thanks to their sponsorship. And a big thanks to @puddly and @hedda from the zigpy team.

Any Texas Instruments CC2531, CC13x2, CC26x2 adapters based on the [Zigbee Network Processors](http://dev.ti.com/tirex/content/simplelink_zigbee_sdk_plugin_2_20_00_06/docs/zigbee_user_guide/html/zigbee/introduction.html ) should be supported, more information could be found on [zigpy-znp](https://github.com/zigpy/zigpy-znp) which provided the layer to interface with the coordinator.

You can also find a list of [Supported Adapters](https://www.zigbee2mqtt.io/guide/adapters/#recommended) which also works with [zigpy-znp](https://github.com/zigpy/zigpy-znp) and so should work with the plugin

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

### stable (will be deprecated)

Support only ZiGate V1. (not supported anymore)

### stable5

Support ALL ZiGate models known today and requires Domoticz 2020.x at minima

### stable6

Support the up coming evolutions and the non-ZiGate controllers via the zigpy layer.

### beta

We can open the beta channel to provide early version and to stabilize the version priori to be move to the stable channel

### master ( deprecated )

This channel is not maintained anymore and is not compatible to the most recent version.
Moving from this channel to the other will required either ar restart from scratch or to do an upgrade of the Domoticz and Zigate database.

## How to switch from one channel to the other

`git pull`

`git checkout stable5  // will move you to the stable5 channel`

`git checkout beta    // will move you to the beta channel`

In case you need to be on stable instead of stable5

`git checkout stable  // will move you to the stable channel`

## Donations

Donations are more than welcome and will be used to buy new hard, devices, sensors and in such testing and making them working with the Zigate plugin. Please feel free to use the current link :

* <img src="https://www.pipiche.fr//pp.svg" width="24" height="24" alt="Donate via Paypal"/> <a href="https://paypal.me/pipiche">Donate via PayPal</a><br/>
