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


def parse_device_id(self, device_id):
    """Parses a DeviceID string into its components.

    Args:
        device_id (str): The DeviceID string in the format '<IEEE>/<endpoint>/<cluster>'.

    Returns:
        dict: A dictionary containing 'IEEE', 'endpoint', and 'cluster' components.
    """
    parts = device_id.split('/')
    if len(parts) != 3:
        self.log.logging("Plugin", "Error", f"Invalid DeviceID format. Expected '<IEEE>/<endpoint>/<cluster>' {device_id}")
        return None

    ieee, endpoint, cluster = parts
    if len(ieee) != 16 or len(endpoint) != 2 or len(cluster) != 4:
        self.log.logging("Plugin", "Error", "Invalid component lengths: IEEE(16), endpoint(2), cluster(4)")
        return None

    return {'IEEE': ieee, 'endpoint': endpoint, 'cluster': cluster}


def create_device_id(self, ieee, endpoint, cluster):
    """Creates a DeviceID string from its components.

    Args:
        ieee (str): The 16-character IEEE address.
        endpoint (str): The 2-character endpoint.
        cluster (str): The 4-character cluster.

    Returns:
        str: The DeviceID string in the format '<IEEE>/<endpoint>/<cluster>'.
    """
    if len(ieee) != 16 or len(endpoint) != 2 or len(cluster) != 4:
        self.log.logging("Plugin", "Error", f"Invalid component lengths: IEEE(16), endpoint(2), cluster(4) {ieee}/{endpoint}/{cluster}")
        return None

    return f"{ieee}/{endpoint}/{cluster}"


def update_device_id(self, device_id, ieee=None, endpoint=None, cluster=None):
    """Updates components of a DeviceID string.

    Args:
        device_id (str): The original DeviceID string.
        ieee (str, optional): New IEEE address. Defaults to None.
        endpoint (str, optional): New endpoint. Defaults to None.
        cluster (str, optional): New cluster. Defaults to None.

    Returns:
        str: The updated DeviceID string.
    """
    components = parse_device_id(self, device_id)
    if components is None:
        return None

    ieee = ieee if ieee is not None else components['IEEE']
    endpoint = endpoint if endpoint is not None else components['endpoint']
    cluster = cluster if cluster is not None else components['cluster']

    return create_device_id(self, ieee, endpoint, cluster)


def validate_device_id(self, device_id):
    """Validates the format of a DeviceID string.

    Args:
        device_id (str): The DeviceID string.

    Returns:
        bool: True if valid, False otherwise.
    """
    if parse_device_id(self, device_id) is None:
        return False
    return True


NORMALIZED_CLUSTERS = {
    'rmt1': 'z001',
    'LumiLock': 'z002',
    'Strenght': 'z003',
    'Orientation': 'z004',
    'WaterCounter': 'z005',
    'Distance': 'z006',
    'TamperSwitch': 'z007',
    'Notification': 'z008',
    'PWFactor': 'z009',
    'phMeter': 'z010',
    'ec': 'z011',
    'orp': 'z012',
    'RainIntensity': 'z013',
    'freeChlorine': 'z014',
    'salinity': 'z015',
    'tds': 'z016'
    }


REVERSE_MAPPING = {v: k for k, v in NORMALIZED_CLUSTERS.items()}


def clustertype_old_to_new(cluster_name):
    """
    Convert an old-fashioned cluster name to its normalized form.
    """
    return NORMALIZED_CLUSTERS.get(cluster_name, f"Unknown cluster: {cluster_name}")


def clustertype_new_to_old(normalized_name):
    """
    Convert a normalized cluster name back to its old-fashioned form.
    """
    return REVERSE_MAPPING.get(normalized_name, f"Unknown normalized name: {normalized_name}")

# Example usage

if __name__ == "__main__":
    # Simple tests for the module

    class DummyLogger:
        @staticmethod
        def logging(module, level, message):
            print(f"[{module}][{level}] {message}")

    class DummySelf:
        log = DummyLogger()

    self = DummySelf()

    # Test data
    valid_device_id = "00124b0001abcdef/01/1234"
    invalid_device_id = "00124b0001abcdef/01"

    print("Testing parse_device_id...")
    print(parse_device_id(self, valid_device_id))  # Should return the components dictionary
    print(parse_device_id(self, invalid_device_id))  # Should log an error and return None

    print("\nTesting create_device_id...")
    print(create_device_id(self, "00124b0001abcdef", "01", "1234"))  # Should return the valid DeviceID
    print(create_device_id(self, "00124b0001abc", "01", "1234"))  # Should log an error and return None

    print("\nTesting update_device_id...")
    print(update_device_id(self, valid_device_id, cluster="5678"))  # Should update the cluster
    print(update_device_id(self, invalid_device_id, cluster="5678"))  # Should return None

    print("\nTesting validate_device_id...")
    print(validate_device_id(self, valid_device_id))  # Should return True
    print(validate_device_id(self, invalid_device_id))  # Should return False


    # Test conversion from old to new cluster
    print(clustertype_old_to_new("LumiLock"))  # Should output: z002

    # Test conversion from new to old
    print(clustertype_new_to_old("z002"))  # Should output: LumiLock
