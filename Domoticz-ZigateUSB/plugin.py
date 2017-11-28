# Zigate Python Plugin
#
# Author: zaraki673
#
"""
<plugin key="ZigateUSB" name="Zigate USB plugin" author="zaraki673" version="1.0.5" wikilink="http://www.domoticz.com/wiki/plugins/zigate.html" externallink="https://www.zigate.fr/">
	<params>
		<param field="SerialPort" label="Serial Port" width="150px" required="true" default=""/>
		<param field="Mode6" label="Debug" width="75px">
			<options>
				<option label="True" value="Debug"/>
				<option label="False" value="Normal"  default="true" />
			</options>
		</param>
	</params>
</plugin>
"""
import Domoticz
import binascii
import time

class BasePlugin:
	enabled = False

	def __init__(self):
		return

	def onStart(self):
		Domoticz.Log("onStart called")
		global ReqRcv
		global SerialConn
		if Parameters["Mode6"] == "Debug":
			Domoticz.Debugging(1)
		SerialConn = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None", Address=Parameters["SerialPort"], Baud=115200)
		SerialConn.Connect()
		ReqRcv=''


	def onStop(self):
		Domoticz.Log("onStop called")

	def onConnect(self, Connection, Status, Description):
		Domoticz.Log("onConnect called")
		global isConnected
		if (Status == 0):
			isConnected = True
			Domoticz.Log("Connected successfully to: "+Parameters["SerialPort"])
			ZigateConf()
		else:
			Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["SerialPort"])
			Domoticz.Debug("Failed to connect ("+str(Status)+") to: "+Parameters["SerialPort"]+" with error: "+Description)
		return True

	def onMessage(self, Connection, Data):
		Domoticz.Log("onMessage called")
		global Tmprcv
		global ReqRcv
		Tmprcv=binascii.hexlify(Data).decode('utf-8')
		if Tmprcv.find('03') != -1 and len(ReqRcv+Tmprcv[:Tmprcv.find('03')+2])%2==0 :### fin de messages detecter dans Data
			ReqRcv+=Tmprcv[:Tmprcv.find('03')+2] #
			try :
				if ReqRcv.find("0301") == -1 : #verifie si pas deux messages coller ensemble
					ZigateDecode(ReqRcv) #demande de decodage de la trame recu
					ReqRcv=Tmprcv[Tmprcv.find('03')+2:]  # traite la suite du tampon
				else : 
					ZigateDecode(ReqRcv[:ReqRcv.find("0301")+2])
					ZigateDecode(ReqRcv[ReqRcv.find("0301")+2:])
					ReqRcv=Tmprcv[Tmprcv.find('03')+2:]
			except :
				Domoticz.Debug("onMessage - effacement de la trame suite a une erreur de decodage : " + ReqRcv)
				ReqRcv = Tmprcv[Tmprcv.find('03')+2:]  # efface le tampon en cas d erreur
		else : # while end of data is receive
			ReqRcv+=Tmprcv
		return

	def onCommand(self, Unit, Command, Level, Hue):
		Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

	def onDisconnect(self, Connection):
		Domoticz.Log("onDisconnect called")

	def onHeartbeat(self):
#		Domoticz.Log("onHeartbeat called")
		ResetDevice("lumi.sensor_motion.aq2")
		ResetDevice("lumi.sensor_motion")
		if (SerialConn.Connected() != True):
			SerialConn.Connect()
		return True

global _plugin
_plugin = BasePlugin()

def onStart():
	global _plugin
	_plugin.onStart()

def onStop():
	global _plugin
	_plugin.onStop()

def onConnect(Connection, Status, Description):
	global _plugin
	_plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
	global _plugin
	_plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
	global _plugin
	_plugin.onCommand(Unit, Command, Level, Hue)

def onDisconnect(Connection):
	global _plugin
	_plugin.onDisconnect(Connection)

def onHeartbeat():
	global _plugin
	_plugin.onHeartbeat()

	# Generic helper functions
def DumpConfigToLog():
	for x in Parameters:
		if Parameters[x] != "":
			Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
	Domoticz.Debug("Device count: " + str(len(Devices)))
	for x in Devices:
		Domoticz.Debug("Device:		   " + str(x) + " - " + str(Devices[x]))
		Domoticz.Debug("Device ID:	   '" + str(Devices[x].ID) + "'")
		Domoticz.Debug("Device Name:	 '" + Devices[x].Name + "'")
		Domoticz.Debug("Device nValue:	" + str(Devices[x].nValue))
		Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
		Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
	return

