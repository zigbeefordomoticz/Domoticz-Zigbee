#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: status.py

    Description: Display Status
    As described in https://www.nxp.com/docs/en/user-guide/JN-UG-3113.pdf section 10.2

"""

STATUS_CODE = {
    '00': 'Success',
    '01': 'Incorrect Parameters',
    '03': 'Command Failed',
    '04': 'Busy',
    '05': 'Stack Already Started'
}

ZCL_NWK_CODE = {
    'c1' : 'An invalid or out-of-range parameter has been passed',
    'c2' : 'Request cannot be processed',
    'c3' : 'NLME-JOIN.request not permitted',
    'c4' : 'NLME-NETWORK-FORMATION.request failed',
    'c5' : 'NLME-DIRECT-JOIN.request failure - device already present',
    'c6' : 'NLME-SYNC.request has failed',
    'c7' : 'NLME-DIRECT-JOIN.request failure - no space in Router table',
    'c8' : 'NLME-LEAVE.request failure - device not in Neighbour table',
    'c9' : 'NLME-GET/SET.request unknown attribute identified',
    'ca' : 'NLME-JOIN.request detected no networks',
    'cb' : 'Reserved',
    'cc' : 'Security processing has failed on outgoing frame due to maximum frame counter',
    'cd' : 'Security processing has failed on outgoing frame due to no key',
    'ce' : 'Security processing has failed on outgoing frame due CCM',
    'cf' : 'Attempt at route discovery has failed due to lack of table space',
    'd0' : 'Attempt at route discovery has failed due to any reason except lack of table space',
    'd1' : 'NLDE-DATA.request has failed due to routing failure on sending device',
    'd2' : 'Broadcast or broadcast-mode multicast has failed as there is no room in BTT',
    'd3' : 'Unicast mode multi-cast frame was discarded pending route discovery',
    'd4' : 'Unicast frame does not have a route available but it is buffered for automatic resend',
}

ZCL_APS_CODE = {
    'a0': 'A transmit request failed since the ASDU is too large and fragmentation is not supported',
    'a1': 'A received fragmented frame could not be defragmented at the current time',
    'a2': 'A received fragmented frame could not be defragmented since the device does not support fragmentation',
    'a3': 'A parameter value was out of range',
    'a4': 'An APSME-UNBIND.request failed due to the requested binding link not existing in the binding table',
    'a5': 'An APSME-REMOVE-GROUP.request has been issued with a group identified that does not appear in the group table',
    'a6': 'A parameter value was invaid or out of range',
    'a7': 'An APSDE-DATA.request requesting ack transmission failed due to no ack being received',
    'a8': 'An APSDE-DATA.request with a destination addressing mode set to 0x00 failed due to there being no devices bound to this device',
    'a9': 'An APSDE-DATA.request with a destination addressing mode set to 0x03 failed due to no corresponding short address found in the address map table',
    'aa': 'An APSDE-DATA.request with a destination addressing mode set to 0x00 failed due to a binding table not being supported on the device',
    'ab': 'An ASDU was received that was secured using a link key',
    'ac': 'An ASDU was received that was secured using a network key',
    'ad': 'An APSDE-DATA.request requesting security has resulted in an error during the corresponding security processing',
    'ae': 'An APSME-BIND.request or APSME.ADDGROUP.request issued when the binding or group tables, respectively, were full.',
    'af': 'An ASDU was received without any security.',
    'b0': 'An APSME-GET.request or APSMESET. request has been issued with an unknown attribute identifier.',
}

ZCL_ZDP_CODE = {
    '80': 'The supplied request type was invalid.',
    '81': 'The requested device did not exist on a device following a child descriptor request to a parent.',
    '82': 'The supplied endpoint was equal to 0x00 or between 0xF1 and 0xFF',
    '83': 'The requested endpoint is not described by a Simple descriptor.',
    '84': 'The requested optional feature is not supported on the target device.',
    '85': 'A timeout has occurred with the requested operation.',
    '86': 'The End Device bind request was unsuccessful due to a failure to match any suitable clusters.',
    '88': 'The unbind request was unsuccessful due to the Coordinator or source device not having an entry in its binding table to unbind.',
    '89': 'A child descriptor was not available following a discovery request to a parent.',
    '8a': 'The device does not have storage space to support the requested operation.',
    '8b': 'The device is not in the proper state to support the requested operation.',
    '8c': 'The device does not have table space to support the operation.',
    '8d': ' The permissions configuration table on the target indicates that the request is not authorised from this device.',
}

ZCL_MAC_CODES = {
    'e0': 'Beacon loss after synchronisation request.',
    'e1': 'CSMA/CA channel access failure.',
    'e2': 'GTS request denied',
    'e3': 'Could not disable transmit or receive',
    'e4': 'Incoming frame failed security check',
    'e5': 'Frame too long, after security processing, to be sent',
    'e6': 'GTS transmission failed',
    'e7': 'Purge request failed to find entry in queue ',
    'e8': 'Out-of-range parameter in function',
    'e9': 'No acknowledgement received when expected ',
    'ea': 'Scan failed to find any beacons',
    'eb': 'No response data after a data request',
    'ec': 'No allocated network (short) address for operation ',
    'ed': 'Receiver-enable request could not be executed, as CAP finished',
    'ee': 'PAN ID conflict has been detected',
    'ef': 'Co-ordinator realignment has been received ',
    'f0': 'Pending transaction has expired and data discarded ',
    'f1': 'No capacity to store transaction',
    'f2': 'Receiver-enable request could not be executed, as in transmit state',
    'f3': 'Appropriate key is not available in ACL',
    'f4': 'PIB Set/Get on unsupported attribute',
}

ZCL_EXTENDED_ERROR_CODES = {
    '01': 'Fatal error - retrying will cause the error again',
    '02': 'Endpoint is not valid for loopback (fatal error)',
    '03': 'No output cluster in the Simple descriptor for this endpoint/cluster (fatal error)',
    '04': 'Fragmented data requests must be sent with APS ack (fatal error)',
    '05': 'Bad parameter has been passed to the command manager (fatal error)',
    '06': 'Address parameter is out-of-range (fatal error), e.g. broadcast address when calling unicast function',
    '07': 'TX ACK bit has been set when attempting to post to a local endpoint (fatal error)',
    '08': 'Resource error/shortage - retrying may succeed',
    '80': "No free NPDUs (resource error) - the number of NPDUs is set in the 'Number of NPDUs' property of the 'PDU Manager' section of the ZPS Configuration Editor ",
    '81': "No free APDUs (resource error) - the number of APDUs is set in the 'Instances' property of the appropriate 'APDU' child of the 'PDU Manager' section of the ZPS Configuration Editor",
    '82': "No free simultaneous data request handles (resource error) - the number of handles is set in the 'Maximum Number of Simultaneous Data Requests' field of the 'APS layer configuration' section of the ZPS Configuration Editor",
    '83': "No free APS acknowledgement handles (resource error) - the number of handles is set in the 'Maximum Number of Simultaneous Data Requests with Acks' field of the 'APS layer configuration' section of the ZPS Configuration Editor",
    '84': "No free fragment record handles (resource error) - the number of handles is set in the 'Maximum Number of Transmitted Simultaneous Fragmented Messages' field of the 'APS layer configuration' section of the ZPS Configuration Editor",
    '85': 'No free MCPS request descriptors (resource error) - there are 8 MCPS request descriptors and these are only ever likely to be exhausted under a very heavy network load or when trying to transmit too many frames too close together',
    '86': 'Loopback send is currently busy (resource error) - there can be only one loopback request at a time',
    '87': 'No free entries in the extended address table (resource error) - this table is configured in the ZPS Configuration Editor',
    '88': 'Simple descriptor does not exist for this endpoint/cluster',
    '89': 'Bad parameter has been found while processing an APSDE request or response',
    '8a': 'No routing table entries free',
    '8b': 'No Broadcast transaction table entries free'
}


def DisplayStatusCode( StatusCode ) :


    if StatusCode in STATUS_CODE:
        return STATUS_CODE[ StatusCode ]

    if StatusCode in ZCL_NWK_CODE:
        return ZCL_NWK_CODE[ StatusCode ]

    if StatusCode in ZCL_APS_CODE:
        return ZCL_APS_CODE[ StatusCode ]

    if StatusCode in ZCL_ZDP_CODE:
        return ZCL_ZDP_CODE[ StatusCode ]

    if StatusCode in  ZCL_MAC_CODES:
        return ZCL_MAC_CODES[ StatusCode ]

    if StatusCode in  ZCL_EXTENDED_ERROR_CODES:
        return ZCL_EXTENDED_ERROR_CODES[ StatusCode ]

    return ''



