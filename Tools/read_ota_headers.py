#!/usr/bin/env python3
"""
Standalone script to read and display Zigbee OTA firmware headers.

This script reads a Zigbee OTA firmware image, finds the OTA header start
(marker 0x0BEEF11E), unpacks the fixed and optional header fields according
to the Zigbee OTA specification, and prints them in a readable table format.

Fields are displayed with both decimal and hexadecimal values where applicable.
"""

import struct
import argparse

def offset_start_firmware(ota_image):
    """
    Find the start offset of the OTA header within a firmware image.

    The OTA header is identified by the 4-byte file identifier 0x0BEEF11E.

    Args:
        ota_image (bytes): The full OTA firmware image.

    Returns:
        int or None: The index where the OTA header starts, or None if not found.
    """
    return next(
        (
            i
            for i in range(len(ota_image) - 4)
            if struct.unpack("<I", ota_image[i:i+4])[0] == 0x0BEEF11E
        ),
        None,
    )

def unpack_headers(ota_image):
    """
    Unpack the 69-byte Zigbee OTA header into a dictionary.

    This follows the Zigbee OTA specification and includes optional fields
    indicated by the field_control bitmask.

    Args:
        ota_image (bytes): The OTA image starting at the header offset.

    Returns:
        dict: Dictionary of OTA header fields with standard Zigbee OTA names,
              or None if unpacking fails.
    """
    if len(ota_image) < 69:
        print("OTA image too short to unpack header")
        return None

    try:
        header_data = list(struct.unpack("<LHHHHHLH32BLBQHH", ota_image[:69]))
    except struct.error:
        print(f"Error unpacking OTA header: {ota_image[:69]}")
        return None

    # Replace null bytes in header string with spaces
    for i in range(8, 40):
        if header_data[i] == 0x00:
            header_data[i] = 0x20

    header_data_compact = header_data[:8] + [header_data[8:40]] + header_data[40:]

    header_fields = [
        "file_identifier",
        "header_version",
        "header_length",
        "field_control",
        "manufacturer_code",
        "image_type",
        "file_version",
        "zigbee_stack_version",
        "header_string",
        "total_image_size",
        "security_cred_version",
        "upgrade_file_destination",
        "minimum_hardware_version",
        "maximum_hardware_version",
    ]

    return dict(zip(header_fields, header_data_compact))

def read_ota_header(file_path):
    """
    Read an OTA firmware file, locate the OTA header, and unpack it.

    Args:
        file_path (str or Path): Path to the OTA firmware file.

    Returns:
        dict: Dictionary of unpacked OTA header fields.

    Raises:
        ValueError: If the OTA header cannot be found or unpacked.
    """
    with open(file_path, "rb") as f:
        ota_image = f.read()

    start_offset = offset_start_firmware(ota_image)
    if start_offset is None:
        raise ValueError("OTA header start (0x0BEEF11E) not found in file")

    ota_image = ota_image[start_offset:]
    headers = unpack_headers(ota_image)
    if headers is None:
        raise ValueError("Failed to unpack OTA headers")

    return headers

def print_headers(headers):
    """
    Print OTA header fields in a readable table format.

    Numeric fields are shown in both decimal and hexadecimal. The header string
    is printed as ASCII. Optional fields like security credentials and hardware
    versions are included if present.

    Args:
        headers (dict): Dictionary of OTA header fields.
    """
    print("\nZigbee OTA Firmware Header:\n")
    print(f"{'Field':30} {'Value':30} {'Hex':10}")
    print("-" * 80)

    for k, v in headers.items():
        if isinstance(v, int):
            print(f"{k:30} {v:<30} 0x{v:X}")
        elif isinstance(v, list):
            header_str = ''.join(chr(c) for c in v)
            print(f"{k:30} {header_str:<30} {'':10}")
        else:
            print(f"{k:30} {v:<30} {'':10}")

    print("-" * 80 + "\n")

def main():
    """
    Command-line interface to read a Zigbee OTA firmware file and print its header.

    Usage:
        python read_ota_header.py <path_to_ota_file>
    """
    parser = argparse.ArgumentParser(description="Read Zigbee OTA firmware header")
    parser.add_argument("file", help="Path to the OTA firmware file")
    args = parser.parse_args()

    try:
        headers = read_ota_header(args.file)
        print_headers(headers)
    except Exception as e:
        print(f"Error reading OTA header: {e}")

if __name__ == "__main__":
    main()

