# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


import json
import queue
import time
from threading import Thread

from Classes.ZigateTransport.tools import handle_thread_error, release_command
from Modules.tools import is_hex
from Modules.zigateConsts import ZIGATE_MAX_BUFFER_SIZE


def start_writer_thread(self):

    if self.writer_thread is None:
        self.writer_thread = Thread(name="ZiGateWriter_%s" % self.hardwareid, target=writer_thread, args=(self,))
        self.writer_thread.start()


def writer_thread(self):
    self.logging_writer("Status", "ZigateTransport: writer_thread Thread start.")
    reset_line_out(self)
    while self.running:
        frame = None
        # Sending messages ( only 1 at a time )
        try:
            # self.logging_writer( 'Debug', "Waiting for next command Qsize: %s" %self.writer_queue.qsize())
            if self.writer_queue is None:
                break

            if (
                self.ZiGateHWVersion
                and self.ZiGateHWVersion == 1
                and self.pluginconf.pluginConf["nPDUaPDUThreshold"]
                and self.firmware_with_8012
            ):
                self.logging_writer(
                    "Debug",
                    "ZigateTransport: writer_thread Thread checking #nPDU: %s and #aPDU: %s." % (self.npdu, self.apdu),
                )

                if self.apdu > 2:
                    self.logging_writer("Log", "ZigateTransport: writer_thread Thread aPDU: %s retry later." % self.apdu)
                    time.sleep(0.25)
                    continue
                if self.npdu > 7:
                    self.logging_writer("Log", "ZigateTransport: writer_thread Thread nPDU: %s retry later." % self.npdu)
                    time.sleep(0.25)
                    continue

            entry = self.writer_queue.get()
            _isqn, command_str = entry
            if command_str == "STOP":
                break

            command = json.loads(command_str)
            if _isqn != command["InternalSqn"]:
                self.logging_writer(
                    "Debug",
                    "Hih Priority command HIsqn: %s Cmd: %s Data: %s i_sqn: %s"
                    % (_isqn, command["cmd"], command["datas"], command["InternalSqn"]),
                )

            # self.logging_writer( 'Debug', "New command received:  %s" %(command))
            if (
                isinstance(command, dict)
                and "cmd" in command
                and "datas" in command
                and "ackIsDisabled" in command
                and "waitForResponseIn" in command
                and "InternalSqn" in command
            ):
                if (command["cmd"], command["datas"]) in self.writer_list_in_queue:
                    self.logging_writer("Debug", "removing %s/%s from list_in_queue" % (command["cmd"], command["datas"]))
                    self.writer_list_in_queue.remove((command["cmd"], command["datas"]))

                if self.writer_queue.qsize() > self.statistics._MaxLoad:
                    self.statistics._MaxLoad = self.writer_queue.qsize()

                # if 'NwkId' in command:
                #    Domoticz.Log("Command on %s" %command['NwkId'])

                # if self.last_nwkid_failure and 'NwkId' in command and command['NwkId'] == self.last_nwkid_failure:
                #    self.logging_writer( 'Log', "removing %s/%s from list_in_queue as it failed previously" %( command['cmd'], command['datas'] ))
                #    # Looks like the command is still for the Nwkid which has failed. Drop
                #    continue

                self.last_nwkid_failure = None

                wait_for_semaphore(self, command)

                send_ok = thread_sendData(
                    self,
                    command["cmd"],
                    command["datas"],
                    command["ackIsDisabled"],
                    command["waitForResponseIn"],
                    command["InternalSqn"],
                )
                self.logging_writer("Debug", "Command sent!!!! %s send_ok: %s" % (command, send_ok))
                if send_ok in ("PortClosed", "SocketClosed"):
                    # Exit
                    break

                # Command sent, if needed wait in order to reduce throughput and load on ZiGate
                limit_throuput(self, command)

            else:
                self.logging_writer("Error", "Hops ... Don't known what to do with that %s" % command)

        except queue.Empty:
            # Empty Queue, timeout.
            pass

        except Exception as e:
            self.logging_writer("Error", "Error while receiving a ZiGate command: %s" % e)
            handle_thread_error(self, e, 0, 0, frame)

    self.logging_writer("Status", "ZigateTransport: writer_thread Thread stop.")


