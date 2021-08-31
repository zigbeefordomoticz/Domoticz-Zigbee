#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: @pipiche38
#
"""
    Module: pdmHost.py

    Description: Implement the PDM on Host functionality.

"""


from Classes.LoggingManagement import LoggingManagement
from Modules.basicOutputs import sendZigateCmd

import Domoticz
import datetime
import os.path
import json

PDM_E_STATUS_OK = "00"
PDM_E_STATUS_INVLD_PARAM = "01"
#  EEPROM based PDM codes
PDM_E_STATUS_PDM_FULL = "02"
PDM_E_STATUS_NOT_SAVED = "03"
PDM_E_STATUS_RECOVERED = "04"
PDM_E_STATUS_PDM_RECOVERED_NOT_SAVED = "05"
PDM_E_STATUS_USER_BUFFER_SIZE = "06"
PDM_E_STATUS_SATURATED_OK = "00"
PDM_E_STATUS_BITMAP_SATURATED_NO_INCREMENT = "07"
PDM_E_STATUS_BITMAP_SATURATED_OK = "08"
PDM_E_STATUS_IMAGE_BITMAP_COMPLETE = "09"
PDM_E_STATUS_IMAGE_BITMAP_INCOMPLETE = "0A"
PDM_E_STATUS_INTERNAL_ERROR = "0B"

MAX_LOAD_BLOCK_SIZE = 256  # Max Block size in Bytes, send to Zigate


def Decode8035(self, Devices, MsgData, MsgLQI):

    # Payload: 030000f104

    PDU_EVENT = {
        "00": "E_PDM_SYSTEM_EVENT_WEAR_COUNT_TRIGGER_VALUE_REACHED",
        "01": "E_PDM_SYSTEM_EVENT_DESCRIPTOR_SAVE_FAILED",
        "02": "E_PDM_SYSTEM_EVENT_PDM_NOT_ENOUGH_SPACE",
        "03": "E_PDM_SYSTEM_EVENT_LARGEST_RECORD_FULL_SAVE_NO_LONGER_POSSIBLE",
        "04": "E_PDM_SYSTEM_EVENT_SEGMENT_DATA_CHECKSUM_FAIL",
        "05": "E_PDM_SYSTEM_EVENT_SEGMENT_SAVE_OK",
        "06": "E_PDM_SYSTEM_EVENT_EEPROM_SEGMENT_HEADER_REPAIRED",
        "07": "E_PDM_SYSTEM_EVENT_SYSTEM_INTERNAL_BUFFER_WEAR_COUNT_SWAP",
        "08": "E_PDM_SYSTEM_EVENT_SYSTEM_DUPLICATE_FILE_SEGMENT_DETECTED",
        "09": "E_PDM_SYSTEM_EVENT_SYSTEM_ERROR",
        "0a": "E_PDM_SYSTEM_EVENT_SEGMENT_PREWRITE",
        "0b": "E_PDM_SYSTEM_EVENT_SEGMENT_POSTWRITE",
        "0c": "E_PDM_SYSTEM_EVENT_SEQUENCE_DUPLICATE_DETECTED",
        "0d": "E_PDM_SYSTEM_EVENT_SEQUENCE_VERIFY_FAIL",
        "0e": "E_PDM_SYSTEM_EVENT_PDM_SMART_SAVE",
        "0f": "E_PDM_SYSTEM_EVENT_PDM_FULL_SAVE",
    }

    eventCode = MsgData[0:2]
    u32eventNumber = MsgData[2:10]

    if eventCode in PDU_EVENT:
        self.log.logging(
            "PDM",
            "Debug",
            "eventCode: %s (%s) eventNumber: %s" % (eventCode, PDU_EVENT[eventCode], u32eventNumber),
        )
        if eventCode == "00":  # E_PDM_SYSTEM_EVENT_WEAR_COUNT_TRIGGER_VALUE_REACHED=0,
            pass
        elif eventCode == "01":  # E_PDM_SYSTEM_EVENT_DESCRIPTOR_SAVE_FAILED,
            # Fatal Error
            Domoticz.Error(
                "Decode8035 - PDM Fata Error %s (%s) Record Failure: %s. Factory Reset might be needed!"
                % (eventCode, PDU_EVENT[eventCode], u32eventNumber)
            )

        elif eventCode == "02":  # E_PDM_SYSTEM_EVENT_PDM_NOT_ENOUGH_SPACE,
            # Fatal Error
            Domoticz.Error(
                "Decode8035 - PDM Fata Error %s (%s) Record Failure %s. Factory Reset might be needed!"
                % (eventCode, PDU_EVENT[eventCode], u32eventNumber)
            )

        elif eventCode == "03":  # E_PDM_SYSTEM_EVENT_LARGEST_RECORD_FULL_SAVE_NO_LONGER_POSSIBLE,
            u16IdValue = u32eventNumber
            pass
        elif eventCode == "04":  # E_PDM_SYSTEM_EVENT_SEGMENT_DATA_CHECKSUM_FAIL,
            pass
        elif eventCode == "05":  # E_PDM_SYSTEM_EVENT_SEGMENT_SAVE_OK,
            pass
        elif eventCode == "06":  # E_PDM_SYSTEM_EVENT_EEPROM_SEGMENT_HEADER_REPAIRED,
            # This code can be ignored by the application software and only needs to be logged
            # if requested by NXP Tech-nical Support.
            pass
        elif eventCode == "07":  # E_PDM_SYSTEM_EVENT_SYSTEM_INTERNAL_BUFFER_WEAR_COUNT_SWAP,
            # This code can be ignored by the application software and only needs to be logged
            # if requested by NXP Tech-nical Support.
            pass
        elif eventCode == "08":  # E_PDM_SYSTEM_EVENT_SYSTEM_DUPLICATE_FILE_SEGMENT_DETECTED,
            # This code can be ignored by the application software and only needs to be logged
            # if requested by NXP Tech-nical Support.
            pass
        elif eventCode == "09":  # E_PDM_SYSTEM_EVENT_SYSTEM_ERROR,
            # This code can be ignored by the application software and only needs to be logged
            # if requested by NXP Tech-nical Support.
            pass
        else:
            self.log.logging(
                "PDM",
                "Debug",
                "Decode8035 - PDM event : eventCode: %s (%s) eventNumber"
                % (eventCode, PDU_EVENT[eventCode], u32eventNumber),
            )
    else:
        self.log.logging(
            "PDM",
            "Debug",
            "Decode8035 - PDM event : eventCode: %s eventNumber" % (eventCode, u32eventNumber),
        )


