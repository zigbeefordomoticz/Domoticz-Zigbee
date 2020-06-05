#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: piZigate.py

    Description: PiZigate specifics settings

"""
import platform
import sys
import os
import Domoticz

def linux_distribution():
  try:
    return platform.linux_distribution()
  except:
    return "N/A"

def switchPiZigate_mode( self, mode='run' ):

    if mode != 'run':
        return
    Domoticz.Status("""Python version: %s dist: %s linux_distribution: %s system: %s machine: %s platform: %s uname: %s version: %s mac_ver: %s """ \
        % ( sys.version.split('\n'), str(platform.dist()), linux_distribution(), platform.system(), platform.machine(),
            platform.platform(), platform.uname(), platform.version(), platform.mac_ver(),))

    if platform.dist()[0] in ( 'fedora' ):
        runmode_with_gpiomodule()
    elif platform.dist()[0] in ( 'debian' ):
        runmode_with_gpiocommand()


def runmode_with_gpiomodule( ):

        try:
            import RPi.GPIO as GPIO

        except RuntimeError:
            Domoticz.Error("Error importing python3 module RPi.GPIO!, trying to recover with GPIO commands from wiringPi")
            runmode_with_gpiocommand()
            return
        except:
            Domoticz.Error("Fail to import RPi.GPIO")
            Domoticz.Error("+ make sure to set the PiZigate in run mode")
            runmode_with_gpiocommand()
            return

        Domoticz.Log("Set PiZigate Channels 11 and 17")
        channel_lst = [ 17, 27]
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup( channel_lst, GPIO.OUT)
            # Mode Run
            ei0 = GPIO.input( 17 )
            ei2 = GPIO.input( 27 )
            GPIO.output( 27, 1 )
            GPIO.output( 17, 0)
            GPIO.output( 17, 1)
             
            ei0 = GPIO.input( 17 )
            ei2 = GPIO.input( 27 )
            Domoticz.Status("Switch PiZigate in RUN mode")
            if ei0: 
                Domoticz.Log(" + GPIO(RUN) OK")
            else: 
                Domoticz.Log(" + GPIO(RUN) KO")
            if ei2: 
                Domoticz.Log(" + GPIO(FLASH) OK")
            else: 
                Domoticz.Log(" + GPIO(FLASH) KO")
        except RuntimeError:
            Domoticz.Error("Error executing GPIO API, let's try with GPIO commands!")
            runmode_with_gpiocommand()
            return
        except:
            Domoticz.Error("Unable to set GPIO")
            Domoticz.Error("+ make sure to set the PiZigate in run mode")


def runmode_with_gpiocommand():

        try:
            from subprocess import run
        except:
            Domoticz.Error("Error while importing run from python module subprocess, fall back to os module")
            runmode_with_osgpiocommand()
            return

        Domoticz.Log("runmode_with_gpiocommand")
        GPIO_CMD = "/usr/bin/gpio"
        if os.path.isfile( GPIO_CMD ):
            Domoticz.Log("+ Checkint GPIO PINs")
            run( GPIO_CMD + " read 0", shell=True, check=True) # nose
            run( GPIO_CMD + " read 2", shell=True, check=True) # nose
    
            run( GPIO_CMD + " mode 0 out", shell=True, check=True) # nose
            run( GPIO_CMD + " mode 2 out", shell=True, check=True) # nose
            run( GPIO_CMD + " write 2 1", shell=True, check=True) # nose
            run( GPIO_CMD + " write 0 0", shell=True, check=True) # nose
            run( GPIO_CMD + " write 0 1", shell=True, check=True) # nose
    
            Domoticz.Log("+ Checkint GPIO PINs")
            run( GPIO_CMD + " read 0", shell=True, check=True) # nose
            run( GPIO_CMD + " read 2", shell=True, check=True) # nose
        else:
            Domoticz.Error("%s command missing. Make sure to install wiringPi package" %GPIO_CMD)

def runmode_with_osgpiocommand():

        Domoticz.Log("runmode_with_osgpiocommand")
        GPIO_CMD = "/usr/bin/gpio"
        if os.path.isfile( GPIO_CMD ):
            Domoticz.Log("+ Checkint GPIO PINs")
            os.system( GPIO_CMD + " read 0") # nosec
            os.system( GPIO_CMD + " read 2") # nosec
    
            os.system( GPIO_CMD + " mode 0 out") # nosec
            os.system( GPIO_CMD + " mode 2 out") # nosec
            os.system( GPIO_CMD + " write 2 1") # nosec
            os.system( GPIO_CMD + " write 0 0") # nosec
            os.system( GPIO_CMD + " write 0 1") # nosec
    
            Domoticz.Log("+ Checkint GPIO PINs")
            os.system( GPIO_CMD + " read 0") # nosec
            os.system( GPIO_CMD + " read 2") # nosec
        else:
            Domoticz.Error("%s command missing. Make sure to install wiringPi package" %GPIO_CMD)