def ZigateConf():

	################### ZiGate - set channel 11 ##################
	sendZigateCmd("0021","0004", "00000800")

	################### ZiGate - Set Type COORDINATOR#################
	sendZigateCmd("0023","0001","00")
	
	################### ZiGate - start network##################
	sendZigateCmd("0024","0000","")

	################### ZiGate - discover mode 255sec ##################
	sendZigateCmd("0049","0004","FFFCFE00")

def ZigateDecode(Data):  # supprime le transcodage
	Domoticz.Debug("ZigateDecode - decodind data : " + Data)
	Out=""
	Outtmp=""
	Transcode = False
	for c in Data :
		Outtmp+=c
		if len(Outtmp)==2 :
			if Outtmp == "02" :
				Transcode=True
			else :
				if Transcode == True:
					Transcode = False
					if Outtmp[0]=="1" :
						Out+="0"
					else :
						Out+="1"
					Out+=Outtmp[1]
					#Out+=str(int(str(Outtmp)) - 10)
				else :
					Out+=Outtmp
			Outtmp=""
	ZigateRead(Out)

def ZigateEncode(Data):  # ajoute le transcodage
	Domoticz.Debug("ZigateDecode - Encodind data : " + Data)
	Out=""
	Outtmp=""
	Transcode = False
	for c in Data :
		Outtmp+=c
		if len(Outtmp)==2 :
			if Outtmp[0] == "1" :
				if Outtmp[1] == "0" :
					Outtmp="0200"
					Out+=Outtmp
				else :
					Out+=Outtmp
			elif Outtmp[0] == "0" :
				Out+="021" + Outtmp[1]
			else :
				Out+=Outtmp
			Outtmp=""
	Domoticz.Debug("Transcode in : " + str(Data) + "  / out :" + str(Out) )
	return Out

def sendZigateCmd(cmd,length,datas) :
	if datas =="" :
		lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(getChecksum(cmd,length,"0")) + "03" 
	else :
		lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(getChecksum(cmd,length,datas)) + str(ZigateEncode(datas)) + "03"   
	Domoticz.Debug("sendZigateCmd - Comand send : " + str(lineinput))
	SerialConn.Send(bytes.fromhex(str(lineinput)))	


	
def ZigateRead(Data):
	Domoticz.Debug("ZigateRead - decoded data : " + Data)
