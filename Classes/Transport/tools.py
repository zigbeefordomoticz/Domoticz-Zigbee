# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz

from Modules.zigateConsts import ZIGATE_COMMANDS, ZIGATE_RESPONSES, MAX_SIMULTANEOUS_ZIGATE_COMMANDS

STANDALONE_MESSAGE = []
PDM_COMMANDS = ('8300', '8200', '8201', '8204', '8205', '8206', '8207', '8208')
CMD_PDM_ON_HOST = []
CMD_ONLY_STATUS = []
CMD_WITH_ACK = []
CMD_NWK_2NDBytes = {}
CMD_WITH_RESPONSE = {}
RESPONSE_SQN = []

def initialize_command_protocol_parameters():
    for x in ZIGATE_RESPONSES:
        STANDALONE_MESSAGE.append(x)

    for x in ZIGATE_COMMANDS:
        if ZIGATE_COMMANDS[x]['NwkId 2nd Bytes']:
            CMD_NWK_2NDBytes[x] = x

        if ZIGATE_COMMANDS[x]['Ack']:
            CMD_WITH_ACK.append(x)

        if ZIGATE_COMMANDS[x]['SQN']:
            RESPONSE_SQN.append(x)

        if len(ZIGATE_COMMANDS[x]['Sequence']) == 0:
            CMD_PDM_ON_HOST.append(x)

        elif len(ZIGATE_COMMANDS[x]['Sequence']) == 1:
            CMD_ONLY_STATUS.append(x)

        elif len(ZIGATE_COMMANDS[x]['Sequence']) == 2:
            CMD_WITH_RESPONSE[x] = ZIGATE_COMMANDS[x]['Sequence'][1]


def stop_waiting_on_queues( self ):
    if self.writer_queue:
        self.writer_queue.put( 'STOP' ) # Stop Writer

    if self.forwarder_queue:
        self.forwarder_queue.put( 'STOP' ) # Stop Forwarded


def waiting_for_end_thread( self ):

    # Release Semaphore
    self.semaphore_gate.release( )

    if self.pluginconf.pluginConf['byPassDzConnection'] and not self.force_dz_communication:
        self.reader_thread.join()
        self.logging_receive( 'Debug', "waiting_for_end_thread - readThread done")

    self.forwarder_thread.join()
    self.logging_receive( 'Debug', "waiting_for_end_thread - forwardedThread done")

    self.writer_thread.join()
    self.logging_receive( 'Debug', "waiting_for_end_thread - writerThread done")


def handle_thread_error( self, e, nb_in, nb_out, data):
    trace = []
    tb = e.__traceback__
    Domoticz.Error("'%s' failed '%s'" %(tb.tb_frame.f_code.co_name, str(e)))
    while tb is not None:
        trace.append(
            {
            "Module": tb.tb_frame.f_code.co_filename,
            "Function": tb.tb_frame.f_code.co_name,
            "Line": tb.tb_lineno
        })
        Domoticz.Error("----> Line %s in '%s', function %s" %( tb.tb_lineno, tb.tb_frame.f_code.co_filename,  tb.tb_frame.f_code.co_name,  ))
        tb = tb.tb_next

    context = {
        'Error Code': 'TRANS-THREADERROR-01',
        'Type:': type(e).__name__,
        'Message code:': str(e),
        'Stack Trace': trace,
        'nb_in': nb_in,
        'nb_out': nb_out,
        'Data': str(data),
    }
    self.logging_receive( 'Error', "handle_error_in_thread ", _context=context)

def update_xPDU( self, npdu, apdu):
    if npdu == '' or apdu == '':
        return
    self.npdu = int(npdu,16)
    self.apdu = int(apdu,16)
    self.statistics._MaxaPdu = max(self.statistics._MaxaPdu, int(apdu,16))
    self.statistics._MaxnPdu = max(self.statistics._MaxnPdu, int(npdu,16))


def release_command( self, isqn):
    # Remove the command from ListOfCommand
    # Release Semaphore
    if isqn is not None and isqn in self.ListOfCommands:
        self.logging_receive( 'Debug', "==== Removing isqn: %s from %s" %(isqn, self.ListOfCommands.keys()))
        del self.ListOfCommands[ isqn ]

    self.logging_receive( 'Debug', "============= - Release semaphore %s (%s)" %(self.semaphore_gate._value, len(self.ListOfCommands)))
    if self.semaphore_gate._value < MAX_SIMULTANEOUS_ZIGATE_COMMANDS:
        self.semaphore_gate.release()
    self.logging_receive( 'Debug', "============= - Semaphore released !! %s writerQueueSize: %s" %(self.semaphore_gate._value, self.writer_queue.qsize( )))

def get_isqn_from_ListOfCommands( self, PacketType):
    for x in  list(self.ListOfCommands):
        if self.ListOfCommands[ x ]['Status'] == 'SENT':
            self.logging_receive( 'Debug', "get_isqn_from_ListOfCommands - Found isqn: %s with Sem: %s" %(x, self.ListOfCommands[ x ]['Semaphore']))
            self.ListOfCommands[ x ]['Status'] = '8000'
            return x

    return None

def get_command_from_msgtype( command ):
    # Return the MsgType expected for a given command

    for x in CMD_WITH_RESPONSE:
        if CMD_WITH_RESPONSE[ x ] == int(command,16):
            return x
    return None

def get_response_from_command( command ):

    if int(command,16) in CMD_WITH_RESPONSE:
        return CMD_WITH_RESPONSE[ int(command,16) ]
    return None

def print_listofcommands( self, isqn ):

    self.logging_receive( 'Debug', 'ListOfCommands[%s]:' %isqn)
    for attribute in self.ListOfCommands[ isqn ]:
        self.logging_receive( 'Debug', '--> %s: %s' %(attribute, self.ListOfCommands[ isqn ][ attribute]))

def get_nwkid_from_datas_for_zcl_command( self, isqn):
    
    return self.ListOfCommands[isqn]['datas'][2:6]

def is_nwkid_available( self, cmd):

    return ZIGATE_COMMANDS[ cmd ]['NwkId 2nd Bytes']
