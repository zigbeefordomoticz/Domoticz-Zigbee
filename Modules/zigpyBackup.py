
import Domoticz
import os.path
import json
from pathlib import Path
import Modules.tools

def handle_zigpy_backup(self, backup):

    if not backup:
        self.log.logging("TransportZigpy", "Log","Backup is incomplete, it is not possible to restore")
        return

    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
    _coordinator_backup = _pluginData /  ("Coordinator-%02d" %self.HardwareID + ".backup")
    self.log.logging("TransportZigpy", "Debug", "Backups: %s" %backup)

    if os.path.exists(_coordinator_backup):
        Modules.tools.helper_versionFile(_coordinator_backup, self.pluginconf.pluginConf["numDeviceListVersion"])

    try:
        with open(_coordinator_backup, "wt") as file:
            file.write(json.dumps((backup.as_dict())))
            self.log.logging("TransportZigpy", "Status", "Coordinator backup is available: %s" %_coordinator_backup)

    except IOError:
        Domoticz.Error("Error while Writing Coordinator backup %s" % _coordinator_backup)


def handle_zigpy_retreive_last_backup( self ):
    
    # Return the last backup
    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
    _coordinator_backup = _pluginData /  ("Coordinator-%02d" %self.HardwareID + ".backup")
    if not os.path.exists(_coordinator_backup):
        return None

    with open(_coordinator_backup, "r") as _coordinator:
        self.log.logging("TransportZigpy", "Debug", "Open : %s" % _coordinator_backup)
        try:
            return json.load(_coordinator)
        except json.JSONDecodeError:
            return None
        except Exception:
            return None
    return None