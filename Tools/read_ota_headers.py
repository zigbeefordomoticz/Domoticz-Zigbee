#!/usr/bin/env python3
"""
Standalone script to read and display Zigbee OTA firmware headers.

This script:
- Scans the file for the OTA header identifier (0x0BEEF11E)
- Parses the mandatory header (56 bytes)
- Parses optional fields (hardware version, security credential, upgrade destination)
- Extracts vendor-specific data and attempts TLV parsing
- Detects vendor by manufacturer code and image type
- Displays first 64 bytes of the firmware payload
- Provides formatted output and hexdump

"""

import struct
import argparse
import textwrap

FILE_IDENTIFIER = 0x0BEEF11E
MANDATORY_HEADER_SIZE = 20       # Zigbee OTA mandatory header
HEADER_STRING_SIZE = 32

# Known vendors mapping
VENDOR_MAP = {
    0x1021: "Legrand",
    0x1037: "Tuya",
    0x1185: "IKEA",
    0x100B: "OSRAM",
    0x1234: "Sonoff",
    # Add more known manufacturer codes as needed
}


def find_header_offset(data):
    """Locate the OTA file identifier 0x0BEEF11E inside the firmware."""
    MAGIC = FILE_IDENTIFIER
    for i in range(len(data) - 4):
        val = struct.unpack_from("<I", data, i)[0]
        if val == MAGIC:
            return i
    return None


def parse_vendor_tlv(vendor_data: bytes):
    """
    Attempt to parse vendor_data as TLV (Tag-Length-Value).
    Returns a list of (tag, length, value) tuples.
    """
    tlv_list = []
    offset = 0
    while offset + 2 <= len(vendor_data):
        tag = vendor_data[offset]
        length = vendor_data[offset + 1]
        if offset + 2 + length > len(vendor_data):
            # Malformed TLV, exit
            break
        value = vendor_data[offset + 2 : offset + 2 + length]
        tlv_list.append((tag, length, value))
        offset += 2 + length
    return tlv_list


def unpack_headers(data: bytes) -> dict:
    """Parse OTA header and optional fields including vendor-specific data."""
    offset = find_header_offset(data)
    if offset is None:
        raise ValueError("OTA header ID (0x0BEEF11E) not found.")

    fmt_base = "<L H H H H H L H 32s L"  # mandatory 56 bytes
    base_size = struct.calcsize(fmt_base)
    base_slice = data[offset : offset + base_size]

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
    ) = struct.unpack(fmt_base, base_slice)

    header_string = header_str_raw.rstrip(b"\x00").decode("ascii", errors="ignore")

    # Optional fields
    extra_offset = offset + base_size
    min_hw_version = max_hw_version = sec_cred_version = upgrade_file_destination = None

    if field_ctrl & 0x01:  # Hardware version
        min_hw_version, max_hw_version = struct.unpack_from("<H H", data, extra_offset)
        extra_offset += 4

    if field_ctrl & 0x02:  # Upgrade file destination
        upgrade_file_destination = data[extra_offset : extra_offset + 8].hex()
        extra_offset += 8

    if field_ctrl & 0x04:  # Security credential version
        sec_cred_version = data[extra_offset]
        extra_offset += 1

    # Vendor-specific data (everything between optional fields and header_length)
    vendor_data_end = offset + header_length
    vendor_data = data[extra_offset : vendor_data_end]
    vendor_tlv = parse_vendor_tlv(vendor_data)

    # Payload starts after the full header (mandatory + optional + vendor)
    payload_offset = vendor_data_end
    payload_bytes = data[payload_offset : payload_offset + 64]  # first 64 bytes of firmware

    # Vendor name detection
    vendor_name = VENDOR_MAP.get(manufacturer_code, "Unknown")

    return {
        "file_id": file_id,
        "header_version": header_version,
        "header_length": header_length,
        "field_control": field_ctrl,
        "manufacturer_code": manufacturer_code,
        "vendor_name": vendor_name,
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
        "vendor_tlv": vendor_tlv,
        "payload_offset": payload_offset,
        "payload_first_64_bytes": payload_bytes,
    }


def read_ota_header(path):
    """Read OTA file and parse header + payload."""
    with open(path, "rb") as f:
        data = f.read()

    headers = unpack_headers(data)
    return headers


def hexdump(data: bytes, width=16):
    """Simple hexdump formatter."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i : i + width]
        hex_bytes = " ".join(f"{b:02X}" for b in chunk)
        lines.append(f"{i:04X}: {hex_bytes}")
    return "\n".join(lines)


def print_headers(h):
    """Pretty formatted OTA header output."""
    print("\n==== Zigbee OTA Firmware Header ====\n")
    print(f"{'File ID':30} {h['file_id']:>10}   0x{h['file_id']:08X}")
    print(f"{'Header Version':30} {h['header_version']:>10}   0x{h['header_version']:04X}")
    print(f"{'Header Length':30} {h['header_length']:>10}   0x{h['header_length']:04X}")
    print(f"{'Field Control':30} {h['field_control']:>10}   0x{h['field_control']:04X}")
    print(f"{'Manufacturer Code':30} {h['manufacturer_code']:>10}   0x{h['manufacturer_code']:04X}")
    print(f"{'Vendor Name':30} {h['vendor_name']}")
    print(f"{'Image Type':30} {h['image_type']:>10}   0x{h['image_type']:04X}")
    print(f"{'File Version':30} {h['image_version']:>10}   0x{h['image_version']:08X}")
    print(f"{'Stack Version':30} {h['stack_version']:>10}   0x{h['stack_version']:04X}")
    print(f"{'Header String':30} '{h['header_str']}'\n")

    print("-- Optional Fields --")
    print(f"{'Min HW Version':30} {h['min_hw_version']}")
    print(f"{'Max HW Version':30} {h['max_hw_version']}")
    print(f"{'Security Cred Version':30} {h['security_cred_version']}")
    print(f"{'Upgrade File Dest':30} {h['upgrade_file_destination']}\n")

    print("-- Vendor Data --")
    print(f"{'Vendor Data Length':30} {h['vendor_data_length']}")
    if h['vendor_data_length'] > 0:
        print("Vendor Data Hex Dump:")
        print(hexdump(h['vendor_data']))
        if h['vendor_tlv']:
            print("\nParsed TLV Entries:")
            for tag, length, value in h['vendor_tlv']:
                print(f"Tag {tag:02X}, Length {length}, Value: {value.hex()}")
    else:
        print("(none)")
    print()

    print("-- Payload (first 64 bytes) --")
    print(hexdump(h['payload_first_64_bytes']))
    print(f"\nPayload Offset: {h['payload_offset']}   0x{h['payload_offset']:X}")
    print("\n====================================\n")


def main():
    parser = argparse.ArgumentParser(description="Read Zigbee OTA firmware header")
    parser.add_argument("file", help="Path to the OTA firmware file")
    args = parser.parse_args()

    headers = read_ota_header(args.file)
    print_headers(headers)


if __name__ == "__main__":
    main()
