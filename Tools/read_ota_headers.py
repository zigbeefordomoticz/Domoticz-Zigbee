#!/usr/bin/env python3
"""
Standalone script to read and display Zigbee OTA firmware headers.

This script:
- Scans the file for the OTA header identifier (0x0BEEF11E)
- Parses the mandatory 56-byte header
- Parses optional fields (if present)
- Extracts vendor-specific data (if any)
- Prints the *first 64 bytes of the actual firmware payload*
- Prints the header in a clean table format
"""

import struct
import argparse

FILE_IDENTIFIER = 0x0BEEF11E

# Zigbee OTA mandatory base header layout (56 bytes)
BASE_HEADER_FORMAT = "<L H H H H H L H 32s L"
BASE_HEADER_SIZE = struct.calcsize(BASE_HEADER_FORMAT)  # 56 bytes


# ------------------------------------------------------------------------------
# Find OTA Header Start
# ------------------------------------------------------------------------------
def find_header_offset(data):
    """Locate the OTA file identifier 0x0BEEF11E inside the firmware."""
    MAGIC = 0x0BEEF11E

    for i in range(len(data) - 4):
        if struct.unpack_from("<I", data, i)[0] == MAGIC:
            return i
    return None


# ------------------------------------------------------------------------------
# Parse OTA Header
# ------------------------------------------------------------------------------
def unpack_headers(data: bytes) -> dict:
    """
    Parse a Zigbee OTA image header according to the Zigbee Cluster Library.

    Works with Legrand, Tuya, IKEA, OSRAM, Sonoff, Schneider, etc.
    """

    # --- 1. Find OTA header ---
    offset = find_header_offset(data)
    if offset is None:
        raise ValueError("OTA header magic 0x0BEEF11E not found.")

    base = data[offset : offset + BASE_HEADER_SIZE]

    # --- 2. Unpack mandatory 56-byte header ---
    (
        file_id,
        header_version,
        header_length,
        field_ctrl,
        manufacturer_code,
        image_type,
        file_version,
        stack_version,
        header_str_raw,
        image_size,
    ) = struct.unpack(BASE_HEADER_FORMAT, base)

    header_string = header_str_raw.rstrip(b"\x00").decode("ascii", errors="ignore")

    # --- 3. Optional fields parsing ---
    extra_offset = offset + BASE_HEADER_SIZE

    # Optional: Hardware versions (Bit 0)
    min_hw_version = max_hw_version = None
    if field_ctrl & 0x01:
        min_hw_version, max_hw_version = struct.unpack_from("<HH", data, extra_offset)
        extra_offset += 4

    # Optional: Upgrade File Destination (Bit 1) → EUI64
    upgrade_file_destination = None
    if field_ctrl & 0x0002:
        upgrade_file_destination = data[extra_offset : extra_offset + 8].hex()
        extra_offset += 8

    # Optional: Security Credential Version (Bit 2)
    sec_cred_version = None
    if field_ctrl & 0x04:
        sec_cred_version = data[extra_offset]
        extra_offset += 1

    # --- 4. Vendor Data ---
    vendor_data_start = extra_offset
    vendor_data_end = offset + header_length
    vendor_data = data[vendor_data_start:vendor_data_end]

    # --- 5. Payload offset ---
    payload_offset = offset + header_length

    return {
        "file_id": file_id,
        "header_version": header_version,
        "header_length": header_length,
        "header_fctl": field_ctrl,
        "manufacturer_code": manufacturer_code,
        "image_type": image_type,
        "image_version": file_version,
        "stack_version": stack_version,
        "header_str": header_string,
        "image_size": image_size,
        "min_hw_version": min_hw_version,
        "max_hw_version": max_hw_version,
        "security_cred_version": sec_cred_version,
        "upgrade_file_destination": upgrade_file_destination,
        "vendor_data_length": len(vendor_data),
        "vendor_data": vendor_data,
        "payload_offset": payload_offset,
    }


# ------------------------------------------------------------------------------
# Read OTA File and Produce Final Data Structure
# ------------------------------------------------------------------------------
def read_ota_header(path):
    """Read and decode an OTA Zigbee header."""
    with open(path, "rb") as f:
        data = f.read()

    headers = unpack_headers(data)

    # Extract FIRST 64 BYTES OF THE ACTUAL PAYLOAD
    start = headers["payload_offset"]
    headers["first_64_bytes"] = data[start : start + 64]

    return headers


# ------------------------------------------------------------------------------
# Pretty Printing
# ------------------------------------------------------------------------------
def print_headers(h):
    print("\n==== Zigbee OTA Firmware Header ====\n")

    print(f"{'File ID':30} {h['file_id']:>10}   0x{h['file_id']:08X}")
    print(f"{'Header Version':30} {h['header_version']:>10}   0x{h['header_version']:04X}")
    print(f"{'Header Length':30} {h['header_length']:>10}   0x{h['header_length']:04X}")
    print(f"{'Field Control':30} {h['header_fctl']:>10}   0x{h['header_fctl']:04X}")
    print()

    print("-- Manufacturer & Image Info --")
    print(f"{'Manufacturer Code':30} {h['manufacturer_code']:>10}   0x{h['manufacturer_code']:04X}")
    print(f"{'Image Type':30} {h['image_type']:>10}   0x{h['image_type']:04X}")
    print(f"{'File Version':30} {h['image_version']:>10}   0x{h['image_version']:08X}")
    print(f"{'Zigbee Stack Version':30} {h['stack_version']:>10}   0x{h['stack_version']:04X}")
    print()

    print("-- Header String --")
    print(f"Header String            '{h['header_str']}'\n")

    print("-- Optional Fields --")
    print(f"{'Min HW Version':30} {h['min_hw_version']}")
    print(f"{'Max HW Version':30} {h['max_hw_version']}")
    print(f"{'Security Cred Version':30} {h['security_cred_version']}")
    print(f"{'Upgrade File Dest':30} {h['upgrade_file_destination']}")
    print()

    print("-- Vendor Data --")
    print(f"{'Vendor Data Length':30} {h['vendor_data_length']}")
    if h["vendor_data_length"] > 0:
        print("Vendor Data (hex):")
        print(h["vendor_data"].hex())
    else:
        print("(none)")
    print()

    print("-- Payload --")
    print(f"{'Payload Offset':30} {h['payload_offset']}   0x{h['payload_offset']:X}")
    print()

    print("-- First 64 bytes of Firmware Payload --")
    print(h["first_64_bytes"].hex(" "))
    print("\n====================================\n")


# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Read Zigbee OTA firmware header")
    parser.add_argument("file", help="Path to the OTA firmware file")
    args = parser.parse_args()

    headers = read_ota_header(args.file)
    print_headers(headers)


if __name__ == "__main__":
    main()
