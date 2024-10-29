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

import traceback

def handle_thread_error(self, e, data=""):

    context = {
        "Message code:": str(e),
        "Stack Trace": str(traceback.format_exc()),
        "Data": str(data),
    }
    
    self.log.logging("TransportWrter", "Error", "Issue in request %s, dumping stack: %s" %( data, (traceback.format_exc() )), context=context)
