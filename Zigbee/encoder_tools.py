import struct

# IMPORTANT
# Zigate firmware is expecting the API to do stuffint, so everythink should be aligned with int
# So the all plugin makes this assumption, and if you look to the Configure Reporting change flag that is the case
# in the device conf file ...
#
# Here what we are going to do is, that in case the len(data) is different to the exepected len, then we will take
# remove the stuffing part.

def decode_endian_data(data, datatype, len_stream=None):
    # Tested with Raw Configure reporting
    # https://zigbeealliance.org/wp-content/uploads/2019/12/07-5123-06-zigbee-cluster-library-specification.pdf Table 2-10 (page 2-41)

    data_type_id = int(datatype, 16)
    if data_type_id == 0x00:
        return ""

    if data_type_id in {0x08, 0x10, 0x18, 0x20, 0x28, 0x30}:
        # 1 byte - 8b
        return data[:2] if len(data) == 2 else data

    if data_type_id in {0x09, 0x19, 0x21, 0x29, 0x31, 0x38}:
        # 2 bytes - 16b
        return "%04x" % struct.unpack(">H", struct.pack("H", int(data[:4], 16)))[0] if len(data) == 4 else data

    if data_type_id in {0x0A, 0x1A, 0x22, 0x2A}:
        # 3 bytes - 24b
        if len(data) == 8:
            # we expect a 3 bytes len
            data = data[2:8]
        return ("%08x" % struct.unpack(">I", struct.pack("I", int("00" + data[:6], 16)))[0])[:6]

    if data_type_id in {0x0B, 0x1B, 0x23, 0x2B, 0x39}:
        # 4 bytes - 32b
        return "%08x" % struct.unpack(">I", struct.pack("I", int(data[:8], 16)))[0]

    if data_type_id in {0x0C, 0x1C, 0x24, 0x2C}:
        # 5 bytes - 40b
        if len(data) == 16:
            # we expect 5 bytes lenght
            data = data[6:16]
        return ("%016x" % struct.unpack(">Q", struct.pack("Q", int("000000" + data[:10], 16)))[0])[:10]

    if data_type_id in {0x0D, 0x1D, 0x25, 0x2D}:
        # 6 bytes - 48b
        if len(data) == 16:
            # we expect 6 bytes lenght
            data = data[4:16]
        return ("%016x" % struct.unpack(">Q", struct.pack("Q", int("0000" + data[:12], 16)))[0])[:12]

    if data_type_id in {0x0E, 0x1E, 0x26, 0x2E}:
        if len(data) == 16:
            # we expect 7 bytes lenght
            data = data[2:16]
        # 7 bytes - 56b
        return "%016x" % ("%014x" % struct.unpack(">Q", struct.pack("Q", int("00" + data[:14], 16)))[0])[:14]

    if data_type_id in {0x0F, 0x1F, 0x27, 0x2F, 0x3A, 0xF0}:
        # 8 bytes - 64b
        return "%016x" % struct.unpack(">Q", struct.pack("Q", int(data[:16], 16)))[0]

    if data_type_id in {0x41, 0x42} and len_stream:
        return data[:len_stream]

    if data_type_id in {0xFE}:
        return "%016x" % struct.unpack(">Q", struct.pack("Q", int(data[:16], 16)))[0]

    return data


def encapsulate_plugin_frame(msgtype, payload, lqi):
    newFrame = "01"  # 0:2
    newFrame += msgtype  # 2:6   MsgType
    newFrame += "%04x" % len(payload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += payload
    newFrame += lqi  # LQI
    newFrame += "03"
    return newFrame
