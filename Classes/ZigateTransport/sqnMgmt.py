#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: badzz & pipiche38
#


"""
    Module: sqnMgmt

    Description: generate and handle the list of internal SQN
    
"""
import sys

# from itertools import filterfalse

# list of [0:i_sqn, 1:e_sqn, 2:timestamp_query_in_seconds, 3:function_answer_status, 4:ack_status, 5:response_status]


TYPE_APP_ZIGATE = 0
TYPE_APP_ZCL = 2
TYPE_APP_ZDP = 3


def sqn_init_stack(self):
    self.sqn_zcl = {}
    self.sqn_zdp = {}
    self.sqn_aps = {}
    self.current_sqn = 0


def sqn_generate_new_internal_sqn(self):  # to be called in zigatecmd

    i_sqn = self.current_sqn
    self.current_sqn = i_sqn + 1

    if self.current_sqn == sys.maxsize:
        self.current_sqn = 0

    # self.logging_proto(  'Debug',"sqnMgmt generate_new_internal_sqn %s" %i_sqn)

    return i_sqn


def sqn_add_external_sqn(
    self, i_sqn, e_sqnAPP, sqnAPP_type, e_sqnAPS
):  # to be called in Transport when receiving 0x8000

    if sqnAPP_type == TYPE_APP_ZIGATE:
        return
    self.sqn_aps[e_sqnAPS] = i_sqn

    if sqnAPP_type == TYPE_APP_ZCL:
        self.sqn_zcl[e_sqnAPP] = i_sqn
    elif sqnAPP_type == TYPE_APP_ZDP:
        self.sqn_zdp[e_sqnAPP] = i_sqn

    # self.logging_proto(  'Debug',"sqnMgmt add_external_sqn i_sqn:%s e_sqnAPP:%s sqnAPP_type:%s e_sqnAPS:%s" %(i_sqn, e_sqnAPP,sqnAPP_type ,e_sqnAPS))


def sqn_get_internal_sqn_from_aps_sqn(self, e_sqn):
    if e_sqn in self.sqn_aps:
        return self.sqn_aps[e_sqn]
    return None


def sqn_get_internal_sqn_from_app_sqn(self, e_sqn, sqnAPP_type):
    
    if self.zigbee_communication != "native":
        return e_sqn
    
    if sqnAPP_type == TYPE_APP_ZIGATE:
        return None

    if sqnAPP_type == TYPE_APP_ZCL:
        if e_sqn in self.sqn_zcl:
            return self.sqn_zcl[e_sqn]
    elif sqnAPP_type == TYPE_APP_ZDP:
        if e_sqn in self.sqn_zdp:
            return self.sqn_zdp[e_sqn]
    return None
