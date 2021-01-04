
import threading

# Login mecanism
def Transport_logging(self, logType, message, NwkId = None, _context=None):
    # Log all activties towards ZiGate
    self.log.logging('Transport', logType, message, context = _context)

def logging_error( self, message, Nwkid=None, context=None):
    if self.pluginconf.pluginConf['trackTransportError']:
        self.Transport_logging( 'Error', message,  Nwkid, transport_error_context( self, context))



def transport_error_context( self, context):
    if context is None:
        context = {}
    context['Queues'] = {
        'ListOfCommands': dict.copy(self.ListOfCommands),
        'writeQueue': str(self.writer_queue.queue),
        'forwardQueue': str(self.forwarder_queue.queue),
        'SemaphoreValue': self.semaphore_gate._value,
        }
    context['Firmware'] = {
        'dzCommunication': self.force_dz_communication,
        'with_aps_sqn': self.firmware_with_aps_sqn ,
        'with_8012': self.firmware_with_8012,
        'nPDU': self.npdu,
        'aPDU': self.apdu,
        }
    context['Sqn Management'] = {
        'sqn_ZCL': self.sqn_zcl,
        'sqn_ZDP': self.sqn_zdp,
        'sqn_APS': self.sqn_aps,
        'current_SQN': self.current_sqn,
        }
    context['inMessage'] = {
        'ReqRcv': str(self._ReqRcv),
    }
    context['Thread'] = {
        'byPassDzCommunication': self.pluginconf.pluginConf['byPassDzConnection'],
        'ThreadName': threading.current_thread().name
    }
    return context


def logging_reader(self, logType, message, NwkId = None, _context=None):
    # Log all activties towards ZiGate
    self.log.logging('TransportRder', logType, message, context = _context)


def logging_flow_control(self, logType, message, NwkId = None, _context=None):
    # Log all activties towards ZiGate
    self.log.logging('TransportFlowCtrl', logType, message, context = _context)

def logging_forwarder(self, logType, message, NwkId = None, _context=None):
    # Log all activties towards ZiGate
    self.log.logging('TransportFrwder', logType, message, context = _context)

def logging_writer(self, logType, message, NwkId = None, _context=None):
    # Log all activities towards ZiGate
    self.log.logging('TransportWrter', logType, message, context = _context)
