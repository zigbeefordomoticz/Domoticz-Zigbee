
from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING, STORE_READ_CONFIGURE_REPORTING

ZLINK_CONF_MODEL = (
    "ZLinky_TIC",
    "ZLinky_TIC-historique-mono" , "ZLinky_TIC-historique-tri",
    "ZLinky_TIC-standard-mono", "ZLinky_TIC-standard-tri",
    "ZLinky_TIC-standard-mono-prod", "ZLinky_TIC-standard-tri-prod"
    )

ZLINKY_MODE = {
    0: { "Mode": ('historique', 'mono'), "Conf": "ZLinky_TIC-historique-mono" },
    1: { "Mode": ('standard', 'mono'), "Conf": "ZLinky_TIC-standard-mono" },
    2: { "Mode": ('historique', 'tri'), "Conf": "ZLinky_TIC-historique-tri" },
    3: { "Mode": ('standard', 'tri'), "Conf": "ZLinky_TIC-standard-tri" },
    5: { "Mode": ('standard', 'mono prod'), "Conf": "ZLinky_TIC-standard-mono-prod" },
    7: { "Mode": ('standard', 'tri prod'), "Conf": "ZLinky_TIC-standard-tri-prod" },
}

ZLINKY_UPGRADE_PATHS = {
    "Linky_TIC": ( 0,1,2,3,5,7),
    "ZLinky_TIC-historique-mono": ( "ZLinky_TIC-standard-mono","ZLinky_TIC-standard-mono-prod", ),
    "ZLinky_TIC-historique-tri": ( "ZLinky_TIC-historique-tri","ZLinky_TIC-standard-tri-prod",),
    "ZLinky_TIC-standard-mono-prod": (),
    "ZLinky_TIC-standard-tri": (),
}
ZLinky_TIC_COMMAND = {
    # Mode Historique
    "0000": "OPTARIF",
    "0001": "DEMAIN",
    "0002": "HHPHC",
    "0003": "PPOT",
    "0004": "PEJP",
    "0005": "ADPS",
    "0006": "ADIR1",
    "0007": "ADIR2",
    "0008": "ADIR3",

    # Mode standard
    "0200": "LTARF",
    "0201": "NTARF",
    "0202": "DATE",
    "0203": "EASD01",
    "0204": "EASD02",
    "0205": "EASD03",
    "0206": "EASD04",
    "0207": "SINSTI",
    "0208": "SMAXIN",
    "0209": "SMAXIN-1",
    "0210": "CCAIN",
    "0211": "CCAIN-1",
    "0212": "SMAXN-1",
    "0213": "SMAXN2-1",
    "0214": "SMAXN3-1",
    "0215": "MSG1",
    "0216": "MSG2",
    "0217": "STGE",
    "0218": "DPM1",
    "0219": "FPM1",
    "0220": "DPM2",
    "0221": "FPM2",
    "0222": "DPM3",
    "0223": "FPM3",
    "0224": "RELAIS",
    "0225": "NJOURF",
    "0226": "NJOURF+1",
    "0227": "PJOURF+1",
    "0228": "PPOINTE1",
    "0300": "PROTOCOL Linky"
}


def linky_mode( self, nwkid ):
    
    if 'ZLinky' not in self.ListOfDevices[ nwkid ]:
        return 
    
    if 'PROTOCOL Linky' not in self.ListOfDevices[ nwkid ]['ZLinky']:
        return
    
    if self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] in ZLINKY_MODE:
        return ZLINKY_MODE[ self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] ]["Mode"]

    return None

