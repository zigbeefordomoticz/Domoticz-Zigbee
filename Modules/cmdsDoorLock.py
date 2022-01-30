#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: cmdsDoorLock.py

    Description: Implement Door Lock cluster command

"""

from Modules.zigateConsts import ZIGATE_EP
from Modules.basicOutputs import raw_APS_request
from Modules.tools import get_and_inc_ZCL_SQN


def cluster0101_lock_door(self, NwkId):

    cmd = "00"
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x01)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #  ClusterFrame: 0b0001 0001
    cluster_frame = "11"

    payload = cluster_frame + sqn + cmd
    raw_APS_request(self, NwkId, "01", "0101", "0104", payload, zigate_ep=ZIGATE_EP)


def cluster0101_unlock_door(self, NwkId):

    cmd = "01"
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x01)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #  ClusterFrame: 0b0001 0001
    cluster_frame = "11"

    payload = cluster_frame + sqn + cmd
    raw_APS_request(self, NwkId, "01", "0101", "0104", payload, zigate_ep=ZIGATE_EP)


def cluster0101_toggle_door(self, NwkId):

    cmd = "02"
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x01)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #  ClusterFrame: 0b0001 0001
    cluster_frame = "11"

    payload = cluster_frame + sqn + cmd
    raw_APS_request(self, NwkId, "01", "0101", "0104", payload, zigate_ep=ZIGATE_EP)
