# Certfied Devices

## Here are the list of Brand/Manufacturer of certified devices

One directory per brand/manufacturer


## Structutre of the Certified device file

* "Ep" 	List of End Point with list of Cluster for each Ep. Must also contains "Type" with the list of Widget
* "Type" 	 Compatibility, but always be set to ""
* "ProfileID" 	ProfileID in Hexa of the device (Optional)
* "ZDeviceID" 	DeviceID in Hexa of the device (Optional)
* NickName 	(Optional)
* ClusterToBind 	List of Cluster to bind in the right order (Optional)
* ReadAttribute 	List Cluster and for each , list of Attributes to read during polling (Optional)
* ConfigureReporting 	 List of Cluster and for each, list of Attribute and parameters for seting Configure Reporting (Optional)
* GroupMembership       List the Groups the devices must be member of.


### How does it impact the plugin behaviour
The plugin usally behave on a standard/default approach. With the Certified file, you can change the behaviour by:

* Impacting clusters to bind
* What to configure Reporting
* Define a Nickname for specific model


#### Considering ClusterToBind, ReadAttribute, ConfigureReporting
1. If entry do not exist, then the default plugin logic is used.
1. If entry is empty, then no action taken, this means that default is not used and nothing is done
1. If entry exists and not empty, then specific action is the given order will be taken
