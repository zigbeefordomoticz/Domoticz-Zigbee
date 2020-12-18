
import Domoticz
import time

instrument_time = True

def time_spent( profile ):

    def profiling( f_in ):

        def f_out(*args, **kwargs):
            # Decorator to instrument the time spent in a function.
            if profile:
                t_start = 1000 * time.time() 
                result = f_in(*args, **kwargs)
                t_end = 1000 * time.time()
                t_elapse = int( t_end - t_start )
                Domoticz.Log("Time spent in {0}: {1} ms".format( f_in, t_elapse))
            else:
                result = f_in(*args, **kwargs)

            return result

        return f_out

    return profiling