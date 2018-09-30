#!/usr/bin/env python3
# coding: utf-8 -*-
#

import Domoticz

import z_var		  # Global variables


def upgrade_v2( self, Devices ) :

	nbdev = 0
	upgradedone = False
	for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
		if Devices[x].Options.get('TypeName') :
			nbdev = nbdev + 1
			upgradedone = True
			Domoticz.Debug("Upgrading - oldDevicesOptions = " +str(Devices[x].Name) + " Options = "  + str(Devices[x].Options) )
			oldDevicesOptions=dict(Devices[x].Options)
			oldTypeName = oldDevicesOptions['TypeName']

			if str(Devices[x].Options.get('LevelActions')) and str(Devices[x].Options.get('Zigate')) :
				ZigateV2=eval(oldDevicesOptions['Zigate'])
				ZigateV2['Version'] = "2"
				newDevicesOptions = {"LevelActions":str(Devices[x].Options.get('LevelActions')), "LevelNames":str(Devices[x].Options.get('LevelNames')), "LevelOffHidden":str(Devices[x].Options.get('LevelOffHidden')), "SelectorStyle":str(Devices[x].Options.get('SelectorStyle')), "Zigate":str(Devices[x].Options.get('Zigate')), "ClusterType":oldTypeName}

			elif str(Devices[x].Options.get('Zigate')):
				ZigateV2=eval(oldDevicesOptions['Zigate'])
				ZigateV2['Version'] = "2"
				newDevicesOptions = { "Zigate":str(Devices[x].Options.get('Zigate')), "ClusterType":oldTypeName} 

			nValue = Devices[x].nValue
			sValue = Devices[x].sValue

			Domoticz.Log("Upgrading - newDevicesOptions = " +str(Devices[x].Name) + str(newDevicesOptions) )
			Domoticz.Status("Upgrading " +str(Devices[x].Name) + " to version 2" )
			Domoticz.Debug("Upgrading " +str(Devices[x].Name) + " to version 2 with Options['Zigate']= " +str(ZigateV2) )

			Devices[x].Update(nValue=int(nValue), sValue=str(sValue), Options={}, SuppressTriggers=True )

			Devices[x].Update(nValue=int(nValue), sValue=str(sValue), Options=newDevicesOptions, SuppressTriggers=True )

		else:
			Domoticz.Debug("NOT Upgrading " +str(Devices[x].Name) + " Options ="  + str(Devices[x].Options) )

	if upgradedone :
		Domoticz.Status("Upgrade of Zigate structure to V2 completed. " + str(nbdev) + " devices updated")
	else:
		Domoticz.Status("Zigate Structure V2")
			
