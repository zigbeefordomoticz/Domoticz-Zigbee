#!/usr/bin/python3


# Modified script from https://github.com/tjikkun/zigate-flasher

import argparse
import atexit
import functools
import itertools
import logging
import struct
import sys
import time
from operator import xor

import serial
from serial.tools.list_ports import comports

import usb

import RPi.GPIO as GPIO

logger = logging.getLogger(__name__)
_responses = {}

ZIGATE_CHIP_ID = 0x10408686
ZIGATE_BINARY_VERSION = bytes.fromhex('07030008')
ZIGATE_FLASH_START = 0x00000000
ZIGATE_FLASH_END = 0x00040000

# For DIN-ZiGate
# cf. https://github.com/fairecasoimeme/ZiGate-DIN/blob/master/tools/flash_ZiGate-DIN.py
BITMODE_CBUS = 0x20
SIO_SET_BITMODE_REQUEST = 0x0b
class Command:

    def __init__(self, type_, fmt=None, raw=False):
        assert not (raw and fmt), 'Raw commands cannot use built-in struct formatting'

        self.type = type_
        self.raw = raw
        if fmt:
            self.struct = struct.Struct(fmt)
        else:
            self.struct = None

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            rv = func(*args, **kwargs)

            if self.struct:
                try:
                    data = self.struct.pack(*rv)
                except TypeError:
                    data = self.struct.pack(rv)
            elif self.raw:
                data = rv
            else:
                data = bytearray()

            return prepare(self.type, data)

        return wrapper


class Response:

    def __init__(self, type_, data, chksum):
        self.type = type_
        self.data = data[1:]
        self.chksum = chksum
        self.status = data[0]

    @property
    def ok(self):
        return self.status == 0

    def __str__(self):
        return 'Response(type=0x%02x, data=0x%s, checksum=0x%02x)' % (
                self.type, self.data.hex(), self.chksum)



def register(type_):
    assert type_ not in _responses, 'Duplicate response type 0x%02x' % type_

    def decorator(func):
        _responses[type_] = func
        return func

    return decorator



def prepare(type_, data):
    length = len(data) + 2

    checksum = functools.reduce(xor, itertools.chain(
            type_.to_bytes(2, 'big'),
            length.to_bytes(2, 'big'),
            data), 0)

    message = struct.pack('!BB%dsB' % len(data), length, type_, data, checksum)
    #print('Prepared command 0x%s' % message.hex())
    return message


def read_response(ser):
    length = ser.read()
    length = int.from_bytes(length, 'big')
    answer = ser.read(length)
    return _unpack_raw_message(length, answer)
    type_, data, chksum = struct.unpack('!B%dsB' % (length - 2), answer)
    return {'type': type_, 'data': data, 'chksum': chksum}


def _unpack_raw_message(length, decoded):
    if len(decoded) != length or length < 2:
        print ("Unpack failed, length: %d, msg %s" % (length, decoded.hex()))
        return False
    type_, data, chksum = \
            struct.unpack('!B%dsB' % (length - 2), decoded)
    return _responses.get(type_, Response)(type_, data, chksum)

@Command(0x07)
def req_flash_erase():
    pass

@Command(0x09, raw=True)
def req_flash_write(addr, data):
    msg = struct.pack('<L%ds' % len(data), addr, data)
    return msg

@Command(0x0b, '<LH')
def req_flash_read(addr, length):
    return (addr, length)

@Command(0x1f, '<LH')
def req_ram_read(addr, length):
    return (addr, length)

@Command(0x25)
def req_flash_id():
    pass


@Command(0x27, '!B')
def req_change_baudrate(rate):
    #print(serial.Serial.BAUDRATES)
    clockspeed = 1000000
    divisor = round(clockspeed / rate)
    #print(divisor)
    return divisor


@Command(0x2c, '<BL')
def req_select_flash_type(type_, custom_jump=0):
    return (type_, custom_jump)

@Command(0x32)
def req_chip_id():
    pass


@Command(0x36, 'B')
def req_eeprom_erase(pdm_only=False):
    return not pdm_only


@register(0x26)
class ReadFlashIDResponse(Response):

    def __init__(self, *args):
        super().__init__(*args)
        self.manufacturer_id, self.device_id = struct.unpack('!BB', self.data)

    def __str__(self):
        return 'ReadFlashIDResponse %d (ok=%s, manufacturer_id=0x%02x, device_id=0x%02x)' % (self.status, self.ok, self.manufacturer_id, self.device_id)


