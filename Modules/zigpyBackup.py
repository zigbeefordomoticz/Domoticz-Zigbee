



def handle_zigpy_backup(self, backups):

    if not backups:
        self.log.logging("TransportZigpy", "Log","Backup is incomplete, it is not possible to restore")
        return

    self.log.logging("TransportZigpy", "Log", "Backups: %s" %backups)
    self.log.logging("TransportZigpy", "Log", "  Type: %s " %type(backups))
    self.log.logging("TransportZigpy", "Log", "  Backups.backups: %s " %(backups.backups))
    self.log.logging("TransportZigpy", "Log", "     Type: %s " %type(backups.backups))


    

