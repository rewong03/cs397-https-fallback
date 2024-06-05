#! /usr/bin/python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import pyshark

VERBOSE=False

def vprintln(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def main():
    parser = argparse.ArgumentParser(
            prog="bfall_graph",
            description="Creates Graphs from the output of bfall_analysis and bfall_measure"
            )
    parser.add_argument('data_csv')
    parser.add_argument('analysis_csv')
    parser.add_argument('plot', default="AVG")
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    to_plot = args.plot

    global VERBOSE
    VERBOSE = args.verbose

    print("Reading ", args.data_csv)
    data = pd.read_csv(args.data_csv)
    data.set_index('uuid')

    print("Reading ", args.analysis_csv)
    analysis = pd.read_csv(args.analysis_csv)
    analysis.set_index('uuid')

    print("Joining the dataframes")
    df = data.merge(analysis, left_index=True,right_index=True)

    print(df)
    
    print("Plotting")

    if to_plot == "AVG":
        ax = df.plot(kind='line', x='loss_percent', y='REL_QUIC_AVG_TIME')
        df.plot(kind='line', x='loss_percent', y='REL_TCP_AVG_TIME', ax=ax)
        df.plot(kind='line', x='loss_percent', y='REL_TLS_AVG_TIME', ax=ax)
        plt.ylabel("Average Packet Appearance (sec)")
        plt.xlabel("Packet Loss %")
        plt.show()

    if to_plot == "LAST":
        ax = df.plot(kind='line', x='loss_percent', y='REL_QUIC_AVG_TIME')
        df.plot(kind='line', x='loss_percent', y='REL_TCP_AVG_TIME', ax=ax)
        df.plot(kind='line', x='loss_percent', y='REL_TLS_AVG_TIME', ax=ax)
        plt.ylabel("Average Packet Appearance (sec)")
        plt.xlabel("Packet Loss %")
        plt.show()

    if to_plot == "TIMES":
        TIMES_TO_CHECK = ["TLS","TCP","UDP","QUIC","DNS"]
        start_time = None
        for index,row in df.iterrows():
            all_times = {}
            for time in TIMES_TO_CHECK:
                all_times[time] = []
            print("Collecting Data from ", row['tshark_path'], '...')
            tshark = pyshark.FileCapture(row['tshark_path'], keep_packets=False)
            for packet in tshark:
                layer = packet.highest_layer
                time = packet.sniff_time.timestamp()

                if start_time == None:
                    start_time = time

                rel_time = time-start_time
                if layer in TIMES_TO_CHECK:
                    all_times[layer].append(rel_time)

            print("Plotting...")
            for layer in TIMES_TO_CHECK:
                times = all_times[layer]
                if len(times) == 0:
                    continue
                plt.hist(times,label=layer)
#                plt.pcolormesh([histogram]*2, cmap='inferno', shading='gouraud')

#                heatmap, xedges, yedges = np.histogram2d(times, [1]*len(times), bins=(np.linspace(0,length_track,length_track+1),1))
#                extent = [0, length_track+1, 0, 50]
#                plt.imshow(heatmap.T, extent=extent, origin='lower', cmap='jet',vmin=0,vmax=None)
            title = "Packet Arrivals (loss={}) (delay={})".format(row['loss_percent'], row['delay_ms'])
            plt.title(title)
            plt.legend()
            plt.savefig(title + ".png")
            plt.close()


if __name__ == "__main__":
    main()

