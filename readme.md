# Zigate Plugin for Domoticz

![zigate.fr](https://github.com/pipiche38/Domoticz-Zigate-Wiki/blob/master/Images/ZiGate.png)

[![Percentage of issues still open](http://isitmaintained.com/badge/open/pipiche38/Domoticz-Zigate.svg)](http://isitmaintained.com/project/pipiche38/Domoticz-Zigate "Percentage of issues still open")
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/pipiche38/Domoticz-Zigate.svg)](http://isitmaintained.com/project/pipiche38/Domoticz-Zigate "Average time to resolve an issue")
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/pipiche "Donate via PayPal")

[![CodeFactor](https://www.codefactor.io/repository/github/pipiche38/domoticz-zigate/badge/beta)](https://www.codefactor.io/repository/github/pipiche38/domoticz-zigate/overview/beta)

[Zigate](https://zigate.fr "Python Plugin for Domoticz home automation.")

For information around the Zigate Plugin, please refer to :

* <https://github.com/pipiche38/Domoticz-Zigate-Wiki/blob/master/en-eng/Home.md> for information

## COMPATIBILITY WARNING: REQUIRES Domoticz 2020 or above

The current plugin version 5.1 supports ZiGate V1 and ZiGate V2. 
We strongly recommend to use Domoticz 2021.1 or above

If you cannot be on Domoticz 2020.x or above, please use the 'stable' branch which is the only one compatible with the oldest Domoticz version

## LIMITATIONS

* Please do consider that the current plugin is limited to create a maximum of 255 "Widgets" (Domoticz devices).  This will still give you the possibility to integrate a large number of Zigbee devices , but not an unlimited number.

## Documentation

Documentation are available on the GitHub [Wiki](https://github.com/pipiche38/Domoticz-Zigate-Wiki "Wiki")

## Support

Your first place to get support is via the Forums.

* English channel : <https://www.domoticz.com/forum/viewforum.php?f=68>
* French Channel : <https://easydomoticz.com/forum/viewforum.php?f=28>

## About release channels

In order to provide stability and also provide more recent development, Zigate plugin has the following channels

### stable (will be deprecated)

Support only ZiGate V1. and supported on best effort

### stable5

Support ALL ZiGate models known today and requires Domoticz 2020.x at minima
This is considered as a solid , reliable version.

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
