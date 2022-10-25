# Zigbee for Domoticz plugin: Connect all your Zigbee devices to Domoticz

![Zigbee for Domoticz](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/blob/beta6/images/Z4D-200.png )

[![Percentage of issues still open](http://isitmaintained.com/badge/open/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Percentage of issues still open")
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Average time to resolve an issue")
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/pipiche "Donate via PayPal")
[![CodeFactor](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/badge/beta6)](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/overview/beta6)

## Zigbee for Domoticz - [Wiki](https://zigbeefordomoticz.github.io/wiki)

Zigbee for Domoticz a plugin for [Domoticz home automation software](https://www.domoticz.com/) to connect Zigbee devices through Zigbee coordinator (Zigbee controllers), like [ZiGate](https://zigate.fr), as well as Texas Instruments CC253x/CC13x2/CC26x2 Zigbee adapters/dongles/sticks/keys like [zzh](https://electrolama.com/projects/zig-a-zig-ah/), as well as Silicon Labs Zigbee adapters/dongles/sticks/keys like [elelabs](https://elelabs.com/)

This plugin is an evolution of the mature Zigate plugin for Domoticz, which will continue to manage and handle Zigate in native mode, while Texas Instruments's will be handle through unified communication libraries from the [zigpy](https://github.com/zigpy/zigpy) project.

For __Windows users__, please check the [Plugin V6 running on Windows](https://zigbeefordomoticz.github.io/wiki/en-eng/Plugin_Version6_on_Windows.htmPlugin) V6 running on Windows

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

## Documentation

Documentation in English, French and Dutch (needs updates) are available on the [Wiki](https://zigbeefordomoticz.github.io/wiki)

## Support

Your first place to get support is via the Forums.

* English channel : <https://www.domoticz.com/forum/viewforum.php?f=68>
* French Channel : <https://easydomoticz.com/forum/viewforum.php?f=28>

## Donations

Donations are more than welcome and will be used to buy new hard, devices, sensors and in such testing and making them working with the Zigate plugin. Please feel free to use the current link :

* <img src="https://www.pipiche.fr//pp.svg" width="24" height="24" alt="Donate via Paypal"/> <a href="https://paypal.me/pipiche">Donate via PayPal</a><br/>