## PDM HOST
def Decode0300(self, Devices, MsgData, MsgLQI):

    self.log.logging("Input", "Log", "Decode0300 - PDMHostAvailableRequest: %20.20s" % (MsgData))
    pdmHostAvailableRequest(self, MsgData)


def Decode0301(self, Devices, MsgData, MsgLQI):

    self.log.logging("Input", "Log", "Decode0301 - E_SL_MSG_ASC_LOG_MSG: %20.20s" % (MsgData))


def Decode0302(self, Devices, MsgData, MsgLQI):

    self.log.logging("Input", "Log", "Decode0302 - PDMloadConfirmed: %20.20s" % (MsgData))
    pdmLoadConfirmed(self, MsgData)


def Decode0200(self, Devices, MsgData, MsgLQI):

    # self.log.logging( "Input", 'Debug',  "Decode0200 - PDMSaveRequest: %20.20s" %(MsgData))
    PDMSaveRequest(self, MsgData)


def Decode0201(self, Devices, MsgData, MsgLQI):

    # self.log.logging( "Input", 'Debug',  "Decode0201 - PDMLoadRequest: %20.20s" %(MsgData))
    PDMLoadRequest(self, MsgData)


def Decode0202(self, Devices, MsgData, MsgLQI):

    # self.log.logging( "Input", 'Debug',  "Decode0202 - PDMDeleteAllRecord: %20.20s" %(MsgData))
    PDMDeleteAllRecord(self, MsgData)


