


from DevicesModules.custom_konke import konke_onoff
from DevicesModules.custom_zlinky import zlinky_clusters
from Modules.lumi import lumi_private_cluster
from Modules.zclClusterHelpers import (compute_electrical_measurement_conso,
                                       compute_metering_conso)

FUNCTION_WITH_ACTIONS_MODULE = {
    # Lumi 0xfcc
    "Lumi_fcc0": lumi_private_cluster,

    # ZLinky
    "zlinky_clusters": zlinky_clusters

}
FUNCTION_MODULE = {
    # 0702 helper
    "compute_metering_conso": compute_metering_conso,

    # 0b04 helper
    "compute_electrical_measurement_conso": compute_electrical_measurement_conso,

    # Konke Switch
    "konke_onoff": konke_onoff,
    
}
