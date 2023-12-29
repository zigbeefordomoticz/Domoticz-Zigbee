
import pkg_resources
import sys
from importlib.metadata import version as import_version
from Modules.tools import how_many_devices
import Domoticz
from pathlib import Path

MODULES_VERSION = {
    "zigpy": "0.59.0",
    "zigpy_znp": "0.11.6",
    "zigpy_deconz": "0.21.1",
    "bellows": "0.36.8",
    }

def networksize_update(self):
    self.log.logging("Plugin", "Debug", "Devices size has changed , let's write ListOfDevices on disk")
    routers, enddevices = how_many_devices(self)
    self.pluginParameters["NetworkSize"] = "Total: %s | Routers: %s | End Devices: %s" %(
        routers + enddevices, routers, enddevices)


def decodeConnection(connection):

    decoded = {}
    for i in connection.strip().split(","):
        label, value = i.split(": ")
        label = label.strip().strip("'")
        value = value.strip().strip("'")
        decoded[label] = value
    return decoded


def check_firmware_level(self):
    # Check Firmware version
    if int(self.FirmwareVersion.lower(),16) == 0x2100:
        self.log.logging("Plugin", "Status", "Firmware for Pluzzy devices")
        self.PluzzyFirmware = True
        return True

    if int(self.FirmwareVersion.lower(),16) < 0x031d:
        self.log.logging("Plugin", "Error", "Firmware level not supported, please update ZiGate firmware")
        return False

    if int(self.FirmwareVersion.lower(),16) >= 0x031e:
        self.pluginconf.pluginConf["forceAckOnZCL"] = False
        return True

    return False


def update_DB_device_status_to_reinit( self ):

    # This function is called because the ZiGate will be reset, and so it is expected that all devices will be reseted and repaired

    for x in self.ListOfDevices:
        if 'Status' in self.ListOfDevices[ x ] and self.ListOfDevices[ x ]['Status'] == 'inDB':
            self.ListOfDevices[ x ]['Status'] = 'erasePDM'


def get_domoticz_version( self, domoticz_version  ):
    lst_version = domoticz_version.split(" ")
    if len(lst_version) == 1:
        return _old_fashon_domoticz(self, lst_version, domoticz_version)
    
    if len(lst_version) != 3:
        Domoticz.Error( "Domoticz version %s unknown not supported, please upgrade to a more recent"% (
            domoticz_version) )
        return _domoticz_not_compatible(self)

    major, minor = lst_version[0].split(".")
    build = lst_version[2].strip(")")
    self.DomoticzBuild = int(build)
    _update_domoticz_firmware_data(self, major, minor)
    return True


def _old_fashon_domoticz(self, lst_version, domoticz_version):
    # No Build
    major, minor = lst_version[0].split(".")
    self.DomoticzBuild = 0
    _update_domoticz_firmware_data(self, major, minor)
    
    if self.DomoticzMajor >= 2020:
        return True
    
    # Old fashon Versioning
    Domoticz.Error( "Domoticz version %s %s %s not supported, please upgrade to a more recent" % (
        domoticz_version, major, minor) )
    return _domoticz_not_compatible(self)


def _update_domoticz_firmware_data(self, major, minor):
    self.DomoticzMajor = int(major)
    self.DomoticzMinor = int(minor)
    self.VersionNewFashion = True


def _domoticz_not_compatible(self):
    self.VersionNewFashion = False
    self.onStop()
    return False


def check_python_modules_version( self ):
    

    flag = True

    for x in MODULES_VERSION:
        if import_version( x ) != MODULES_VERSION[ x]:
            self.log.logging("Plugin", "Error", "The python module %s version %s loaded is not compatible as we are expecting this level %s" %(
                x, import_version( x ), MODULES_VERSION[ x] ))
            flag = False
            
    return flag


def check_requirements( home_folder):

    requirements_file = Path( home_folder + "requirements.txt" )
    Domoticz.Status("Checking Python modules %s" %requirements_file)

    with open(requirements_file, 'r') as file:
        requirements_list = file.readlines()

    for req_str in list(requirements_list):
        try:
            pkg_resources.require(req_str.strip())

        except pkg_resources.DistributionNotFound:
            Domoticz.Error("Looks like %s python module is not installed. Make sure to install the required python3 module" %(req_str.strip()))
            Domoticz.Error("Use the command:")
            Domoticz.Error("sudo python3 -m pip install -r requirements.txt --upgrade")
            return True

        except pkg_resources.VersionConflict:
            Domoticz.Error("Looks like %s python module is conflicting. Make sure to install the required python3 module" %(req_str.strip()))
            Domoticz.Error("Use the command:")
            Domoticz.Error("sudo python3 -m pip install -r requirements.txt --upgrade")
            return True

        except Exception as e:
            Domoticz.Error(f"An unexpected error occurred: {e}")

    return False


def list_all_modules_loaded(self):
    # Get a list of installed packages and their versions
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}

    # Get a list of modules imported by the main script
    main_modules = set(sys.modules.keys())

    # Combine the lists
    all_modules = set(installed_packages.keys()) | main_modules

    # Print the list of modules and their versions
    self.log.logging("Plugin", "Log", "=============================")
    for module_name in sorted(all_modules):
        version = installed_packages.get(module_name, "Not installed")
        self.log.logging("Plugin", "Log", f"{module_name}: {version}")
    self.log.logging("Plugin", "Log", "=============================")