def Decode0203(self, Devices, MsgData, MsgLQI):

    # self.log.logging( "Input", 'Debug',  "Decode0203 - PDMDeleteRecord: %20.20s" %(MsgData))
    PDMDeleteRecord(self, MsgData)


def Decode0204(self, Devices, MsgData, MsgLQI):

    # self.log.logging( "Input", 'Debug',  "Decode0204 - E_SL_MSG_CREATE_BITMAP_RECORD_REQUEST: %20.20s" %(MsgData))
    PDMCreateBitmap(self, MsgData)


def Decode0205(self, Devices, MsgData, MsgLQI):

    # self.log.logging( "Input", 'Debug',  "Decode0205 - E_SL_MSG_DELETE_BITMAP_RECORD_REQUEST: %20.20s" %(MsgData))
    PDMDeleteBitmapRequest(self, MsgData)


def Decode0206(self, Devices, MsgData, MsgLQI):

    # self.log.logging( "Input", 'Debug',  "Decode0206 - PDMGetBitmapRequest: %20.20s" %(MsgData))
    PDMGetBitmapRequest(self, MsgData)


def Decode0207(self, Devices, MsgData, MsgLQI):

    # self.log.logging( "Input", 'Debug',  "Decode0207 - PDMIncBitmapRequest: %20.20s" %(MsgData))
    PDMIncBitmapRequest(self, MsgData)


def Decode0208(self, Devices, MsgData, MsgLQI):

    # self.log.logging( "Input", 'Debug',  "Decode0208 - PDMExistanceRequest: %20.20s" %(MsgData))
    PDMExistanceRequest(self, MsgData)


def openPDM(self):
    def _copyfile(source, dest, move=True):
        try:
            import shutil

            if move:
                shutil.move(source, dest)
            else:
                shutil.copy(source, dest)
        except:
            with open(source, "r") as src, open(dest, "wt") as dst:
                for line in src:
                    dst.write(line)
            return

    def _versionFile(source, nbversion):

        if nbversion == 0:
            return

        if nbversion == 1:
            _copyfile(source, source + "-%02d" % 1)

        else:
            for version in range(nbversion - 1, 0, -1):
                _fileversion_n = source + "-%02d" % version
                if not os.path.isfile(_fileversion_n):
                    continue
                else:
                    _fileversion_n1 = source + "-%02d" % (version + 1)
                    _copyfile(_fileversion_n, _fileversion_n1)
            # Last one
            _copyfile(source, source + "-%02d" % 1, move=False)

    self.PDM = {}
    # zigatePDMfilename = self.pluginconf.pluginConf['pluginData'] + "zigatePDM-%02d.pck" %self.HardwareID
    # if os.path.isfile(zigatePDMfilename):
    #    with open( zigatePDMfilename, 'rb') as zigatePDMfile:
    #        self.PDM = pickle.load( zigatePDMfile )
    zigatePDMfilename = self.pluginconf.pluginConf["pluginData"] + "zigatePDM-%02d.json" % self.HardwareID
    if os.path.isfile(zigatePDMfilename):
        _versionFile(zigatePDMfilename, 12)
        with open(zigatePDMfilename, "r") as zigatePDMfile:
            self.PDM = {}
            try:
                self.PDM = json.load(zigatePDMfile)

            except json.decoder.JSONDecodeError as e:
                Domoticz.Error("error while reading Zigate PDM on Host %s, not JSON: %s" % (zigatePDMfilename, e))


def savePDM(self):

    # zigatePDMfilename = self.pluginconf.pluginConf['pluginData'] + "zigatePDM-%02d.pck" %self.HardwareID
    # with open( zigatePDMfilename, 'wb') as zigatePDMfile:
    #   pickle.dump( self.ListOfGroups, zigatePDMfile, protocol=pickle.HIGHEST_PROTOCOL)

    if self.PDM is None:
        return
    zigatePDMfilename = self.pluginconf.pluginConf["pluginData"] + "zigatePDM-%02d.json" % self.HardwareID
    with open(zigatePDMfilename, "wt") as zigatePDMfile:
        try:
            json.dump(self.PDM, zigatePDMfile, indent=4, sort_keys=True)
        except IOError:
            Domoticz.Error("Error while writing Zigate Network Details%s" % zigatePDMfile)


