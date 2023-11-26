def Decode8501(self, Devices, MsgData, MsgLQI):
    """BLOCK_REQUEST  0x8501  ZiGate will receive this command when device asks OTA firmware"""
    if self.OTA:
        self.OTA.ota_image_block_request(MsgData)