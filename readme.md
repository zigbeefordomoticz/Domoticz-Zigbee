# Zigate Plugin for Domoticz


[Zigate](https://zigate.fr Python Plugin for Domoticz home automation.

For information around the Zigate Plugin, please refer to :
* https://github.com/sasu-drooz/Domoticz-Zigate/wiki for informations 

## About release channels

In order to provide stability and also provide more recent developement, Zigate plugin has the following channels

### stable
This is considered as a solid , reliable version.

### beta

We can open the beta channel to provide early version and to stabilize he version priori t o be move to the stable channel

### dev

This is where developement are under go. This is not a reliable version and could be buggy and even not working depending on the stage of integration we are.
This branch is only for users whom known exactly what they are doing.

### master ( deprecated )
This channel is not maintained anymore and is not compatible to the most recent version.
Moving from this channel to the other will required either ar restart from scratch or to do an upgrade of the Domoticz and Zigate database.

## How to switch from one channel to the other

`git pull`

`git checkout stable  // will move you to the stable channel`

`git checkout beta    // will move you to the beta channel`
