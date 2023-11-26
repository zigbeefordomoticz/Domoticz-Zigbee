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