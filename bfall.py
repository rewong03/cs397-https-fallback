#! /usr/bin/python3

import subprocess as subproc
import argparse
import atexit
import re
import time
import psutil
import csv
import os
from datetime import datetime
from rich.progress import Progress
import rich
import parse
import itertools

VERBOSE=False
MAX_RUNTIME=10

def eprintln(*args,**kwargs):
    print("ERROR: ", end='')
    print(*args, **kwargs)

CHILD_PROCESSES=set()
def kill_all():
    copy_proc = CHILD_PROCESSES.copy()
    for proc in CHILD_PROCESSES:
        kill_proc(proc)
        
class NetDev:

    REGISTERED = {}

    def close_all():
        for name,dev in NetDev.REGISTERED.items():
            if not dev.closed:
                dev.close()

    def run_qdisc_cmd(self, cmd_type="change"):
        cmd = ["sudo", "tc", "qdisc", cmd_type, "dev", self.name, self.parent, "netem"]
        cmd.extend(["loss", "{}%".format(self.loss_percent)])
        cmd.extend(["delay", "{}ms".format(self.delay_ms)])
        cp = subproc.run(cmd)
        if cp.returncode != 0:
            raise RuntimeError("Command: {} exited with code ({})".format(cmd,cp.returncode))

    def __init__(self, dev_name, parent="root"):
        # Name of the device "eth0", "wlp1n0", etc.
        self.name = dev_name
        # qdisc parent name
        self.parent = parent

        # Current emulated network conditions
        self.loss_percent = 0
        self.delay_ms = 0
        self.closed = True

        if self.name in NetDev.REGISTERED:
            raise RuntimeError("Trying to register NetDev {} twice!".format(self.name))
        else:
            self.run_qdisc_cmd(cmd_type="add")
            NetDev.REGISTERED[self.name] = self
            self.closed = False

    def close(self):
        if self.closed:
            raise RuntimeError("Trying to close NetDev which is already closed!")
        cp = subproc.run(["sudo", "tc", "qdisc", "del", "dev", self.name, self.parent])
        if cp.returncode != 0:
            raise RuntimeError('Could not reset NetDev conditions for device "{}"!'.format(self.name))
        else:
            self.closed = True

    def set_delay(self, delay_ms):
        self.delay_ms = delay_ms

    def set_loss(self, loss_percent):
        self.loss_percent = loss_percent

    def update(self):
        self.run_qdisc_cmd(cmd_type="change")

atexit.register(NetDev.close_all)
atexit.register(kill_all)

def run_proc(cmd, add_to_outstanding=True):
    proc = subproc.Popen(cmd, stdout=subproc.PIPE, stderr=subproc.PIPE, stdin=subproc.PIPE, process_group=0)
    if add_to_outstanding:
        CHILD_PROCESSES.add(proc)
    return proc

def kill_proc(proc):
    run_proc(["kill", "-9", str(-proc.pid)], False).wait()
    if proc in CHILD_PROCESSES:
        CHILD_PROCESSES.remove(proc)

def parse_all_socket_syscalls(lines):
    sockets = {}

    for true_line in lines:
        if not true_line.startswith("socket("):
            continue
        line = true_line.replace(" ","")
        parsed = parse.parse("socket({},{},{})={}", line)
        if parsed == None:
            eprintln("Failed to parse line starting with 'socket': Line=\'",line,"'")
            continue
        domain, sock_type, prot, sock_id = parsed
        if sock_id in sockets.keys():
            eprintln("Multiple definitions of socket {}".format(sock_id))
            continue
        sockets[sock_id] = (domain,sock_type,prot)

    return sockets


