#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: badzz & pipiche38
#


"""
    Module: sqnMgmt

    Description: generate and handle the list of internal SQN
    
"""
import Domoticz
import time
import sys
from itertools import filterfalse

# list of [0:i_sqn, 1:e_sqn, 2:timestamp_query_in_seconds, 3:function_answer_status, 4:ack_status, 5:response_status]

I_SQN = 0
E_SQN = 1
TIMESTAMP = 2
TIMEOUT = 800 #seconds


def sqn_init_stack(self):
    self.sqn_stack = []
    self.current_sqn = 0


def sqn_generate_new_internal_sqn (self): # to be called in zigatecmd

    self.loggingSend(  'Debug',"sqnMgmt generate_new_internal_sqn")
   
    i_sqn = self.current_sqn
    self.current_sqn = i_sqn + 1

    if self.current_sqn == sys.maxsize:
        self.current_sqn = 0

    now = int(time.time())

    self.sqn_stack.append ([i_sqn, -1, now])
    self.loggingSend(  'Debug',"sqnMgmt generate_new_internal_sqn %s" %i_sqn)
    
    return i_sqn

def sqn_add_external_sqn (self, i_sqn, e_sqn, e_sqnZcl): # to be called in Transport when receiving 0x8000

  #  Domoticz.Error ("sqnMgmt add_external_sqn %s %s" %(e_sqn, self.sqn_stack))
    for sqn_tuple in self.sqn_stack:
        if sqn_tuple[E_SQN]  == -1 :
            ok = sqn_tuple[ I_SQN ] == i_sqn
            self.loggingSend(  'Log',"sqn_add_external_sqn Ok %s" %ok)
            sqn_tuple[E_SQN] = e_sqn
            return
    self.loggingSend(  'Error',"sqnMgmt add_external_sqn could not find i_sqn corresponding %s %s" %(e_sqn, self.sqn_stack))

def sqn_get_tuple (self, e_sqn):

    for sqn_tuple in self.sqn_stack:
        if sqn_tuple[E_SQN] == e_sqn:
            return sqn_tuple
    return None

def sqn_get_internal_sqn (self, e_sqn):

    sqn_tuple = sqn_get_tuple (self, e_sqn)
    if sqn_tuple is not None:
        self.loggingSend(  'Debug',"sqnMgmt sqn_get_internal found i_sqn %s" %(sqn_tuple[0]))
        return sqn_tuple[I_SQN]
    else:
        Domoticz.Error ("sqnMgmt sqn_get_internal not found e_sqn %s" %(e_sqn))
        return None

def sqn_cleanup (self):
    now = int(time.time())
    newstack  = filterfalse(lambda sqn_tuple: now > (sqn_tuple[TIMESTAMP] + TIMEOUT), self.sqn_stack )
    self.sqn_stack = list(newstack)

def sqn_delete (self, i_sqn):
    for sqn_tuple in self.sqn_stack:
        if sqn_tuple[I_SQN] == i_sqn:
            self.sqn_stack.remove(sqn_tuple)

def sqn_reset (self,i_sqn):
    now = int(time.time())

    for sqn_tuple in self.sqn_stack:
        if sqn_tuple[I_SQN] == i_sqn:
            sqn_tuple[E_SQN] = -1
            sqn_tuple[TIMESTAMP] = now

