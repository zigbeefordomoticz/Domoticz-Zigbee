#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
    Module: piZigate.py

    Description: PiZigate specifics settings

"""
import os
import platform
import sys

import distro


def linux_distribution():
    try:
        return [distro.id(), distro.version(), distro.codename()]
    except Exception as e:
        return "N/A"


def switchPiZigate_mode(self, mode="run"):

    if mode != "run":
        return

    try:
        self.log.logging("PiZigate", "Status", "Python version: %s dist info: %s linux_distribution: %s system: %s machine: %s platform: %s uname: %s version: %s mac_ver: %s " % (
            sys.version.split("\n"), str(distro.info()), linux_distribution(), platform.system(), platform.machine(), platform.platform(), platform.uname(), platform.version(), platform.mac_ver(), ) )

    except Exception as e:
        self.log.logging("PiZigate", "Error", "switchPiZigate_mode - unable to find distribution: Assuming debian, Error: %s" % e)
        runmode_with_gpiomodule(self)
        return

    if distro.id() in ("fedora"):
        runmode_with_gpiomodule(self)

    if distro.id() in ("debian", "raspbian"):
        runmode_with_gpiocommand(self)


def runmode_with_gpiomodule(self):

    try:
        import RPi.GPIO as GPIO

    except RuntimeError:
        self.log.logging("PiZigate", "Error","Error importing python3 module RPi.GPIO!, trying to recover with GPIO commands from wiringPi")
        runmode_with_gpiocommand()
        return
    except Exception as e:
        self.log.logging("PiZigate", "Error","Fail to import RPi.GPIO")
        self.log.logging("PiZigate", "Error","+ make sure to set the PiZigate in run mode")
        runmode_with_gpiocommand()
        return

    self.log.logging("PiZigate", "Debug", "Set PiZigate Channels 11 and 17")
    channel_lst = [17, 27]
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(channel_lst, GPIO.OUT)
        # Mode Run
        ei0 = GPIO.input(17)
        ei2 = GPIO.input(27)
        GPIO.output(27, 1)
        GPIO.output(17, 0)
        GPIO.output(17, 1)

        ei0 = GPIO.input(17)
        ei2 = GPIO.input(27)
        self.log.logging("PiZigate", "Status", "Switch PiZigate in RUN mode")
        if ei0:
            self.log.logging("PiZigate", "Log", " + GPIO(RUN) OK")
        else:
            self.log.logging("PiZigate", "Log"," + GPIO(RUN) KO")
        if ei2:
            self.log.logging("PiZigate", "Log"," + GPIO(FLASH) OK")
        else:
            self.log.logging("PiZigate", "Log"," + GPIO(FLASH) KO")
    except RuntimeError:
        self.log.logging("PiZigate", "Error", "Error executing GPIO API, let's try with GPIO commands!")
        runmode_with_gpiocommand(self)
        return
    except Exception as e:
        self.log.logging("PiZigate", "Error", "Unable to set GPIO")
        self.log.logging("PiZigate", "Error", "+ make sure to set the PiZigate in run mode")


def runmode_with_gpiocommand(self):

    try:
        from subprocess import run  # nosec
    except Exception as e:
        self.log.logging("PiZigate", "Error","Error while importing run from python module subprocess, fall back to os module")
        runmode_with_osgpiocommand(self)
        return

    self.log.logging("PiZigate", "Log", "runmode_with_gpiocommand")
    GPIO_CMD = "/usr/bin/gpio"
    if os.path.isfile(GPIO_CMD):
        self.log.logging("PiZigate", "Log", "+ Checkint GPIO PINs")
        run(GPIO_CMD + " read 0", shell=True, check=True)  # nosec
        run(GPIO_CMD + " read 2", shell=True, check=True)  # nosec

        run(GPIO_CMD + " mode 0 out", shell=True, check=True)  # nosec
        run(GPIO_CMD + " mode 2 out", shell=True, check=True)  # nosec
        run(GPIO_CMD + " write 2 1", shell=True, check=True)  # nosec
        run(GPIO_CMD + " write 0 0", shell=True, check=True)  # nosec
        run(GPIO_CMD + " write 0 1", shell=True, check=True)  # nosec

        self.log.logging("PiZigate", "Log", "+ Checkint GPIO PINs")
        run(GPIO_CMD + " read 0", shell=True, check=True)  # nosec
        run(GPIO_CMD + " read 2", shell=True, check=True)  # nosec
    else:
        self.log.logging("PiZigate", "Error", "%s command missing. Make sure to install wiringPi package" % GPIO_CMD)


def runmode_with_osgpiocommand(self):

    self.log.logging("PiZigate", "Log","runmode_with_osgpiocommand")
    GPIO_CMD = "/usr/bin/gpio"
    if os.path.isfile(GPIO_CMD):
        self.log.logging("PiZigate", "Log","+ Checkint GPIO PINs")
        os.system(GPIO_CMD + " read 0")  # nosec
        os.system(GPIO_CMD + " read 2")  # nosec

        os.system(GPIO_CMD + " mode 0 out")  # nosec
        os.system(GPIO_CMD + " mode 2 out")  # nosec
        os.system(GPIO_CMD + " write 2 1")  # nosec
        os.system(GPIO_CMD + " write 0 0")  # nosec
        os.system(GPIO_CMD + " write 0 1")  # nosec

        self.log.logging("PiZigate", "Log", "+ Checkint GPIO PINs")
        os.system(GPIO_CMD + " read 0")  # nosec
        os.system(GPIO_CMD + " read 2")  # nosec
    else:
        self.log.logging("PiZigate", "Error", "%s command missing. Make sure to install wiringPi package" % GPIO_CMD)