@register(0x28)
class ChangeBaudrateResponse(Response):

    def __init__(self, *args):
        super().__init__(*args)

    def __str__(self):
        return 'ChangeBaudrateResponse %d (ok=%s)' % (self.status, self.ok)


@register(0x33)
class GetChipIDResponse(Response):

    def __init__(self, *args):
        super().__init__(*args)
        (self.chip_id,) = struct.unpack('!L', self.data)

    def __str__(self):
        return 'GetChipIDResponse (ok=%s, chip_id=0x%04x)' % (self.ok, self.chip_id)


@register(0x37)
class EraseEEPROMResponse(Response):

    def __init__(self, *args):
        super().__init__(*args)

    def __str__(self):
        return 'EraseEEPROMResponse %d (ok=%s)' % (self.status, self.ok)


def change_baudrate(ser, baudrate):
    ser.write(req_change_baudrate(baudrate))

    res = read_response(ser)
    if not res or not res.ok:
        logger.exception('Change baudrate failed')
        raise SystemExit(1)

    ser.baudrate = baudrate


def check_chip_id(ser):
    ser.write(req_chip_id())
    res = read_response(ser)
    if not res or not res.ok:
        logger.exception('Getting Chip ID failed')
        raise SystemExit(1)
    if res.chip_id != ZIGATE_CHIP_ID:
        logger.exception('This is not a supported chip, patches welcome')
        raise SystemExit(1)


def get_flash_type(ser):
    ser.write(req_flash_id())
    res = read_response(ser)

    if not res or not res.ok:
        print('Getting Flash ID failed')
        raise SystemExit(1)

    if res.manufacturer_id != 0xcc or res.device_id != 0xee:
        print('Unsupported Flash ID, patches welcome')
        raise SystemExit(1)
    else:
        return 8


def get_mac(ser):
    ser.write(req_ram_read(0x01001570, 8))
    res = read_response(ser)
    if res.data == bytes.fromhex('ffffffffffffffff'):
        ser.write(req_ram_read(0x01001580, 8))
        res = read_response(ser)
    return ':'.join(''.join(x) for x in zip(*[iter(res.data.hex())]*2))


def select_flash(ser, flash_type):
    ser.write(req_select_flash_type(flash_type))
    res = read_response(ser)
    if not res or not res.ok:
        print('Selecting flash type failed')
        raise SystemExit(1)


def write_flash_to_file(ser, filename):
    flash_start = cur = ZIGATE_FLASH_START
    flash_end = ZIGATE_FLASH_END

    print('reading old flash to %s' % filename)
    with open(filename, 'wb') as fd:
        fd.write(ZIGATE_BINARY_VERSION)
        read_bytes = 128
        while cur < flash_end:
            if cur + read_bytes > flash_end:
                read_bytes = flash_end - cur
            ser.write(req_flash_read(cur, read_bytes))
            res = read_response(ser)
            if cur == 0:
                (flash_end,) = struct.unpack('>L', res.data[0x20:0x24])
            fd.write(res.data)
            cur += read_bytes


def write_file_to_flash(ser, filename):
    print('writing new flash from %s' % filename)
    with open(filename, 'rb') as fd:
        ser.write(req_flash_erase())
        res = read_response(ser)
        if not res or not res.ok:
            print('Erasing flash failed')
            raise SystemExit(1)

        flash_start = cur = ZIGATE_FLASH_START
        flash_end = ZIGATE_FLASH_END

        bin_ver = fd.read(4)
        if bin_ver != ZIGATE_BINARY_VERSION:
            print('Not a valid image for Zigate')
            raise SystemExit(1)
        read_bytes = 128
        while cur < flash_end:
            data = fd.read(read_bytes)
            if not data:
                break
            ser.write(req_flash_write(cur, data))
            res = read_response(ser)
            if not res.ok:
                print('writing failed at 0x%08x, status: 0x%x, data: %s' % (cur, res.status, data.hex()))
                raise SystemExit(1)
            cur += read_bytes


def erase_EEPROM(ser, pdm_only=False):
    ser.timeout = 10
    ser.write(req_eeprom_erase(pdm_only))
    res = read_response(ser)
    if not res or not res.ok:
        print('Erasing EEPROM failed')
        raise SystemExit(1)

def ftdi_set_bitmode(dev, bitmask):
    bmRequestType = usb.util.build_request_type(usb.util.CTRL_OUT,
                                                usb.util.CTRL_TYPE_VENDOR,
                                                usb.util.CTRL_RECIPIENT_DEVICE)

    wValue = bitmask | (BITMODE_CBUS << BITMODE_CBUS)
    dev.ctrl_transfer(bmRequestType, SIO_SET_BITMODE_REQUEST, wValue)

