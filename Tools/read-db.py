#!/usr/bin/python
# -*- coding: utf-8 -*-




import sqlite3
import base64

global ClusterType
global DomoID
global IEEE
global Zigate


def extract_fields( partOptions ) :
	global ClusterType
	global DomoID
	global IEEE
	global Zigate

	kField, vField = partOptions.split(':', 2)

	if kField == "ClusterType" or kField == "TypeName" :
		vClusterType = vField
		ClusterType = str( base64.b64decode(vClusterType) )

	if kField == "Zigate" :
		vZigate = vField
		Zigate = eval (base64.b64decode(vZigate))
		if Zigate.get('IEEE') :
			IEEE = str(Zigate['IEEE'])
		else :
			IEEE =''
		if Zigate.get('DomoID') :
			DomoID = str(Zigate['DomoID'])
		else :
			DomoID = ''

	
	


HardwareID = 0
DomoID = ''
IEEE = ''
ClusterType =''
Zigate =''

conn = sqlite3.connect('/var/lib/domoticz/domoticz.db')

cursor = conn.cursor()

for row in cursor.execute("""SELECT ID from hardware Where Extra="Zigate" """) :
	HardwareID = row[0]

cursor = conn.cursor()
print("| DeviceID | CusterType | IEEE | DomoID |")
for row in cursor.execute("""SELECT DeviceID, Options From DeviceStatus Where  HardwareID=? """, (HardwareID,) ) :

	deviceID = row[0]
	Options = str(row[1])

	sOptions = Options.split(';', 2)
	for f in sOptions :
		if f.find(";") >0 :
			f2 = f.split(';', 2)
			for x in f2 :
				if x.find(";") >0 :
					y = x.split(';', 2)
					for z in y :
						extract_fields( z )
				else :
					extract_fields( x )
		else :
			extract_fields( f )

	print("|" +str(deviceID) +" | " + str(ClusterType) + " | " + str(IEEE) + " | " +str(DomoID) +" |" )



conn.close()
