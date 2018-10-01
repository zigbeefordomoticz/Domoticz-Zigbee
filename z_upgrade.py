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
			newDevicesOptions=dict(Devices[x].Options)
			oldTypeName = newDevicesOptions['TypeName']

			# Remove 'TypeName' and add 'ClusterType'
			del newDevicesOptions['TypeName']
			newDevicesOptions['ClusterType'] = oldTypeName

			ZigateV2 = eval(newDevicesOptions['Zigate'])
			Domoticz.Log("Upgrading - oldDevicesOptions['Zigate'] = " +str(Devices[x].Name) + " Zigate = "  + str(ZigateV2) )
			ZigateV2['Version'] = 2
			newDevicesOptions['Zigate'] = ZigateV2

			Domoticz.Log("Upgrading " +str(Devices[x].Name) + " to version 2 with Options['Zigate']= " +str(ZigateV2) )
			
			Domoticz.Log("Upgrading - newDevicesOptions = " +str(Devices[x].Name) + str(newDevicesOptions) )
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
			
