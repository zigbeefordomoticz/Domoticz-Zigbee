#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: errorCodes.py

    Description: Table with all error codes

"""


ZIGATE_CODES = {
    "00": "Success",
    "01": "Incorrect Parameters",
    "02": "Unhandled Command",
    "03": "Command Failed",
    "04": "Busy",
    "05": "Stack Already Started",
    "14": "E_ZCL_ERR_ZBUFFER_FAIL",
    "15": "E_ZCL_ERR_ZTRANSMIT_FAIL",
}

APS_CODES = {
    "a0": "A transmit request failed since the ASDU is too large and fragmentation is not supported",
    "a1": "A received fragmented frame could not be defragmented at the current time",
    "a2": "A received fragmented frame could not be defragmented since the device does not support fragmentation",
    "a3": "A parameter value was out of range",
    "a4": "An APSME-UNBIND.request failed due to the requested binding link not existing in the binding table",
    "a5": "An APSME-REMOVE-GROUP.request has been issued with a group identified that does not appear in the group table",
    "a6": "A parameter value was invalid or out of range",
    "a7": "An APSDE-DATA.request requesting ack transmission failed due to no ack being received",
    "a8": "An APSDE-DATA.request with a destination addressing mode set to 0x00 failed due to there being no devices bound to this device",
    "a9": "An APSDE-DATA.request with a destination addressing mode set to 0x03 failed due to no corresponding short address found in the address map table",
    "aa": "An APSDE-DATA.request with a destination addressing mode set to 0x00 failed due to a binding table not being supported on the device",
    "ab": "An ASDU was received that was secured using a link key",
    "ac": "An ASDU was received that was secured using a network key",
    "ad": "An APSDE-DATA.request requesting security has resulted in an error during the corresponding security processing",
    "ae": "An APSME-BIND.request or APSME.ADDGROUP.request issued when the binding or group tables, respectively, were full.",
    "af": "An ASDU was received without any security.",
    "b0": "An APSME-GET.request or APSMESET. request has been issued with an unknown attribute identifier.",
}

NWK_CODES = {
    "c1": "An invalid or out-of-range parameter has been passed",
    "c2": "Request cannot be processed",
    "c3": "NLME-JOIN.request not permitted",
    "c4": "NLME-NETWORK-FORMATION.request failed",
    "c5": "NLME-DIRECT-JOIN.request failure - device already present",
    "c6": "NLME-SYNC.request has failed",
    "c7": "NLME-DIRECT-JOIN.request failure - no space in Router table",
    "c8": "NLME-LEAVE.request failure - device not in Neighbour table",
    "c9": "NLME-GET/SET.request unknown attribute identified",
    "ca": "NLME-JOIN.request detected no networks",
    "cb": "Reserved",
    "cc": "Security processing has failed on outgoing frame due to maximum frame counter",
    "cd": "Security processing has failed on outgoing frame due to no key",
    "ce": "Security processing has failed on outgoing frame due CCM",
    "cf": "Attempt at route discovery has failed due to lack of table space",
    "d0": "Attempt at route discovery has failed due to any reason except lack of table space",
    "d1": "NLDE-DATA.request has failed due to routing failure on sending device",
    "d2": "Broadcast or broadcast-mode multicast has failed as there is no room in BTT",
    "d3": "Unicast mode multi-cast frame was discarded pending route discovery",
    "d4": "Unicast frame does not have a route available but it is buffered for automatic resend",
}

MAC_CODES = {
    "e0": "Beacon loss after synchronisation request.",
    "e1": "CSMA/CA channel access failure.",
    "e2": "GTS request denied",
    "e3": "Could not disable transmit or receive",
    "e4": "Incoming frame failed security check",
    "e5": "Frame too long, after security processing, to be sent",
    "e6": "GTS transmission failed",
    "e7": "Purge request failed to find entry in queue ",
    "e8": "Out-of-range parameter in function",
    "e9": "No acknowledgement received when expected ",
    "ea": "Scan failed to find any beacons",
    "eb": "No response data after a data request",
    "ec": "No allocated network (short) address for operation ",
    "ed": "Receiver-enable request could not be executed, as CAP finished",
    "ee": "PAN ID conflict has been detected",
    "ef": "Co-ordinator realignment has been received ",
    "f0": "Pending transaction has expired and data discarded ",
    "f1": "No capacity to store transaction",
    "f2": "Receiver-enable request could not be executed, as in transmit state",
    "f3": "Appropriate key is not available in ACL",
    "f4": "PIB Set/Get on unsupported attribute",
}

ZCL_EXTENDED_ERROR_CODES = {
    "01": "Fatal error - retrying will cause the error again",
    "02": "Endpoint is not valid for loopback (fatal error)",
    "03": "No output cluster in the Simple descriptor for this endpoint/cluster (fatal error)",
    "04": "Fragmented data requests must be sent with APS ack (fatal error)",
    "05": "Bad parameter has been passed to the command manager (fatal error)",
    "06": "Address parameter is out-of-range (fatal error), e.g. broadcast address when calling unicast function",
    "07": "TX ACK bit has been set when attempting to post to a local endpoint (fatal error)",
    "08": "Resource error/shortage - retrying may succeed",
    "80": "No free NPDUs (resource error) - the number of NPDUs is set in the Number of NPDUs property of the PDU Manager section of the ZPS Configuration Editor ",
    "81": "No free APDUs (resource error) - the number of APDUs is set in the Instances property of the appropriate APDU child of the PDU Manager section of the ZPS Configuration Editor",
    "82": "No free simultaneous data request handles (resource error) - the number of handles is set in the Maximum Number of Simultaneous Data Requests field of the APS layer configuration section of the ZPS Configuration Editor",
    "83": "No free APS acknowledgement handles (resource error) - the number of handles is set in the Maximum Number of Simultaneous Data Requests with Acks field of the APS layer configuration section of the ZPS Configuration Editor",
    "84": "No free fragment record handles (resource error) - the number of handles is set in the Maximum Number of Transmitted Simultaneous Fragmented Messages field of the APS layer configuration section of the ZPS Configuration Editor",
    "85": "No free MCPS request descriptors (resource error) - there are 8 MCPS request descriptors and these are only ever likely to be exhausted under a very heavy network load or when trying to transmit too many frames too close together",
    "86": "Loopback send is currently busy (resource error) - there can be only one loopback request at a time",
    "87": "No free entries in the extended address table (resource error) - this table is configured in the ZPS Configuration Editor",
    "88": "Simple descriptor does not exist for this endpoint/cluster",
    "89": "Bad parameter has been found while processing an APSDE request or response",
    "8a": "No routing table entries free",
    "8b": "No Broadcast transaction table entries free",
}


def DisplayStatusCode(StatusCode):

    StatusMsg = ""
    if StatusCode in ZIGATE_CODES:
        return "ZIGATE - [%s] %s" % (StatusCode, ZIGATE_CODES[StatusCode])

    elif StatusCode in APS_CODES:
        return "APS - [%s] %s" % (StatusCode, APS_CODES[StatusCode])

    elif StatusCode in NWK_CODES:
        return "NWK - [%s] %s" % (StatusCode, NWK_CODES[StatusCode])

    elif StatusCode in MAC_CODES:
        return "MAC - [%s] %s" % (StatusCode, MAC_CODES[StatusCode])

    else:
        return "Unknown code : %s" % StatusCode
