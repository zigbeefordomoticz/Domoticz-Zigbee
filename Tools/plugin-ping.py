import argparse
import requests
import time
import sys

# PLUGIN_PING = "rest-z4d/1/health"
PLUGIN_PING = "rest-z4d/1/plugin-ping"

def check_zigbee_plugin_alive(ip, port, silent=False):
    """
    Check if the Zigbee for Domoticz plugin is alive via a REST API.

    Args:
        ip (str): The IP address of the server running the plugin.
        port (str): The port number of the Zigbee plugin.
        silent (bool): Whether to print status messages or not. Default is False.

    Returns:
        bool: True if the plugin is alive, False otherwise.
    """
    try:
        response = requests.get(f"http://{ip}:{port}/{PLUGIN_PING}", timeout=1)
        if response.status_code == 200:
            if not silent:
                print("The Zigbee for Domoticz plugin is alive!")
            return True
        else:
            if not silent:
                print("The Zigbee for Domoticz plugin is not alive.")
            return False
    except (requests.ConnectionError, requests.Timeout):
        if not silent:
            print("The Zigbee for Domoticz plugin is not alive.")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor if the Zigbee for Domoticz plugin is alive.")
    parser.add_argument("--ip", help="IP address of the server running the Zigbee plugin", default="127.0.0.1")
    parser.add_argument("--port", help="Port number of the Zigbee plugin", default="9440")
    parser.add_argument("--check_period", help="Time interval between checks in seconds", type=int, default=300)
    parser.add_argument("--silent", help="Run in silent mode (no output except errors)", action="store_true")
    args = parser.parse_args()

    ip = args.ip
    port = args.port
    check_period = args.check_period
    silent = args.silent

    while True:
        if not check_zigbee_plugin_alive(ip, port, silent):
            sys.exit(1)  # Exit with error code 1 if the plugin is not alive
        time.sleep(check_period)  # Sleep before next check
