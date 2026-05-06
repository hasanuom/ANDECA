#!/usr/bin/env python3
"""Capture harmonics for a fixed duration, save CSV, and plot afterwards.

Usage:
    python3 monitor_capture_and_plot.py --baud 1000000 --harmonic 2 --duration 30

The script enables streaming mode, collects data for the specified duration
(seconds), writes a CSV file containing timestamp, packet count and the selected
harmonic's real/imag/magnitude, then pops up a matplotlib plot of magnitude vs
time.  All heavy plotting happens after capture, eliminating real‑time lag.
"""

import argparse
import csv
import sys
import time
import struct
import math
import os
from datetime import datetime

import matplotlib.pyplot as plt

from packet import PacketSerial, Packet
from pac_ids import GET_MASK, SET_MASK, PAC_ID_HARMONICS_RX, PAC_ID_SETTINGS_STREAMING

OUTPUT_DIR = "/media/andeca/ENUODA/readings/monitor_capture_and_plot"


def parse_harmonics(data):
    n_floats = len(data) // 4
    bigendian = bytearray(0)
    for i in range(0, len(data), 4):
        lsword = data[i : i + 2]
        word = data[i + 2 : i + 4] + lsword
        bigendian += word
    floats = list(struct.unpack(f">{n_floats}f", bytes(bigendian)))
    harmonics = []
    for i in range(0, len(floats), 2):
        real = floats[i]
        imag = floats[i + 1] if i + 1 < len(floats) else 0.0
        magnitude = math.sqrt(real * real + imag * imag)
        harmonics.append({'real': real, 'imag': imag, 'mag': magnitude})
    return harmonics


def main():
    parser = argparse.ArgumentParser(description="Capture harmonics to CSV then plot.")
    parser.add_argument("--port", type=str, default="/dev/ttyUSB0", help="Serial port")
    parser.add_argument("--baud", type=int, default=1000000, help="Baud rate")
    parser.add_argument("--harmonic", type=int, default=2,
                        help="Harmonic index to save/plot")
    parser.add_argument("--duration", type=float, default=30.0,
                        help="Capture duration in seconds")
    parser.add_argument("--output", default=None,
                        help="CSV filename (default timestamped)")
    args = parser.parse_args()

    try:
        ps = PacketSerial(args.port, args.baud, timeout=0.5)
    except Exception as e:
        print(f"Failed to open port: {e}", file=sys.stderr)
        sys.exit(1)

    # enable streaming (RXV)
    stream_enable = 4
    payload = struct.pack(">B", stream_enable)
    req = Packet(device_address=0,
                 command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
                 seq_num=0,
                 payload=payload)
    try:
        ps.send(req)
        time.sleep(0.2)
    except Exception as e:
        print(f"Failed to enable streaming: {e}", file=sys.stderr)

    start = time.time()
    records = []
    records1 = []
    records2 = []
    records3 = []
    pkt_count = 0

    try:
        while True:
            if time.time() - start >= args.duration:
                break
            pkt = ps.receive()
            if pkt is None:
                continue
            if (pkt.command & ~GET_MASK) != PAC_ID_HARMONICS_RX:
                continue
            try:
                harmonics = parse_harmonics(pkt.payload)
            except Exception:
                continue
            pkt_count += 1
            ts = datetime.now().isoformat()
            if args.harmonic < len(harmonics):
                #h = harmonics[args.harmonic]
                h = harmonics[0]
                h1 = harmonics[1]
                h2 = harmonics[2] 
                h3 = harmonics[3]
            else:
                h = {'real': 0.0, 'imag': 0.0, 'mag': 0.0}
            records.append((ts, pkt_count, h['real'], h['imag'], h['mag'])) 
            records1.append((ts, pkt_count, h1['real'], h1['imag'], h1['mag']))
            records2.append((ts, pkt_count, h2['real'], h2['imag'], h2['mag']))
            records3.append((ts, pkt_count, h3['real'], h3['imag'], h3['mag']))

    except KeyboardInterrupt:
        pass
    finally:
        # disable streaming
        try:
            off = struct.pack(">B", 0)
            stopreq = Packet(device_address=0,
                             command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
                             seq_num=0,
                             payload=off)
            ps.send(stopreq)
        except Exception:
            pass
        # PacketSerial wraps a pyserial.Serial; close underlying port if present
        try:
            ps.ser.close()
        except Exception:
            pass

    if not records:
        print("No data captured")
        return

    # write CSV
    # ensure output directory exists
    out_dir = OUTPUT_DIR
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception:
        pass

    if args.output:
        fname = os.path.join(out_dir, args.output)
    else:
        #fname = os.path.join(out_dir,
        #                     f"harmonics_{args.port.replace('/', '_')}_{int(start)}.csv")
        fname = os.path.join(out_dir, "harmonics_0.csv")
        fname1 = os.path.join(out_dir, "harmonics_1.csv")
        fname2 = os.path.join(out_dir, "harmonics_2.csv")
        fname3 = os.path.join(out_dir, "harmonics_3.csv")

    with open(fname, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['timestamp', 'pkt', 'real', 'imag', 'mag'])
        w.writerows(records)
    print(f"Saved {len(records)} rows to {fname}")

    with open(fname1, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['timestamp', 'pkt', 'real', 'imag', 'mag'])
        w.writerows(records1)
    print(f"Saved {len(records1)} rows to {fname1}")

    with open(fname2, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['timestamp', 'pkt', 'real', 'imag', 'mag'])
        w.writerows(records2)
    print(f"Saved {len(records2)} rows to {fname2}")

    with open(fname3, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['timestamp', 'pkt', 'real', 'imag', 'mag'])
        w.writerows(records3)
    print(f"Saved {len(records3)} rows to {fname3}")

    # plot magnitude time series
    times = [i for (_, i, _, _, _) in records]
    mags = [r[4] for r in records]
    """
    plt.figure(figsize=(8,4))
    plt.plot(times, mags, '-')
    plt.xlabel('packet #')
    plt.ylabel(f'magnitude')
    plt.title(f'Magnitude vs packet (duration {args.duration}s)')
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    """
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    axs[0, 0].plot([r[1] for r in records], [r[4] for r in records], '-')
    axs[0, 0].set_title('Harmonic 0')
    axs[0, 0].set_xlabel('packet #')
    axs[0, 0].set_ylabel('magnitude')
    axs[0, 0].grid(True)

    axs[0, 1].plot([r[1] for r in records1], [r[4] for r in records1], '-')
    axs[0, 1].set_title('Harmonic 1')
    axs[0, 1].set_xlabel('packet #')
    axs[0, 1].set_ylabel('magnitude')
    axs[0, 1].grid(True)

    axs[1, 0].plot([r[1] for r in records2], [r[4] for r in records2], '-')
    axs[1, 0].set_title('Harmonic 2')
    axs[1, 0].set_xlabel('packet #')
    axs[1, 0].set_ylabel('magnitude')
    axs[1, 0].grid(True)

    axs[1, 1].plot([r[1] for r in records3], [r[4] for r in records3], '-')
    axs[1, 1].set_title('Harmonic 3')
    axs[1, 1].set_xlabel('packet #')
    axs[1, 1].set_ylabel('magnitude')
    axs[1, 1].grid(True)

    fig.suptitle(f"Harmonics 0-3 Magnitude vs Packet # (duration {args.duration}s)")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

if __name__ == '__main__':
    main()
