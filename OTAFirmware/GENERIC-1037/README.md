Manufacturer code 0x1037 is shared by several vendors: Eurotronic, LiXee and Lumi.

A Zigbee OTA image is matched on the (manufacturer_code, image_type) pair carried in
its own header, not on the folder it sits in, so firmware for any of these vendors
can be dropped here.

- Eurotronic: https://github.com/Koenkk/zigbee-OTA
- LiXee: https://github.com/fairecasoimeme/Zlinky_TIC/releases
- Lumi: https://github.com/Koenkk/zigbee-OTA

The former EUROTRONICS/, LIXEE/ and LUMI/ folders are still scanned, so firmware
already placed there keeps working. New firmware is better placed here.

Make sure that the folder has only the README.md file and Firmware files.
