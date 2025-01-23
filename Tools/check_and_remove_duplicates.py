#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

import os
import sys
import subprocess
import argparse
import importlib.metadata

def find_duplicates(directory):
    """
    Find and list all duplicate versions of packages in the specified directory.

    Args:
        directory (str): The directory containing the Python modules.

    Returns:
        dict: A dictionary where the keys are package names and the values are lists of duplicate versions.
    """
    installed_packages = {}
    for dist in importlib.metadata.distributions(path=[directory]):
        package_name = dist.metadata['Name']
        package_version = dist.version
        if package_name in installed_packages:
            installed_packages[package_name].append(package_version)
        else:
            installed_packages[package_name] = [package_version]

    return {
        pkg: versions
        for pkg, versions in installed_packages.items()
        if len(versions) > 1
    }

def remove_duplicates(directory, duplicates, keep_version):
    """
    Remove duplicate versions of packages, keeping the specified version.

    Args:
        directory (str): The directory containing the Python modules.
        duplicates (dict): A dictionary where the keys are package names and the values are lists of duplicate versions.
        keep_version (str): The version to keep.
    """
    for pkg, versions in duplicates.items():
        for version in versions:
            if version != keep_version:
                print(f"Uninstalling {pkg}=={version}")
                subprocess.run([sys.executable, '-m', 'pip', 'uninstall', f'{pkg}=={version}', '-y'], check=True)

def main():
    """
    Main function to check for and remove duplicate versions of Python modules.

    The script accepts a directory path and an optional flag to remove duplicates.
    """
    parser = argparse.ArgumentParser(description="Check for and remove duplicate versions of Python modules.")
    parser.add_argument('directory', type=str, help="The directory containing the Python modules.")
    parser.add_argument('--remove-duplicates', action='store_true', help="Remove duplicate versions of modules.")
    args = parser.parse_args()

    directory = args.directory
    remove_duplicates_flag = args.remove_duplicates

    duplicates = find_duplicates(directory)

    if duplicates:
        print("Duplicate versions found:")
        for pkg, versions in duplicates.items():
            print(f"{pkg}: {versions}")

        if remove_duplicates_flag:
            for pkg, versions in duplicates.items():
                keep_version = versions[0]  # Keep the first version found
                remove_duplicates(directory, {pkg: versions}, keep_version)
    else:
        print("No duplicate versions found.")

if __name__ == "__main__":
    main()