def linky_device_conf(self, nwkid):

    if 'ZLinky' not in self.ListOfDevices[ nwkid ]:
        # Let check if we have in the Cluster infos
        if "Ep" not in self.ListOfDevices[ nwkid ]:
            return "ZLinky_TIC"
        if "01" not in self.ListOfDevices[ nwkid ]["Ep"]:
            return "ZLinky_TIC"
        if "ff66" not in self.ListOfDevices[ nwkid ]["Ep"]["01"]:
            return "ZLinky_TIC"
        if "0300" not in self.ListOfDevices[ nwkid ]["Ep"]["01"]["ff66"]:
            return "ZLinky_TIC"
        if self.ListOfDevices[ nwkid ]["Ep"]["01"]["ff66"]["0300"] not in ZLINKY_MODE:
            return "ZLinky_TIC"

        self.log.logging( "Cluster", "Status", "linky_device_conf %s found 0xff66/0x0300: %s" %( nwkid, self.ListOfDevices[ nwkid ]["Ep"]["01"]["ff66"]["0300"] ))

        mode = self.ListOfDevices[ nwkid ]["Ep"]["01"]["ff66"]["0300"]
        return ZLINKY_MODE[ mode ]["Conf"]

    if 'PROTOCOL Linky' not in self.ListOfDevices[ nwkid ]['ZLinky']:
        return "ZLinky_TIC"

    if self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] not in ZLINKY_MODE:
        return "ZLinky_TIC"
    
    self.log.logging( "Cluster", "Status", "linky_device_conf %s found Protocol Linky: %s" %( nwkid, self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] ))


    return ZLINKY_MODE[ self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] ]["Conf"]
    
def linky_upgrade_authorized( current_model, new_model ):

    if current_model in ZLINKY_UPGRADE_PATHS and new_model in ZLINKY_UPGRADE_PATHS[ current_model ]:
        return True
    return False

def update_zlinky_device_model_if_needed( self, nwkid ):
    
    if "Model" not in self.ListOfDevices[ nwkid ]:
        return

    zlinky_conf = linky_device_conf(self, nwkid)

    if self.ListOfDevices[ nwkid ]["Model"] != zlinky_conf:
        if not linky_upgrade_authorized( self.ListOfDevices[ nwkid ]["Model"], zlinky_conf ):
            return

        self.log.logging( "ZLinky", "Status", "Adjusting ZLinky model from %s to %s" %( self.ListOfDevices[ nwkid ]["Model"], zlinky_conf  ))
        
        # Looks like we have to update the Model in order to use the right attributes
        self.ListOfDevices[ nwkid ]["Model"] = zlinky_conf

        # Read Attribute has to be redone from scratch
        if "ReadAttributes" in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid]["ReadAttributes"]

        if 'ZLinky' in self.ListOfDevices[ nwkid ]:
            del self.ListOfDevices[ nwkid ]['ZLinky']

        # Configure Reporting to be done
        if STORE_CONFIGURE_REPORTING in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid][STORE_CONFIGURE_REPORTING]

        if STORE_READ_CONFIGURE_REPORTING in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid][STORE_READ_CONFIGURE_REPORTING]
            
        if self.configureReporting:
            self.configureReporting.check_configuration_reporting_for_device( nwkid, force=True)
            
        if "Heartbeat" in self.ListOfDevices[nwkid]:
            self.ListOfDevices[nwkid]["Heartbeat"] = "-1"