def handle_strace_output(data, output):

    # First split the output by PID
    pid_lines = {}
    for line in output.splitlines():
        pid_str, syscall_str = line.split(" ", maxsplit=1)
        pid = int(pid_str)
        syscall_str = syscall_str.strip()
        if pid in pid_lines.keys():
            pid_lines[pid].append(syscall_str)
        else:
            pid_lines[pid] = [syscall_str]
    for pid, lines in pid_lines.items():
        for line in lines:
            #print("pid={}: {}".format(pid, line))
            pass

    # We need to patch up each pid's output,
    # Currently we'll have lots of <... unfinished> <... resumed>
    # back to back from when the PID's were all interleaved
    STRACE_UNFINISHED = "<unfinished ...>"
    pid_patched_lines = {}
    for pid, lines in pid_lines.items():
        patched = []
        unfinished = None
        for line in lines:
            if line.endswith(STRACE_UNFINISHED):
                if unfinished is not None:
                    raise RuntimeError("Two unfinished syscalls at once")
                else:
                    unfinished = line[0:len(line)-len(STRACE_UNFINISHED)]
            elif line.startswith("<..."):
                if unfinished is None:
                    raise RuntimeError("Unmatched resume statement in strace output")
                else:
                    _, second_half = line.split(">", maxsplit=1)
                    new_line = unfinished + second_half
                    patched.append(new_line)
                    unfinished = None
            else:
                patched.append(line)
        pid_patched_lines[pid] = patched

    pid_lines = pid_patched_lines

    data['num_unique_pid'] = len(pid_lines.keys())

    pid_socket_info = {}
    for pid, lines in pid_lines.items():
        pid_socket_info[pid] = parse_all_socket_syscalls(lines)

    raw = "\n"
    for pid, lines in pid_lines.items():
        for line in lines:
            raw += str(pid) + ": " + line + "\n"
    data['strace_raw'] = raw

def run_test(browser_cmd, website, netdev):

    strace_output_file = "strace.tmp"
    
    cmd = ["strace", "-f", "-o", strace_output_file, "-e", "trace=network,close"]
    cmd.extend(re.split(r'\s+', browser_cmd.replace('$URL', website)))

    now = datetime.now()
    proc = run_proc(cmd)

    stdout = b""
    stderr = b""
    try:
        stdout, stderr = proc.communicate(timeout=MAX_RUNTIME)
    except subproc.TimeoutExpired:
        #print("Killing Process: {}".format(proc.pid))
        kill_proc(proc)
        #print("Communicating with Process: {}".format(proc.pid))
        stdout, stderr = proc.communicate()

    stdout = stdout.decode()
    stderr = stderr.decode()
    strace = ""
    with open(strace_output_file, 'r') as file:
        strace = file.read()

    run_data = {}
    run_data['website'] = website
    run_data['browser'] = browser_cmd
    run_data['delay_ms'] = netdev.delay_ms
    run_data['loss_percent'] = netdev.loss_percent
    run_data['date'] = now.strftime("%m/%d/%Y")
    run_data['time'] = now.strftime("%H:%M:%S")
    run_data['stderr'] = repr(stderr)

    handle_strace_output(run_data, strace)

    os.remove(strace_output_file)

    return run_data

def main():
    parser = argparse.ArgumentParser(
            prog="bfall",
            description='Tests a Browser\'s HTTP/3 Fallback Mechanism'
            )
    parser.add_argument('netdev')
    parser.add_argument('website_list')
    parser.add_argument('browser_command_list')
    parser.add_argument('output_csv')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    global VERBOSE
    VERBOSE=args.verbose

    website_list = []
    with open(args.website_list) as website_file:
        website_list = [line.strip() for line in website_file.readlines()]

    browser_command_list = []
    with open(args.browser_command_list) as browser_command_file:
        browser_command_list = [line.strip() for line in browser_command_file.readlines()]

    netdev = NetDev(args.netdev)

    delay_list = list(range(0,101,10))
    loss_list = list(range(0,91,10))

    netdev.set_delay(100)
    netdev.set_loss(10)
    netdev.update()

    data = []
    with Progress(
            rich.progress.TextColumn("[progress.description]{task.description}"),
            rich.progress.BarColumn(),
            rich.progress.TaskProgressColumn(),
            rich.progress.TimeRemainingColumn(),
            rich.progress.MofNCompleteColumn(),
            ) as progress, open(args.output_csv, 'a') as csv_file:

        # Figure out the file size (the seek might not be necessary but let's be safe)
        csv_file.seek(0, os.SEEK_END)
        original_size = csv_file.tell()

        # Write to the end
        writer = None 

        iteration_space = list(itertools.product(delay_list,loss_list,browser_command_list,website_list))

        total_task = progress.add_task("[green]Total", total=len(iteration_space))

        for i in iteration_space:
            delay,loss,browser,website = i
            progress.console.print("Working on: Loss({}%), Delay({}ms), Browser({}), Website({})".format(loss,delay,browser,website))
            netdev.set_delay(delay)
            netdev.set_loss(loss)
            run_data = run_test(browser,website,netdev)
            if writer == None:
                writer = csv.DictWriter(csv_file, run_data.keys())
                if original_size == 0:
                    writer.writeheader()
            writer.writerow(run_data)
            progress.advance(total_task)
            
    exit(0)

if __name__ == "__main__":
    main()

