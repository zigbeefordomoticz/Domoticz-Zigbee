


def legrand_operating_time(self, nwkid, ep, cluster, attribut, value):
    
    op_time = value
    dd = op_time // 62400
    op_time -= dd * 62400
    hh = op_time // 3600
    op_time -= hh * 3600
    mm = op_time // 60
    op_time -= mm * 60
    ss = op_time

    return "%sd %sh %sm %ss" % (dd, hh, mm, ss)
