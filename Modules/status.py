#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_status.py

    Description: Display Status

"""

def DisplayStatusCode( StatusCode ) :
    # As described in https://www.nxp.com/docs/en/user-guide/JN-UG-3113.pdf section 10.2

    StatusMsg=""
    if str(StatusCode) =="00" :   
        StatusMsg="Success"
    elif str(StatusCode) == "01" : 
        StatusMsg ="Incorrect Parameters"
    elif str(StatusCode) == "02" : 
        StatusMsg ="Unhandled Command"
    elif str(StatusCode) == "03" : 
        StatusMsg ="Command Failed"
    elif str(StatusCode) == "04" : 
        StatusMsg ="Busy"
    elif str(StatusCode) == "05" : 
        StatusMsg ="Stack Already Started"
    
# ZCL return status code
    
#NWK CODES    
    elif str(StatusCode)=="c1" : 
        StatusMsg="An invalid or out-of-range parameter has been passed"
    elif str(StatusCode)=="c2" : 
        StatusMsg="Request cannot be processed"
    elif str(StatusCode)=="c3" : 
        StatusMsg="NLME-JOIN.request not permitted"
    elif str(StatusCode)=="c4" : 
        StatusMsg="NLME-NETWORK-FORMATION.request failed"
    elif str(StatusCode)=="c5" : 
        StatusMsg="NLME-DIRECT-JOIN.request failure - device already present"
    elif str(StatusCode)=="c6" : 
        StatusMsg="NLME-SYNC.request has failed"
    elif str(StatusCode)=="c7" : 
        StatusMsg="NLME-DIRECT-JOIN.request failure - no space in Router table"
    elif str(StatusCode)=="c8" : 
        StatusMsg="NLME-LEAVE.request failure - device not in Neighbour table"
    elif str(StatusCode)=="c9" : 
        StatusMsg="NLME-GET/SET.request unknown attribute identified"
    elif str(StatusCode)=="ca" : 
        StatusMsg="NLME-JOIN.request detected no networks"
    elif str(StatusCode)=="cb" : 
        StatusMsg="Reserved"
    elif str(StatusCode)=="cc" : 
        StatusMsg="Security processing has failed on outgoing frame due to maximum frame counter"
    elif str(StatusCode)=="cd" : 
        StatusMsg="Security processing has failed on outgoing frame due to no key"
    elif str(StatusCode)=="ce" : 
        StatusMsg="Security processing has failed on outgoing frame due CCM"
    elif str(StatusCode)=="cf" : 
        StatusMsg="Attempt at route discovery has failed due to lack of table space"
    elif str(StatusCode)=="d0" : 
        StatusMsg="Attempt at route discovery has failed due to any reason except lack of table space"
    elif str(StatusCode)=="d1" : 
        StatusMsg="NLDE-DATA.request has failed due to routing failure on sending device"
    elif str(StatusCode)=="d2" : 
        StatusMsg="Broadcast or broadcast-mode multicast has failed as there is no room in BTT"
    elif str(StatusCode)=="d3" : 
        StatusMsg="Unicast mode multi-cast frame was discarded pending route discovery"
    elif str(StatusCode)=="d4" : 
        StatusMsg="Unicast frame does not have a route available but it is buffered for automatic resend"

#APS CODES
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
    elif str(StatusCode)=="ae": StatusMsg="An APSME-BIND.request or APSME.ADDGROUP.request issued when the binding or group tables, respectively, were full."
    elif str(StatusCode)=="af": StatusMsg="An ASDU was received without any security."
    elif str(StatusCode)=="b0": StatusMsg="An APSME-GET.request or APSMESET. request has been issued with an unknown attribute identifier."

#ZDP CODES
    elif str(StatusCode)=="80": StatusMsg="The supplied request type was invalid."
    elif str(StatusCode)=="81": StatusMsg="The requested device did not exist on a device following a child descriptor request to a parent."
    elif str(StatusCode)=="82": StatusMsg="The supplied endpoint was equal to 0x00 or between 0xF1 and 0xFF"
    elif str(StatusCode)=="83": StatusMsg="The requested endpoint is not described by a Simple descriptor."
    elif str(StatusCode)=="84": StatusMsg="The requested optional feature is not supported on the target device."
    elif str(StatusCode)=="85": StatusMsg="A timeout has occurred with the requested operation."
    elif str(StatusCode)=="86": StatusMsg="The End Device bind request was unsuccessful due to a failure to match any suitable clusters."
    elif str(StatusCode)=="88": StatusMsg="The unbind request was unsuccessful due to the Coordinator or source device not having an entry in its binding table to unbind."
    elif str(StatusCode)=="89": StatusMsg="A child descriptor was not available following a discovery request to a parent."
    elif str(StatusCode)=="8a": StatusMsg="The device does not have storage space to support the requested operation."
    elif str(StatusCode)=="8b": StatusMsg="The device is not in the proper state to support the requested operation."
    elif str(StatusCode)=="8c": StatusMsg="The device does not have table space to support the operation."
    elif str(StatusCode)=="8d": StatusMsg=" The permissions configuration table on the target indicates that the request is not authorised from this device."
    
#MAC CODES
    elif str(StatusCode)=="e0": StatusMsg="Beacon loss after synchronisation request."
    elif str(StatusCode)=="e1": StatusMsg="CSMA/CA channel access failure."
    elif str(StatusCode)=="e2": StatusMsg="GTS request denied"
    elif str(StatusCode)=="e3": StatusMsg="Could not disable transmit or receive"
    elif str(StatusCode)=="e4": StatusMsg="Incoming frame failed security check"
    elif str(StatusCode)=="e5": StatusMsg="Frame too long, after security processing, to be sent"
    elif str(StatusCode)=="e6": StatusMsg="GTS transmission failed"
    elif str(StatusCode)=="e7": StatusMsg="Purge request failed to find entry in queue "
    elif str(StatusCode)=="e8": StatusMsg="Out-of-range parameter in function"
    elif str(StatusCode)=="e9": StatusMsg="No acknowledgement received when expected "
    elif str(StatusCode)=="ea": StatusMsg="Scan failed to find any beacons"
    elif str(StatusCode)=="eb": StatusMsg="No response data after a data request"
    elif str(StatusCode)=="ec": StatusMsg="No allocated network (short) address for operation "
    elif str(StatusCode)=="ed": StatusMsg="Receiver-enable request could not be executed, as CAP finished"
    elif str(StatusCode)=="ee": StatusMsg="PAN ID conflict has been detected"
    elif str(StatusCode)=="ef": StatusMsg="Co-ordinator realignment has been received "
    elif str(StatusCode)=="f0": StatusMsg="Pending transaction has expired and data discarded "
    elif str(StatusCode)=="f1": StatusMsg="No capacity to store transaction"
    elif str(StatusCode)=="f2": StatusMsg="Receiver-enable request could not be executed, as in transmit state"
    elif str(StatusCode)=="f3": StatusMsg="Appropriate key is not available in ACL"
    elif str(StatusCode)=="f4": StatusMsg="PIB Set/Get on unsupported attribute"

#EXTENDED ERROR CODES
    elif str(StatusCode)=="01": StatusMsg="Fatal error - retrying will cause the error again"
    elif str(StatusCode)=="02": StatusMsg="Endpoint is not valid for loopback (fatal error)"
    elif str(StatusCode)=="03": StatusMsg="No output cluster in the Simple descriptor for this endpoint/cluster (fatal error)"
    elif str(StatusCode)=="04": StatusMsg="Fragmented data requests must be sent with APS ack (fatal error)"
    elif str(StatusCode)=="05": StatusMsg="Bad parameter has been passed to the command manager (fatal error)"
    elif str(StatusCode)=="06": StatusMsg="Address parameter is out-of-range (fatal error), e.g. broadcast address when calling unicast function"
    elif str(StatusCode)=="07": StatusMsg="TX ACK bit has been set when attempting to post to a local endpoint (fatal error)"
    elif str(StatusCode)=="08": StatusMsg="Resource error/shortage - retrying may succeed"
    elif str(StatusCode)=="80": StatusMsg="No free NPDUs (resource error) - the number of NPDUs is set in the 'Number of NPDUs' property of the 'PDU Manager' section of the ZPS Configuration Editor "
    elif str(StatusCode)=="81": StatusMsg="No free APDUs (resource error) - the number of APDUs is set in the 'Instances' property of the appropriate 'APDU' child of the 'PDU Manager' section of the ZPS Configuration Editor"
    elif str(StatusCode)=="82": StatusMsg="No free simultaneous data request handles (resource error) - the number of handles is set in the 'Maximum Number of Simultaneous Data Requests' field of the 'APS layer configuration' section of the ZPS Configuration Editor"
    elif str(StatusCode)=="83": StatusMsg="No free APS acknowledgement handles (resource error) - the number of handles is set in the 'Maximum Number of Simultaneous Data Requests with Acks' field of the 'APS layer configuration' section of the ZPS Configuration Editor"
    elif str(StatusCode)=="84": StatusMsg="No free fragment record handles (resource error) - the number of handles is set in the 'Maximum Number of Transmitted Simultaneous Fragmented Messages' field of the 'APS layer configuration' section of the ZPS Configuration Editor"
    elif str(StatusCode)=="85": StatusMsg="No free MCPS request descriptors (resource error) - there are 8 MCPS request descriptors and these are only ever likely to be exhausted under a very heavy network load or when trying to transmit too many frames too close together"
    elif str(StatusCode)=="86": StatusMsg="Loopback send is currently busy (resource error) - there can be only one loopback request at a time"
    elif str(StatusCode)=="87": StatusMsg="No free entries in the extended address table (resource error) - this table is configured in the ZPS Configuration Editor"
    elif str(StatusCode)=="88": StatusMsg="Simple descriptor does not exist for this endpoint/cluster"
    elif str(StatusCode)=="89": StatusMsg="Bad parameter has been found while processing an APSDE request or response"
    elif str(StatusCode)=="8a": StatusMsg="No routing table entries free"
    elif str(StatusCode)=="8b": StatusMsg="No Broadcast transaction table entries free"

    else:                       StatusMsg="Unknown code : " + StatusCode


    return StatusMsg



