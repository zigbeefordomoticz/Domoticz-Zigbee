#!/usr/bin/python3

import sys


if (len(sys.argv) != 2 ):
    print("Usage: %s run | flash")
    sys.exit(1)

try:
    import RPi.GPIO as GPIO

except:
    print("Fail to import RPi.GPIO")
    print("If you are on Fedora make sure to install the python3-RPi.GPIO module")
    print("dnf install python3-RPi.GPIO")
    sys.exit(1)

else:

    print("Set PiZigate Channels 11 and 17")
    channel_lst = [ 17, 27]
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup( channel_lst, GPIO.OUT)


    if sys.argv[1] == 'run':
        # Mode Run
        GPIO.output( 27, 1 )
        GPIO.output( 17, 0)
        GPIO.output( 17, 1)
        
        ei0 = GPIO.input( 17 )
        ei2 = GPIO.input( 27 )
        if ei0:
            print(" + GPIO(RUN) OK")
        else:
            print(" + GPIO(RUN) KO")
        if ei2:
            print(" + GPIO(FLASH) OK")
        else:
            print(" + GPIO(FLASH) KO")

    elif sys.argv[1] == 'flash':
        # Mode Flash
        GPIO.output( 27, 0 )
        GPIO.output( 17, 0)
        GPIO.output( 17, 1)
        #
        ei0 = GPIO.input( 17 )
        ei2 = GPIO.input( 27 )
        if ei0:
            print(" + GPIO(RUN) OK")
        else:
            print(" + GPIO(RUN) KO")
        if not ei2:
            print(" + GPIO(FLASH) OK")
        else:
            print(" + GPIO(FLASH) KO")
