MANUFACTURER_NAME_TO_CODE = {
    "EMBER": "1002",
    "PHILIPS": "100b",
    "frient A/S": "1015",
    "LEGRAND": "1021",
    "VANTAGE": "1021",
    "LUMI": "1037",
    "SCHNEIDER ELECTRIC": "105e",
    "COMPUTIME": "1078",
    "PROFALUX": "1110",
    "DANALOCK": "115c",
    "OSRAM": "110c",
    "OWON": "113c",
    "XIAOMI": "115f",
    "INNR": "1166",
    "IKEA OF SWEDEN": "117c",
    "LEDVANCE": "1189",
    "HEIMAN": "120b",
    "DANFOSS": "1246",
    "KONKE": "1268",
    "OSRAM-2": "bbaa",
    "Develco": "1015",
}

TUYA_PREFIX = (
    "_TZ",
    "_TY",
)
TUYA_MANUF_CODE = 1002


def check_and_update_manufcode(self):

    for nwkid in list(self.ListOfDevices):
        if "Manufacturer Name" in self.ListOfDevices[nwkid]:
            if str(self.ListOfDevices[nwkid]["Manufacturer Name"]).upper() in MANUFACTURER_NAME_TO_CODE:
                if (
                    self.ListOfDevices[nwkid]["Manufacturer"]
                    != MANUFACTURER_NAME_TO_CODE[str(self.ListOfDevices[nwkid]["Manufacturer Name"]).upper()]
                ):
                    self.ListOfDevices[nwkid]["Manufacturer"] = MANUFACTURER_NAME_TO_CODE[
                        str(self.ListOfDevices[nwkid]["Manufacturer Name"]).upper()
                    ]

            elif self.ListOfDevices[nwkid]["Manufacturer Name"][0:3] in TUYA_PREFIX:
                # Tuya
                if self.ListOfDevices[nwkid]["Manufacturer"] != TUYA_MANUF_CODE:
                    self.ListOfDevices[nwkid]["Manufacturer"] = TUYA_MANUF_CODE