#Trame serie
#
#0	 1	 2	 3	 4 	 5 	 6	 7	 8 	 9	 10	 11	 12	14 16 18 20 22 24 26 28 30 32 34 36 38 ...
#1		|2		|3		|4		|5		|6		|7  											|n+8	|n+9
#0x01	|		|		|n				|		|												|		|0x03
#Start	| MSG TYPE		|LENGTH			|CHKSM	|DATA											|RSSI	|STOP
#
#01		 81		 02		 00		 0f		 06		 b9 cd 4d 01 04 03 00 10 00 29 00 02 27 3a		 93		 03
#01		 81		 02		 00		 0f		 89		 50 2a 61 01 04 02 00 00 00 29 00 02 07 fa		 cf 	 03
#01		 81		 02		 00		 0e		 c6		 c0 cd 4d 01 04 03 00 14 00 28 00 01 ff 		 cf 	 03
#01		 81		 02		 00		 0f		 f9		 d6 cd 4d 01 04 05 00 00 00 21 00 02 16 d9 		 cf	 	 03
#01		 81		 02		 00		 32		 c3		 bd cd 4d 01 00 00 ff 01 00 42 00 25 01 21 bd 0b 04 21 a8 13 05 21 06 00 06 24 01 00 00 00 00 64 29 75 07 65 21 22 16 66 2b b0 89 01 00 0a 21 00 00 	 cf		 03
#01		 81		 02		 00		 0e		 98		 c7	cd 4d 01 04 03 00 14 00 28 00 01 ff 		 96		 03
#01		 81		 02		 00		 0F		 AB		 02 6F 2F 01 04 02 00 00 00 29 00 02 09 89 		 C9		 03
#01		 80		 45		 00		 07		 23		 290007780101									 b7		 03
#01		 80		 43		 02		 10		 1e		 021f3302106a0217160211021102145f0211021102140210021002100213ffff0210021602130210021002100213ffff02100216	 c6		 03
#01		 80		 43		 00	 	 1e		 8c		 42008439160101045f01010400000003ffff00060300000003ffff0006				e4 		03

	MsgType=Data[2:6]
	MsgData=Data[12:len(Data)-4]
	MsgRSSI=Data[len(Data)-4:len(Data)-2]
	MsgLength=Data[6:10]
	MsgCRC=Data[10:12]
	Domoticz.Debug("ZigateRead - Message Type : " + MsgType + ", Data : " + MsgData + ", RSSI : " + MsgRSSI + ", Length : " + MsgLength + ", Checksum : " + MsgCRC)


	if str(MsgType)=="004d":  # Device announce
		MsgSrcAddr=MsgData[0:4]
		MsgIEEE=MsgData[4:20]
		MsgMacCapa=MsgData[20:22]

		Domoticz.Debug("reception Device announce : Source :" + MsgSrcAddr + ", IEEE : "+ MsgIEEE + ", Mac capa : " + MsgMacCapa)
		
		# tester si le device existe deja dans la base domoticz
		#sendZigateCmd("0045","0002", str(MsgSrcAddr))    # Envoie une demande Active Endpoint request
		#SerialConn.Send(bytes.fromhex(lineinput))
		
	elif str(MsgType)=="00d1":  #
		Domoticz.Debug("reception Touchlink status : " + Data)

	elif str(MsgType)=="8000":  # Status
		MsgDataLenght=MsgData[0:4]
		MsgDataStatus=MsgData[4:6]
		if MsgDataStatus=="00" :
			MsgDataStatus="Success"
		elif MsgDataStatus=="01" :
			MsgDataStatus="Incorrect Parameters"
		elif MsgDataStatus=="02" :
			MsgDataStatus="Unhandled Command"
		elif MsgDataStatus=="03" :
			MsgDataStatus="Command Failed"
		elif MsgDataStatus=="04" :
			MsgDataStatus="Busy"
		elif MsgDataStatus=="05" :
			MsgDataStatus="Stack Already Started"
		else :
			MsgDataStatus="ZigBee Error Code "+ MsgDataStatus
		MsgDataSQN=MsgData[6:8]
		if int(MsgDataLenght,16) > 2 :
			MsgDataMessage=MsgData[8:len(MsgData)]
		else :
			MsgDataMessage=""
		
		Domoticz.Debug("ZigateRead - MsgType 8000 - reception status : " + MsgDataStatus + ", SQN : " + MsgDataSQN + ", Message : " + MsgDataMessage)

	elif str(MsgType)=="8001":  # Log
		MsgLogLvl=MsgData[0:2]
		MsgDataMessage=MsgData[2:len(MsgData)]
		
		Domoticz.Debug("reception log Level 0x: " + MsgLogLvl + "Message : " + MsgDataMessage)

	elif str(MsgType)=="8002":  #
	
		Domoticz.Debug("reception Data indication : " + Data)

	elif str(MsgType)=="8003":  #
	
		Domoticz.Debug("reception Liste des cluster de l'objet : " + Data)

	elif str(MsgType)=="8004":  #
	
		Domoticz.Debug("reception Liste des attributs de l'objet : " + Data)

	elif str(MsgType)=="8005":  #
	
		Domoticz.Debug("reception Liste des commandes de l'objet : " + Data)

	elif str(MsgType)=="8006":  #

		Domoticz.Debug("reception Non factory new restart : " + Data)

	elif str(MsgType)=="8007":  #
	
		Domoticz.Debug("reception Factory new restart : " + Data)

	elif str(MsgType)=="8010":  # Version
		MsgDataApp=MsgData[0:4]
		MsgDataSDK=MsgData[4:8]
		
		Domoticz.Debug("reception Version list : " + Data)

	elif str(MsgType)=="8014":  #
	
		Domoticz.Debug("reception Permit join status response : " + Data)

	elif str(MsgType)=="8024":  #
	
		Domoticz.Debug("reception Network joined /formed : " + Data)

	elif str(MsgType)=="8028":  #
	
		Domoticz.Debug("reception Authenticate response : " + Data)

	elif str(MsgType)=="8029":  #
	
		Domoticz.Debug("reception Out of band commissioning data response : " + Data)

	elif str(MsgType)=="802b":  #
	
		Domoticz.Debug("reception User descriptor notify : " + Data)

	elif str(MsgType)=="802c":  #
	
		Domoticz.Debug("reception User descriptor response : " + Data)


	elif str(MsgType)=="8030":  #
	
		Domoticz.Debug("reception Bind response : " + Data)

	elif str(MsgType)=="8031":  #
	
		Domoticz.Debug("reception Unbind response : " + Data)

	elif str(MsgType)=="8034":  #
	
		Domoticz.Debug("reception Coplex Descriptor response : " + Data)

	elif str(MsgType)=="8040":  #
	
		Domoticz.Debug("reception Network address response : " + Data)

	elif str(MsgType)=="8041":  #
	
		Domoticz.Debug("reception IEEE address response : " + Data)

	elif str(MsgType)=="8042":  #
	
		Domoticz.Debug("reception Node descriptor response : " + Data)

	elif str(MsgType)=="8043":  # Simple Descriptor Response
		MsgDataSQN=MsgData[0:2]
		MsgDataStatus=MsgData[2:4]
		MsgDataShAddr=MsgData[4:8]
		MsgDataLenght=MsgData[8:10]
			# if int(MsgDataLenght,16)>0 :
				# MsgDataEp=MsgData[8:10]
				
		Domoticz.Debug("reception Simple descriptor response : SQN : " + MsgDataSQN + ", Status " + MsgDataStatus + ", short Addr " + MsgDataShAddr + ", Lenght " + MsgDataLenght)

	elif str(MsgType)=="8044":  #
	
		Domoticz.Debug("reception Power descriptor response : " + Data)

	elif str(MsgType)=="8045":  # Active Endpoints Response
		MsgDataSQN=MsgData[0:2]
		MsgDataStatus=MsgData[2:4]
		MsgDataShAddr=MsgData[4:8]
		MsgDataEpCount=MsgData[8:10]
		MsgDataEPlist=MsgData[10:len(MsgData)]
		
		Domoticz.Debug("reception Active endpoint response : SQN : " + MsgDataSQN + ", Status " + MsgDataStatus + ", short Addr " + MsgDataShAddr + ", EP count " + MsgDataEpCount + ", Ep list " + MsgDataEPlist)
		
		#OutEPlist=""
		#for i in MsgDataEPlist :
		#	OutEPlist+=i
		#	if len(OutEPlist)==2 :
		#		Domoticz.Debug("Envoie une demande Simple Descriptor request pour avoir les informations du EP :" + OutEPlist + ", du device adresse : " + MsgDataShAddr)
		#		sendZigateCmd("0043","0004", str(MsgDataShAddr)+str(OutEPlist))    # Envoie une demande Simple Descriptor request pour avoir les informations du EP
		#		OutEPlisttmp=""
		

	elif str(MsgType)=="8046":  #
	
		Domoticz.Debug("reception Match descriptor response : " + Data)

	elif str(MsgType)=="8047":  #
	
		Domoticz.Debug("reception Management leave response : " + Data)

	elif str(MsgType)=="8048":  #
	
		Domoticz.Debug("reception Leave indication : " + Data)

	elif str(MsgType)=="804a":  #

	
		Domoticz.Debug("reception Management Network Update response : " + Data)

	elif str(MsgType)=="804b":  #
	
		Domoticz.Debug("reception System server discovery response : " + Data)

	elif str(MsgType)=="804e":  #

		Domoticz.Debug("reception Management LQI response : " + Data)

	elif str(MsgType)=="8060":  #
	
		Domoticz.Debug("reception Add group response : " + Data)

	elif str(MsgType)=="8061":  #
	
		Domoticz.Debug("reception Viex group response : " + Data)

	elif str(MsgType)=="8062":  #
	
		Domoticz.Debug("reception Get group Membership response : " + Data)

	elif str(MsgType)=="8063":  #
	
		Domoticz.Debug("reception Remove group response : " + Data)

	elif str(MsgType)=="80a0":  #

	
		Domoticz.Debug("reception View scene response : " + Data)

	elif str(MsgType)=="80a1":  #
	
		Domoticz.Debug("reception Add scene response : " + Data)

	elif str(MsgType)=="80a2":  #
	
		Domoticz.Debug("reception Remove scene response : " + Data)

	elif str(MsgType)=="80a3":  #
	
		Domoticz.Debug("reception Remove all scene response : " + Data)

	elif str(MsgType)=="80a4":  #
	
		Domoticz.Debug("reception Store scene response : " + Data)

	elif str(MsgType)=="80a6":  #
	
		Domoticz.Debug("reception Scene membership response : " + Data)

	elif str(MsgType)=="8100":  #
	
		Domoticz.Debug("reception Real individual attribute response : " + Data)

	elif str(MsgType)=="8101":  # Default Response
		MsgDataSQN=MsgData[0:2]
		MsgDataEp=MsgData[2:4]
		MsgClusterId=MsgData[4:8]
		MsgDataCommand=MsgData[8:10]
		MsgDataStatus=MsgData[10:12]
		
		Domoticz.Debug("reception Default response : SQN : " + MsgDataSQN + ", EP : " + MsgDataEp + ", Cluster ID : " + MsgClusterId + " , Command : " + MsgDataCommand+ ", Status : " + MsgDataStatus)

	elif str(MsgType)=="8102":  # Report Individual Attribute response
		MsgSQN=MsgData[0:2]
		MsgSrcAddr=MsgData[2:6]
		MsgSrcEp=MsgData[6:8]
		MsgClusterId=MsgData[8:12]
		MsgAttrID=MsgData[12:16]
		MsgAttType=MsgData[16:20]
		MsgAttSize=MsgData[20:24]
		MsgClusterData=MsgData[24:len(MsgData)]

		Domoticz.Debug("ZigateRead - MsgType 8102 - reception data : " + Data + " ClusterID : " + MsgClusterId + " Attribut ID : " + MsgAttrID + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp)
				
		if MsgClusterId=="0000" :
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception heartbeat (0000) : " + MsgClusterData)
			if MsgAttrID=="ff01" :
				MsgBattery=MsgClusterData[4:8]
				try :
					ValueBattery='%s%s' % (str(MsgBattery[2:4]),str(MsgBattery[0:2]))
					ValueBattery=round(int(ValueBattery,16)/10/3)
					Domoticz.Debug("ZigateRead - MsgType 8102 - reception batteryLVL (0000) : " + str(ValueBattery) + " pour le device addr : " +  MsgSrcAddr)
					UpdateBattery(MsgSrcAddr,ValueBattery)
				except :
					Domoticz.Debug("ZigateRead - MsgType 8102 - reception batteryLVL (0000) : erreur de lecture pour le device addr : " +  MsgSrcAddr)
			
			if MsgAttrID=="0005" :
				Type=binascii.unhexlify(MsgClusterData).decode('utf-8')
				Domoticz.Debug("ZigateRead - MsgType 8102 - reception heartbeat (0000) - MsgAttrID (0005) - Type de Device : " + Type)
				IsCreated=False
				x=0
				nbrdevices=0
				for x in Devices:
					#Domoticz.Debug("ZigateRead - MsgType 8102 - reception heartbeat (0000) - MsgAttrID (0005) - Type de Device : " + Type + " read Devices id : " + x )
					#DOptions = Devices[x].Options
					if Devices[x].DeviceID == str(MsgSrcAddr) : #and DOptions['devices_type'] == str(Type) and DOptions['Ep'] == str(MsgSrcEp) :
						IsCreated = True
						Domoticz.Debug("Devices already exist. Unit=" + str(x))
					if IsCreated == False :
						nbrdevices=x
				if IsCreated == False :
					nbrdevices=nbrdevices+1
					Domoticz.Debug("ZigateRead - MsgType 8102 - reception heartbeat (0000) - MsgAttrID (0005) - Type de Device : " + Type + " Device not found, creating device " )
					CreateDomoDevice(nbrdevices,MsgSrcAddr,MsgSrcEp,Type)
				
			
		elif MsgClusterId=="0006" :  # General: On/Off xiaomi

			#SetSwitch(MsgSrcAddr,MsgSrcEp,MsgClusterData,16)
			MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Switch",MsgClusterData)
			
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception General: On/Off : " + str(MsgClusterData) )
		
		elif MsgClusterId=="0402" :  # Measurement: Temperature xiaomi
			MsgValue=Data[len(Data)-8:len(Data)-4]
			MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Temperature",round(int(MsgValue,16)/100,1))
			
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception temp : " + str(int(MsgValue,16)/100) )
					
		elif MsgClusterId=="0403" :  # Measurement: Pression atmospherique xiaomi   ### a corriger/modifier http://zigate.fr/xiaomi-capteur-temperature-humidite-et-pression-atmospherique-clusters/
			if str(Data[28:32])=="0028":
				MsgValue=Data[len(Data)-6:len(Data)-4] ##bug !!!!!!!!!!!!!!!!
				#MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgValue,8))
				
				Domoticz.Debug("ZigateRead - MsgType 8102 - reception atm : " + str(int(MsgValue,8)) )
				
			if str(Data[26:32])=="000029":
				MsgValue=Data[len(Data)-8:len(Data)-4]
				MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgValue,16),1))
				
				Domoticz.Debug("ZigateRead - MsgType 8102 - reception atm : " + str(round(int(MsgValue,16)/100,1)))
				
			if str(Data[26:32])=="100029":
				MsgValue=Data[len(Data)-8:len(Data)-4]
				MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgValue,16)/10,1))
				
				Domoticz.Debug("ZigateRead - MsgType 8102 - reception atm : " + str(round(int(MsgValue,16)/10,1)))

		elif MsgClusterId=="0405" :  # Measurement: Humidity xiaomi
			MsgValue=Data[len(Data)-8:len(Data)-4]
			MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Humidity",round(int(MsgValue,16)/100,1))
			
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception hum : " + str(int(MsgValue,16)/100) )
	
		elif MsgClusterId=="0406" :  # (Measurement: Occupancy Sensing) xiaomi
			MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Switch",MsgClusterData)
			
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception Occupancy Sensor : " + str(MsgClusterData) )

		elif MsgClusterId=="0400" :  # (Measurement: LUX) xiaomi
			MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Lux",str(int(MsgClusterData,16) ))
			
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception LUX Sensor : " + str(MsgClusterData) )
			
			
		elif MsgClusterId=="0012" :  # Magic Cube Xiaomi
			MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Switch",MsgClusterData)
			
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception Xiaomi Magic Cube Value : " + str(MsgClusterData) )
			
		elif MsgClusterId=="000c" :  # Magic Cube Xiaomi rotation
			MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Vert Rot",MsgClusterData)
			
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception Xiaomi Magic Cube Value Vert Rot : " + str(MsgClusterData) )
			
		
			
			
		else :
		
			Domoticz.Debug("ZigateRead - MsgType 8102 - Error/unknow Cluster Message : " + MsgClusterId)

	elif str(MsgType)=="8110":  #
		Domoticz.Debug("reception Write attribute response : " + Data)

	elif str(MsgType)=="8120":  #
		Domoticz.Debug("reception Configure reporting response : " + Data)

	elif str(MsgType)=="8140":  #
		Domoticz.Debug("reception Attribute discovery response : " + Data)

	elif str(MsgType)=="8401":  #
		Domoticz.Debug("reception Zone status change notification : " + Data)
		MsgSrcAddr=MsgData[10:14]
		MsgSrcEp=MsgData[2:4]
		MsgClusterData=MsgData[16:18]
		MajDomoDevice(MsgSrcAddr,MsgSrcEp,"Switch",MsgClusterData)

	elif str(MsgType)=="8701":  # reception Router discovery confirm
	
		Domoticz.Debug("reception Router discovery confirm : " + Data)

	elif str(MsgType)=="8702":  # APS Data Confirm Fail
		MsgDataStatus=MsgData[0:2]
		MsgDataSrcEp=MsgData[2:4]
		MsgDataDestEp=MsgData[4:6]
		MsgDataDestMode=MsgData[6:8]
		MsgDataDestAddr=MsgData[8:12]
		MsgDataSQN=MsgData[12:14]
		
		Domoticz.Debug("reception APS Data confirm fail : Status : " + MsgDataStatus + ", Source Ep : " + MsgDataSrcEp + ", Destination Ep : " + MsgDataDestEp + ", Destination Mode : " + MsgDataDestMode + ", Destination Address : " + MsgDataDestAddr + ", SQN : " + MsgDataSQN)

	else: # unknow or not dev function
	
		Domoticz.Debug("ZigateRead - Unknow Message Type " + MsgType)

	
