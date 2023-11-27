
import struct
from datetime import datetime

from Modules.basicOutputs import setTimeServer


def Decode8017(self, Devices, MsgData, MsgLQI):
    ZigateTime = MsgData[:8]
    EPOCTime = datetime(2000, 1, 1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())
    ZigateTime = struct.unpack('I', struct.pack('I', int(ZigateTime, 16)))[0]
    self.log.logging('Input', 'Debug', 'UTC time is: %s, Zigate Time is: %s with deviation of: %s ' % (UTCTime, ZigateTime, UTCTime - ZigateTime))
    if abs(UTCTime - ZigateTime) > 5:
        setTimeServer(self)