#!/bin/bash
if test -e /opt/domoticz/.initplugin; then
    echo "Environment already loaded."
    if test -d /opt/domoticz/userdata/plugins/Domoticz-Zigbee; then
        pip3 install -r /opt/domoticz/userdata/plugins/Domoticz-Zigbee/requirements.txt
    fi
else
    apt update
    apt install -y python3-dev
    python3 -m pip install --upgrade pip
    pip3 install wheel
    touch /opt/domoticz/.initplugin
    if test -d /opt/domoticz/userdata/plugins/Domoticz-Zigbee; then
        pip3 install -r /opt/domoticz/userdata/plugins/Domoticz-Zigbee/requirements.txt
    else
        cd /opt/domoticz/userdata/plugins
        git clone https://github.com/zigbeefordomoticz/Domoticz-Zigbee.git
        pip3 install -r /opt/domoticz/userdata/plugins/Domoticz-Zigbee/requirements.txt
    fi
fi
