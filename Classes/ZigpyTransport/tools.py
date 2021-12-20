import Domoticz

def handle_thread_error(self, e, data=""):
    trace = []
    tb = e.__traceback__
    self.logging_writer( "Error", "Issue in request, dumping stack")
    self.logging_writer( "Error", "==>  %s" %data)
    self.logging_writer( "Error", "'%s' failed '%s'" % (tb.tb_frame.f_code.co_name, str(e)))
    while tb is not None:
        self.logging_writer( "Error",
            "----> Line %s in '%s', function %s"
            % ( tb.tb_lineno, tb.tb_frame.f_code.co_filename, tb.tb_frame.f_code.co_name, ))
        tb = tb.tb_next

