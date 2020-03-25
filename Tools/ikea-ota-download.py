#!/usr/bin/python3

"""
Snipped to dowload current IKEA ZLL OTA files into current directory
"""

import os
import json
import urllib.request

f = urllib.request.urlopen("https://fw.ota.homesmart.ikea.net/feed/version_info.json")
data = f.read()

arr = json.loads(data)

otapath = './'

if not os.path.exists(otapath):
    os.makedirs(otapath)

for i in arr:
    if 'fw_binary_url' in i:
        url = i['fw_binary_url']
        ls = url.split('/')
        fname = ls[len(ls) - 1]
        path = '%s/%s' % (otapath, fname)

        if not os.path.isfile(path):
            urllib.request.urlretrieve(url, path)
            print(i['fw_binary_url'])
            print(path)
        else:
            print('%s already exists' % fname)



