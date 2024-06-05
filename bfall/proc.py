
import atexit
import subprocess as subproc

CHILD_PROCESSES=set()
def kill_all():
    copy_proc = CHILD_PROCESSES.copy()
    for proc in CHILD_PROCESSES:
        kill_proc(proc, False)

atexit.register(kill_all)

def run_proc(cmd, add_to_outstanding=True, stdout=subproc.PIPE, stderr=subproc.PIPE):
    proc = subproc.Popen(cmd, process_group=0, stdout=stdout, stderr=stderr)
    if add_to_outstanding:
        CHILD_PROCESSES.add(proc)
    return proc

def term_proc(proc, remove=True):
    proc.kill()

def kill_proc(proc, remove=True):
    run_proc(["kill", "-9", str(-proc.pid)], False).wait()
    if remove and proc in CHILD_PROCESSES:
        CHILD_PROCESSES.remove(proc)