def limit_throuput(self, command):
    # Purpose is to have a regulate the load on ZiGate.
    # It is important for non 31e firmware, as we don't have all elements to regulate the flow
    #
    # It takes on an USB ZiGate around 70ms for a full turn around time between the commande sent and the 0x8011 received

    if self.firmware_compatibility_mode:
        # We are in firmware 31a where we control the flow is only on 0x8000
        # Throught put of 2 messages per seconds
        self.logging_writer("Debug", "Firmware 31a limit_throuput regulate to 500")
        time.sleep(0.500)

    elif not self.firmware_with_8012:
        # Firmware is not 31e
        # Throught put of 4 messages per seconds
        self.logging_writer("Debug", "Firmware 31d limit_throuput regulate to 300")
        time.sleep(0.350)

    elif self.firmware_nosqn:
        time.sleep(1.0)

    else:
        self.logging_writer("Debug", "Firmware 31e limit_throuput regulate to 100")
        time.sleep(0.100)


def wait_for_semaphore(self, command):
    if self.force_dz_communication or self.pluginconf.pluginConf["writerTimeOut"]:
        self.logging_writer("Debug", "Waiting for a write slot . Semaphore %s TimeOut of 8s" % (self.semaphore_gate._value))
        timeout_cmd = 4.0 if self.firmware_compatibility_mode else 8.0
        block_status = self.semaphore_gate.acquire(blocking=True, timeout=timeout_cmd)  # Blocking until 8s
    # else:
    #    self.logging_writer( 'Debug', "Waiting for a write slot . Semaphore %s ATTENTION NO TIMEOUT FOR TEST PURPOSES" %(self.semaphore_gate._value))
    #    block_status = self.semaphore_gate.acquire( blocking = True, timeout = None) # Blocking

    self.logging_writer(
        "Debug",
        "============= semaphore %s given with status %s ============== Len: ListOfCmd %s - %s writerQueueSize: %s"
        % (
            self.semaphore_gate._value,
            block_status,
            len(self.ListOfCommands),
            str(self.ListOfCommands.keys()),
            self.writer_queue.qsize(),
        ),
    )

    if self.pluginconf.pluginConf["writerTimeOut"] and not block_status:
        semaphore_timeout(self, command)


def thread_sendData(self, cmd, datas, ackIsDisabled, waitForResponseIn, isqn):
    self.logging_writer("Debug", "thread_sendData")
    if datas is None:
        datas = ""

    # Check if Datas are hex
    if datas != "" and not is_hex(datas):
        context = {
            "Error code": "TRANS-SENDDATA-01",
            "Cmd": cmd,
            "Datas": datas,
            "ackIsDisabled": ackIsDisabled,
            "waitForResponseIn": waitForResponseIn,
            "InternalSqn": isqn,
        }
        self.logging_writer("Error", "sendData", _context=context)
        return "BadData"

    self.ListOfCommands[isqn] = {
        "cmd": cmd,
        "datas": datas,
        "ackIsDisabled": ackIsDisabled,
        "waitForResponseIn": waitForResponseIn,
        "Status": "SENT",
        "TimeStamp": time.time(),
        "Semaphore": self.semaphore_gate._value,
    }
    self.statistics._sent += 1
    if self.pluginconf.pluginConf["debugzigateCmd"]:
        self.logging_writer("Log", "_sendData to ZiGate NOW  - [%s] %s %s" % (isqn, cmd, datas))

    return write_to_zigate(self, self._connection, bytes.fromhex(encode_message(cmd, datas)))


