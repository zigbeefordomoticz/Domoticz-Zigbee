

MAX_KB_TO_SEND = 8 * 1024   # Chunk size
DEBUG_HTTP = False


def setupHeadersResponse( cookie = None ):
    
    _response = {}
    _response["Headers"] = {}
    _response["Headers"]["Server"] = "Domoticz"
    _response["Headers"]["User-Agent"] = "Plugin-Zigate/v1"

    _response["Headers"]['Access-Control-Allow-Headers'] = 'Cache-Control, Pragma, Origin, Authorization,   Content-Type, X-Requested-With'
    _response["Headers"]['Access-Control-Allow-Methods'] = 'GET, POST, DELETE'
    _response["Headers"]['Access-Control-Allow-Origin'] = '*'

    _response["Headers"]["Referrer-Policy"] = "no-referrer"

    if cookie:
        _response["Headers"]["Cookie"] = cookie

    #_response["Headers"]["Accept-Ranges"] = "bytes"
    # allow users of a web application to include images from any origin in their own conten
    # and all scripts only to a specific server that hosts trusted code.
    #_response["Headers"]["Content-Security-Policy"] = "default-src 'self'; img-src *"
    #_response["Headers"]["Content-Security-Policy"] = "default-src * 'unsafe-inline' 'unsafe-eval'"

    return _response



def keepConnectionAlive( self ):

    self.heartbeats += 1
    return

def DumpHTTPResponseToLog(httpDict):
    
    if not DEBUG_HTTP:
        return
    if isinstance(httpDict, dict):
        self.logging( 'Log', "HTTP Details ("+str(len(httpDict))+"):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                self.logging( 'Log', "--->'"+x+" ("+str(len(httpDict[x]))+"):")
                for y in httpDict[x]:
                    self.logging( 'Log', "------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                if x == 'Data':
                    self.logging( 'Log', "--->'%s':'%.40s'" %(x, str(httpDict[x])))
                else:
                    self.logging( 'Log', "--->'" + x + "':'" + str(httpDict[x]) + "'")
