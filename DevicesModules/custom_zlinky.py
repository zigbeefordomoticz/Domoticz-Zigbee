import binascii 

from Modules.domoMaj import MajDomoDevice
from Modules.tools import checkAndStoreAttributeValue
from Modules.zlinky import (ZLINK_CONF_MODEL, ZLinky_TIC_COMMAND,
                            convert_kva_to_ampere, decode_STEG, linky_mode,
                            store_ZLinky_infos,
                            update_zlinky_device_model_if_needed,
                            zlinky_check_alarm, zlinky_color_tarif,
                            zlinky_totalisateur)


def zlinky_clusters(self, Devices, nwkid, ep, cluster, attribut, value):
    self.log.logging( "ZLinky", "Debug", "zlinky_clusters %s - %s/%s Attribute: %s Value: %s" % (
        cluster, nwkid, ep, attribut, value), nwkid, )

    if cluster == "0b01":
        zlinky_meter_identification(self, Devices, nwkid, ep, cluster, attribut, value)
        
    elif cluster == "0702":
        zlinky_cluster_metering(self, Devices, nwkid, ep, cluster, attribut, value)
        
    elif cluster == "0b04":
        zlinky_cluster_electrical_measurement(self, Devices, nwkid, ep, cluster, attribut, value)
    
    elif cluster == "ff66":
        zlinky_cluster_lixee_private(self, Devices, nwkid, ep, cluster, attribut, value)
        
def zlinky_meter_identification(self, Devices, nwkid, ep, cluster, attribut, value):
    self.log.logging( "ZLinky", "Debug", "zlinky_meter_identification %s - %s/%s Attribute: %s Value: %s" % (
        cluster, nwkid, ep, attribut, value), nwkid, )
    
    checkAndStoreAttributeValue( self, nwkid, ep, cluster, attribut, value, )
    if attribut == "000d":
        # Looks like in standard mode PREF is in VA while in historique mode ISOUSC is in A
        # Donc en mode standard ISOUSC = ( value * 1000) / 200
        if "ZLinky" in self.ListOfDevices[nwkid] and "PROTOCOL Linky" in self.ListOfDevices[nwkid]["ZLinky"]:
            if self.ListOfDevices[nwkid]["ZLinky"]["PROTOCOL Linky"] in (0, 2):
                # Mode Historique mono ( 0 )
                # Mode Historique tri ( 2 )
                store_ZLinky_infos( self, nwkid, 'ISOUSC', value)
            else:
                # Mode standard 
                store_ZLinky_infos( self, nwkid, 'PREF', value)
                store_ZLinky_infos( self, nwkid, 'ISOUSC', convert_kva_to_ampere(value) )
        
    elif attribut == "000a":
        store_ZLinky_infos( self, nwkid, 'VTIC', value)
        
    elif attribut == "000e":
        store_ZLinky_infos( self, nwkid, 'PCOUP', value)


