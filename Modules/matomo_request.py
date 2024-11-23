import hashlib
import json
import os
import platform
import re
import sys
import time

import distro
import requests

# Matomo endpoint details
MATOMO_URL = "https://z4d.pipiche.net/matomo.php"
APIV = 1  # API Version
SITE_ID = 9   # 7 for Production
ACTION_NAME = "PluginInstanceInfos"

RONELABS_MODEL_INFO = "/etc/modelinfo"
DEVICE_TREE_CONFIGURATION = "/proc/device-tree/model"


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


def populate_custom_dimmensions(self):

    _custom_dimensions = { }

    # Domoticz version
    _domo = self.pluginParameters.get("DomoticzVersion")
    if _domo:
        _custom_dimensions[ "dimension1"] = clean_custom_dimension_value( _domo)

    # Coordinator Model
    _coordinator_model = self.pluginParameters.get("CoordinatorModel")
    if _coordinator_model:
        _custom_dimensions[ "dimension2"] = clean_custom_dimension_value( _coordinator_model)

    # Plugin Version
    _plugin_version = self.pluginParameters.get("PluginVersion")
    if _plugin_version:
        _custom_dimensions[ "dimension3"] = clean_custom_dimension_value( _plugin_version)

    # Coordinator Firmware Version
    _coordinator_version = self.pluginParameters.get("DisplayFirmwareVersion")
    if _coordinator_version:
        _custom_dimensions[ "dimension4"] = clean_custom_dimension_value( _coordinator_version)

    # Network Size
    total, router, end_devices = get_network_size_items(self.pluginParameters.get("NetworkSize"))
    if total:
        _custom_dimensions[ "dimension5"] = clean_custom_dimension_value(total)

    # Certified Db Version
    certified_db_version = self.pluginParameters.get("CertifiedDbVersion")
    if certified_db_version:
        _custom_dimensions[ "dimension6"] = clean_custom_dimension_value( certified_db_version)

    # OS Distribution
    _distribution = get_distribution(self)
    if _distribution:
        _custom_dimensions[ "dimension7"] = clean_custom_dimension_value( _distribution)

    # Platform Architecture
    _archi = get_architecture_model(self)
    if _archi:
        _custom_dimensions[ "dimension8"] = clean_custom_dimension_value( _archi)

    # Uptime
    _uptime = get_uptime_category(self.statistics._start)
    if _uptime:
        _custom_dimensions[ "dimension9"] = clean_custom_dimension_value( _uptime)

    # Ronelab model
    ronelab_model = get_ronelabs_model_custom_definition()
    if ronelab_model:
        _custom_dimensions[ "dimension10"] = clean_custom_dimension_value(ronelab_model)

    # Platform Id ( Pi Model )
    pi_model = get_raspberry_pi_model()
    if pi_model:
        _custom_dimensions[ "dimension11"] = clean_custom_dimension_value(pi_model)

    return _custom_dimensions


def matomo_plugin_analytics_infos(self):
    send_matomo_request(self, "Z4DPluginInfos", None, populate_custom_dimmensions(self))


def matomo_opt_out_action(self):
    """ Tracks a user's opt-out action in Matomo. """
    send_matomo_request( self, action_name="Opt-Out Action", event_category="Privacy", event_action="Opt-Out", event_name="User Opted Out" )


def matomo_opt_in_action(self):
    """ Tracks a user's opt-oin action in Matomo. """
    send_matomo_request( self, action_name="Opt-In Action", event_category="Privacy", event_action="Opt-In", event_name="User Opted In" )


def matomo_coordinator_initialisation(self):
    send_matomo_request( self, action_name="Coordinator Action", event_category="Coordinator", event_action="NewNetwork", event_name="Coordinator Formed new network" )


def matomo_plugin_shutdown(self):
    send_matomo_request( self, action_name="Plugin Action", event_category="Plugin", event_action="Shutdown", event_name="Plugin Shutdown" )


def matomo_plugin_restart(self):
    send_matomo_request( self, action_name="Plugin Action", event_category="Plugin", event_action="Restart", event_name="Plugin Restart" )


def matomo_plugin_started(self):
    send_matomo_request( self, action_name="Plugin Action", event_category="Plugin", event_action="Started", event_name="Plugin Started" )


def matomo_plugin_update(self, status):
    if status:
        send_matomo_request( self, action_name="Plugin Action", event_category="Plugin", event_action="SuccessfullUpdate", event_name="Plugin Update Successfully" )
    else:
        send_matomo_request( self, action_name="Plugin Action", event_category="Plugin", event_action="ErrorUpdate", event_name="Plugin Update with error" )


