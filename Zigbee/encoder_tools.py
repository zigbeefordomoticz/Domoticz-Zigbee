import struct


def decode_endian_data(data, datatype):
    # Tested with Raw Configure reporting

    if datatype in ("10", "18", "20", "28", "30"):
        return data

    if datatype in ("09", "19", "21", "29", "31"):
        data = "%04x" % struct.unpack(">H", struct.pack("H", int(data, 16)))[0]
        return data[:4]

    if datatype in ("22", "2a"):
        data = "%06x" % struct.unpack(">I", struct.pack("I", int(data, 16)))[0]
        return data[:6]

    if datatype in ("23", "2b", "39"):
        data = "%08x" % struct.unpack(">i", struct.pack("I", int(data, 16)))[0]
        return data[:8]

    if datatype in ("25", "2d"):  # Tested Ok
        data = "%012x" % struct.unpack("Q", struct.pack(">Q", int(data, 16)))[0]
        return data[:12]

    if datatype in ("00", "41", "42", "4c", "48"):
        return data

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
