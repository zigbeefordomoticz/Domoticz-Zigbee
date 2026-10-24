#!/bin/bash

# customstart.sh
#
# Purpose:
# Initialise a Domoticz Docker container (official domoticz/domoticz image) for the
# Zigbee for Domoticz plugin. Copy this file to /opt/domoticz/userdata/customstart.sh
# (the root of the userdata volume). It:
# 1. Updates the package list.
# 2. Installs convenience packages (iputils-ping, vim and openssh-client).
# 3. Installs the Python modules required by the Zigbee for Domoticz plugin.
#
# How the official image runs it:
# docker-entrypoint.sh SOURCES this file, but only while /opt/domoticz/FIRSTRUN does not
# exist, and creates FIRSTRUN itself once this file has returned. FIRSTRUN lives in the
# container, not in the userdata volume, so this file runs once per container: again after
# an image update or a re-creation (Synology Container Manager "Reset", a project rebuild),
# not on a plain stop/start.
#
# Rules that follow from being sourced:
# - Never call "exit": it would end docker-entrypoint.sh itself and stop the container.
# - Never create FIRSTRUN here: if the container is stopped while the modules are being
#   installed, FIRSTRUN must still be missing so that the next start installs them again.
#
# Error handling:
# The network-dependent steps are retried, as the network may not be up yet when the host
# has just booted. If the Python modules still cannot be installed, a message tells how to
# install them by hand and Domoticz starts anyway.

z4d_customstart_retry() {
    # z4d_customstart_retry <attempts> <delay in seconds> <command...>
    local attempts="$1" delay="$2" i
    shift 2
    for (( i = 1; i <= attempts; i++ )); do
        "$@" && return 0
        if (( i < attempts )); then
            echo "Attempt ${i}/${attempts} failed, retrying in ${delay}s: $*"
            sleep "$delay"
        fi
    done
    return 1
}

z4d_customstart() {
    local plugin_dir=/opt/domoticz/userdata/plugins/Domoticz-Zigbee

    echo 'updating packages'
    z4d_customstart_retry 3 20 apt-get -qq update || echo 'Warning: failed to update packages, continuing'

    echo 'installing iputils-ping, vim and openssh-client'
    apt-get -y install iputils-ping vim openssh-client || echo 'Warning: failed to install iputils-ping, vim or openssh-client, continuing'

    if [ ! -f "$plugin_dir/requirements.txt" ]; then
        echo "Zigbee for Domoticz plugin not found in $plugin_dir, skipping its Python modules"
        return 0
    fi

    echo 'Install the necessary python3 modules for Zigbee for Domoticz plugin'
    if ! cd "$plugin_dir"; then
        echo "Error: cannot change directory to $plugin_dir"
        return 1
    fi
    # Run through bash: the execute bit is lost when the plugin is copied over SMB or File Station.
    if ! z4d_customstart_retry 3 30 bash Tools/plugin-auto-upgrade.sh; then
        echo '************************************************************************'
        echo 'Error: the Python modules of the Zigbee for Domoticz plugin are NOT installed.'
        echo 'Domoticz starts anyway, but the plugin will not. Once the cause is fixed, either:'
        echo '  - re-create the container (this script runs again), or'
        echo "  - run: docker exec -it <container> bash -c 'cd $plugin_dir && bash Tools/plugin-auto-upgrade.sh'"
        echo '    then restart the container.'
        echo '************************************************************************'
        return 1
    fi
    return 0
}

z4d_customstart
unset -f z4d_customstart z4d_customstart_retry
cd /opt/domoticz || true
