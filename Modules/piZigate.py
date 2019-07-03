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

    Domoticz.Status("Switch PiZigate in RUN mode")
    if platform.dist()[0] in ( 'fedora' ):
        try:
            import RPi.GPIO as GPIO
        except RuntimeError:
            Domoticz.Log("Error importing RPi.GPIO!")
            return
        except:
            Domoticz.Log("Fail to import RPi.GPIO")
            Domoticz.Log("+ make sure to set the PiZigate in run mode")
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
            if ei0: Domoticz.Log(" + GPIO(RUN) OK")
            else: Domoticz.Log(" + GPIO(RUN) KO")
            if ei2: Domoticz.Log(" + GPIO(FLASH) OK")
            else: Domoticz.Log(" + GPIO(FLASH) KO")
        except RuntimeError:
            Domoticz.Log("Error importing RPi.GPIO!")
            return
        except:
            Domoticz.Log("Unable to set GPIO")
            Domoticz.Log("+ make sure to set the PiZigate in run mode")

    elif platform.dist()[0] in ( 'debian' ):
        from subprocess import run
        import os
    
        GPIO_CMD = "/usr/bin/gpio"
        if os.path.isfile( GPIO_CMD ):
            Domoticz.Log("+ Checkint GPIO PINs")
            run( GPIO_CMD + " read 0", shell=True, check=True)
            run( GPIO_CMD + " read 2", shell=True, check=True)
    
            run( GPIO_CMD + " mode 0 out", shell=True, check=True)
            run( GPIO_CMD + " mode 2 out", shell=True, check=True)
            run( GPIO_CMD + " write 2 1", shell=True, check=True)
            run( GPIO_CMD + " write 0 0", shell=True, check=True)
            run( GPIO_CMD + " write 0 1", shell=True, check=True)
    
            Domoticz.Log("+ Checkint GPIO PINs")
            run( GPIO_CMD + " read 0", shell=True, check=True)
            run( GPIO_CMD + " read 2", shell=True, check=True)
        else:
            Domoticz.Error("%s command missing. Make sure to install wiringPi package" %GPIO_CMD)
