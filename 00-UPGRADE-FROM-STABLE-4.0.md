# IMPORTANT - 

If you were running version 4.0 or 4.1-beta of the plugin, you must follow this.
Otherwise, you will start with a Clean plugin database !!!!!

## New Directory Structutre
after the update , you have a new directory structure 
https://github.com/sasu-drooz/Domoticz-Zigate/wiki/Plugin-directory-structure :

 - Classes     
 - Conf
 - Data
 - images
 - Modules
 - Tools
 - www
 - Zdatas

* you MUST move your plugin database ( file DeviceList-xx.txt ) to the Data directory, otherwise when you'll start the plugin it will start with an empty plugin database
* if you want to customize the PluginConf.txt, it is now available on Conf/PluginConf.txt. 

### For example:

1. Stop domoticz
1. Upgrade to the lasted version
   assuming you are on 
   `..../plugins/Domoticz-Zigate`
   `git pull`
   
1. Move the files
   assuming you are still on 
   
   `..../plugins/Domoticz-Zigate`
   `mv DeviceList* Data/`
   
   Here is what the `..../plugins/Domoticz-Zigate` should look like
   
   `ls -l`
   
   ```bash
   -rw-rw-r-- 1 domoticz domoticz  1016 Mar 11 19:38 00-UPGRADE-FROM-STABLE-4.0
   drwxrwxr-x 2 domoticz domoticz  4096 Mar 11 19:38 Classes
   drwxrwxr-x 2 domoticz domoticz  4096 Mar 11 19:38 Conf 
   drwxrwxr-x 2 domoticz domoticz  4096 Mar 11 19:38 Data
   drwxrwxr-x 2 domoticz domoticz  4096 Mar 11 19:38 images
   -rw-rw-r-- 1 domoticz domoticz 35144 Mar  2 20:57 LICENSE.txt
   -rw-rw-r-- 1 domoticz domoticz   203 Mar 11 19:38 MANIFEST.in
   drwxrwxr-x 2 domoticz domoticz  4096 Mar 11 19:38 Modules
   -rw-rw-r-- 1 domoticz domoticz 29686 Mar 11 19:38 plugin.py
   -rw-rw-r-- 1 domoticz domoticz  2415 Mar 11 19:38 readme.md
   -rw-rw-r-- 1 domoticz domoticz 12322 Mar 11 19:38 ReleaseNotes.md
   drwxrwxr-x 2 domoticz domoticz  4096 Mar 11 19:38 Tools
   drwxrwxr-x 3 domoticz domoticz  4096 Mar 11 19:38 www
   drwxrwxr-x 2 domoticz domoticz  4096 Mar  2 20:57 Zdatas
   ```

