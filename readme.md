# Seamlessly Integrate and Empower Your Zigbee Devices with DomoticZ Using the ZigBeeForDomoticz Plugin

![Zigbee for Domoticz](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/blob/stable6/images/Z4D-200.png?raw=true )

[![Percentage of issues still open](http://isitmaintained.com/badge/open/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Percentage of issues still open")
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Average time to resolve an issue")
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/pipiche "Donate via PayPal")
[![CodeFactor](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/badge/stable6)](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/overview/stable6)

ZigBeeForDomoticz serves as an advanced plugin designed to seamlessly integrate Zigbee devices into the [Domoticz home automation software](https://www.domoticz.com/) software. By utilizing a Zigbee coordinator (such as ZigBee hubs, gateways, bridges, controllers, adapters, dongles, sticks, or keys), this plugin establishes a reliable connection with Zigbee-enabled devices.

This plugin represents an evolution of the well-established Zigate plugin. While Zigate coordinators will continue to be efficiently managed and handled in native mode, ZigBeeForDomoticz leverages unified communication libraries from the [zigpy](https://github.com/zigpy/zigpy) to effectively handle other Zigbee devices. This integration enables enhanced functionality and seamless communication within the Domoticz ecosystem.

# Documentation - Installation

Everything is on our Wiki : <https://zigbeefordomoticz.github.io/wiki>

The wiki is available in [English](https://zigbeefordomoticz.github.io/wiki/en-eng/).
Le wiki est disposnible en [Français](https://zigbeefordomoticz.github.io/wiki/fr-fr/).
Der wiki ist auf [Deutsch](https://zigbeefordomoticz.github.io/wiki/nl-dut/) verfügbar.

# Repository structure

### The main branches

* Support for `stable5` is deprecated.
* Support for `stable6` is deprecated. We recommend upgrading to the latest version, stable7.
* The `stable7` branch is located at origin and represents the most stable environment for the plugin.
* The `develop`branch is deprecated
* The `develop7` branch runs parallel to `stable7` and serves as the primary branch for ongoing development. This is where you can access the latest features, but please be aware that potential bugs may also be present.

### Working branches

Branches made out of `develop` are used for paralell development and will be merged back to `deevelop`when ready.

# Compatible hardware

## Tested Zigbee Coordinator hardware

### Zigbee Coordinator adapters

Since the release of 6th version in april 2022, we opened the plugin to other Zigbee Coordinator adapters than ZiGate's by adding the zigpy protocol.

#### ZiGate Zigbee Coordinator adapters

The plugin was initially created for the [ZiGate Coordinator](https://zigate.fr) adapters, which are currently functioning in their native mode. However, we are encountering increasing limitations primarily caused by the insufficient support from NXP and the scarce firmware updates/developments.

#### Texas Instrument based Zigbee Coordinator adapters

Support should be available for any Texas Instruments CC2531, CC13x2, CC26x2 adapters that are based on [ZigBee Network Processors](http://dev.ti.com/tirex/content/simplelink_zigbee_sdk_plugin_2_20_00_06/docs/zigbee_user_guide/html/zigbee/introduction.html). For more information, you can refer to [zigpy-znp](https://github.com/zigpy/zigpy-znp), which provides the interface layer with the coordinator.

List of supported [Texas Instruments supported adapters](https://www.zigbee2mqtt.io/guide/adapters/#recommended).

#### Silicon Labs based Zigbee Coordinator adapters

As for TI coordinator, we rely on [zigpy-bellows](https://github.com/zigpy/bellows) for the Silicon Labs compatibility . A list of compatible hardware is available [here](https://github.com/zigpy/bellows#hardware-requirement).

## Tested Zigbee Device Objects

The community maintains a list of certified Zigbee Device Objects at [https://zigbee.blakadder.com](https://zigbee.blakadder.com/z4d.html). It's important to note that if a Zigbee Device object is not listed there, it does not necessarily mean that it won't work with the plugin. Zigbee devices may still function directly or partially, requiring some customization to achieve full compatibility. The community, including anyone interested, can contribute to updating and maintaining the list through Blackadder's Zigbee Device Compatibility Repository.

In theory, any Zigbee devices that fully comply with the Zigbee 3.0, Zigbee Home Automation, and Zigbee Light Link specifications set by the Zigbee Alliance should be technically compatible with this project. However, it's worth noting that certain hardware manufacturers may not consistently adhere to all the specified requirements, resulting in partial or non-functional device behavior without custom integrations. Nevertheless, developers often find solutions or workarounds for non-standard features to address these issues.


# Limitations

* Keep in mind that the current plugin has a limitation where it can create a maximum of 255 "Widgets" (Domoticz devices). While this allows for integration of a substantial number of Zigbee devices, it's important to note that there is a finite limit, and it does not support an unlimited number of devices.

* It's essential to understand that Zigbee networks always require the inclusion of multiple mains-powered "Zigbee Router" devices (also known as Zigbee repeaters and extenders) to effectively extend the reach, range, and coverage of your Zigbee network mesh. This is crucial for increasing the size of your Zigbee network to reach the maximum number of devices. The Zigbee Coordinator adapters themselves have relatively limited range and signal penetration, as well as support for only a smaller number of directly connected devices (referred to as direct children). It is highly recommended to thoroughly review and adhere to the documentation's [best practices guidelines](https://zigbeefordomoticz.github.io/wiki/en-eng/HowTo_Build-a-ZigBee-network.html) for optimal network setup and performance.


# Support

Your first place to get support is via the Forums.

* English channel : <https://www.domoticz.com/forum/viewforum.php?f=68>
* French Channel : <https://easydomoticz.com/forum/viewforum.php?f=28>

# Donations

We warmly invite Manufacturers and sellers to contribute by sending us samples of their devices for integration. Your support in this regard is greatly appreciated as it enables us to expand our compatibility and offer a more comprehensive solution.

We extend our heartfelt gratitude to our generous donors whose contributions enable us to acquire additional equipment for rigorous testing and seamless integration. With your support, we can further enhance the plugin's capabilities and deliver an even more powerful and versatile experience for our users.

* <img src="https://www.pipiche.fr//pp.svg" width="24" height="24" alt="Donate via Paypal"/> <a href="https://paypal.me/pipiche">Donate via PayPal</a>
<br/>
