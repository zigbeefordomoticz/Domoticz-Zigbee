# Zigate Plugin for Domoticz

[Zigate](zigate.fr) Python Plugin for Domoticz home automation.

## Installation

Python version 3.4 or higher required & Domoticz version 3.87xx or greater.

To install:

- Go in your Domoticz directory using a command line and open the plugins directory.
- Run: `git clone https://github.com/sasu-drooz/Domoticz-Zigate.git`
- Restart Domoticz.

In the web UI, navigate to the Hardware page. In the hardware dropdown there will be an entry called "Zigate plugin".

## Updating

To update:

- Go in your Domoticz directory using a command line and open the plugins directory then the Domoticz-Zigate-Plugin directory.
- Run: `git pull`
- Restart Domoticz.

## Configuration

In Domoticz, go in Setup>Hardware, in Type select "Zigate plugin".

![](https://github.com/sasu-drooz/Domoticz-Zigate/blob/dev2/images/Zigate-Configuration.png)

- Select a name for your hardware (here it's zigate)
- Select your model (USB or Wifi)
  - if Wifi enter IP of your Zigate, keep port to 9999 (not possible to change this on the zigate yet)
  - if USB, select your device port (always /dev/ttyUSBx under linux, COMx for Windows)
- Select ZigBee channel (by default it's set to 11, but if you have pluzzy device, ou need to set it to 19, see [zigate.fr](zigate.fr) for more information)
- Set Permit join time, between 0 (for no) , 1 and 254 ( for 1 to 254 cycles) and 255 (always)  to Permit join devices on plugin or Domoticz start
- Set Erase Persistent Data to true if you want to clean Zigate memory (devices know list in zigate). Be CARREFUL, as you might create some discrapancy between the Zigate HW and the Domoticz Devices.
- Set Debug to true if you have trouble

## How it's work

Your Device need to send a device announce while zigate is in permit join mode.

Then your zigate will ask your device for this End Point. Plugin will wait until your device answer or send an Active End Point Request again after 10 Heartbeat without answer or enough information to create device in Domoticz

If we receive an Active Endpoint Request response, then plugin will ask for a Simple Descriptor Request for each End Point.

Then plugin should have enough information to create Domoticz Device for this Device

## Setup new device

To add a new device your zigate must be in Permit Join mode

### Ikea Tradfri Bulb

Just turn off/on 6 times your bulb (not with ikea remote, shut off then on power). Your bulb will send a device announce to your zigate, then your zigate will ask some information to your bulb to know wich model it is and add it to Domoticz. If your model is not in DeviceConf.txt it should take a little longer but it will be automatically add as soon as the zigate will have information need foor this.

![](https://github.com/sasu-drooz/Domoticz-Zigate/blob/dev2/images/Zigate-Bulb-Device.png)

You should find between 1 and 3 new devices in your Domoticz Device list :

- simple switch, to turn on or off your bulb
- Level Control (LvlControl), to set brigthness level of your bulb
- Color Control (ColorControl), to set color of your bulb

### Xiaomi ZigBee Device

Push reset button while your device blink 3 times quickly, then your device will be announce to your zigate and it will be add to your device list

#### support Xiaomi know device are :

- Motion sensor (v1 and v2)
- Door/window sensor 
- Temperature/humidity sensor
- Weather sensor (Temperatur/humidity/barometer)
- Water sensor
- Single Switch
- Dual Switch
- Smoke sensor

### Other Zigbee device
 zigbee device should be add do domoticz after zigate will have receive a device announce.