def pdmHostAvailableRequest(self, MsgData):
    # Decode0300

    self.log.logging("PDM", "Debug", "pdmHostAvailableRequest - receiving 0x0300 with data: %s" % (MsgData))
    self.PDMready = False

    status = PDM_E_STATUS_OK

    # Allow only PDM traffic
    self.ZigateComm.pdm_lock(True)

    # Open PDM file and populate the Data Structure self.PDM
    if self.PDM is None:
        openPDM(self)
    sendZigateCmd(self, "8300", status)


def pdmLoadConfirmed(self, MsgData):

    self.log.logging("PDM", "Debug", "pdmLoadConfirmed - receiving 0x0302 with data: %s" % (MsgData))
    # Decode0302
    savePDM(self)

    # Allow ALL traffic
    self.ZigateComm.pdm_lock(False)

    # Let's tell the plugin that we can enter in run mode.
    self.PDMready = True


def PDMSaveRequest(self, MsgData):
    """
    We received from the zigate a buffer to write down to the PDM.
    Data can come in several blocks for the same RecordID.
    Only copmplete record must be save into the Persistent structure
    #Decode0200
    """

    self.log.logging("PDM", "Debug", "PDMSaveRequest - receiving 0x0200 with data: %s" % (MsgData))

    if self.PDM is None:
        openPDM(self)
    # Allow only PDM traffic
    self.ZigateComm.pdm_lock(True)

    RecordId = MsgData[:4]  # record ID
    u16Size = MsgData[4:8]  # total PDM record size
    u16NumberOfWrites = MsgData[8:12]  # total number of block writes expected
    u16BlocksWritten = MsgData[12:16]  # This number corresponds to the block id from 0 to (NumberOfWrite - 1)
    dataReceived = int(MsgData[16:20], 16)  # Send size of this particular block (number of bytes)
    sWriteData = MsgData[20 : 20 + (2 * dataReceived)]  # bytes is coded into 2 chars

    self.log.logging(
        "PDM",
        "Debug",
        "      --------- RecordId: %s, u16Size: %s, u16BlocksWritten: %s, u16NumberOfWrites: %s, dataReceived: %s "
        % (RecordId, u16Size, u16BlocksWritten, u16NumberOfWrites, dataReceived),
    )

    if RecordId not in self.PDM:
        self.PDM[RecordId] = {}

    # We assume block comes in the righ order
    if int(u16BlocksWritten, 16) == 0:
        # First block, we rest the Temporary structure
        self.PDM[RecordId]["ReceivingData"] = ""
    self.PDM[RecordId]["ReceivingData"] += sWriteData

    if int(u16NumberOfWrites, 16) == int(u16BlocksWritten, 16) + 1:
        # All Blocks received
        Domoticz.Log("Saving on Disk RecordId: %s RecordData: %s" % (RecordId, self.PDM[RecordId]["ReceivingData"]))
        self.PDM[RecordId]["RecSize"] = u16Size
        self.PDM[RecordId]["PersistedData"] = self.PDM[RecordId]["ReceivingData"]
        self.PDM[RecordId]["ReceivingData"] = ""
        if self.PDMready:
            savePDM(self)

    datas = PDM_E_STATUS_OK + RecordId + u16BlocksWritten
    sendZigateCmd(self, "8200", datas)

    if (int(u16BlocksWritten, 16) + 1) == int(u16NumberOfWrites, 16):
        # Allow ALL traffic
        self.ZigateComm.pdm_lock(False)