def piZiGate_flash():
    # Cf: https://github.com/fairecasoimeme/ZiGate/blob/master/Tools/PiZiGate/Test/main.c
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    channel_lst = [17, 27]
    GPIO.setup(channel_lst, GPIO.OUT)

    GPIO.output( 27,0)
    time.sleep(0.5)
    GPIO.output( 17,0)
    time.sleep(0.5)
    GPIO.output( 17,1)
    time.sleep(0.5)


def piZiGate_run():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    channel_lst = [17, 27]
    GPIO.setup(channel_lst, GPIO.OUT)

    # Mode Run
    GPIO.output(27, 1)
    time.sleep(0.5)
    GPIO.output(17, 0)
    time.sleep(0.5)
    GPIO.output(17, 1)
    time.sleep(0.5)


def piZiGate_status( mode ):

    ei0 = GPIO.input(17)
    ei2 = GPIO.input(27)
    if mode == 'flash':
        if not ei2:
            print(" + GPIO(FLASH) OK")
        else:
            print(" + GPIO(FLASH) KO")
    elif mode == 'run':
        if ei0:
            print(" + GPIO(RUN) OK") 
        else:
            print(" + GPIO(RUN) KO")


def main():
    ports_available = [port for (port, _, _) in sorted(comports(include_links=True))] + [ '/dev/ttyUSBRPI3']
    parser = argparse.ArgumentParser()
    print("Available ports: %s" %ports_available)
    parser.add_argument('--din', help='Firmware flash for DIN-ZiGate', action='store_true', default= False)
    parser.add_argument('--pi', help='Firmware flash for Pi-ZiGate', action='store_true', default= False)
    #parser.add_argument('-p', '--serialport', choices=ports_available, help='Serial port, e.g. /dev/ttyUSB0', required=True)
    parser.add_argument('-p', '--serialport',  help='Serial port, e.g. /dev/ttyUSB0', required=True)
    parser.add_argument('-b', '--serialspeed', help='Serial port speed', required=True)
    parser.add_argument('-w', '--write', help='Firmware bin to flash onto the chip')
    parser.add_argument('-s', '--save', help='File to save the currently loaded firmware to')
    parser.add_argument('-e', '--erase', help='Erase EEPROM', action='store_true')
    parser.add_argument('--pdm-only', help='Erase PDM only, use it with --erase', action='store_true')


    args = parser.parse_args()

    try:
        ser = serial.Serial(args.serialport,  38400, timeout=5)
    except serial.SerialException:
        logger.exception("Could not open serial device %s", args.serialport)
        raise SystemExit(1)
    
    atexit.register(change_baudrate, ser, 38400)
    if args.din:
        # Put DIN-ZiGate in flash mode
        # From @faircasoimeme tool
        dev_din = usb.core.find(custom_match = \
            lambda d: \
                d.idVendor==0x0403 and
                d.idProduct==0x6001 )
        ftdi_set_bitmode(dev_din, 0x00)
        time.sleep(1.0)
        # Set CBUS2/3 high...
        ftdi_set_bitmode(dev_din, 0xCC)
        time.sleep(1.0)
        # Set CBUS2/3 low...
        ftdi_set_bitmode(dev_din, 0xC0)
        time.sleep(1.0)
        ftdi_set_bitmode(dev_din, 0xC4)
        time.sleep(1.0)

    elif args.pi:
        piZiGate_flash()
        piZiGate_status( 'flash')



    change_baudrate(ser, int(args.serialspeed))
    check_chip_id(ser)
    flash_type = get_flash_type(ser)
    mac_address = get_mac(ser)
    print('Found MAC-address: %s' % mac_address)
    if args.write or args.save or args.erase:
        select_flash(ser, flash_type)

    if args.save:
        write_flash_to_file(ser, args.save)

    if args.write:
        write_file_to_flash(ser, args.write)

    if args.erase:
        erase_EEPROM(ser, args.pdm_only)

    if args.din:
        # Put DIN-ZiGate in flash mode
        # From @faircasoimeme tool
        ftdi_set_bitmode(dev_din, 0xC8)
        time.sleep(1.0)
        ftdi_set_bitmode(dev_din, 0xCC)

    elif args.pi:
        piZiGate_run()
        piZiGate_status( 'run')


if __name__ == "__main__":
    main()
