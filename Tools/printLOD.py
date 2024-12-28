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

import os.path

def main():
    """
    Main function to prompt the user for a filename and process the DeviceList.txt file.
    """
    while True:
        print("Enter the DeviceList.txt filename: ")
        filename = input()
        if os.path.exists(filename):
            break

    process_file(filename)

def process_file(filename):
    """
    Process the given DeviceList.txt file and print its contents in a formatted manner.

    Args:
        filename (str): The name of the DeviceList.txt file to process.
    """
    with open(filename, 'r') as myfile2:
        for line in myfile2:
            if not line.strip():
                # Empty line
                continue
            key, val = line.split(":", 1)
            key = key.replace(" ", "").replace("'", "")

            dlVal = eval(val)
            print("%-10s %s" % ('NwkID', key))
            for i, j in dlVal.items():
                if i == 'Ep':
                    # Ep {'01': {'0000': {}, 'ClusterType': {'576': 'ColorControl'}, '0003': {}, '0004': {}, '0005': {}, '0006': '00', '0008': {}, '0300': {}, '0b05': {}, '1000': {}}}
                    print("Ep")
                    j = eval(str(j))
                    for k, l in j.items():
                        print("           %-10s %s" % (k, l))
                else:
                    print("%-10s %s" % (i, j))

            print("======")

if __name__ == "__main__":
    main()