def PDMLoadRequest(self, MsgData):
    """
    Retreive RecordID from PDM (on Host) and send it back to Zigate
    Must be split into bocks as a block size is limited to
    """
    # Decode0201
    #  Send the Host PDM to Zigate
    #

    self.log.logging("PDM", "Debug", "PDMLoadRequest - receiving 0x0200 with data: %s" % (MsgData))
    RecordId = MsgData[0:4]

    if self.PDM is None:
        openPDM(self)
    # Allow only PDM traffic
    self.ZigateComm.pdm_lock(True)

    if RecordId not in self.PDM:
        # Record not found
        TotalRecordSize = 0
        TotalBlocks = 0
        BlockId = 1
        CurentBlockSize = 0

        datas = PDM_E_STATUS_OK  # response status
        datas += RecordId  # record id
        datas += "%04x" % TotalRecordSize  # total record size in bytes
        datas += "%04x" % TotalBlocks  # total number of expected blocks for this record
        datas += "%04x" % BlockId  # block number for this record
        datas += "%04x" % CurentBlockSize  # size of this block in bytes

        self.log.logging(
            "PDM",
            "Debug",
            "PDMLoadRequest - Sending 0x8201 : RecordId: %s TotalRecordSize: %s TotalBlocks: %s BlockId: %s CurentBlockSize: %s"
            % (RecordId, TotalRecordSize, TotalBlocks, BlockId, CurentBlockSize),
        )

        sendZigateCmd(self, "8201", datas)
        # Allow ALL traffic
        self.ZigateComm.pdm_lock(False)
    else:
        # Let's retreive the recordID Data and RecordSize from PDM
        persistedData = self.PDM[RecordId]["PersistedData"]
        u16TotalRecordSize = int(self.PDM[RecordId]["RecSize"], 16)

        # Sanity Check is the retreived Data lenght match the expected record size
        if len(persistedData) != 2 * u16TotalRecordSize:
            Domoticz.Error(
                "PDMLoadRequest - Loaded data is incomplete, Real size: %s Expected size: %s"
                % (len(persistedData), u16TotalRecordSize)
            )
            return

        # Compute the number of Blocks. One block size is 128Bytes
        _TotalBlocks = u16TotalRecordSize // MAX_LOAD_BLOCK_SIZE
        if (u16TotalRecordSize % MAX_LOAD_BLOCK_SIZE) > 0:
            TotalBlocksToSend = _TotalBlocks + 1
        else:
            TotalBlocksToSend = _TotalBlocks

        # At that stage TotalBlocksToSend is the number of expected Total Blocks to be received and writen
        lowerBound = upperBound = u16CurrentBlockId = u16CurrentBlockSize = 0

        bMoreData = True
        while bMoreData:
            u16CurrentBlockSize = u16TotalRecordSize - (u16CurrentBlockId * MAX_LOAD_BLOCK_SIZE)
            if u16CurrentBlockSize > MAX_LOAD_BLOCK_SIZE:
                u16CurrentBlockSize = MAX_LOAD_BLOCK_SIZE
            else:
                bMoreData = False

            u16CurrentBlockId += 1
            datas = "02"
            datas += RecordId
            datas += "%04x" % u16TotalRecordSize
            datas += "%04x" % TotalBlocksToSend
            datas += "%04x" % u16CurrentBlockId
            datas += "%04x" % u16CurrentBlockSize
            upperBound += 2 * u16CurrentBlockSize
            datas += persistedData[lowerBound:upperBound]

            self.log.logging(
                "PDM",
                "Debug",
                "PDMLoadRequest - Sending 0x8201 : RecordId: %s TotalRecordSize: %s TotalBlocks: %s BlockId: %s CurentBlockSize: %s"
                % (RecordId, u16TotalRecordSize, TotalBlocksToSend, u16CurrentBlockId, u16CurrentBlockSize),
            )
            sendZigateCmd(self, "8201", datas)

            lowerBound += 2 * u16CurrentBlockSize
            if not bMoreData:
                # Allow ALL traffic
                self.ZigateComm.pdm_lock(False)


def PDMDeleteAllRecord(self, MsgData):
    "E_SL_MSG_DELETE_ALL_PDM_RECORDS_REQUEST"
    "Decode0202"

    self.log.logging("PDM", "Debug", "PDMDeleteAllRecord - Remove ALL records with data: %s" % (MsgData))
    if self.PDM is None:
        openPDM(self)
    del self.PDM
    self.PDM = {}
    if self.PDMready:
        savePDM(self)


