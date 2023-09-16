
import Domoticz

# Configuration Helpers
def setConfigItem(Key=None, Attribute="", Value=None):

    Config = {}
    if not isinstance(Value, (str, int, float, bool, bytes, bytearray, list, dict)):
        Domoticz.Error("setConfigItem - A value is specified of a not allowed type: '" + str(type(Value)) + "'")
        return Config

    if isinstance(Value, dict):
        # There is an issue that Configuration doesn't allow None value in dictionary !
        # Replace none value to 'null'
        Value = prepare_dict_for_storage(Value, Attribute)

    try:
        Config = Domoticz.Configuration()
        if Key is None:
            Config = Value  # set whole configuration if no key specified
        else:
            Config[Key] = Value

        Config = Domoticz.Configuration(Config)
    except Exception as inst:
        Domoticz.Error("setConfigItem - Domoticz.Configuration operation failed: '" + str(inst) + "'")
        return None
    return Config


def getConfigItem(Key=None, Attribute="", Default=None):
    
    Domoticz.Log("Loading %s - %s from Domoticz sqlite Db" %( Key, Attribute))
    
    if Default is None:
        Default = {}
    Value = Default
    try:
        Config = Domoticz.Configuration()
        Value = Config if Key is None else Config[Key]
    except KeyError:
        Value = Default
    except Exception as inst:
        Domoticz.Error(
            "getConfigItem - Domoticz.Configuration read failed: '"
            + str(inst)
            + "'"
        )

    return repair_dict_after_load(Value, Attribute)


def prepare_dict_for_storage(dict_items, Attribute):

    from base64 import b64encode

    if Attribute in dict_items:
        dict_items[Attribute] = b64encode(str(dict_items[Attribute]).encode("utf-8"))
    dict_items["Version"] = 1
    return dict_items


def repair_dict_after_load(b64_dict, Attribute):
    if b64_dict in ("", {}):
        return {}
    if "Version" not in b64_dict:
        Domoticz.Log("repair_dict_after_load - Not supported storage")
        return {}
    if Attribute in b64_dict:
        from base64 import b64decode

        b64_dict[Attribute] = eval(b64decode(b64_dict[Attribute]))
    return b64_dict