def zlinky_cluster_metering(self, Devices, nwkid, ep, cluster, attribut, value):
    # Smart Energy Metering

    self.log.logging( "ZLinky", "Debug", "zlinky_cluster_metering - %s - %s/%s attribut: %s value: %s" % (
        cluster, nwkid, ep, attribut, value), nwkid, )

    if attribut == "0000":  # CurrentSummationDelivered
        # HP or Base
        self.log.logging( "ZLinky", "Debug", "Cluster0702 - 0x0000 ZLinky_TIC Value: %s" % (value), nwkid, )
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        MajDomoDevice(self, Devices, nwkid, ep, cluster, str(value), Attribute_=attribut)
        store_ZLinky_infos( self, nwkid, 'BASE', value)
        store_ZLinky_infos( self, nwkid, 'EAST', value)

    elif attribut == "0001":  # CURRENT_SUMMATION_RECEIVED
        self.log.logging("Cluster", "Debug", "Cluster0702 - CURRENT_SUMMATION_RECEIVED %s " % (value), nwkid)
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'EAIT', value)
            

    elif attribut == "0020":
        if value == 0:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        MajDomoDevice(self, Devices, nwkid, ep, "0009", str(value), Attribute_="0020")
        zlinky_color_tarif(self, nwkid, str(value))
        store_ZLinky_infos( self, nwkid, 'PTEC', value)

    elif attribut == "0100":
        # HC or Base or BBRHCJB
        if value == "":
            return
        self.log.logging( "ZLinky", "Debug", "Cluster0702 - 0x0100 ZLinky_TIC Conso: %s " % (value), nwkid, )
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        zlinky_totalisateur(self, nwkid, attribut, value)
        MajDomoDevice(self, Devices, nwkid, ep, cluster, str(value), Attribute_=attribut)
        store_ZLinky_infos( self, nwkid, 'EASF01', value)
        store_ZLinky_infos( self, nwkid, 'HCHC', value)
        store_ZLinky_infos( self, nwkid, 'EJPHN', value)
        store_ZLinky_infos( self, nwkid, 'BBRHCJB', value)

    elif attribut == "0102":
        # HP or BBRHPJB
        if value == 0:
            return
        self.log.logging( "ZLinky", "Debug", "Cluster0702 - 0x0100 ZLinky_TIC Conso: %s " % (value), nwkid, )
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        zlinky_totalisateur(self, nwkid, attribut, value)
        MajDomoDevice(self, Devices, nwkid, ep, cluster, str(value), Attribute_=attribut)
        store_ZLinky_infos( self, nwkid, 'EASF02', value)
        store_ZLinky_infos( self, nwkid, 'HCHP', value)
        store_ZLinky_infos( self, nwkid, 'EJPHPM', value)
        store_ZLinky_infos( self, nwkid, 'BBRHCJW', value)

    elif attribut == "0104":
        if value == 0:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        zlinky_totalisateur(self, nwkid, attribut, value)
        MajDomoDevice(self, Devices, nwkid, "f2", cluster, str(value), Attribute_=attribut)
        store_ZLinky_infos( self, nwkid, 'EASF03', value)
        store_ZLinky_infos( self, nwkid, 'BBRHCJW', value)

        
    elif attribut == "0106":
        if value == 0:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        zlinky_totalisateur(self, nwkid, attribut, value)
        MajDomoDevice(self, Devices, nwkid, "f2", cluster, str(value), Attribute_=attribut)
        store_ZLinky_infos( self, nwkid, 'EASF04', value)
        store_ZLinky_infos( self, nwkid, 'BBRHPJW', value)

    elif attribut == "0108":
        if value == 0:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        zlinky_totalisateur(self, nwkid, attribut, value)
        MajDomoDevice(self, Devices, nwkid, "f3", cluster, str(value), Attribute_=attribut)
        store_ZLinky_infos( self, nwkid, 'EASF05', value)
        store_ZLinky_infos( self, nwkid, 'BBRHCJR', value)

    elif attribut == "010a":
        if value == 0:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        zlinky_totalisateur(self, nwkid, attribut, value)
        MajDomoDevice(self, Devices, nwkid, "f3", cluster, str(value), Attribute_=attribut)
        store_ZLinky_infos( self, nwkid, 'EASF06', value)
        store_ZLinky_infos( self, nwkid, 'BBRHPJR', value)

    elif attribut == "010c":
        if value == 0:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'EASF07', value)

    elif attribut == "010e":
        if value == 0:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'EASF08', value)

    elif attribut == "0110":
        if value == 0:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'EASF09', value)

    elif attribut == "0112":
        if value == 0:
            return

        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'EASF10', value)

    elif attribut == "0307":  # PRM
        store_ZLinky_infos( self, nwkid, 'PRM', value)
        
    elif attribut == "0308":  # Serial Number
        self.log.logging( "ZLinky", "Debug", "Cluster0702 - 0x0308 - Serial Number %s" % (value), nwkid, )
        
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'ADC0', value)
        store_ZLinky_infos( self, nwkid, 'ADSC', value)    