CONTACT_SEC = {
    0: "fermé",
    1: "ouvert"
}
ETAT_CACHE_BORNES = {
    0: "fermé",
    1: "ouvert"
}
FONCTION_PROD_CONSO = {
    0: "consommateur",
    1: "producteur"
}
SENS_ENERGIE = {
    0: "énergie active positive",
    1: "énergie active négative"
}
HORLOGE = {
    0: "horloge correcte",
    1: "horloge en mode dégradée"
}
SORTIE_TIC = {
    0: "mode historique",
    1: "mode standard"
}
SORTIE_EURIDIS = {
    0: "désactivée",
    1: "activée sans sécurité",
    3: "activée avec sécurité"
}
STATUT_CPL = {
    0: "New/Unlock",
    1: "New/Lock",
    3: "Registered"
}
SYNCHRO_CPL = {
    0: "compteur non synchronisé",
    1: "compteur synchronisé"
}
COULEUR = {
    0: "néant",
    1: "Bleu",
    2: "Blanc",
    3: "Rouge"
}
def decode_STEG( stge ):
    # '003A4001'
    # '0b1110100100000000000001'

    stge = int( stge, 16)

    # Decodage Registre Statuts

    # Contact Sec : bit 0
    # Organe de coupure: bits 1 à 3
    # Etat du cache-bornes distributeur: bit 4
    # Surtension sur une des phases: bit 6
    # Dépassement de la puissance de référence bit 7
    # Fonctionnement produ/conso: bit 8
    # Sens de l'énégerie active: bit 9
    # Tarif en cours contrat fourniture: bit 10 à 13
    # Tarif en cours contrat distributeur: bit 14 et 15
    # Mode dégradée de l'horloge: bit 16
    # Etat de sortie tic: bit 17
    # Etat de sortie Euridis: bit 19 et 20
    # Statut du CPL: bit 21 et 22
    # Synchro CPL: bit 23
    # Couleur du jour: bit 24 et 25
    # Couleur du lendemain: bit 26 et 27
    # Préavis points mobiles: bit 28 à 29
    # Pointe mobile: bit 30 et 31
    contact_sec =      ( stge     & 0b00000000000000000000000000000001)
    organe_coupure =   ( stge     & 0b00000000000000000000000000001110) >> 1
    etat_cache_bornes = (stge     & 0b00000000000000000000000000010000) >> 4
    sur_tension =      ( stge     & 0b00000000000000000000000001000000) >> 6
    depassement_puissance = (stge & 0b00000000000000000000000010000000) >> 7
    mode_fonctionnement =(stge    & 0b00000000000000000000000100000000) >> 8
    sens_energie =     ( stge     & 0b00000000000000000000001000000000) >> 9
    tarif_fourniture = ( stge     & 0b00000000000000000011110000000000) >> 10
    tarif_distributeur =(stge     & 0b00000000000000001100000000000000) >> 14
    Mode_horloge =   ( stge       & 0b00000000000000010000000000000000) >> 16
    sortie_tic =     ( stge       & 0b00000000000000100000000000000000) >> 17
    sortie_euridis = ( stge       & 0b00000000000110000000000000000000) >> 19
    status_cpl = ( stge           & 0b00000000011000000000000000000000) >> 21
    synchro_cpl = ( stge          & 0b00000000100000000000000000000000) >> 23
    couleur_jour = ( stge         & 0b00000011000000000000000000000000) >> 24
    couleur_demain = ( stge       & 0b00001100000000000000000000000000) >> 26
    preavis_point_mobile = ( stge & 0b00110000000000000000000000000000) >> 28
    pointe_mobile = ( stge        & 0b11000000000000000000000000000000) >> 30

    if contact_sec in CONTACT_SEC:
        contact_sec = CONTACT_SEC[ contact_sec ]

    if etat_cache_bornes in ETAT_CACHE_BORNES:
        etat_cache_bornes = ETAT_CACHE_BORNES[ etat_cache_bornes ]  

    if mode_fonctionnement in FONCTION_PROD_CONSO:
        mode_fonctionnement = FONCTION_PROD_CONSO[ mode_fonctionnement ]

    if sens_energie in SENS_ENERGIE:
        sens_energie = SENS_ENERGIE[ sens_energie ]

    if Mode_horloge in HORLOGE:
        Mode_horloge = HORLOGE[ Mode_horloge]

    if sortie_tic in SORTIE_TIC:
        sortie_tic = SORTIE_TIC[ sortie_tic ]

    if sortie_euridis in SORTIE_EURIDIS:
        sortie_euridis = SORTIE_EURIDIS[ sortie_euridis ]

    if status_cpl in STATUT_CPL:
        status_cpl = STATUT_CPL[ status_cpl ]

    if synchro_cpl in SYNCHRO_CPL:
        synchro_cpl = SYNCHRO_CPL[ synchro_cpl ]

    if couleur_jour in COULEUR:
        couleur_jour = COULEUR[ couleur_jour]
        
    if couleur_demain in COULEUR:
        couleur_demain = COULEUR[ couleur_demain]
    return {
        'Contact sec ': contact_sec,
        'Organe de coupure ': organe_coupure,
        'État du cache-bornes distributeur': etat_cache_bornes,
        'Surtension sur une des phases ': sur_tension,
        'Dépassement de la puissance de référence': depassement_puissance,
        'Fonctionnement producteur/consommateur': mode_fonctionnement,
        'Sens énergie active ': sens_energie,
        'Tarif en cours sur le contrat fourniture': tarif_fourniture,
        'Tarif en cours sur le contrat distributeur': tarif_distributeur,
        'Mode dégradée horloge': Mode_horloge,
        'État de la sortie télé-information ': sortie_tic,
        'État de la sortie communication': sortie_euridis,
        'Statut du CPL ': status_cpl,
        'Synchronisation CPL ': synchro_cpl,
        'Couleur du jour': couleur_jour,
        'Couleur du lendemain': couleur_demain,
        'Préavis pointes mobiles ': preavis_point_mobile,
        'Pointe mobile ': pointe_mobile,
    }