def CreateDomoDevice(nbrdevices,Addr,Ep,Type) :
	DeviceID=Addr #int(Addr,16)
	Domoticz.Debug("CreateDomoDevice - Device ID : " + str(DeviceID) + " Device EP : " + str(Ep) + " Type : " + str(Type) )
	if Type=="lumi.weather" :  # Detecteur temp/hum/baro xiaomi (v2)
		typename="Temp+Hum+Baro"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Temp+Hum"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+1, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Temperature"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+2, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Humidity"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+3, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Barometer"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+4, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		
	if Type=="lumi.sensor_ht" : # Detecteur temp/humi xiaomi (v1)
		typename="Temp+Hum"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Temperature"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+1, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Humidity"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+2, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		
	if Type=="lumi.sensor_magnet.aq2" or Type=="lumi.sensor_magnet": # capteur ouverture/fermeture xiaomi  (v1 et v2)
		typename="Switch"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=73 , Switchtype=2 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		
	if Type=="lumi.sensor_motion" :  # detecteur de presence (v1) xiaomi
		typename="Switch"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=73 , Switchtype=8 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()

	if Type=="lumi.sensor_switch.aq2" or Type=="lumi.sensor_switch"  :  # petit inter rond ou carre xiaomi (v1)
		typename="Switch"		
		Options = {"LevelActions": "||||", "LevelNames": "Off|1 Click|2 Clicks|3 Clicks|4 Clicks", "LevelOffHidden": "true", "SelectorStyle": "0","EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}
		Domoticz.Device(DeviceID=str(DeviceID),Name="lumi.sensor_switch.aq2" + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()
		
	if Type=="lumi.sensor_86sw2"  :  #inter sans fils 2 touches 86sw2 xiaomi
		typename="Switch"		
		Options = {"LevelActions": "|||", "LevelNames": "Off|Left Click|Right Click|Both Click", "LevelOffHidden": "true", "SelectorStyle": "0","EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}
		Domoticz.Device(DeviceID=str(DeviceID),Name="lumi.sensor_86sw2" + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()
		
	if Type=="lumi.sensor_smoke" :  # detecteur de fumee (v1) xiaomi
		typename="Switch"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=73 , Switchtype=5 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()

	if Type=="lumi.sensor_motion.aq2" :  # Lux sensors + detecteur xiaomi v2
		typename="Lux"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, Type=246, Subtype=1 , Switchtype=0 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Switch"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+1, Type=244, Subtype=73 , Switchtype=8 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()

	if Type=="lumi.sensor_86sw1":  # inter sans fils 1 touche 86sw1 xiaomi
		typename="Switch"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=73 , Switchtype=9 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		
	if Type=="lumi.sensor_cube" :  # Xiaomi Magic Cube
		#typename="Text"
		#Domoticz.Device(DeviceID=str(DeviceID),Name="lumi.sensor_cube-text" + " - " + str(DeviceID), Unit=nbrdevices, Type=243, Subtype=19 , Switchtype=0 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Switch"		
		Options = {"LevelActions": "||||||||", "LevelNames": "Off|Shake|Slide|90°|Clockwise|Tap|Move|Free Fall|Anti Clockwise|180°", "LevelOffHidden": "true", "SelectorStyle": "0","EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}
		Domoticz.Device(DeviceID=str(DeviceID),Name="lumi.sensor_cube" + " - " + str(DeviceID), Unit=nbrdevices+1, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()
		
def MajDomoDevice(Addr,Ep,Type,value) :
	Domoticz.Debug("MajDomoDevice - Device ID : " + str(Addr) + " - Device EP : " + str(Ep) + " - Type : " + str(Type)  + " - Value : " + str(value) )
	x=0
	nbrdevices=1
	DeviceID=Addr #int(Addr,16)
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID) : 
			DOptions = Devices[x].Options
			DType=DOptions['devices_type']
			Dtypename=DOptions['typename']
			if DType=="lumi.weather" : #temp+hum+baro xiaomi
				if Type==Dtypename=="Temperature" :  # temperature
					Devices[x].Update(nValue = 0,sValue = str(value))
				if Type==Dtypename=="Humidity" :   # humidite
					Devices[x].Update(nValue = int(value), sValue = "0")
				if Type==Dtypename=="Barometer" :  # barometre
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					valueBaro='%s;%s' % (value,SplitData[0])
					Devices[x].Update(nValue = 0,sValue = str(valueBaro))
				if Dtypename=="Temp+Hum+Baro" :
					if Type=="Temperature" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s;%s;%s'	% (str(value) ,  SplitData[1] , SplitData[2] , SplitData[3] , SplitData[4])
						Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
						Devices[x].Update(nValue = 0,sValue = str(NewSvalue))						
					if Type=="Humidity" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s;%s;%s'	% (SplitData[0], str(value) , SplitData[2] , SplitData[3] , SplitData[4])
						Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
						Devices[x].Update(nValue = 0,sValue = str(NewSvalue))						
					if Type=="Barometer" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s;%s;%s'	% (SplitData[0], SplitData[1] , SplitData[2] , str(value) , SplitData[3])
						Domoticz.Debug("MajDomoDevice bar NewSvalue : " + NewSvalue)
						Devices[x].Update(nValue = 0,sValue = str(NewSvalue))						
				if Dtypename=="Temp+Hum" : #temp+hum xiaomi
					if Type=="Temperature" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s'	% (str(value), SplitData[1] , SplitData[2])
						Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
						Devices[x].Update(nValue = 0,sValue = str(NewSvalue))						
					if Type=="Humidity" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s'	% (SplitData[0], str(value) , SplitData[2])
						Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
						Devices[x].Update(nValue = 0,sValue = str(NewSvalue))					
	
			if DType=="lumi.sensor_ht" :
				if Type==Dtypename=="Temperature" :
					Devices[x].Update(nValue = 0,sValue = str(value))
				if Type==Dtypename=="Humidity" :
					Devices[x].Update(nValue = int(value), sValue = "0")
				#if Dtypename=="Temp+Hum" :
					#Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, TypeName=typename, options={"EP":Ep, "devices_type": str(Type), "typename":str(typename)}).Create()				
				if Dtypename=="Temp+Hum" :
					if Type=="Temperature" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s'	% (str(value), SplitData[1] , SplitData[2])
						Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
						Devices[x].Update(nValue = 0,sValue = str(NewSvalue))						
					if Type=="Humidity" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s'	% (SplitData[0], str(value) , SplitData[2])
						Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
						Devices[x].Update(nValue = 0,sValue = str(NewSvalue))		

			if DType=="lumi.sensor_magnet.aq2" or DType=="lumi.sensor_magnet" :  # detecteur ouverture/fermeture Xiaomi
				if Type==Dtypename :
					if value == "01" :
						state="Open"
					elif value == "00" :
						state="Closed"
					Devices[x].Update(nValue = int(value),sValue = str(state))
				
			if DType=="lumi.sensor_86sw1" or DType=="lumi.sensor_smoke" or DType=="lumi.sensor_motion" :  # detecteur de presence / interrupteur / detecteur de fumée
				if Type==Dtypename=="Switch" :
					if value == "01" :
						state="On"
					elif value == "00" :
						state="Off"
					Devices[x].Update(nValue = int(value),sValue = str(state))
					
					
			if DType=="lumi.sensor_switch" or DType=="lumi.sensor_switch.aq2"  :  # interrupteur xiaomi rond et carre
				if Type==Dtypename :
					if Type=="Switch" :
						if value == "01" :
							state="10"
						elif value == "02" :
							state="20"
						elif value == "03" :
							state="30"
						elif value == "04" :
							state="40"
						Devices[x].Update(nValue = int(value),sValue = str(state))
						
						
			if DType=="lumi.sensor_86sw2"   :  # inter 2 touches xiaomi 86sw2
				if Type==Dtypename :
					if Type=="Switch" :
						if Ep == "01" :
							if value == "01" :
								state="10"
								data="01"
						elif Ep == "02" :
							if value == "01" :
								state="20"
								data="02"
						elif Ep == "03" :
							if value == "01" :
								state="30"
								data="03"
						Devices[x].Update(nValue = int(data),sValue = str(state))
						
						
						
			if DType=="lumi.sensor_cube"   :  # Xiaomi Magic Cube
				if Type==Dtypename :
					if Type=="Switch" :
						if Ep == "02" :
							if value == "0000" : #shake
								state="10"
								data="01"
						
							elif value == "0204" or value == "0200" or value == "0203" or value == "0201" or value == "0202" or value == "0205": #tap
								state="50"
								data="05"
							
							elif value == "0103" or value == "0100" or value == "0104" or value == "0101" or value == "0102" or value == "0105": #Slide
								state="20"
								data="02"
							
							elif value == "0003" : #Free Fall
								state="70"
								data="07"
								
							elif value >= "0004" and value <= "0059": #90°
								state="30"
								data="03"
								
							elif value >= "0060" : #180°
								state="90"
								data="09"
					# elif Type=="Switch" : #rotation
						# elif MsgClusterId=="000c":
							# if Ep == "03" :
								# if value == "40404040" or value=="41414141" or value=="42424242" or value=="43434343" : #clockwise
								  # state="40"
								  # data="04"
						
							# # elif value == "0204" or value == "0200": #tap
								# # state="50"
								# # data="05"
								
							Devices[x].Update(nValue = int(data),sValue = str(state))

			if DType=="lumi.sensor_motion.aq2":  # detecteur de luminosite
				if Type==Dtypename :
					if Type=="Lux" :
						Devices[x].Update(nValue = 0 ,sValue = str(value))
						
				elif Type==Dtypename :
					if Type=="Switch" :
						if value == "01" :
							state="On"
						elif value == "00" :
							state="Off"
						Devices[x].Update(nValue = int(value),sValue = str(state))
			
def ResetDevice(Type) :
	x=0
	for x in Devices: 
		LUpdate=Devices[x].LastUpdate
		LUpdate=time.mktime(time.strptime(LUpdate,"%Y-%m-%d %H:%M:%S"))
		current = time.time()
		DOptions = Devices[x].Options
		DType=DOptions['devices_type']
		Dtypename=DOptions['typename']
		if (current-LUpdate)> 30 :
			if DType==Type :
				if Dtypename=="Switch":
					value = "00"
					state="Off"
					Devices[x].Update(nValue = int(value),sValue = str(state))
			
			
	

def getChecksum(msgtype,length,datas) :
	temp = 0 ^ int(msgtype[0:2],16) 
	temp ^= int(msgtype[2:4],16) 
	temp ^= int(length[0:2],16) 
	temp ^= int(length[2:4],16)
	for i in range(0,len(datas),2) :
		temp ^= int(datas[i:i+2],16)
		chk=hex(temp)
	Domoticz.Debug("getChecksum - Checksum : " + str(chk))
	return chk[2:4]


def UpdateBattery(DeviceID,BatteryLvl):
	x=0
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID):
			Domoticz.Log("Devices already exist. Unit=" + str(x))
			CurrentnValue=Devices[x].nValue
			Domoticz.Log("CurrentnValue = " + str(CurrentnValue))
			CurrentsValue=Devices[x].sValue
			Domoticz.Log("CurrentsValue = " + str(CurrentsValue))
			Domoticz.Log("BatteryLvl = " + str(BatteryLvl))
			Devices[x].Update(nValue = int(CurrentnValue),sValue = str(CurrentsValue), BatteryLevel = BatteryLvl )
	#####################################################################################################################



	
