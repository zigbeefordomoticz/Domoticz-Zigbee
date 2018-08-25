	elif str(StatusCode)=="c6" : StatusMsg="NLME-SYNC.request has failed"
	elif str(StatusCode)=="c7" : StatusMsg="NLME-DIRECT-JOIN.request failure - no space in Router table"
	elif str(StatusCode)=="c8" : StatusMsg="NLME-LEAVE.request failure - device not in Neighbour table"
	elif str(StatusCode)=="c9" : StatusMsg="NLME-GET/SET.request unknown attribute identified"
	elif str(StatusCode)=="ca" : StatusMsg="NLME-JOIN.request detected no networks"
	elif str(StatusCode)=="cb" : StatusMsg="Reserved"
	elif str(StatusCode)=="cc" : StatusMsg="Security processing has failed on outgoing frame due to maximum frame counter"
	elif str(StatusCode)=="cd" : StatusMsg="Security processing has failed on outgoing frame due to no key"
	elif str(StatusCode)=="ce" : StatusMsg="Security processing has failed on outgoing frame due CCM"
	elif str(StatusCode)=="cf" : StatusMsg="Attempt at route discovery has failed due to lack of table space"
	elif str(StatusCode)=="d0" : StatusMsg="Attempt at route discovery has failed due to any reason except lack of table space"
	elif str(StatusCode)=="d1" : StatusMsg="NLDE-DATA.request has failed due to routing failure on sending device"
	elif str(StatusCode)=="d2" : StatusMsg="Broadcast or broadcast-mode multicast has failed as there is no room in BTT"
	elif str(StatusCode)=="d3" : StatusMsg="Unicast mode multi-cast frame was discarded pending route discovery"
	elif str(StatusCode)=="d4" : StatusMsg="Unicast frame does not have a route available but it is buffered for automatic resend"

	elif str(StatusCode)=="a0": StatusMsg="A transmit request failed since the ASDU is too large and fragmentation is not supported"
	elif str(StatusCode)=="a1": StatusMsg="A received fragmented frame could not be defragmented at the current time"
	elif str(StatusCode)=="a2": StatusMsg="A received fragmented frame could not be defragmented since the device does not support fragmentation"
	elif str(StatusCode)=="a3": StatusMsg="A parameter value was out of range"
	elif str(StatusCode)=="a4": StatusMsg="An APSME-UNBIND.request failed due to the requested binding link not existing in the binding table"
	elif str(StatusCode)=="a5": StatusMsg="An APSME-REMOVE-GROUP.request has been issued with a group identified that does not appear in the group table"
	elif str(StatusCode)=="a6": StatusMsg="A parameter value was invaid or out of range"
	elif str(StatusCode)=="a7": StatusMsg="An APSDE-DATA.request requesting ack transmission failed due to no ack being received"
	elif str(StatusCode)=="a8": StatusMsg="An APSDE-DATA.request with a destination addressing mode set to 0x00 failed due to there being no devices bound to this device"
	elif str(StatusCode)=="a9": StatusMsg="An APSDE-DATA.request with a destination addressing mode set to 0x03 failed due to no corresponding short address found in the address map table"
	elif str(StatusCode)=="aa": StatusMsg="An APSDE-DATA.request with a destination addressing mode set to 0x00 failed due to a binding table not being supported on the device"
	elif str(StatusCode)=="ab": StatusMsg="An ASDU was received that was secured using a link key"
	elif str(StatusCode)=="ac": StatusMsg="An ASDU was received that was secured using a network key"
	elif str(StatusCode)=="ad": StatusMsg="An APSDE-DATA.request requesting security has resulted in an error during the corresponding security processing"

	else:                       StatusMsg="Unknown code : " + StatusCode


	return StatusMsg


def removeZigateDevice( self, key ) :
	# remove a device in Zigate
	# Key is the short address of the device
	# extended address is ieee address
	
	if key in  self.ListOfDevices:
		ieee =  self.ListOfDevices[key]['IEEE']
		Domoticz.Log("Remove from Zigate Device = " + str(key) + " IEEE = " +str(ieee) )
		sendZigateCmd("0026", str(ieee) + str(ieee) )
	else :
		Domoticz.Log("Unknow device to be removed - Device  = " + str(key))
		
	return
