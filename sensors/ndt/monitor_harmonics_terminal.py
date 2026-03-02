#!/usr/bin/env python3
"""Ultra-fast terminal plotter with ASCII visualization and color codes.

Usage:
    python3 monitor_harmonics_terminal.py /dev/ttyUSB0 --baud 1000000

Shows real-time harmonics with no GUI lag whatsoever.
"""

import argparse
import sys
import time
import struct
import math
import os
from collections import deque

from packet import PacketSerial, Packet
from pac_ids import GET_MASK, SET_MASK, PAC_ID_HARMONICS_RX, PAC_ID_SETTINGS_STREAMING


# ANSI color codes
class Color:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    COLORS = [RED, GREEN, BLUE, YELLOW, MAGENTA, CYAN, WHITE]


def parse_harmonics(data):
    """Parse harmonics payload into list of (real, imag) complex pairs."""
    n_floats = len(data) // 4
    
    # Convert middle-endian floats to big-endian floats
    bigendian = bytearray(0)
    for i in range(0, len(data), 4):
        lsword = data[i : i + 2]
        word = data[i + 2 : i + 4] + lsword
        bigendian += word
    
    floats = list(struct.unpack(f">{n_floats}f", bytes(bigendian)))
    
    # Pair into (real, imag) tuples
    harmonics = []
    for i in range(0, len(floats), 2):
        real = floats[i]
        imag = floats[i + 1] if i + 1 < len(floats) else 0.0
        magnitude = math.sqrt(real**2 + imag**2)
        phase = math.atan2(imag, real)
        harmonics.append({
            'real': real,
            'imag': imag,
            'mag': magnitude,
            'phase': phase
        })
    return harmonics


def format_bar(value, width=40, range_max=100):
    """Create a bar chart visualization.  Wider default for longer bars."""
    if range_max <= 0:
        range_max = 1
    normalized = max(0, min(1, value / range_max))
    filled = int(normalized * width)
    bar = '█' * filled + '░' * (width - filled)
    return bar


def main():
    parser = argparse.ArgumentParser(
        description="Ultra-fast terminal harmonics visualization."
    )
    parser.add_argument("port", help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=1000000,
                        help="Baud rate (default: 1000000)")
    parser.add_argument("--harmonic", type=int, default=2,
                        help="Harmonic index to track (0=fund, 1=3rd, 2=5th, default: 2)")
    parser.add_argument("--baseline-secs", type=float, default=3.0,
                        help="Collect baseline for N seconds")
    
    args = parser.parse_args()
    
    try:
        ps = PacketSerial(args.port, args.baud, timeout=0.5)
    except Exception as e:
        print(f"Failed to open {args.port}: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Enable streaming
    stream_enable = 4  # bit 2 for RXV
    stream_payload = struct.pack(">B", stream_enable)
    
    stream_req = Packet(
        device_address=0,
        command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
        seq_num=0,
        payload=stream_payload
    )
    
    try:
        ps.send(stream_req)
        time.sleep(0.2)
    except Exception as e:
        print(f"Error enabling streaming: {e}", file=sys.stderr)
    
    pkt_count = 0
    harmonic_idx = args.harmonic
    baseline_mags = deque(maxlen=int(100 * args.baseline_secs / 0.3))
    baseline_time = time.time()
    baseline_done = False
    baseline_mean = None
    baseline_std = None
    last_baseline_update = 0
    
    history = deque(maxlen=32)  # keep a little more for scaling
    mag_history = deque(maxlen=32)  # magnitudes for selected harmonic
    
    print(f"\n{Color.BOLD}Harmonics Monitor (Terminal) - {args.port} @ {args.baud}{Color.RESET}\n")
    print(f"Tracking H{harmonic_idx}  |  Baseline: {args.baseline_secs}s\n")
    
    try:
        while True:
            try:
                pkt = ps.receive()
            except Exception:
                continue
            
            if pkt is None:
                continue
            
            if (pkt.command & ~GET_MASK) != PAC_ID_HARMONICS_RX:
                continue
            
            try:
                harmonics = parse_harmonics(pkt.payload)
            except Exception:
                continue
            
            pkt_count += 1
            now = time.time()
            elapsed = now - baseline_time
            
            # Collect baseline
            if harmonic_idx < len(harmonics):
                mag = harmonics[harmonic_idx]['mag']
                mag_history.append(mag)
                baseline_mags.append(mag)
                
                if not baseline_done and elapsed < args.baseline_secs:
                    if now - last_baseline_update > 0.1:  # Update display every 0.1s
                        sys.stdout.write('\r' + f"Baseline: {elapsed:.1f}/{args.baseline_secs:.1f}s  ")
                        sys.stdout.flush()
                        last_baseline_update = now
                elif not baseline_done:
                    baseline_done = True
                    mags = list(baseline_mags)
                    baseline_mean = sum(mags) / len(mags)
                    baseline_std = math.sqrt(
                        sum((x - baseline_mean)**2 for x in mags) / len(mags)
                    ) if len(mags) > 1 else 0.1
                    print(f"\n\nBaseline: mean={baseline_mean:.1f}, std={baseline_std:.1f}\n")
            
            # Keep minimal history
            history.append({
                'harmonics': harmonics,
                'time': pkt_count
            })
            
            # Clear screen and display (every 30 updates for speed, but text updates are fast)
            if pkt_count % 3 == 0:
                os.system('clear')
                
                print(f"{Color.BOLD}Harmonics - Packet {pkt_count}{Color.RESET}\n")
                
                # Show all harmonics
                for idx in range(min(8, len(harmonics))):
                    h = harmonics[idx]
                    color = Color.COLORS[idx % len(Color.COLORS)]
                    
                    # Determine dynamic bar range from recent history
                    recent_max = max(mag_history) if mag_history else 50
                    bar_max = max(recent_max * 1.2,
                                  (baseline_mean + 5 * baseline_std if baseline_mean else 0),
                                  50)
                    bar = format_bar(h['mag'], width=40, range_max=bar_max)
                    
                    # Select marker for watched harmonic
                    marker = f" {Color.BOLD}◄─{Color.RESET}" if idx == harmonic_idx else ""
                    
                    print(f"{color}H{idx}{Color.RESET} | "
                          f"R={h['real']:7.1f}  I={h['imag']:7.1f}  "
                          f"M={h['mag']:7.1f} {bar}{marker}")
                

                # draw scale axis underneath bars
                # calculate tick values at quartiles
                tick_count = 4
                labels = []
                for i in range(tick_count + 1):
                    labels.append(f"{bar_max * i / tick_count:.1f}")
                label_line = "".join(l.center(10) for l in labels)
                bar_line = "".join("|".center(10) for _ in labels)
                print()
                print("Scale:", label_line)
                print("      ", bar_line)
                current_mag = harmonics[harmonic_idx]['mag'] if harmonic_idx < len(harmonics) else 0

    
    except KeyboardInterrupt:
        print(f"\n\n{Color.GREEN}Stopped{Color.RESET}")
        
        # Disable streaming
        try:
            stream_disable = 0
            disable_payload = struct.pack(">B", stream_disable)
            stop_req = Packet(
                device_address=0,
                command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
                seq_num=0,
                payload=disable_payload
            )
            ps.send(stop_req)
        except Exception:
            pass
        
        ps.close()
        sys.exit(0)


if __name__ == '__main__':
    main()
