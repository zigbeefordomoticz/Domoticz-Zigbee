#!/bin/bash

# export GIT_TRACE=1

exec 2>&1

echo "Starting Zigbee for Domoticz plugin Upgrade process."
echo "----------------------------------------------------"

#env
#echo $(id)
#echo $(who am i)

echo "(1) updating Zigbee for Domoticz plugin"
echo ""
echo "Setup submodule.recurse $(git config --add submodule.recurse true)"
echo ""
git pull --recurse-submodules
#git pull --recurse-submodules  && git submodule update --recursive
ret="$?"
if [ "$ret" != "0" ] ; then
    echo "ERROR while running command 'git pull --recurse-submodules'."
    echo "Git Status: $(git status)"
    exit -1
fi

echo "(2) update python3 modules if needed"
echo ""
sudo python3 -m pip --no-input install -r requirements.txt --ignore-requires-python
ret="$?"
if [ "$ret" != "0" ] ; then
    echo "ERROR while running command 'sudo python3 -m pip --ignore-requires-python --no-input install -r requirements.txt'."
    echo "Is sudo available for this user without password ?"
    exit -2
fi


echo "Plugin Upgrade process completed without errors."
exit 0
