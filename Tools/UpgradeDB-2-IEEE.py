#!/usr/bin/python
# -*- coding: utf-8 -*-

# You need to change the path of Domoticz DB and DeviceList.txt 
# At the end of the migration, the DomoticzDB will be updated and the DeviceList.txt will be renamed into DeviceList-<hardrwareid>.txt
# Search for DomoDB and ZigateDB and update accordingly to your setup.
# Do a proper backup before starting

import sqlite3
import base64

global ClusterType
global DomoID
global IEEE


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
		ClusterType = base64.b64decode(vClusterType)
		ClusterType = ClusterType.decode("utf-8")
		ClusterType = '{ClusterType}'.format(ClusterType=ClusterType)
	elif kField == "Zigate" :
		vZigate = vField
		Zigate = eval (base64.b64decode(vZigate))
		if Zigate.get('IEEE') : IEEE = str(Zigate['IEEE'])
		else : IEEE =''
		if Zigate.get('DomoID') : DomoID = str(Zigate['DomoID'])
		else : DomoID = ''
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



### VARIABLES TO BE EDITED
DomoDB = "/var/lib/domoticz/domoticz.db"
ZigateDB = "/var/lib/domoticz/plugin/Domoticz-Zigate/DeviceList.txt"

#########################
conn = sqlite3.connect( DomoDB )

cursor = conn.cursor()

print("Retreive the HardwareID from Domoticz ".
for row in cursor.execute("""SELECT ID from hardware Where Extra="Zigate" """) :
	HardwareID = row[0]

cursor = conn.cursor()
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
				if s1 > 0 and newOptions[len(newOptions)-1] == ';' : newOptions+=";"
				if x.find(";") >0 :
					y = x.split(';', 2)
					for z in y :
						if s1 > 0 and not newOptions[len(newOptions)-1] == ';' : newOptions+=";"
						extract_fields( z )
				else : extract_fields( x )
		else : extract_fields( f )

	
	if s1 > 0 : 
		if newOptions[len(newOptions)-1] == ';' : newOptions = newOptions[0:len(newOptions)-2]
		newOptions.replace(';;',';')

	list = [ str(ID), str(deviceID) , str(IEEE), str(newOptions) , ClusterType ]
	tobeupdate.append( list )


print("Domoticz Database migration")
for ID, deviceID, IEEE, Options , ClusterType in tobeupdate :
	if IEEE != '' :
		print("---> Migrating Unit : " +str(ID) + " NWK_ID = " +str(deviceID) + " IEEE = " +str(IEEE) )
		cursor.execute('''UPDATE DeviceStatus SET DeviceID = ?, Options = ?  WHERE ID = ? and HardwareID=? ''', (IEEE, Options, ID, HardwareID))
	else :
		print("----===>Cannot migrate this device, you'll have to remove from Domotciz : " +str(ID) + " - DeviceID : "+str(deviceID) + " no IEEE found " )


# Now we need to Load DeviceList and add the ClusterType Information for each NWK@

# Load DevceList in memory
DeviceListName=ZigateDB
ListOfDevices = {}
with open( DeviceListName , 'r') as myfile2:
	print("DeviceList migration" +DeviceListName)
	for line in myfile2:
		(key, val) = line.split(":",1)
		key = key.replace(" ","")
		key = key.replace("'","")

		ListOfDevices[key] = eval(val)

		for  ID, deviceID, IEEE, Options , ClusterType in tobeupdate :
			if key == deviceID :
				print("---> Migrating Unit : " +str(ID) + " NWK_ID = " +str(deviceID) + " IEEE = " +str(IEEE) )
				if not ListOfDevices[key].get('IEEE') or IEEE == '' :
					print("---===> This entry doesn't have an IEEE " + str(key) + " " +str(IEEE) )
					del ListOfDevices[key]
					continue
				if IEEE != ListOfDevices[key]['IEEE'] :
					print("---===> This entry doesn't match IEEE" +str(key) +"/" +str(IEEE) + " versus " +str(ListOfDevices[key]['IEEE']) )
					del ListOfDevices[key]
					continue
				ListOfDevices[key]['ClusterType'] = str(ClusterType)
				if ListOfDevices[key].get('DomoID') :
					del ListOfDevices[key]['DomoID']
				ListOfDevices[key]['Version'] = '3'
			

# write the file down
with open( DeviceListName , 'wt') as file:
	for key in ListOfDevices :
		file.write(key + " : " + str(ListOfDevices[key]) + "\n")

conn.commit()
conn.close()
