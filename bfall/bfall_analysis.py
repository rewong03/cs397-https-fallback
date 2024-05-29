#! /usr/bin/python3

import argparse
import csv
import scapy

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
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    with open(args.csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            vprintln(row['browser'], " : ", row['website'], " -> ", row['uuid'])

if __name__ == "__main__":
    main()

