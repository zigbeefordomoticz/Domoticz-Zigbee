# ZigBeeForDomoticz plugin : Connect all your Zigbee devices to DomoticZ

![Zigbee for Domoticz](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/blob/beta6/images/Z4D-200.png )

[![Percentage of issues still open](http://isitmaintained.com/badge/open/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Percentage of issues still open")
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Average time to resolve an issue")
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/pipiche "Donate via PayPal")
[![CodeFactor](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/badge/beta6)](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/overview/beta6)

ZigBeeForDomoticz is a plugin for [Domoticz home automation software](https://www.domoticz.com/) to connect Zigbee devices through Zigbee coordinator (ZigBee hubs/gateways/bridges/controllers/adapters/dongles/sticks/keys).
This plugin is an evolution of the mature Zigate plugin, which will continue to manage and handle ZiGates in native mode, while the others will be handle through unified communication libraries from the [zigpy](https://github.com/zigpy/zigpy) project.

# Documentation - Installation

Everything is on our Wiki : <https://zigbeefordomoticz.github.io/wiki>

The wiki is available in [English](https://zigbeefordomoticz.github.io/wiki/en-eng/).
Le wiki est disposnible en [Français](https://zigbeefordomoticz.github.io/wiki/fr-fr/).
Der wiki ist auf [Deutsch](https://zigbeefordomoticz.github.io/wiki/nl-dut/) verfügbar.

# Repository structure

### The main branches

* `stable6` branch at `origin`, This is where you should find the most stable environment.
* `dev`is a parallel branch to `stable6` which is the main branch for the developpement, this is where you can find the latest features , but also potentials bugs.

### Working branches

Branches made out of `develop`are used for paralell development and will be merged back to `dev`when ready.

# Compatible hardware

## Tested Zigbee Coordinator hardware

### Zigbee Coordinator adapters

Since the release of 6th version in april 2022, we opened the plugin to other Zigbee Coordinator adapters than ZiGate's by adding the zigpy protocol.

#### ZiGate Zigbee Coordinator adapters

The plugin was originally developed for the [ZiGate](https://zigate.fr) Coordinator adapterss. They are still working in native mode.

#### Texas Instrument based Zigbee Coordinator adapters

Any Texas Instruments CC2531, CC13x2, CC26x2 adapters based on the [ZigBee Network Processors](http://dev.ti.com/tirex/content/simplelink_zigbee_sdk_plugin_2_20_00_06/docs/zigbee_user_guide/html/zigbee/introduction.html ) should be supported, more information could be found on [zigpy-znp](https://github.com/zigpy/zigpy-znp) which provided the layer to interface with the coordinator.

You can also find a list of [Texas Instruments supported adapters](https://www.zigbee2mqtt.io/guide/adapters/#recommended) which also works with [zigpy-znp](https://github.com/zigpy/zigpy-znp) and as such should also work with this plugin.

#### Silicon Labs based Zigbee Coordinator adapters

As for TI coordinator, we rely on [zigpy-bellows](https://github.com/zigpy/bellows) for the Silicon Labs compatibility . A list of compatible hardware is available [here](https://github.com/zigpy/bellows#hardware-requirement).

## Tested Zigbee Device Objects

A list of certified Zigbee Device Objects is maintained by community at [https://zigbee.blakadder.com](https://zigbee.blakadder.com/z4d.html). However please note that if Zigbee Device object is not listed there then that does not mean that it is not working with the plugin, Zigbee devices can still work directly or work partially and need some customization to get it fully working. Anyone in the community can help update and maintain that list via [Blackadder's Zigbee Device Compatibility Repository](https://github.com/blakadder/zigbee).

The reason for that that is that practically all Zigbee that are fully compliant with standard Zigbee 3.0, Zigbee Home Automation and Zigbee Light Link specifications as set by the Zigbee Alliance should technically be compatible with this project. The fact remains, however, that some hardware manufacturers do not always fully comply with each set specification, which can cause a few devices to only partially work or not work at all without custom integrations, but developers can often create workarounds for such issues via a solution for non-standard features. 

# Limitations

* Please do consider that the current plugin is limited to create a maximum of 255 "Widgets" (Domoticz devices).  This will still give you the possibility to integrate a large number of Zigbee devices , but not an unlimited number.

* Note that Zigbee always require you to add several mains-powered "Zigbee Router" devices (sometimes also refered to as Zigbee repeater and Zigbee extender) in order to extend reach range and coverage of your Zigbee network mesh as well as increase the size of your Zigbee network to reach that maximum number of devices, as the Zigbee Coordinator adapters on their own have relativly short range and poor signal penetration as well as only support a smaller number of directly connected devices (also known as direct children). It is highly recommended to read and follow the documentation for [best practices guidelines](https://zigbeefordomoticz.github.io/wiki/en-eng/HowTo_Build-a-ZigBee-network.html).

# Support

Your first place to get support is via the Forums.

* English channel : <https://www.domoticz.com/forum/viewforum.php?f=68>
* French Channel : <https://easydomoticz.com/forum/viewforum.php?f=28>

# Donations

Donations are more than welcome and will be used to buy new hardware, devices, sensors and in such testing and making them working with this ZigBee plugin For Domoticz. Please feel free to use the current link :

* <img src="https://www.pipiche.fr//pp.svg" width="24" height="24" alt="Donate via Paypal"/> <a href="https://paypal.me/pipiche">Donate via PayPal</a>
<br/>
