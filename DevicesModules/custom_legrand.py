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


def legrand_operating_time(self, nwkid, ep, cluster, attribut, value):
    """
    Convert a device operating time value (seconds) into a human-readable format.
    
    Expands to years, months, days, hours, minutes, seconds as needed.
    """
    try:
        total_seconds = int(value)

        seconds_in_minute = 60
        seconds_in_hour = 3600
        seconds_in_day = 86400
        seconds_in_month = 30 * seconds_in_day
        seconds_in_year = 365 * seconds_in_day

        years, total_seconds = divmod(total_seconds, seconds_in_year)
        months, total_seconds = divmod(total_seconds, seconds_in_month)
        days, total_seconds = divmod(total_seconds, seconds_in_day)
        hours, total_seconds = divmod(total_seconds, seconds_in_hour)
        minutes, seconds = divmod(total_seconds, seconds_in_minute)

        parts = []
        if years:
            parts.append(f"{years}y")
        if months:
            parts.append(f"{months}m")
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")  # always show seconds

        operating_time = " ".join(parts)
    except (ValueError, TypeError, OverflowError):
        operating_time = "99y 99m 99d 99h 99m 99s"

    return operating_time
