#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license


"""
    Module: z_command.py

    Description: Implement the onCommand() 

"""

from Modules.actuators import (actuator_off, actuator_on, actuator_setcolor,
                               actuator_setlevel, actuator_stop, actuators)
from Modules.adeo import adeo_fip
from Modules.casaia import (casaia_ac201_fan_control, casaia_swing_OnOff,
                            casaia_system_mode)
from Modules.cmdsDoorLock import cluster0101_lock_door, cluster0101_unlock_door
from Modules.danfoss import danfoss_on_off
from Modules.domoticzAbstractLayer import (domo_read_Name,
                                           domo_read_nValue_sValue,
                                           is_dimmable_blind,
                                           is_dimmable_light,
                                           is_dimmable_switch)
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
from Modules.tools import get_deviceconf_parameter_value
from Modules.tuya import (tuya_curtain_lvl, tuya_curtain_openclose,
                          tuya_dimmer_dimmer, tuya_dimmer_onoff,
                          tuya_energy_onoff, tuya_garage_door_action,
                          tuya_polling_control, tuya_switch_command,
                          tuya_watertimer_command,
                          tuya_window_cover_calibration)
from Modules.tuyaSiren import (tuya_siren2_trigger, tuya_siren_alarm,
                               tuya_siren_humi_alarm, tuya_siren_temp_alarm)
from Modules.tuyaTRV import (tuya_coil_fan_thermostat, tuya_fan_speed,
                             tuya_lidl_set_mode, tuya_trv_brt100_set_mode,
                             tuya_trv_mode, tuya_trv_onoff)
from Modules.tuyaTS0601 import (ts0601_actuator,
                                ts0601_curtain_accurate_calibration_cmd,
                                ts0601_extract_data_point_infos)
from Modules.zigateConsts import (THERMOSTAT_LEVEL_2_MODE,
                                  THERMOSTAT_LEVEL_3_MODE)

# Matrix between Domoticz Type, Subtype, SwitchType and Plugin DeviceType
# Type, Subtype, Switchtype
DEVICE_SWITCH_MATRIX = {
    (242, 1, ): ("ThermoSetpoint", "TempSetCurrent"),
    (241, 2, 7): ("ColorControlRGB",),
    (241, 4, 7): ("ColorControlRGBWW",),
    (241, 7, 7): ("ColorControlFull",),
    (241, 8, 7): ("ColorControlWW",),
    (241, 6, 7): ("ColorControlRGBWZ",),
    (241, 1, 7): ("ColorControlRGBW",),
    (244, 62, 18): ("Switch Selector",),
    (244, 73, 0): ("Switch", "" "LivoloSWL", "LivoloSWR", "SwitchButton", "Water", "Plug"),
    (244, 73, 3): ("WindowCovering",),
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
    "ThermoMode_8",
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
    "SwitchCalibration",
    "TamperSwitch",
    "PollingControl",
    "PollingControlV2"
]


def domoticz_command(self, Devices, DeviceID, Unit, Nwkid, Command, Level, Color):
    """ Handle Domoticz onCommand"""
    
    widget_name = domo_read_Name(self, Devices, DeviceID, Unit)
    self.log.logging("Command", "Debug", f"mgtCommand ({Nwkid}) {DeviceID} {Unit} Name: {widget_name} Command: {Command} Level: {Level} Color: {Color}", Nwkid)

    SignalLevel, BatteryLevel = RetreiveSignalLvlBattery(self, Nwkid)
    ClusterTypeList = RetreiveWidgetTypeList(self, Devices, DeviceID, Nwkid, Unit)
    
    if not ClusterTypeList or len(ClusterTypeList) != 1:
        self.log.logging("Command", "Error", f"Unexpected ClusterTypeList: {ClusterTypeList} for Nwkid: {Nwkid}")
        return

    EPout, DeviceTypeWidgetId, DeviceType = ClusterTypeList[0]

    if self.ListOfDevices.get(Nwkid, {}).get("Health") == "Disabled":
        self.log.logging("Command", "Error", f"Attempted action on a disabled device: {widget_name}/{Nwkid}")
        return

    forceUpdateDev = SWITCH_SELECTORS.get(DeviceType, {}).get("ForceUpdate", False)

    if DeviceType not in ACTIONATORS and not self.pluginconf.pluginConf.get("forcePassiveWidget"):
        self.log.logging("Command", "Log", f"mgtCommand - You are trying to action not allowed for Device: {widget_name} Type: {ClusterTypeList} and DeviceType: {DeviceType} Command: {Command} Level:{Level}", Nwkid)
        return
    
    health_value = self.ListOfDevices.get(Nwkid, {}).get("Health")
    if health_value == "Not Reachable":
        self.ListOfDevices.setdefault(Nwkid, {})["Health"] = ""


    if Command == "Stop":
        handle_command_stop(self, Devices, DeviceID, Unit, Nwkid, EPout, DeviceType, BatteryLevel, SignalLevel, forceUpdateDev)

    elif Command in ("Off", "Close"):
        handle_command_off(self, Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, BatteryLevel, SignalLevel, forceUpdateDev)

    elif Command in ("On", "Open"):
        handle_command_on(self, Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, BatteryLevel, SignalLevel, forceUpdateDev)

    elif Command == "Set Level":
        handle_command_setlevel(self, Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, BatteryLevel, SignalLevel, forceUpdateDev)

    elif Command == "Set Color":
        handle_command_setcolor(self, Devices, DeviceID, Unit, Level, Color, Nwkid, EPout, DeviceType, BatteryLevel, SignalLevel, forceUpdateDev)


def request_read_device_status(self, Nwkid):
    """ request a read attribute, by setting device heartbeat to -1"""
    self.ListOfDevices[Nwkid]["Heartbeat"] = "-1"


