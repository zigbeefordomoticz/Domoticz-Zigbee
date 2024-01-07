#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

from Modules.basicOutputs import raw_APS_request
from Modules.tools import get_and_inc_ZCL_SQN, get_device_config_param
from Modules.zigateConsts import ZIGATE_EP



def tuya_ts011F_threshold_overTemperatureBreaker( self, NwkId, enablement):
    threshold = get_device_config_param( self, NwkId, "TS011F_overTemperatureThreshold")
    self.log.logging("TuyaTS011F", "Debug", "tuya_ts011F_threshold_overTemperatureBreaker %s %s %s" %(NwkId, enablement, threshold), NwkId)
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "11" + sqn + "e6" + "05" + "%02x" %enablement + "00" + "%04x" %threshold
    raw_APS_request(self, NwkId, "01", "e001", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)


def tuya_ts011F_threshold_overPowerBreaker( self, NwkId, enablement):
    threshold = get_device_config_param( self, NwkId, "TS011F_overPowerThreshold")
    self.log.logging("TuyaTS011F", "Debug", "tuya_ts011F_threshold_overPowerBreaker %s %s %s" %(NwkId, enablement, threshold), NwkId)
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "11" + sqn + "e6" + "07" + "%02x" %enablement + "00" + "%04x" %threshold
    raw_APS_request(self, NwkId, "01", "e001", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)


def tuya_ts011F_threshold_overCurrentBreaker( self, NwkId, enablement):
    threshold = get_device_config_param( self, NwkId, "TS011F_overCurrentThreshold")
    self.log.logging("TuyaTS011F", "Debug", "tuya_ts011F_threshold_overCurrentBreaker %s %s %s" %(NwkId, enablement, threshold), NwkId)
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "11" + sqn + "e7" + "01" + "%02x" %enablement + "00" + "%04x" %threshold
    raw_APS_request(self, NwkId, "01", "e001", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)


def tuya_ts011F_threshold_overVoltageBreaker( self, NwkId, enablement):
    threshold = get_device_config_param( self, NwkId, "TS011F_overVoltageThreshold")
    self.log.logging("TuyaTS011F", "Debug", "tuya_ts011F_threshold_overVoltageBreaker %s %s %s" %(NwkId, enablement, threshold), NwkId)
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "11" + sqn + "e7" + "03" + "%02x" %enablement + "00" + "%04x" %threshold
    raw_APS_request(self, NwkId, "01", "e001", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)


def tuya_ts011F_threshold_underVoltageBreaker( self, NwkId, enablement):
    threshold = get_device_config_param( self, NwkId, "TS011F_underVoltageThreshold")
    self.log.logging("TuyaTS011F", "Debug", "tuya_ts011F_threshold_underVoltageBreaker %s %s %s" %(NwkId, enablement, threshold), NwkId)
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "11" + sqn + "e7" + "04" + "%02x" %enablement + "00" + "%04x" %threshold
    raw_APS_request(self, NwkId, "01", "e001", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)
