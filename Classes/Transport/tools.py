# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz

from Modules.zigateConsts import ZIGATE_COMMANDS, ZIGATE_RESPONSES

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

    self.reader_thread.join()
    self.logging_receive( 'Log', "waiting_for_end_thread - readThread done")
    self.forwarder_thread.join()
    self.logging_receive( 'Log', "waiting_for_end_thread - forwardedThread done")
    self.writer_thread.join()
    self.logging_receive( 'Log', "waiting_for_end_thread - writerThread done")


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

def is_final_step( self, isqn, step):
    # Step is 0x8000
    if step == 0x8000 and self.ListOfCommands[ isqn ]['cmd'] in CMD_ONLY_STATUS:
        return True

    expAck = exp8012 = False
    cmd = int(self.ListOfCommands[ isqn ]['cmd'], 16)
    if cmd in ZIGATE_COMMANDS:
        expAck = ZIGATE_COMMANDS[ cmd ]['Ack']
        exp8012 = ZIGATE_COMMANDS[ cmd ]['8012']

    if not expAck and not exp8012: 
        return True
    if step == 0x8012:
        return is_final_step_8012( self, isqn)
    return False

def is_final_step_8012(self, isqn):
    cmd = int(self.ListOfCommands[ isqn ]['cmd'], 16)
    expAck = ZIGATE_COMMANDS[ cmd ]['Ack']
    ackIsDisabled =  self.ListOfCommands[ isqn ]['ackIsDisabled']
    return bool(ackIsDisabled or not expAck)



def release_command( self, isqn):
    # Remove the command from ListOfCommand
    # Release Semaphore
    if isqn and isqn in self.ListOfCommands:
        del self.ListOfCommands[ isqn ]
    self.logging_receive( 'Log', "self.release_command - Release semaphore %s" %self.semaphore_gate)
    self.semaphore_gate.release()

def get_isqn_from_ListOfCommands( self, PacketType):
    for x in  list(self.ListOfCommands):
        if self.ListOfCommands[ x ]['Status'] == 'SENT':
            self.logging_receive( 'Log', "decode8000 - Found isqn: %s with Sem: %s" %(x, self.ListOfCommands[ x ]['Semaphore']))
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