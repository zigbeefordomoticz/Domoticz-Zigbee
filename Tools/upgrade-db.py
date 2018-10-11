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
	global newOptions
	global s1

	kField, vField = partOptions.split(':', 2)

	if kField == "ClusterType" or kField == "TypeName" :
		vClusterType = vField
		ClusterType = str( base64.b64decode(vClusterType) )
	elif kField == "Zigate" :
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
	else :
		newOptions += kField
		newOptions += ":" 
		newOptions += vField
		s1 = 1

	return
	


newOptions = ''
HardwareID = 0
DomoID = ''
IEEE = ''
ClusterType =''
Zigate =''
tobeupdate = []

conn = sqlite3.connect('base.db')

cursor = conn.cursor()

for row in cursor.execute("""SELECT ID from hardware Where Extra="Zigate" """) :
	HardwareID = row[0]

cursor = conn.cursor()
print("| DeviceID | CusterType | IEEE | DomoID |")
for row in cursor.execute("""SELECT ID, DeviceID, Options From DeviceStatus Where  HardwareID=? """, (HardwareID,) ) :

	ID = row[0]
	deviceID = row[1]
	Options = str(row[2])

	sOptions = Options.split(';', 2)
	newOptions =''
	s1=0
	for f in sOptions :
		if s1 > 0 : newOptions+=";"
		if f.find(";") >0 :
			f2 = f.split(';', 2)
			for x in f2 :
				if s1 > 0 and newOptions[len(newOptions)-1] == ';' :
					newOptions+=";"
				if x.find(";") >0 :
					y = x.split(';', 2)
					for z in y :
						if s1 > 0 and not newOptions[len(newOptions)-1] == ';' :
							newOptions+=";"
						extract_fields( z )
				else :
					extract_fields( x )
		else :
			extract_fields( f )

	
	if s1 > 0 : 
		if newOptions[len(newOptions)-1] == ';' : newOptions = newOptions[0:len(newOptions)-2]
		newOptions.replace(';;',';')

	print("ID = " + str(ID) + "DeviceID = " +str(deviceID) + " newOptions = " + newOptions)

	#print("|" +str(ID) + "|" +str(deviceID) +" | " + str(ClusterType) + " | " + str(IEEE) + " | " +str(DomoID) +" |" +str(newOptions) + " | ")

	list = [ str(ID), str(deviceID) , str(IEEE), str(newOptions) ]
	tobeupdate.append( list )


for ID, deviceID, IEEE, Options in tobeupdate :
	print("|" +str(ID) + "|" +str(deviceID) +" | " + str(ClusterType) + " | " + str(IEEE) + " | " +str(DomoID) +" |" +str(Options) + " | ")

	cursor.execute('''UPDATE DeviceStatus SET DeviceID = ?, Options = ?  WHERE ID = ? and HardwareID=? ''', (IEEE, Options, ID, HardwareID))

conn.commit()


for row in cursor.execute("""SELECT ID, DeviceID, Options From DeviceStatus Where  HardwareID=? """, (HardwareID,) ) :
	print(row )

conn.close()
