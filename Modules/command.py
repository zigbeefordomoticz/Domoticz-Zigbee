#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_command.py

    Description: Implement the onCommand() 

"""

from Modules.actuators import (actuator_off, actuator_on, actuator_setcolor,
                               actuator_setlevel, actuator_stop, actuators)
from Modules.adeo import adeo_fip
from Modules.casaia import (casaia_ac201_fan_control, casaia_setpoint,
                            casaia_swing_OnOff, casaia_system_mode)
from Modules.cmdsDoorLock import cluster0101_lock_door, cluster0101_unlock_door
from Modules.danfoss import danfoss_on_off
from Modules.domoticzAbstractLayer import (
    domo_read_Name, domo_read_nValue_sValue, domo_read_SwitchType_SubType_Type,
    is_dimmable_blind, is_dimmable_light, is_dimmable_switch,
    retreive_widgetid_from_deviceId_unit)
from Modules.domoTools import (RetreiveSignalLvlBattery,
                               RetreiveWidgetTypeList, update_domoticz_widget)
from Modules.fanControl import change_fan_mode
from Modules.ikeaTradfri import ikea_air_purifier_mode
from Modules.legrand_netatmo import cable_connected_mode, legrand_fc40
from Modules.livolo import livolo_OnOff
from Modules.profalux import profalux_MoveToLiftAndTilt, profalux_stop
from Modules.schneider_wiser import (schneider_EHZBRTS_thermoMode,
                                     schneider_hact_fip_mode,
                                     schneider_hact_heater_type,
                                     schneider_set_contract,
                                     schneider_temp_Setcurrent)
from Modules.switchSelectorWidgets import SWITCH_SELECTORS
from Modules.thermostats import thermostat_Mode, thermostat_Setpoint
from Modules.tools import get_deviceconf_parameter_value, str_round
from Modules.tuya import (tuya_curtain_lvl, tuya_curtain_openclose,
                          tuya_dimmer_dimmer, tuya_dimmer_onoff,
                          tuya_energy_onoff, tuya_garage_door_action,
                          tuya_switch_command, tuya_watertimer_command,
                          tuya_window_cover_calibration)
from Modules.tuyaSiren import (tuya_siren2_trigger, tuya_siren_alarm,
                               tuya_siren_humi_alarm, tuya_siren_temp_alarm)
from Modules.tuyaTRV import (tuya_coil_fan_thermostat, tuya_fan_speed,
                             tuya_lidl_set_mode, tuya_trv_brt100_set_mode,
                             tuya_trv_mode, tuya_trv_onoff,
                             tuya_trv_switch_onoff)
from Modules.tuyaTS0601 import ts0601_actuator, ts0601_extract_data_point_infos
from Modules.zigateConsts import (THERMOSTAT_LEVEL_2_MODE,
                                  THERMOSTAT_LEVEL_3_MODE, ZIGATE_EP)

# Matrix between Domoticz Type, Subtype, SwitchType and Plugin DeviceType
# Type, Subtype, Switchtype
DEVICE_SWITCH_MATRIX = {
    ( 242, 1, ): ("ThermoSetpoint", "TempSetCurrent"),
    (241, 2, 7): ("ColorControlRGB",),
    (241, 4, 7): ("ColorControlRGBWW",),
    (241, 7, 7): ("ColorControlFull",),
    (241, 8, 7): ("ColorControlWW",),
    (241, 6, 7): ("ColorControlRGBWZ",),
    (241, 1, 7): ("ColorControlRGBW",),
    (244, 62, 18): ("Switch Selector",),
    (244, 73, 0): ("Switch", "" "LivoloSWL", "LivoloSWR", "SwitchButton", "Water", "Plug"),
    (244, 73, 5): ("Smoke",),
    (244, 73, 7): ("LvlControl",),
    (244, 73, 9): ("Button",),
    (244, 73, 13): ("BSO",),
    (244, 73, 15): ("VenetianInverted", "Venetian"),
    (244, 73, 16): ("BlindInverted", "WindowCovering"),
    (244, 73, 22): ("Vanne", "Curtain"),
    (244, 73, 21): ("VanneInverted", "CurtainInverted")
}

ACTIONATORS = [
    "Switch",
    "Plug",
    "Motion",
    "SwitchAQ2",
    "Smoke",
    "DSwitch",
    "LivoloSWL",
    "LivoloSWR",
    "Toggle",
    "Venetian",
    "VenetianInverted",
    "VanneInverted",
    "Vanne",
    "Curtain",
    "CurtainInverted",
    "WindowCovering",
    "BSO",
    "BSO-Orientation",
    "BSO-Volet",
    "LvlControl",
    "ColorControlRGB",
    "ColorControlWW",
    "ColorControlRGBWW",
    "ColorControlFull",
    "ColorControl",
    "ColorControlRGBWZ",
    "ColorControlRGBW",
    "ThermoSetpoint",
    "ThermoMode",
    "ACMode", "CAC221ACMode",
    "ThermoMode_2",
    "ThermoMode_3",
    "ThermoMode_4",
    "ThermoMode_5",
    "ThermoMode_6",
    "ThermoMode_7",
    "ThermoModeEHZBRTS",
    "AirPurifierMode",
    "FanSpeed",
    "FanControl",
    "PAC-SWITCH",
    "ACMode_2",
    "ACSwing",
    "TempSetCurrent",
    "AlarmWD",
    "FIP",
    "HACTMODE",
    "LegranCableMode",
    "ContractPower",
    "HeatingSwitch",
    "DoorLock",
    "TuyaSiren",
    "TuyaSirenHumi",
    "TuyaSirenTemp",
    "ThermoOnOff",
    "ShutterCalibration",
    "SwitchAlarm",
    "TamperSwitch"
]



def mgtCommand(self, Devices, DeviceID, Unit, Nwkid, Command, Level, Color):
    
    widget_name = domo_read_Name(self, Devices, DeviceID, Unit)

    self.log.logging("Command", "Debug", f"mgtCommand ({Nwkid}) {DeviceID} {Unit} Name: {widget_name} Command: {Command} Level: {Level} Color: {Color}", Nwkid)

    deviceSwitchType, deviceSubType, deviceType = domo_read_SwitchType_SubType_Type(self, Devices, DeviceID, Unit)

    # domoticzType = DEVICE_SWITCH_MATRIX.get((deviceType, deviceSubType, deviceSwitchType))
    # if domoticzType is not None:
    #     self.log.logging("Command", "Debug", f"---------> DeviceType: {domoticzType}", Nwkid)

    SignalLevel, BatteryLevel = RetreiveSignalLvlBattery(self, Nwkid)

    ClusterTypeList = RetreiveWidgetTypeList(self, Devices, DeviceID, Nwkid, Unit)
    if not ClusterTypeList:
        self.log.logging("Command", "Error", f"mgtCommand - no ClusterType found !  {self.ListOfDevices[Nwkid]}")
        return

    self.log.logging("Command", "Debug", f"--------->1 ClusterType founds: {ClusterTypeList} for Unit: {Unit}", Nwkid)

    if len(ClusterTypeList) != 1:
        self.log.logging("Command", "Error", f"mgtCommand - Not Expected. ClusterType: {ClusterTypeList} for Nwkid: {Nwkid}")
        return

    if ClusterTypeList[0][0] == "00":
        EPout = "01"

    EPout, DeviceTypeWidgetId, DeviceType = ClusterTypeList[0]

    self.log.logging("Command", "Debug", f"--------->2 EPOut: {EPout} DeviceType: {DeviceType} WidgetID: {DeviceTypeWidgetId}", Nwkid)

    if Nwkid in self.ListOfDevices and self.ListOfDevices[Nwkid].get("Health") == "Disabled":
        self.log.logging("Command", "Error", f"You tried to action a disabled device: {widget_name}/{Nwkid}", Nwkid)
        return

    forceUpdateDev = False
    if DeviceType in SWITCH_SELECTORS and SWITCH_SELECTORS[DeviceType].get("ForceUpdate"):
        forceUpdateDev = SWITCH_SELECTORS[DeviceType]["ForceUpdate"]
    self.log.logging("Command", "Debug", f"--------->3 forceUpdateDev: {forceUpdateDev}", Nwkid)

    if DeviceType not in ACTIONATORS and not self.pluginconf.pluginConf.get("forcePassiveWidget"):
        self.log.logging("Command", "Log", f"mgtCommand - You are trying to action not allowed for Device: {widget_name} Type: {ClusterTypeList} and DeviceType: {DeviceType} Command: {Command} Level:{Level}", Nwkid)
        return
    
    self.log.logging("Command", "Debug", "---------> Ready to action", Nwkid)

    profalux = self.ListOfDevices[Nwkid].get("Manufacturer") == "1110" and self.ListOfDevices[Nwkid].get("ZDeviceID") in ("0200", "0202")
    self.log.logging("Command", "Debug", f"---------> profalux: {profalux}", Nwkid)

    _model_name = self.ListOfDevices[Nwkid].get("Model", "")
    self.log.logging("Command", "Debug", f"---------> Model Name: {_model_name}", Nwkid)

    health_value = self.ListOfDevices[Nwkid].get("Health")
    if health_value == "Not Reachable":
        self.ListOfDevices[Nwkid]["Health"] = ""
    self.log.logging("Command", "Debug", f"---------> Health: {health_value}", Nwkid)

    if Command == "Stop":
        handle_command_stop(self, Devices, DeviceID, Unit, Nwkid, EPout, DeviceType, _model_name, profalux, BatteryLevel, SignalLevel, forceUpdateDev)

    elif Command in ("Off", "Close"):
        handle_command_off(self, Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, _model_name, profalux, BatteryLevel, SignalLevel, forceUpdateDev)

    elif Command in ("On", "Open"):
        handle_command_on(self, Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, _model_name, profalux, BatteryLevel, SignalLevel, forceUpdateDev)

    elif Command == "Set Level":
        handle_command_setlevel(self, Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, _model_name, profalux, BatteryLevel, SignalLevel, forceUpdateDev)

    elif Command == "Set Color":
        handle_command_setcolor(self, Devices, DeviceID, Unit, Level, Color, Nwkid, EPout, DeviceType, _model_name, profalux, BatteryLevel, SignalLevel, forceUpdateDev)


def get_previous_switch_level(self, Nwkid, Ep):
    
    if Nwkid not in self.ListOfDevices:
        return None
    if Ep not in self.ListOfDevices[ Nwkid ][ 'Ep']:
        return None
    if "0008" not in self.ListOfDevices[ Nwkid ][ 'Ep' ][ Ep]:
        return None
    if "0000" not in self.ListOfDevices[ Nwkid ][ 'Ep' ][ Ep][ "0008" ]:
        return None
    if self.ListOfDevices[ Nwkid ][ 'Ep' ][ Ep][ "0008" ]["0000"] in ( '', {} ):
        return None
    switch_level = self.ListOfDevices[ Nwkid ][ 'Ep' ][ Ep][ "0008" ]["0000"] 
    if switch_level is None:
        return None
    if self.ListOfDevices[ Nwkid ][ 'Ep' ][ Ep][ "0008" ]["0000"] in ( '', {} ):
        return None
    if isinstance( self.ListOfDevices[ Nwkid ][ 'Ep' ][ Ep][ "0008" ]["0000"], str):
        return int( self.ListOfDevices[ Nwkid ][ 'Ep' ][ Ep][ "0008" ]["0000"], 16)
    if isinstance( self.ListOfDevices[ Nwkid ][ 'Ep' ][ Ep][ "0008" ]["0000"], int):
        return self.ListOfDevices[ Nwkid ][ 'Ep' ][ Ep][ "0008" ]["0000"]

    self.log.logging( "Command", "Error", "get_previous_switch_level : level is bizarre >%s<" % (
        self.ListOfDevices[ Nwkid ][ 'Ep' ][ Ep][ "0008" ]["0000"]), Nwkid, )
    return None


def request_read_device_status(self, Nwkid):
    # Purpose is to reset the Heartbeat in order to trigger a readattribute
    
    self.ListOfDevices[Nwkid]["Heartbeat"] = "-1"


def handle_command_stop(self,Devices, DeviceID, Unit, Nwkid, EPout, DeviceType, _model_name, profalux, BatteryLevel, SignalLevel, forceUpdateDev):
    self.log.logging( "Command", "Debug", "mgtCommand : Stop for Device: %s EPout: %s Unit: %s DeviceType: %s" % (Nwkid, EPout, Unit, DeviceType), Nwkid, )

    if DeviceType == "LvlControl" and _model_name == "TS0601-curtain":
        tuya_curtain_openclose(self, Nwkid, EPout, "01")

    elif profalux:
        # Profalux offer a Manufacturer command to make Stop on Cluster 0x0008
        profalux_stop(self, Nwkid)

    elif _model_name in ( "TS0601-_TZE200_nklqjk62", ):
        self.log.logging("Command", "Debug", "mgtCommand : Off for Tuya Garage Door %s" % Nwkid)
        tuya_garage_door_action( self, Nwkid, "02")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

    elif DeviceType in ("WindowCovering", "VenetianInverted", "Venetian", "Vanne", "VanneInverted", "Curtain", "CurtainInverted"): 
        if _model_name in ("PR412", "CPR412", "CPR412-E"):
            profalux_stop(self, Nwkid)
        else:
            # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
            actuator_stop( self, Nwkid, EPout, "WindowCovering")
            #sendZigateCmd(self, "00FA", "02" + Nwkid + ZIGATE_EP + EPout + "02")
            
        if DeviceType in ( "CurtainInverted", "Curtain"):
            # Refresh will be done via the Report Attribute
            return

        update_domoticz_widget(self, Devices, DeviceID, Unit, 17, "0", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
    else:
        actuator_stop( self, Nwkid, EPout, "Light")
        #sendZigateCmd(self, "0083", "02" + Nwkid + ZIGATE_EP + EPout + "02")

    # Let's force a refresh of Attribute in the next Heartbeat
    request_read_device_status(self, Nwkid)


def handle_command_off(self,Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, _model_name, profalux, BatteryLevel, SignalLevel, forceUpdateDev):
    # Let's force a refresh of Attribute in the next Heartbeat
    if DeviceType not in ( "CurtainInverted", "Curtain"):
        # Refresh will be done via the Report Attribute
        request_read_device_status(self, Nwkid)

    self.log.logging(
        "Command",
        "Debug",
        "mgtCommand : Off for Device: %s EPout: %s Unit: %s DeviceType: %s modelName: %s"
        % (Nwkid, EPout, Unit, DeviceType, _model_name),
        Nwkid,
    )

    if _model_name in ( "TS0601-switch", "TS0601-2Gangs-switch", "TS0601-2Gangs-switch", ):
        self.log.logging("Command", "Debug", "mgtCommand : Off for Tuya Switches Gang/EPout: %s" % EPout)
        tuya_switch_command(self, Nwkid, "00", gang=int(EPout, 16))
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return
    
    if _model_name in ( "TS0601-_TZE200_nklqjk62", ):
        self.log.logging("Command", "Debug", "mgtCommand : Off for Tuya Garage Door %s" % Nwkid)
        tuya_garage_door_action( self, Nwkid, "00")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if _model_name == "TS0601-Parkside-Watering-Timer":
        self.log.logging("Command", "Debug", "mgtCommand : On for Tuya ParkSide Water Time")
        if (
            "Param" in self.ListOfDevices[Nwkid]
            and "TimerMode" in self.ListOfDevices[Nwkid]["Param"]
            and self.ListOfDevices[Nwkid]["Param"]["TimerMode"]
        ):
            self.log.logging("Command", "Debug", "mgtCommand : Off for Tuya ParkSide Water Time - Timer Mode")
            tuya_watertimer_command(self, Nwkid, "00", gang=int(EPout, 16))
        else:
            self.log.logging("Command", "Debug", "mgtCommand : Off for Tuya ParkSide Water Time - OnOff Mode")
            actuator_off(self, Nwkid, EPout, "Light")
            #sendZigateCmd(self, "0092", "02" + Nwkid + ZIGATE_EP + EPout + "00")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "SwitchAlarm" and _model_name == "TS0601-_TZE200_t1blo2bj":
        tuya_siren2_trigger(self, Nwkid, '00')
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "SwitchAlarm" and _model_name == "SMSZB-120" and self.iaszonemgt:
        self.iaszonemgt.iaswd_develco_warning(Nwkid, EPout, "00")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "SwitchAlarm" and _model_name == "TS0601-Solar-Siren" and ts0601_extract_data_point_infos( self, _model_name):
        ts0601_actuator(self, Nwkid, "TuyaAlarmSwitch", 0)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return
        
    if DeviceType == "TamperSwitch" and ts0601_extract_data_point_infos( self, _model_name):
        ts0601_actuator(self, Nwkid, "TuyaTamperSwitch", 0)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return
        
    if _model_name in ("TS0601-Energy",):
        tuya_energy_onoff(self, Nwkid, "00")
        # update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off",BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "LivoloSWL":
        livolo_OnOff(self, Nwkid, EPout, "Left", "Off")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "LivoloSWR":
        livolo_OnOff(self, Nwkid, EPout, "Right", "Off")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "DoorLock":
        # Widget Doorlock seems to work in the oposit
        cluster0101_unlock_door(self, Nwkid)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Closed", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        request_read_device_status(self, Nwkid)
        return

    if DeviceType in ("ThermoMode", "ACMode", "ThermoMode_3", "CAC221ACMode"):
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )

        self.log.logging("Command", "Debug", "ThermoMode - requested Level: %s" % Level, Nwkid)
        self.log.logging(
            "Command",
            "Debug",
            " - Set Thermostat Mode to : %s / %s" % (Level, THERMOSTAT_LEVEL_2_MODE[Level]),
            Nwkid,
        )
        thermostat_Mode(self, Nwkid, "Off")
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == ("ThermoMode_2", ):
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        self.log.logging("Command", "Debug", "ThermoMode - requested Level: %s" % Level, Nwkid)
        if ts0601_extract_data_point_infos( self, _model_name):
            ts0601_actuator(self, Nwkid, "TRV7SystemMode", 0)
            return

        tuya_trv_mode(self, Nwkid, 0)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return
    
    if DeviceType in ("ThermoMode_4", "ThermoMode_5", "ThermoMode_6", "ThermoMode_7"):
        self.log.logging( "Command", "Debug", "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
            Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        self.log.logging("Command", "Debug", "ThermoMode - requested Level: %s" % Level, Nwkid)
        
        if DeviceType == "ThermoMode_7" and ts0601_extract_data_point_infos( self, _model_name):
            ts0601_actuator(self, Nwkid, "TRV6SystemMode", 0)
            return

        if _model_name in ( "TS0601-_TZE200_dzuqwsyg", "TS0601-eTRV5"):
            tuya_trv_onoff(self, Nwkid, 0x01)
            update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            return
    
    if DeviceType == "ThermoModeEHZBRTS":
        self.log.logging("Command", "Debug", "MajDomoDevice EHZBRTS Schneider Thermostat Mode Off", Nwkid)
        schneider_EHZBRTS_thermoMode(self, Nwkid, 0)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType in ("ACMode_2", "FanControl"):
        casaia_system_mode(self, Nwkid, "Off")
        return

    if DeviceType == "AirPurifierMode" and _model_name in ('STARKVIND Air purifier', ):
        ikea_air_purifier_mode( self, Nwkid, EPout, 0 )

    if ( DeviceType == "ACSwing" and "Model" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Model"] == "AC201A" ):
        casaia_swing_OnOff(self, Nwkid, "00")
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        return

    if DeviceType == "LvlControl" and _model_name in ("TS0601-dimmer", "TS0601-2Gangs-dimmer"):
        tuya_dimmer_onoff(self, Nwkid, EPout, "00")
        _, cur_sValue = domo_read_nValue_sValue(self, Devices, DeviceID, Unit)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, cur_sValue, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        return

    if DeviceType == "LvlControl" and _model_name == "TS0601-curtain":
        tuya_curtain_openclose(self, Nwkid, "02")

    elif DeviceType == "BSO-Volet" and profalux:
        profalux_MoveToLiftAndTilt(self, Nwkid, level=1)

    elif DeviceType == "TuyaSiren":
        tuya_siren_alarm(self, Nwkid, 0x00)

    elif DeviceType == "TuyaSirenHumi":
        tuya_siren_humi_alarm(self, Nwkid, 0x00)

    elif DeviceType == "TuyaSirenTemp":
        tuya_siren_temp_alarm(self, Nwkid, 0x00)

    elif DeviceType == "WindowCovering":
        actuator_off(self, Nwkid, EPout, "WindowCovering")
        #sendZigateCmd(self, "00FA", "02" + Nwkid + ZIGATE_EP + EPout + "01")  # Blind inverted (On, for Close)

    elif DeviceType in ("VenetianInverted", "VanneInverted", "CurtainInverted"):
        if "Model" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Model"] in ("PR412", "CPR412", "CPR412-E"):
            actuator_on(self, Nwkid, EPout, "Light")
            #sendZigateCmd(self, "0092", "02" + Nwkid + ZIGATE_EP + EPout + "01")
        else:
            actuator_on(self, Nwkid, EPout, "WindowCovering")
            #sendZigateCmd( self, "00FA", "02" + Nwkid + ZIGATE_EP + EPout + "01")  # Venetian Inverted/Blind (On, for Close)
            
        if DeviceType in ( "CurtainInverted", "Curtain"):
            # Refresh will be done via the Report Attribute
            return


    elif DeviceType in ( "Venetian", "Vanne", "Curtain"):
        if "Model" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Model"] in ( "PR412", "CPR412", "CPR412-E"):
            actuator_off(self, Nwkid, EPout, "Light")
            #sendZigateCmd(self, "0092", "02" + Nwkid + ZIGATE_EP + EPout + "00")
        elif (
            DeviceType in ("Vanne", "Curtain",) 
            or "Model" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Model"] in ( "TS130F",)
        ):
            actuator_off(self, Nwkid, EPout, "WindowCovering")
            
        if DeviceType in ( "CurtainInverted", "Curtain"):
            # Refresh will be done via the Report Attribute
            return

        else:
            actuator_on(self, Nwkid, EPout, "WindowCovering")
            #sendZigateCmd(self, "00FA", "02" + Nwkid + ZIGATE_EP + EPout + "00")  # Venetian /Blind (Off, for Close)

    elif DeviceType == "AlarmWD":
        self.iaszonemgt.alarm_off(Nwkid, EPout)

    elif DeviceType == "HeatingSwitch":
        thermostat_Mode(self, Nwkid, "Off")

    elif DeviceType == "ThermoOnOff":
        self.log.logging("Command", "Debug", "ThermoOnOff - requested Off", Nwkid)
        if "Model" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Model"] in ("eTRV0100"):
            danfoss_on_off(self, Nwkid, 0x00)
        else:
            tuya_trv_onoff(self, Nwkid, 0x00)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

    elif DeviceType == "ShutterCalibration":
        self.log.logging("Command", "Debug", "mgtCommand : Disable Window Cover Calibration")
        tuya_window_cover_calibration(self, Nwkid, "01")

    elif DeviceType == "Switch" and ts0601_extract_data_point_infos( self, _model_name):
        ts0601_actuator(self, Nwkid, "switch", 0)

    else:
        # Remaining Slider widget
        if profalux:  # Profalux are define as LvlControl but should be managed as Blind Inverted
            actuator_setlevel(self, Nwkid, EPout, 0, "Light", "0000", withOnOff=False)
            #sendZigateCmd(self, "0081", "02" + Nwkid + ZIGATE_EP + EPout + "01" + "%02X" % 0 + "0000")
        else:
            if (
                "Param" in self.ListOfDevices[Nwkid]
                and "fadingOff" in self.ListOfDevices[Nwkid]["Param"]
                and self.ListOfDevices[Nwkid]["Param"]["fadingOff"]
            ):
                effect = "0000"
                if self.ListOfDevices[Nwkid]["Param"]["fadingOff"] == 1:
                    effect = "0002"  # 50% dim down in 0.8 seconds then fade to off in 12 seconds
                elif self.ListOfDevices[Nwkid]["Param"]["fadingOff"] == 2:
                    effect = "0100"  # 20% dim up in 0.5s then fade to off in 1 second
                elif self.ListOfDevices[Nwkid]["Param"]["fadingOff"] == 255:
                    effect = "0001"  # No fade

                self.log.logging("Command", "Debug", "mgtCommand : %s fading Off effect: %s" % (Nwkid, effect))
                # Increase brightness by 20% (if possible) in 0.5 seconds then fade to off in 1 second (default)
                actuator_off(self, Nwkid, EPout, "Light", effect)
                #sendZigateCmd(self, "0094", "02" + Nwkid + ZIGATE_EP + EPout + effect)
            else:
                actuator_off(self, Nwkid, EPout, "Light")
                #sendZigateCmd(self, "0092", "02" + Nwkid + ZIGATE_EP + EPout + "00")

        # Making a trick for the GLEDOPTO LED STRIP.
        if _model_name == "GLEDOPTO" and EPout == "0a":
            # When switching off the WW channel, make sure to switch Off the RGB channel
            actuator_off(self, Nwkid, "0b", "Light")
            #sendZigateCmd(self, "0092", "02" + Nwkid + ZIGATE_EP + "0b" + "00")

    # Update Devices
    if is_dimmable_blind(self, Devices, DeviceID, Unit):
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "0", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
    else:
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

    # Let's force a refresh of Attribute in the next Heartbeat
    request_read_device_status(self, Nwkid)


def handle_command_on(self,Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, _model_name, profalux, BatteryLevel, SignalLevel, forceUpdateDev):
    # Let's force a refresh of Attribute in the next Heartbeat
    request_read_device_status(self, Nwkid)
    self.log.logging(
        "Command",
        "Debug",
        "mgtCommand : On for Device: %s EPout: %s Unit: %s DeviceType: %s ModelName: %s"
        % (Nwkid, EPout, Unit, DeviceType, _model_name),
        Nwkid,
    )

    if _model_name in ( "TS0601-switch", "TS0601-2Gangs-switch", "TS0601-2Gangs-switch", ):
        self.log.logging("Command", "Debug", "mgtCommand : On for Tuya Switches Gang/EPout: %s" % EPout)

        tuya_switch_command(self, Nwkid, "01", gang=int(EPout, 16))
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "SwitchAlarm" and _model_name == "TS0601-_TZE200_t1blo2bj":
        tuya_siren2_trigger(self, Nwkid, '01')
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return
    
    if DeviceType == "SwitchAlarm" and _model_name == "SMSZB-120" and self.iaszonemgt:
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        self.iaszonemgt.iaswd_develco_warning(Nwkid, EPout, "01")
        return
    
    if DeviceType == "SwitchAlarm" and _model_name == "TS0601-Solar-Siren" and ts0601_extract_data_point_infos( self, _model_name):
        ts0601_actuator(self, Nwkid, "TuyaAlarmSwitch", 1)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "TamperSwitch" and _model_name == "TS0601-Solar-Siren" and ts0601_extract_data_point_infos( self, _model_name):
        ts0601_actuator(self, Nwkid, "TuyaTamperSwitch", 1)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if _model_name in ("TS0601-_TZE200_nklqjk62", ):
        self.log.logging("Command", "Debug", "mgtCommand : On for Tuya Garage Door %s" % Nwkid)
        tuya_garage_door_action( self, Nwkid, "01")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if _model_name == "TS0601-Parkside-Watering-Timer":
        self.log.logging("Command", "Debug", "mgtCommand : On for Tuya ParkSide Water Time")
        if (
            "Param" in self.ListOfDevices[Nwkid]
            and "TimerMode" in self.ListOfDevices[Nwkid]["Param"]
            and self.ListOfDevices[Nwkid]["Param"]["TimerMode"]
        ):
            self.log.logging("Command", "Debug", "mgtCommand : On for Tuya ParkSide Water Time - Timer Mode")
            tuya_watertimer_command(self, Nwkid, "01", gang=int(EPout, 16))
        else:
            self.log.logging("Command", "Debug", "mgtCommand : On for Tuya ParkSide Water Time - OnOff Mode")
            actuator_on(self, Nwkid, EPout, "Light")
            #sendZigateCmd(self, "0092", "02" + Nwkid + ZIGATE_EP + EPout + "01")

    if _model_name in ("TS0601-Energy",):
        tuya_energy_onoff(self, Nwkid, "01")
        # update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On",BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "AirPurifierMode" and _model_name in ('STARKVIND Air purifier', ):
        ikea_air_purifier_mode( self, Nwkid, EPout, 1 )

    if DeviceType == "LivoloSWL":
        livolo_OnOff(self, Nwkid, EPout, "Left", "On")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "LivoloSWR":
        livolo_OnOff(self, Nwkid, EPout, "Right", "On")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "DoorLock":
        cluster0101_lock_door(self, Nwkid)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "Open", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        self.ListOfDevices[Nwkid]["Heartbeat"] = 0
        return

    if DeviceType == "LvlControl" and _model_name in ("TS0601-dimmer", "TS0601-2Gangs-dimmer"):
        tuya_dimmer_onoff(self, Nwkid, EPout, "01")
        _, cur_sValue = domo_read_nValue_sValue(self, Devices, DeviceID, Unit)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, cur_sValue, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "LvlControl" and _model_name == "TS0601-curtain":
        tuya_curtain_openclose(self, Nwkid, "00")

    elif DeviceType == "BSO-Volet" and profalux:
        # On translated into a Move to 254
        profalux_MoveToLiftAndTilt(self, Nwkid, level=255)

    elif DeviceType == "WindowCovering":
        # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
        actuator_on(self, Nwkid, EPout, "WindowCovering")
        #sendZigateCmd(self, "00FA", "02" + Nwkid + ZIGATE_EP + EPout + "00")  # Blind inverted (Off, for Open)

    elif DeviceType in ("VenetianInverted", "VanneInverted", "CurtainInverted"):
        if "Model" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Model"] in ("PR412", "CPR412", "CPR412-E"):
            actuator_off(self, Nwkid, EPout, "Light")
        else:
            actuator_off(self, Nwkid, EPout, "WindowCovering")
            
        if DeviceType in ( "CurtainInverted", "Curtain"):
            # Refresh will be done via the Report Attribute
            return

    elif DeviceType in ("Venetian", "Vanne", "Curtain"):
        if "Model" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Model"] in ("PR412", "CPR412", "CPR412-E"):
            actuator_on(self, Nwkid, EPout, "Light")
            #sendZigateCmd(self, "0092", "02" + Nwkid + ZIGATE_EP + EPout + "01")    
                
        elif DeviceType in ( "Vanne", "Curtain",) or "Model" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Model"] in ( "TS130F",):
            actuator_on(self, Nwkid, EPout, "WindowCovering")

        else:
            actuator_off(self, Nwkid, EPout, "WindowCovering")
            #sendZigateCmd(self, "00FA", "02" + Nwkid + ZIGATE_EP + EPout + "01")  # Venetian/Blind (On, for Open)
            
        if DeviceType in ( "CurtainInverted", "Curtain"):
            # Refresh will be done via the Report Attribute
            return

    elif DeviceType == "HeatingSwitch":
        thermostat_Mode(self, Nwkid, "Heat")

    elif DeviceType == "ThermoOnOff":
        if "Model" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Model"] in ("eTRV0100"):
            danfoss_on_off(self, Nwkid, 0x01)
        else:
            tuya_trv_onoff(self, Nwkid, 0x01)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

    elif DeviceType == "ShutterCalibration":
        self.log.logging("Command", "Debug", "mgtCommand : Enable Window Cover Calibration")
        tuya_window_cover_calibration(self, Nwkid, "00")

    elif DeviceType == "Switch" and ts0601_extract_data_point_infos( self, _model_name):
        ts0601_actuator(self, Nwkid, "switch", 1)

    else:
        # Remaining Slider widget
        if profalux:
            actuator_setlevel(self, Nwkid, EPout, 255, "Light", "0000", withOnOff=False)
            #sendZigateCmd(self, "0081", "02" + Nwkid + ZIGATE_EP + EPout + "01" + "%02X" % 255 + "0000")
        else:
            actuator_on(self, Nwkid, EPout, "Light")
            #sendZigateCmd(self, "0092", "02" + Nwkid + ZIGATE_EP + EPout + "01")

    if is_dimmable_blind(self, Devices, DeviceID, Unit):
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "100", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
    else:
        previous_level = get_previous_switch_level(self, Nwkid, EPout)
        self.log.logging( "Command", "Debug", "mgtCommand : Previous Level was %s" % (
            previous_level), Nwkid, )

        if previous_level is None:
            update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            
        elif is_dimmable_light(self, Devices, DeviceID, Unit):
            percentage_level = int(( (previous_level * 100 )/ 255))
            self.log.logging( "Command", "Debug", "mgtCommand : Previous Level was %s" %previous_level)
            update_domoticz_widget(self, Devices, DeviceID, Unit, 1, str(percentage_level), BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            
        else:
            percentage_level = int(( (previous_level * 100 )/ 255))
            self.log.logging( "Command", "Debug", "mgtCommand : Previous Level was %s" %(previous_level,))
            update_domoticz_widget(self, Devices, DeviceID, Unit, 2, str(percentage_level), BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            
    # Let's force a refresh of Attribute in the next Heartbeat
    self.log.logging( "Command", "Debug", "mgtCommand : request_read_device_status()")
    request_read_device_status(self, Nwkid)


def handle_command_setlevel(self,Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, _model_name, profalux, BatteryLevel, SignalLevel, forceUpdateDev):       
    # Level is normally an integer but may be a floating point number if the Unit is linked to a thermostat device
    # There is too, move max level, mode = 00/01 for 0%/100%
    self.log.logging( "Command", "Debug", "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
        Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )

    if DeviceType == "ThermoSetpoint":
        self.log.logging( "Command", "Debug", "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        value = int(float(Level) * 100)
        thermostat_Setpoint(self, Nwkid, value)
        Level = round(float(Level), 2)
        # Normalize SetPoint value with 2 digits
        Level = str_round(float(Level), 2)  # 2 decimals
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, str(Level), BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "TempSetCurrent":
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Temp for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        value = int(float(Level) * 100)
        schneider_temp_Setcurrent(self, Nwkid, value)
        Level = round(float(Level), 2)
        # Normalize SetPoint value with 2 digits
        Level = str_round(float(Level), 2)  # 2 decimals
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, str(Level), BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "ThermoModeEHZBRTS":
        self.log.logging("Command", "Debug", "MajDomoDevice EHZBRTS Schneider Thermostat Mode %s" % Level, Nwkid)
        schneider_EHZBRTS_thermoMode(self, Nwkid, Level)
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "HACTMODE":
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for HACT Mode: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        if "Schneider Wiser" not in self.ListOfDevices[Nwkid]:
            self.ListOfDevices[Nwkid]["Schneider Wiser"] = {}

        if "HACT Mode" not in self.ListOfDevices[Nwkid]["Schneider Wiser"]:
            self.ListOfDevices[Nwkid]["Schneider Wiser"]["HACT Mode"] = ""

        if Level == 10:  # Conventional
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
            self.ListOfDevices[Nwkid]["Schneider Wiser"]["HACT Mode"] = "conventional"
            schneider_hact_heater_type(self, Nwkid, "conventional")

        elif Level == 20:  # fip
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
            self.ListOfDevices[Nwkid]["Schneider Wiser"]["HACT Mode"] = "FIP"
            schneider_hact_heater_type(self, Nwkid, "fip")

        else:
            self.log.logging("Command", "Error", "Unknown mode %s for HACTMODE for device %s" % (Level, Nwkid))

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "LegranCableMode":
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for Legrand Cable Mode: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        cable_connected_mode(self, Nwkid, str(Level))
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "ContractPower":
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for ContractPower Mode: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        CONTRACT_MODE = {
            10: 3,
            20: 6,
            30: 9,
            40: 12,
            50: 15,
        }
        if "Schneider Wiser" not in self.ListOfDevices[Nwkid]:
            self.ListOfDevices[Nwkid]["Schneider Wiser"] = {}

        if Level in CONTRACT_MODE:
            self.log.logging(
                "Command",
                "Debug",
                "mgtCommand : -----> Contract Power : %s - %s KVA" % (Level, CONTRACT_MODE[Level]),
                Nwkid,
            )
            if (
                "Model" in self.ListOfDevices[Nwkid]
                and self.ListOfDevices[Nwkid]["Model"] == "EH-ZB-BMS"
            ):
                self.ListOfDevices[Nwkid]["Schneider Wiser"]["Contract Power"] = CONTRACT_MODE[Level]
                schneider_set_contract(self, Nwkid, EPout, CONTRACT_MODE[Level])
                update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev, )

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "FIP":
        FIL_PILOT_MODE = {
            10: "Confort",
            20: "Confort -1",
            30: "Confort -2",
            40: "Eco",
            50: "Frost Protection",
            60: "Off",
        }
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for FIP: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        if "Schneider Wiser" not in self.ListOfDevices[Nwkid]:
            self.ListOfDevices[Nwkid]["Schneider Wiser"] = {}

        if ( Level in FIL_PILOT_MODE and _model_name ):
            if _model_name == "EH-ZB-HACT":
                self.log.logging( "Command", "Debug","mgtCommand : -----> HACT -> Fil Pilote mode: %s - %s" % (
                    Level, FIL_PILOT_MODE[Level]),Nwkid, )
                self.ListOfDevices[Nwkid]["Schneider Wiser"]["HACT FIP Mode"] = FIL_PILOT_MODE[Level]
                schneider_hact_fip_mode(self, Nwkid, FIL_PILOT_MODE[Level])
                update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev, )

            elif _model_name == "Cable outlet":
                self.log.logging( "Command", "Debug", "mgtCommand : -----> Fil Pilote mode: %s - %s" % (
                    Level, FIL_PILOT_MODE[Level]), Nwkid, )
                legrand_fc40(self, Nwkid, FIL_PILOT_MODE[Level])
                update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev, )

            elif _model_name in ( "SIN-4-FP-21_EQU", "SIN-4-FP-21"):
                ADEO_FIP_ONOFF_COMMAND = {
                    10: 1,
                    20: 4,
                    30: 5,
                    40: 2,
                    50: 3,
                    60: 0,
                    }
                self.log.logging( "Command", "Log", "mgtCommand : -----> Adeo/Nodon/Enky Fil Pilote mode: %s - %s" % (
                    Level, ADEO_FIP_ONOFF_COMMAND[Level]), Nwkid, )

                adeo_fip(self, Nwkid, EPout, ADEO_FIP_ONOFF_COMMAND[ Level ])
                update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev, )

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType in ("ThermoMode_3", ): 
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        self.log.logging("Command", "Debug", "ThermoMode_3 (Acova) - requested Level: %s" % Level, Nwkid)
        if Level in THERMOSTAT_LEVEL_3_MODE:
            self.log.logging(
                "Command",
                "Debug",
                " - Set Thermostat Mode to : %s / T2:%s " % (Level, THERMOSTAT_LEVEL_3_MODE[Level]),
                Nwkid,
            )

            thermostat_Mode(self, Nwkid, THERMOSTAT_LEVEL_3_MODE[Level])
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType in ("ThermoMode", ):
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        self.log.logging("Command", "Debug", "ThermoMode - requested Level: %s" % Level, Nwkid)
        if Level in THERMOSTAT_LEVEL_2_MODE:
            self.log.logging(
                "Command",
                "Debug",
                " - Set Thermostat Mode to : %s / %s" % (Level, THERMOSTAT_LEVEL_2_MODE[Level]),
                Nwkid,
            )
            thermostat_Mode(self, Nwkid, THERMOSTAT_LEVEL_2_MODE[Level])
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "ACMode":
        ACLEVEL_TO_MODE = {
            0: "Off",
            10: "Cool",
            20: "Heat",
            30: "Dry",
            40: "Fan Only",
        }
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        self.log.logging("Command", "Debug", "ThermoMode - requested Level: %s" % Level, Nwkid)
        if Level in ACLEVEL_TO_MODE:
            self.log.logging(
                "Command", "Debug", " - Set Thermostat Mode to : %s / %s" % (Level, ACLEVEL_TO_MODE[Level]), Nwkid
            )
            thermostat_Mode(self, Nwkid, ACLEVEL_TO_MODE[Level])
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "CAC221ACMode":
        CAC221ACLevel_TO_MODE = {
            0: "Off",
            10: "Auto",
            20: "Cool",
            30: "Heat",
            40: "Dry",
            50: "Fan Only",
        }
        self.log.logging( "Command", "Debug", "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        self.log.logging("Command", "Debug", "ThermoMode - requested Level: %s" % Level, Nwkid)
        if Level in CAC221ACLevel_TO_MODE:
            self.log.logging( "Command", "Debug", " - Set Thermostat Mode to : %s / %s" % (Level, CAC221ACLevel_TO_MODE[Level]), Nwkid )
            thermostat_Mode(self, Nwkid, CAC221ACLevel_TO_MODE[Level])
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return
                    
    if DeviceType == "ThermoMode_2":
        self.log.logging( "Command", "Debug", "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        self.log.logging("Command", "Debug", "ThermoMode_2 - requested Level: %s" % Level, Nwkid)
        if ts0601_extract_data_point_infos( self, _model_name):
            ts0601_actuator(self, Nwkid, "TRV7SystemMode", int(Level // 10))
            return

        tuya_trv_mode(self, Nwkid, Level)
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level // 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        return

    if DeviceType == "ThermoMode_4":
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        
        if _model_name == "TS0601-_TZE200_b6wax7g0":
            self.log.logging("Command", "Debug", "ThermoMode_4 - requested Level: %s" % Level, Nwkid)
            # 0x00 - Auto, 0x01 - Manual, 0x02 - Temp Hand, 0x03 - Holliday   
            tuya_trv_brt100_set_mode(self, Nwkid, int(Level / 10) - 1)
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level / 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            return

    if DeviceType == "ThermoMode_7" and ts0601_extract_data_point_infos( self, _model_name):
        ts0601_actuator(self, Nwkid, "TRV6SystemMode", int(Level // 10))
        return

    if DeviceType in ("ThermoMode_5", "ThermoMode_6"):
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        
        if _model_name == "TS0601-_TZE200_chyvmhay":
            # 1: // manual 2: // away 0: // auto
            tuya_lidl_set_mode( self, Nwkid, int(Level / 10) - 1 )
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level / 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            
        elif _model_name == "TS0601-_TZE200_dzuqwsyg":
            tuya_trv_onoff(self, Nwkid, 0x01)

            tuya_coil_fan_thermostat(self, Nwkid, int(Level / 10) - 1)
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level / 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            
        elif _model_name == "TS0601-eTRV5":
            # "fr-FR": {"LevelNames": "Arrêt|Auto|Manual|Away"}},
            # Off: 00 -> Will get Command Off, so not here
            # Auto:10 -> 00 [0] Scheduled/auto 
            # Manual:20 --> 01 [1] manual 
            # Away:30 -> 02 [2] Holiday

            if Level >= 10:
                self.log.logging( "Command", "Debug", "   Selector: %s" % ( Level ), Nwkid,)
                _tuya_mode = ( Level - 10 )
                self.log.logging( "Command", "Debug", "   Selector: %s translated into Mode: %s" % ( Level, _tuya_mode ), Nwkid,)
                tuya_trv_mode(self, Nwkid, _tuya_mode)
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level // 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
            return
            
    if DeviceType == "AirPurifierMode" and _model_name in ('STARKVIND Air purifier', ):
        self.log.logging( "Command", "Debug", "   Air Purifier Mode: %s" % ( Level ), Nwkid,)
        
        if Level == 10:
            ikea_air_purifier_mode( self, Nwkid, EPout, 1 )
        elif Level in ( 20, 30, 40, 50, 60):
            mode = Level - 10
            ikea_air_purifier_mode( self, Nwkid, EPout, mode)
        
    if DeviceType == "FanControl":
        _set_level_fan_control(self, Devices, DeviceID, Unit, BatteryLevel, SignalLevel, forceUpdateDev, DeviceType, Nwkid, EPout, Level, _model_name)

    if DeviceType == "ACSwing":
        if Level == 10:
            casaia_swing_OnOff(self, Nwkid, "01")
        return

    if DeviceType == "ACMode_2":
        _set_level_acmode_2(self, Nwkid, EPout, Level)
        return

    if DeviceType == "BSO-Volet":
        if profalux:
            # Transform slider % into analog value
            lift = min(max((255 * Level) // 100, 1), 255)

            self.log.logging(
                "Command",
                "Debug",
                f"mgtCommand : profalux_MoveToLiftAndTilt: {Nwkid} BSO-Volet Lift: Level: {Level} Lift: {lift}",
                Nwkid,
            )
            profalux_MoveToLiftAndTilt(self, Nwkid, level=lift)

    elif DeviceType == "BSO-Orientation":
        if profalux:
            Tilt = Level - 10
            self.log.logging(
                "Command",
                "Debug",
                f"mgtCommand : profalux_MoveToLiftAndTilt: {Nwkid} BSO-Orientation : Level: {Level} Tilt: {Tilt}",
                Nwkid,
            )
            profalux_MoveToLiftAndTilt(self, Nwkid, tilt=Tilt)

    elif DeviceType in ( "WindowCovering", "Venetian", "Vanne", "Curtain", "VenetianInverted", "VanneInverted", "CurtainInverted"):
        _set_level_windows_covering(self, DeviceType, Nwkid, EPout, Level)

    elif DeviceType == "AlarmWD":
        _set_level_alarm_wd(self, Nwkid, EPout, Level)

    elif DeviceType == "TuyaSiren":
        _set_level_tuya_siren(self, Nwkid, EPout, Level)

    elif DeviceType == "TuyaSirenHumi":
        if Level == 10:
            tuya_siren_humi_alarm(self, Nwkid, 0x01)

    elif DeviceType == "TuyaSirenTemp":
        if Level == 10:
            tuya_siren_temp_alarm(self, Nwkid, 0x01)

    elif DeviceType == "Toggle":
        _set_level_device_toggle(self, Nwkid, EPout, Level)

    elif _model_name in ("TS0601-dimmer", "TS0601-2Gangs-dimmer"):
        cur_nValue, _ = domo_read_nValue_sValue(self, Devices, DeviceID, Unit)
        if cur_nValue == 0:
            tuya_dimmer_onoff(self, Nwkid, EPout, "01")
        Level = max(Level, 1)
        tuya_dimmer_dimmer(self, Nwkid, EPout, Level)

    elif _model_name == "TS0601-curtain":
        tuya_curtain_lvl(self, Nwkid, (Level))

    elif profalux:
        actuator_setlevel(self, Nwkid, EPout, Level, "Light", "0000", withOnOff=False)

    else:
        if Level > 1 and get_deviceconf_parameter_value(self, _model_name, "ForceSwitchOnformoveToLevel", return_default=False):
            actuator_on(self, Nwkid, EPout, "Light")

        transitionMoveLevel = self.ListOfDevices[Nwkid].get("Param", {}).get("moveToLevel", "0010")
        actuator_setlevel(self, Nwkid, EPout, Level, "Light", transitionMoveLevel, withOnOff=True)

    # Domoticz widget update
    if is_dimmable_blind(self, Devices, DeviceID, Unit) and Level in ( 0, 50, 100):
        if Level == 0:
            update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "0", BatteryLevel, SignalLevel)
        
        elif Level == 100:
            update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "1", BatteryLevel, SignalLevel)
        
        elif Level == 50:
            update_domoticz_widget(self, Devices, DeviceID, Unit, 17, "0", BatteryLevel, SignalLevel)
        
    else:
        partially_opened_nValue = is_dimmable_blind(self, Devices, DeviceID, Unit) or is_dimmable_light(self, Devices, DeviceID, Unit) or is_dimmable_switch(self, Devices, DeviceID, Unit)
        update_domoticz_widget(self, Devices, DeviceID, Unit, partially_opened_nValue, str(Level), BatteryLevel, SignalLevel)

    # Let's force a refresh of Attribute in the next Heartbeat
    request_read_device_status(self, Nwkid)


def _set_level_fan_control(self, Devices, DeviceID, Unit, BatteryLevel, SignalLevel, forceUpdateDev, DeviceType, Nwkid, EPout, Level, _model_name):
    if _model_name == "AC201A":
        casaia_ac201_fan_control(self, Nwkid, Level)
        return

    if _model_name == "TS0601-_TZE200_dzuqwsyg":
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Fan Control: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )

        FAN_SPEED_MAPPING = {
            10: 0x03,
            20: 0x00,
            30: 0x01,
            40: 0x02,
        }
        if Level in FAN_SPEED_MAPPING:
            tuya_fan_speed(self, Nwkid, FAN_SPEED_MAPPING[ Level ])
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level / 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            return 
        
        self.log.logging(
            "Command",
            "Debug",
            "mgtCommand : Fan Control not expected Level : %s EPout: %s Unit: %s DeviceType: %s Level: %s "
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        
    FAN_MODE = {
        0: "Off",
        20: "Low",
        30: "Medium",
        40: "High",
        10: "Auto",
    }

    if Level in FAN_MODE:
        change_fan_mode(self, Nwkid, EPout, FAN_MODE[Level])
    request_read_device_status(self, Nwkid)


def _set_level_acmode_2(self, Nwkid, EPout, Level):
    if Level == 10:
        casaia_system_mode(self, Nwkid, "Cool")
    elif Level == 20:
        casaia_system_mode(self, Nwkid, "Heat")
    elif Level == 30:
        casaia_system_mode(self, Nwkid, "Dry")
    elif Level == 40:
        casaia_system_mode(self, Nwkid, "Fan")


def _set_level_windows_covering(self, DeviceType, Nwkid, EPout, Level):
    if DeviceType in ("WindowCovering", "Venetian", "Vanne", "Curtain"):
        Level = min(max(Level, 1), 99)
    elif DeviceType in ("VenetianInverted", "VanneInverted", "CurtainInverted"):
        Level = min(max(100 - Level, 1), 99)

    value = "%02x" % Level
    if DeviceType == "WindowCovering":
        log_message = f"WindowCovering - Lift Percentage Command - {Nwkid}/{EPout} Level: 0x{value} {Level}"
    else:
        log_message = (
            f"Venetian blind - Lift Percentage Command - {Nwkid}/{EPout} Level: 0x{value} {Level}"
        )
        if DeviceType in ("VenetianInverted", "VanneInverted", "CurtainInverted"):
            log_message = (
                f"VenetianInverted blind - Lift Percentage Command - {Nwkid}/{EPout} Level: 0x{value} {Level}"
            )

    self.log.logging("Command", "Debug", log_message, Nwkid)
    actuator_setlevel(self, Nwkid, EPout, Level, "WindowCovering")

    if DeviceType in ("CurtainInverted", "Curtain"):
        # Refresh will be done via the Report Attribute
        return


def _set_level_alarm_wd(self, Nwkid, EPout, Level):
    self.log.logging("Command", "Debug", "Alarm WarningDevice - value: %s" % Level)
    if Level == 0:  # Stop
        self.iaszonemgt.alarm_off(Nwkid, EPout)
    elif Level == 10:  # Alarm
        self.iaszonemgt.alarm_on(Nwkid, EPout)
    elif Level == 20:  # Siren Only
        self.iaszonemgt.siren_only(Nwkid, EPout)
    elif Level == 30:  # Strobe Only
        self.iaszonemgt.strobe_only(Nwkid, EPout)
    elif Level == 40:  # Armed - Squawk
        self.iaszonemgt.write_IAS_WD_Squawk(Nwkid, EPout, "armed")
    elif Level == 50:  # Disarmed
        self.iaszonemgt.write_IAS_WD_Squawk(Nwkid, EPout, "disarmed")

   
def _set_level_tuya_siren(self, Nwkid, EPout, Level):
    if Level == 10:
        tuya_siren_alarm(self, Nwkid, 0x01, 1)
    elif Level == 20:
        tuya_siren_alarm(self, Nwkid, 0x01, 2)
    elif Level == 30:
        tuya_siren_alarm(self, Nwkid, 0x01, 3)
    elif Level == 40:
        tuya_siren_alarm(self, Nwkid, 0x01, 4)
    elif Level == 50:
        tuya_siren_alarm(self, Nwkid, 0x01, 5)
    

def _set_level_device_toggle(self, Nwkid, EPout, Level):
    self.log.logging("Command", "Debug", "Toggle switch - value: %s" % Level)
    if Level == 10:  # Off
        actuators(self, Nwkid, EPout, "Off", "Switch")
    elif Level == 20:  # On
        actuators(self, Nwkid, EPout, "On", "Switch")
    elif Level == 30:  # Toggle
        actuators(self, Nwkid, EPout, "Toggle", "Switch")

  
def handle_command_setcolor(self,Devices, DeviceID, Unit, Level, Color, Nwkid, EPout, DeviceType, _model_name, profalux, BatteryLevel, SignalLevel, forceUpdateDev):    

    self.log.logging( "Command", "Debug", "mgtCommand : Set Color for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s Color: %s" % (
        Nwkid, EPout, Unit, DeviceType, Level, Color), Nwkid,
    )
    
    actuator_setcolor(self, Nwkid, EPout, Level, Color)
    request_read_device_status(self, Nwkid)

    update_domoticz_widget(self, Devices, DeviceID, Unit, 1, str(Level), BatteryLevel, SignalLevel, str(Color))
