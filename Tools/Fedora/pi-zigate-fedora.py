#!/usr/bin/python3
"""
    This script of for Fedora based system. It has been tested on FC30 and FC31
    It requires to add iomem=relaxed to the Kernel sequence.
    for exemple: 
        Edit /etc/extlinux.conf and you should have somethink like that (see last parameters of append statement

        label Fedora (5.4.17-200.fc31.armv7hl) 31 (Thirty One)
	    kernel /vmlinuz-5.4.17-200.fc31.armv7hl
	    append ro root=UUID=2161061e-8612-4e18-a4e1-0e95aca6d2ff LANG=en_US.UTF-8 selinux=0 audit=0 rd.driver.blacklist=nouveau iomem=relaxed
	    fdtdir /dtb-5.4.17-200.fc31.armv7hl/
	    initrd /initramfs-5.4.17-200.fc31.armv7hl.img

"""
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
