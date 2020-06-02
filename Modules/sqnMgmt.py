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
from itertools import filterfalse


def init_sqn_stack(self):
    self.sqn_stack = []
    self.current_sqn = 0


def generate_new_internal_sqn (self): # to be called in zigatecmd

    Domoticz.Error ("sqnMgmt generate_new_internal_sqn")
   
    i_sqn = self.current_sqn
    self.current_sqn = i_sqn + 1
    now = int(time.time())

    self.sqn_stack.append ([i_sqn, -1, now])
    Domoticz.Error ("sqnMgmt generate_new_internal_sqn %s" %i_sqn)
    
    return i_sqn

def add_external_sqn(self, e_sqn): # to be called in decode8000

    Domoticz.Error ("sqnMgmt add_external_sqn %s %s" %(e_sqn, self.sqn_stack))

    for sqn_tuple in self.sqn_stack:
        if sqn_tuple[1]  == -1 :
            sqn_tuple[1] = e_sqn
            return
    Domoticz.Error ("sqnMgmt add_external_sqn could not find i_sqn corresponding %s %s" %(e_sqn, self.sqn_stack))


def get_internal_sqn (self, e_sqn):

    for sqn_tuple in self.sqn_stack:
        if sqn_tuple[1]  == e_sqn:
            Domoticz.Error ("sqnMgmt get_internal_sqn found i_sqn %s" %(sqn_tuple[0]))

            return sqn_tuple[0]
    Domoticz.Error ("sqnMgmt get_internal_sqn not found e_sqn %s" %(e_sqn))
    return None

def sqn_cleanup (self):
    now = int(time.time())
    newstack  = filterfalse(lambda sqn_tuple: now > (sqn_tuple[2] + 900), self.sqn_stack )
    self.sqn_stack = list(newstack)




