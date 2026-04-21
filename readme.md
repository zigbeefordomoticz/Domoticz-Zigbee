# Zigbee for Domoticz Plugin

![Zigbee for Domoticz](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/blob/stable7/images/Z4D-200.png?raw=true )

[![Percentage of issues still open](http://isitmaintained.com/badge/open/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Percentage of issues still open")
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/zigbeefordomoticz/Domoticz-Zigbee.svg)](http://isitmaintained.com/project/zigbeefordomoticz/Domoticz-Zigbee "Average time to resolve an issue")
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/pipiche "Donate via PayPal")
[![CodeFactor](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/badge/stable7)](https://www.codefactor.io/repository/github/zigbeefordomoticz/domoticz-zigbee/overview/stable7)

**Zigbee for Domoticz** is a powerful Python plugin that integrates Zigbee devices into the [Domoticz](https://www.domoticz.com/) home automation system without requiring cloud applications. Evolving from the original Zigate plugin, it supports a wide range of Zigbee coordinators and approximately **500 certified Zigbee devices**, leveraging the [zigpy](https://github.com/zigpy/zigpy) libraries for enhanced compatibility and performance.

## Features
- **Broad Coordinator Support**: Compatible with Zigate, Texas Instruments (CC2531, CC13x2, CC26x2 via zigpy-znp), Silicon Labs (EFR32MGxx via zigpy-bellows), and deCONZ (ConBee/RaspBee via zigpy-deconz) Zigbee coordinators.
- **Device Compatibility**: Supports Zigbee 3.0, Zigbee Home Automation, and Zigbee Light Link devices, with dedicated configuration files for ~500 certified devices via the [z4d-certified-devices](https://github.com/zigbeefordomoticz/z4d-certified-devices) module. Any Zigbee 3.0-compliant device can be integrated without specific configuration.
- **Web User Interface**: A modern WebUI (available at [Domoticz-Zigbee-UI](https://github.com/zigbeefordomoticz/Domoticz-Zigbee-UI)) allows device management, raw Zigbee command sending, and network topology visualization. Accessible at `/z4d` and reverse-proxy compatible.
- **Over-The-Air (OTA) Updates**: Supports firmware upgrades for compatible Zigbee devices.
- **Advanced Features**: Includes network topology visualization, attribute discovery (in zigpy mode), and support for devices like ZLinky in multiple modes.
- **Limit of 255 Widgets**: Domoticz devices (widgets) are capped at 255, requiring mains-powered Zigbee routers to extend the network mesh.

## Requirements
- **Domoticz**: Version 2025.1 or higher.
- **Python**: Version 3.11 or higher with the `python3-dev` package.
- **Operating System**: Recommended for Linux (Raspberry Pi, Debian, Ubuntu). Windows support is not officially supported and may encounter issues.
- **Zigbee Coordinator**: A supported Zigbee radio module (see [Coordinator Compatibility](#coordinator-compatibility)).

## Limitations
- Running **multiple instances** of the plugin when running Domoticz 2026 and python3.11 is buggy due to an issue in python3.11 ( https://github.com/domoticz/domoticz/issues/6763 )
  We recommend you to switch to Python3.13 at least which doesn't have such issue.

## Documentation - Installation
Everything is on our Wiki : <https://zigbeefordomoticz.github.io/wiki>

The wiki is available in [English](https://zigbeefordomoticz.github.io/wiki/en-eng/).
Le wiki est disposnible en [Français](https://zigbeefordomoticz.github.io/wiki/fr-fr/).
Der wiki ist auf [Deutsch](https://zigbeefordomoticz.github.io/wiki/nl-dut/) verfügbar.

## Coordinator Compatibility
- **Zigate**: Native support for Zigate coordinators (serial and WiFi). **NOT SUPPORTED anymore**, we advise any user to move to a TI, Silicon Labs, or deConz coordinaor
- **Texas Instruments**: CC2531, CC13x2, CC26x2 (via zigpy-znp). Note: CC253x adapters are obsolete and not recommended [compatible hardware](https://github.com/zigpy/zigpy-znp?tab=readme-ov-file#hardware-requirements)
- **Silicon Labs**: EFR32MGxx chipsets (via zigpy-bellows) [compatible hardware](https://github.com/zigpy/bellows#hardware-requirement)
- **deCONZ**: ConBee/RaspBee (via zigpy-deconz). ConBee III support is deprecated due to instability.

## Device Compatibility
- Supports ~500 certified devices with configuration files in [z4d-certified-devices](https://github.com/zigbeefordomoticz/z4d-certified-devices).
- Compatible with Zigbee 3.0-compliant devices, even without specific configurations.
- Limitations:
  - Some devices (e.g., Philips bulbs) require polling due to missing Configure Reporting.
  - Non-standard devices (e.g., GLEDOPTO) may act as poor routers or lack features like LQI reporting.
  - Partial support for devices like Wiser Thermostat (temperature reporting only).

The community maintains a list of certified Zigbee Device Objects at [https://zigbee.blakadder.com](https://zigbee.blakadder.com/z4d.html). It's important to note that if a Zigbee Device object is not listed there, it does not necessarily mean that it won't work with the plugin. Zigbee devices may still function directly or partially, requiring some customization to achieve full compatibility. The community, including anyone interested, can contribute to updating and maintaining the list through Blackadder's Zigbee Device Compatibility Repository.

In theory, any Zigbee devices that fully comply with the Zigbee 3.0, Zigbee Home Automation, and Zigbee Light Link specifications set by the Zigbee Alliance should be technically compatible with this project. However, it's worth noting that certain hardware manufacturers may not consistently adhere to all the specified requirements, resulting in partial or non-functional device behavior without custom integrations. Nevertheless, developers often find solutions or workarounds for non-standard features to address these issues.

## Branches
- **stable7**: out of support (version 7.1.xxx).
- **stable8**: Recommended for production use (version 8.1.xxx).


## Troubleshooting
- Check the Domoticz log file for errors.
- Refer to the [Wiki](https://zigbeefordomoticz.github.io/wiki) for best practices and troubleshooting guides.
- Ensure mains-powered Zigbee routers are included to extend the network mesh.
- For zigpy-related issues, consult the [zigpy documentation](https://zigpy.readthedocs.io/).

## Community and Support
- **English Forum**: [Domoticz Forum](https://www.domoticz.com/forum/viewforum.php?f=68)
- **French Forum**: [EasyDomoticz Forum](https://easydomoticz.com/forum/viewforum.php?f=28)
- **Wiki**: [Zigbee for Domoticz Wiki](https://zigbeefordomoticz.github.io/wiki) (available in English, French, German)
- **Contributions**: We welcome device samples for testing, WebUI translations (English, French, German, Spanish), and code contributions. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License
This project is licensed under the [GNU General Public License v3.0](LICENSE.txt).

## Acknowledgments
- Built on the original Zigate plugin.
- Powered by [zigpy](https://github.com/zigpy/zigpy) and its radio libraries.
- Thanks to the Domoticz and Zigbee communities for their support and contributions.

## Donations and Sponsorship
We warmly invite Manufacturers and sellers to contribute by sending us samples of their devices for integration. Your support in this regard is greatly appreciated as it enables us to expand our compatibility and offer a more comprehensive solution.
We extend our heartfelt gratitude to our generous donors whose contributions enable us to acquire additional equipment for rigorous testing and seamless integration. With your support, we can further enhance the plugin's capabilities and deliver an even more powerful and versatile experience for our users.

* <img src="https://www.pipiche.fr//pp.svg" width="24" height="24" alt="Donate via Paypal"/> <a href="https://paypal.me/pipiche">Donate via PayPal</a>
<br/>

