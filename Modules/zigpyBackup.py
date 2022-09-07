
import Domoticz


import Modules.tools

def handle_zigpy_backup(self, backups):

    if not backups:
        self.log.logging("TransportZigpy", "Log","Backup is incomplete, it is not possible to restore")
        return

    _coordinator_backup = self.pluginconf.pluginConf["pluginData"] + "/Coordinator-%02d" %self.HardwareID + ".backup"

    self.log.logging("TransportZigpy", "Log", "Backups: %s" %backups)
    Modules.tools.helper_versionFile(_coordinator_backup, self.pluginconf.pluginConf["numDeviceListVersion"])

    try:
        with open(_coordinator_backup, "wt") as file:
            file.write(str(backups) + "\n")
            self.log.logging("TransportZigpy", "Status", "Coordinator backup is available: %s" %_coordinator_backup)

    except IOError:
        Domoticz.Error("Error while Writing Coordinator backup %s" % _coordinator_backup)
