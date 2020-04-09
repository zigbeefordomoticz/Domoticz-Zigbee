import http.client, urllib.request, urllib.parse, urllib.error, base64, time
import json
import os


"""
https://portal.update.ledvance.com/docs/services/firmware-rest-api/operations/5d8e482e2968c2f30d278392

https://api.update.ledvance.com/v1/zigbee/firmwares/download
"""

headers = {
}

params = urllib.parse.urlencode({
})

conn = http.client.HTTPSConnection('api.update.ledvance.com')

print("Retreive list of products")
conn.request("GET", "/v1/zigbee/products/details?%s" % params, "{body}", headers)
response = conn.getresponse()
data = json.loads(response.read().decode(response.headers.get_content_charset('utf-8')), encoding=dict)
conn.close()
#data = response.read()

otapath = '%s/LEDVANCE-OTAU' % os.path.expanduser('~')
if not os.path.exists(otapath):
        os.makedirs(otapath)

for products in data['products']:
    print("Processing %s" %products['displayName'])

    if 'firmwares' not in products:
        print("Not firmware in %s" %products)
        continue
    if 'latest' not in products:
        print("Not latest in %s" %products)
        continue

    Company = products['latest']['identity']['company']
    Product = products['latest']['identity']['product']
    Version = '%s.%s.%s' %(products['latest']['identity']['version']['major'],
        products['latest']['identity']['version']['minor'],
        products['latest']['identity']['version']['build'])
    path = products['latest']['name']

    if not os.path.exists( otapath + '/' + path ):
        # https://portal.update.ledvance.com/docs/services/firmware-rest-api/operations/5d8e482e89d78b3d6bf67e69?
        url = "https://api.update.ledvance.com" + "/v1/zigbee/firmwares/download/%s/%s/latest" %(Company, Product)
        print('--> Url: %s' %url)
        print('--> Path: %s' %path)
        urllib.request.urlretrieve(url, otapath + '/' + path)
        time.sleep(30)
    else:
        print('-- Already existing')

