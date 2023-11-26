def Decode8502(self, Devices, MsgData, MsgLQI):
    if self.OTA:
        self.OTA.ota_image_page_request(MsgData)