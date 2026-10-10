Manufacturer code 0x1015 is shared by Develco and frient A/S (the same hardware sold
under two brands).

A Zigbee OTA image is matched on the (manufacturer_code, image_type) pair carried in
its own header, not on the folder it sits in, so firmware for either vendor can be
dropped here.

- https://github.com/Koenkk/zigbee-OTA

The former DEVELCO/ folder is still scanned, so firmware already placed there keeps
working. New firmware is better placed here.

Make sure that the folder has only the README.md file and Firmware files.
