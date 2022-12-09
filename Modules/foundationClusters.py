
import json
from os import listdir
from os.path import isdir, isfile, join


def _read_foundation_cluster( self, cluster_filename ):
    with open(cluster_filename, "rt") as handle:
        try:
            return json.load(handle)
        except ValueError as e:
            self.log.logging("FoundationCluster", "Error", "--> JSON FoundationCluster: %s load failed with error: %s" % (cluster_filename, str(e)))

            return None
        except Exception as e:
            self.log.logging("FoundationCluster", "Error", "--> JSON FoundationCluster: %s load general error: %s" % (cluster_filename, str(e)))
            return None
    return None


def load_foundation_cluster(self):

    foundation_cluster_path = self.pluginconf.pluginConf["pluginConfig"] + "Foundation"

    if not isdir(foundation_cluster_path):
        return

    foundation_cluster_definition = [f for f in listdir(foundation_cluster_path) if isfile(join(foundation_cluster_path, f))]

    for cluster_definition in foundation_cluster_definition:
        cluster_filename = str(foundation_cluster_path + "/" + cluster_definition)
        cluster_definition = _read_foundation_cluster( self, cluster_filename )
        
        if cluster_definition is None:
            continue
        
        if "ClusterId" not in cluster_definition:
            continue
        if "Enabled" not in cluster_definition or not cluster_definition["Enabled"]:
            continue
        if cluster_definition[ "ClusterId"] in self.FoundationClusters:
            continue
        
        self.FoundationClusters[ cluster_definition[ "ClusterId"] ] = {
            "Version": cluster_definition[ "Version" ],
            "Attributes": dict( cluster_definition[ "Attributes" ] )
        }
        self.log.logging("FoundationCluster", "Status", " .  Foundation Cluster %s version %s loaded" %( 
            cluster_definition[ "ClusterId"], cluster_definition[ "Version" ]))


    self.log.logging("FoundationCluster", "Debug", "--> Foundation Clusters loaded: %s" % self.FoundationClusters.keys())
    
