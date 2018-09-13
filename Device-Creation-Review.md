# Création des devices par le plugin

L'idée est de revoir la création de device et de réduire au maximum les cas particulier dans le code et plutot axer vers un fichier de configuration.

## Principe

1. Node -> Host : Message d'annonce 0x004d
1. Host -> Node : Demande de liste de EndPoint ( 0x0045 )
1. Node -> Host : Reception de la liste des EndPoint 0x8045
1. Host -> Node : Demande de Simple Descriptor pour chaque EndPoint ( 0x0045 )
1. Host -> Node : On pourrait aussi demander le Node Detail Description ( 0x0042 )
1. Node -> Host : Pour chaque EndPoint reception des Clusters dispo pour ce EndPoint ( 0x8045 )

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

  * Pour ces 2 recherches nous devrions avoir une et une seules correspondance.
    * ZigBee annonce que le couple ProfileID/ZdeviceID est unique. A priori ce n'est pas le cas Ampoule.LED1622G12.Tradfri et switch.legrand.netamo, qui sont ProfileID 0104 et ZDeviceID 0100

    * Il est donc necessaire d'avoir en dernier recours l'utilisation de la liste EP et Cluster pour avoir une reponse unique


* Pour les devices non connus/certifiés, c'est à dire nouveau ProfileID/ZdeviceID, je suggère que soit alors qu'on implémente un mecanisme à minima de creation de device, par le biais de la liste des Clusters

				Cluster     ->    Device
				0x0006			  Switch ( General On/Off )
				0x0008			  Level Control ( Variateur / Lampe, Volets ... )

* Pour les autres, il nous faut un système qui dans le cas ou le devices n'est pas certifié, génère un dictionnaire des information recoltées le long du process et en fasse un fichier, qui peut nous etre envoyé ou deposé dans github pour traitement

