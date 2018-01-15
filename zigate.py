## Trames Zigate 

def DecodeUnknow(self, MsgDate) :
	Domoticz.Debug("DecodeUnknow - Unknow Message Type for : " + Data)

def Decode00d1(self, MsgData) : 
	Domoticz.Debug("Decode00d1 - Reception Touchlink status : " + Data)
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

def Decode8001(self, MsgData) : # Reception log Level
	MsgLogLvl=MsgData[0:2]
	MsgDataMessage=MsgData[2:len(MsgData)]
	Domoticz.Debug("Decode8001 - Reception log Level 0x: " + MsgLogLvl + "Message : " + MsgDataMessage)

def Decode8002(self, MsgData) :
	Domoticz.Debug("Decode8002 - Reception Data indication : " + Data)
	return

def Decode8003(self, MsgData) :
	Domoticz.Debug("Decode8003 - Reception Liste des cluster de l'objet : " + Data)

def Decode8004(self, MsgData) :
	Domoticz.Debug("Decode8004 - Reception Liste des attributs de l'objet : " + Data)

def Decode8005(self, MsgData) :
	Domoticz.Debug("Decode8005 - Reception Liste des commandes de l'objet : " + Data)

def Decode8006(self, MsgData) :
	Domoticz.Debug("Decode8006 - Reception Non factory new restart : " + Data)

def Decode8007(self, MsgData) :
	Domoticz.Debug("Decode8007 - Reception Factory new restart : " + Data)

def Decode8010(self,MsgData) : # Reception Version list
	MsgDataApp=MsgData[0:4]
	MsgDataSDK=MsgData[4:8]
	Domoticz.Debug("Decode8010 - Reception Version list : " + MsgData)
	
def Decode8014(self, MsgData) :
	Domoticz.Debug("Decode8014 - Reception Permit join status response : " + Data)
	return

def Decode8024(self, MsgData) :
	Domoticz.Debug("Decode8024 - Reception Network joined /formed : " + Data)
	return

def Decode8028(self, MsgData) :
	Domoticz.Debug("Decode8028 - Reception Authenticate response : " + Data)
	return

def Decode8029(self, MsgData) :
	Domoticz.Debug("Decode8029 - Reception Out of band commissioning data response : " + Data)
	return


def Decode802b(self, MsgData) :
	Domoticz.Debug("Decode802b - Reception User descriptor notify : " + Data)
	return

def Decode802c(self, MsgData) :
	Domoticz.Debug("Decode802c - Reception User descriptor response : " + Data)
	return

def Decode8030(self, MsgData) :
	Domoticz.Debug("Decode8030 - Reception Bind response : " + Data)
	return

def Decode8031(self, MsgData) :
	Domoticz.Debug("Decode8031 - Reception Unbind response : " + Data)
	return

def Decode8034(self, MsgData) :
	Domoticz.Debug("Decode8034 - Reception Coplex Descriptor response : " + Data)
	return

def Decode8040(self, MsgData) :
	Domoticz.Debug("Decode8040 - Reception Network address response : " + Data)
	return

def Decode8041(self, MsgData) :
	Domoticz.Debug("Decode8041 - Reception IEEE address response : " + Data)
	return

def Decode8042(self, MsgData) :
	Domoticz.Debug("Decode8042 - Reception Node descriptor response : " + Data)
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

def Decode8044(self, MsgData) :
	Domoticz.Debug("Decode8044 - Reception Power descriptor response : " + Data)
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
def Decode8046(self, MsgData) :
	Domoticz.Debug("Decode8046 - Reception Match descriptor response : " + Data)
	return	

def Decode8047(self, MsgData) :
	Domoticz.Debug("Decode8047 - Reception Management leave response : " + Data)
	return	

def Decode8048(self, MsgData) :
	Domoticz.Debug("Decode8048 - Reception Leave indication : " + Data)
	return	

def Decode804a(self, MsgData) :
	Domoticz.Debug("Decode804a - Reception Management Network Update response : " + Data)
	return

def Decode804b(self, MsgData) :
	Domoticz.Debug("Decode804b - Reception System server discovery response : " + Data)
	return	

def Decode804e(self, MsgData) :
	Domoticz.Debug("Decode804e - Reception Management LQI response : " + Data)
	return	

def Decode8060(self, MsgData) :
	Domoticz.Debug("Decode8060 - Reception Add group response : " + Data)
	return	

def Decode8061(self, MsgData) :
	Domoticz.Debug("Decode8061 - Reception Viex group response : " + Data)
	return	

def Decode8062(self, MsgData) :
	Domoticz.Debug("Decode8062 - Reception Get group Membership response : " + Data)
	return	

def Decode8063(self, MsgData) :
	Domoticz.Debug("Decode8063 - Reception Remove group response : " + Data)
	return	

def Decode80a0(self, MsgData) :
	Domoticz.Debug("Decode80a0 - Reception View scene response : " + Data)
	return	

def Decode80a1(self, MsgData) :
	Domoticz.Debug("Decode80a1 - Reception Add scene response : " + Data)
	return	

def Decode80a2(self, MsgData) :
	Domoticz.Debug("Decode80a2 - Reception Remove scene response : " + Data)
	return	

def Decode80a3(self, MsgData) :
	Domoticz.Debug("Decode80a3 - Reception Remove all scene response : " + Data)
	return	

def Decode80a4(self, MsgData) :
	Domoticz.Debug("Decode80a4 - Reception Store scene response : " + Data)
	return	