def PDMDeleteRecord(self, MsgData):
    "E_SL_MSG_DELETE_PDM_RECORD_REQUEST"
    "Decode0203"

    self.log.logging("PDM", "Debug", "PDMDeleteRecord - receiving 0x0202 with data: %s" % (MsgData))

    RecordId = MsgData[:4]  # record ID
    if self.PDM is None:
        openPDM(self)

    if RecordId in self.PDM:
        del self.PDM[RecordId]
    if self.PDMready:
        savePDM(self)


def PDMCreateBitmap(self, MsgData):
    # create a bitmap counter
    # Decode0204
    # https://www.nxp.com/docs/en/user-guide/JN-UG-3116.pdf
    """
    The function creates a bitmap structure for a counter in a segment of the EEPROM.
    A user-defined ID and a start value for the bitmap counter must be specified.
    The start value is stored in the counter’s header. A bitmap is created to store
    the incremental value of the counter (over the start value).
    This bitmap can subsequently be incremented (by one) by calling the function PDM_eIncrementBitmap().
    The incremental value stored in the bitmap and the start value stored in the header
    can be read at any time using the function PDM_eGetBitmap().
    If the specified ID value has already been used or the specified start value is NULL,
    the function returns PDM_E_STATUS_INVLD_PARAM.
    If the EEPROM has no free segments, the function returns PDM_E_STATUS_USER_PDM_FULL.
    """

    RecordId = MsgData[0:4]
    BitMapValue = MsgData[4:12]

    self.log.logging(
        "PDM", "Debug", "PDMCreateBitmap - Create Bitmap counter RecordId: %s BitMapValue: %s" % (RecordId, BitMapValue)
    )
    # Do what ever has to be done
    if self.PDM is None:
        openPDM(self)

    if RecordId not in self.PDM:
        self.PDM[RecordId] = {}

    if "Bitmap" not in self.PDM[RecordId]:
        self.PDM[RecordId]["Bitmap"] = {}

    self.PDM[RecordId]["Bitmap"] = BitMapValue

    sendZigateCmd(self, "8204", RecordId)


def PDMDeleteBitmapRequest(self, MsgData):
    """
    This function deletes the specified counter in the EEPROM. The counter must be identified using
    the user-defined ID value assigned when the bitmap was created using the function PDM_eCreateBitmap().
    The function can be used to formally delete a counter. It clears the current segment occupied by the
    counter and also all the older (expired) segments used for the counter. This deletion increments the
    Wear Counts for these segments and should be done only if absolutely necessary, as the expired segments
    can be re-used directly via the PDM without formal deletion.

    """
    # Decode0205

    RecordId = MsgData[0:4]

    self.log.logging("PDM", "Debug", "PDMDeleteBitmapRequest - Delete Bitmap counter RecordId: %s" % (RecordId))
    # Do what ever has to be done

    if self.PDM is None:
        openPDM(self)

    if RecordId not in self.PDM:
        return

    if "Bitmap" in self.PDM[RecordId]:
        del self.PDM[RecordId]["Bitmap"]


def PDMGetBitmapRequest(self, MsgData):
    """
    The function reads the specified counter value from the EEPROM.
    The counter must be identified using the user-defined ID value assigned when the counter was created using
    the function PDM_eCreateBitmap().
    The function returns the counter’s start value (from the counter’s header) and incremental value
    (from the counter’s bitmap).
    The counter value is calculated as:
        Start Value + Incremental Value
    or in terms of the function parameters:
        *pu32InitialValue + *pu32BitmapValueNote
    that the start value may be different from the one specified when the counter was created,
    as the start value is updated each time the counter outgrows a segment and the bitmap is
    reset to zero.
    This function should be called when the device comes up from a cold start,
    to check whether a bitmap counter is present in EEPROM.
    If the specified ID value has already been used or a NULL pointer is provided for the received values,
    the function returns PDM_E_STATUS_INVLD_PARAM.
    """
    # Decode0206
    self.log.logging("PDM", "Debug", "PDMGetBitmapRequest - Get BitMaprequest data: %s" % (MsgData))

    RecordId = MsgData[0:4]
    if self.PDM is None:
        openPDM

    status = PDM_E_STATUS_OK

    datas = status + RecordId + "%08x" % 0

    if RecordId not in self.PDM:
        self.PDM[RecordId] = {}
    if "Bitmap" not in self.PDM[RecordId]:
        self.PDM[RecordId]["Bitmap"] = "%08x" % 0

    counter = int(self.PDM[RecordId]["Bitmap"], 16)
    datas = status + RecordId + "%08x" % counter

    sendZigateCmd(self, "8206", datas)
    self.log.logging("PDM", "Debug", "PDMGetBitmapRequest - Sending 0x8206 data: %s" % (datas))


