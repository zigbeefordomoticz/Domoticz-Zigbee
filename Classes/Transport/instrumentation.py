import Domoticz
import time

instrument_time = True

# Decorator for profiling process_frame
def time_spent_process_frame():
    def profiling(f_in):
        def f_out(self, decoded_frame):
            # Decorator to instrument the time spent in a function.
            if self.pluginconf.pluginConf["ZiGateReactTime"]:
                t_start = 1000 * time.time()
                result = f_in(self, decoded_frame)
                t_end = 1000 * time.time()
                t_elapse = int(t_end - t_start)
                self.statistics.add_timing_thread(t_elapse)
                if t_elapse > 1000:
                    self.log.logging(
                        "debugTiming",
                        "Log",
                        "thread_process_messages (process_frame) spend more than 1s (%s ms) frame: %s"
                        % (t_elapse, decoded_frame),
                    )
            else:
                result = f_in(self, decoded_frame)
            return result

        return f_out

    return profiling


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
