#!/bin/bash

# export GIT_TRACE=1

exec 2>&1

echo "Starting Zigbee for Domoticz plugin Upgrade process."
echo "----------------------------------------------------"


if [ -z ${HOME} ]; then
    export HOME=$(pwd)
fi

env
echo " "

/usr/bin/id
echo " "

/usr/bin/whoami
echo " "

PIP_OPTIONS="--no-input install -r requirements.txt --ignore-requires-python --upgrade"

if command -v lsb_release &> /dev/null; then
    DISTRIB_ID=$(lsb_release -is)
    DISTRIB_RELEASE=$(lsb_release -rs)
    if [ "$DISTRIB_ID" = "Debian" ] && [ "$DISTRIB_RELEASE" = "12" ]; then
        PIP_OPTIONS="$PIP_OPTIONS --break-system-packages"
    fi
fi
echo "PIP Options: $PIP_OPTIONS"



echo "Current version  : $(cat .hidden/VERSION)"
echo "latest git commit: $(git log --pretty=oneline -1)"
echo ""

echo "(1) git config --global --add safe.directory"
git config  --global --add safe.directory $(pwd)
git config  --global --add safe.directory $(pwd)/external/zigpy
git config  --global --add safe.directory $(pwd)/external/zigpy-znp
git config  --global --add safe.directory $(pwd)/external/zigpy-zigate
git config  --global --add safe.directory $(pwd)/external/zigpy-deconz
git config  --global --add safe.directory $(pwd)/external/bellows

echo " "
echo "(2) updating Zigbee for Domoticz plugin"
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

echo " "
echo "(3) update python3 modules if needed"
echo ""
if [ "$(whoami)" == "root" ]; then
    # Si l'utilisateur est root
    python3 -m pip $PIP_OPTIONS
else
    # Si l'utilisateur n'est pas root, utilisez sudo
    sudo python3 -m pip $PIP_OPTIONS
fi
ret="$?"
if [ "$ret" != "0" ] ; then
    echo "ERROR while running command 'sudo python3 -m pip --no-input install -r requirements.txt --ignore-requires-python --upgrade'."
    echo "Is sudo available for this user without password ?"
    exit -2
fi

echo " "
echo "(4) git config --global --unset safe.directory"
git config --global --unset safe.directory $(pwd)/external/bellows
git config --global --unset safe.directory $(pwd)/external/zigpy-deconz
git config --global --unset safe.directory $(pwd)/external/zigpy-zigate
git config --global --unset safe.directory $(pwd)/external/zigpy-znp
git config --global --unset safe.directory $(pwd)/external/zigpy
git config --global --unset safe.directory $(pwd)

echo " "
echo "Plugin Upgrade process completed without errors."
exit 0