def encode_message(cmd, datas):

    if datas == "":
        length = "0000"
        checksumCmd = get_checksum(cmd, length, "0")
        strchecksum = "0" + checksumCmd if len(checksumCmd) == 1 else checksumCmd
        return "01" + zigate_encode(cmd) + zigate_encode(length) + zigate_encode(strchecksum) + "03"

    length = "%04x" % (len(datas) // 2)
    checksumCmd = get_checksum(cmd, length, datas)
    strchecksum = "0" + checksumCmd if len(checksumCmd) == 1 else checksumCmd
    return "01" + zigate_encode(cmd) + zigate_encode(length) + zigate_encode(strchecksum) + zigate_encode(datas) + "03"


def zigate_encode(Data):
    # The encoding is the following:
    # Let B any byte value of the message. If B is between 0x00 and 0x0f (included) then :
    #    Instead of B, a 2-byte content will be written in the encoded frame
    #    The first byte is a fixed value: 0x02
    #    The second byte is the result of B ^ 0x10

    Out = ""
    Outtmp = ""
    for c in Data:
        Outtmp += c
        if len(Outtmp) == 2:
            if Outtmp[0] == "1" and Outtmp != "10":
                if Outtmp[1] == "0":
                    Outtmp = "0200"
                Out += Outtmp
            elif Outtmp[0] == "0":
                Out += "021" + Outtmp[1]
            else:
                Out += Outtmp
            Outtmp = ""
    return Out


def get_checksum(msgtype, length, datas):
    temp = 0 ^ int(msgtype[0:2], 16)
    temp ^= int(msgtype[2:4], 16)
    temp ^= int(length[0:2], 16)
    temp ^= int(length[2:4], 16)
    chk = 0
    for i in range(0, len(datas), 2):
        temp ^= int(datas[i : i + 2], 16)
        chk = hex(temp)
    return chk[2:4]


def write_to_zigate(self, serialConnection, encoded_data):
    # self.logging_writer('Log', "write_to_zigate")

    if len(encoded_data) >= ZIGATE_MAX_BUFFER_SIZE:
        self.logging_writer("Error", "write_to_zigate - looks like your frame is greated than the maximum ZiGate buffer size: %s" % encoded_data)
        
    if self.pluginconf.pluginConf["byPassDzConnection"] and not self.force_dz_communication:
        return native_write_to_zigate(self, serialConnection, encoded_data)

    return domoticz_write_to_zigate(self, encoded_data)


def domoticz_write_to_zigate(self, encoded_data):
    if self._connection:
        self._connection.Send(encoded_data, 0)
        return True

    self.logging_writer("Error", "domoticz_write_to_zigate - No connection available: %s" % self._connection)
    return False


def reset_line_out(self):
    if (
        self._transp
        not in (
            "Wifi",
            "V2-Wifi",
        )
        and not self.force_dz_communication
    ):
        self.logging_writer("Debug", "Reset Serial Line OUT")
        if self._connection:
            self._connection.reset_output_buffer()


def native_write_to_zigate(self, serialConnection, encoded_data):

    if self._transp in (
        "Wifi",
        "V2-Wifi",
    ):
        self.tcp_send_queue.put(encoded_data)
        return True

    self.serial_send_queue.put(encoded_data)
    return True


def semaphore_timeout(self, current_command):
    # Semaphore has been Release due to Timeout
    # In that case we should release the pending command in ListOfCommands
    if len(self.ListOfCommands) == 2:
        if list(self.ListOfCommands.keys())[0] == current_command["InternalSqn"]:
            # We remove element [1]
            isqn_to_be_removed = list(self.ListOfCommands.keys())[1]
        else:
            # We remove element [0]
            isqn_to_be_removed = list(self.ListOfCommands.keys())[0]

        context = {
            "Error code": "TRANS-SEMAPHORE-01",
            "ListofCmds": dict.copy(self.ListOfCommands),
            "IsqnCurrent": current_command["InternalSqn"],
            "IsqnToRemove": isqn_to_be_removed,
        }
        if not self.force_dz_communication and self.pluginconf.pluginConf["showTimeOutMsg"]:
            self.logging_writer("Error", "writerThread Timeout ", _context=context)
        release_command(self, isqn_to_be_removed)
        return

    # We need to find which Command is in Timeout
    context = {
        "Error code": "TRANS-SEMAPHORE-02",
        "ListofCmds": dict.copy(self.ListOfCommands),
        "IsqnCurrent": current_command["InternalSqn"],
        "IsqnToRemove": [],
    }
    for x in list(self.ListOfCommands):
        if x == current_command["InternalSqn"]:
            # On going command, this one is the one accepted via the Timeout
            continue
        if time.time() + 8 >= self.ListOfCommands[x]["TimeStamp"]:
            # This command has at least 8s life and can be removed
            release_command(self, x)
            context["IsqnToRemove"].append(x)

    if not self.force_dz_communication and self.pluginconf.pluginConf["showTimeOutMsg"]:
        self.logging_writer("Error", "writerThread Timeout ", _context=context)
