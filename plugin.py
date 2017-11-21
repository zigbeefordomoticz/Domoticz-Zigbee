# Zigate Python Plugin
#
# Author: zaraki673
#
"""
<plugin key="Zigate" name="Zigate USB plugin" author="zaraki673" version="1.0.2" wikilink="http://www.domoticz.com/wiki/plugins/zigate.html" externallink="https://www.zigate.fr/">
	<params>
		<param field="SerialPort" label="Serial Port" width="150px" required="true" default="" />
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
			#with open(Parameters["HomeFolder"]+"Debug.txt", "wt") as text_file:
			#	print("Started recording message for debug.", file=text_file)
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
				ZigateDecode(ReqRcv) #demande de decodage de la trame reçu
				ReqRcv=Tmprcv[Tmprcv.find('03')+2:]  # traite la suite du tampon
			except :
				#verifier si pas deux messages coller ensemble
				Domoticz.Debug("onMessage - effacement de la trame suite à une erreur de decodage : " + ReqRcv)
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
		#sendZigateCmd("0045","0002", "75de")    # Envoie une demande Active Endpoint request
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
	#lineinput="01021021021002142D021002100218021003"
	#SerialConn.Send(bytes.fromhex(lineinput))
	sendZigateCmd("0021","0004", "00000800")

	################### ZiGate - Set Type COORDINATOR#################
	#lineinput="010210230210021122021003"
	#SerialConn.Send(bytes.fromhex(lineinput))
	sendZigateCmd("0023","0001","00")
	
	################### ZiGate - start network##################
	#lineinput= "01021024021002102403"
	#SerialConn.Send(bytes.fromhex(lineinput))
	sendZigateCmd("0024","0000","")

	################### ZiGate - discover mode 255sec ##################
	#lineinput= "01 0210 49 0210 0214 B0 FFFCFE0210 03"
	#SerialConn.Send(bytes.fromhex(lineinput))
	sendZigateCmd("0049","0004","FFFCFE00")
	

def ZigateDecode(Data):  # supprime le transcodage
	#if Parameters["Mode6"] == "Debug":
	#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
	#		print("ZigateDecode - decodind data : " + Data, file=text_file)
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
	#if Parameters["Mode6"] == "Debug":
	#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
	#		print("ZigateDecode - Encodind data : " + Data, file=text_file)
	Domoticz.Debug("ZigateDecode - Encodind data : " + Data)
	Out=""
	Outtmp=""
	Transcode = False
	for c in Data :
		Outtmp+=c
		if len(Outtmp)==2 :
			#if int(Outtmp,16) <= int("10",16) :
			#	Out+="02" + str(int(Outtmp,16) ^ 10)
			#else :
			#	Out+=Outtmp
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
	#if Parameters["Mode6"] == "Debug":
	#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
	#		print("sendZigateCmd - Comand send : " + str(lineinput), file=text_file)
	Domoticz.Debug("sendZigateCmd - Comand send : " + str(lineinput))
	SerialConn.Send(bytes.fromhex(str(lineinput)))	


	
def ZigateRead(Data):
	#if Parameters["Mode6"] == "Debug":
	#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
	#		print("ZigateRead - decoded data : " + Data, file=text_file)
	Domoticz.Debug("ZigateRead - decoded data : " + Data)
#Trame série
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
	#if Parameters["Mode6"] == "Debug":
	#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
	#		print("ZigateRead - Message Type : " + MsgType + ", Data : " + MsgData + ", RSSI : " + MsgRSSI + ", Length : " + MsgLength + ", Checksum : " + MsgCRC, file=text_file)
	Domoticz.Debug("ZigateRead - Message Type : " + MsgType + ", Data : " + MsgData + ", RSSI : " + MsgRSSI + ", Length : " + MsgLength + ", Checksum : " + MsgCRC)

	if str(MsgType)=="004d":  # Device announce
		MsgSrcAddr=MsgData[0:4]
		MsgIEEE=MsgData[4:20]
		MsgMacCapa=MsgData[20:22]
	
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Device announce : Source :" + MsgSrcAddr + ", IEEE : "+ MsgIEEE + ", Mac capa : " + MsgMacCapa, file=text_file)
		Domoticz.Debug("reception Device announce : Source :" + MsgSrcAddr + ", IEEE : "+ MsgIEEE + ", Mac capa : " + MsgMacCapa)
		
		# tester si le device existe deja dans la base domoticz
		#sendZigateCmd("0045","0002", str(MsgSrcAddr))    # Envoie une demande Active Endpoint request
		#SerialConn.Send(bytes.fromhex(lineinput))
		
	elif str(MsgType)=="00d1":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Touchlink status : " + Data, file=text_file)
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
		
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("ZigateRead - MsgType 8000 - reception status : " + MsgDataStatus + ", SQN : " + MsgDataSQN + ", Message : " + MsgDataMessage, file=text_file)
		Domoticz.Debug("ZigateRead - MsgType 8000 - reception status : " + MsgDataStatus + ", SQN : " + MsgDataSQN + ", Message : " + MsgDataMessage)

	elif str(MsgType)=="8001":  # Log
		MsgLogLvl=MsgData[0:2]
		MsgDataMessage=MsgData[2:len(MsgData)]
		
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception log Level 0x: " + MsgLogLvl + "Message : " + MsgDataMessage, file=text_file)
		Domoticz.Debug("reception log Level 0x: " + MsgLogLvl + "Message : " + MsgDataMessage)

	elif str(MsgType)=="8002":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Data indication : " + Data, file=text_file)
		Domoticz.Debug("reception Data indication : " + Data)

	elif str(MsgType)=="8003":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Liste des cluster de l'objet : " + Data, file=text_file)
		Domoticz.Debug("reception Liste des cluster de l'objet : " + Data)

	elif str(MsgType)=="8004":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Liste des attributs de l'objet : " + Data, file=text_file)
		Domoticz.Debug("reception Liste des attributs de l'objet : " + Data)

	elif str(MsgType)=="8005":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Liste des commandes de l'objet : " + Data, file=text_file)
		Domoticz.Debug("reception Liste des commandes de l'objet : " + Data)

	elif str(MsgType)=="8006":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Non factory new restart : " + Data, file=text_file)
		Domoticz.Debug("reception Non factory new restart : " + Data)

	elif str(MsgType)=="8007":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Factory new restart : " + Data, file=text_file)
		Domoticz.Debug("reception Factory new restart : " + Data)

	elif str(MsgType)=="8010":  # Version
		MsgDataApp=MsgData[0:4]
		MsgDataSDK=MsgData[4:8]
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Version list : " + Data, file=text_file)
		Domoticz.Debug("reception Version list : " + Data)

	elif str(MsgType)=="8014":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Permit join status response : " + Data, file=text_file)
		Domoticz.Debug("reception Permit join status response : " + Data)

	elif str(MsgType)=="8024":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Network joined /formed : " + Data, file=text_file)
		Domoticz.Debug("reception Network joined /formed : " + Data)

	elif str(MsgType)=="8028":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Authenticate response : " + Data, file=text_file)
		Domoticz.Debug("reception Authenticate response : " + Data)

	elif str(MsgType)=="8029":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Out of band commissioning data response : " + Data, file=text_file)
		Domoticz.Debug("reception Out of band commissioning data response : " + Data)

	elif str(MsgType)=="802b":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception User descriptor notify : " + Data, file=text_file)
		Domoticz.Debug("reception User descriptor notify : " + Data)

	elif str(MsgType)=="802c":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception User descriptor response : " + Data, file=text_file)
		Domoticz.Debug("reception User descriptor response : " + Data)

	elif str(MsgType)=="8030":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Bind response : " + Data, file=text_file)
		Domoticz.Debug("reception Bind response : " + Data)

	elif str(MsgType)=="8031":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Unbind response : " + Data, file=text_file)
		Domoticz.Debug("reception Unbind response : " + Data)

	elif str(MsgType)=="8034":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Coplex Descriptor response : " + Data, file=text_file)
		Domoticz.Debug("reception Coplex Descriptor response : " + Data)

	elif str(MsgType)=="8040":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Network address response : " + Data, file=text_file)
		Domoticz.Debug("reception Network address response : " + Data)

	elif str(MsgType)=="8041":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception IEEE address response : " + Data, file=text_file)
		Domoticz.Debug("reception IEEE address response : " + Data)

	elif str(MsgType)=="8042":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Node descriptor response : " + Data, file=text_file)
		Domoticz.Debug("reception Node descriptor response : " + Data)

	elif str(MsgType)=="8043":  # Simple Descriptor Response
		MsgDataSQN=MsgData[0:2]
		MsgDataStatus=MsgData[2:4]
		MsgDataShAddr=MsgData[4:8]
		MsgDataLenght=MsgData[8:10]
			# if int(MsgDataLenght,16)>0 :
				# MsgDataEp=MsgData[8:10]
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Simple descriptor response : SQN : " + MsgDataSQN + ", Status " + MsgDataStatus + ", short Addr " + MsgDataShAddr + ", Lenght " + MsgDataLenght, file=text_file)
		Domoticz.Debug("reception Simple descriptor response : SQN : " + MsgDataSQN + ", Status " + MsgDataStatus + ", short Addr " + MsgDataShAddr + ", Lenght " + MsgDataLenght)

	elif str(MsgType)=="8044":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Power descriptor response : " + Data, file=text_file)
		Domoticz.Debug("reception Power descriptor response : " + Data)

	elif str(MsgType)=="8045":  # Active Endpoints Response
		MsgDataSQN=MsgData[0:2]
		MsgDataStatus=MsgData[2:4]
		MsgDataShAddr=MsgData[4:8]
		MsgDataEpCount=MsgData[8:10]
		MsgDataEPlist=MsgData[10:len(MsgData)]
		
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Active endpoint response : SQN : " + MsgDataSQN + ", Status " + MsgDataStatus + ", short Addr " + MsgDataShAddr + ", EP count " + MsgDataEpCount + ", Ep list" + MsgDataEPlist, file=text_file)
		Domoticz.Debug("reception Active endpoint response : SQN : " + MsgDataSQN + ", Status " + MsgDataStatus + ", short Addr " + MsgDataShAddr + ", EP count " + MsgDataEpCount + ", Ep list " + MsgDataEPlist)
		
		#OutEPlist=""
		#for i in MsgDataEPlist :
		#	OutEPlist+=i
		#	if len(OutEPlist)==2 :
		#		Domoticz.Debug("Envoie une demande Simple Descriptor request pour avoir les informations du EP :" + OutEPlist + ", du device adresse : " + MsgDataShAddr)
		#		sendZigateCmd("0043","0004", str(MsgDataShAddr)+str(OutEPlist))    # Envoie une demande Simple Descriptor request pour avoir les informations du EP
		#		OutEPlisttmp=""
		

	elif str(MsgType)=="8046":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Match descriptor response : " + Data, file=text_file)
		Domoticz.Debug("reception Match descriptor response : " + Data)

	elif str(MsgType)=="8047":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Management leave response : " + Data, file=text_file)
		Domoticz.Debug("reception Management leave response : " + Data)

	elif str(MsgType)=="8048":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Leave indication : " + Data, file=text_file)
		Domoticz.Debug("reception Leave indication : " + Data)

	elif str(MsgType)=="804a":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Management Network Update response : " + Data, file=text_file)
		Domoticz.Debug("reception Management Network Update response : " + Data)

	elif str(MsgType)=="804b":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception System server discovery response : " + Data, file=text_file)
		Domoticz.Debug("reception System server discovery response : " + Data)

	elif str(MsgType)=="804e":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Management LQI response : " + Data, file=text_file)
		Domoticz.Debug("reception Management LQI response : " + Data)

	elif str(MsgType)=="8060":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Add group response : " + Data, file=text_file)
		Domoticz.Debug("reception Add group response : " + Data)

	elif str(MsgType)=="8061":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Viex group response : " + Data, file=text_file)
		Domoticz.Debug("reception Viex group response : " + Data)

	elif str(MsgType)=="8062":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Get group Membership response : " + Data, file=text_file)
		Domoticz.Debug("reception Get group Membership response : " + Data)

	elif str(MsgType)=="8063":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Remove group response : " + Data, file=text_file)
		Domoticz.Debug("reception Remove group response : " + Data)

	elif str(MsgType)=="80a0":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception View scene response : " + Data, file=text_file)
		Domoticz.Debug("reception View scene response : " + Data)

	elif str(MsgType)=="80a1":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Add scene response : " + Data, file=text_file)
		Domoticz.Debug("reception Add scene response : " + Data)

	elif str(MsgType)=="80a2":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Remove scene response : " + Data, file=text_file)
		Domoticz.Debug("reception Remove scene response : " + Data)

	elif str(MsgType)=="80a3":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Remove all scene response : " + Data, file=text_file)
		Domoticz.Debug("reception Remove all scene response : " + Data)

	elif str(MsgType)=="80a4":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Store scene response : " + Data, file=text_file)
		Domoticz.Debug("reception Store scene response : " + Data)

	elif str(MsgType)=="80a6":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Scene membership response : " + Data, file=text_file)
		Domoticz.Debug("reception Scene membership response : " + Data)

	elif str(MsgType)=="8100":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Real individual attribute response : " + Data, file=text_file)
		Domoticz.Debug("reception Real individual attribute response : " + Data)

	elif str(MsgType)=="8101":  # Default Response
		MsgDataSQN=MsgData[0:2]
		MsgDataEp=MsgData[2:4]
		MsgClusterId=MsgData[4:8]
		MsgDataCommand=MsgData[8:10]
		MsgDataStatus=MsgData[10:12]
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Default response : SQN : " + MsgDataSQN + ", EP : " + MsgDataEp + ", Cluster ID : " + MsgClusterId + " , Command : " + MsgDataCommand+ ", Status : " + MsgDataStatus, file=text_file)
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

		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("ZigateRead - MsgType 8102 - reception data : " + Data + " ClusterID : " + MsgClusterId + " Attribut ID : " + MsgAttrID + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp, file=text_file)
		Domoticz.Debug("ZigateRead - MsgType 8102 - reception data : " + Data + " ClusterID : " + MsgClusterId + " Attribut ID : " + MsgAttrID + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp)
				
		if MsgClusterId=="0000" :
			#if Parameters["Mode6"] == "Debug":
			#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
			#		print("ZigateRead - MsgType 8102 - reception heartbeat (0000) : " + MsgClusterData , file=text_file)	
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception heartbeat (0000) : " + MsgClusterData)
			if MsgAttrID=="ff01" :
				MsgBattery=MsgClusterData[61:64]
				try :
					#MsgBattery=MsgBattery[0:1]+MsgBattery[2:3]+MsgBattery[1:2]
					MsgBattery=round(int(MsgBattery,16)/100,2)
					UpdateBattery(MsgSrcAddr,MsgBattery)
					#if Parameters["Mode6"] == "Debug":
					#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
					#		print("ZigateRead - MsgType 8102 - reception batteryLVL (0000) : " + MsgBattery + "% pour le device addr : " +  MsgSrcAddr, file=text_file)
					Domoticz.Debug("ZigateRead - MsgType 8102 - reception batteryLVL (0000) : " + MsgBattery + "% pour le device addr : " +  MsgSrcAddr)
				except :
					#if Parameters["Mode6"] == "Debug":
					#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
					#		print("ZigateRead - MsgType 8102 - reception batteryLVL (0000) : erreur de lecture pour le device addr : " +  MsgSrcAddr, file=text_file)
					Domoticz.Debug("ZigateRead - MsgType 8102 - reception batteryLVL (0000) : erreur de lecture pour le device addr : " +  MsgSrcAddr)
							
		elif MsgClusterId=="0006" :  # General: On/Off
			SetSwitch(MsgSrcAddr,MsgSrcEp,MsgClusterData,16)
			#if Parameters["Mode6"] == "Debug":
			#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
			#		print("ZigateRead - MsgType 8102 - reception General: On/Off : " + str(MsgClusterData) , file=text_file)			
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception General: On/Off : " + str(MsgClusterData) )
		
		elif MsgClusterId=="0402" :  # Measurement: Temperature
			MsgValue=Data[len(Data)-8:len(Data)-4]
			SetTemp(MsgSrcAddr,MsgSrcEp,int(MsgValue,16)/100,80)
			#if Parameters["Mode6"] == "Debug":
			#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
			#		print("ZigateRead - MsgType 8102 - reception temp : " + str(int(MsgValue,16)/100) , file=text_file)
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception temp : " + str(int(MsgValue,16)/100) )
					
		elif MsgClusterId=="0403" :  # Measurement: Pression atmospherique    ### a corriger/modifier http://zigate.fr/xiaomi-capteur-temperature-humidite-et-pression-atmospherique-clusters/
			if str(Data[28:32])=="0028":
				MsgValue=Data[len(Data)-6:len(Data)-4] ##bug !!!!!!!!!!!!!!!!
				SetATM(MsgSrcAddr,MsgSrcEp,round(int(MsgValue,8)),243)
				#if Parameters["Mode6"] == "Debug":
				#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
				#		print("ZigateRead - MsgType 8102 - reception atm : " + str(int(MsgValue,8)) , file=text_file)
				Domoticz.Debug("ZigateRead - MsgType 8102 - reception atm : " + str(int(MsgValue,8)) )
			if str(Data[26:32])=="000029":
				MsgValue=Data[len(Data)-8:len(Data)-4]
				SetATM(MsgSrcAddr,MsgSrcEp,str(round(int(MsgValue,16),1)),243)
				#if Parameters["Mode6"] == "Debug":
				#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
				#		print("ZigateRead - MsgType 8102 - reception atm : " + str(round(int(MsgValue,16)/100,1)) , file=text_file)
				Domoticz.Debug("ZigateRead - MsgType 8102 - reception atm : " + str(round(int(MsgValue,16)/100,1)))
			if str(Data[26:32])=="100029":
				MsgValue=Data[len(Data)-8:len(Data)-4]
				SetATM(MsgSrcAddr,MsgSrcEp,str(round(int(MsgValue,16)/10,1)),243)
				#if Parameters["Mode6"] == "Debug":
				#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
				#		print("ZigateRead - MsgType 8102 - reception atm : " + str(round(int(MsgValue,16)/10,1)) , file=text_file)
				Domoticz.Debug("ZigateRead - MsgType 8102 - reception atm : " + str(round(int(MsgValue,16)/10,1)))

		elif MsgClusterId=="0405" :  # Measurement: Humidity
			MsgValue=Data[len(Data)-8:len(Data)-4]
			SetHum(MsgSrcAddr,MsgSrcEp,round(int(MsgValue,16)/100),81)
			#if Parameters["Mode6"] == "Debug":
			#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
			#		print("ZigateRead - MsgType 8102 - reception hum : " + str(int(MsgValue,16)/100) , file=text_file)
			Domoticz.Debug("ZigateRead - MsgType 8102 - reception hum : " + str(int(MsgValue,16)/100) )

		else :
			#if Parameters["Mode6"] == "Debug":
			#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
			#		print("ZigateRead - MsgType 8102 - Error/unknow Cluster Message : " + MsgClusterId, file=text_file)
			Domoticz.Debug("ZigateRead - MsgType 8102 - Error/unknow Cluster Message : " + MsgClusterId)

	elif str(MsgType)=="8110":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Write attribute response : " + Data, file=text_file)
		Domoticz.Debug("reception Write attribute response : " + Data)

	elif str(MsgType)=="8120":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Configure reporting response : " + Data, file=text_file)
		Domoticz.Debug("reception Configure reporting response : " + Data)

	elif str(MsgType)=="8140":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Attribute discovery response : " + Data, file=text_file)
		Domoticz.Debug("reception Attribute discovery response : " + Data)

	elif str(MsgType)=="8401":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Zone status change notification : " + Data, file=text_file)
		Domoticz.Debug("reception Zone status change notification : " + Data)

	elif str(MsgType)=="8701":  #
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception Router discovery confirm : " + Data, file=text_file)
		Domoticz.Debug("reception Router discovery confirm : " + Data)

	elif str(MsgType)=="8702":  # APS Data Confirm Fail
		MsgDataStatus=MsgData[0:2]
		MsgDataSrcEp=MsgData[2:4]
		MsgDataDestEp=MsgData[4:6]
		MsgDataDestMode=MsgData[6:8]
		MsgDataDestAddr=MsgData[8:12]
		MsgDataSQN=MsgData[12:14]
		
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("reception APS Data confirm fail : Status : " + MsgDataStatus + ", Source Ep : " + MsgDataSrcEp + ", Destination Ep : " + MsgDataDestEp + ", Destination Mode : " + MsgDataDestMode + ", Destination Address : " + MsgDataDestAddr + ", SQN : " + MsgDataSQN, file=text_file)
		Domoticz.Debug("reception APS Data confirm fail : Status : " + MsgDataStatus + ", Source Ep : " + MsgDataSrcEp + ", Destination Ep : " + MsgDataDestEp + ", Destination Mode : " + MsgDataDestMode + ", Destination Address : " + MsgDataDestAddr + ", SQN : " + MsgDataSQN)

	else: # unknow or not dev function
		#if Parameters["Mode6"] == "Debug":
		#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
		#		print("ZigateRead - Unknow Message Type " + MsgType, file=text_file)
		Domoticz.Debug("ZigateRead - Unknow Message Type " + MsgType)

	return
	

def getChecksum(msgtype,length,datas) :
	temp = 0 ^ int(msgtype[0:2],16) 
	#Domoticz.Debug("getChecksum - msgtype[0:2] : " + str(msgtype[0:2]))
	temp ^= int(msgtype[2:4],16) 
	#Domoticz.Debug("getChecksum - msgtype[2:4] : " + str(msgtype[2:4]))
	temp ^= int(length[0:2],16) 
	#Domoticz.Debug("getChecksum - length[0:2] : " + str(length[0:2]))
	temp ^= int(length[2:4],16)
	#Domoticz.Debug("getChecksum - length[2:4] : " + str(length[2:4]))
	for i in range(0,len(datas),2) :
		temp ^= int(datas[i:i+2],16)
		#Domoticz.Debug("getChecksum - datas[" + str(i) + ":" + str(i+2) + "] : " + str(datas[i:i+2]))
		chk=hex(temp)
	#if Parameters["Mode6"] == "Debug":
	#	with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
	#		print("getChecksum - Checksum : " + chk, file=text_file)
	Domoticz.Debug("getChecksum - Checksum : " + str(chk))
	return chk[2:4]

def SetSwitch(Addr,Ep, value, type):
	IsCreated=False
	x=0
	nbrdevices=1
	DeviceID=int(Addr,16)

	if str(type)=="16" : 
		typename="Switch"
	if value == "01" :
		state="On"
	elif value == "00" :
		state="Off"
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID) : # and str(Devices[x].Type)==str(type):
			IsCreated = True
			Domoticz.Log("Devices already exist. Unit=" + str(x))
			nbrdevices=x
		if IsCreated == False :
			nbrdevices=x
	if IsCreated == False :
		nbrdevices=nbrdevices+1
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, TypeName=typename).Create()
		Devices[nbrdevices].Update(nValue = 0,sValue = str(state))
	elif IsCreated == True :
		Devices[nbrdevices].Update(nValue = 0,sValue = str(state))


def SetTemp(Addr,Ep, value, type):
	IsCreated=False
	x=0
	nbrdevices=1
	DeviceID=int(Addr,16)
	if str(type)=="80" :
		typename = "Temperature"
	if str(type)=="81" :
		typename = "Humidity"

	#Domoticz.Log("Devices already exist. Unit=" + str(x))
		
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID) and str(Devices[x].Type)==str(type):
			IsCreated = True
			Domoticz.Log("Devices already exist. Unit=" + str(x))
			nbrdevices=x
		if IsCreated == False :
			nbrdevices=x
	if IsCreated == False :
		nbrdevices=nbrdevices+1
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, TypeName=typename).Create()
		Devices[nbrdevices].Update(nValue = 0,sValue = str(value))
	elif IsCreated == True :
		Devices[nbrdevices].Update(nValue = 0,sValue = str(value))
	#####################################################################################################################

def SetHum(Addr,Ep, value, type):
	IsCreated=False
	x=0
	nbrdevices=1
	DeviceID=int(Addr,16)
	if str(type)=="80" :
		typename = "Temperature"
	if str(type)=="81" :
		typename = "Humidity"

	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID) and str(Devices[x].Type)==str(type):
			IsCreated = True
			Domoticz.Log("Devices already exist. Unit=" + str(x))
			nbrdevices=x
		if IsCreated == False :
			nbrdevices=x
	if IsCreated == False :
		nbrdevices=nbrdevices+1
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, TypeName=typename).Create()
		Devices[nbrdevices].Update(nValue = int(value), sValue = "0")
	elif IsCreated == True :
		Devices[nbrdevices].Update(nValue = int(value), sValue = "0")
	#####################################################################################################################


def SetATM(Addr,Ep, value, type):
	IsCreated=False
	x=0
	nbrdevices=1
	DeviceID=int(Addr,16)
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID) and str(Devices[x].Type)==str(type):
			IsCreated = True
			Domoticz.Log("Devices already exist. Unit=" + str(x))
			nbrdevices=x
		if IsCreated == False :
			nbrdevices=x
	if IsCreated == False :
		nbrdevices=nbrdevices+1
		Domoticz.Device(DeviceID=str(DeviceID),Name="ATM - " + str(DeviceID), Unit=nbrdevices, TypeName="Pressure").Create()
		Devices[nbrdevices].Update(nValue = 0,sValue = str(value))
	elif IsCreated == True :
		Devices[nbrdevices].Update(nValue = 0,sValue = str(value))
	#####################################################################################################################

def UpdateBattery(DeviceID,BatteryLvl):
	IsCreated=False
	x=0
	nbrdevices=1
	DeviceID=int(Addr,16)
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID):
			IsCreated = True
			Domoticz.Log("Devices already exist. Unit=" + str(x))
			nbrdevices=x
		if IsCreated == False :
			nbrdevices=x
	#if IsCreated == False :
		# rien à faire
	if IsCreated == True :
		Devices[nbrdevices].Update(nValue = Devices[nbrdevices].nValue,sValue = Devices[nbrdevices].sValue, BatteryLevel = BatteryLvl)
	#####################################################################################################################



	