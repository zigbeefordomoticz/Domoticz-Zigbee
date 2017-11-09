# Zigate Python Plugin
#
# Author: zaraki673
#
"""
<plugin key="Zigate" name="Zigate USB plugin" author="zaraki673" version="1.0.1" wikilink="http://www.domoticz.com/wiki/plugins/zigate.html" externallink="https://www.zigate.fr/">
	<params>
		<param field="SerialPort" label="Serial Port" width="150px" required="true" default="">
		</param>
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
		#self.var = 123
		return

	def onStart(self):
		Domoticz.Log("onStart called")
		global ReqRcv
		global SerialConn
		if Parameters["Mode6"] == "Debug":
			Domoticz.Debugging(1)
			with open(Parameters["HomeFolder"]+"Debug.txt", "wt") as text_file:
				print("Started recording message for debug.", file=text_file)
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
		if Tmprcv.endswith('03',0,len(Tmprcv))==True :   ### a modifier on peut recevoir 0301 (fin-début) qui ne serais pas interprété
		#if Tmprcv.find('03') != -1 :### fin de messages detecter dans Data
			ReqRcv+=Tmprcv #[:Tmprcv.find('03')+2] #
			Zdata=ZigateDecode(ReqRcv) #demande de decodage de la trame reçu
			ZigateRead(Zdata)
			ReqRcv="" #Tmprcv[Tmprcv.find('03')+2:]  # efface le tampon
		else : # while end of data is receive
			ReqRcv+=Tmprcv
		return

	def onCommand(self, Unit, Command, Level, Hue):
		Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

	def onDisconnect(self, Connection):
		Domoticz.Log("onDisconnect called")

	def onHeartbeat(self):
#		Domoticz.Log("onHeartbeat called")
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
	################### ZiGate - get status ##################
	#lineinput="01021010021002101003".decode("hex") 
	#SerialConn.Send(lineinput)
	
	#01 02 10 49 02 10 02 14 B0 FF FC FE 02 10 03  > passer en mode discover devices
	
	
	################### ZiGate - set channel 11 ##################
	lineinput="01 02 10 21 02 10 02 14 2D 02 10 02 10 02 18 02 10 03 "
	SerialConn.Send(bytes.fromhex(lineinput))

	################### ZiGate - Set Type COORDINATOR#################
	lineinput="010210230210021122021003"
	SerialConn.Send(bytes.fromhex(lineinput))
	
	################### ZiGate - start network##################
	lineinput= "01021024021002102403" 
	SerialConn.Send(bytes.fromhex(lineinput))
	
	################### ZiGate - discover mode 30sec ##################
	lineinput= "0102104902100214B0FFFCFE021003" 
	SerialConn.Send(bytes.fromhex(lineinput))	

def ZigateDecode(Data):  # supprime le transcodage
	if Parameters["Mode6"] == "Debug":
		with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
			print("decodind data : " + Data, file=text_file)
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
	
	return Out
	
def ZigateRead(Data):
	if Parameters["Mode6"] == "Debug":
		with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
			print("decoded data : " + Data, file=text_file)	
	
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
#01		 81		 02		 00		 0F		 AB		 02 6F 2F 01 04 02 00 00 00 29 00 02 09 89 		 C9		 03
						
	MsgType=Data[2:6]
	MsgData=Data[12:len(Data)-4]
	MsgRSSI=Data[len(Data)-4:len(Data)-2]
	MsgLength=Data[6:10]
	MsgCRC=Data[10:12]
	if Parameters["Mode6"] == "Debug":
		with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
			print("Message Type : " + MsgType + ", Data : " + MsgData + ", RSSI : " + MsgRSSI + ", Length : " + MsgLength + ", Checksum : " + MsgCRC, file=text_file)	

	
	if str(MsgType)=="8000":  # Status
		if Parameters["Mode6"] == "Debug":
			with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
				print("reception status : " + Data, file=text_file)	
			
	elif str(MsgType)=="8102":  # Report Individual Attribute response
		MsgSQN=Data[12:14]
		MsgSrcAddr=Data[14:18]
		MsgSrcEp=Data[18:20]
		MsgClusterId=Data[20:24]
		
		if MsgClusterId=="0402" :  # Measurement: Temperature
			MsgValue=Data[len(Data)-6:len(Data)-4]
			SetTempHum(MsgSrcAddr,MsgSrcEp,int(MsgValue,16),80)
			if Parameters["Mode6"] == "Debug":
				with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
					print("reception temp : " + int(MsgValue,16) , file=text_file)	
					
		elif MsgClusterId=="0403" :  # Measurement: Pression atmospherique
			MsgValue=Data[len(Data)-6:len(Data)-4]
			SetATM(MsgSrcAddr,MsgSrcEp,int(MsgValue,16),246)
			if Parameters["Mode6"] == "Debug":
				with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
					print("reception atm : " + int(MsgValue,16) , file=text_file)	
								
		elif MsgClusterId=="0405" :  # Measurement: Humidity
			MsgValue=Data[len(Data)-6:len(Data)-4]
			SetTempHum(MsgSrcAddr,MsgSrcEp,int(MsgValue,16),81)
			if Parameters["Mode6"] == "Debug":
				with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
					print("reception hum : " + int(MsgValue,16) , file=text_file)	
								
		else :
			if Parameters["Mode6"] == "Debug":
				with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
					print("Error/unknow Cluster Message : " + MsgClusterId, file=text_file)	
					
		if Parameters["Mode6"] == "Debug":
			with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
				print("reception data : " + Data + " ClusterID : " + MsgClusterId + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp, file=text_file)	
				
				
	else: # unknow or not dev function
		if Parameters["Mode6"] == "Debug":
			with open(Parameters["HomeFolder"]+"Debug.txt", "at") as text_file:
				print("Unknow Message Type " + MsgType, file=text_file)	
						
	
	return 

	
def SetTempHum(Addr,Ep, value, type):
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
	if IsCreated == False :
		nbrdevices=nbrdevices+1
		Domoticz.Device(DeviceID=str(DeviceID),Name="Temp - " + str(DeviceID), Unit=nbrdevices, Type=type, Switchtype=0).Create()
		Devices[nbrdevices].Update(nValue = 0,sValue = str(value))
	elif IsCreated == True :
		Devices[nbrdevices].Update(nValue = 0,sValue = str(value))
	#####################################################################################################################

	
def SetATM(Addr,Ep, value, type):
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
	if IsCreated == False :
		nbrdevices=nbrdevices+1
		Domoticz.Device(DeviceID=str(DeviceID),Name="ATM - " + str(DeviceID), Unit=nbrdevices, Type=243, Subtype=26, Switchtype=0).Create()
		Devices[nbrdevices].Update(nValue = 0,sValue = str(value))
	elif IsCreated == True :
		Devices[nbrdevices].Update(nValue = 0,sValue = str(value))
	#####################################################################################################################



	

	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	