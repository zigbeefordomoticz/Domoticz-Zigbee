def Decode8503(self, Devices, MsgData, MsgLQI):
    if self.OTA:
        self.OTA.ota_upgrade_end_request(MsgData)