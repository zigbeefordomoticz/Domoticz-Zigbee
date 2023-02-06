import binascii
from Modules.tools import  checkAndStoreAttributeValue

def zlinky_CurrentSummationDelivered(self, nwkid, ep, cluster, attribut, value):
    # HP or Base
    MajDomoDevice(self, Devices, nwkid, ep, cluster, str(value), Attribute_=attribut)
    store_ZLinky_infos( self, nwkid, 'BASE', value)
    store_ZLinky_infos( self, nwkid, 'EAST', value)
    return value

def zlinky_CurrentSummationDelivered(self, nwkid, ep, cluster, attribut, value):
    store_ZLinky_infos( self, nwkid, 'EAIT', value)
    return value

def zlinky_ActiveRegisterTierDelivered(self, nwkid, ep, cluster, attribut, value):
    if value == 0:
        return None
    
    MajDomoDevice(self, Devices, nwkid, ep, "0009", str(value), Attribute_="0020")
    zlinky_color_tarif(self, nwkid, str(value))
    store_ZLinky_infos( self, nwkid, 'PTEC', value)
    return value


def zlinky_CurrentTier1SummationDelivered(self, nwkid, ep, cluster, attribut, value):
    # HC or Base or BBRHCJB
    if value == "":
        return None

    self.log.logging( "ZLinky", "Debug", "Cluster0702 - 0x0100 ZLinky_TIC Value: %s Conso: %s " % (MsgClustervalue, value), nwkid, )
    zlinky_totalisateur(self, nwkid, attribut, value)
    MajDomoDevice(self, Devices, nwkid, ep, cluster, str(value), Attribute_=attribut)
    store_ZLinky_infos( self, nwkid, 'EASF01', value)
    store_ZLinky_infos( self, nwkid, 'HCHC', value)
    store_ZLinky_infos( self, nwkid, 'EJPHN', value)
    store_ZLinky_infos( self, nwkid, 'BBRHCJB', value)
    return value

def zlinky_CurrentTier2SummationDelivered(self, nwkid, ep, cluster, attribut, value):
    # HP or BBRHPJB
    if value == 0:
        return None
    self.log.logging( "ZLinky", "Debug", "Cluster0702 - 0x0100 ZLinky_TIC Value: %s Conso: %s " % (MsgClustervalue, value), nwkid, )
    zlinky_totalisateur(self, nwkid, attribut, value)
    MajDomoDevice(self, Devices, nwkid, ep, cluster, str(value), Attribute_=attribut)
    store_ZLinky_infos( self, nwkid, 'EASF02', value)
    store_ZLinky_infos( self, nwkid, 'HCHP', value)
    store_ZLinky_infos( self, nwkid, 'EJPHPM', value)
    store_ZLinky_infos( self, nwkid, 'BBRHCJW', value)
    return value

def zlinky_CurrentTier3SummationDelivered(self, nwkid, ep, cluster, attribut, value):
    if value == 0:
        return None

    zlinky_totalisateur(self, nwkid, attribut, value)
    MajDomoDevice(self, Devices, nwkid, "f2", cluster, str(value), Attribute_=attribut)
    store_ZLinky_infos( self, nwkid, 'EASF03', value)
    store_ZLinky_infos( self, nwkid, 'BBRHCJW', value)
    return value

def zlinky_CurrentTier4SummationDelivered(self, nwkid, ep, cluster, attribut, value):
    if value == 0:
        return

    zlinky_totalisateur(self, nwkid, attribut, value)
    MajDomoDevice(self, Devices, nwkid, "f2", cluster, str(value), Attribute_=attribut)
    store_ZLinky_infos( self, nwkid, 'EASF04', value)
    store_ZLinky_infos( self, nwkid, 'BBRHPJW', value)
    return value


def zlinky_CurrentTier5SummationDelivered(self, nwkid, ep, cluster, attribut, value):
    if value == 0:
        return None
    zlinky_totalisateur(self, nwkid, attribut, value)
    MajDomoDevice(self, Devices, nwkid, "f3", cluster, str(value), Attribute_=attribut)
    store_ZLinky_infos( self, nwkid, 'EASF05', value)
    store_ZLinky_infos( self, nwkid, 'BBRHCJR', value)
    return value

def zlinky_CurrentTier6SummationDelivered(self, nwkid, ep, cluster, attribut, value):
    if value == 0:
        return None

    zlinky_totalisateur(self, nwkid, attribut, value)
    MajDomoDevice(self, Devices, nwkid, "f3", cluster, str(value), Attribute_=attribut)
    store_ZLinky_infos( self, nwkid, 'EASF06', value)
    store_ZLinky_infos( self, nwkid, 'BBRHPJR', value)
    return value

def zlinky_CurrentTier7SummationDelivered(self, nwkid, ep, cluster, attribut, value):
    if value == 0:
        return None

    store_ZLinky_infos( self, nwkid, 'EASF07', value)
    return value



def zlinky_CurrentTier8SummationDelivered(self, nwkid, ep, cluster, attribut, value):
    if value == 0:
        return None

    store_ZLinky_infos( self, nwkid, 'EASF08', value)
    return value


def zlinky_CurrentTier9SummationDelivered(self, nwkid, ep, cluster, attribut, value):
    if value == 0:
        return None

    checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
    store_ZLinky_infos( self, nwkid, 'EASF09', value)
    return value

def zlinky_CurrentTier10SummationDelivered(self, nwkid, ep, cluster, attribut, value):
    if value == 0:
        return None

    store_ZLinky_infos( self, nwkid, 'EASF10', value)
    return value
        

def zlinky_SiteID(self, nwkid, ep, cluster, attribut, value):
    store_ZLinky_infos( self, nwkid, 'PRM', binascii.unhexlify(value).decode("utf-8"))
    return value
        
def zlinky_MeterSerialNumber(self, nwkid, ep, cluster, attribut, value):
    value = binascii.unhexlify(value).decode("utf-8")
    self.log.logging(
        "Cluster",
        "Debug",
        "Cluster0702 - 0x0308 - Serial Number %s" % (value),
        nwkid,
    )
    
    store_ZLinky_infos( self, nwkid, 'ADC0', value)
    store_ZLinky_infos( self, nwkid, 'ADSC', value)
    return value
    