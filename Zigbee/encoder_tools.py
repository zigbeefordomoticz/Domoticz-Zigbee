



def encapsulate_plugin_frame( msgtype, payload, lqi ):
    newFrame = "01"  # 0:2
    newFrame += msgtype  # 2:6   MsgType
    newFrame += "%04x" % len(payload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += payload
    newFrame += lqi  # LQI
    newFrame += "03"
    
    return newFrame