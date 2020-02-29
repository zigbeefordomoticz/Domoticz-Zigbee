#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Stefan Agner

import os
import sys
import time
import usb
import getopt


BITMODE_CBUS = 0x20

SIO_SET_BITMODE_REQUEST = 0x0b

# FTDIs CBUS bitmode expect the following value:
# CBUS Bits
# 3210 3210
#      |------ Output Control 0->LO, 1->HI
# |----------- Input/Output   0->Input, 1->Output

# PyUSB control endpoint communication, see also:
# https://github.com/pyusb/pyusb/blob/master/docs/tutorial.rst

def ftdi_set_bitmode(dev, bitmask):
    bmRequestType = usb.util.build_request_type(usb.util.CTRL_OUT,
                                                usb.util.CTRL_TYPE_VENDOR,
                                                usb.util.CTRL_RECIPIENT_DEVICE)

    wValue = bitmask | (BITMODE_CBUS << BITMODE_CBUS)
    dev.ctrl_transfer(bmRequestType, SIO_SET_BITMODE_REQUEST, wValue)

def usage():
	print("\033[1;31;40m")
	print("**** Error ****")
	print("\033[0;37;40m")
	print("Usage : sudo python3 flash_ZiGate-DIN -s[SerialPort] -b[bauds] -f[firmware.bin]\n")
	
	
def main():
    """Main program"""
    dev = usb.core.find(custom_match = \
            lambda d: \
                d.idVendor==0x0403 and
                d.idProduct==0x6001 )
    
    speed="115200"
    serial="/dev/ttyUSB0"
    firmware=""
	
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
	# Set CBUS2/3 back to tristate
    ftdi_set_bitmode(dev, 0x00)
	
    time.sleep(1)	
	
	# Set CBUS2/3 high...
    ftdi_set_bitmode(dev, 0xCC)

    time.sleep(1)

    # Set CBUS2/3 low...
    ftdi_set_bitmode(dev, 0xC0)
    time.sleep(1)
    ftdi_set_bitmode(dev, 0xC4)
    time.sleep(1)	
	
	# Set CBUS2/3 back to tristate
    ftdi_set_bitmode(dev, 0xCC)

    command = "./JennicModuleProgrammer -V 6 -P "+speed+" -f "+firmware+" -s "+serial
    os.system(command)
    
    print("\033[1;33;40m")
    print("**** Mode Production ****")
    print("\033[0;37;40m")
	
    ftdi_set_bitmode(dev, 0xC8)
    time.sleep(1)
    ftdi_set_bitmode(dev, 0xCC)
	
    print("\033[1;32;40m")
    print("**** Terminé ****")
    print("\033[0;37;40m")

main()
