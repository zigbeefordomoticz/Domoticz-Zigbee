# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#


def stop_waiting_on_queues( self ):
    self.writer_prio_queue(1, 'STOP') # Stop Writer
    self.forwarder_prio_queue( 1, 'STOP') # Stop Forwarded

def waiting_for_end_thread( self ):
    self.reader_thread.join()
    self.forwarder_thread.join()
    self.writer_thread.join()