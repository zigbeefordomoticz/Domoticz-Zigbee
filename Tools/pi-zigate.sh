#!/bin/bash

if [ -z $1 ]
then
	echo "Usage: pi-zigate.sh flash | run " 
	exit 0
fi
echo "Verif GPIO ..."
io0=$(gpio read 0)
io2=$(gpio read 2)

if [ "$io0" -eq "1" ]
then
	echo "+ GPIO 0 (RESET) $io0 --> OK"
else
	echo "+ GPIO 0 (RESET) $io0 --> KO"
fi
if [ "$io2" -eq "1" ]
then
	echo "+ GPIO 2 (FLASH) $io2 --> OK"
else
	echo "+ GPIO 2 (FLASH) $io2 --> KO"
fi

if [ $1 == "flash" ]
then
	echo "Switching PI-Zigate to Flash mode"

	gpio mode 0 out
	gpio mode 2 out
	gpio write 2 0 
	gpio write 0 0
	gpio write 0 1
fi

if [ $1 == "run" ]
then
	echo "Switching PI-Zigate to Run mode"
	gpio mode 0 out
	gpio mode 2 out
	gpio write 2 1 
	gpio write 0 0
	gpio write 0 1
fi
