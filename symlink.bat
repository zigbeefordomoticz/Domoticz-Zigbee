REM This tool allows the creation of the Windows Symbolic links after a git clone

del dns bellows serial zigpy zigpy_zigate zigpy_znp zigpy_znp

mklink /D dns external\dnspython\dns
mklink /D bellows external\bellows\bellow
mklink /D serial external\pyserial\serial
mklink /D zigpy external\zigpy\zigpy
mklink /D zigpy_deconz external\zigpy-deconz\zigpy_deconz
mklink /D zigpy_zigate external\zigpy-zigate\zigpy_zigate
mklink /D zigpy_znp external\zigpy-znp\zigpy_znp
