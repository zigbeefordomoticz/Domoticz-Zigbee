#!/bin/bash

if test -e /opt/domoticz/.initplugin; then
    echo "Environment already loaded."
else
    apt update
    apt install -y python3-dev
    python3 -m pip install --upgrade pip
    pip3 install wheel
    touch /opt/domoticz/.initplugin
fi


if test -d /opt/domoticz/userdata/plugins/Domoticz-Zigbee; then
    pip3  --ignore-requires-python -r /opt/domoticz/userdata/plugins/Domoticz-Zigbee/requirements.txt
else
    cd /opt/domoticz/userdata/plugins
    git clone https://github.com/zigbeefordomoticz/Domoticz-Zigbee.git
    cd Domoticz-Zigbee
    git config --add submodule.recurse true
    git submodule update --init --recursive
    pip3  --ignore-requires-python -r /opt/domoticz/userdata/plugins/Domoticz-Zigbee/requirements.txt
fi
