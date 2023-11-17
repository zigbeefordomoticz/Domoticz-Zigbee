import json
import re
import tracemalloc
from pathlib import Path

import os
import Domoticz

TOP_nENTRIES = 5 
def start_memory_allocation_tracking(self):
    
    self.snapshot1 = None
    self.snapshot2 = None
    self.tracemalloc = {}

    tracemalloc.start()
    self.snapshot2 = tracemalloc.take_snapshot()
        
        
def check_memory_allocation(self):

    if self.snapshot2:
        self.snapshot1 = self.snapshot2

    self.snapshot2 = tracemalloc.take_snapshot()
    
    if self.snapshot1 and self.snapshot2:
        store_memory_allocation(self)
    
    
def store_memory_allocation(self):
    top_stats = self.snapshot2.compare_to(self.snapshot1, 'lineno')
    store_in_dictionnary(self, top_stats)
    

def store_in_dictionnary(self, tracemalloc_stats):
    # Define a regex pattern to extract relevant information
    pattern = re.compile(r'(\S+):(\d+): size=([\d.]+ [KMGTPEB]+) \(\+(-?[\d.]+ [KMGTPEB]+)?, count=(\d+) \(\+(-?\d+)?\), average=(\d+ [KMGTPEB]+)?\)')

    # Parse each line of the tracemalloc logs
    for line in tracemalloc_stats:
        entry = str(line.traceback)
        if "plugins" not in entry:
            continue
        
        size = int(line.size)
        count = (line.count)

        if entry in self.tracemalloc:
            MaxSize = self.tracemalloc[ entry ]['MaxSize']
            MaxCount = self.tracemalloc[ entry ]['MaxSize']
            sizeIncrease = self.tracemalloc[ entry ]['sizeIncrease']
        else:
            sizeIncrease = MaxSize = MaxCount = 0

        if size > MaxSize:
            sizeIncrease += 1
        MaxSize = max(size, MaxSize)
        MaxCount = max(count, MaxCount)
        
        if 'traceMemoryAllocation' in entry:
            return

        self.tracemalloc[entry] = {'size': size, 'count': count, 'MaxSize': MaxSize, 'MaxCount': MaxCount, 'sizeIncrease': sizeIncrease}
            
            
def dump_trace_malloc(self):

    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
    _tracemalloc_filename = _pluginData / ("Plugin_Malloc_Allocations.json")

    with open(_tracemalloc_filename, "wt") as file:
        json.dump(self.tracemalloc, file, sort_keys=True, indent=2)


def report_top10_allocation(self):

    # Tri par MaxSize décroissant, puis par sizeIncrease décroissant
    sorted_entries_maxsize = sorted(self.tracemalloc.items(), key=lambda x: x[1]['MaxSize'], reverse=True)[:TOP_nENTRIES]
    sorted_entries_sizeincrease = sorted(self.tracemalloc.items(), key=lambda x: x[1]['sizeIncrease'], reverse=True)[:TOP_nENTRIES]

    top10_allocation_data = _extracted_from_report_top10_allocation_8( "Top %s MaxSize ", sorted_entries_maxsize )
    top10_allocation_data = _extracted_from_report_top10_allocation_8( "Top %s sizeIncrease ", sorted_entries_sizeincrease )


def _extracted_from_report_top10_allocation_8(self, arg0, arg1):
    # Affichage des n premières entrées avec le MaxSize le plus élevé
    result = arg0 % TOP_nENTRIES
    for entry in arg1:
        module_name = str(os.path.basename(entry[0]))
        result += "| %s | %s | %s | %s" % (
            module_name,
            entry[1]['size'],
            entry[1]['MaxSize'],
            entry[1]['sizeIncrease'],
        )
    log_top10(self, result)

    return result
    
def log_top10(self,data):
 
    if self.log:
        self.log.logging( "Plugin", "Log", "%s" %(data))
    else:
        Domoticz.Log("%s" %(data))
