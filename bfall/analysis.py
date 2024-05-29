
from trace import *

def analyze_traced_processes(data, processes):
    pid_skts = {}
    for pid,process in processes.items():
        pid_skts[pid] = process.trace_sockets()
        process.trace_tcp(pid_skts[pid])

    num_sockets = 0 
    data['num_sockets'] = num_sockets

