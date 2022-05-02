#!/bin/bash



echo "Starting Zigbee for Domoticz plugin Upgrade process."
echo "----------------------------------------------------"

#env
#echo $(id)
#echo $(who am i)

echo "Checking pip3 and upgrading if needed"
sudo python3 -m pip install --upgrade pip
ret="$?"
if [ "$ret" != "0" ] ; then
    echo "Problem while running command 'sudo python3 -m pip install --upgrade pip.'"
    echo "Is sudo available for this user without password ?"
    echo "\n"
    exit -1
fi

echo "(1) update python3 modules if needed"
sudo python3 -m pip --no-input install -r requirements.txt
ret="$?"
if [ "$ret" != "0" ] ; then
    echo "Problem while running command 'sudo python3 -m pip --no-input install -r requirements.txt'."
    echo "Is sudo available for this user without password ?"
    exit -2
fi


echo "(2) updating Zigbee for Domoticz plugin"
echo "Git Status: $(git status)"

echo "Setup submodule.recurse $(git config --add submodule.recurse true)"
git pull --recurse-submodules
ret="$?"
if [ "$ret" != "0" ] ; then
    echo "Problem while running command 'git pull --recurse-submodules'."
    exit -3
fi


echo "Plugin Upgrade process completed without errors."
exit 0
