

FILENAME = 'DeviceList-13.txt'

ListOfDevices = {}

with open( FILENAME , 'r') as myfile2:
    for line in myfile2:
        if not line.strip() :
            #Empty line
            continue
        (key, val) = line.split(":",1)
        key = key.replace(" ","")
        key = key.replace("'","")

        if key in  ( '0000'): continue

        try:
            dlVal=eval(val)
        except (SyntaxError, NameError, TypeError, ZeroDivisionError):
            Domoticz.Error("LoadDeviceList failed on %s" %val)
            continue

        if 'Status' in dlVal:
            if dlVal['Status'] == 'inDB':
                print("Patching Status")
                dlVal['Status'] = '8043'


        ListOfDevices[ key] = dlVal


for nwkid in ListOfDevices:
    for ep in  ListOfDevices[ nwkid ]['Ep']:
        if 'ClusterType' in ListOfDevices[ nwkid ]['Ep'][ ep ]:
            print("Patching ClusterType")
            ListOfDevices[ nwkid ]['Ep'][ ep ]['ClusterType'] = {}

with open( FILENAME + '-updated' , 'wt') as file:
    for key in ListOfDevices :
        try:
            file.write(key + " : " + str(ListOfDevices[key]) + "\n")
        except IOError:
            Domoticz.Error("Error while writing to plugin Database %s" %_DeviceListFileName)