def zlinky_cluster_electrical_measurement(self, Devices, nwkid, ep, cluster, attribut, value):
    
    self.log.logging( "ZLinky", "Debug", "zlinky_cluster_electrical_measurement - %s - %s/%s attribut: %s value: %s" % (
        cluster, nwkid, ep, attribut, value), nwkid, )

    if attribut == "0305":
            store_ZLinky_infos( self, nwkid, 'ERQ1', value)

    elif attribut == "050e":
            store_ZLinky_infos( self, nwkid, 'ERQ2', value)
        
    elif attribut == "090e":
            store_ZLinky_infos( self, nwkid, 'ERQ3', value)

    elif attribut == "0a0e":
            store_ZLinky_infos( self, nwkid, 'ERQ4', value)
    
    elif attribut == "050b":  # Active Power
        
        self.log.logging("Cluster", "Debug", "ReadCluster %s - %s/%s Power %s" % (cluster, nwkid, ep, value))
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        MajDomoDevice(self, Devices, nwkid, ep, cluster, str(value))
        store_ZLinky_infos( self, nwkid, 'CCASN', value)

    elif attribut == "090b":
        store_ZLinky_infos( self, nwkid, 'CCASN-1',value)
        
    elif attribut in ("0505", "0905", "0a05"):  # RMS Voltage
        self.log.logging("Cluster", "Debug", "ReadCluster %s - %s/%s Voltage %s" % (cluster, nwkid, ep, value))
        if value == 0xFFFF:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        if attribut == "0505":
            MajDomoDevice(self, Devices, nwkid, ep, "0001", str(value))
            if "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] in ZLINK_CONF_MODEL:
                store_ZLinky_infos( self, nwkid, 'URMS1', value)
        elif attribut == "0905":
            if "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] in ZLINK_CONF_MODEL:
                store_ZLinky_infos( self, nwkid, 'URMS2', value)
        elif attribut == "0a05":
            if "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] in ZLINK_CONF_MODEL:
                store_ZLinky_infos( self, nwkid, 'URMS3', value)            

    elif attribut == "0508":  # RMSCurrent
        if value == 0xFFFF:
            return
        self.log.logging( "ZLinky", "Debug", "ReadCluster %s - %s/%s %s Current L1 %s" % (
            cluster, nwkid, ep, attribut, value), nwkid, )

        # from random import randrange
        # value = randrange( 0x0, 0x3c)
        if value == 0xFFFF:
            return

        store_ZLinky_infos( self, nwkid, 'IRMS1', value)
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        MajDomoDevice(self, Devices, nwkid, ep, cluster, str(value), Attribute_=attribut)

        # Check if Intensity is below subscription level
        MajDomoDevice( self, Devices, nwkid, ep, "0009", zlinky_check_alarm(self, Devices, nwkid, ep, value), Attribute_="0005", )

    elif attribut in ("050a", "090a", "0a0a"):  # Max Current
        if value == 0xFFFF:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        if attribut == "050a":
            store_ZLinky_infos( self, nwkid, 'IMAX', value)
            store_ZLinky_infos( self, nwkid, 'IMAX1', value)
        elif attribut == "090a":
            store_ZLinky_infos( self, nwkid, 'IMAX2', value)
        elif attribut == "0a0a":
            store_ZLinky_infos( self, nwkid, 'IMAX3', value)            

    elif attribut in ( "050d", "0304",):
        # Max Tri Power reached
        if value == 0x8000:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        
        _linkyMode = linky_mode( self, nwkid, protocol=True ) 
        
        if _linkyMode in ( 0, 2,) and attribut == "050d":
            # Historique Tri
            store_ZLinky_infos( self, nwkid, 'PMAX', value) 
            
        elif _linkyMode in ( 1, 5, ) and attribut == "050d":
            # Historic Mono
            store_ZLinky_infos( self, nwkid, 'SMAXN', value) 

        elif _linkyMode in ( 3, 7, ) and attribut == "050d":
            # Standard Tri
            store_ZLinky_infos( self, nwkid, 'SMAXN1', value) 
            return

        elif _linkyMode in ( 3, 7, ) and attribut == "0304":
            # Standard Tri
            store_ZLinky_infos( self, nwkid, 'SMAXN', value)

        else:                
            self.log.logging( "ZLinky", "Error", "=====> ReadCluster %s - %s/%s Unexpected %s/%s linkyMode: %s" % (
                cluster, nwkid, ep, attribut, value, _linkyMode ), nwkid, )
            return

        store_ZLinky_infos( self, nwkid, 'PMAX', value) 
        store_ZLinky_infos( self, nwkid, 'SMAXN', value) 
        store_ZLinky_infos( self, nwkid, 'SMAXN1', value) 

    elif attribut == "090d":
        # Max Tri Power reached
        if value == 0x8000:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'SMAXN2', value) 

    elif attribut == "0a0d":
        # Max Tri Power reached
        if value == 0x8000:
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'SMAXN3', value) 

    elif attribut in ( "050f", "0306",) :  # Apparent Power - 0x0306 is for tri-phased
        if value >= 0xFFFF:
            self.log.logging( "ZLinky", "Error", "=====> ReadCluster %s - %s/%s Apparent Power %s out of range !!!" % (cluster, nwkid, ep, value), nwkid, )
            return
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        
        self.log.logging( "ZLinky", "Debug", "=====> ReadCluster %s - %s/%s Apparent Power %s" % (cluster, nwkid, ep, value), nwkid, )
        # ApparentPower (Represents  the  single  phase  or  Phase  A,  current  demand  of  apparent  (Square  root  of  active  and  reactive power) power, in VA.)

        self.log.logging( "ZLinky", "Debug", "=====> ReadCluster %s - %s/%s Apparent Power %s" % (cluster, nwkid, ep, value), nwkid, )
        
        _linkyMode = linky_mode( self, nwkid, protocol=True ) 
        
        if _linkyMode in ( 0, 2,) and attribut == "050f":
            # Historique Tri
            store_ZLinky_infos( self, nwkid, 'PAPP', value) 
            
        elif _linkyMode in ( 1, 5, ) and attribut == "050f":
            # Historic Mono
            store_ZLinky_infos( self, nwkid, 'SINSTS', value) 

        elif _linkyMode in ( 3, 7, ) and attribut == "050f":
            # Standard Tri
            store_ZLinky_infos( self, nwkid, 'SINSTS1', value) 
            return

        elif _linkyMode in ( 3, 7, ) and attribut == "0306":
            # Standard Tri
            store_ZLinky_infos( self, nwkid, 'SINSTS', value)

        else:                
            self.log.logging( "ZLinky", "Error", "=====> ReadCluster %s - %s/%s Unexpected %s/%s linkyMode: %s" % (
                cluster, nwkid, ep, attribut, value, _linkyMode ), nwkid, )
            return
            
        tarif_color = None
        if "ZLinky" in self.ListOfDevices[nwkid] and "Color" in self.ListOfDevices[nwkid]["ZLinky"]:
            tarif_color = self.ListOfDevices[nwkid]["ZLinky"]["Color"]
            if tarif_color == "White":
                MajDomoDevice(self, Devices, nwkid, "01", cluster, str(0), Attribute_=attribut)
                MajDomoDevice(self, Devices, nwkid, "f2", cluster, str(value), Attribute_=attribut)
                MajDomoDevice(self, Devices, nwkid, "f3", cluster, str(0), Attribute_=attribut)

            elif tarif_color == "Red":
                MajDomoDevice(self, Devices, nwkid, "01", cluster, str(0), Attribute_=attribut)
                MajDomoDevice(self, Devices, nwkid, "f2", cluster, str(0), Attribute_=attribut)
                MajDomoDevice(self, Devices, nwkid, "f3", cluster, str(value), Attribute_=attribut)

            else:
                # All others
                MajDomoDevice(self, Devices, nwkid, "01", cluster, str(value), Attribute_=attribut)
                MajDomoDevice(self, Devices, nwkid, "f2", cluster, str(0), Attribute_=attribut)
                MajDomoDevice(self, Devices, nwkid, "f3", cluster, str(0), Attribute_=attribut)
        else:
            MajDomoDevice(self, Devices, nwkid, "01", cluster, str(value), Attribute_=attribut)

        self.log.logging( "ZLinky", "Debug", "ReadCluster %s - %s/%s Apparent Power %s" % (cluster, nwkid, ep, value), nwkid, )

    elif attribut in ( "090f", ):
            store_ZLinky_infos( self, nwkid, 'SINSTS2', value)

    elif attribut in ( "0a0f", ):
            store_ZLinky_infos( self, nwkid, 'SINSTS3', value)
       
    elif attribut in ("0908", "0a08"):  # Current Phase 2 and Current Phase 3
        # from random import randrange
        # value = randrange( 0x0, 0x3c)
        if value == 0xFFFF:
            return

        MajDomoDevice(self, Devices, nwkid, ep, cluster, str(value), Attribute_=attribut)
        # Check if Intensity is below subscription level
        if attribut == "0908":
            self.log.logging("Cluster", "Debug", "ReadCluster %s - %s/%s %s Current L2 %s" % (cluster, nwkid, ep, attribut, value), nwkid)
            MajDomoDevice( self, Devices, nwkid, "f2", "0009", zlinky_check_alarm(self, Devices, nwkid, ep, value), Attribute_="0005", )
            store_ZLinky_infos( self, nwkid, 'IRMS2', value)

        elif attribut == "0a08":
            self.log.logging("Cluster", "Debug", "ReadCluster %s - %s/%s %s Current L3 %s" % (cluster, nwkid, ep, attribut, value), nwkid)
            MajDomoDevice( self, Devices, nwkid, "f3", "0009", zlinky_check_alarm(self, Devices, nwkid, ep, value), Attribute_="0005", )
            store_ZLinky_infos( self, nwkid, 'IRMS3', value)
        
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut == "0511":
        store_ZLinky_infos( self, nwkid, 'UMOY1', value)   

    elif attribut == "0911":
        store_ZLinky_infos( self, nwkid, 'UMOY2', value)     

    elif attribut == "0a11":
        store_ZLinky_infos( self, nwkid, 'UMOY3', value)
        
        
