# Xiaomi Aqara Cube


The remote commande Aqara cube is fully operational on the developement branch. 
The outcome of the pairing process is the creation of a Switch Selector. The different states of the Seelctors are :
- Shake
- Wakeup ( It is more a transition state, so there is weak chance to get it on the selector. However if you want to use Lua script or DZevent it will trigger an event).
- Drop
- 90°
- 180°
- Push
- Tap ( You need to double tab teh cube on the table)
- Rotation (horinzotal)


## Pairing process

* Make sure that the Zigate is in Joint Permit mode (via the plugin menu)
* In order to pair your Cube, you need to open the battery door and you'll find a "button". Press it 5 seconds until the led is blinking. Then release. The pairing process should start.

## Switch Selector 

By default the Switch Selector created include the Short Address (Domoticz Id) of the Cube
![]( https://github.com/sasu-drooz/Domoticz-Zigate/blob/developement/images/Aqara-Cub.PNG )

In the Setup -> Device section of Domoticz you'll find the device for which Signal Quality and Battery Level will be given
