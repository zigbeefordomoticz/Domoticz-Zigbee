# coding: utf-8 -*-
#
# Author: pipiche38
#

import time

instrument_time = True


# Decorator for profiling forwarder
def time_spent_forwarder():
    def profiling(f_in):
        def f_out(self, message):
            # Decorator to instrument the time spent in a function.
            if self.pluginconf.pluginConf["ZiGateReactTime"]:
                t_start = 1000 * time.time()
                result = f_in(self, message)
                t_end = 1000 * time.time()
                t_elapse = int(t_end - t_start)
                self.statistics.add_rxTiming(t_elapse)
                if t_elapse > 1000:
                    self.log.logging(
                        "debugTiming",
                        "Log",
                        "forward_message (F_out) spend more than 1s (%s ms) frame: %s" % (t_elapse, message),
                    )
            else:
                result = f_in(self, message)
            return result

        return f_out

    return profiling
