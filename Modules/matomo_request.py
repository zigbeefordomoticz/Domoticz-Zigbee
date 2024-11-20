import hashlib
import json
import platform
import sys
import time

import requests

# Matomo endpoint and authentication details
MATOMO_URL = "https://z4d.pipiche.net/matomo.php"
APIV = 1
SITE_ID = 8  # 8 for Testing , 7 for Production
ACTION_NAME = "PluginInstanceInfos"
RONELABS_MODEL_INFO = "/etc/modelinfo"

# Custom Variables (up to 5 allowed per request)


def get_clientid(self):
    """ 
    Reterieve the MacAddress that will be used a Client Id
    
    Ensure compliance with privacy laws like GDPR or CCPA when using MAC addresses or other personal identifiers. 
    anonymize or hash the MAC address before sending it to Matomo.
    """
    mac_address = self.ListOfDevices.get('0000', {}).get('IEEE', None)
    if mac_address:
        return hashlib.sha256(mac_address.encode()).hexdigest()
    
    return None


def populate_custom_variables_pack1(self):

    return {
        "1" : [ "DomoticzVersion", self.pluginParameters.get("DomoticzVersion") ],
        "2" : [ "CoordinatorModel", self.pluginParameters.get("CoordinatorModel") ],
        "3" : [ "PluginVersion", self.pluginParameters.get("PluginVersion") ],
        "4" : [ "CoordinatorFirmwareversion", self.pluginParameters.get("DisplayFirmwareVersion") ],
        "5" : [ "NetworkSize", self.pluginParameters.get("NetworkSize") ],
    }


def populate_custom_variables_pack2(self):
    return {
        "6" : [ "NetworkDevices", self.pluginParameters.get("NetworkDevices") ],
        "7" : [ "CertifiedDbVersion", self.pluginParameters.get("CertifiedDbVersion") ],
        "8" : [ "PlatformDistribution", str( get_os_info()) ],
        "9" : [ "ArchitectureInformation", str( get_architecture_model() )],
        "10": [ "Uptime", str( time.time() - self.statistics._start) ],
    }


def populate_custom_dimmensions(self):
    
    _custom_dimmensions = {}
    _ronlabs_model = get_ronelabs_model_custom_definition()
    if _ronlabs_model:
        _custom_dimmensions[ _ronlabs_model[0] ] = _ronlabs_model[1]

    return _custom_dimmensions


def sending_plugin_analytics_infos(self):
    
    send_matomo_request(self, (ACTION_NAME + "_1"), None, populate_custom_dimmensions(self))
    send_matomo_request(self, (ACTION_NAME + "_2"), populate_custom_variables_pack1(self), None)
    send_matomo_request(self, (ACTION_NAME + "_3"), populate_custom_variables_pack2(self), None)


def send_matomo_request(self, action_name, custom_variable, custom_dimension):
    
    client_id = get_clientid(self)
    if client_id is None:
        self.log.logging( "Matomo", "Error", "Noting reported as MacAddress is None!")
        return

    # Construct the payload
    payload = {
        "idsite": SITE_ID,
        "rec": 1,
        "apiv": APIV,
        "action_name": action_name,
        "uid": client_id,
    }
    
    if custom_variable:
        payload[ "cvar"] = json.dumps(custom_variable)
        
    # Add Custom Dimensions to the request
    if custom_dimension:
        payload.update(custom_dimension)

    try:
        # Send the request to Matomo
        self.log.logging( "Matomo", "Debug", f"send_matomo_request - Request {MATOMO_URL} {payload}")
        response = requests.get(MATOMO_URL, params=payload)

        # Handle the response
        if response.status_code == 200:
            self.log.logging( "Matomo", "Debug", "send_matomo_request - Request sent successfully!")

        else:
            self.log.logging( "Matomo", "Error", f"send_matomo_request - Failed to send request. Status code: {response.status_code}")
            self.log.logging( "Matomo", "Error", "send_matomo_request - Response content:", response.content)

    except Exception as e:
        self.log.logging( "Matomo","Error", f"send_matomo_request - An error occurred: {e}")



def get_os_info():
    os_name = platform.system()
    if os_name == "Linux":
        try:
            with open("/etc/os-release") as f:
                lines = f.readlines()
                os_info = {line.split('=')[0]: line.split('=')[1].strip().strip('"') for line in lines if '=' in line}
            return os_info.get("NAME", "Unknown"), os_info.get("VERSION", "Unknown")

        except Exception as e:
            return "Linux", "Unknown"

    elif os_name == "Windows":
        return "Windows", platform.version()

    elif os_name == "Darwin":
        return "macOS", platform.mac_ver()[0]

    else:
        return os_name, "Unknown"
    
    

def get_architecture_model():
    """
    Retrieve the architecture model of the current Python runtime and system.

    Returns:
        dict: A dictionary containing architecture information.
    """
    return {
        "python_version": platform.python_version(),
        "architecture": platform.architecture()[0],
        "platform": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_architecture": "64-bit" if sys.maxsize > 2**32 else "32-bit",
    }



def get_ronelabs_model_custom_definition():

    RONELABS_DIMENSION = {
        "Ronelabs-GW-G5Lite": "dimension11",
        "Ronelabs-GW-G5Mini": "dimension12"
    }
    with open(RONELABS_MODEL_INFO) as f:
        ronelabs_model = f.readline().strip()
    
    if ronelabs_model in RONELABS_DIMENSION:
        return RONELABS_DIMENSION[ ronelabs_model ], ronelabs_model
    
    return None, None