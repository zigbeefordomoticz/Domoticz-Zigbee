
from datetime import datetime as dt

def legrand_operating_time(self, nwkid, ep, cluster, attribut, value):
    try:
        operating_time = dt.strftime(dt.utcfromtimestamp(value), '%Hh %Mm %Ss')
    except OverflowError:
        operating_time = "99h 99m 99s"
    return operating_time
