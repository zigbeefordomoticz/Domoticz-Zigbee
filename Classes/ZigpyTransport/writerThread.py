import json
import queue
import select
import socket
import time
from threading import Thread

import Domoticz
from Classes.Transport.tools import handle_thread_error, release_command
from Modules.tools import is_hex
from Modules.zigateConsts import ZIGATE_MAX_BUFFER_SIZE


def start_writer_thread(self):
    self.writer_thread.start()
    

def stop_writer_thread(self):
    self.writer_queue.put((1, "STOP")) 


def writer_thread(self):
    self.logging_writer("Status", "ZigyTransport: writer_thread Thread start.")

    while self.running:
        # Sending messages ( only 1 at a time )
        try:
            # self.logging_writer( 'Debug', "Waiting for next command Qsize: %s" %self.writer_queue.qsize())
            if self.writer_queue is None:
                break

            prio, entry = self.writer_queue.get()
            if entry == "STOP":
                break

            command = json.loads(entry)
            #self.ZigateComm.request(self, device, profile, cluster, src_ep, dst_ep, sequence, data, expect_reply=True, use_ieee=False)
            
            if self.writer_queue.qsize() > self.statistics._MaxLoad:
                self.statistics._MaxLoad = self.writer_queue.qsize()

        except queue.Empty:
            # Empty Queue, timeout.
            pass

        except Exception as e:
            self.logging_writer("Error", "Error while receiving a ZiGate command: %s" % e)
            handle_thread_error(self, e, 0, 0, "None")

    self.logging_writer("Status", "ZigyTransport: writer_thread Thread stop.")
