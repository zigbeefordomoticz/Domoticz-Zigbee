
from DevicesModules.custom_konke import konke_onoff
from DevicesModules.custom_zlinky import (
    zlinky_ActiveRegisterTierDelivered, zlinky_CurrentSummationDelivered,
    zlinky_CurrentTier1SummationDelivered,
    zlinky_CurrentTier2SummationDelivered,
    zlinky_CurrentTier3SummationDelivered,
    zlinky_CurrentTier4SummationDelivered,
    zlinky_CurrentTier5SummationDelivered,
    zlinky_CurrentTier6SummationDelivered,
    zlinky_CurrentTier7SummationDelivered,
    zlinky_CurrentTier8SummationDelivered,
    zlinky_CurrentTier9SummationDelivered,
    zlinky_CurrentTier10SummationDelivered, zlinky_MeterSerialNumber,
    zlinky_SiteID)

FUNCTION_MODULE = {
    # Konke Switch
    "konke_onoff": konke_onoff,
    
    # ZLinky
    "zlinky_CurrentSummationDelivered": zlinky_CurrentSummationDelivered,
    "zlinky_CurrentSummationDelivered": zlinky_CurrentSummationDelivered,
    "zlinky_ActiveRegisterTierDelivered": zlinky_ActiveRegisterTierDelivered,
    "zlinky_CurrentTier1SummationDelivered": zlinky_CurrentTier1SummationDelivered,
    "zlinky_CurrentTier2SummationDelivered": zlinky_CurrentTier2SummationDelivered,
    "zlinky_CurrentTier3SummationDelivered": zlinky_CurrentTier3SummationDelivered,
    "zlinky_CurrentTier4SummationDelivered": zlinky_CurrentTier4SummationDelivered,
    "zlinky_CurrentTier5SummationDelivered": zlinky_CurrentTier5SummationDelivered,
    "zlinky_CurrentTier6SummationDelivered": zlinky_CurrentTier6SummationDelivered,
    "zlinky_CurrentTier7SummationDelivered": zlinky_CurrentTier7SummationDelivered,
    "zlinky_CurrentTier8SummationDelivered": zlinky_CurrentTier8SummationDelivered,
    "zlinky_CurrentTier9SummationDelivered": zlinky_CurrentTier9SummationDelivered,
    "zlinky_CurrentTier10SummationDelivered": zlinky_CurrentTier10SummationDelivered,
    "zlinky_SiteID": zlinky_SiteID,
    "zlinky_MeterSerialNumber": zlinky_MeterSerialNumber,
}
