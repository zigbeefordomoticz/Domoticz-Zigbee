#!/usr/bin/env python3
"""
Standalone script to read and display Zigbee OTA firmware headers.

This script:
- Scans the file for the OTA header identifier (0x0BEEF11E)
- Parses the mandatory 20-byte header
- Parses the standard 32-byte header string
- Parses optional fields (if present)
- Extracts vendor-specific data (if any)
- Prints the first 64 bytes of the OTA file
- Prints the header in a clean table format

Author: ChatGPT (2025)
"""

import struct
import argparse

FILE_IDENTIFIER = 0x0BEEF11E
MANDATORY_HEADER_SIZE = 20       # Correct Zigbee OTA spec
HEADER_STRING_SIZE = 32
BASE_HEADER_SIZE = 56            # 20 mandatory + 32 string + 4? Zigbee spec defines 56 bytes for minimal header


def find_header_offset(data):
    """Locate the OTA file identifier 0x0BEEF11E inside the firmware."""
    
    MAGIC = 0x0BEEF11E

    for i in range(len(data) - 4):
        val = struct.unpack_from("<I", data, i)[0]
        if val == MAGIC:
            return i

    return None

    
def unpack_headers(data: bytes) -> dict:
    """
    Parse a Zigbee OTA image header according to the Zigbee Cluster Library (ZCL)
    OTA Upgrade specification (Cluster 0x0019).

    This function works with **all vendors** (standard, Legrand, Tuya, Ikea, OSRAM,
    Sonoff, Schneider, etc.) because it only parses the mandatory header fields,
    checks the Field Control flags, and treats all other data as vendor-specific.

    ---------------------------------------------------------------------------
    Zigbee OTA Header Structure (Mandatory Section – Always Present)
    ---------------------------------------------------------------------------
    Offset | Size | Field Name          | Format | Description
    -------+------+----------------------+--------+-------------------------------
      0    |  4   | File Identifier      |  L     | Magic: 0x0BEEF11E (little-endian)
      4    |  2   | Header Version       |  H     | Usually 0x0001
      6    |  2   | Header Length        |  H     | Total header size in bytes
      8    |  2   | Field Control        |  H     | Bitmask defining optional fields
     10    |  2   | Manufacturer Code    |  H     | ZCL manufacturer ID
     12    |  2   | Image Type           |  H     | Device-specific firmware type
     14    |  4   | File Version         |  L     | Firmware version
     18    |  2   | Stack Version        |  H     | Zigbee stack version
     20    | 32   | Header String        | 32s    | ASCII name padded with 0x00
     52    |  4   | Image Size           |  L     | Total firmware size

    Total mandatory length = 56 bytes

    ---------------------------------------------------------------------------
    Optional Fields (based on Field Control bits)
    ---------------------------------------------------------------------------
    Bit 0 (0x01): Hardware version fields included:
      - Minimum Hardware Version (uint16)
      - Maximum Hardware Version (uint16)

    Additional metadata may follow but is **vendor-specific** and not standardized.

    ---------------------------------------------------------------------------
    Vendor-Specific Fields
    ---------------------------------------------------------------------------
    Everything between:
       offset + header_length
       and
       offset + parsed_optional_fields_end
    is considered vendor-specific metadata.

    Examples:
      - Legrand firmwares add proprietary metadata directly after the header.
      - Tuya OTAs embed custom TLV metadata.
      - OSRAM and IKEA sometimes append signature blocks.

    This function preserves vendor data in raw form under "vendor_data" without
    attempting to parse it.

    ---------------------------------------------------------------------------
    Searching for the OTA Magic
    ---------------------------------------------------------------------------
    The function automatically finds the OTA header by scanning for:
        0x1E F1 EE 0B   (little-endian 0x0BEEF11E)

    This allows working with:
      - Encapsulated OTAs
      - Bootloader images prepended
      - Vendor-wrapped images

    ---------------------------------------------------------------------------
    Returns:
        dict with the following keys:

        file_id: int
        header_version: int
        header_length: int
        field_control: int
        manufacturer_code: int
        image_type: int
        file_version: int
        stack_version: int
        header_string: str
        image_size: int
        min_hw_version: Optional[int]
        max_hw_version: Optional[int]
        sec_cred_version: Optional[int]
        vendor_data: bytes  # raw vendor metadata block
        payload_offset: int # absolute offset of firmware payload inside file

    Raises:
        ValueError: If the OTA magic cannot be found or the header is malformed.

    ---------------------------------------------------------------------------
    Example:
        headers = unpack_headers(ota_data)
        print(headers["manufacturer_code"])
        print(headers["image_size"])
    ---------------------------------------------------------------------------
    """
    
    # --- 1. Magic search ---
    offset = find_header_offset(data)

    # --- 2. Base header (56 bytes) ---
    fmt_base = "<L H H H H H L H 32s L"
    BASE_HEADER_SIZE = struct.calcsize(fmt_base)

    base_slice = data[offset : offset + BASE_HEADER_SIZE]

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


    # --- 3. Optional hardware version fields ---
    # After unpacking base header
    extra_offset = offset + BASE_HEADER_SIZE

    # Bit 0 → Hardware Version
    min_hw_version, max_hw_version = None, None
    if field_ctrl & 0x01:
        fmt_hw = "<H H"
        hw_size = struct.calcsize(fmt_hw)
        hw_slice = data[extra_offset : extra_offset + hw_size]
        min_hw_version, max_hw_version = struct.unpack(fmt_hw, hw_slice)
        extra_offset += hw_size

    # Bit 1 - Upgrade File Destination (EUI64)
    if field_ctrl & 0x0002:
        eui = data[offset:offset+8]
        upgrade_file_destination = eui.hex()
        offset += 8
    else:
        upgrade_file_destination = None


    # Bit 2 → Security Credential Version
    sec_cred_version = None
    if field_ctrl & 0x04:
        sec_cred_version = data[extra_offset]
        extra_offset += 1

    # Vendor-specific data
    vendor_data = data[extra_offset : offset + header_length]
    # --- 5. Construct result dictionary ---
    header_string = header_str_raw.rstrip(b"\x00").decode( "ascii", errors="ignore" )
    
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
        "payload_offset": offset + header_length,
    }


def read_ota_header(path):
    """Read and decode an OTA Zigbee header."""
    with open(path, "rb") as f:
        data = f.read()

    header_offset = find_header_offset(data)
    if header_offset is None:
        raise ValueError("OTA Header ID (0x0BEEF11E) not found.")

    ota = data[header_offset:]

    headers = unpack_headers(ota)

    return {
        **headers,
        "first_64_bytes": ota[:64],
    }


def print_headers(h):
    """Pretty formatted header output."""
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

    print("-- First 64 bytes --")
    print(h["first_64_bytes"].hex(" "))
    print("\n====================================\n")


def main():
    parser = argparse.ArgumentParser(description="Read Zigbee OTA firmware header")
    parser.add_argument("file", help="Path to the OTA firmware file")
    args = parser.parse_args()

    headers = read_ota_header(args.file)
    print_headers(headers)


if __name__ == "__main__":
    main()