def Decode80a6(self, MsgData) :
	Domoticz.Debug("Decode80a6 - Reception Scene membership response : " + Data)
	return	

def Decode8100(self, MsgData) :
	Domoticz.Debug("Decode8100 - Reception Real individual attribute response : " + Data)
	return	

	
def Decode8101(self, MsgData) :  # Default Response
	MsgDataSQN=MsgData[0:2]
	MsgDataEp=MsgData[2:4]
	MsgClusterId=MsgData[4:8]
	MsgDataCommand=MsgData[8:10]
	MsgDataStatus=MsgData[10:12]
	Domoticz.Debug("Decode8101 - reception Default response : SQN : " + MsgDataSQN + ", EP : " + MsgDataEp + ", Cluster ID : " + MsgClusterId + " , Command : " + MsgDataCommand+ ", Status : " + MsgDataStatus)

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

def Decode8110(self, MsgData) :
	Domoticz.Debug("Decode8110 - Reception Write attribute response : " + Data)
	return
	
def Decode8120(self, MsgData) :
	Domoticz.Debug("Decode8120 - Reception Configure reporting response : " + Data)
	return

def Decode8140(self, MsgData) :
	Domoticz.Debug("Decode8140 - Reception Attribute discovery response : " + Data)
	return

def Decode8401(self, MsgData) : # Reception Zone status change notification
	Domoticz.Debug("Decode8401 - Reception Zone status change notification : " + MsgData)
	MsgSrcAddr=MsgData[10:14]
	MsgSrcEp=MsgData[2:4]
	MsgClusterData=MsgData[16:18]
	MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, "0006", MsgClusterData)

def Decode8701(self, MsgData) :
	Domoticz.Debug("ZigateRead - MsgType 8701 - Reception Router discovery confirm : " + Data)
	return

def Decode8702(self, MsgData) : # Reception APS Data confirm fail
	MsgDataStatus=MsgData[0:2]
	MsgDataSrcEp=MsgData[2:4]
	MsgDataDestEp=MsgData[4:6]
	MsgDataDestMode=MsgData[6:8]
	MsgDataDestAddr=MsgData[8:12]
	MsgDataSQN=MsgData[12:14]
	Domoticz.Debug("Decode 8702 - Reception APS Data confirm fail : Status : " + MsgDataStatus + ", Source Ep : " + MsgDataSrcEp + ", Destination Ep : " + MsgDataDestEp + ", Destination Mode : " + MsgDataDestMode + ", Destination Address : " + MsgDataDestAddr + ", SQN : " + MsgDataSQN)

	
	
##Initilitation du dictionnaire, tout les messages appelerons la fonction "DecodeUnknow"
for num in range (0,0x10000) :
  Dict_DecodeData={str(hex(num))[2:5],DecodeUnknow}

#ImplÃ©ntation des messages dÃ©dÃ©pÃ©fiques :
Dict_DecodeData={"004d",Decode004d}
Dict_DecodeData={"00d1",Decode00d1}
Dict_DecodeData={"8000",Decode8000}
Dict_DecodeData={"8001",Decode8001}
Dict_DecodeData={"8002",Decode8002}
Dict_DecodeData={"8003",Decode8003}
Dict_DecodeData={"8004",Decode8004}
Dict_DecodeData={"8005",Decode8005}
Dict_DecodeData={"8006",Decode8006}
Dict_DecodeData={"8007",Decode8007}
Dict_DecodeData={"8010",Decode8010}
Dict_DecodeData={"8014",Decode8014}
Dict_DecodeData={"8024",Decode8024}
Dict_DecodeData={"8028",Decode8028}
Dict_DecodeData={"8029",Decode8029}
Dict_DecodeData={"802b",Decode802b}
Dict_DecodeData={"802c",Decode802c}
Dict_DecodeData={"8030",Decode8030}
Dict_DecodeData={"8031",Decode8031}
Dict_DecodeData={"8034",Decode8034}
Dict_DecodeData={"8040",Decode8040}
Dict_DecodeData={"8041",Decode8041}
Dict_DecodeData={"8042",Decode8042}
Dict_DecodeData={"8043",Decode8043}
Dict_DecodeData={"8044",Decode8044}
Dict_DecodeData={"8045",Decode8045}
Dict_DecodeData={"8046",Decode8046}
Dict_DecodeData={"8047",Decode8047}
Dict_DecodeData={"8048",Decode8048}
Dict_DecodeData={"804a",Decode804a}
Dict_DecodeData={"804b",Decode804b}
Dict_DecodeData={"804e",Decode804e}
Dict_DecodeData={"8060",Decode8060}
Dict_DecodeData={"8061",Decode8061}
Dict_DecodeData={"8062",Decode8062}
Dict_DecodeData={"8063",Decode8063}
Dict_DecodeData={"80a0",Decode80a0}
Dict_DecodeData={"80a1",Decode80a1}
Dict_DecodeData={"80a2",Decode80a2}
Dict_DecodeData={"80a3",Decode80a3}
Dict_DecodeData={"80a4",Decode80a4}
Dict_DecodeData={"80a6",Decode80a6}
Dict_DecodeData={"8100",Decode8100}
Dict_DecodeData={"8101",Decode8101}
Dict_DecodeData={"8102",Decode8102}
Dict_DecodeData={"8110",Decode8110}
Dict_DecodeData={"8120",Decode8120}
Dict_DecodeData={"8140",Decode8140}
Dict_DecodeData={"8401",Decode8401}
Dict_DecodeData={"8701",Decode8701}
Dict_DecodeData={"8702",Decode8702}
