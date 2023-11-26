def Decode8060(self, Devices, MsgData, MsgLQI):
    if self.groupmgt:
        self.groupmgt.add_group_member_ship_response(MsgData)
        
        
def Decode8061(self, Devices, MsgData, MsgLQI):
    if self.groupmgt:
        self.groupmgt.check_group_member_ship_response(MsgData)
        
        
def Decode8062(self, Devices, MsgData, MsgLQI):
    if self.groupmgt:
        self.groupmgt.look_for_group_member_ship_response(MsgData)
        
        
def Decode8063(self, Devices, MsgData, MsgLQI):
    if self.groupmgt:
        self.groupmgt.remove_group_member_ship_response(MsgData)