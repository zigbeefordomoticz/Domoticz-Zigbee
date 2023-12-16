import binascii
from datetime import datetime

from Modules.legrand_netatmo import rejoin_legrand_reset


def Decode0302(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode0302 - PDM Load')
    rejoin_legrand_reset(self)
    
def Decode8001(self, Decode, MsgData, MsgLQI):
    LOG_FILE = 'ZiGate'
    MsgLogLvl = MsgData[:2]
    log_message = binascii.unhexlify(MsgData[2:]).decode('utf-8')
    logfilename = self.pluginconf.pluginConf['pluginLogs'] + '/' + LOG_FILE + '_' + '%02d' % self.HardwareID + '_' + '.log'
    try:
        with open(logfilename, 'at', encoding='utf-8') as file:
            try:
                file.write('%s %s %s' % (str(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]), MsgLogLvl, log_message) + '\n')
            except IOError:
                self.log.logging('Input', 'Error', 'Error while writing to ZiGate log file %s' % logfilename)
    except IOError:
        self.log.logging('Input', 'Error', 'Error while Opening ZiGate log file %s' % logfilename)
        
def Decode8006(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode8006 - MsgData: %s' % MsgData)
    Status = MsgData[:2]
    if Status == '00':
        Status = 'STARTUP'
    elif Status == '01' or (Status != '02' and Status == '06'):
        Status = 'RUNNING'
    elif Status == '02':
        Status = 'NFN_START'
    self.log.logging('Input', 'Status', "Non 'Factory new' Restart status: %s" % Status)
    
def Decode8007(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode8007 - MsgData: %s' % MsgData)
    Status = MsgData[:2]
    if Status == '00':
        Status = 'STARTUP'
    elif Status == '01' or (Status != '02' and Status == '06'):
        Status = 'RUNNING'
    elif Status == '02':
        Status = 'NFN_START'
    self.ErasePDMDone = True
    self.log.logging('Input', 'Status', "'Factory new' Restart status: %s" % Status)