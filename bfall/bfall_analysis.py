#! /usr/bin/python3

import argparse
import pandas as pd
import pyshark
import rich.progress
import csv
from rich.progress import Progress

VERBOSE=False

def vprintln(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)

def main():
    parser = argparse.ArgumentParser(
            prog="bfall_analysis",
            description="Runs Analysis on the output of bfall_measure"
            )
    parser.add_argument('csv_file')
    parser.add_argument('output_csv')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    data = pd.read_csv(args.csv_file)
    data = data.set_index('uuid')

    row_datas = []

    with Progress(
            rich.progress.TextColumn("[progress.description]{task.description}"),
            rich.progress.BarColumn(),
            rich.progress.TaskProgressColumn(),
            rich.progress.TimeRemainingColumn(),
            rich.progress.MofNCompleteColumn(),
            ) as progress:
        row_task = progress.add_task("[green]Runs Analyzed", total=len(data))
        for index,row in data.iterrows():
            analysis_data = analyse_row(index,row,progress)
            fallback = determine_fallback(row,analysis_data)
            row_datas.append(analysis_data)
            progress.advance(row_task)

    output_csv = open(args.output_csv, 'w+')

    writer = None
    for row in row_datas:
        if writer == None:
            writer = csv.DictWriter(output_csv, row.keys())
            writer.writeheader()
        writer.writerow(row)

    output_csv.close()
 
    print("Done")

        
COUNTED_LAYERS = ['TCP','QUIC','UDP','DNS','TLS','HTTP','HTTPS']
TIMED_LAYERS = ['TCP','QUIC','TLS']

def analyse_row(uuid,data,progress):
    files = []

    print(data['tshark_path'])
    tshark = pyshark.FileCapture(data['tshark_path'], keep_packets=False)
    packet_task = progress.add_task("[cyan]Packets Analyzed", total=None)

    row_data = {}
    row_data['uuid'] = uuid

    global COUNTED_LAYERS
    row_data['PKTS'] = 0
    for layer in COUNTED_LAYERS:
        row_data[layer + "_PKTS"] = 0

    for packet in tshark:
        analyze_packet(packet, row_data)
        progress.advance(packet_task)

    global TIMED_LAYERS
    if 'START_TIME' in row_data.keys():
        row_data['REL_AVG_TIME'] = row_data['AVG_TIME'] - row_data['START_TIME']
        for layer in TIMED_LAYERS:
            row_data['REL_' + layer + '_AVG_TIME'] = row_data[layer + '_AVG_TIME'] - row_data['START_TIME']
            if row_data[layer + '_FIRST_TIME'] == None:
                row_data[layer + '_FIRST_TIME'] = row_data['START_TIME']
            row_data['REL_' + layer + '_FIRST_TIME'] = row_data[layer + '_FIRST_TIME'] - row_data['START_TIME']
            row_data['REL_' + layer + '_LAST_TIME'] = row_data[layer + '_LAST_TIME'] - row_data['START_TIME']


    tshark.close()
    for file in files:
        file.close()

    progress.remove_task(packet_task)
    return row_data

def analyze_packet(packet, row_data):

    global TIMED_LAYERS
    protocol = packet.highest_layer
    time = packet.sniff_time.timestamp()

    if not 'START_TIME' in row_data.keys():
       row_data['START_TIME'] = time
       row_data['AVG_TIME'] = time
       for layer in TIMED_LAYERS:
           row_data[layer + '_FIRST_TIME'] = None
           row_data[layer + '_LAST_TIME'] = time
           row_data[layer + '_AVG_TIME'] = time

    global COUNTED_LAYERS
    if protocol in COUNTED_LAYERS:
        row_data[protocol + "_PKTS"] += 1
    if protocol in TIMED_LAYERS:
        if row_data[protocol + '_FIRST_TIME'] == None:
            row_data[protocol + '_FIRST_TIME'] = time
        row_data[protocol + '_LAST_TIME'] = time
    row_data["PKTS"] += 1

    
    num = row_data['PKTS']
    old_num = num-1
    # Running average
    row_data['AVG_TIME'] = ((row_data['AVG_TIME'] * old_num) + time) / num
   
    if protocol in TIMED_LAYERS:
        num = row_data[protocol + '_PKTS']
        old_num = num-1
        # Running average
        row_data[protocol + '_AVG_TIME'] = ((row_data[protocol + '_AVG_TIME'] * old_num) + time) / num

def determine_fallback(row,data):

    if data['QUIC_PKTS'] == 0:
        print("No Fallback (NO QUIC)!")
        return False

    FALLBACK_THRESHOLD = 5.0
    WEIGHTS = {}
    WEIGHTS['quic_avg_earlier'] = 1.0
    WEIGHTS['quic_last_early'] = 5.0
    WEIGHTS['tls_first_later_than_quic_last'] = 1.0
    WEIGHTS['quic_last_later_than_tcp_last'] = -10.0
    WEIGHTS['tls_avg_later'] = 1.0
    WEIGHTS['tcp_avg_later'] = 1.0

    COND = {}
    COND['quic_avg_earlier'] = lambda row,data: data['REL_QUIC_AVG_TIME'] < data['REL_AVG_TIME']
    COND['quic_last_early'] = lambda row,data: data['REL_QUIC_LAST_TIME'] < data['REL_AVG_TIME']
    COND['tls_first_later_than_quic_last'] = lambda row,data: data['TLS_FIRST_TIME'] > data['QUIC_LAST_TIME']
    COND['quic_last_later_than_tcp_last'] = lambda row,data: data['QUIC_LAST_TIME'] > data['TCP_LAST_TIME']
    COND['tls_avg_later'] = lambda row,data: data['TLS_AVG_TIME'] > data['AVG_TIME']
    COND['tcp_avg_later'] = lambda row,data: data['TCP_AVG_TIME'] > data['AVG_TIME']

    conf = 0.0
    for key,weight in WEIGHTS.items():
        if not key in COND.keys():
            raise RuntimeError("Key {} in WEIGHTS but not COND!".format(key))
        if COND[key](row,data):
            conf += weight

    fallback = False
    if conf > FALLBACK_THRESHOLD:
        fallback = True

    if fallback:
        print("Fallback! conf={}".format(conf))
    else:
        print("No Fallback! conf={}".format(conf))

    data['FALLBACK'] = fallback
    return fallback

if __name__ == "__main__":
    main()

