import os.path


while 1:
    print("Enter the DeviceList.txt filename: ")
    filename=input()
    if os.path.exists(filename):
        break


nb = 0
with open( filename, 'r') as myfile2:
    for line in myfile2:
        if not line.strip() :
            #Empty line
            continue
        (key, val) = line.split(":",1)
        key = key.replace(" ","")
        key = key.replace("'","")

        dlVal=eval(val)
        print("%-10s %s" %('NwkID', key))
        for i, j in dlVal.items():
            if 'Ep' == i:
                # Ep {'01': {'0000': {}, 'ClusterType': {'576': 'ColorControl'}, '0003': {}, '0004': {}, '0005': {}, '0006': '00', '0008': {}, '0300': {}, '0b05': {}, '1000': {}}}
                print("Ep")
                j = eval(str(j))
                for k,l in j.items():
                    print("           %-10s %s" %(k,l))
            else:
                print("%-10s %s" %(i,j))

        print("======")


myfile2.close()

