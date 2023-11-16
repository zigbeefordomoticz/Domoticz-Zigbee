import json
import re
import tracemalloc
from pathlib import Path

import Domoticz

TOP_LIST = 10

def start_memory_allocation_tracking(self):
    
    self.snapshot1 = None
    self.snapshot2 = None
    self.tracemalloc = {}
    
    tracemalloc.start()
    check_memory_allocation(self, "Init")
    
    
def check_memory_allocation(self, label):
    
    if self.snapshot2:
        self.snapshot1 = self.snapshot2

    self.snapshot2 = tracemalloc.take_snapshot()
    
    if self.snapshot1 and self.snapshot2:
        top_5_differences(self, label)
    
    
    
    
def top_5_differences(self, label):
    
    top_stats = self.snapshot2.compare_to(self.snapshot1, 'lineno')
    store_in_dictionnary(self, top_stats)
    if self.log:
        self.log.logging( "Plugin", "Log", "Top 5 differences at %s" %label)
    else:
        Domoticz.Log("Top %s differences at %s" %(TOP_LIST,label))

    for stat in top_stats[:TOP_LIST]:
        if self.log:
            self.log.logging( "Plugin", "Log", " - %s" %stat)
        else:
            Domoticz.Log( " - %s" %stat)
    if self.log:
        self.log.logging( "Plugin", "Log", " " )
    else:
        Domoticz.Log(" ")
        

def store_in_dictionnary(self, tracemalloc_stats):
    # Define a regex pattern to extract relevant information
    pattern = re.compile(r'(\S+):(\d+): size=([\d.]+ [KMGTPEB]+) \(\+(-?[\d.]+ [KMGTPEB]+)?, count=(\d+) \(\+(-?\d+)?\), average=(\d+ [KMGTPEB]+)?\)')

    # Parse each line of the tracemalloc logs
    for line in tracemalloc_stats:
        entry = str(line.traceback)
        size = int(line.size)
        count = (line.count)

        if entry in self.tracemalloc:
            MaxSize = self.tracemalloc[ entry ]['MaxSize']
            MaxCount = self.tracemalloc[ entry ]['MaxSize']
        else:
            MaxSize = MaxCount =MaxAverage = 0

        MaxSize = max(size, MaxSize)
        MaxCount = max(count, MaxCount)

        self.tracemalloc[entry] = {'size': size, 'count': count, 'MaxSize': MaxSize, 'MaxCount': MaxCount}
            
            
def dump_trace_malloc(self):
    
    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
    _tracemalloc_filename = _pluginData / ("Plugin_Malloc_Allocations.json")

    with open(_tracemalloc_filename, "wt") as file:
        json.dump(self.tracemalloc, file, sort_keys=True, indent=2)
    self.log.logging("Database", "Debug", "WriteDeviceList - flush Plugin db to %s" % _tracemalloc_filename)