def send_matomo_request(self, action_name, custom_variable=None, custom_dimension=None, event_category=None, event_action=None, event_name=None):
    """
    Sends a tracking request to Matomo with optional custom variables, dimensions, and events.

    Args:
        action_name (str): Name of the action being tracked.
        custom_variable (dict, optional): Custom variables to include.
        custom_dimension (dict, optional): Custom dimensions to include.
        event_category (str, optional): Category for the event (e.g., "Privacy").
        event_action (str, optional): Action for the event (e.g., "Opt-Out").
        event_name (str, optional): Name of the event (e.g., "User Opted Out").
    """
    
    client_id = get_clientid(self)
    self.log.logging( "Matomo", "Debug", f"send_matomo_request - Clien_id {client_id}")
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

    # Add custom variables if provided
    if custom_variable:
        try:
            payload["cvar"] = json.dumps(custom_variable)
        except TypeError as e:
            self.log.logging("Matomo", "Error", f"Failed to serialize custom_variable: {e}")
            return

    # Add custom dimensions if provided
    if custom_dimension:
        payload.update(custom_dimension)

    # Add event-specific parameters if provided
    if event_category and event_action:
        payload["e_c"] = event_category  # Event category
        payload["e_a"] = event_action  # Event action
        if event_name:
            payload["e_n"] = event_name  # Event name (optional)

    self.log.logging( "Matomo", "Debug", f"send_matomo_request - payload {payload}")
    # Send the request
    response = fetch_data_with_timeout(self, MATOMO_URL, payload)


def fetch_data_with_timeout(self, url, params, connect_timeout=3, read_timeout=5):
    try:
        response = requests.get(url, params=params, timeout=(connect_timeout, read_timeout))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)

        if response.status_code == 200:
            self.log.logging( "Matomo", "Debug", f"send_matomo_request - Request sent successfully! {response}")

        else:
            self.log.logging( "Matomo", "Error", f"send_matomo_request - Failed to send request. Status code: {response.status_code}")
            self.log.logging( "Matomo", "Error", "send_matomo_request - Response content:", response.content)

    except requests.exceptions.Timeout:
        self.log.logging( "Matomo", "Error",f"Timeout after {connect_timeout}s connect / {read_timeout}s read.")

    except requests.exceptions.RequestException as e:
        self.log.logging( "Matomo", "Error",f"Request failed: {e}")


def get_architecture_model(self):
    """
    Retrieve the architecture model of the current Python runtime and system.

    Returns:
        str: A string containing architecture information.
    """
    try:
        return f"python: {platform.python_version()} arch: {platform.architecture()[0]} machine: {platform.machine()} processor:{platform.processor()}"
    except Exception as e:
        self.log.logging( "Matomo", "Error", f"get_architecture_model error {e}")
    return None


def get_ronelabs_model_custom_definition():
    if os.path.exists( RONELABS_MODEL_INFO ):
        with open(RONELABS_MODEL_INFO) as f:
            return f.readline().strip()
    return None


def classify_uptime(uptime_seconds):
    # Define thresholds in seconds for each category
    thresholds = [
        (1 * 86400, "1 day"),
        (2 * 86400, "2 days"),
        (3 * 86400, "3 days"),
        (4 * 86400, "4 days"),
        (5 * 86400, "5 days"),
        (7 * 86400, "1 week"),
        (14 * 86400, "2 weeks"),
        (21 * 86400, "3 weeks"),
        (28 * 86400, "4 weeks"),
        (30 * 86400, "1 month"),
        (60 * 86400, "2 months"),
        (90 * 86400, "3 months"),
        (120 * 86400, "4 months"),
        (150 * 86400, "5 months"),
        (180 * 86400, "6 months"),
    ]

    return next(
        (
            label
            for threshold, label in thresholds
            if uptime_seconds <= threshold
        ),
        "Beyond 6 months",
    )


def get_uptime_category(start_time):
    # Calculate uptime in seconds
    uptime_seconds = time.time() - start_time
    return classify_uptime(uptime_seconds)


def get_network_size_items(networksize):

    if not networksize:
        return None, None, None

    # Split the string by " | " to separate each category
    parts = networksize.split(" | ")

    # Extract individual values using string splitting
    try:
        networkTotalsize = int(parts[0].split(":")[1].strip())  # Extract the number after "Total: "
        networkRoutersize = int(parts[1].split(":")[1].strip())  # Extract the number after "Routers: "
        networkEndDevicesize = int(parts[2].split(":")[1].strip())  # Extract the number after "End Devices: "

    except IndexError:
        print("Error: The string format doesn't match the expected pattern.")
        return None, None, None

    return classify_nwk_size(networkTotalsize), classify_nwk_size(networkRoutersize), classify_nwk_size(networkEndDevicesize)


def classify_nwk_size(value):
    if value < 5:
        return "Micro"
    elif 5 <= value < 10:
        return "Small"
    elif 10 <= value < 25:
        return "Medium"
    elif 25 <= value < 50:
        return "Large"
    elif 50 <= value < 75:
        return "Very Large"
    else:
        return "Xtra Large"


def get_distribution(self):
    try:
        return f"{distro.name()} {distro.version()}"
    except Exception as e:
        self.log.logging( "Matomo", "Error", f"get_distribution error {e}")
    return None


def clean_custom_dimension_value(value: str) -> str:
    # Define a regex pattern for allowed characters: alphanumeric, spaces, underscores, hyphens, and periods
    allowed_pattern = re.compile(r'[^a-zA-Z0-9 _.-]')

    # Replace disallowed characters with a space
    cleaned_value = re.sub(allowed_pattern, ' ', value)

    # Collapse multiple spaces into a single space
    cleaned_value = re.sub(r'\s{2,}', ' ', cleaned_value)

    # Optionally, strip leading and trailing spaces
    return cleaned_value.strip()


def get_raspberry_pi_model():
    if os.path.exists( DEVICE_TREE_CONFIGURATION ):
        with open( DEVICE_TREE_CONFIGURATION , 'r') as f:
            return f.read().strip()
    return None