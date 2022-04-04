REM This tool allows the creation of the Windows Symbolic links after a git clone

del dns
mklink /D dns external\dnspython\dns

del bellows
mklink /D bellows external\bellows\bellows

del serial
mklink /D serial external\pyserial\serial

del zigpy
mklink /D zigpy external\zigpy\zigpy

del zigpy_deconz
mklink /D zigpy_deconz external\zigpy-deconz\zigpy_deconz

del zigpy_zigate
mklink /D zigpy_zigate external\zigpy-zigate\zigpy_zigate

del zigpy_znp
mklink /D zigpy_znp external\zigpy-znp\zigpy_znp
