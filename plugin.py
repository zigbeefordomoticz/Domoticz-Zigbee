# Zigate Python Plugin
#
# Author: zaraki673
#

"""
<plugin key="Zigate" name="Zigate plugin" author="zaraki673" version="2.1.4" wikilink="http://www.domoticz.com/wiki/Zigate" externallink="https://www.zigate.fr/">
	<params>
		<param field="Mode1" label="Type" width="75px">
			<options>
				<option label="USB" value="USB" default="true" />
				<option label="Wifi" value="Wifi"/>
			</options>
		</param>
		<param field="Address" label="IP" width="150px" required="true" default="0.0.0.0"/>
		<param field="Port" label="Port" width="150px" required="true" default="9999"/>
		<param field="SerialPort" label="Serial Port" width="150px" required="true" default="/dev/ttyUSB0"/>
		<param field="Mode5" label="Channel " width="50px" required="true" default="11" />
		<param field="Mode2" label="Duree association (entre 0 et 255) au demarrage : " width="75px" required="true" default="254" />
		<param field="Mode3" label="Erase Persistent Data ( !!! reassociation de tous les devices obligatoirs !!! ): " width="75px">
			<options>
				<option label="True" value="True"/>
				<option label="False" value="False" default="true" />
			</options>
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
import time

class BasePlugin:
	enabled = False

	def __init__(self):
		self.ListOfDevices = {}  # {DevicesAddresse : { status : status_de_detection, data : {ep list ou autres en fonctions du status}}, DevicesAddresse : ...}
		self.HBcount=0
		return

	def onStart(self):
		Domoticz.Log("onStart called")
		global ReqRcv
		global ZigateConn
		if Parameters["Mode6"] == "Debug":
			Domoticz.Debugging(1)
			DumpConfigToLog()
			#Domoticz.Log("Debugger started, use 'telnet 0.0.0.0 4444' to connect")
			#import rpdb
			#rpdb.set_trace()
		if Parameters["Mode1"] == "USB":
			ZigateConn = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None", Address=Parameters["SerialPort"], Baud=115200)
			ZigateConn.Connect()
		if Parameters["Mode1"] == "Wifi":
			ZigateConn = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ", Address=Parameters["Address"], Port=Parameters["Port"])
			ZigateConn.Connect()
		ReqRcv=''
		for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
			ID = Devices[x].DeviceID
			self.ListOfDevices[ID]={}
			self.ListOfDevices[ID]=eval(Devices[x].Options['Zigate'])
		#Import DeviceConf.txt
		with open(Parameters["HomeFolder"]+"DeviceConf.txt", 'r') as myfile:
			tmpread=myfile.read().replace('\n', '')
			self.DeviceConf=eval(tmpread)
			Domoticz.Debug("DeviceConf.txt = " + str(self.DeviceConf))
		#Import DeviceList.txt
		with open(Parameters["HomeFolder"]+"DeviceList.txt", 'r') as myfile2:
			Domoticz.Debug("DeviceList.txt open ")
			for line in myfile2:
				(key, val) = line.split(":",1)
				CheckDeviceList(self, key, val)
		return


	def onStop(self):
		ZigateConn.Disconnect()
		Domoticz.Log("onStop called")

	def onConnect(self, Connection, Status, Description):
		Domoticz.Log("onConnect called")
		global isConnected
		if (Status == 0):
			isConnected = True
			Domoticz.Log("Connected successfully")
			if Parameters["Mode3"] == "True":
			################### ZiGate - ErasePD ##################
				sendZigateCmd("0012", "")
			ZigateConf()
		else:
			Domoticz.Log("Failed to connect ("+str(Status)+")")
			Domoticz.Debug("Failed to connect ("+str(Status)+") with error: "+Description)
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
					ZigateDecode(self, ReqRcv) #demande de decodage de la trame recu
					ReqRcv=Tmprcv[Tmprcv.find('03')+2:]  # traite la suite du tampon
				else : 
					ZigateDecode(self, ReqRcv[:ReqRcv.find("0301")+2])
					ZigateDecode(self, ReqRcv[ReqRcv.find("0301")+2:])
					ReqRcv=Tmprcv[Tmprcv.find('03')+2:]
			except :
				Domoticz.Debug("onMessage - effacement de la trame suite a une erreur de decodage : " + ReqRcv)
				ReqRcv = Tmprcv[Tmprcv.find('03')+2:]  # efface le tampon en cas d erreur
		else : # while end of data is receive
			ReqRcv+=Tmprcv

#		#"""Read ZiGate output and split messages"""  from https://github.com/doudz/zigate/blob/master/zigate/core.py
#		ReqRcv += binascii.hexlify(Data).decode('utf-8')
#		endpos = ReqRcv.find('03')
#		startpos = 0
#		while endpos != -1 and len(ReqRcv[startpos :endpos+2])%2==0:
#			startpos = ReqRcv.find('01')
#			# stripping starting 0x01 & ending 0x03
#			ZigateDecode(self, ReqRcv[startpos :endpos+2])
#			ReqRcv = ReqRcv[endpos+2 :]
#			endpos = ReqRcv.find('03')

		return

	def onCommand(self, Unit, Command, Level, Hue):
		Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
		DOptions = Devices[Unit].Options
		Dtypename=DOptions['TypeName']
		Dzigate=eval(DOptions['Zigate'])
		EPin="01"
		if Dtypename=="Switch" or Dtypename=="Plug":
			ClusterSearch="0006"
		if Dtypename=="LvlControl" :
			ClusterSearch="0008"
		if Dtypename=="ColorControl" :
			ClusterSearch="0300"
		
		for tmpEp in self.ListOfDevices[Devices[Unit].DeviceID]['Ep'] :
			if ClusterSearch in self.ListOfDevices[Devices[Unit].DeviceID]['Ep'][tmpEp] : #switch cluster
				EPout=tmpEp
				EPfound=True
			else :
				EPfound=False
		if EPfound==False :
			EPout="01"


		if Command == "On" :
			#if Dtypename == "Switch" :
			sendZigateCmd("0092","02" + Devices[Unit].DeviceID + EPin + EPout + "01")
			UpdateDevice(Unit, 1, "On")
		if Command == "Off" :
			#if Dtypename == "Switch" :
			sendZigateCmd("0092","02" + Devices[Unit].DeviceID + EPin + EPout + "00")
			UpdateDevice(Unit, 0, "Off")

		if Command == "Set Level" :
			if Dtypename == "LvlControl" :
				if Level == 0 :
					sendZigateCmd("0092","02" + Devices[Unit].DeviceID + EPin + EPout + "00")
					UpdateDevice(Unit, 0, "Off")
				else :
					value=returnlen(2,hex(round(Level*255/100))[2:])
					sendZigateCmd("0081","02" + Devices[Unit].DeviceID + EPin + EPout + "00" + value + "0010")
					UpdateDevice(Unit, 1, "On")

			if Dtypename == "ColorControl" :
				if Level == 0 :
					sendZigateCmd("0092","02" + Devices[Unit].DeviceID + EPin + EPout + "00")
					UpdateDevice(Unit, 0, "Off")
				else :
					value=returnlen(4,hex(round(Level*1700/100))[2:])
					sendZigateCmd("00C0","02" + Devices[Unit].DeviceID + EPin + EPout + value + "0000")
					UpdateDevice(Unit, 1, "On")

	def onDisconnect(self, Connection):
		Domoticz.Log("onDisconnect called")

	def onHeartbeat(self):
		#Domoticz.Log("onHeartbeat called")
		Domoticz.Debug("ListOfDevices : " + str(self.ListOfDevices))
		for key in self.ListOfDevices :
			status=self.ListOfDevices[key]['Status']
			RIA=int(self.ListOfDevices[key]['RIA'])
			self.ListOfDevices[key]['Heartbeat']=str(int(self.ListOfDevices[key]['Heartbeat'])+1)
			# Envoi une demande Active Endpoint request
			if status=="004d" and self.ListOfDevices[key]['Heartbeat']=="1":
				Domoticz.Debug("Envoie une demande Active Endpoint request pour avoir la liste des EP du device adresse : " + key)
				sendZigateCmd("0045", str(key))
				self.ListOfDevices[key]['Status']="0045"
				self.ListOfDevices[key]['Heartbeat']="0"
			if status=="004d" and self.ListOfDevices[key]['Heartbeat']>="10":
				self.ListOfDevices[key]['Heartbeat']="0"
			if status=="0045" and self.ListOfDevices[key]['Heartbeat']>="10":
				self.ListOfDevices[key]['Heartbeat']="0"
				self.ListOfDevices[key]['Status']="004d"
			# Envoie une demande Simple Descriptor request par EP
			if status=="8045" and self.ListOfDevices[key]['Heartbeat']=="1":
				for cle in self.ListOfDevices[key]['Ep']:
					Domoticz.Debug("Envoie une demande Simple Descriptor request pour avoir les informations du EP :" + cle + ", du device adresse : " + key)
					sendZigateCmd("0043", str(key)+str(cle))
				self.ListOfDevices[key]['Status']="0043"
				self.ListOfDevices[key]['Heartbeat']="0"
			if status=="8045" and self.ListOfDevices[key]['Heartbeat']>="10":
				self.ListOfDevices[key]['Heartbeat']="0"
			if status=="0043" and self.ListOfDevices[key]['Heartbeat']>="10":
				self.ListOfDevices[key]['Heartbeat']="0"
				self.ListOfDevices[key]['Status']="8045"
		
			if status != "inDB" :
				if (RIA>=10 or self.ListOfDevices[key]['Model']!= {}) :
					#creer le device ds domoticz en se basant sur les clusterID ou le Model si il est connu
					IsCreated=False
					x=0
					nbrdevices=0
					for x in Devices:
						if Devices[x].DeviceID == str(key) :
							IsCreated = True
							Domoticz.Debug("HearBeat - Devices already exist. Unit=" + str(x))
					if IsCreated == False :
						Domoticz.Debug("HearBeat - creating device id : " + str(key))
						CreateDomoDevice(self, key)

				if self.ListOfDevices[key]['MacCapa']=="8e" : 
					if self.ListOfDevices[key]['ProfileID']=="c05e" :
						if self.ListOfDevices[key]['ZDeviceID']=="0220" :
							# exemple ampoule Tradfi
							self.ListOfDevices[key]['Model']="Ampoule.Tradfri"
							IsCreated=False
							x=0
							nbrdevices=0
							for x in Devices:
								if Devices[x].DeviceID == str(key) :
									IsCreated = True
									Domoticz.Debug("HearBeat - Devices already exist. Unit=" + str(x))
							if IsCreated == False :
								Domoticz.Debug("HearBeat - creating device id : " + str(key))
								CreateDomoDevice(self, key)

		ResetDevice("Motion",5)
		WriteDeviceList(self, 200)

		if (ZigateConn.Connected() != True):
			ZigateConn.Connect()
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
		Domoticz.Debug("Device Options: " + str(Devices[x].Options))
	return

def ZigateConf():

	################### ZiGate - set channel 11 ##################
	sendZigateCmd("0021", "0000" + returnlen(2,hex(int(Parameters["Mode5"]))[2:4]) + "00")

	################### ZiGate - Set Type COORDINATOR#################
	sendZigateCmd("0023","00")
	
	################### ZiGate - start network##################
	sendZigateCmd("0024","")

	################### ZiGate - discover mode 255sec ##################
	sendZigateCmd("0049","FFFC" + hex(int(Parameters["Mode2"]))[2:4] + "00")

def ZigateDecode(self, Data):  # supprime le transcodage
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
	ZigateRead(self, Out)

def ZigateEncode(Data):  # ajoute le transcodage
	Domoticz.Debug("ZigateEncode - Encodind data : " + Data)
	Out=""
	Outtmp=""
	Transcode = False
	for c in Data :
		Outtmp+=c
		if len(Outtmp)==2 :
			if Outtmp[0] == "1" and Outtmp != "10":
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

def sendZigateCmd(cmd,datas) :
	if datas == "" :
		length="0000"
	else :
		#length=returnlen(4,str(round(len(datas)/2)))
		length=returnlen(4,(str(hex(int(round(len(datas)/2)))).split('x')[-1]))  # by Cortexlegeni 
		Domoticz.Debug("sendZigateCmd - length is : " + str(length) )
	if datas =="" :
		checksumCmd=getChecksum(cmd,length,"0")
		if len(checksumCmd)==1 :
			strchecksum="0" + str(checksumCmd)
		else :
			strchecksum=checksumCmd
		lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(ZigateEncode(strchecksum)) + "03" 
	else :
		checksumCmd=getChecksum(cmd,length,datas)
		if len(checksumCmd)==1 :
			strchecksum="0" + str(checksumCmd)
		else :
			strchecksum=checksumCmd
		lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(ZigateEncode(strchecksum)) + str(ZigateEncode(datas)) + "03"   
	Domoticz.Debug("sendZigateCmd - Comand send : " + str(lineinput))
	if Parameters["Mode1"] == "USB":
		ZigateConn.Send(bytes.fromhex(str(lineinput)))	
	if Parameters["Mode1"] == "Wifi":
		ZigateConn.Send(bytes.fromhex(str(lineinput))+bytes("\r\n",'utf-8'),1)

def ZigateRead(self, Data):
	Domoticz.Debug("ZigateRead - decoded data : " + Data)
	MsgType=Data[2:6]
	MsgData=Data[12:len(Data)-4]
	MsgRSSI=Data[len(Data)-4:len(Data)-2]
	MsgLength=Data[6:10]
	MsgCRC=Data[10:12]
	Domoticz.Debug("ZigateRead - Message Type : " + MsgType + ", Data : " + MsgData + ", RSSI : " + MsgRSSI + ", Length : " + MsgLength + ", Checksum : " + MsgCRC)

	if str(MsgType)=="004d":  # Device announce
		Domoticz.Debug("ZigateRead - MsgType 004d - Reception Device announce : " + Data)
		Decode004d(self, MsgData)
		return
		
	elif str(MsgType)=="00d1":  #
		Domoticz.Debug("ZigateRead - MsgType 00d1 - Reception Touchlink status : " + Data)
		return
		
	elif str(MsgType)=="8000":  # Status
		Domoticz.Debug("ZigateRead - MsgType 8000 - reception status : " + Data)
		Decode8000(self, MsgData)
		return

	elif str(MsgType)=="8001":  # Log
		Domoticz.Debug("ZigateRead - MsgType 8001 - Reception log Level : " + Data)
		Decode8001(self, MsgData)
		return

	elif str(MsgType)=="8002":  #
		Domoticz.Debug("ZigateRead - MsgType 8002 - Reception Data indication : " + Data)
		return

	elif str(MsgType)=="8003":  #
		Domoticz.Debug("ZigateRead - MsgType 8003 - Reception Liste des cluster de l'objet : " + Data)
		return

	elif str(MsgType)=="8004":  #
		Domoticz.Debug("ZigateRead - MsgType 8004 - Reception Liste des attributs de l'objet : " + Data)
		return
		
	elif str(MsgType)=="8005":  #
		Domoticz.Debug("ZigateRead - MsgType 8005 - Reception Liste des commandes de l'objet : " + Data)
		return

	elif str(MsgType)=="8006":  #
		Domoticz.Debug("ZigateRead - MsgType 8006 - Reception Non factory new restart : " + Data)
		return

	elif str(MsgType)=="8007":  #
		Domoticz.Debug("ZigateRead - MsgType 8007 - Reception Factory new restart : " + Data)
		return

	elif str(MsgType)=="8010":  # Version
		Domoticz.Debug("ZigateRead - MsgType 8010 - Reception Version list : " + Data)
		Decode8010(self, MsgData)
		return

	elif str(MsgType)=="8014":  #
		Domoticz.Debug("ZigateRead - MsgType 8014 - Reception Permit join status response : " + Data)
		return
		
	elif str(MsgType)=="8024":  #
		Domoticz.Debug("ZigateRead - MsgType 8024 - Reception Network joined /formed : " + Data)
		return

	elif str(MsgType)=="8028":  #
		Domoticz.Debug("ZigateRead - MsgType 8028 - Reception Authenticate response : " + Data)
		return

	elif str(MsgType)=="8029":  #
		Domoticz.Debug("ZigateRead - MsgType 8029 - Reception Out of band commissioning data response : " + Data)
		return

	elif str(MsgType)=="802b":  #
		Domoticz.Debug("ZigateRead - MsgType 802b - Reception User descriptor notify : " + Data)
		return

	elif str(MsgType)=="802c":  #
		Domoticz.Debug("ZigateRead - MsgType 802c - Reception User descriptor response : " + Data)
		return

	elif str(MsgType)=="8030":  #
		Domoticz.Debug("ZigateRead - MsgType 8030 - Reception Bind response : " + Data)
		return

	elif str(MsgType)=="8031":  #
		Domoticz.Debug("ZigateRead - MsgType 8031 - Reception Unbind response : " + Data)
		return

	elif str(MsgType)=="8034":  #
		Domoticz.Debug("ZigateRead - MsgType 8034 - Reception Coplex Descriptor response : " + Data)
		return

	elif str(MsgType)=="8040":  #
		Domoticz.Debug("ZigateRead - MsgType 8040 - Reception Network address response : " + Data)
		return

	elif str(MsgType)=="8041":  #
		Domoticz.Debug("ZigateRead - MsgType 8041 - Reception IEEE address response : " + Data)
		return

	elif str(MsgType)=="8042":  #
		Domoticz.Debug("ZigateRead - MsgType 8042 - Reception Node descriptor response : " + Data)
		return

	elif str(MsgType)=="8043":  # Simple Descriptor Response
		Domoticz.Debug("ZigateRead - MsgType 8043 - Reception Simple descriptor response " + Data)
		Decode8043(self, MsgData)
		return

	elif str(MsgType)=="8044":  #
		Domoticz.Debug("ZigateRead - MsgType 8044 - Reception Power descriptor response : " + Data)
		return

	elif str(MsgType)=="8045":  # Active Endpoints Response
		Domoticz.Debug("ZigateRead - MsgType 8045 - Reception Active endpoint response : " + Data)
		Decode8045(self, MsgData)
		return

	elif str(MsgType)=="8046":  #
		Domoticz.Debug("ZigateRead - MsgType 8046 - Reception Match descriptor response : " + Data)
		return

	elif str(MsgType)=="8047":  #
		Domoticz.Debug("ZigateRead - MsgType 8047 - Reception Management leave response : " + Data)
		return

	elif str(MsgType)=="8048":  #
		Domoticz.Debug("ZigateRead - MsgType 8048 - Reception Leave indication : " + Data)
		return

	elif str(MsgType)=="804a":  #
		Domoticz.Debug("ZigateRead - MsgType 804a - Reception Management Network Update response : " + Data)
		return

	elif str(MsgType)=="804b":  #
		Domoticz.Debug("ZigateRead - MsgType 804b - Reception System server discovery response : " + Data)
		return

	elif str(MsgType)=="804e":  #
		Domoticz.Debug("ZigateRead - MsgType 804e - Reception Management LQI response : " + Data)
		return

	elif str(MsgType)=="8060":  #
		Domoticz.Debug("ZigateRead - MsgType 8060 - Reception Add group response : " + Data)
		return

	elif str(MsgType)=="8061":  #
		Domoticz.Debug("ZigateRead - MsgType 8061 - Reception Viex group response : " + Data)
		return

	elif str(MsgType)=="8062":  #
		Domoticz.Debug("ZigateRead - MsgType 8062 - Reception Get group Membership response : " + Data)
		return

	elif str(MsgType)=="8063":  #
		Domoticz.Debug("ZigateRead - MsgType 8063 - Reception Remove group response : " + Data)
		return

	elif str(MsgType)=="80a0":  #
		Domoticz.Debug("ZigateRead - MsgType 80a0 - Reception View scene response : " + Data)
		return

	elif str(MsgType)=="80a1":  #
		Domoticz.Debug("ZigateRead - MsgType 80a1 - Reception Add scene response : " + Data)
		return

	elif str(MsgType)=="80a2":  #
		Domoticz.Debug("ZigateRead - MsgType 80a2 - Reception Remove scene response : " + Data)
		return

	elif str(MsgType)=="80a3":  #
		Domoticz.Debug("ZigateRead - MsgType 80a3 - Reception Remove all scene response : " + Data)
		return

	elif str(MsgType)=="80a4":  #
		Domoticz.Debug("ZigateRead - MsgType 80a4 - Reception Store scene response : " + Data)
		return

	elif str(MsgType)=="80a6":  #
		Domoticz.Debug("ZigateRead - MsgType 80a6 - Reception Scene membership response : " + Data)
		return

	elif str(MsgType)=="8100":  #
		Domoticz.Debug("ZigateRead - MsgType 8100 - Reception Real individual attribute response : " + Data)
		return

	elif str(MsgType)=="8101":  # Default Response
		Domoticz.Debug("ZigateRead - MsgType 8101 - Default Response: " + Data)
		Decode8101(self, MsgData)
		return

	elif str(MsgType)=="8102":  # Report Individual Attribute response
		Domoticz.Debug("ZigateRead - MsgType 8102 - Report Individual Attribute response : " + Data)	
		Decode8102(self, MsgData)
		return
		
	elif str(MsgType)=="8110":  #
		Domoticz.Debug("ZigateRead - MsgType 8110 - Reception Write attribute response : " + Data)
		return

	elif str(MsgType)=="8120":  #
		Domoticz.Debug("ZigateRead - MsgType 8120 - Reception Configure reporting response : " + Data)
		return

	elif str(MsgType)=="8140":  #
		Domoticz.Debug("ZigateRead - MsgType 8140 - Reception Attribute discovery response : " + Data)
		return

	elif str(MsgType)=="8401":  # Reception Zone status change notification
		Domoticz.Debug("ZigateRead - MsgType 8401 - Reception Zone status change notification : " + Data)
		Decode8401(self, MsgData)
		return

	elif str(MsgType)=="8701":  # 
		Domoticz.Debug("ZigateRead - MsgType 8701 - Reception Router discovery confirm : " + Data)
		return

	elif str(MsgType)=="8702":  # APS Data Confirm Fail
		Domoticz.Debug("ZigateRead - MsgType 8702 -  Reception APS Data confirm fail : " + Data)
		Decode8702(self, MsgData)
		return

	else: # unknow or not dev function
		Domoticz.Debug("ZigateRead - Unknow Message Type for : " + Data)
		return
	
	return

def Decode004d(self, MsgData) : # Reception Device announce
	MsgSrcAddr=MsgData[0:4]
	MsgIEEE=MsgData[4:20]
	MsgMacCapa=MsgData[20:22]
	Domoticz.Debug("Decode004d - Reception Device announce : Source :" + MsgSrcAddr + ", IEEE : "+ MsgIEEE + ", Mac capa : " + MsgMacCapa)
	# tester si le device existe deja dans la base domoticz
	if DeviceExist(self, MsgSrcAddr)==False :
		self.ListOfDevices[MsgSrcAddr]['MacCapa']=MsgMacCapa
		self.ListOfDevices[MsgSrcAddr]['IEEE']=MsgIEEE
	return

def Decode8000(self, MsgData) : # Reception status
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
	Domoticz.Debug("Decode8000 - Reception status : " + MsgDataStatus + ", SQN : " + MsgDataSQN + ", Message : " + MsgDataMessage)
	return

def Decode8001(self, MsgData) : # Reception log Level
	MsgLogLvl=MsgData[0:2]
	MsgDataMessage=MsgData[2:len(MsgData)]
	Domoticz.Debug("ZigateRead - MsgType 8001 - Reception log Level 0x: " + MsgLogLvl + "Message : " + MsgDataMessage)
	return

def Decode8010(self,MsgData) : # Reception Version list
	MsgDataApp=MsgData[0:4]
	MsgDataSDK=MsgData[4:8]
	Domoticz.Debug("Decode8010 - Reception Version list : " + MsgData)
	return

def Decode8043(self, MsgData) : # Reception Simple descriptor response
	MsgDataSQN=MsgData[0:2]
	MsgDataStatus=MsgData[2:4]
	MsgDataShAddr=MsgData[4:8]
	MsgDataLenght=MsgData[8:10]
	Domoticz.Debug("Decode8043 - Reception Simple descriptor response : SQN : " + MsgDataSQN + ", Status : " + MsgDataStatus + ", short Addr : " + MsgDataShAddr + ", Lenght : " + MsgDataLenght)
	if self.ListOfDevices[MsgDataShAddr]['Status']!="inDB" :
		self.ListOfDevices[MsgDataShAddr]['Status']="8043"
	if int(MsgDataLenght,16)>0 :
		MsgDataEp=MsgData[10:12]
		MsgDataProfile=MsgData[12:16]
		self.ListOfDevices[MsgDataShAddr]['ProfileID']=MsgDataProfile
		MsgDataDeviceId=MsgData[16:20]
		self.ListOfDevices[MsgDataShAddr]['ZDeviceID']=MsgDataDeviceId
		MsgDataBField=MsgData[20:22]
		MsgDataInClusterCount=MsgData[22:24]
		Domoticz.Debug("Decode8043 - Reception Simple descriptor response : EP : " + MsgDataEp + ", Profile : " + MsgDataProfile + ", Device Id : " + MsgDataDeviceId + ", Bit Field : " + MsgDataBField)
		Domoticz.Debug("Decode8043 - Reception Simple descriptor response : In Cluster Count : " + MsgDataInClusterCount)
		i=1
		if int(MsgDataInClusterCount,16)>0 :
			while i <= int(MsgDataInClusterCount,16) :
				MsgDataCluster=MsgData[24+((i-1)*4):24+(i*4)]
				if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
					self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}
				Domoticz.Debug("Decode8043 - Reception Simple descriptor response : Cluster in: " + MsgDataCluster)
				MsgDataCluster=""
				i=i+1
		MsgDataOutClusterCount=MsgData[24+(int(MsgDataInClusterCount,16)*4):26+(int(MsgDataInClusterCount,16)*4)]
		Domoticz.Debug("Decode8043 - Reception Simple descriptor response : Out Cluster Count : " + MsgDataOutClusterCount)
		i=1
		if int(MsgDataOutClusterCount,16)>0 :
			while i <= int(MsgDataOutClusterCount,16) :
				MsgDataCluster=MsgData[24+((i-1)*4):24+(i*4)]
				if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] :
					self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster]={}
				Domoticz.Debug("Decode8043 - Reception Simple descriptor response : Cluster out: " + MsgDataCluster)
				MsgDataCluster=""
				i=i+1
	return

def Decode8045(self, MsgData) : # Reception Active endpoint response
	MsgDataSQN=MsgData[0:2]
	MsgDataStatus=MsgData[2:4]
	MsgDataShAddr=MsgData[4:8]
	MsgDataEpCount=MsgData[8:10]
	MsgDataEPlist=MsgData[10:len(MsgData)]
	Domoticz.Debug("Decode8045 - Reception Active endpoint response : SQN : " + MsgDataSQN + ", Status " + MsgDataStatus + ", short Addr " + MsgDataShAddr + ", EP count " + MsgDataEpCount + ", Ep list " + MsgDataEPlist)
	OutEPlist=""
	DeviceExist(self, MsgDataShAddr)
	if self.ListOfDevices[MsgDataShAddr]['Status']!="inDB" :
		self.ListOfDevices[MsgDataShAddr]['Status']="8045"
	for i in MsgDataEPlist :
		OutEPlist+=i
		if len(OutEPlist)==2 :
			if OutEPlist not in self.ListOfDevices[MsgDataShAddr]['Ep'] :
				self.ListOfDevices[MsgDataShAddr]['Ep'][OutEPlist]={}
				OutEPlist=""
	return

def Decode8101(self, MsgData) :  # Default Response
	MsgDataSQN=MsgData[0:2]
	MsgDataEp=MsgData[2:4]
	MsgClusterId=MsgData[4:8]
	MsgDataCommand=MsgData[8:10]
	MsgDataStatus=MsgData[10:12]
	Domoticz.Debug("Decode8101 - reception Default response : SQN : " + MsgDataSQN + ", EP : " + MsgDataEp + ", Cluster ID : " + MsgClusterId + " , Command : " + MsgDataCommand+ ", Status : " + MsgDataStatus)
	return

def Decode8102(self, MsgData) :  # Report Individual Attribute response
	MsgSQN=MsgData[0:2]
	MsgSrcAddr=MsgData[2:6]
	MsgSrcEp=MsgData[6:8]
	MsgClusterId=MsgData[8:12]
	MsgAttrID=MsgData[12:16]
	MsgAttType=MsgData[16:20]
	MsgAttSize=MsgData[20:24]
	MsgClusterData=MsgData[24:len(MsgData)]
	Domoticz.Debug("Decode8102 - reception data : " + MsgClusterData + " ClusterID : " + MsgClusterId + " Attribut ID : " + MsgAttrID + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp)	
	ReadCluster(self, MsgData) 
	return

def Decode8702(self, MsgData) : # Reception APS Data confirm fail
	MsgDataStatus=MsgData[0:2]
	MsgDataSrcEp=MsgData[2:4]
	MsgDataDestEp=MsgData[4:6]
	MsgDataDestMode=MsgData[6:8]
	MsgDataDestAddr=MsgData[8:12]
	MsgDataSQN=MsgData[12:14]
	Domoticz.Debug("Decode 8702 - Reception APS Data confirm fail : Status : " + MsgDataStatus + ", Source Ep : " + MsgDataSrcEp + ", Destination Ep : " + MsgDataDestEp + ", Destination Mode : " + MsgDataDestMode + ", Destination Address : " + MsgDataDestAddr + ", SQN : " + MsgDataSQN)
	return

def Decode8401(self, MsgData) : # Reception Zone status change notification
	Domoticz.Debug("Decode8401 - Reception Zone status change notification : " + MsgData)
	MsgSrcAddr=MsgData[10:14]
	MsgSrcEp=MsgData[2:4]
	MsgClusterData=MsgData[16:18]
	MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, "0006", MsgClusterData)
	return

def CreateDomoDevice(self, DeviceID) :
	#DeviceID=Addr #int(Addr,16)
	for Ep in self.ListOfDevices[DeviceID]['Ep'] :
		if self.ListOfDevices[DeviceID]['Type']== {} :
			Type=GetType(self, DeviceID, Ep).split("/")
		else :
			Type=self.ListOfDevices[DeviceID]['Type'].split("/")
		if Type !="" :
			for t in Type :
				Domoticz.Debug("CreateDomoDevice - Device ID : " + str(DeviceID) + " Device EP : " + str(Ep) + " Type : " + str(t) )
				if t=="Temp" : # Detecteur temp
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, TypeName="Temperature", Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Humi" : # Detecteur hum
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, TypeName="Humidity", Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Baro" : # Detecteur Baro
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, TypeName="Barometer", Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Door": # capteur ouverture/fermeture xiaomi
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=73 , Switchtype=2 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Motion" :  # detecteur de presence
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=73 , Switchtype=8 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="MSwitch"  :  # interrupteur multi lvl
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "||||", "LevelNames": "Push|1 Click|2 Clicks|3 Clicks|4 Clicks", "LevelOffHidden": "false", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="DSwitch"  :  # interrupteur double sur EP different
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "|||", "LevelNames": "Off|Left Click|Right Click|Both Click", "LevelOffHidden": "true", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="Smoke" :  # detecteur de fumee
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=73 , Switchtype=5 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Lux" :  # Lux sensors
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=246, Subtype=1 , Switchtype=0 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Switch":  # inter sans fils 1 touche 86sw1 xiaomi
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=73 , Switchtype=0 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="XCube" :  # Xiaomi Magic Cube
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Options = {"LevelActions": "||||||||", "LevelNames": "Off|Shake|Slide|90°|Clockwise|Tap|Move|Free Fall|Anti Clockwise|180°", "LevelOffHidden": "true", "SelectorStyle": "0","Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()

				if t=="Water" :  # detecteur d'eau 
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=73 , Switchtype=0 , Image=11 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="Plug" :  # prise pilote
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=73 , Switchtype=0 , Image=1 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="LvlControl" :  # variateur de luminosite
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=73, Switchtype=7 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

				if t=="ColorControl" :  # variateur de couleur
					self.ListOfDevices[DeviceID]['Status']="inDB"
					Domoticz.Device(DeviceID=str(DeviceID),Name=str(t) + " - " + str(DeviceID), Unit=len(Devices)+1, Type=244, Subtype=73 , Switchtype=7 , Options={"Zigate":str(self.ListOfDevices[DeviceID]), "TypeName":t}).Create()

def MajDomoDevice(self,DeviceID,Ep,clusterID,value) :
	Domoticz.Debug("MajDomoDevice - Device ID : " + str(DeviceID) + " - Device EP : " + str(Ep) + " - Type : " + str(clusterID)  + " - Value : " + str(value) )
	x=0
	Type=TypeFromCluster(clusterID)
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID) :
			DOptions = Devices[x].Options
			Dtypename=DOptions['TypeName']
			if Type==Dtypename=="Temp" :  # temperature
				UpdateDevice(x,0,str(value))				
			if Type==Dtypename=="Humi" :   # humidite
				UpdateDevice(x,int(value),"0")				
			if Type==Dtypename=="Baro" :  # barometre
				CurrentnValue=Devices[x].nValue
				CurrentsValue=Devices[x].sValue
				Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
				SplitData=CurrentsValue.split(";")
				valueBaro='%s;%s' % (value,SplitData[0])
				UpdateDevice(x,0,str(valueBaro))
			if Type=="Switch" and Dtypename=="Door" :  # porte / fenetre
				if value == "01" :
					state="Open"
				elif value == "00" :
					state="Closed"
				UpdateDevice(x,int(value),str(state))
			if Type==Dtypename=="Switch" : # switch simple
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				UpdateDevice(x,int(value),str(state))
			if Type=="Switch" and Dtypename=="Water" : # detecteur d eau
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				UpdateDevice(x,int(value),str(state))
			if Type=="Switch" and Dtypename=="Smoke" : # detecteur de fume
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				UpdateDevice(x,int(value),str(state))
			if Type=="Switch" and Dtypename=="MSwitch" : # multi lvl switch
				if value == "00" :
					state="00"
				if value == "01" :
					state="10"
				elif value == "02" :
					state="20"
				elif value == "03" :
					state="30"
				elif value == "04" :
					state="40"
				else :
					state="0"
				UpdateDevice(x,int(value),str(state))
			if Type=="Switch" and Dtypename=="DSwitch" : # double switch avec EP different   ====> a voir pour passer en deux switch simple ...
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
				UpdateDevice(x,int(data),str(state))
			if Type==Dtypename=="XCube" :  # cube xiaomi
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
					UpdateDevice(x,int(data),str(state))
			if Type==Dtypename=="Lux" :
				UpdateDevice(x,0,str(value))
			if Type==Dtypename=="Motion" :
				if value == "01" :
					state="On"
				elif value == "00" :
					state="Off"
				UpdateDevice(x,int(value),str(state))

def ResetDevice(Type,HbCount) :
	x=0
	for x in Devices: 
		try :
			LUpdate=Devices[x].LastUpdate
			LUpdate=time.mktime(time.strptime(LUpdate,"%Y-%m-%d %H:%M:%S"))
			current = time.time()
			DOptions = Devices[x].Options
			Dtypename=DOptions['TypeName']
			if (current-LUpdate)> 30 :
				if Dtypename=="Motion":
					value = "00"
					state="Off"
					#Devices[x].Update(nValue = int(value),sValue = str(state))
					UpdateDevice(x,int(value),str(state))	
		except :
			return

def DeviceExist(self, Addr) :
	#check in ListOfDevices
	if Addr in self.ListOfDevices and Addr != '' :
		if 'Status' in self.ListOfDevices[Addr] :
			return True
		else :
			initDeviceInList(self, Addr)
			return False
	else :  # devices inconnu ds listofdevices et ds db
		initDeviceInList(self, Addr)
		return False

def initDeviceInList(self, Addr) :
	self.ListOfDevices[Addr]={}
	self.ListOfDevices[Addr]['Ep']={}
	self.ListOfDevices[Addr]['Status']="004d"
	self.ListOfDevices[Addr]['Heartbeat']="0"
	self.ListOfDevices[Addr]['RIA']="0"
	self.ListOfDevices[Addr]['Battery']={}
	self.ListOfDevices[Addr]['Model']={}
	self.ListOfDevices[Addr]['MacCapa']={}
	self.ListOfDevices[Addr]['IEEE']={}
	self.ListOfDevices[Addr]['Type']={}
	self.ListOfDevices[Addr]['ProfileID']={}
	self.ListOfDevices[Addr]['ZDeviceID']={}

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
	found=False
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID):
			found==True
			Domoticz.Log("Devices exist in DB. Unit=" + str(x))
			CurrentnValue=Devices[x].nValue
			Domoticz.Log("CurrentnValue = " + str(CurrentnValue))
			CurrentsValue=Devices[x].sValue
			Domoticz.Log("CurrentsValue = " + str(CurrentsValue))
			Domoticz.Log("BatteryLvl = " + str(BatteryLvl))
			Devices[x].Update(nValue = int(CurrentnValue),sValue = str(CurrentsValue), BatteryLevel = BatteryLvl )
	if found==False :
		self.ListOfDevices[DeviceID]['Status']="004d"
		self.ListOfDevices[DeviceID]['Battery']=BatteryLvl

def UpdateDevice(Unit, nValue, sValue):
	# Make sure that the Domoticz device still exists (they can be deleted) before updating it 
	if (Unit in Devices):
		if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
			Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
			Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
	return		

def ReadCluster(self, MsgData):
	MsgSQN=MsgData[0:2]
	MsgSrcAddr=MsgData[2:6]
	MsgSrcEp=MsgData[6:8]
	MsgClusterId=MsgData[8:12]
	MsgAttrID=MsgData[12:16]
	MsgAttType=MsgData[16:20]
	MsgAttSize=MsgData[20:24]
	MsgClusterData=MsgData[24:len(MsgData)]
	tmpEp=""
	tmpClusterid=""
	if DeviceExist(self, MsgSrcAddr)==False :
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]={}
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]={}

	else :
		self.ListOfDevices[MsgSrcAddr]['RIA']=str(int(self.ListOfDevices[MsgSrcAddr]['RIA'])+1)
		try : 
			tmpEp=self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]
			try :
				tmpClusterid=self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]
			except : 
				self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]={}
		except :
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]={}
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]={}

	if MsgClusterId=="0000" :  # (General: Basic)
		if MsgAttrID=="ff01" :  # xiaomi battery lvl
			MsgBattery=MsgClusterData[4:8]
			try :
				ValueBattery='%s%s' % (str(MsgBattery[2:4]),str(MsgBattery[0:2]))
				ValueBattery=round(int(ValueBattery,16)/10/3)
				Domoticz.Debug("ReadCluster (8102) - ClusterId=0000 - MsgAttrID=ff01 - reception batteryLVL : " + str(ValueBattery) + " pour le device addr : " +  MsgSrcAddr)
				if self.ListOfDevices[MsgSrcAddr]['Status']=="inDB":
					UpdateBattery(MsgSrcAddr,ValueBattery)
				self.ListOfDevices[MsgSrcAddr]['Battery']=ValueBattery
			except :
				Domoticz.Debug("ReadCluster (8102) - ClusterId=0000 - MsgAttrID=ff01 - reception batteryLVL : erreur de lecture pour le device addr : " +  MsgSrcAddr)
				return
		elif MsgAttrID=="0005" :  # Model info Xiaomi
			MType=binascii.unhexlify(MsgClusterData).decode('utf-8')
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0000 - MsgAttrID=0005 - reception Model de Device : " + MType)
			self.ListOfDevices[MsgSrcAddr]['Model']=MType
			if self.ListOfDevices[MsgSrcAddr]['Model']!= {} and self.ListOfDevices[MsgSrcAddr]['Model'] in self.DeviceConf : # verifie que le model existe ds le fichier de conf des models
				Modeltmp=str(self.ListOfDevices[MsgSrcAddr]['Model'])
				for Ep in self.DeviceConf[Modeltmp]['Ep'] :
					if Ep in self.ListOfDevices[MsgSrcAddr]['Ep'] :
						for cluster in self.DeviceConf[Modeltmp]['Ep'][Ep] :
							if cluster not in self.ListOfDevices[MsgSrcAddr]['Ep'][Ep] :
								self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster]={}
					else :
						self.ListOfDevices[MsgSrcAddr]['Ep'][Ep]={}
						for cluster in self.DeviceConf[Modeltmp]['Ep'][Ep] :
							self.ListOfDevices[MsgSrcAddr]['Ep'][Ep][cluster]={}
				self.ListOfDevices[MsgSrcAddr]['Type']=self.DeviceConf[Modeltmp]['Type']
		else :
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0000 - reception heartbeat - Message attribut inconnu : " + MsgData)
			return
	
	elif MsgClusterId=="0006" :  # (General: On/Off) xiaomi
		if MsgAttrID=="0000":
			MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0006 - reception General: On/Off : " + str(MsgClusterData) )
		else :
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0006 - reception heartbeat - Message attribut inconnu : " + MsgData)
			return

	elif MsgClusterId=="0402" :  # (Measurement: Temperature) xiaomi
		#MsgValue=Data[len(Data)-8:len(Data)-4]
		if MsgClusterData[0] == "f" :  # cas temperature negative
			MsgClusterData=-(int(MsgClusterData,16)^int("FFFF",16))
		else : 
			MsgClusterData=int(MsgClusterData,16)
		MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, round(MsgClusterData/100,1))
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData/100,1))
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0402 - reception temp : " + str(MsgClusterData/100) )

	elif MsgClusterId=="0403" :  # (Measurement: Pression atmospherique) xiaomi   ### a corriger/modifier http://zigate.fr/xiaomi-capteur-temperature-humidite-et-pression-atmospherique-clusters/
		if MsgAttType=="0028":
			#MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgClusterData,8))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0403 - reception atm : " + str(MsgClusterData) )
			
		if MsgAttType=="0029" and MsgAttrID=="0000":
			#MsgValue=Data[len(Data)-8:len(Data)-4]
			MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/100,1))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/100,1)
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0403 - reception atm : " + str(round(int(MsgClusterData,16),1)))
			
		if MsgAttType=="0029" and MsgAttrID=="0010":
			#MsgValue=Data[len(Data)-8:len(Data)-4]
			MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/10,1))
			self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/10,1)
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0403 - reception atm : " + str(round(int(MsgClusterData,16)/10,1)))

	elif MsgClusterId=="0405" :  # (Measurement: Humidity) xiaomi
		#MsgValue=Data[len(Data)-8:len(Data)-4]
		MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,round(int(MsgClusterData,16)/100,1))
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=round(int(MsgClusterData,16)/100,1)
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0405 - reception hum : " + str(int(MsgClusterData,16)/100) )

	elif MsgClusterId=="0406" :  # (Measurement: Occupancy Sensing) xiaomi
		MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0406 - reception Occupancy Sensor : " + str(MsgClusterData) )

	elif MsgClusterId=="0400" :  # (Measurement: LUX) xiaomi
		MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,str(int(MsgClusterData,16) ))
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0400 - reception LUX Sensor : " + str(MsgClusterData) )
		
	elif MsgClusterId=="0012" :  # Magic Cube Xiaomi
		MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0012 - reception Xiaomi Magic Cube Value : " + str(MsgClusterData) )
		
	elif MsgClusterId=="000c" :  # Magic Cube Xiaomi rotation
		MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgClusterData)
		self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]=MsgClusterData
		Domoticz.Debug("ReadCluster (8102) - ClusterId=000c - reception Xiaomi Magic Cube Value Vert Rot : " + str(MsgClusterData) )
		
	else :
		Domoticz.Debug("ReadCluster (8102) - Error/unknow Cluster Message : " + MsgClusterId)
		return

def CheckType(self, MsgSrcAddr) :
	Domoticz.Debug("CheckType of device : " + MsgSrcAddr)
	x=0
	found=False
	for x in Devices:
		if Devices[x].DeviceID == str(MsgSrcAddr) :
			found=True
	
	if found==False :
		#check type with domoticz device type then add or del then re add device
		self.ListOfDevices[MsgSrcAddr]['Status']="inDB"

def GetType(self, Addr, Ep) :
	if self.ListOfDevices[Addr]['Model']!={} and self.ListOfDevices[Addr]['Model'] in self.DeviceConf :  # verifie si le model a ete detecte et est connu dans le fichier DeviceConf.txt
		Type = self.DeviceConf[self.ListOfDevices[Addr]['Model']]['Type']
		Domoticz.Debug("GetType - Type was set to : " + str(Type) )
	else :
		Type=""
		for cluster in self.ListOfDevices[Addr]['Ep'][Ep] :
			Domoticz.Debug("GetType - Type will be set to : " + str(Type) )
			Domoticz.Debug("GetType - check Type for Cluster : " + str(cluster) )
			if Type != "" and Type[:1]!="/" :
				Type+="/"
			Type+=TypeFromCluster(cluster)
		#Type+=Type
		Type=Type.replace("/////","/")
		Type=Type.replace("////","/")
		Type=Type.replace("///","/")
		Type=Type.replace("//","/")
		if Type[:-1]=="/" :
			Type = Type[:-1]
		if Type[0:]=="/" :
			Type = Type[1:]
		if Type != "" :
			self.ListOfDevices[Addr]['Type']=Type
			Domoticz.Debug("GetType - Type is now set to : " + str(Type) )
	return Type

def TypeFromCluster(cluster):
	if cluster=="0405" :
		TypeFromCluster="Humi"
	elif cluster=="0406" :
		TypeFromCluster="Motion"
	elif cluster=="0400" :
		TypeFromCluster="Lux"
	elif cluster=="0403" :
		TypeFromCluster="Baro"
	elif cluster=="0402" :
		TypeFromCluster="Temp"
	elif cluster=="0006" :
		TypeFromCluster="Switch"
	elif cluster=="0500" :
		TypeFromCluster="Door"
	elif cluster=="0012" :
		TypeFromCluster="XCube"
	elif cluster=="000c" :
		TypeFromCluster="XCube"
	elif cluster=="0008" :
		TypeFromCluster="LvlControl"
	elif cluster=="0300" :
		TypeFromCluster="ColorControl"
	else :
		TypeFromCluster=""
	return TypeFromCluster

def WriteDeviceList(self, count):
	if self.HBcount>=count :
		with open(Parameters["HomeFolder"]+"DeviceList.txt", 'wt') as file:
			for key in self.ListOfDevices :
				file.write(key + " : " + str(self.ListOfDevices[key]) + "\n")
		Domoticz.Debug("Write DeviceList.txt = " + str(self.ListOfDevices))
		self.HBcount=0
	else :
		Domoticz.Debug("HB count = " + str(self.HBcount))
		self.HBcount=self.HBcount+1

def returnlen(taille , value) :
	while len(value)<taille:
		value="0"+value
	return str(value)

def CheckDeviceList(self, key, val) :
	Domoticz.Debug("CheckDeviceList - Address search : " + str(key))
	Domoticz.Debug("CheckDeviceList - with value : " + str(val))
	
	DeviceListVal=eval(val)
	if DeviceExist(self, key)==False :
		Domoticz.Debug("CheckDeviceList - Address will be add : " + str(key))
		self.ListOfDevices[key]['RIA']="10"
		self.ListOfDevices[key]['Ep']=DeviceListVal['Ep']
		if 'Type' in DeviceListVal :
			self.ListOfDevices[key]['Type']=DeviceListVal['Type']
		if 'Model' in DeviceListVal :
			self.ListOfDevices[key]['Model']=DeviceListVal['Model']
		if 'MacCapa' in DeviceListVal :
			self.ListOfDevices[key]['MacCapa']=DeviceListVal['MacCapa']
		if 'IEEE' in DeviceListVal :
			self.ListOfDevices[key]['IEEE']=DeviceListVal['IEEE']
		if 'ProfileID' in DeviceListVal :
			self.ListOfDevices[key]['ProfileID']=DeviceListVal['ProfileID']
		if 'ZDeviceID' in DeviceListVal :
			self.ListOfDevices[key]['ZDeviceID']=DeviceListVal['ZDeviceID']
		if 'Status' in DeviceListVal :
			self.ListOfDevices[key]['Status']=DeviceListVal['Status']
	return