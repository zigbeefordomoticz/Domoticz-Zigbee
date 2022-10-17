#!/bin/bash



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
ret="$?"
if [ "$ret" != "0" ] ; then
    echo "Problem while running command 'git pull --recurse-submodules'."
    echo "Git Status: $(git status)"
    exit -1
fi

echo "(2) update python3 modules if needed"
echo ""
sudo python3 -m pip --no-input install -r requirements.txt
ret="$?"
if [ "$ret" != "0" ] ; then
    echo "Problem while running command 'sudo python3 -m pip --no-input install -r requirements.txt'."
    echo "Is sudo available for this user without password ?"
    exit -2
fi


echo "Plugin Upgrade process completed without errors."
exit 0