def handle_command_stop(self,Devices, DeviceID, Unit, Nwkid, EPout, DeviceType, BatteryLevel, SignalLevel, forceUpdateDev):
    """ STOP command. Usally STOP opening/closing blind,windows covering."""
    
    self.log.logging( "Command", "Debug", "handle_command_stop : Stop for Device: %s EPout: %s Unit: %s DeviceType: %s" % (Nwkid, EPout, Unit, DeviceType), Nwkid, )

    model_name = self.ListOfDevices[Nwkid].get("Model", "")
    profalux = self.ListOfDevices[Nwkid].get("Manufacturer") == "1110" and self.ListOfDevices[Nwkid].get("ZDeviceID") in ("0200", "0202")
    
    if DeviceType == "LvlControl" and model_name == "TS0601-curtain":
        tuya_curtain_openclose(self, Nwkid, EPout, "01")

    elif profalux:
        # Profalux offer a Manufacturer command to make Stop on Cluster 0x0008
        profalux_stop(self, Nwkid)

    elif model_name in ( "TS0601-_TZE200_nklqjk62", ):
        self.log.logging("Command", "Debug", "handle_command_stop : Off for Tuya Garage Door %s" % Nwkid)
        tuya_garage_door_action( self, Nwkid, "02")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

    elif DeviceType in ("WindowCovering", "VenetianInverted", "Venetian", "Vanne", "VanneInverted", "Curtain", "CurtainInverted"): 
        if model_name in ("PR412", "CPR412", "CPR412-E"):
            profalux_stop(self, Nwkid)
        else:
            actuator_stop( self, Nwkid, EPout, "WindowCovering")
            
        if DeviceType in ( "CurtainInverted", "Curtain"):
            if ts0601_extract_data_point_infos( self, model_name):
                ts0601_actuator(self, Nwkid, "CurtainState", 1)
                update_domoticz_widget(self, Devices, DeviceID, Unit, 17, "0", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

            # Refresh will be done via the Report Attribute
            return

        update_domoticz_widget(self, Devices, DeviceID, Unit, 17, "0", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
    else:
        actuator_stop( self, Nwkid, EPout, "Light")

    # Let's force a refresh of Attribute in the next Heartbeat
    request_read_device_status(self, Nwkid)


def handle_command_off(self,Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, BatteryLevel, SignalLevel, forceUpdateDev):
    """ OFF command"""

    model_name = self.ListOfDevices[Nwkid].get("Model", "")
    profalux = self.ListOfDevices[Nwkid].get("Manufacturer") == "1110" and self.ListOfDevices[Nwkid].get("ZDeviceID") in ("0200", "0202")
    
    if DeviceType not in ( "CurtainInverted", "Curtain"):
        # Refresh will be done via the Report Attribute
        request_read_device_status(self, Nwkid)

    self.log.logging("Command", "Debug", f"handle_command_off : Off for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} modelName: {model_name}", Nwkid)

    if model_name in ( "TS0601-switch", "TS0601-2Gangs-switch", "TS0601-2Gangs-switch", ):
        self.log.logging("Command", "Debug", "handle_command_off : Off for Tuya Switches Gang/EPout: %s" % EPout)
        tuya_switch_command(self, Nwkid, "00", gang=int(EPout, 16))
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return
    
    if model_name in ( "TS0601-_TZE200_nklqjk62", ):
        self.log.logging("Command", "Debug", "handle_command_off : Off for Tuya Garage Door %s" % Nwkid)
        tuya_garage_door_action( self, Nwkid, "00")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if model_name == "TS0601-Parkside-Watering-Timer":
        self.log.logging("Command", "Debug", "handle_command_off : On for Tuya ParkSide Water Time")
        if self.ListOfDevices[Nwkid].get("Param", {}).get("TimerMode"):
            self.log.logging("Command", "Debug", "handle_command_off : Off for Tuya ParkSide Water Time - Timer Mode")
            tuya_watertimer_command(self, Nwkid, "00", gang=int(EPout, 16))
        else:
            self.log.logging("Command", "Debug", "handle_command_off : Off for Tuya ParkSide Water Time - OnOff Mode")
            actuator_off(self, Nwkid, EPout, "Light")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "SwitchCalibration" and model_name == "TS0601-Moes-Curtain":
        # Switch Off Calibration
        self.log.logging("Command", "Status", "mgtCommand : Switch Off Calibration on %s/%s" % (Nwkid,EPout))
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        ts0601_curtain_accurate_calibration_cmd( self, Nwkid, EPout, 0x03, mode=1)
        return

    if DeviceType == "SwitchAlarm" and model_name == "TS0601-_TZE200_t1blo2bj":
        tuya_siren2_trigger(self, Nwkid, '00')
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "SwitchAlarm" and model_name == "SMSZB-120" and self.iaszonemgt:
        self.iaszonemgt.iaswd_develco_warning(Nwkid, EPout, "00")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "SwitchAlarm" and model_name == "TS0601-Solar-Siren" and ts0601_extract_data_point_infos( self, model_name):
        ts0601_actuator(self, Nwkid, "TuyaAlarmSwitch", 0)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return
        
    if DeviceType == "TamperSwitch" and ts0601_extract_data_point_infos( self, model_name):
        ts0601_actuator(self, Nwkid, "TuyaTamperSwitch", 0)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return
        
    if model_name in ("TS0601-Energy",):
        tuya_energy_onoff(self, Nwkid, "00")
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
        self.log.logging("Command", "Debug", f"handle_command_off : Set Level for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid)

        thermostat_Mode(self, Nwkid, "Off")
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType in ("ThermoMode_2", ):
        self.log.logging("Command", "Debug", f"handle_command_off : Set Level for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid)
        
        if ts0601_extract_data_point_infos( self, model_name):
            ts0601_actuator(self, Nwkid, "TRV7SystemMode", 0)
            return

        tuya_trv_mode(self, Nwkid, 0)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType in ("PollingControl", "PollingControlV2", ):
        self.log.logging("Command", "Log", f"handle_command_off : PollingControl Set Level/Off for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid)
        tuya_polling_control(self, Nwkid, DeviceType, Level)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return
    
    if DeviceType in ("ThermoMode_4", "ThermoMode_5", "ThermoMode_6", "ThermoMode_7"):
        self.log.logging("Command", "Debug", f"handle_command_off : Set Level for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid)
        
        if DeviceType == "ThermoMode_7" and ts0601_extract_data_point_infos( self, model_name):
            ts0601_actuator(self, Nwkid, "TRV6SystemMode", 0)
            return

        if model_name in ( "TS0601-_TZE200_dzuqwsyg", "TS0601-eTRV5"):
            tuya_trv_onoff(self, Nwkid, 0x01)
            update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            return
    
    if DeviceType == "ThermoModeEHZBRTS":
        self.log.logging("Command", "Debug", "handle_command_off EHZBRTS Schneider Thermostat Mode Off", Nwkid)
        schneider_EHZBRTS_thermoMode(self, Nwkid, 0)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType in ("ACMode_2", "FanControl"):
        casaia_system_mode(self, Nwkid, "Off")
        return

    if DeviceType == "AirPurifierMode" and model_name in ('STARKVIND Air purifier', ):
        ikea_air_purifier_mode( self, Nwkid, EPout, 0 )

    if DeviceType == "ACSwing" and model_name == "AC201A":
        casaia_swing_OnOff(self, Nwkid, "00")
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        return

    if DeviceType == "LvlControl" and model_name in ("TS0601-dimmer", "TS0601-2Gangs-dimmer"):
        tuya_dimmer_onoff(self, Nwkid, EPout, "00")
        _, cur_sValue = domo_read_nValue_sValue(self, Devices, DeviceID, Unit)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, cur_sValue, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        return

    if DeviceType == "LvlControl" and model_name == "TS0601-curtain":
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

    elif DeviceType in ("VenetianInverted", "VanneInverted", "CurtainInverted"):
        if model_name in ("PR412", "CPR412", "CPR412-E"):
            actuator_on(self, Nwkid, EPout, "Light")
        else:
            actuator_on(self, Nwkid, EPout, "WindowCovering")
            
        if DeviceType in ( "CurtainInverted", ):
            # Refresh will be done via the Report Attribute
            return

    elif DeviceType in ( "Venetian", "Vanne", "Curtain"):

        if model_name in ( "PR412", "CPR412", "CPR412-E"):
            actuator_off(self, Nwkid, EPout, "Light")

        elif DeviceType in ( "Curtain", ) and ts0601_extract_data_point_infos( self, model_name):
            ts0601_actuator(self, Nwkid, "CurtainState", 2)
            update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            return

        elif ( DeviceType in ("Vanne", "Curtain",) or model_name in ( "TS130F",) ):
            actuator_off(self, Nwkid, EPout, "WindowCovering")
            
        elif DeviceType in ( "CurtainInverted", "Curtain"):
            # Refresh will be done via the Report Attribute
            return

        else:
            actuator_on(self, Nwkid, EPout, "WindowCovering")

    elif DeviceType == "AlarmWD":
        self.iaszonemgt.alarm_off(Nwkid, EPout)

    elif DeviceType == "HeatingSwitch":
        thermostat_Mode(self, Nwkid, "Off")

    elif DeviceType == "ThermoOnOff":
        self.log.logging("Command", "Debug", "ThermoOnOff - requested Off", Nwkid)
        if model_name in ("eTRV0100"):
            danfoss_on_off(self, Nwkid, 0x00)
        else:
            tuya_trv_onoff(self, Nwkid, 0x00)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

    elif DeviceType == "ShutterCalibration":
        self.log.logging("Command", "Debug", "handle_command_off : Disable Window Cover Calibration")
        tuya_window_cover_calibration(self, Nwkid, "01")

    elif (
        DeviceType == "Switch"
        and not get_deviceconf_parameter_value(self, model_name, "StandardZigbeeCommand", return_default=False)
        and ts0601_extract_data_point_infos( self, model_name)
        ):
        ts0601_actuator(self, Nwkid, "switch", 0)
    else:
        # Remaining Slider widget
        _off_command_default(self, Nwkid, EPout, profalux, model_name)

    # Update Devices
    if is_dimmable_blind(self, Devices, DeviceID, Unit):
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "0", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
    else:
        update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

    # Let's force a refresh of Attribute in the next Heartbeat
    request_read_device_status(self, Nwkid)


def _off_command_default(self, Nwkid, EPout, profalux, model_name):
    """ Handle all other widgets for the OFF command"""

    if profalux:  # Profalux are define as LvlControl but should be managed as Blind Inverted
        actuator_setlevel(self, Nwkid, EPout, 0, "Light", "0000", withOnOff=False)

    elif self.ListOfDevices[Nwkid].get("Param", {}).get("fadingOff", False):
        effect_mapping = {
            1: "0002",  # 50% dim down in 0.8 seconds then fade to off in 12 seconds
            2: "0100",  # 20% dim up in 0.5s then fade to off in 1 second
            255: "0001"  # No fade
        }

        effect = effect_mapping.get(self.ListOfDevices[Nwkid].get("Param", {}).get("fadingOff"))
        if effect is None:
            effect = "0000"

        self.log.logging("Command", "Debug", f"mgtCommand : {Nwkid} fading Off effect: {effect}")

        actuator_off(self, Nwkid, EPout, "Light", effect)
    else:
        actuator_off(self, Nwkid, EPout, "Light")

    # Making a trick for the GLEDOPTO LED STRIP.
    if model_name == "GLEDOPTO" and EPout == "0a":
        # When switching off the WW channel, make sure to switch Off the RGB channel
        actuator_off(self, Nwkid, "0b", "Light")

   
def handle_command_on(self,Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, BatteryLevel, SignalLevel, forceUpdateDev):
    model_name = self.ListOfDevices[Nwkid].get("Model", "")
    profalux = self.ListOfDevices[Nwkid].get("Manufacturer") == "1110" and self.ListOfDevices[Nwkid].get("ZDeviceID") in ("0200", "0202")

    request_read_device_status(self, Nwkid)

    self.log.logging( "Command", "Debug", f"mgtCommand : On for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} ModelName: {model_name}", Nwkid, )

    if model_name in ( "TS0601-switch", "TS0601-2Gangs-switch", "TS0601-2Gangs-switch", ):
        self.log.logging("Command", "Debug", "mgtCommand : On for Tuya Switches Gang/EPout: %s" % EPout)
        tuya_switch_command(self, Nwkid, "01", gang=int(EPout, 16))
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "SwitchCalibration" and model_name == "TS0601-Moes-Curtain":
        # Switch On calibration
        self.log.logging("Command", "Status", "mgtCommand : Switch ON Calibration on %s/%s" % (Nwkid,EPout))
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        ts0601_curtain_accurate_calibration_cmd( self, Nwkid, EPout, 0x03, mode=0)
        return

    if DeviceType == "SwitchAlarm" and model_name == "TS0601-_TZE200_t1blo2bj":
        tuya_siren2_trigger(self, Nwkid, '01')
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return
    
    if DeviceType == "SwitchAlarm" and model_name == "SMSZB-120" and self.iaszonemgt:
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        self.iaszonemgt.iaswd_develco_warning(Nwkid, EPout, "01")
        return
    
    if DeviceType == "SwitchAlarm" and model_name == "TS0601-Solar-Siren" and ts0601_extract_data_point_infos( self, model_name):
        ts0601_actuator(self, Nwkid, "TuyaAlarmSwitch", 1)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "TamperSwitch" and model_name == "TS0601-Solar-Siren" and ts0601_extract_data_point_infos( self, model_name):
        ts0601_actuator(self, Nwkid, "TuyaTamperSwitch", 1)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if model_name in ("TS0601-_TZE200_nklqjk62", ):
        self.log.logging("Command", "Debug", "handle_command_on : On for Tuya Garage Door %s" % Nwkid)
        tuya_garage_door_action( self, Nwkid, "01")
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if model_name == "TS0601-Parkside-Watering-Timer":
        self.log.logging("Command", "Debug", "handle_command_on : On for Tuya ParkSide Water Time")
        if self.ListOfDevices[Nwkid].get("Param", {}).get("TimerMode"):
            self.log.logging("Command", "Debug", "handle_command_on : On for Tuya ParkSide Water Time - Timer Mode")
            tuya_watertimer_command(self, Nwkid, "01", gang=int(EPout, 16))
        else:
            self.log.logging("Command", "Debug", "handle_command_on : On for Tuya ParkSide Water Time - OnOff Mode")
            actuator_on(self, Nwkid, EPout, "Light")

    if model_name in ("TS0601-Energy",):
        tuya_energy_onoff(self, Nwkid, "01")
        return

    if DeviceType == "AirPurifierMode" and model_name in ('STARKVIND Air purifier', ):
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

    if DeviceType == "LvlControl" and model_name in ("TS0601-dimmer", "TS0601-2Gangs-dimmer"):
        tuya_dimmer_onoff(self, Nwkid, EPout, "01")
        _, cur_sValue = domo_read_nValue_sValue(self, Devices, DeviceID, Unit)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, cur_sValue, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        return

    if DeviceType == "LvlControl" and model_name == "TS0601-curtain":
        tuya_curtain_openclose(self, Nwkid, "00")

    elif DeviceType == "BSO-Volet" and profalux:
        # On translated into a Move to 254
        profalux_MoveToLiftAndTilt(self, Nwkid, level=255)

    elif DeviceType == "WindowCovering":
        actuator_on(self, Nwkid, EPout, "WindowCovering")

    elif DeviceType in ("VenetianInverted", "VanneInverted", "CurtainInverted"):
        if model_name in ("PR412", "CPR412", "CPR412-E"):
            actuator_off(self, Nwkid, EPout, "Light")
        else:
            actuator_off(self, Nwkid, EPout, "WindowCovering")
            
        if DeviceType in ( "CurtainInverted", ):
            # Refresh will be done via the Report Attribute
            return

    elif DeviceType in ("Venetian", "Vanne", "Curtain"):
        if model_name in ("PR412", "CPR412", "CPR412-E"):
            actuator_on(self, Nwkid, EPout, "Light")
                
        elif DeviceType in ( "Curtain", ) and ts0601_extract_data_point_infos( self, model_name):
            ts0601_actuator(self, Nwkid, "CurtainState", 0)
            update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "Open", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType in ( "Vanne", "Curtain",) or model_name in ( "TS130F",):
            actuator_on(self, Nwkid, EPout, "WindowCovering")

        elif DeviceType in ( "CurtainInverted", "Curtain"):
            return

        else:
            actuator_off(self, Nwkid, EPout, "WindowCovering")
            # Refresh will be done via the Report Attribute
            return

    elif DeviceType == "HeatingSwitch":
        thermostat_Mode(self, Nwkid, "Heat")

    elif DeviceType == "ThermoOnOff":
        if model_name in ("eTRV0100"):
            danfoss_on_off(self, Nwkid, 0x01)
        else:
            tuya_trv_onoff(self, Nwkid, 0x01)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

    elif DeviceType == "ShutterCalibration":
        self.log.logging("Command", "Debug", "mgtCommand : Enable Window Cover Calibration")
        tuya_window_cover_calibration(self, Nwkid, "00")

    elif (
        DeviceType == "Switch"
        and not get_deviceconf_parameter_value(self, model_name, "StandardZigbeeCommand", return_default=False)
        and ts0601_extract_data_point_infos( self, model_name)
        ):
        ts0601_actuator(self, Nwkid, "switch", 1)

    elif profalux:
            actuator_setlevel(self, Nwkid, EPout, 255, "Light", "0000", withOnOff=False)

    else:
        actuator_on(self, Nwkid, EPout, "Light")

    if is_dimmable_blind(self, Devices, DeviceID, Unit):
        # (13, 14, 15, 16)
        update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "100", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)

    else:
        previous_level = get_previous_switch_level(self, Nwkid, EPout)
        self.log.logging( "Command", "Debug", "handle_command_on : Previous Level was %s" % (
            previous_level), Nwkid, )

        if previous_level is None:
            update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            
        elif is_dimmable_light(self, Devices, DeviceID, Unit):
            percentage_level = int(( (previous_level * 100 )/ 255))
            self.log.logging( "Command", "Debug", "handle_command_on : Previous Level was %s" %previous_level)
            update_domoticz_widget(self, Devices, DeviceID, Unit, 1, str(percentage_level), BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            
        else:
            percentage_level = int(( (previous_level * 100 )/ 255))
            self.log.logging( "Command", "Debug", "handle_command_on : Previous Level was %s" %(previous_level,))
            update_domoticz_widget(self, Devices, DeviceID, Unit, 2, str(percentage_level), BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            
    # Let's force a refresh of Attribute in the next Heartbeat
    self.log.logging( "Command", "Debug", "handle_command_on : request_read_device_status()")
    request_read_device_status(self, Nwkid)


def handle_command_setlevel(self,Devices, DeviceID, Unit, Level, Nwkid, EPout, DeviceType, BatteryLevel, SignalLevel, forceUpdateDev):
    
    model_name = self.ListOfDevices[Nwkid].get("Model", "")
    profalux = self.ListOfDevices[Nwkid].get("Manufacturer") == "1110" and self.ListOfDevices[Nwkid].get("ZDeviceID") in ("0200", "0202")
     
    self.log.logging( "Command", "Debug", f"handle_command_setlevel : Set Level for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid, )

    if DeviceType == "ThermoSetpoint":
        _set_level_setpoint(self, Devices, DeviceID, Unit, Nwkid, EPout, model_name, Level, BatteryLevel, SignalLevel,DeviceType, forceUpdateDev )
        return

    if DeviceType == "TempSetCurrent":
        _set_level_set_current_temp(self, Devices, DeviceID, Unit, Nwkid, EPout, Level, BatteryLevel, SignalLevel,DeviceType, forceUpdateDev)
        return

    if DeviceType == "ThermoModeEHZBRTS":
        self.log.logging("Command", "Debug", "MajDomoDevice EHZBRTS Schneider Thermostat Mode %s" % Level, Nwkid)
        schneider_EHZBRTS_thermoMode(self, Nwkid, Level)
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "HACTMODE":
        _set_level_hact_mode(self, Devices, DeviceID, Unit, Nwkid, EPout, Level, BatteryLevel, SignalLevel,DeviceType, forceUpdateDev)
        return

    if DeviceType == "LegranCableMode":
        self.log.logging( "Command", "Debug", "handle_command_setlevel : Set Level for Legrand Cable Mode: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
            Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        cable_connected_mode(self, Nwkid, str(Level))
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        request_read_device_status(self, Nwkid)
        return

    if DeviceType == "ContractPower":
        self.log.logging( "Command", "Debug", "handle_command_setlevel : Set Level for ContractPower Mode: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
            Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
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
            self.log.logging( "Command", "Debug", "handle_command_setlevel : -----> Contract Power : %s - %s KVA" % (
                Level, CONTRACT_MODE[Level]), Nwkid, )
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
        self.log.logging( "Command", "Debug", "handle_command_setlevel : Set Level for FIP: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
            Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        if "Schneider Wiser" not in self.ListOfDevices[Nwkid]:
            self.ListOfDevices[Nwkid]["Schneider Wiser"] = {}

        if ( Level in FIL_PILOT_MODE and model_name ):
            if model_name == "EH-ZB-HACT":
                self.log.logging( "Command", "Debug","handle_command_setlevel : -----> HACT -> Fil Pilote mode: %s - %s" % (
                    Level, FIL_PILOT_MODE[Level]),Nwkid, )
                self.ListOfDevices[Nwkid]["Schneider Wiser"]["HACT FIP Mode"] = FIL_PILOT_MODE[Level]
                schneider_hact_fip_mode(self, Nwkid, FIL_PILOT_MODE[Level])
                update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev, )

            elif model_name == "Cable outlet":
                self.log.logging( "Command", "Debug", "handle_command_setlevel : -----> Fil Pilote mode: %s - %s" % (
                    Level, FIL_PILOT_MODE[Level]), Nwkid, )
                legrand_fc40(self, Nwkid, FIL_PILOT_MODE[Level])
                update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev, )

            elif model_name in ( "SIN-4-FP-21_EQU", "SIN-4-FP-21"):
                ADEO_FIP_ONOFF_COMMAND = {
                    10: 1,
                    20: 4,
                    30: 5,
                    40: 2,
                    50: 3,
                    60: 0,
                    }
                self.log.logging( "Command", "Log", "handle_command_setlevel : -----> Adeo/Nodon/Enky Fil Pilote mode: %s - %s" % (
                    Level, ADEO_FIP_ONOFF_COMMAND[Level]), Nwkid, )

                adeo_fip(self, Nwkid, EPout, ADEO_FIP_ONOFF_COMMAND[ Level ])
                update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev, )

        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType in ("ThermoMode_3", ): 
        self.log.logging( "Command", "Debug", "handle_command_setlevel : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
            Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        self.log.logging("Command", "Debug", "ThermoMode_3 (Acova) - requested Level: %s" % Level, Nwkid)
        if Level in THERMOSTAT_LEVEL_3_MODE:
            self.log.logging( "Command", "Debug", " - Set Thermostat Mode to : %s / T2:%s " % (
                Level, THERMOSTAT_LEVEL_3_MODE[Level]), Nwkid, )

            thermostat_Mode(self, Nwkid, THERMOSTAT_LEVEL_3_MODE[Level])
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return

    if DeviceType in ("ThermoMode", ):
        self.log.logging( "Command", "Debug", "handle_command_setlevel : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
            Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        self.log.logging("Command", "Debug", "ThermoMode - requested Level: %s" % Level, Nwkid)
        if Level in THERMOSTAT_LEVEL_2_MODE:
            self.log.logging( "Command", "Debug", " - Set Thermostat Mode to : %s / %s" % (
                Level, THERMOSTAT_LEVEL_2_MODE[Level]), Nwkid, )
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
        self.log.logging( "Command", "Debug", "handle_command_setlevel : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
            Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        self.log.logging("Command", "Debug", "ThermoMode - requested Level: %s" % Level, Nwkid)
        if Level in ACLEVEL_TO_MODE:
            self.log.logging( "Command", "Debug", " - Set Thermostat Mode to : %s / %s" % (Level, ACLEVEL_TO_MODE[Level]), Nwkid )
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
        self.log.logging( "Command", "Debug", "handle_command_setlevel : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
            Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        self.log.logging("Command", "Debug", "ThermoMode - requested Level: %s" % Level, Nwkid)
        if Level in CAC221ACLevel_TO_MODE:
            self.log.logging( "Command", "Debug", " - Set Thermostat Mode to : %s / %s" % (Level, CAC221ACLevel_TO_MODE[Level]), Nwkid )
            thermostat_Mode(self, Nwkid, CAC221ACLevel_TO_MODE[Level])
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        # Let's force a refresh of Attribute in the next Heartbeat
        request_read_device_status(self, Nwkid)
        return
                    
    if DeviceType == "ThermoMode_2":
        self.log.logging( "Command", "Debug", "handle_command_setlevel : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
            Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        self.log.logging("Command", "Debug", "ThermoMode_2 - requested Level: %s" % Level, Nwkid)
        if ts0601_extract_data_point_infos( self, model_name):
            ts0601_actuator(self, Nwkid, "TRV7SystemMode", int(Level // 10))
            return

        tuya_trv_mode(self, Nwkid, Level)
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level // 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        return

    if DeviceType in ("PollingControl", "PollingControlV2", ):
        self.log.logging("Command", "Log", f"handle_command_setlevel : PollingControl Set Level for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid)
        tuya_polling_control(self, Nwkid, DeviceType, Level)
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level // 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )
        return

    if DeviceType == "ThermoMode_4":
        self.log.logging(
            "Command",
            "Debug",
            "handle_command_setlevel : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s"
            % (Nwkid, EPout, Unit, DeviceType, Level),
            Nwkid,
        )
        
        if model_name == "TS0601-_TZE200_b6wax7g0":
            self.log.logging("Command", "Debug", "ThermoMode_4 - requested Level: %s" % Level, Nwkid)
            # 0x00 - Auto, 0x01 - Manual, 0x02 - Temp Hand, 0x03 - Holliday   
            tuya_trv_brt100_set_mode(self, Nwkid, int(Level / 10) - 1)
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level / 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            return

    if DeviceType == "ThermoMode_7" and ts0601_extract_data_point_infos( self, model_name):
        ts0601_actuator(self, Nwkid, "TRV6SystemMode", int(Level // 10))
        return

    if DeviceType == "ThermoMode_8" and ts0601_extract_data_point_infos( self, model_name):
        ts0601_actuator(self, Nwkid, "TRV8SystemMode", int(Level // 10))
        return

    if DeviceType in ("ThermoMode_5", "ThermoMode_6"):
        self.log.logging( "Command", "Debug", "handle_command_setlevel : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" % (
            Nwkid, EPout, Unit, DeviceType, Level), Nwkid, )
        
        if model_name == "TS0601-_TZE200_chyvmhay":
            # 1: // manual 2: // away 0: // auto
            tuya_lidl_set_mode( self, Nwkid, int(Level / 10) - 1 )
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level / 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            
        elif model_name == "TS0601-_TZE200_dzuqwsyg":
            tuya_trv_onoff(self, Nwkid, 0x01)

            tuya_coil_fan_thermostat(self, Nwkid, int(Level / 10) - 1)
            update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level / 10), Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            
        elif model_name == "TS0601-eTRV5":
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
            
    if DeviceType == "AirPurifierMode" and model_name in ('STARKVIND Air purifier', ):
        self.log.logging( "Command", "Debug", "   Air Purifier Mode: %s" % ( Level ), Nwkid,)
        
        if Level == 10:
            ikea_air_purifier_mode( self, Nwkid, EPout, 1 )
        elif Level in ( 20, 30, 40, 50, 60):
            mode = Level - 10
            ikea_air_purifier_mode( self, Nwkid, EPout, mode)
        
    if DeviceType == "FanControl":
        _set_level_fan_control(self, Devices, DeviceID, Unit, BatteryLevel, SignalLevel, forceUpdateDev, DeviceType, Nwkid, EPout, Level, model_name)

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

            self.log.logging( "Command", "Debug", f"handle_command_setlevel : profalux_MoveToLiftAndTilt: {Nwkid} BSO-Volet Lift: Level: {Level} Lift: {lift}", Nwkid, )
            profalux_MoveToLiftAndTilt(self, Nwkid, level=lift)

    elif DeviceType == "BSO-Orientation":
        if profalux:
            Tilt = Level - 10
            self.log.logging( "Command", "Debug", f"handle_command_setlevel : profalux_MoveToLiftAndTilt: {Nwkid} BSO-Orientation : Level: {Level} Tilt: {Tilt}", Nwkid, )
            profalux_MoveToLiftAndTilt(self, Nwkid, tilt=Tilt)

    elif DeviceType in ( "WindowCovering", "Venetian", "Vanne", "Curtain", "VenetianInverted", "VanneInverted", "CurtainInverted"):
        if ts0601_extract_data_point_infos( self, model_name):
            self.log.logging( "Command", "Debug", f"handle_command_setlevel : Tuya TS0601: {Nwkid} Level: {Level}", Nwkid, )
            ts0601_actuator(self, Nwkid, "CurtainLevel", Level)
            update_domoticz_widget(self, Devices, DeviceID, Unit, 2, str(Level), BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
            return

        _set_level_windows_covering(self, DeviceType, Nwkid, EPout, Level)

    elif DeviceType == "AlarmWD":
        handle_alarm_command(self, Nwkid, EPout, Level)

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

    elif model_name in ("TS0601-dimmer", "TS0601-2Gangs-dimmer"):
        cur_nValue, _ = domo_read_nValue_sValue(self, Devices, DeviceID, Unit)
        if cur_nValue == 0:
            tuya_dimmer_onoff(self, Nwkid, EPout, "01")
        Level = max(Level, 1)
        tuya_dimmer_dimmer(self, Nwkid, EPout, Level)

    elif model_name == "TS0601-curtain":
        tuya_curtain_lvl(self, Nwkid, (Level))

    elif profalux:
        actuator_setlevel(self, Nwkid, EPout, Level, "Light", "0000", withOnOff=False)

    else:
        if Level > 1 and get_deviceconf_parameter_value(self, model_name, "ForceSwitchOnformoveToLevel", return_default=False):
            actuator_on(self, Nwkid, EPout, "Light")

        move_to_level = self.ListOfDevices.get(Nwkid, {}).get("Param", {}).get("moveToLevel")
        transitionMoveLevel = f"{int(move_to_level):04x}" if move_to_level is not None else "0010"

        actuator_setlevel(self, Nwkid, EPout, Level, "Light", transitionMoveLevel, withOnOff=True)

    # Domoticz widget update
    dimmable_blind = is_dimmable_blind(self, Devices, DeviceID, Unit)
    if dimmable_blind and Level in ( 0, 50, 100):
        if Level == 0:
            update_domoticz_widget(self, Devices, DeviceID, Unit, 0, "0", BatteryLevel, SignalLevel)
        
        elif Level == 100:
            update_domoticz_widget(self, Devices, DeviceID, Unit, 1, "1", BatteryLevel, SignalLevel)
        
        elif Level == 50:
            update_domoticz_widget(self, Devices, DeviceID, Unit, 17, "0", BatteryLevel, SignalLevel)

    else:
        partially_opened_nValue = dimmable_blind or is_dimmable_light(self, Devices, DeviceID, Unit) or is_dimmable_switch(self, Devices, DeviceID, Unit)
        if partially_opened_nValue is None:
            partially_opened_nValue = 1
        update_domoticz_widget(self, Devices, DeviceID, Unit, partially_opened_nValue, str(Level), BatteryLevel, SignalLevel)

    # Let's force a refresh of Attribute in the next Heartbeat
    request_read_device_status(self, Nwkid)


def get_previous_switch_level(self, Nwkid, Ep):
    device = self.ListOfDevices.get(Nwkid)
    if not device:
        return None
    
    ep_data = device.get('Ep', {})
    if Ep not in ep_data:
        return None

    ep_0008_data = ep_data[Ep].get('0008', {})
    switch_level = ep_0008_data.get('0000')
    
    if switch_level in ('', {}):
        return None
    
    if isinstance(switch_level, str):
        return int(switch_level, 16)
    
    if isinstance(switch_level, int):
        return switch_level
    
    self.log.logging( "Command", "Debug", f"get_previous_switch_level : Mostlikely a non-dimmable device >{switch_level}<", Nwkid, )
    return None


def _set_level_hact_mode(self, Devices, DeviceID, Unit, Nwkid, EPout, Level, BatteryLevel, SignalLevel, DeviceType, forceUpdateDev):
    self.log.logging("Command", "Debug", f"_set_level_hact_mode: Set Level for HACT Mode: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid)

    schneider_wiser_data = self.ListOfDevices.setdefault(Nwkid, {}).setdefault("Schneider Wiser", {})
    hact_mode = None

    if Level == 10:  # Conventional
        hact_mode = "conventional"
    elif Level == 20:  # fip
        hact_mode = "FIP"

    if hact_mode:
        update_domoticz_widget(self, Devices, DeviceID, Unit, int(Level) // 10, Level, BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev)
        schneider_wiser_data["HACT Mode"] = hact_mode
        schneider_hact_heater_type(self, Nwkid, hact_mode)
    else:
        self.log.logging("Command", "Error", f"Unknown mode {Level} for HACTMODE for device {Nwkid}")

    # Let's force a refresh of Attribute in the next Heartbeat
    request_read_device_status(self, Nwkid)
    return


def _set_level_set_current_temp(self, Devices, DeviceID, Unit, Nwkid, EPout, Level, BatteryLevel, SignalLevel, DeviceType, forceUpdateDev):
    self.log.logging( "Command", "Debug", f"_set_level_set_current_temp : Set Temp for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid, )

    # Convert Level to the appropriate format for temperature
    temp_value = int(float(Level) * 100)

    # Set current temperature
    schneider_temp_Setcurrent(self, Nwkid, temp_value)

    # Normalize Level value with 2 digits
    normalized_level = round(float(Level), 2)

    # Update Domoticz widget
    update_domoticz_widget( self, Devices, DeviceID, Unit, 0, str(normalized_level), BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )

    # Request a refresh of attribute in the next Heartbeat
    request_read_device_status(self, Nwkid)

    return


def _set_level_setpoint(self, Devices, DeviceID, Unit, Nwkid, EPout, model_name, Level, BatteryLevel, SignalLevel, DeviceType, forceUpdateDev):
    # Log the command
    self.log.logging( "Command", "Debug", f"_set_level_setpoint : Set Level for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid, )

    # Convert Level to the appropriate format for the thermostat
    thermostat_value = int(float(Level) * 100)

    # Set the thermostat setpoint
    thermostat_Setpoint(self, Nwkid, thermostat_value)

    # Normalize the Level value to 2 decimal places
    normalized_level = round(float(Level), 2)

    # Update the Domoticz widget
    update_domoticz_widget( self, Devices, DeviceID, Unit, 0, str(normalized_level), BatteryLevel, SignalLevel, ForceUpdate_=forceUpdateDev )

    # Request a refresh of the attribute in the next Heartbeat
    if get_deviceconf_parameter_value(self, model_name, "READ_ATTRIBUTE_AFTER_COMMAND", return_default=True):
        request_read_device_status(self, Nwkid)

    return


def _set_level_fan_control(self, Devices, DeviceID, Unit, BatteryLevel, SignalLevel, forceUpdateDev, DeviceType, Nwkid, EPout, Level, model_name):
    if model_name == "AC201A":
        casaia_ac201_fan_control(self, Nwkid, Level)
        return

    if model_name == "TS0601-_TZE200_dzuqwsyg":
        self.log.logging( "Command", "Debug", f"mgtCommand : Fan Control: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid, )

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

        self.log.logging( "Command", "Debug", f"mgtCommand : Fan Control not expected Level : {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level}", Nwkid, )        
        return

    # Generic FAN
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
    mode_mapping = {
        10: "Cool",
        20: "Heat",
        30: "Dry",
        40: "Fan",
    }
    mode = mode_mapping.get(Level)
    if mode:
        casaia_system_mode(self, Nwkid, mode)


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


def handle_alarm_command(self, Nwkid, EPout, Level):
    ias_action_mapping = {
        0: self.iaszonemgt.alarm_off,
        10: self.iaszonemgt.alarm_on,
        20: self.iaszonemgt.siren_only,
        30: self.iaszonemgt.strobe_only,
        40: self.iaszonemgt.write_IAS_WD_Squawk,
        50: self.iaszonemgt.write_IAS_WD_Squawk,
    }

    if Level in ias_action_mapping:
        action = ias_action_mapping.get(Level)
        if Level in (40, 50):
            mode = "armed" if Level == 40 else "disarmed"
            action(Nwkid, EPout, mode)
        else:
            action(Nwkid, EPout)
    else:
        self.log.logging("Command", "Error", "Invalid alarm level: %s" % Level)

  
def _set_level_tuya_siren(self, Nwkid, EPout, Level):
    level_mapping = {
        10: (0x01, 1),
        20: (0x01, 2),
        30: (0x01, 3),
        40: (0x01, 4),
        50: (0x01, 5),
    }
    params = level_mapping.get(Level)
    if params:
        tuya_siren_alarm(self, Nwkid, *params)
    else:
        self.log.logging("Command", "Error", "Invalid level for tuya siren: %s" % Level)
    

def _set_level_device_toggle(self, Nwkid, EPout, Level):
    self.log.logging("Command", "Debug", "Toggle switch - value: %s" % Level)
    if Level in (10, 20, 30):
        command = {10: "Off", 20: "On", 30: "Toggle"}[Level]
        actuators(self, Nwkid, EPout, command, "Switch")
    else:
        self.log.logging("Command", "Error", "Invalid level for device toggle: %s" % Level)

  
def handle_command_setcolor(self,Devices, DeviceID, Unit, Level, Color, Nwkid, EPout, DeviceType, BatteryLevel, SignalLevel, forceUpdateDev):    
    self.log.logging("Command", "Debug", f"mgtCommand : Set Color for Device: {Nwkid} EPout: {EPout} Unit: {Unit} DeviceType: {DeviceType} Level: {Level} Color: {Color}", Nwkid)
    
    actuator_setcolor(self, Nwkid, EPout, Level, Color)
    request_read_device_status(self, Nwkid)

    # Use nValue=15 as https://github.com/zigbeefordomoticz/Domoticz-Zigbee/issues/1680
    update_domoticz_widget(self, Devices, DeviceID, Unit, 15, str(Level), BatteryLevel, SignalLevel, str(Color))