def PDMIncBitmapRequest(self, MsgData):
    """
    The function increments the bitmap value of the specified counter in the EEPROM.
    The counter must be identified using the user-defined ID value assigned when the counter
    was created using the function PDM_eCreateBitmap().
    The bitmap can be incremented within an EEPROM segment until its value saturates (contains all 1s).
    At this point, the function returns the code PDM_E_STATUS_SATURATED_OK.
    The next time that this function is called, the counter is automatically moved to a
    new segment (provided that one is available), the start value in its header is increased appropriately and
    the bitmap is reset to zero.
    To avoid increasing the segment Wear Count, the old segment is not formally deleted before a new segment is started.
    If the EEPROM has no free segments when the above overflow occurs,
    the function returns the code PDM_E_STATUS_USER_PDM_FULL.
    If the specified ID value has already been used, the function returns PDM_E_STATUS_INVLD_PARAM.
    """
    # Decode0207

    self.log.logging("PDM", "Debug", "PDMIncBitmapRequest - Inc BitMap request data: %s" % (MsgData))

    RecordId = MsgData[0:4]
    if self.PDM is None:
        openPDM(self)

    datas = "00" + RecordId + "%08x" % 0

    if RecordId not in self.PDM:
        self.PDM[RecordId] = {}
    if "Bitmap" not in self.PDM[RecordId]:
        self.PDM[RecordId]["Bitmap"] = "%08x" % 0

    status = PDM_E_STATUS_OK
    Counter = int(self.PDM[RecordId]["Bitmap"], 16) + 1
    self.PDM[RecordId]["Bitmap"] = "%08X" % Counter

    if int(self.PDM[RecordId]["Bitmap"], 16) == 0xFFFFFFFF:
        # Let's check if counter is saturated, if so we move to a new segment (in fact on Host, simply restart at 0)
        # Next time it will be at 0
        status = PDM_E_STATUS_SATURATED_OK
        self.PDM[RecordId]["Bitmap"] = "%08X" % 0

    datas = status + RecordId + "%08x" % Counter

    sendZigateCmd(self, "8207", datas)
    self.log.logging("PDM", "Debug", "PDMIncBitmapRequest - Sending 0x8207 data: %s" % (datas))
    savePDM(self)


def PDMExistanceRequest(self, MsgData):
    "E_SL_MSG_PDM_EXISTENCE_REQUEST"
    # Decode0208

    self.log.logging("PDM", "Debug", "PDMExistanceRequest - receiving 0x0208 with data: %s" % (MsgData))
    RecordId = MsgData[0:4]
    if self.PDM is None:
        openPDM(self)

    recordExist = 0x00
    if RecordId in self.PDM and "PersistedData" in self.PDM[RecordId]:
        recordExist = 0x01
        persistedData = self.PDM[RecordId]["PersistedData"]
        size = self.PDM[RecordId]["RecSize"]

    if not recordExist:
        recordExist = 0x00
        size = "%04x" % 0
        persistedData = None

    self.log.logging(
        "PDM",
        "Debug",
        "      --------- RecordId: %s, u16Size: %s, recordExist: %s" % (RecordId, size, recordExist == 0x01),
    )

    datas = RecordId
    datas += "%02x" % recordExist  # 0x00 not exist, 0x01 exist
    datas += size

    sendZigateCmd(self, "8208", datas)
    self.log.logging("PDM", "Debug", "PDMExistanceRequest - Sending 0x8208 data: %s" % (datas))
