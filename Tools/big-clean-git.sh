#!/bin/bash


rm -rf .flake8 .github .gitmodules IMPORTANT.md CONTRIBUTING.md LICENSE.txt MANIFEST.in
rm -rf Conf/Certified
rm -rf Classes
rm -rf Modules
rm -rf Tools
rm -rf Zigbee
rm -rf Zigate-Firmware
rm -rf bellows
rm -rf zigpy
rm -rf zigpy_znp
rm -rf zigpy_deconz
rm -rf external


git config --add submodule.recurse true
git reset --hard
