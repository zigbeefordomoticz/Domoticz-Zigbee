#!/usr/bin/env python3
# coding: utf-8 -*-
#

import Domoticz

import z_var		  # Global variables


def upgrade_v2( self, Devices ) :

	nbdev = 0
	upgradedone = False
	for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
		upgradeneeded = False
		
		nbdev = nbdev + 1
		Domoticz.Debug("Upgrading - oldDevicesOptions = " +str(Devices[x].Name) + " Options = "  + str(Devices[x].Options) )
		newDevicesOptions=dict(Devices[x].Options)

		if Devices[x].Options.get('TypeName') :
			upgradedone = True
			ugradeneeded = False
			oldTypeName = newDevicesOptions['TypeName']

			# Remove 'TypeName' and add 'ClusterType'
			del newDevicesOptions['TypeName']
			newDevicesOptions['ClusterType'] = oldTypeName

		ZigateV2 = eval(newDevicesOptions['Zigate'])
		Domoticz.Debug("Upgrading - oldDevicesOptions['Zigate'] = " +str(Devices[x].Name) + " Zigate = "  + str(ZigateV2) )

		if ZigateV2.get('Version') != "2" :
			upgradedone = True
			ugradeneeded = False
			ZigateV2['Version'] = "2"
			newDevicesOptions['Zigate'] = ZigateV2

		if upgradeneeded :
			Domoticz.Log("Upgrading - newDevicesOptions = " +str(Devices[x].Name) + str(newDevicesOptions) )
			Domoticz.Log("Upgrading " +str(Devices[x].Name) + " to version 2 with Options['Zigate']= " +str(ZigateV2) )
			nValue = Devices[x].nValue
			sValue = Devices[x].sValue

			Domoticz.Status("Upgrading " +str(Devices[x].Name) + " to version 2" )
			Devices[x].Update(nValue=int(nValue), sValue=str(sValue), Options={}, SuppressTriggers=True )
			Devices[x].Update(nValue=int(nValue), sValue=str(sValue), Options=newDevicesOptions, SuppressTriggers=True )

		else:
			Domoticz.Debug("NOT Upgrading " +str(Devices[x].Name) + " Options ="  + str(Devices[x].Options) )

	if upgradedone :
		Domoticz.Log("Upgrade of Zigate structure to V2 completed. " + str(nbdev) + " devices updated")
	else:
		Domoticz.Status("Zigate Structure V2")
			
