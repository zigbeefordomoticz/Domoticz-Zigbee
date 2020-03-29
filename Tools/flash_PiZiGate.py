#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import usb
import getopt

JENNIC_MODULE_PROGRAMMER = "./JennicModuleProgrammer/Build/JennicModuleProgrammer"

def usage():
	print("\033[1;31;40m")
	print("**** Error ****")
	print("\033[0;37;40m")
	print("Usage : sudo python3 flash_PiZiGate -s[SerialPort] -b[bauds] -f[firmware.bin]\n")
	
	
def main():
    """Main program"""
    
    speed="115200"
    firmware=""
	

    if not os.path.isfile( JENNIC_MODULE_PROGRAMMER ):
        print("JennicModuleProgrammer not available.")
        print("Make sure you are on the Tool directory, and you have build JennicModuleProgrammer with build-Jennic.sh script")
        sys.exit(2)

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:b:f:", ["help", "serial=","baud=","firmware="])
    except getopt.GetoptError as err:
        # print help information and exit:
        usage() # will print something like "option -a not recognized"
        sys.exit(2)

    if len(sys.argv) != 7:
        usage()
        sys.exit(2)
	
	
    for o, a in opts:
        if o == "-b":
            speed = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-s", "--serial"):
            serial = a
        elif o in ("-f", "--firmware"):
            firmware = a
        else:
            assert False, "unhandled option"
    
    print("\033[1;33;40m")
    print("**** Mode Flash ****")
    print("\033[0;37;40m")	

    command = "gpio mode 0 out; gpio mode 2 out; gpio write 2 0 ; gpio write 0 0 gpio write 0 1"
    os.system(command)


    command = JENNIC_MODULE_PROGRAMMER + " -V 6 -P " + speed + " -f " + firmware + " -s " + serial
    print(command)
    os.system(command)
    
    print("\033[1;33;40m")
    print("**** Mode RUN ****")
    print("\033[0;37;40m")
	
    command = " gpio mode 0 out; gpio mode 2 out; gpio write 2 1 ; gpio write 0 0; gpio write 0 1"
    os.system(command)
	
    print("\033[1;32;40m")
    print("**** Terminé ****")
    print("\033[0;37;40m")

main()
