#!/bin/bash

JENNICMODULE_DIR="./JennicModuleProgrammer/"
if [ -d $JENNICMODUL_DIR ]; then
	cd $JENNICMODULE_DIR/Build
	make
fi
