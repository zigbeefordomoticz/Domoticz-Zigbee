# Création des devices par le plugin

L'idée est de revoir la création de device et de réduire au maximum les cas particulier dans le code et plutot axer vers un fichier de configuration.

## Principe

1. Node -> Host : Message d'annonce 0x004d
1. Host -> Node : Demande de liste de EndPoint ( 0x0045 )
1. Node -> Host : Reception de la liste des EndPoint 0x8045
1. Host -> Node : Demande de Simple Descriptor pour chaque EndPoint ( 0x0045 )
1. Host -> Node : On pourrait aussi demander le Node Detail Description ( 0x0042 )
1. Node -> Host : Pour chaque EndPoint reception des Clusters dispo pour ce EndPoint ( 0x8045 )
1. Node -> Host : Request ReadAttribute pour chaque Cluster IN ( Du coup on adresse également le cas Xiaomi qui envoie un Cluster 0x0000 )

* Cas des Xiaomi 
Node -> Hosts : Reception d'un message Cluster 0x0000/0x0005 - Model Informationo


## Idée initiale

* Après la phase de découvert on doit disposer des informations suivantes :
  * Model Information ( dans le cas des Xiaomi )
  * ProfileID / ZDeviceID
  * List d'EPs et list de Cluster pour chaque EP


* Nous devrions avoir 3 modes de recherche  dans le fichier DeviceConf.txt. Cela afin d'automatiser la création des devices connus/certifiés par le plugin
  * recherche avec 'Model Name'
  * recherche avec 'Profile ID / ZdeviceID'
  * recherche sur la base d'un Cluster pour Obtenir un Type de Device ( ClusterType ). cela permettrait de créer une serie de devices pour  les produits non encore certifiés/reconnus pas le plugin

  * Pour ces 2 premières recherches nous devrions avoir une et une seules correspondance.
    * ZigBee annonce que le couple ProfileID/ZdeviceID est unique. A priori ce n'est pas le cas Ampoule.LED1622G12.Tradfri et switch.legrand.netamo, qui sont ProfileID 0104 et ZDeviceID 0100

    * Il est donc necessaire d'avoir en dernier recours l'utilisation de la liste EP et Cluster pour avoir une reponse unique


* Pour les devices non connus/certifiés, c'est à dire nouveau ProfileID/ZdeviceID, je suggère que soit alors qu'on implémente un mecanisme à minima de creation de device, par le biais de la liste des Clusters

				Cluster     ->    Device
				0x0006			  Switch ( General On/Off )
				0x0008			  Level Control ( Variateur / Lampe, Volets ... )

* Pour les autres, il nous faut un système qui dans le cas ou le devices n'est pas certifié, génère un dictionnaire des information recoltées le long du process et en fasse un fichier, qui peut nous etre envoyé ou deposé dans github pour traitement


## Process de discovery

| Plugin receive | Plugin send | Purpose | Status | Comments |
|----------------|-------------|---------|--------|----------|
| 0x004d | | Device annoucenement | Implemented | |
| | 0x0045 | Request EndPoint List | Implemented | |
| | 0x0042 | Request Node Descriptor | not implemented | |
| 0x8045 | | List of EndPoint | Implemented | |
| | 0x0043 | Request Active Point for each Ep | Implemented | |
| 0x8043 | | Active Point descriptor by Ep | Implemented | I wonder if we move to 8043 to early as we might not received all EP descriptor |
| 0x8042 | | Node Descriptor | not implemented | |
| 0x0100 | 0x0100 | Read Attribute Request for each In Cluster | not implemented | |


## Structure du fichier DeviceConf.txt

Celle-ci n'est pas compatible avec l'ancienne structure , et je ne pense pas qu'il faille garder cette compatibilité, car nous maitrisons l'ensemble.
Par contre à minima, nous pouvous reprendre la version précédente et la mettre au format nouveau
```

{
'tata.plug':{
	'Epin':{ '01': {'0000':'','Type':'Plug/Power/Alarm'}},
	'Epout':{ '01': {'0000':'','0006':'','Type':'Plug/Power/Alarm'}},
	'MacCap':'80',
	'ProfileID':'0114',
	'ZDeviceID':'0117'},
'toto.plug':{
	'Epin':{ '01': {'0000':'','Type':'Plug/Power/Alarm'}},
	'MacCap':'80',
	'ProfileID':'0114',
	'ZDeviceID':'0117'},
'lumi.plug':{
	'Epin':{
		'01': {'0000':'','000c':'','0006':'','0004':'','0003':'','0010':'','0005':'','000a':'','0001':'','0002':'', 'Type':'Plug'},
		'02': {'000c':'', 'Type':'Power/Meter'}, 
		'03': {'000c':''}, 
		'64': {'000f':''}
	     }, 
	'Epout':{
		'01': {'0000':'','0004':''}, 
		'02': {'000c':'','0200':''}, 
		'03': {'000c':''}, 
		'64': {'000f':'','0200':''}
	     }, 
	'MacCap':'80',
	'ProfileID':'0104',
	'ZDeviceID':'0107'} ,
}
```


### Du coup :
* Le Type global tel que défini aujourd'hui n'existe plus. Il est associé au EP à chaque EP si necessaire

### Avantages :
* Distinguer les clusters In et Out, cela donne la possibilité de faire un ReadAttribute Request sur tout les clusters In lors de la découverte du Device après 0x8043
* ProfileID , ZDeviceID et MacCapa permettent de donner un autre moyen d'acces 


## Considération Implémentation

* z_tools.py

| Fonction | Description |
|----------|-------------|
| getTypesbyModel( Model )                    | search Model in DeviceConf and return a tuple of ( Epin , Type ). If nothing found return '' |
| getTypebyCluster( ClusterIN )              | Return a list of tuples ( epin, Type)  based on the Cluster provided | 
| getModelbyZDeviceID( ZDeviceID, ProfileID) | Search for an entry matching ZDeviceID, if several found de-duplicate with ProfileID. Rreturn entry or '' if still several entries. |
| getEPinbyModel( Model )                    | Return the EPin list for a given Model
| getEPoutbyModel( Model )                   | Return the EPout list for a given Model
| getTypefromList ( Type )		     | En entré c'est un Type au format DeviceConf.txt ( Plug/Power/Meter ), en sortie on retourne une liste de Type ( Plug, Power, Meter )

* z_domoticz.py
  * in CreateDomoDevice

* z_heartbeat.py
  * En remplacement du hardcoding des Device sur secteur

* Mecanique opérationnelle du plugin
  * Avec la séeparation Ep In et Out il sera éégalement necessaire de modifier le code existant pour géerer dans ListOfDevice ces 2 informations. L'idéee etant depouvoir utiliser la liste des Cluster In pour faire des Read Attributes
