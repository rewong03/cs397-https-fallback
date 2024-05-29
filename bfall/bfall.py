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
from ast import literal_eval

from throttle import NetDev
from proc import *
from trace import *
from analysis import *

VERBOSE=False
MAX_RUNTIME=15

CHARS_PER_BYTE=4
MAX_STRACE_STR_LEN=(2**16)*CHARS_PER_BYTE

def eprintln(*args,**kwargs):
    print("ERROR: ", end='')
    print(*args, **kwargs)

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
        # leave off the last entry
        pid_lines[pid] = lines[:len(lines)-1]

    # We need to patch up each pid's output,
    # Currently we'll have lots of <... unfinished> <... resumed>
    # back to back from when the PID's were all intejrleaved
    STRACE_UNFINISHED = "<unfinished ...>"
    pid_patched_lines = {}
    for pid, lines in pid_lines.items():
        patched = []
        unfinished = None
        for line in lines:
            if line.endswith(STRACE_UNFINISHED):
                if unfinished is not None:
                    eprintln("Unfinished = {}".format(unfinished))
                    eprintln("New Unfinished = {}".format(line))
                    raise RuntimeError("Two unfinished syscalls at once: pid = {}".format(pid))
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
    #for pid, lines in pid_lines.items():
    #    for line in lines:
    #        print("{}: {}".format(pid, line))
     
    data['num_unique_pid'] = len(pid_lines.keys())

    traced_processes = {}
    for pid, lines in pid_lines.items():
        traced_processes[pid] = TracedProcess(pid, lines)

    return traced_processes

def run_test(browser_cmd, website, netdev):

    strace_output_file = "strace.tmp"

    piped_in = '""'
    
    cmd = ["strace", "-f", "-o", strace_output_file, "-e", "trace=network", "-v", "-s", str(MAX_STRACE_STR_LEN), "-x"]
    s = browser_cmd.replace('$URL',website).split("<")
    if len(s) > 1:
        piped_in = s[1].strip()
    cmd.extend(re.split(r'\s+', s[0]))
    piped_in = literal_eval(piped_in)

    now = datetime.now()
    proc = run_proc(cmd)
    proc.stdin.write(piped_in.encode())

    timed_out = False
    stdout = b""
    stderr = b""
    try:
        stdout, stderr = proc.communicate(timeout=MAX_RUNTIME)
    except subproc.TimeoutExpired:
        #print("Killing Process: {}".format(proc.pid))
        kill_proc(proc)
        #print("Communicating with Process: {}".format(proc.pid))
        stdout, stderr = proc.communicate()
        timed_out = True

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
    run_data['timed_out'] = timed_out
    run_data['date'] = now.strftime("%m/%d/%Y")
    run_data['time'] = now.strftime("%H:%M:%S")
    #run_data['stderr'] = repr(stderr)

    traced_processes = handle_strace_output(run_data, strace)
    run_data['num_proc'] = len(traced_processes.keys())

    analyze_traced_processes(run_data, traced_processes)

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

    delay_list = [0,5,50,200]
    loss_list = [0,5,15,50,90]

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
            delay,loss,browser_cmd,website = i
            progress.console.print("Working on: Loss({}%), Delay({}ms), Browser({}), Website({})".format(loss,delay,browser_cmd,website))
            netdev.set_delay(delay)
            netdev.set_loss(loss)
            run_data = run_test(browser_cmd,website,netdev)
            if writer == None:
                writer = csv.DictWriter(csv_file, run_data.keys())
                if original_size == 0:
                    writer.writeheader()
            writer.writerow(run_data)
            progress.advance(total_task)
            
    exit(0)

if __name__ == "__main__":
    main()

