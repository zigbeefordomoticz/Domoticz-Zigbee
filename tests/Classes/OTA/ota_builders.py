"""
Frame and firmware-file builders for the Classes.OTA unit tests.

    make_ota_image(...)    a Zigbee OTA file, laid out as the ZCL spec says
    block_request(...)     the 8501 pseudo-frame of an Image Block Request
    page_request(...)      the 8502 pseudo-frame of an Image Page Request
    upgrade_end(...)       the 8503 pseudo-frame of an Upgrade End Request
    query_next_image(...)  the ZCL payload of a Query Next Image Request
"""

import struct

DEVICE_NWKID = "1234"
DEVICE_EP = "01"
DEVICE_IEEE = "00158d0000000001"

OTA_MAGIC = 0x0BEEF11E

def make_ota_image(
    manuf_code=0x117C,
    image_type=0x2203,
    version=0x01020304,
    payload=b"\xAB" * 200,
    field_control=0,
    security_credential=None,
    destination=None,
    min_hw=None,
    max_hw=None,
    header_string=b"Z4D unit test image",
    stack_version=0x0002,
    prefix=b"",
    vendor_data=b"",
):
    """Build a Zigbee OTA upgrade file, field order as in ZCL 11.4.2.

    Optional fields follow the base header in this order: security credential
    version (bit 0, 1 byte), upgrade file destination (bit 1, 8 bytes), then
    minimum / maximum hardware version (bit 2, 2 + 2 bytes).
    """
    optional = b""
    if field_control & 0x01:
        optional += struct.pack("<B", security_credential)
    if field_control & 0x02:
        optional += struct.pack("<Q", destination)
    if field_control & 0x04:
        optional += struct.pack("<HH", min_hw, max_hw)
    optional += vendor_data

    header_length = 56 + len(optional)
    image_size = header_length + len(payload)
    header = struct.pack(
        "<LHHHHHLH32sL",
        OTA_MAGIC,
        0x0100,
        header_length,
        field_control,
        manuf_code,
        image_type,
        version,
        stack_version,
        header_string.ljust(32, b"\x00"),
        image_size,
    )
    return prefix + header + optional + payload


def block_request(nwkid=DEVICE_NWKID, ep=DEVICE_EP, offset=0, version=0x01020304, image_type=0x2203,
                  manuf_code=0x117C, delay=0, max_size=0x30, field_control=0, sqn=0x10):
    """8501 pseudo-frame, as Zigbee/zclDecoders.buildframe_for_cluster_8501 builds it."""
    return (
        f"{sqn:02x}{ep}0019" "02" f"{nwkid}" "0000000000000000"
        f"{offset:08x}{version:08x}{image_type:04x}{manuf_code:04x}{delay:04x}{max_size:02x}{field_control:02x}"
    )


def page_request(nwkid=DEVICE_NWKID, ep=DEVICE_EP, offset=0, version=0x01020304, image_type=0x2203,
                 manuf_code=0x117C, max_size=0x30, page_size=0x0100, spacing=0, field_control=0, sqn=0x10):
    """8502 pseudo-frame, as Zigbee/zclDecoders.buildframe_for_cluster_8502 builds it."""
    return (
        f"{sqn:02x}{ep}0019" "02" f"{nwkid}"
        f"{offset:08x}{version:08x}{image_type:04x}{manuf_code:04x}{max_size:02x}{page_size:04x}{spacing:04x}{field_control:02x}"
    )


def upgrade_end(nwkid=DEVICE_NWKID, ep=DEVICE_EP, version=0x01020304, image_type=0x2203, manuf_code=0x117C,
                status="00", sqn=0x20):
    """8503 pseudo-frame, as Zigbee/zclDecoders.buildframe_for_cluster_8503 builds it."""
    return f"{sqn:02x}{ep}0019" "02" f"{nwkid}" f"{version:08x}{image_type:04x}{manuf_code:04x}{status}"


def query_next_image(manuf_code=0x117C, image_type=0x2203, version=0x01000000, hw_version=None):
    """ZCL payload of Query Next Image Request (command 0x01): little-endian on the air."""
    field_control = 0x01 if hw_version is not None else 0x00
    data = struct.pack("<BHHL", field_control, manuf_code, image_type, version)
    if hw_version is not None:
        data += struct.pack("<H", hw_version)
    return data.hex()
