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
    self.forwarder_thread.join()
    self.writer_thread.join()


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