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


import functools
import tracemalloc

FILTER_PATH = "Domoticz-Zigbee"


def memory_leak_detector(func):
    """Decorator to trace memory usage before and after function execution."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # We assumed that tracemalloc is already started
        #tracemalloc.start()

        # Snapshot before execution
        snapshot_before = tracemalloc.take_snapshot()

        # Execute the function
        result = func(self, *args, **kwargs)

        # Snapshot after execution
        snapshot_after = tracemalloc.take_snapshot()

        # Compare memory usage
        top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')

        # Filter for relevant lines (optional)
        filtered_stats = [
            stat for stat in top_stats
            if stat.count > 1 and stat.size > (5 * 1024)
            and FILTER_PATH in stat.traceback[0].filename
        ]

        # Log memory usage
        if filtered_stats:
            self.log.logging("MemoryLeak", "Debug", f"[ Memory Leak Detected in '{func.__name__}' ]")
            for stat in filtered_stats[:10]:  # Limit to top 10 results
                self.log.logging("MemoryLeak", "Debug", stat)

        return result
    return wrapper