def zlinky_cluster_lixee_private(self, Devices, nwkid, ep, cluster, attribut, value):
    if nwkid not in self.ListOfDevices:
        return
    if "Ep" not in self.ListOfDevices[nwkid]:
        return
    if ep not in self.ListOfDevices[nwkid]["Ep"]:
        return

    if 'ZLinky' not in self.ListOfDevices[ nwkid ]:
        self.ListOfDevices[ nwkid ]['ZLinky'] = {}

    if attribut in ZLinky_TIC_COMMAND:
        self.log.logging( "ZLinky", "Debug", "Store Attribute: %s - %s  Value: %s" % (
            ZLinky_TIC_COMMAND[ attribut ] ,attribut, value), nwkid, )
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, ZLinky_TIC_COMMAND[ attribut ], value)


    if attribut == "0000":
        # Option tarifaire
        value = ''.join(map(lambda x: x if ord(x) in range(128) else ' ', value))
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut == "0001":
        # Histo : DEMAIN
        value = ''.join(map(lambda x: x if ord(x) in range(128) else ' ', value))
        tarif = None
        if (
            "ff66" in self.ListOfDevices[nwkid]["Ep"][ep]
            and "0000" in self.ListOfDevices[nwkid]["Ep"][ep]["ff66"]
            and self.ListOfDevices[nwkid]["Ep"][ep]["ff66"]["0000"]
            not in ("", {})
        ):
            tarif = self.ListOfDevices[nwkid]["Ep"][ep]["ff66"]["0000"]
        if tarif and "BBR" not in tarif:
            return

        # Couleur du Lendemain DEMAIN Trigger Alarm
        if value == "BLAN":
            MajDomoDevice(self, Devices, nwkid, ep, "0009", "20|Tomorrow WHITE day", Attribute_="0001")
        elif value == "BLEU":
            MajDomoDevice(self, Devices, nwkid, ep, "0009", "10|Tomorrow BLUE day", Attribute_="0001")
        elif value == "ROUG":
            MajDomoDevice(self, Devices, nwkid, ep, "0009", "40|Tomorrow RED day", Attribute_="0001")
        else:
            MajDomoDevice(self, Devices, nwkid, ep, "0009", "00|No information", Attribute_="0001")

        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut == "0002":
        # Histo : HHPHC
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut == "0003":
        # Histo : PPOT
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut == "0004":
        # Histo : PEJP
        tarif = None
        if (
            "ff66" in self.ListOfDevices[nwkid]["Ep"][ep]
            and "0000" in self.ListOfDevices[nwkid]["Ep"][ep]["ff66"]
            and self.ListOfDevices[nwkid]["Ep"][ep]["ff66"]["0000"]
            not in ("", {})
        ):
            tarif = self.ListOfDevices[nwkid]["Ep"][ep]["ff66"]["0000"]
        if tarif != "EJP.":
            return

        # PEJP : Preavis début EJP (30 min) Trigger Alarm
        value = int(value)

        if value == 0:
            MajDomoDevice(self, Devices, nwkid, ep, "0009", "00|No information", Attribute_="0001")
        else:
            MajDomoDevice( self, Devices, nwkid, ep, "0009", "40|Mobile peak preannoncement: %s" % value, Attribute_="0001", )

        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut in ("0005", "0006", "0007", "0008"):
        # Histo : ADPS
        # Histo : ADIR1 (Triphasé)
        # Histo : ADIR2 (Triphasé)
        # Histo : ADIR3 (Triphasé)
        # It is understood that the Attribute represent also the Instant Current, so we will update accordingly the P1Meter
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        # Alarm
        if attribut in ["0005", "0006"]:
            _tmpep = "01"
            _tmpattr = "0508"
        elif attribut == "0007":
            _tmpep = "f2"
            _tmpattr = "0908"
        elif attribut == "0008":
            _tmpep = "f3"
            _tmpattr = "0a08"

        if value == 0:
            MajDomoDevice(self, Devices, nwkid, _tmpep, "0009", "00|Normal", Attribute_="0005")
            return

        # value is equal to the Amper over the souscription
        # Issue critical alarm
        MajDomoDevice(self, Devices, nwkid, _tmpep, "0009", "04|Critical", Attribute_="0005")

        # Isse Current on the corresponding Ampere
        MajDomoDevice(self, Devices, nwkid, ep, "0b04", str(value), Attribute_=_tmpattr)

    elif attribut == "0201":
        # Standard : NTARF
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'LTARF', value)
        
    elif attribut in ( "0200", ):
        # Standard : LTARF
        s_tarif = ""
        if "BLEU" in value:
            # HC BLUE
            s_tarif = "B"
        elif "BLAN" in value:
            # HC BLANC
            s_tarif = "W"
        elif "ROUG" in value:
            # HC ROUGE
            s_tarif = "R"
        if "HP" in value:
            s_tarif += "HP"
        elif "HC" in value:
            s_tarif += "HC"

        MajDomoDevice(self, Devices, nwkid, ep, "0009", s_tarif, Attribute_="0020")
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'NTARF', value)
        
    elif attribut in ( "0202", ):
        # Standard : DATE
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'DATE', value)
        
    elif attribut in ( "0203", ):
        # Standard : EASD01
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'EASD01', value)
        
    elif attribut in ( "0204", ):
        # Standard : EASD02
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'EASD02', value)
        
    elif attribut in ( "0205", ):
        # Standard : EASD03
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'EASD03', value)
        
    elif attribut in ( "0206", ):
        # Standard : EASD04
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, 'EASD04', value)
        
    elif attribut in ( "0207", ):
        # Standard : SINSTI (Production)
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut in ( "0208", ):
        # Standard : SMAXIN (Production)
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut in ( "0209", ):
        # Standard : SMAXIN-1 (Production)
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut in ( "0210", ):
        # Standard : CCAIN (Production)
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut in ( "0211", ):
        # Standard : CCAIN-1 (Production)
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut in ( "0212", ):
        # Standard :
        # - SMAXN-1 (Monophasé)
        # - SMAXN1-1 (Triphasé)
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut in ( "0213", ):
        # Standard : SMAXN2-1 (Triphasé)
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut in ( "0214", ):
        # Standard : SMAXN3-1 (Triphasé)
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut in ( "0215", ):
        # Standard : MSG1
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut in ( "0216", ):
        # Standard : MSG2
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)

    elif attribut == "0217":
        # Standard : STGE
        self.log.logging( "ZLinky", "Log", "STGE raw Value: %s" % ( value ))
        try:
            stge = binascii.unhexlify( value ).decode("utf-8")
            self.log.logging( "ZLinky", "Log", "STGE unhexlify Value: %s/%s" % ( value, stge ))
        except Exception as e:
            self.log.logging( "ZLinky", "Log", "STGE Value: %s" % ( value ))
            stge = value

        self.log.logging( "ZLinky", "Log", "STGE decoded %s : %s" % ( stge,  decode_STEG( stge ) ))
        store_ZLinky_infos( self, nwkid, "STGE", decode_STEG( stge ))
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, stge)

    elif attribut in ( "0218", ):
        # Standard : DPM1
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "DPM1", value)

    elif attribut in ( "0219", ):
        # Standard : FPM1
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "FPM1", value)

    elif attribut in ( "0220", ):
        # Standard : DPM2
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "DPM2", value)

    elif attribut in ( "0221", ):
        # Standard : FPM2
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "FPM2", value)

    elif attribut in ( "0222", ):
        # Standard : DPM3
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "DPM3", value)

    elif attribut in ( "0223", ):
        # Standard : FPM3
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "FPM3", value)

    elif attribut in ( "0224", ):
        # Standard : RELAIS
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "RELAIS", value)

    elif attribut in ( "0225", ):
        # Standard : NJOURF
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "NJOURF", value)

    elif attribut in ( "0226", ):
        # Standard : NJOURF+1
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "NJOURF+1", value)

    elif attribut in ( "0227", ):
        # Standard : PJOURF+1
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "PJOURF+1", value)

    elif attribut in ( "0228", ):
        # Standard : PPOINTE1
        checkAndStoreAttributeValue(self, nwkid, ep, cluster, attribut, value)
        store_ZLinky_infos( self, nwkid, "PPOINTE1", value)

    elif attribut == "0300":
        # Linky Mode
        update_zlinky_device_model_if_needed( self, nwkid )