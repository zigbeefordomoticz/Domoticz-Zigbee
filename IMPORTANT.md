# IMPORTANT : Release 6.x with embedded zigpy library

## ENglish

You have move to the release 6, following a git pull on beta branch or simply a git checkout beta

most likely the plugin won't start and you have somethink like that in the domoticz logs.

```log
Jan 14 14:25:24 rasp domoticz[30058]: 2022-01-14 14:25:24.816  Status: Zigate: Entering work loop.
Jan 14 14:25:24 rasp domoticz[30058]: 2022-01-14 14:25:24.817  Zigate: Worker thread started.
Jan 14 14:25:24 rasp domoticz[30058]: 2022-01-14 14:25:24.817  Status: Zigate: Started.
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.920  Error: Zigate: (ZigateZigpy) failed to load 'plugin.py', Python Path used was '/var/lib/domoticz/plugins/Domoticz-zigpy/:/usr/lib/python39.zip:/usr/lib/python3.9:/usr/lib/python3.9/lib-dynload:/usr/local/lib/python3.9/site-packages:/usr/lib/python3.9/site-packages'.
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate: Module Import failed, exception: 'ModuleNotFoundError'
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate: Module Import failed: ' Name: dns'
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate: Error Line details not available.
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate: Exception traceback:
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate:  ----> Line 104 in '/var/lib/domoticz/plugins/Domoticz-zigpy/plugin.py', function <module>
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate:  ----> Line 16 in '/var/lib/domoticz/plugins/Domoticz-zigpy/Modules/checkingUpdate.py', function <module>
```

This error message indicates that you are missing some important python libraries needed for the plugin

In order to solve this problem you must run the following command from the plugin directory ( Domoticz-Zigate or Domoticz-Zigbee is that is a recent installation)

run: `git submodule update --init --recursive`

Last you must known that starting now the command `git pull` to update the plugin is not enought and it is key to execute instead `git pull --recurse-submodules`

## FRançais

Vous etes sur la version 6 du plugin, probablement suite à un update de la branche beta, un récent changement de branche.

Il y a de forte chance que le plugin ne se lance pas et qu'un message de ce type soit dans les logs domoticz.

```log
Jan 14 14:25:24 rasp domoticz[30058]: 2022-01-14 14:25:24.816  Status: Zigate: Entering work loop.
Jan 14 14:25:24 rasp domoticz[30058]: 2022-01-14 14:25:24.817  Zigate: Worker thread started.
Jan 14 14:25:24 rasp domoticz[30058]: 2022-01-14 14:25:24.817  Status: Zigate: Started.
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.920  Error: Zigate: (ZigateZigpy) failed to load 'plugin.py', Python Path used was '/var/lib/domoticz/plugins/Domoticz-zigpy/:/usr/lib/python39.zip:/usr/lib/python3.9:/usr/lib/python3.9/lib-dynload:/usr/local/lib/python3.9/site-packages:/usr/lib/python3.9/site-packages'.
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate: Module Import failed, exception: 'ModuleNotFoundError'
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate: Module Import failed: ' Name: dns'
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate: Error Line details not available.
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate: Exception traceback:
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate:  ----> Line 104 in '/var/lib/domoticz/plugins/Domoticz-zigpy/plugin.py', function <module>
Jan 14 14:25:25 rasp domoticz[30058]: 2022-01-14 14:25:25.921  Error: Zigate:  ----> Line 16 in '/var/lib/domoticz/plugins/Domoticz-zigpy/Modules/checkingUpdate.py', function <module>
```

Ce message d'erreyr indique qu'il manque des libraries python pour le plugin.
Pour regler ce problème vous devez executer la commande suivante depuis le repertoire du plugin § domoticz/plugins/Domoticz-Zigate ou domoticz/plugins/Domoticz-Zigbee)

executez: `git submodule update --init --recursive`

Notez également et cela est important que dorénavant la commande `git pull` n'est pas suffisante pour la mise à jour du plugin, par conséquent il est clef d'executer la commande suivante `git pull --recurse-submodules`
