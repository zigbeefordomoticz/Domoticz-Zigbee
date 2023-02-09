


def konke_onoff(self, nwkid, ep, cluster, attribut, data):
    value = None
    if data in ("01", "80"):  # Simple Click
        value = "01"
    elif data in ("02", "81"):  # Multiple Click
        value = "02"
    elif data == "82":  # Long Click
        value = "03"
    elif data == "cd":  # short reset , a short click on the reset button
        value = None

    return value
